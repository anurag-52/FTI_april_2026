"""
AGENT 3 — SCAN ENGINE
indicator_engine.py

Computes ALL technical indicators for the Courtney Smith Channel Breakout strategy.
All computations are vectorized with pandas/numpy for performance.

Input:  DataFrame with columns [date, open, high, low, close, volume]
        Optional: holiday_dates set for post-holiday/gap detection
Output: DataFrame with all indicator columns added

Indicator Columns Added:
  ch55_high, ch55_low            – 55-day channel high/low
  ch20_high, ch20_low            – 20-day channel high/low (ch20_low = trailing stop)
  adx_20, adx_rising             – ADX(20) and trend direction
  ch55_high_flat_days            – consecutive days 55-high flat/declining
  ch55_low_flat_days             – consecutive days 55-low flat/rising
  is_post_holiday                – first trading day after a market holiday
  gap_down_pct                   – gap down % from pre-holiday close
  gap_risk_warning               – is_post_holiday AND gap_down_pct > 2%
  hit_upper_circuit              – stock hit upper circuit limit
  hit_lower_circuit              – stock hit lower circuit limit
  circuit_limit_pct              – detected circuit limit percentage (5/10/20)
"""
import pandas as pd
import numpy as np
from datetime import date
from typing import Optional, Set
import logging

logger = logging.getLogger(__name__)


def compute_indicators(
    df: pd.DataFrame,
    holiday_dates: Optional[Set[date]] = None,
) -> pd.DataFrame:
    """
    Compute all indicators needed for signal generation.
    Requires at least 56 rows of OHLCV data for full channel computation.

    Args:
        df: DataFrame sorted by date ascending with columns:
            date, open, high, low, close, volume
        holiday_dates: set of market holiday dates for post-holiday detection

    Returns:
        DataFrame with all indicator columns added.
        Rows where indicators can't be computed (warmup period) will have NaN.
    """
    if df is None or df.empty:
        return df

    df = df.copy().sort_values("date").reset_index(drop=True)

    # ── 55-Day Channel Breakout ──────────────────────────────────────────────
    # ch55_high: highest HIGH over the 55 trading days PRIOR to today.
    # We compute rolling max on 55 days then shift by 1 so that
    # today's ch55_high represents the channel level to break above.
    df["_raw_ch55_high"] = df["high"].rolling(window=55, min_periods=55).max()
    df["_raw_ch55_low"] = df["low"].rolling(window=55, min_periods=55).min()

    df["ch55_high"] = df["_raw_ch55_high"].shift(1)
    df["ch55_low"] = df["_raw_ch55_low"].shift(1)

    # ── 20-Day Channel (Trailing Stop) ───────────────────────────────────────
    # ch20_low IS the trailing stop level.
    df["_raw_ch20_high"] = df["high"].rolling(window=20, min_periods=20).max()
    df["_raw_ch20_low"] = df["low"].rolling(window=20, min_periods=20).min()

    df["ch20_high"] = df["_raw_ch20_high"].shift(1)
    df["ch20_low"] = df["_raw_ch20_low"].shift(1)

    # ── ADX (20-period, Wilder's smoothing) ──────────────────────────────────
    df = _compute_adx(df, period=20)
    df["adx_rising"] = df["adx_20"] > df["adx_20"].shift(1)

    # ── 55-High Flat/Declining Days ──────────────────────────────────────────
    # Count consecutive days where the UNSHIFTED ch55_high is flat or declining.
    # This counts on the raw rolling max, so flat_days on row T tells us
    # how many days the 55-day high has been flat/declining ending at day T.
    # For the buy signal, we need yesterday's flat_days >= 5 (5 days flat BEFORE today).
    df["ch55_high_flat_days"] = _count_flat_or_declining_streak(df["_raw_ch55_high"])
    df["ch55_low_flat_days"] = _count_flat_or_rising_streak(df["_raw_ch55_low"])

    # ── Post-Holiday & Gap Risk ──────────────────────────────────────────────
    df["is_post_holiday"] = False
    df["gap_down_pct"] = np.nan

    if holiday_dates:
        _compute_post_holiday_gaps(df, holiday_dates)

    df["gap_risk_warning"] = (
        df["is_post_holiday"] &
        (df["gap_down_pct"].fillna(0) > 2.0)
    )

    # ── Circuit Detection ────────────────────────────────────────────────────
    _detect_circuits(df)

    # ── Cleanup intermediate columns ─────────────────────────────────────────
    df.drop(columns=["_raw_ch55_high", "_raw_ch55_low",
                     "_raw_ch20_high", "_raw_ch20_low"],
            inplace=True, errors="ignore")

    return df


