"""
AGENT 3 — SCAN ENGINE
scan_runner.py

Daily EOD scan orchestrator. Called by:
  1. Render Cron Job at 4:30 PM IST daily (Mon-Fri)
  2. POST /internal/scan/run endpoint (manual trigger by admin/trader)

Complete Scan Sequence:
  1. Pre-check at 4:25 PM → is today a holiday? If yes → skip + notify
  2. Collect all unique stocks across active traders' watchlists
  3. Fetch EOD data for each stock (3-tier cascade)
  4. Compute indicators (channels, ADX, flat days, gaps, circuits)
  5. Compute buy/exit signal flags
  6. Store all fields in stock_prices table
  7. Per active trader:
     a. Read buy_signal flags for watchlist stocks
     b. Check exit signals on ALL open positions
     c. Check rejection rule per position (2 trading days)
     d. Skip stocks with unconfirmed pending signals
     e. Generate per-trader signals in signals table
     f. Apply position sizing formula
  8. Inactivity + auto-pause/suspend checks
  9. Stock suspension detection (3+ missing data days)
  10. Create notification_sessions per trader
  11. Log scan result in scan_log
"""
import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional, List, Dict, Set
import pandas as pd

from config import supabase
from scan_engine.data_fetcher import (
    fetch_stock_eod,
    get_existing_prices,
)
from scan_engine.indicator_engine import compute_indicators
from scan_engine.signal_engine import (
    compute_buy_signals,
    compute_exit_signals,
    check_rejection_rule,
    compute_position_size,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Main Entry Point
# ═══════════════════════════════════════════════════════════════════════════════

def run_daily_scan(
    triggered_by: str = "AUTO",
    triggered_by_user: Optional[str] = None,
) -> dict:
    """
    Main scan entry point. Returns summary dict.

    Args:
        triggered_by: 'AUTO' (cron), 'ADMIN', or 'TRADER'
        triggered_by_user: UUID of user who triggered (for manual scans)

    Returns:
        dict with scan results summary
    """
    scan_date = date.today()
    started_at = datetime.now(timezone.utc)

    # Create scan_log entry
    scan_log_id = _create_scan_log(scan_date, started_at, triggered_by, triggered_by_user)

    try:
        return _execute_scan(scan_date, scan_log_id, triggered_by, triggered_by_user)
    except Exception as e:
        logger.exception(f"Scan failed with unexpected error: {e}")
        _complete_scan_log(scan_log_id, "failed", errors=str(e))
        # Notify super admin of failure
        _notify_admin_scan_failure(scan_date, str(e))
        return {"status": "failed", "error": str(e)}


def _execute_scan(
    scan_date: date,
    scan_log_id: int,
    triggered_by: str,
    triggered_by_user: Optional[str],
) -> dict:
    """Core scan execution logic."""

    # ── Step 1: Holiday Check ────────────────────────────────────────────────
    holiday = _check_holiday(scan_date)
    if holiday:
        holiday_name = holiday["holiday_name"]
        logger.info(f"Market holiday: {holiday_name}. Skipping scan.")
        _complete_scan_log(scan_log_id, "skipped_holiday")
        _notify_all_traders_holiday(scan_date, holiday_name)
        return {"status": "skipped_holiday", "message": holiday_name}

    # Also check if it's a weekend
    if scan_date.weekday() >= 5:  # Saturday=5, Sunday=6
        logger.info(f"Weekend ({scan_date.strftime('%A')}). Skipping scan.")
        _complete_scan_log(scan_log_id, "skipped_holiday")
        return {"status": "skipped_weekend", "message": scan_date.strftime("%A")}

    # ── Step 2: Get all watchlist stocks (deduplicated) ──────────────────────
    stocks = _get_all_active_watchlist_stocks()
    if not stocks:
        _complete_scan_log(scan_log_id, "completed", stocks_scanned=0, signals_generated=0)
        return {"status": "completed", "message": "No active watchlist stocks"}

    logger.info(f"Starting scan for {len(stocks)} stocks on {scan_date}")

    # ── Step 3: Get holiday dates for gap detection ──────────────────────────
    holiday_dates = _get_holiday_dates_set()

    # ── Step 4: Fetch + Compute + Store per stock ────────────────────────────
    fetch_errors = []
    data_source_used = None
    stocks_with_data = 0

    for stock in stocks:
        ticker_display = stock.get("ticker_nse") or stock.get("ticker_bse") or stock["id"]
        try:
            source = _fetch_compute_and_store(stock, scan_date, holiday_dates,
                                              triggered_by, triggered_by_user)
            if source:
                data_source_used = data_source_used or source
                stocks_with_data += 1
            else:
                # Track missing data for suspension detection
                _track_missing_data(stock, scan_date)
        except Exception as e:
            logger.error(f"Error processing {ticker_display}: {e}")
            fetch_errors.append(f"{ticker_display}: {str(e)[:100]}")

    # ── Step 5: Generate per-trader signals ──────────────────────────────────
    active_traders = _get_active_traders()
    total_signals = 0
    traders_with_signals = 0

    for trader in active_traders:
        try:
            signals = _generate_trader_signals(trader, scan_date)
            signal_count = len(signals)
            total_signals += signal_count

            if signal_count > 0:
                traders_with_signals += 1

            # ── Step 6: Inactivity tracking ──────────────────────────────────
            _update_inactivity(trader, signal_count > 0, scan_date)

            # ── Step 7: Create notification session ──────────────────────────
            _create_notification_session(trader, scan_date, signal_count)

        except Exception as e:
            logger.error(f"Error generating signals for trader {trader['id']}: {e}")
            fetch_errors.append(f"trader-{trader['id'][:8]}: {str(e)[:100]}")

    # ── Step 8: Stock suspension detection ───────────────────────────────────
    _check_stock_suspensions()

    # ── Step 9: Complete scan log ────────────────────────────────────────────
    _complete_scan_log(
        scan_log_id,
        status="completed",
        source=data_source_used,
        stocks_scanned=len(stocks),
        signals_generated=total_signals,
        errors="; ".join(fetch_errors) if fetch_errors else None,
    )

    summary = {
        "status": "completed",
        "scan_date": str(scan_date),
        "stocks_scanned": len(stocks),
        "stocks_with_data": stocks_with_data,
        "signals_generated": total_signals,
        "traders_processed": len(active_traders),
        "traders_with_signals": traders_with_signals,
        "errors": fetch_errors if fetch_errors else None,
    }
    logger.info(f"Scan complete: {summary}")
    return summary


# ═══════════════════════════════════════════════════════════════════════════════
# Step 1: Holiday Check
# ═══════════════════════════════════════════════════════════════════════════════

def _check_holiday(scan_date: date) -> Optional[dict]:
    """Check if today is a market holiday."""
    result = supabase.table("market_holidays") \
        .select("*") \
        .eq("holiday_date", str(scan_date)) \
        .execute()
    return result.data[0] if result.data else None


# ═══════════════════════════════════════════════════════════════════════════════
# Step 2: Watchlist Stock Collection
# ═══════════════════════════════════════════════════════════════════════════════

def _get_all_active_watchlist_stocks() -> List[dict]:
    """Get deduplicated list of all stocks across all active traders' watchlists."""
    # Only get stocks from active traders' watchlists
    result = supabase.table("watchlists") \
        .select("stock_id, stocks(id, ticker_nse, ticker_bse, exchange, is_active)") \
        .eq("is_active", True) \
        .execute()

    seen = set()
    stocks = []
    for row in result.data or []:
        s = row.get("stocks")
        if s and s["id"] not in seen and s.get("is_active", True):
            seen.add(s["id"])
            stocks.append(s)
    return stocks


def _get_holiday_dates_set() -> Set[date]:
    """Load all market holiday dates for gap detection."""
    result = supabase.table("market_holidays") \
        .select("holiday_date") \
        .execute()
    holidays = set()
    for row in result.data or []:
        try:
            holidays.add(date.fromisoformat(row["holiday_date"]))
        except (ValueError, TypeError):
            pass
    return holidays


# ═══════════════════════════════════════════════════════════════════════════════
# Step 4: Fetch + Compute + Store
# ═══════════════════════════════════════════════════════════════════════════════

def _fetch_compute_and_store(
    stock: dict,
    scan_date: date,
    holiday_dates: Set[date],
    triggered_by: str,
    triggered_by_user: Optional[str],
) -> Optional[str]:
    """
    Fetch EOD data for a stock, compute all indicators and signals,
    and upsert into stock_prices.

    Returns the data source used ('yfinance', 'nse_bhavcopy', 'bse_bhavcopy')
    or None if no data available.
    """
    stock_id = stock["id"]

    # Fetch today's data with cascade
    fetch_result = fetch_stock_eod(
        supabase, stock, scan_date,
        triggered_by=triggered_by,
        triggered_by_user=triggered_by_user,
    )

    fetched_df = fetch_result["data"]
    source = fetch_result["source"]

    if fetched_df is None or fetched_df.empty:
        logger.warning(f"No data for stock {stock_id} on {scan_date}")
        return None

    # Get existing historical prices from DB to build full window
    from_date = scan_date - timedelta(days=200)
    existing_df = get_existing_prices(supabase, stock_id, from_date, scan_date - timedelta(days=1))

    # Merge: existing historical + newly fetched
    if not existing_df.empty and len(fetched_df) == 1:
        # Daily scan: we got today's row only from bhavcopy fallback
        # Need historical context for indicators
        combined_df = pd.concat([existing_df, fetched_df], ignore_index=True)
    else:
        # yfinance returned multiple days — use that directly
        combined_df = fetched_df

    combined_df = combined_df.drop_duplicates(subset=["date"], keep="last")
    combined_df = combined_df.sort_values("date").reset_index(drop=True)

    if len(combined_df) < 56:
        logger.warning(f"Insufficient data for indicators: {len(combined_df)} rows for stock {stock_id}")
        # Still store raw price data even without indicators
        _store_raw_price(stock_id, scan_date, fetched_df)
        return source

    # Compute indicators
    df = compute_indicators(combined_df, holiday_dates=holiday_dates)

    # Compute signals
    df = compute_buy_signals(df)
    df = compute_exit_signals(df)

    # Get today's row
    today_rows = df[df["date"] == scan_date]
    if today_rows.empty:
        logger.warning(f"Today's date {scan_date} not in computed data for stock {stock_id}")
        return source

    row = today_rows.iloc[-1]

    # Upsert into stock_prices
    _upsert_stock_price(stock_id, scan_date, row)

    return source


def _store_raw_price(stock_id: str, scan_date: date, df: pd.DataFrame):
    """Store raw OHLCV without indicators when insufficient history exists."""
    if df.empty:
        return
    row = df.iloc[-1]
    supabase.table("stock_prices").upsert({
        "stock_id": stock_id,
        "price_date": str(scan_date),
        "open": _safe_float(row.get("open")),
        "high": _safe_float(row.get("high")),
        "low": _safe_float(row.get("low")),
        "close": _safe_float(row.get("close")),
        "volume": _safe_int(row.get("volume")),
    }, on_conflict="stock_id,price_date").execute()


def _upsert_stock_price(stock_id: str, scan_date: date, row: pd.Series):
    """Upsert a fully computed row into stock_prices."""
    supabase.table("stock_prices").upsert({
        "stock_id": stock_id,
        "price_date": str(scan_date),
        # Raw OHLCV
        "open": _safe_float(row.get("open")),
        "high": _safe_float(row.get("high")),
        "low": _safe_float(row.get("low")),
        "close": _safe_float(row.get("close")),
        "volume": _safe_int(row.get("volume")),
        # Channel indicators
        "ch55_high": _safe_float(row.get("ch55_high")),
        "ch55_low": _safe_float(row.get("ch55_low")),
        "ch20_high": _safe_float(row.get("ch20_high")),
        "ch20_low": _safe_float(row.get("ch20_low")),
        # ADX
        "adx_20": _safe_float(row.get("adx_20")),
        "adx_rising": _safe_bool(row.get("adx_rising")),
        # Flat days
        "ch55_high_flat_days": _safe_int(row.get("ch55_high_flat_days")),
        "ch55_low_flat_days": _safe_int(row.get("ch55_low_flat_days")),
        # Signal flags
        "buy_signal": _safe_bool(row.get("buy_signal"), default=False),
        "exit_trailing_stop": _safe_bool(row.get("exit_trailing_stop"), default=False),
        "exit_adx": _safe_bool(row.get("exit_adx"), default=False),
        "exit_rejection": False,  # Set per-position below
        "any_exit_signal": _safe_bool(row.get("any_exit_signal"), default=False),
        # Indian market specifics
        "hit_upper_circuit": _safe_bool(row.get("hit_upper_circuit"), default=False),
        "hit_lower_circuit": _safe_bool(row.get("hit_lower_circuit"), default=False),
        "circuit_limit_pct": _safe_float(row.get("circuit_limit_pct")),
        # Post-holiday gaps
        "is_post_holiday": _safe_bool(row.get("is_post_holiday"), default=False),
        "gap_down_pct": _safe_float(row.get("gap_down_pct")),
        "gap_risk_warning": _safe_bool(row.get("gap_risk_warning"), default=False),
    }, on_conflict="stock_id,price_date").execute()


# ═══════════════════════════════════════════════════════════════════════════════
# Step 5: Per-Trader Signal Generation
# ═══════════════════════════════════════════════════════════════════════════════

def _get_active_traders() -> List[dict]:
    """Get all active traders (not paused, not suspended)."""
    result = supabase.table("users") \
        .select("*") \
        .eq("role", "trader") \
        .eq("status", "active") \
        .execute()
    return result.data or []


def _generate_trader_signals(trader: dict, scan_date: date) -> List[str]:
    """
    Generate BUY and EXIT signals for a specific trader.

    CRITICAL LOGIC:
    - EXIT and BUY are checked INDEPENDENTLY (not elif)
    - A stock can have both an exit and a new buy on the same day
    - ALL open positions in a stock exit simultaneously on any exit
    - Skip stocks with unconfirmed pending signals
    - Fresh BUY fires even if confirmed open positions exist

    Returns list of signal types created.
    """
    user_id = trader["id"]
    signals_created = []

    # Get trader's active watchlist
    watchlist = supabase.table("watchlists") \
        .select("stock_id, stocks(*)") \
        .eq("user_id", user_id) \
        .eq("is_active", True) \
        .execute().data or []

    # Get ALL open positions for this trader (grouped by stock)
    open_positions = supabase.table("positions") \
        .select("*") \
        .eq("user_id", user_id) \
        .eq("status", "open") \
        .execute().data or []

    # Group positions by stock_id (multiple positions per stock possible)
    positions_by_stock: Dict[str, List[dict]] = {}
    for pos in open_positions:
        sid = pos["stock_id"]
        if sid not in positions_by_stock:
            positions_by_stock[sid] = []
        positions_by_stock[sid].append(pos)

    # Get pending (unconfirmed) signals — skip stocks with pending signals
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

        # Skip if unconfirmed pending signal exists for this stock
        if stock_id in pending_stock_ids:
            logger.debug(f"Skipping {stock_id} for trader {user_id[:8]}: pending signal exists")
            continue

        # Get today's price data from stock_prices
        price_data = _get_todays_price(stock_id, scan_date)
        if not price_data:
            continue

        # ── CHECK EXIT SIGNALS ───────────────────────────────────────────
        # Check exits for ALL open positions in this stock
        if stock_id in positions_by_stock:
            stock_positions = positions_by_stock[stock_id]
            exit_type = _check_exits_for_positions(
                stock_id, stock_positions, price_data, scan_date
            )
            if exit_type:
                _create_exit_signal(
                    user_id, stock_id, scan_date, exit_type, price_data
                )
                signals_created.append(exit_type)

        # ── CHECK BUY SIGNALS ────────────────────────────────────────────
        # INDEPENDENT of exit check — buy can fire even with open positions
        # (per PRD rule #9: fresh BUY valid if confirmed open position exists)
        if price_data.get("buy_signal"):
            sizing = compute_position_size(
                available_capital=float(trader.get("available_capital", 0)),
                risk_percent=float(trader.get("risk_percent", 1.0)),
                entry_price=float(price_data["close"]),
                stop_loss=float(price_data.get("ch20_low") or price_data["close"] * 0.95),
            )
            _create_buy_signal(
                user_id, stock_id, scan_date, price_data, sizing
            )
            signals_created.append("BUY")

    return signals_created


def _get_todays_price(stock_id: str, scan_date: date) -> Optional[dict]:
    """Get today's pre-computed price data from stock_prices."""
    result = supabase.table("stock_prices") \
        .select("*") \
        .eq("stock_id", stock_id) \
        .eq("price_date", str(scan_date)) \
        .execute()
    return result.data[0] if result.data else None


def _check_exits_for_positions(
    stock_id: str,
    positions: List[dict],
    price_data: dict,
    scan_date: date,
) -> Optional[str]:
    """
    Check all exit conditions for a stock's open positions.
    ANY exit condition on ANY position triggers exit of ALL positions.

    Exit priority:
    1. Trailing Stop (most common)
    2. ADX Reversal
    3. Rejection Rule (per-position, checked for each position)
    """
    # Check trailing stop (stock-level, not per-position)
    if price_data.get("exit_trailing_stop"):
        return "EXIT_TRAILING"

    # Check ADX reversal (stock-level)
    if price_data.get("exit_adx"):
        return "EXIT_ADX"

    # Check rejection rule PER POSITION (position-specific)
    for pos in positions:
        entry_date_str = pos.get("entry_date")
        if not entry_date_str:
            continue

        entry_date = date.fromisoformat(entry_date_str) if isinstance(entry_date_str, str) else entry_date_str

        # Get ch55_high at entry from the entry signal
        ch55_at_entry = None
        if pos.get("signal_id"):
            sig_result = supabase.table("signals") \
                .select("ch55_high_at_signal") \
                .eq("id", pos["signal_id"]) \
                .execute()
            if sig_result.data:
                ch55_at_entry = sig_result.data[0].get("ch55_high_at_signal")

        # Fallback: use current ch55_high
        if ch55_at_entry is None:
            ch55_at_entry = price_data.get("ch55_high")

        if ch55_at_entry is None:
            continue

        rejection = check_rejection_rule(
            supabase, stock_id, entry_date,
            float(ch55_at_entry), scan_date
        )
        if rejection:
            return "EXIT_REJECTION"

    return None


def _create_exit_signal(
    user_id: str,
    stock_id: str,
    scan_date: date,
    exit_type: str,
    price_data: dict,
):
    """Create an EXIT signal in the signals table."""
    token = uuid.uuid4().hex
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
    logger.info(f"EXIT signal created: {exit_type} for stock={stock_id}, trader={user_id[:8]}")


def _create_buy_signal(
    user_id: str,
    stock_id: str,
    scan_date: date,
    price_data: dict,
    sizing: dict,
):
    """Create a BUY signal in the signals table."""
    token = uuid.uuid4().hex
    supabase.table("signals").insert({
        "user_id": user_id,
        "stock_id": stock_id,
        "signal_date": str(scan_date),
        "signal_type": "BUY",
        "trigger_price": price_data["close"],
        "ch55_high_at_signal": price_data.get("ch55_high"),
        "ch20_low_at_signal": price_data.get("ch20_low"),
        "adx_at_signal": price_data.get("adx_20"),
        "flat_days": price_data.get("ch55_high_flat_days"),
        "suggested_qty": sizing["qty"],
        "suggested_cost": sizing["cost"],
        "circuit_warning": price_data.get("hit_upper_circuit", False),
        "circuit_type": "UPPER" if price_data.get("hit_upper_circuit") else None,
        "notification_token": token,
    }).execute()
    logger.info(
        f"BUY signal created: stock={stock_id}, trader={user_id[:8]}, "
        f"qty={sizing['qty']}, cost=₹{sizing['cost']}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Step 6: Inactivity Tracking
# ═══════════════════════════════════════════════════════════════════════════════

def _update_inactivity(trader: dict, had_signals_today: bool, scan_date: date):
    """
    Update inactivity tracking for a trader.

    Rules:
    - Inactivity counter ONLY increments on days trader had signals to confirm
    - Counter does NOT increment on no-signal days or holidays
    - Day 5:  warning notification
    - Day 7:  auto-pause
    - Day 12: warning notification (5 days after pause)
    - Day 15: auto-suspend
    """
    user_id = trader["id"]
    current_days = trader.get("inactivity_days", 0)

    # Check if trader has ANY pending (unconfirmed) signals
    pending = supabase.table("signals") \
        .select("id") \
        .eq("user_id", user_id) \
        .is_("confirmed", "null") \
        .execute().data or []

    if not pending:
        # No pending signals — reset inactivity counter
        if current_days > 0:
            supabase.table("users").update({
                "inactivity_days": 0,
                "warned_day5": False,
                "warned_day12": False,
            }).eq("id", user_id).execute()
        return

    # Has pending signals — only increment if today was a signal day
    # (inactivity counts market days with pending signals, not all days)
    if not had_signals_today and current_days == 0:
        # First time — start counting from when signals were generated
        return

    new_days = current_days + 1
    updates = {"inactivity_days": new_days}

    if new_days == 5 and not trader.get("warned_day5"):
        updates["warned_day5"] = True
        logger.info(f"Inactivity DAY 5 warning for trader {user_id[:8]}")
        # Notification will be dispatched by notification system

    elif new_days == 7:
        updates["status"] = "paused"
        logger.warning(f"AUTO-PAUSED trader {user_id[:8]} at day 7 inactivity")

    elif new_days == 12 and not trader.get("warned_day12"):
        updates["warned_day12"] = True
        logger.info(f"Inactivity DAY 12 warning for trader {user_id[:8]}")

    elif new_days >= 15:
        updates["status"] = "suspended"
        logger.warning(f"AUTO-SUSPENDED trader {user_id[:8]} at day {new_days} inactivity")

    supabase.table("users").update(updates).eq("id", user_id).execute()


# ═══════════════════════════════════════════════════════════════════════════════
# Step 7: Notification Sessions
# ═══════════════════════════════════════════════════════════════════════════════

def _create_notification_session(trader: dict, scan_date: date, signal_count: int):
    """
    Create a notification_session for this trader for today.
    Created even on no-signal days (has_signals=False) so notifications
    can be dispatched for no-signal-day messages.
    """
    user_id = trader["id"]
    session_token = uuid.uuid4().hex

    supabase.table("notification_sessions").upsert({
        "user_id": user_id,
        "signal_date": str(scan_date),
        "session_token": session_token,
        "has_signals": signal_count > 0,
        "total_rows": signal_count,
        "actioned_rows": 0,
        "submitted": False,
        "is_active": True,
    }, on_conflict="user_id,signal_date").execute()

    logger.debug(
        f"Notification session created: trader={user_id[:8]}, "
        f"signals={signal_count}, token={session_token[:8]}..."
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Step 8: Stock Suspension Detection
# ═══════════════════════════════════════════════════════════════════════════════

def _track_missing_data(stock: dict, scan_date: date):
    """Increment missing_data_days counter when no EOD data is found."""
    stock_id = stock["id"]
    try:
        # Get current missing count
        result = supabase.table("stocks") \
            .select("missing_data_days") \
            .eq("id", stock_id) \
            .execute()
        current = result.data[0]["missing_data_days"] if result.data else 0
        supabase.table("stocks").update({
            "missing_data_days": current + 1
        }).eq("id", stock_id).execute()
    except Exception as e:
        logger.error(f"Failed to track missing data for {stock_id}: {e}")


def _check_stock_suspensions():
    """
    Check for stocks with 3+ consecutive missing data days.
    Flag them as possibly suspended/delisted.
    Send alerts to super admin and affected traders.
    """
    result = supabase.table("stocks") \
        .select("id, ticker_nse, ticker_bse, company_name, missing_data_days") \
        .eq("is_active", True) \
        .gte("missing_data_days", 3) \
        .eq("is_suspended", False) \
        .execute()

    for stock in result.data or []:
        stock_id = stock["id"]
        ticker = stock.get("ticker_nse") or stock.get("ticker_bse")
        logger.warning(f"STOCK SUSPENSION detected: {ticker} — {stock['missing_data_days']} missing days")

        # Mark as suspended
        supabase.table("stocks").update({
            "is_suspended": True,
            "suspended_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", stock_id).execute()

        # Deactivate from watchlists where no open position exists
        _deactivate_suspended_stock(stock_id)


def _deactivate_suspended_stock(stock_id: str):
    """Deactivate a suspended stock from watchlists where no open position exists."""
    # Get all watchlist entries for this stock
    watchlist_entries = supabase.table("watchlists") \
        .select("id, user_id") \
        .eq("stock_id", stock_id) \
        .eq("is_active", True) \
        .execute().data or []

    for entry in watchlist_entries:
        # Check if user has open positions in this stock
        positions = supabase.table("positions") \
            .select("id") \
            .eq("user_id", entry["user_id"]) \
            .eq("stock_id", stock_id) \
            .eq("status", "open") \
            .execute().data or []

        if not positions:
            # Safe to deactivate
            supabase.table("watchlists").update({
                "is_active": False,
                "deactivated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", entry["id"]).execute()
            logger.info(f"Deactivated suspended stock {stock_id} from watchlist for user {entry['user_id'][:8]}")


# ═══════════════════════════════════════════════════════════════════════════════
# Scan Logging
# ═══════════════════════════════════════════════════════════════════════════════

def _create_scan_log(
    scan_date: date,
    started_at: datetime,
    triggered_by: str,
    triggered_by_user: Optional[str],
) -> int:
    """Create initial scan_log entry with status 'running'."""
    result = supabase.table("scan_log").insert({
        "scan_date": str(scan_date),
        "started_at": started_at.isoformat(),
        "status": "running",
        "triggered_by": triggered_by,
        "triggered_by_user": triggered_by_user,
    }).execute()
    return result.data[0]["id"]


def _complete_scan_log(
    scan_log_id: int,
    status: str,
    source: Optional[str] = None,
    stocks_scanned: int = 0,
    signals_generated: int = 0,
    errors: Optional[str] = None,
):
    """Update scan_log entry with final status."""
    supabase.table("scan_log").update({
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "data_source": source,
        "stocks_scanned": stocks_scanned,
        "signals_generated": signals_generated,
        "errors": errors,
    }).eq("id", scan_log_id).execute()


# ═══════════════════════════════════════════════════════════════════════════════
# Admin Notifications
# ═══════════════════════════════════════════════════════════════════════════════

def _notify_admin_scan_failure(scan_date: date, error: str):
    """Notify super admin of scan failure via notification system."""
    try:
        admin = supabase.table("users") \
            .select("id") \
            .eq("role", "admin") \
            .execute().data
        if admin:
            admin_id = admin[0]["id"]
            supabase.table("notification_log").insert({
                "user_id": admin_id,
                "channel": "EMAIL",
                "notification_type": "SCAN_FAILURE",
                "subject": f"ALERT: Daily scan failed on {scan_date}",
                "body_preview": f"Scan failed with error: {error[:300]}",
                "status": "pending",
            }).execute()
    except Exception as e:
        logger.error(f"Failed to notify admin of scan failure: {e}")


def _notify_all_traders_holiday(scan_date: date, holiday_name: str):
    """Queue market holiday notifications for all active traders."""
    traders = supabase.table("users") \
        .select("id, full_name") \
        .eq("role", "trader") \
        .in_("status", ["active"]) \
        .execute().data or []

    for trader in traders:
        try:
            supabase.table("notification_log").insert({
                "user_id": trader["id"],
                "channel": "EMAIL",
                "notification_type": "MARKET_HOLIDAY",
                "subject": f"Market closed today — {holiday_name}",
                "body_preview": (
                    f"Hi {trader['full_name']}, market is closed today for "
                    f"{holiday_name}. No signals today. See you tomorrow!"
                )[:300],
                "status": "pending",
            }).execute()
        except Exception as e:
            logger.error(f"Failed to queue holiday notification for {trader['id'][:8]}: {e}")

    logger.info(f"Holiday notification queued for {len(traders)} traders: {holiday_name}")


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _safe_float(val, default=None):
    """Safely convert to float for DB insertion."""
    if val is None:
        return default
    try:
        f = float(val)
        if f != f:  # NaN check
            return default
        return f
    except (TypeError, ValueError):
        return default


def _safe_int(val, default=None):
    """Safely convert to int for DB insertion."""
    if val is None:
        return default
    try:
        f = float(val)
        if f != f:  # NaN check
            return default
        return int(f)
    except (TypeError, ValueError):
        return default


def _safe_bool(val, default=None):
    """Safely convert to bool for DB insertion."""
    if val is None:
        return default
    try:
        return bool(val)
    except (TypeError, ValueError):
        return default
