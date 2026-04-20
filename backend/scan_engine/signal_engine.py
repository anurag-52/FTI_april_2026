"""
AGENT 3 — SCAN ENGINE
signal_engine.py

Dedicated signal computation engine. Applies Courtney Smith Channel Breakout
buy and exit rules to pre-computed indicator data.

BUY SIGNAL — All 3 must be TRUE simultaneously:
  1. ch55_high_flat_days >= 5  on the day BEFORE today (55-high was flat 5+ days)
  2. today.close > ch55_high   (breakout above the 55-day channel)
  3. adx_rising == True         (trend gaining strength)

EXIT SIGNALS — Any 1 triggers full exit of ALL positions in that stock:
  1. Rejection Rule:  no close above ch55_high_at_entry within 2 trading days
  2. Trailing Stop:   today.close < today.ch20_low
  3. ADX Reversal:    yesterday.adx >= 40 AND today.adx < yesterday.adx

Position Sizing — Courtney Smith Fixed Fractional (Chapter 7):
  Qty = (Available Capital × Risk%) ÷ (Entry Price − Stop Loss)
"""
import pandas as pd
import numpy as np
from datetime import date
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# BUY Signal Computation
# ═══════════════════════════════════════════════════════════════════════════════

def compute_buy_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute BUY signal flags on the indicator DataFrame.

    BUY fires when ALL 3 conditions are TRUE:
    1. Yesterday's ch55_high_flat_days >= 5
       (the 55-day high has been flat/declining for 5+ consecutive days
        before today — indicating channel compression)
    2. today.close > today.ch55_high
       (ch55_high is already shifted by 1 day in indicator_engine,
        so comparing close > ch55_high checks if close broke above
        yesterday's 55-day channel high)
    3. adx_rising == True
       (ADX is rising today vs yesterday — trend gaining strength)

    Args:
        df: DataFrame from compute_indicators() with all indicator columns

    Returns:
        DataFrame with 'buy_signal' column added
    """
    df = df.copy()

    # ch55_high_flat_days is counted on the UNSHIFTED raw 55-high.
    # To check "flat for 5+ days BEFORE today", we need yesterday's count.
    # Since the count already represents "days flat ending at this row",
    # and the count is on the raw (unshifted) series, we shift by 1
    # to get "how many flat days ended yesterday".
    flat_days_before_today = df["ch55_high_flat_days"].shift(1)

    condition_1_flat = flat_days_before_today >= 5
    condition_2_breakout = df["close"] > df["ch55_high"]
    condition_3_adx = df["adx_rising"] == True

    df["buy_signal"] = (
        condition_1_flat &
        condition_2_breakout &
        condition_3_adx
    ).fillna(False).astype(bool)

    # Log signal days for debugging
    signal_days = df[df["buy_signal"] == True]
    if not signal_days.empty:
        for _, row in signal_days.iterrows():
            logger.debug(
                f"BUY signal: date={row['date']}, close={row['close']:.2f}, "
                f"ch55_high={row['ch55_high']:.2f}, "
                f"flat_days_before={flat_days_before_today.loc[row.name]}, "
                f"adx={row.get('adx_20', 'N/A')}"
            )

    return df


# ═══════════════════════════════════════════════════════════════════════════════
# EXIT Signal Computation (Trailing Stop + ADX Reversal)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_exit_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute EXIT signal flags for trailing stop and ADX reversal.
    Note: Rejection rule is computed per-position separately.

    EXIT conditions:
    - Trailing Stop: today.close < today.ch20_low
    - ADX Reversal:  yesterday.adx >= 40 AND today.adx < yesterday.adx

    Args:
        df: DataFrame with indicator columns

    Returns:
        DataFrame with exit signal columns added
    """
    df = df.copy()

    # EXIT: Trailing Stop — close below 20-day channel low
    df["exit_trailing_stop"] = (
        df["close"] < df["ch20_low"]
    ).fillna(False).astype(bool)

    # EXIT: ADX Reversal — ADX turned down from a reading at or above 40
    yesterday_adx = df["adx_20"].shift(1)
    df["exit_adx"] = (
        (yesterday_adx >= 40) &
        (df["adx_20"] < yesterday_adx)
    ).fillna(False).astype(bool)

    # Rejection Rule placeholder — set per-position by scan_runner
    df["exit_rejection"] = False

    # Composite: any exit signal active
    df["any_exit_signal"] = (
        df["exit_trailing_stop"] |
        df["exit_adx"] |
        df["exit_rejection"]
    ).astype(bool)

    return df


# ═══════════════════════════════════════════════════════════════════════════════
# Rejection Rule — Per-Position Check
# ═══════════════════════════════════════════════════════════════════════════════

def check_rejection_rule(
    supabase,
    stock_id: str,
    entry_date: date,
    ch55_high_at_entry: float,
    scan_date: date,
) -> bool:
    """
    Check the Rejection Rule for a specific position:
    After entry, if the price has NOT closed above ch55_high_at_entry
    within 2 TRADING DAYS of entry → exit.

    This fires on the 2nd trading day after entry if no breakout confirmation.

    Args:
        supabase: Supabase client
        stock_id: UUID of the stock
        entry_date: date the position was opened
        ch55_high_at_entry: the 55-day channel high at time of entry
        scan_date: today's date (the day we're checking)

    Returns:
        True if rejection rule triggers (should exit), False otherwise
    """
    if ch55_high_at_entry is None or ch55_high_at_entry <= 0:
        return False

    # Get all trading days for this stock from entry_date to scan_date
    result = supabase.table("stock_prices") \
        .select("price_date, close") \
        .eq("stock_id", stock_id) \
        .gt("price_date", str(entry_date)) \
        .lte("price_date", str(scan_date)) \
        .order("price_date") \
        .execute()

    trading_days_since_entry = result.data or []

    if not trading_days_since_entry:
        return False

    # Count trading days since entry
    num_trading_days = len(trading_days_since_entry)

    # Only trigger rejection on the 2nd trading day after entry
    if num_trading_days < 2:
        return False

    # Check if ANY close since entry was above the breakout level
    any_close_above = any(
        row["close"] is not None and float(row["close"]) > ch55_high_at_entry
        for row in trading_days_since_entry
    )

    if not any_close_above and num_trading_days >= 2:
        logger.info(
            f"REJECTION RULE triggered: stock={stock_id}, "
            f"entry={entry_date}, ch55_at_entry={ch55_high_at_entry}, "
            f"trading_days={num_trading_days}"
        )
        return True

    return False


# ═══════════════════════════════════════════════════════════════════════════════
# Position Sizing — Courtney Smith Fixed Fractional
# ═══════════════════════════════════════════════════════════════════════════════

def compute_position_size(
    available_capital: float,
    risk_percent: float,
    entry_price: float,
    stop_loss: float,
) -> dict:
    """
    Courtney Smith Fixed Fractional Position Sizing (Chapter 7):
    Qty = (Available Capital × Risk%) ÷ (Entry Price − Stop Loss)

    Args:
        available_capital: trader's current available capital (₹)
        risk_percent: risk per trade (0.5% – 5.0%, default 1%)
        entry_price: the signal trigger price (today's close)
        stop_loss: the trailing stop level (ch20_low)

    Returns:
        dict with:
          qty: suggested quantity (integer, rounded down)
          cost: estimated total cost (qty × entry_price)
          risk_per_share: entry_price - stop_loss
          total_risk: risk amount in ₹
    """
    if entry_price <= 0 or stop_loss <= 0:
        return {"qty": 0, "cost": 0, "risk_per_share": 0, "total_risk": 0}

    if entry_price <= stop_loss:
        # Stop loss above entry — invalid, skip
        logger.warning(
            f"Invalid position sizing: entry={entry_price} <= stop={stop_loss}"
        )
        return {"qty": 0, "cost": 0, "risk_per_share": 0, "total_risk": 0}

    if available_capital <= 0:
        return {"qty": 0, "cost": 0, "risk_per_share": 0, "total_risk": 0}

    risk_amount = available_capital * (risk_percent / 100.0)
    risk_per_share = entry_price - stop_loss
    qty = int(risk_amount / risk_per_share)

    # Ensure we don't exceed available capital
    max_affordable = int(available_capital / entry_price)
    qty = min(qty, max_affordable)
    qty = max(qty, 0)

    cost = round(qty * entry_price, 2)

    return {
        "qty": qty,
        "cost": cost,
        "risk_per_share": round(risk_per_share, 2),
        "total_risk": round(risk_amount, 2),
    }
