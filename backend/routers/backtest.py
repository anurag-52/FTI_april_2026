"""
/backtest routes — Run backtests and retrieve results

Courtney Smith Channel Breakout backtesting engine.
Uses pre-computed indicator data from stock_prices table.
Up to 7 stocks, shared capital pool.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List
from auth import get_current_user
from config import supabase
from datetime import date, datetime, timezone
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class BacktestRequest(BaseModel):
    stock_ids: List[str]
    from_date: str       # YYYY-MM-DD
    to_date: str         # YYYY-MM-DD
    starting_capital: float
    position_size_type: str    # PERCENT_CAPITAL | FIXED_AMOUNT
    position_size_value: float # e.g. 10.0 = 10% of capital per trade
    risk_percent: float = 1.0


@router.post("/backtest")
async def run_backtest(req: BacktestRequest, background_tasks: BackgroundTasks, user=Depends(get_current_user)):
    """Kick off a backtest run. Returns immediately with run ID; compute in background."""
    if len(req.stock_ids) > 7:
        raise HTTPException(status_code=400, detail="Maximum 7 stocks per backtest")
    if len(req.stock_ids) < 1:
        raise HTTPException(status_code=400, detail="At least 1 stock required")
    if req.starting_capital < 10000:
        raise HTTPException(status_code=400, detail="Minimum capital ₹10,000")
    if req.position_size_type not in ("FIXED_AMOUNT", "PERCENT_CAPITAL"):
        raise HTTPException(status_code=400, detail="position_size_type must be FIXED_AMOUNT or PERCENT_CAPITAL")

    # Validate stocks exist
    stocks = supabase.table("stocks").select("id, ticker_nse, company_name") \
        .in_("id", req.stock_ids).execute().data or []
    if len(stocks) != len(req.stock_ids):
        raise HTTPException(status_code=400, detail="One or more stock IDs not found")

    run_id = str(uuid.uuid4())

    supabase.table("backtest_runs").insert({
        "id": run_id,
        "user_id": user["id"],
        "stock_ids": req.stock_ids,
        "stock_names": [s["ticker_nse"] or s["company_name"] for s in stocks],
        "from_date": req.from_date,
        "to_date": req.to_date,
        "starting_capital": req.starting_capital,
        "position_size_type": req.position_size_type,
        "position_size_value": req.position_size_value,
        "risk_percent": req.risk_percent,
    }).execute()

    background_tasks.add_task(_run_backtest_compute, run_id, req, stocks, user["id"])
    return {"id": run_id, "status": "running"}


@router.get("/backtest/{run_id}")
async def get_backtest_result(run_id: str, user=Depends(get_current_user)):
    """Get a backtest result by ID including trade log."""
    result = supabase.table("backtest_runs") \
        .select("*") \
        .eq("id", run_id) \
        .eq("user_id", user["id"]) \
        .maybe_single() \
        .execute().data

    if not result:
        raise HTTPException(status_code=404, detail="Backtest run not found")

    # If still running (no total_trades yet)
    if result.get("total_trades") is None:
        return {"id": run_id, "status": "running"}

    # Get trade log
    trades = supabase.table("backtest_trades") \
        .select("*") \
        .eq("backtest_id", run_id) \
        .order("trade_date") \
        .execute().data or []
        
    return {**result, "status": "completed", "trades": trades}

@router.get("/backtest/{run_id}/daily-log")
async def get_backtest_daily_log(run_id: str, user=Depends(get_current_user)):
    """Fetch day-by-day simulation log by merging actual trades with raw stock prices."""
    run = supabase.table("backtest_runs") \
        .select("*") \
        .eq("id", run_id) \
        .eq("user_id", user["id"]) \
        .maybe_single() \
        .execute().data
        
    if not run:
        raise HTTPException(status_code=404, detail="Backtest run not found")
        
    trades = supabase.table("backtest_trades") \
        .select("*") \
        .eq("backtest_id", run_id) \
        .execute().data or []
        
    raw_prices = supabase.table("stock_prices") \
        .select("price_date, stock_id, close, ch55_high, ch55_low, ch20_high, ch20_low, adx_20, adx_rising, ch55_high_flat_days") \
        .in_("stock_id", run["stock_ids"]) \
        .gte("price_date", run["from_date"]) \
        .lte("price_date", run["to_date"]) \
        .order("price_date") \
        .execute().data or []
        
    date_stock_map = {}
    for p in raw_prices:
        p_date = str(p["price_date"])
        s_id = p["stock_id"]
        if p_date not in date_stock_map:
            date_stock_map[p_date] = {}
        date_stock_map[p_date][s_id] = {
            "close_price": p["close"],
            "ch55_high": p["ch55_high"],
            "ch55_low": p["ch55_low"],
            "ch20_high": p["ch20_high"],
            "ch20_low": p["ch20_low"],
            "adx_value": p["adx_20"],
            "adx_rising": p["adx_rising"],
            "flat_days": p["ch55_high_flat_days"],
            "action": "HOLD",
            "pnl_percent": None
        }
        
    for t in trades:
        t_date = str(t["trade_date"])
        s_id = t["stock_id"]
        if t_date in date_stock_map and s_id in date_stock_map[t_date]:
            date_stock_map[t_date][s_id]["action"] = t["action"]
            date_stock_map[t_date][s_id]["pnl_percent"] = t.get("pnl_percent")
            
    stocks = supabase.table("stocks").select("id, ticker_nse, company_name").in_("id", run["stock_ids"]).execute().data or []
    stock_names = {s["id"]: s["ticker_nse"] or s["company_name"] for s in stocks}

    daily_log = []
    for d in sorted(date_stock_map.keys()):
        for s_id, s_data in date_stock_map[d].items():
            daily_log.append({
                "date": d,
                "stock": stock_names.get(s_id, "Unknown"),
                **s_data
            })
            
    return daily_log


@router.get("/backtest")
async def list_backtests(user=Depends(get_current_user)):
    """List user's backtest runs."""
    result = supabase.table("backtest_runs") \
        .select("id, stock_names, from_date, to_date, starting_capital, total_trades, win_rate_percent, total_return_percent, final_capital, created_at") \
        .eq("user_id", user["id"]) \
        .order("created_at", desc=True) \
        .limit(20) \
        .execute()
    return result.data or []


