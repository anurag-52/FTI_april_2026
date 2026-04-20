"""
AGENT 3 — SCAN ENGINE
scan_runner.py

Daily EOD scan orchestrator. Called by:
1. Render Cron Job at 4:30 PM IST daily (Mon-Fri)
2. POST /internal/scan/run endpoint (manual trigger by admin/trader)

Sequence:
1. Check if today is a market holiday → skip + notify
2. Fetch EOD data for all watchlisted stocks (deduplicated)
3. Compute indicators + store in stock_prices
4. Per active trader: generate BUY and EXIT signals
5. Create notification_sessions
6. Dispatch notifications at 5:00 PM IST
"""
import logging
from datetime import date, datetime, timezone
from typing import Optional
import uuid

from config import supabase
from scan_engine.data_fetcher import fetch_ohlcv_yfinance
from scan_engine.indicator_engine import compute_indicators, compute_signals

logger = logging.getLogger(__name__)


def is_market_holiday(scan_date: date) -> Optional[dict]:
    """Check if today is a market holiday. Returns holiday record or None."""
    result = supabase.table("market_holidays").select("*").eq("holiday_date", str(scan_date)).execute()
    return result.data[0] if result.data else None


def get_all_active_watchlist_stocks() -> list:
    """Get deduplicated list of all stocks across all active traders' watchlists."""
    result = supabase.table("watchlists") \
        .select("stock_id, stocks(id, ticker_nse, ticker_bse, exchange)") \
        .eq("is_active", True) \
        .execute()

    seen = set()
    stocks = []
    for row in result.data or []:
        s = row.get("stocks")
        if s and s["id"] not in seen:
            seen.add(s["id"])
            stocks.append(s)
    return stocks


def compute_position_size(available_capital: float, risk_pct: float,
                           entry_price: float, stop_loss: float) -> int:
    """
    Courtney Smith position sizing formula:
    Qty = (Capital × Risk%) ÷ (Entry Price − Stop Loss)
    """
    if entry_price <= stop_loss or available_capital <= 0:
        return 0
    risk_amount = available_capital * (risk_pct / 100)
    risk_per_share = entry_price - stop_loss
    qty = int(risk_amount / risk_per_share)
    return max(qty, 0)


def run_daily_scan(triggered_by: str = "AUTO", triggered_by_user: Optional[str] = None) -> dict:
    """
    Main scan entry point. Returns summary dict.
    """
    scan_date = date.today()
    started_at = datetime.now(timezone.utc)

    # Log start
    scan_log_id = supabase.table("scan_log").insert({
        "scan_date": str(scan_date),
        "started_at": started_at.isoformat(),
        "status": "running",
        "triggered_by": triggered_by,
        "triggered_by_user": triggered_by_user
    }).execute().data[0]["id"]

    def complete_log(status, source=None, stocks_scanned=0, signals_generated=0, errors=None):
        supabase.table("scan_log").update({
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "data_source": source,
            "stocks_scanned": stocks_scanned,
            "signals_generated": signals_generated,
            "errors": errors
        }).eq("id", scan_log_id).execute()

    # 1. Holiday check
    holiday = is_market_holiday(scan_date)
    if holiday:
        logger.info(f"Market holiday: {holiday['holiday_name']}. Skipping scan.")
        complete_log("skipped_holiday")
        _notify_all_traders_holiday(scan_date, holiday["holiday_name"])
        return {"status": "skipped_holiday", "message": holiday["holiday_name"]}

    # 2. Get all watchlist stocks
    stocks = get_all_active_watchlist_stocks()
    if not stocks:
        complete_log("completed", stocks_scanned=0, signals_generated=0)
        return {"status": "completed", "message": "No active watchlist stocks"}

    logger.info(f"Starting scan for {len(stocks)} stocks on {scan_date}")

    # 3. Fetch + compute indicators for each stock
    total_signals = 0
    fetch_errors = []

    for stock in stocks:
        try:
            _fetch_and_store_indicators(stock, scan_date)
        except Exception as e:
            logger.error(f"Error processing {stock['ticker_nse']}: {e}")
            fetch_errors.append(f"{stock['ticker_nse']}: {str(e)}")

    # 4. Generate per-trader signals
    active_traders = _get_active_traders()
    for trader in active_traders:
        trader_signals = _generate_trader_signals(trader, scan_date)
        total_signals += len(trader_signals)

        # Update inactivity
        _update_inactivity(trader, len(trader_signals) > 0)

    complete_log(
        "completed",
        source="yfinance",
        stocks_scanned=len(stocks),
        signals_generated=total_signals,
        errors="; ".join(fetch_errors) if fetch_errors else None
    )

    logger.info(f"Scan complete: {total_signals} signals generated for {len(active_traders)} traders")
    return {
        "status": "completed",
        "stocks_scanned": len(stocks),
        "signals_generated": total_signals,
        "traders": len(active_traders)
    }


