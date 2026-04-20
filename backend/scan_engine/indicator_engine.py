"""
AGENT 3 — SCAN ENGINE
indicator_engine.py

Computes all technical indicators for the Courtney Smith Channel Breakout strategy.
Input: pandas DataFrame with columns [open, high, low, close, volume, date]
Output: DataFrame with all indicator columns added
"""
import pandas as pd
import numpy as np


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute all indicators needed for signal generation.
    Requires at least 55 rows of OHLCV data for full computation.
    
    Args:
        df: DataFrame sorted by date ascending, with columns: date, open, high, low, close, volume
    
    Returns:
        DataFrame with additional indicator columns
    """
    df = df.copy().sort_values("date").reset_index(drop=True)

    # ── 55-day Channel Breakout ──────────────────────────────────────────────
    # ch55_high: rolling max of HIGH over 55 days (exclude today → shift 1)
    # We use shift(1) so today's breakout is against yesterday's 55-day high
    df["ch55_high"] = df["high"].rolling(window=55, min_periods=55).max().shift(1)
    df["ch55_low"]  = df["low"].rolling(window=55,  min_periods=55).min().shift(1)

    # ── 20-day Channel (Trailing Stop) ───────────────────────────────────────
    df["ch20_high"] = df["high"].rolling(window=20, min_periods=20).max().shift(1)
    df["ch20_low"]  = df["low"].rolling(window=20,  min_periods=20).min().shift(1)

    # ── ADX (20-period) ──────────────────────────────────────────────────────
    df = _compute_adx(df, period=20)
    df["adx_rising"] = df["adx_20"] > df["adx_20"].shift(1)

    # ── 55-High Flat/Declining Days ──────────────────────────────────────────
    # Count consecutive days where ch55_high is flat or declining
    df["ch55_high_flat_days"] = _count_flat_or_declining_streak(df["ch55_high"])
    df["ch55_low_flat_days"]  = _count_flat_or_rising_streak(df["ch55_low"])

    # ── Post-Holiday & Gap Risk ──────────────────────────────────────────────
    # These are injected by scan_runner based on market_holidays table
    if "is_post_holiday" not in df.columns:
        df["is_post_holiday"] = False
    if "gap_down_pct" not in df.columns:
        df["gap_down_pct"] = None

    # gap_risk_warning: post-holiday AND gap > 2%
    df["gap_risk_warning"] = (
        df["is_post_holiday"] &
        df["gap_down_pct"].fillna(0).abs() > 2.0
    )

    # ── Circuit Detection ────────────────────────────────────────────────────
    # Upper circuit: open == high == close (no downward movement)
    df["hit_upper_circuit"] = (
        (df["high"] == df["low"]) &
        (df["close"] == df["open"]) &
        (df["close"] > df["close"].shift(1))
    )
    # Lower circuit: open == high == close (no upward movement)
    df["hit_lower_circuit"] = (
        (df["high"] == df["low"]) &
        (df["close"] == df["open"]) &
        (df["close"] < df["close"].shift(1))
    )

    return df


def compute_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute BUY and EXIT signal flags.
    Must be called AFTER compute_indicators.
    
    BUY SIGNAL (all 3 must be TRUE):
    1. ch55_high_flat_days >= 5 (55-day high flat/declining for 5+ days BEFORE today)
    2. today.close > prev_day.ch55_high (price breaks out above 55-day channel)
    3. adx_rising == True (ADX is rising today vs yesterday)
    
    EXIT SIGNALS (any 1 triggers):
    - Rejection Rule: no close above ch55_high within 2 days of entry
    - Trailing Stop: close < ch20_low
    - ADX Reversal: yesterday adx >= 40 AND today adx < yesterday
    """
    df = df.copy()

    # BUY signal
    df["buy_signal"] = (
        (df["ch55_high_flat_days"] >= 5) &
        (df["close"] > df["ch55_high"]) &
        (df["adx_rising"] == True)
    ).fillna(False)

    # EXIT: Trailing Stop
    df["exit_trailing_stop"] = (
        df["close"] < df["ch20_low"]
    ).fillna(False)

    # EXIT: ADX Reversal (ADX turned down from 40+)
    df["exit_adx"] = (
        (df["adx_20"].shift(1) >= 40) &
        (df["adx_20"] < df["adx_20"].shift(1))
    ).fillna(False)

    # EXIT: Rejection Rule — handled per position in scan_runner
    # (requires knowing entry date + entry ch55_high)
    df["exit_rejection"] = False  # Set per-position by scan_runner

    # Any exit
    df["any_exit_signal"] = (
        df["exit_trailing_stop"] | df["exit_adx"] | df["exit_rejection"]
    )

    return df


# ─── Internal helpers ────────────────────────────────────────────────────────

def _compute_adx(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """True Strength ADX computation using Wilder's smoothing."""
    high  = df["high"]
    low   = df["low"]
    close = df["close"]

    # True Range
    df["tr"] = np.maximum(
        high - low,
        np.maximum(abs(high - close.shift(1)), abs(low - close.shift(1)))
    )

    # Directional Movement
    df["dm_plus"]  = np.where((high - high.shift(1)) > (low.shift(1) - low),
                              np.maximum(high - high.shift(1), 0), 0)
    df["dm_minus"] = np.where((low.shift(1) - low) > (high - high.shift(1)),
                              np.maximum(low.shift(1) - low, 0), 0)

    # Wilder's smoothing
    df["atr"]       = df["tr"].ewm(alpha=1/period, adjust=False).mean()
    df["di_plus"]   = 100 * df["dm_plus"].ewm(alpha=1/period, adjust=False).mean()  / df["atr"]
    df["di_minus"]  = 100 * df["dm_minus"].ewm(alpha=1/period, adjust=False).mean() / df["atr"]

    # DX and ADX
    dx = 100 * abs(df["di_plus"] - df["di_minus"]) / (df["di_plus"] + df["di_minus"]).replace(0, np.nan)
    df["adx_20"] = dx.ewm(alpha=1/period, adjust=False).mean()

    # Clean up intermediary columns
    df.drop(columns=["tr", "dm_plus", "dm_minus", "atr", "di_plus", "di_minus"], inplace=True)

    return df


def _count_flat_or_declining_streak(series: pd.Series) -> pd.Series:
    """
    For each row, count how many consecutive preceding days the series
    was flat or declining (current <= previous).
    Used for ch55_high_flat_days: breakout is valid if 55H has been
    flat/declining for 5+ consecutive days before today.
    """
    result = pd.Series(0, index=series.index)
    for i in range(1, len(series)):
        if pd.isna(series.iloc[i]) or pd.isna(series.iloc[i - 1]):
            result.iloc[i] = 0
        elif series.iloc[i] <= series.iloc[i - 1]:
            result.iloc[i] = result.iloc[i - 1] + 1
        else:
            result.iloc[i] = 0
    return result


def _count_flat_or_rising_streak(series: pd.Series) -> pd.Series:
    """Count consecutive days where series is flat or rising."""
    result = pd.Series(0, index=series.index)
    for i in range(1, len(series)):
        if pd.isna(series.iloc[i]) or pd.isna(series.iloc[i - 1]):
            result.iloc[i] = 0
        elif series.iloc[i] >= series.iloc[i - 1]:
            result.iloc[i] = result.iloc[i - 1] + 1
        else:
            result.iloc[i] = 0
    return result
