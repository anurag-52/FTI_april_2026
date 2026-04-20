"""
/backtest routes — Run backtests and retrieve results
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from auth import get_current_user
from config import supabase
from datetime import date, datetime, timezone

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
    if req.starting_capital < 10000:
        raise HTTPException(status_code=400, detail="Minimum capital ₹10,000")

    # Validate stocks exist
    stocks = supabase.table("stocks").select("id, ticker_nse, company_name") \
        .in_("id", req.stock_ids).execute().data or []
    if len(stocks) != len(req.stock_ids):
        raise HTTPException(status_code=400, detail="One or more stock IDs not found")

    run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    supabase.table("backtest_runs").insert({
        "id": run_id,
        "user_id": user["id"],
        "stock_ids": req.stock_ids,
        "stock_names": [s["ticker_nse"] for s in stocks],
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
    """Get a backtest result by ID."""
    result = supabase.table("backtest_runs") \
        .select("*") \
        .eq("id", run_id) \
        .eq("user_id", user["id"]) \
        .maybeSingle() \
        .execute().data

    if not result:
        raise HTTPException(status_code=404, detail="Backtest run not found")

    # If still has no trades count, it's still running
    if result.get("total_trades") is None:
        return {"id": run_id, "status": "running"}

    return {**result, "status": "completed"}


@router.get("/backtest")
async def list_backtests(user=Depends(get_current_user)):
    """List user's backtest runs."""
    result = supabase.table("backtest_runs") \
        .select("id, stock_names, from_date, to_date, starting_capital, total_trades, win_rate_percent, total_return_percent, created_at") \
        .eq("user_id", user["id"]) \
        .order("created_at", desc=True) \
        .limit(10) \
        .execute()
    return result.data or []


# ─── Background backtest compute engine ──────────────────────────────────────

def _run_backtest_compute(run_id: str, req: BacktestRequest, stocks: list, user_id: str):
    """
    Run the full Courtney Smith Channel Breakout backtest on historical data.
    Uses pre-computed indicator data from stock_prices table.
    """
    from scan_engine.indicator_engine import compute_indicators, compute_signals
    import pandas as pd
    import json

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

    for stock in stocks:
        stock_id = stock["id"]
        ticker = stock["ticker_nse"]

        # Fetch historical price data from DB
        prices = supabase.table("stock_prices") \
            .select("price_date, open, high, low, close, volume, ch55_high, ch55_low, ch20_high, ch20_low, adx_20, adx_rising, ch55_high_flat_days, buy_signal, exit_trailing_stop, exit_adx") \
            .eq("stock_id", stock_id) \
            .gte("price_date", req.from_date) \
            .lte("price_date", req.to_date) \
            .order("price_date") \
            .execute().data or []

        if len(prices) < 56:
            # Not enough history — fetch and compute from yfinance
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
            except Exception:
                continue

        # Simulate trades
        in_position = False
        entry_price = 0
        entry_date = None
        entry_ch55_high = 0
        qty = 0

        for row in prices:
            row_date = str(row.get("price_date") or row.get("date", ""))
            close = row.get("close", 0) or 0
            ch20_low = row.get("ch20_low") or 0

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
                        action = "SKIPPED_CAPITAL"
                    else:
                        entry_price = close
                        entry_date = row_date
                        entry_ch55_high = row.get("ch55_high") or close
                        qty = int(alloc / close)
                        if qty > 0:
                            capital -= qty * close
                            in_position = True
                            action = "BUY"
                        else:
                            action = "SKIPPED_CAPITAL"
                else:
                    action = "HOLD"
            else:
                # Check EXIT signals
                exit_triggered = False
                exit_reason = None

                if row.get("exit_trailing_stop") and ch20_low and close < ch20_low:
                    exit_triggered = True
                    exit_reason = "TRAILING_STOP"
                elif row.get("exit_adx"):
                    exit_triggered = True
                    exit_reason = "ADX_EXIT"

                # Rejection rule (days 1-2 from entry)
                if entry_date and not exit_triggered:
                    days_held = (date.fromisoformat(row_date) - date.fromisoformat(entry_date)).days
                    if days_held == 2 and close <= entry_ch55_high:
                        exit_triggered = True
                        exit_reason = "REJECTION_RULE"

                if exit_triggered:
                    exit_value = qty * close
                    pnl = exit_value - (qty * entry_price)
                    pnl_pct = (pnl / (qty * entry_price) * 100) if entry_price else 0
                    days = (date.fromisoformat(row_date) - date.fromisoformat(entry_date)).days

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
                        "action": "SELL",
                        "entry_price": entry_price,
                        "exit_price": close,
                        "quantity": qty,
                        "exit_reason": exit_reason,
                        "pnl_amount": round(pnl, 2),
                        "pnl_percent": round(pnl_pct, 4),
                        "days_held": days,
                        "capital_after": round(capital, 2)
                    })

                    in_position = False
                    action = "SELL"
                else:
                    action = "HOLD"

            # Update equity curve monthly
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

    # Store trade records
    if all_trades:
        supabase.table("backtest_trades").insert(all_trades).execute()