# ─── Background backtest compute engine ──────────────────────────────────────

def _run_backtest_compute(run_id: str, req: BacktestRequest, stocks: list, user_id: str):
    """
    Run the full Courtney Smith Channel Breakout backtest on historical data.
    Uses pre-computed indicator data from stock_prices table.
    Shared capital pool across all stocks.
    """
    try:
        _run_backtest_inner(run_id, req, stocks, user_id)
    except Exception as e:
        logger.error(f"Backtest {run_id} failed: {e}")
        supabase.table("backtest_runs").update({
            "total_trades": 0,
            "equity_curve": [{"date": req.from_date, "capital": req.starting_capital, "error": str(e)}],
        }).eq("id", run_id).execute()


def _run_backtest_inner(run_id: str, req: BacktestRequest, stocks: list, user_id: str):
    """Core backtest simulation logic."""
    from scan_engine.indicator_engine import compute_indicators, compute_signals
    import pandas as pd

    capital = req.starting_capital
    equity_curve = [{"date": req.from_date, "capital": capital}]
    all_trades = []

    total_trades = 0
    winning = 0
    losing = 0
    profits = []
    losses = []
    max_dd = 0
    peak = capital

    # Track open positions per stock (list for multiple positions)
    open_positions = {}  # stock_id -> list of {entry_price, entry_date, qty, ch55_high}

    for stock in stocks:
        stock_id = stock["id"]
        ticker = stock["ticker_nse"]

        # Fetch historical price data from DB
        prices = supabase.table("stock_prices") \
            .select("price_date, open, high, low, close, volume, ch55_high, ch55_low, ch20_high, ch20_low, adx_20, adx_rising, ch55_high_flat_days, buy_signal, exit_rejection, exit_trailing_stop, exit_adx, any_exit_signal") \
            .eq("stock_id", stock_id) \
            .gte("price_date", req.from_date) \
            .lte("price_date", req.to_date) \
            .order("price_date") \
            .execute().data or []

        if len(prices) < 56:
            # Not enough history in DB — try yfinance
            try:
                from scan_engine.data_fetcher import fetch_ohlcv_yfinance
                from datetime import timedelta
                from_d = date.fromisoformat(req.from_date) - timedelta(days=120)
                to_d = date.fromisoformat(req.to_date)
                raw = fetch_ohlcv_yfinance(ticker, from_d, to_d)
                if raw is not None and not raw.empty:
                    raw = compute_indicators(raw)
                    raw = compute_signals(raw)
                    prices = raw[raw["date"].astype(str) >= req.from_date].to_dict("records")
            except Exception as e:
                logger.warning(f"Backtest yfinance fallback failed for {ticker}: {e}")
                continue

        # Simulate trades
        in_position = False
        entry_price = 0
        entry_date = None
        entry_ch55_high = 0
        qty = 0

        for row in prices:
            row_date = str(row.get("price_date") or row.get("date", ""))
            close = float(row.get("close", 0) or 0)
            ch20_low = float(row.get("ch20_low") or 0) if row.get("ch20_low") else 0

            if not in_position:
                # Check BUY signal
                buy = row.get("buy_signal", False)
                if buy and close > 0:
                    # Position sizing
                    if req.position_size_type == "PERCENT_CAPITAL":
                        alloc = capital * (req.position_size_value / 100)
                    else:
                        alloc = req.position_size_value

                    if alloc > capital or alloc <= 0:
                        # Log skipped trade
                        all_trades.append({
                            "backtest_id": run_id,
                            "stock_id": stock_id,
                            "trade_date": row_date,
                            "close_price": close,
                            "ch55_high": row.get("ch55_high"),
                            "ch20_low": row.get("ch20_low"),
                            "adx_value": row.get("adx_20"),
                            "buy_signal": True,
                            "action": "SKIPPED_CAPITAL",
                            "capital_after": round(capital, 2),
                        })
                    else:
                        entry_price = close
                        entry_date = row_date
                        entry_ch55_high = float(row.get("ch55_high") or close)
                        qty = int(alloc / close)
                        if qty > 0:
                            capital -= qty * close
                            in_position = True

                            # Store BUY trade
                            all_trades.append({
                                "backtest_id": run_id,
                                "stock_id": stock_id,
                                "trade_date": row_date,
                                "close_price": close,
                                "ch55_high": row.get("ch55_high"),
                                "ch20_low": row.get("ch20_low"),
                                "adx_value": row.get("adx_20"),
                                "adx_rising": row.get("adx_rising"),
                                "flat_days": row.get("ch55_high_flat_days"),
                                "buy_signal": True,
                                "action": "BUY",
                                "entry_price": close,
                                "quantity": qty,
                                "capital_after": round(capital, 2),
                            })
            else:
                # Check EXIT signals
                exit_triggered = False
                exit_reason = None

                # Trailing stop
                if row.get("exit_trailing_stop") or (ch20_low and close < ch20_low):
                    exit_triggered = True
                    exit_reason = "TRAILING_STOP"
                # ADX exit
                elif row.get("exit_adx"):
                    exit_triggered = True
                    exit_reason = "ADX_EXIT"

                # Rejection rule (day 2 from entry — no close above entry ch55_high)
                if entry_date and not exit_triggered:
                    try:
                        days_held = (date.fromisoformat(row_date) - date.fromisoformat(entry_date)).days
                        if days_held >= 2 and close <= entry_ch55_high:
                            exit_triggered = True
                            exit_reason = "REJECTION_RULE"
                    except ValueError:
                        pass

                if exit_triggered:
                    exit_value = qty * close
                    pnl = exit_value - (qty * entry_price)
                    pnl_pct = (pnl / (qty * entry_price) * 100) if entry_price else 0
                    days = 0
                    try:
                        days = (date.fromisoformat(row_date) - date.fromisoformat(entry_date)).days
                    except ValueError:
                        pass

                    capital += exit_value
                    total_trades += 1
                    if pnl > 0:
                        winning += 1
                        profits.append(pnl_pct)
                    else:
                        losing += 1
                        losses.append(pnl_pct)

                    # Track drawdown
                    if capital > peak:
                        peak = capital
                    dd = ((peak - capital) / peak * 100) if peak else 0
                    if dd > max_dd:
                        max_dd = dd

                    all_trades.append({
                        "backtest_id": run_id,
                        "stock_id": stock_id,
                        "trade_date": row_date,
                        "close_price": close,
                        "ch55_high": row.get("ch55_high"),
                        "ch20_low": row.get("ch20_low"),
                        "adx_value": row.get("adx_20"),
                        "action": "SELL",
                        "entry_price": entry_price,
                        "exit_price": close,
                        "quantity": qty,
                        "exit_reason": exit_reason,
                        "pnl_amount": round(pnl, 2),
                        "pnl_percent": round(pnl_pct, 4),
                        "days_held": days,
                        "capital_after": round(capital, 2),
                    })

                    in_position = False

            # Update equity curve at intervals
            if row_date[-2:] in ["01", "15"]:
                equity_curve.append({"date": row_date, "capital": round(capital, 2)})

    # Final equity curve point
    equity_curve.append({"date": req.to_date, "capital": round(capital, 2)})

    # Compute summary metrics
    win_rate = (winning / total_trades * 100) if total_trades else 0
    avg_profit = (sum(profits) / len(profits)) if profits else 0
    avg_loss = (sum(losses) / len(losses)) if losses else 0
    total_return = ((capital - req.starting_capital) / req.starting_capital * 100) if req.starting_capital else 0

    # Update backtest_runs
    supabase.table("backtest_runs").update({
        "total_trades": total_trades,
        "winning_trades": winning,
        "losing_trades": losing,
        "win_rate_percent": round(win_rate, 4),
        "avg_profit_percent": round(avg_profit, 4),
        "avg_loss_percent": round(avg_loss, 4),
        "max_drawdown_percent": round(max_dd, 4),
        "final_capital": round(capital, 2),
        "total_return_percent": round(total_return, 4),
        "equity_curve": equity_curve,
    }).eq("id", run_id).execute()

    # Store trade records (batch insert)
    if all_trades:
        # Insert in batches of 100 to avoid payload limits
        for i in range(0, len(all_trades), 100):
            batch = all_trades[i:i+100]
            supabase.table("backtest_trades").insert(batch).execute()

    logger.info(f"Backtest {run_id} complete: {total_trades} trades, {win_rate:.1f}% win rate, {total_return:.1f}% return")