# ═══════════════════════════════════════════════════════════════════════════════
# ADX Computation — Wilder's Smoothing Method
# ═══════════════════════════════════════════════════════════════════════════════

def _compute_adx(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """
    True ADX computation using Wilder's smoothing.
    Matches standard technical analysis implementations.
    """
    high = df["high"].values
    low = df["low"].values
    close = df["close"].values
    n = len(df)

    # True Range
    tr = np.zeros(n)
    dm_plus = np.zeros(n)
    dm_minus = np.zeros(n)

    for i in range(1, n):
        h_l = high[i] - low[i]
        h_pc = abs(high[i] - close[i - 1])
        l_pc = abs(low[i] - close[i - 1])
        tr[i] = max(h_l, h_pc, l_pc)

        up_move = high[i] - high[i - 1]
        down_move = low[i - 1] - low[i]

        dm_plus[i] = up_move if (up_move > down_move and up_move > 0) else 0.0
        dm_minus[i] = down_move if (down_move > up_move and down_move > 0) else 0.0

    # Wilder's smoothed averages (using EWM with alpha=1/period)
    alpha = 1.0 / period

    atr = pd.Series(tr).ewm(alpha=alpha, adjust=False).mean().values
    smooth_dm_plus = pd.Series(dm_plus).ewm(alpha=alpha, adjust=False).mean().values
    smooth_dm_minus = pd.Series(dm_minus).ewm(alpha=alpha, adjust=False).mean().values

    # Directional Indicators
    with np.errstate(divide="ignore", invalid="ignore"):
        di_plus = np.where(atr > 0, 100.0 * smooth_dm_plus / atr, 0.0)
        di_minus = np.where(atr > 0, 100.0 * smooth_dm_minus / atr, 0.0)

        di_sum = di_plus + di_minus
        dx = np.where(di_sum > 0, 100.0 * np.abs(di_plus - di_minus) / di_sum, 0.0)

    # ADX = smoothed DX
    adx = pd.Series(dx).ewm(alpha=alpha, adjust=False).mean().values

    df["adx_20"] = adx

    # NaN out the warmup period where ADX isn't reliable
    warmup = period * 2  # Need 2x period for ADX to stabilize
    df.loc[:warmup - 1, "adx_20"] = np.nan

    return df


# ═══════════════════════════════════════════════════════════════════════════════
# Flat/Declining Streak Counters
# ═══════════════════════════════════════════════════════════════════════════════

def _count_flat_or_declining_streak(series: pd.Series) -> pd.Series:
    """
    For each row, count how many consecutive preceding days the series
    was flat or declining (current <= previous).

    Used for ch55_high_flat_days: the 55-day high has been consolidating
    (not making new highs) for N consecutive days. A breakout after 5+
    flat days indicates genuine channel compression.
    """
    values = series.values
    result = np.zeros(len(values), dtype=int)

    for i in range(1, len(values)):
        if np.isnan(values[i]) or np.isnan(values[i - 1]):
            result[i] = 0
        elif values[i] <= values[i - 1]:
            result[i] = result[i - 1] + 1
        else:
            result[i] = 0

    return pd.Series(result, index=series.index)


def _count_flat_or_rising_streak(series: pd.Series) -> pd.Series:
    """Count consecutive days where series is flat or rising."""
    values = series.values
    result = np.zeros(len(values), dtype=int)

    for i in range(1, len(values)):
        if np.isnan(values[i]) or np.isnan(values[i - 1]):
            result[i] = 0
        elif values[i] >= values[i - 1]:
            result[i] = result[i - 1] + 1
        else:
            result[i] = 0

    return pd.Series(result, index=series.index)


# ═══════════════════════════════════════════════════════════════════════════════
# Post-Holiday & Gap Detection
# ═══════════════════════════════════════════════════════════════════════════════

def _compute_post_holiday_gaps(df: pd.DataFrame, holiday_dates: Set[date]):
    """
    Detect post-holiday trading days and compute gap percentages.

    A day is post-holiday if there is at least one market holiday
    between today's date and the previous trading day in the data.
    Gap down % = (prev_close - today_open) / prev_close * 100
    """
    dates = df["date"].values
    opens = df["open"].values
    closes = df["close"].values

    for i in range(1, len(df)):
        prev_date = dates[i - 1]
        curr_date = dates[i]

        # Check if any holiday falls between prev trading day and current
        if isinstance(prev_date, np.datetime64):
            prev_date = pd.Timestamp(prev_date).date()
        if isinstance(curr_date, np.datetime64):
            curr_date = pd.Timestamp(curr_date).date()

        # Check all calendar dates between prev_date+1 and curr_date-1
        check_date = prev_date + pd.Timedelta(days=1)
        end_check = curr_date
        has_holiday = False

        d = prev_date
        while True:
            from datetime import timedelta
            d = d + timedelta(days=1)
            if d >= curr_date:
                break
            if d in holiday_dates:
                has_holiday = True
                break

        if has_holiday:
            df.iloc[i, df.columns.get_loc("is_post_holiday")] = True
            prev_close = closes[i - 1]
            today_open = opens[i]
            if prev_close and prev_close > 0:
                gap_pct = ((prev_close - today_open) / prev_close) * 100
                df.iloc[i, df.columns.get_loc("gap_down_pct")] = round(gap_pct, 4)


# ═══════════════════════════════════════════════════════════════════════════════
# Circuit Limit Detection
# ═══════════════════════════════════════════════════════════════════════════════

def _detect_circuits(df: pd.DataFrame):
    """
    Detect upper and lower circuit hits from OHLC patterns.

    Upper circuit: stock locked at upper limit — typically:
      - high == low == close (no range, stuck at limit)
      - OR very narrow range with close > previous close by ~5/10/20%

    Lower circuit: stock locked at lower limit — typically:
      - high == low == close (no range, stuck at limit)
      - OR very narrow range with close < previous close by ~5/10/20%

    Also computes circuit_limit_pct (5, 10, or 20).
    """
    n = len(df)
    upper = np.full(n, False)
    lower = np.full(n, False)
    circuit_pct = np.full(n, np.nan)

    highs = df["high"].values
    lows = df["low"].values
    closes = df["close"].values
    opens = df["open"].values

    for i in range(1, n):
        prev_close = closes[i - 1]
        if prev_close is None or prev_close == 0 or np.isnan(prev_close):
            continue

        h, l, c, o = highs[i], lows[i], closes[i], opens[i]
        if any(np.isnan(x) for x in [h, l, c, o]):
            continue

        price_range = h - l
        pct_change = ((c - prev_close) / prev_close) * 100

        # Circuit hit if range is effectively zero or very tiny
        # (less than 0.5% of close price — locked at circuit)
        is_locked = price_range < (c * 0.005) if c > 0 else False

        if is_locked:
            if c > prev_close:
                upper[i] = True
                # Determine circuit limit percentage
                abs_pct = abs(pct_change)
                if abs_pct >= 19.0:
                    circuit_pct[i] = 20.0
                elif abs_pct >= 9.0:
                    circuit_pct[i] = 10.0
                elif abs_pct >= 4.0:
                    circuit_pct[i] = 5.0
            elif c < prev_close:
                lower[i] = True
                abs_pct = abs(pct_change)
                if abs_pct >= 19.0:
                    circuit_pct[i] = 20.0
                elif abs_pct >= 9.0:
                    circuit_pct[i] = 10.0
                elif abs_pct >= 4.0:
                    circuit_pct[i] = 5.0

    df["hit_upper_circuit"] = upper
    df["hit_lower_circuit"] = lower
    df["circuit_limit_pct"] = circuit_pct