def _fetch_and_store_indicators(stock: dict, scan_date: date):
    """Fetch 60+ days of data, compute indicators, store today's row."""
    from datetime import timedelta
    import pandas as pd

    ticker = stock["ticker_nse"]
    stock_id = stock["id"]

    # Fetch last 120 days for indicator computation (need 55+ for channels)
    from_date = scan_date - timedelta(days=120)
    df = fetch_ohlcv_yfinance(ticker, from_date, scan_date)

    if df is None or df.empty:
        logger.warning(f"No data for {ticker} on {scan_date}")
        return

    # Compute indicators
    df = compute_indicators(df)
    df = compute_signals(df)

    # Get today's row
    today_rows = df[df["date"] == scan_date]
    if today_rows.empty:
        logger.warning(f"No today's data for {ticker}")
        return

    row = today_rows.iloc[-1]

    def safe(val):
        if val is None or (isinstance(val, float) and (val != val)):
            return None
        return float(val) if isinstance(val, (int, float)) else val

    # Upsert into stock_prices
    supabase.table("stock_prices").upsert({
        "stock_id": stock_id,
        "price_date": str(scan_date),
        "open": safe(row.get("open")),
        "high": safe(row["high"]),
        "low": safe(row["low"]),
        "close": safe(row["close"]),
        "volume": int(row.get("volume", 0)) if row.get("volume") else None,
        "ch55_high": safe(row.get("ch55_high")),
        "ch55_low": safe(row.get("ch55_low")),
        "ch20_high": safe(row.get("ch20_high")),
        "ch20_low": safe(row.get("ch20_low")),
        "adx_20": safe(row.get("adx_20")),
        "adx_rising": bool(row.get("adx_rising")) if row.get("adx_rising") is not None else None,
        "ch55_high_flat_days": int(row.get("ch55_high_flat_days", 0)),
        "ch55_low_flat_days": int(row.get("ch55_low_flat_days", 0)),
        "buy_signal": bool(row.get("buy_signal", False)),
        "exit_trailing_stop": bool(row.get("exit_trailing_stop", False)),
        "exit_adx": bool(row.get("exit_adx", False)),
        "exit_rejection": False,  # Per-position, set separately
        "any_exit_signal": bool(row.get("any_exit_signal", False)),
        "hit_upper_circuit": bool(row.get("hit_upper_circuit", False)),
        "hit_lower_circuit": bool(row.get("hit_lower_circuit", False)),
    }, on_conflict="stock_id,price_date").execute()


def _get_active_traders() -> list:
    """Get all active traders (not paused, not suspended)."""
    result = supabase.table("users") \
        .select("*") \
        .eq("role", "trader") \
        .eq("status", "active") \
        .execute()
    return result.data or []


def _generate_trader_signals(trader: dict, scan_date: date) -> list:
    """Generate BUY and EXIT signals for a specific trader."""
    user_id = trader["id"]
    signals_created = []

    # Get trader's active watchlist
    watchlist = supabase.table("watchlists") \
        .select("stock_id, stocks(*)") \
        .eq("user_id", user_id) \
        .eq("is_active", True) \
        .execute().data or []

    # Get trader's open positions
    open_positions = supabase.table("positions") \
        .select("*, stocks(*)") \
        .eq("user_id", user_id) \
        .eq("status", "open") \
        .execute().data or []

    open_position_by_stock = {p["stock_id"]: p for p in open_positions}

    # Check for pending (unconfirmed) signals — skip stocks with pending signals
    pending = supabase.table("signals") \
        .select("stock_id") \
        .eq("user_id", user_id) \
        .is_("confirmed", "null") \
        .execute().data or []
    pending_stock_ids = {p["stock_id"] for p in pending}

    for item in watchlist:
        stock = item.get("stocks")
        if not stock:
            continue
        stock_id = stock["id"]

        # Skip if pending signal exists for this stock
        if stock_id in pending_stock_ids:
            continue

        # Get today's price data
        price_data = supabase.table("stock_prices") \
            .select("*") \
            .eq("stock_id", stock_id) \
            .eq("price_date", str(scan_date)) \
            .maybeSingle() \
            .execute().data

        if not price_data:
            continue

        # ── EXIT SIGNALS (check BEFORE buy) ──────────────────────────────
        if stock_id in open_position_by_stock:
            exit_triggered = False
            exit_type = None

            if price_data.get("exit_trailing_stop"):
                exit_triggered = True
                exit_type = "EXIT_TRAILING"
            elif price_data.get("exit_adx"):
                exit_triggered = True
                exit_type = "EXIT_ADX"

            # Rejection rule: check if position is 1-2 days old with no close above entry ch55_high
            pos = open_position_by_stock[stock_id]
            if not exit_triggered:
                entry_date = date.fromisoformat(pos["entry_date"])
                days_held = (scan_date - entry_date).days
                if days_held in [1, 2]:
                    # Was there a close above ch55_high since entry?
                    prices_since = supabase.table("stock_prices") \
                        .select("close, ch55_high") \
                        .eq("stock_id", stock_id) \
                        .gte("price_date", str(entry_date)) \
                        .lte("price_date", str(scan_date)) \
                        .execute().data or []

                    ch55_at_entry = pos.get("ch55_high_at_entry") or price_data.get("ch55_high")
                    any_breakout = any(
                        p["close"] and p["close"] > (ch55_at_entry or 0)
                        for p in prices_since
                    )
                    if not any_breakout and days_held == 2:
                        exit_triggered = True
                        exit_type = "EXIT_REJECTION"

            if exit_triggered and exit_type:
                # Create exit signal for ALL positions in this stock
                token = str(uuid.uuid4()).replace("-", "")
                supabase.table("signals").insert({
                    "user_id": user_id,
                    "stock_id": stock_id,
                    "signal_date": str(scan_date),
                    "signal_type": exit_type,
                    "trigger_price": price_data["close"],
                    "ch55_high_at_signal": price_data.get("ch55_high"),
                    "ch20_low_at_signal": price_data.get("ch20_low"),
                    "adx_at_signal": price_data.get("adx_20"),
                    "gap_risk_warning": price_data.get("gap_risk_warning", False),
                    "gap_down_pct": price_data.get("gap_down_pct"),
                    "circuit_warning": price_data.get("hit_lower_circuit", False),
                    "circuit_type": "LOWER" if price_data.get("hit_lower_circuit") else None,
                    "notification_token": token,
                }).execute()
                signals_created.append(exit_type)

        # ── BUY SIGNALS ──────────────────────────────────────────────────
        elif price_data.get("buy_signal"):
            # Calculate position size
            ch20_low = price_data.get("ch20_low") or price_data["close"] * 0.95
            qty = compute_position_size(
                trader["available_capital"],
                trader["risk_percent"],
                price_data["close"],
                ch20_low
            )

            token = str(uuid.uuid4()).replace("-", "")
            supabase.table("signals").insert({
                "user_id": user_id,
                "stock_id": stock_id,
                "signal_date": str(scan_date),
                "signal_type": "BUY",
                "trigger_price": price_data["close"],
                "ch55_high_at_signal": price_data.get("ch55_high"),
                "ch20_low_at_signal": ch20_low,
                "adx_at_signal": price_data.get("adx_20"),
                "flat_days": price_data.get("ch55_high_flat_days"),
                "suggested_qty": qty,
                "suggested_cost": round(qty * price_data["close"], 2) if qty else None,
                "circuit_warning": price_data.get("hit_upper_circuit", False),
                "circuit_type": "UPPER" if price_data.get("hit_upper_circuit") else None,
                "notification_token": token,
            }).execute()
            signals_created.append("BUY")

    # Create notification session for this trader (even if no signals)
    if signals_created:
        all_signals = supabase.table("signals") \
            .select("id") \
            .eq("user_id", user_id) \
            .eq("signal_date", str(scan_date)) \
            .execute().data or []

        session_token = str(uuid.uuid4()).replace("-", "")
        supabase.table("notification_sessions").upsert({
            "user_id": user_id,
            "signal_date": str(scan_date),
            "session_token": session_token,
            "has_signals": True,
            "total_rows": len(all_signals),
            "actioned_rows": 0,
            "submitted": False,
        }, on_conflict="user_id,signal_date").execute()

    return signals_created


def _update_inactivity(trader: dict, has_signals: bool):
    """Increment inactivity counter if trader has unconfirmed pending signals."""
    user_id = trader["id"]
    current_days = trader.get("inactivity_days", 0)

    pending = supabase.table("signals") \
        .select("id") \
        .eq("user_id", user_id) \
        .is_("confirmed", "null") \
        .execute().data or []

    updates = {}

    if pending:
        new_days = current_days + 1
        updates["inactivity_days"] = new_days

        if new_days == 5 and not trader.get("warned_day5"):
            updates["warned_day5"] = True
            # TODO: send day-5 warning notification
        elif new_days == 7:
            updates["status"] = "paused"
        elif new_days == 12 and not trader.get("warned_day12"):
            updates["warned_day12"] = True
            # TODO: send day-12 warning notification
        elif new_days == 15:
            updates["status"] = "suspended"

    if updates:
        supabase.table("users").update(updates).eq("id", user_id).execute()


def _notify_all_traders_holiday(scan_date: date, holiday_name: str):
    """Log market holiday notification for all active traders."""
    traders = supabase.table("users") \
        .select("id") \
        .eq("role", "trader") \
        .in_("status", ["active", "paused"]) \
        .execute().data or []

    # TODO: integrate with notifications.py when INTEGRATIONS-ENG complete
    logger.info(f"Holiday notification queued for {len(traders)} traders: {holiday_name}")
