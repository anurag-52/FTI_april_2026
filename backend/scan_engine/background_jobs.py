"""
AGENT 3 — SCAN ENGINE
background_jobs.py

Background computation when a new stock is added to a watchlist.
Fetches ~10 years of historical data, computes all indicators & signals,
and bulk upserts into stock_prices.

Usage:
    from scan_engine.background_jobs import fetch_and_compute_historical
    background_tasks.add_task(fetch_and_compute_historical, stock_id, ticker_nse)
"""
import logging
from datetime import date, datetime, timedelta, timezone
import math

from config import supabase
from scan_engine.data_fetcher import fetch_ohlcv_yfinance
from scan_engine.indicator_engine import compute_indicators, compute_signals

logger = logging.getLogger(__name__)

# Batch size for bulk upserts (avoid hitting Supabase payload limits)
UPSERT_BATCH_SIZE = 500


async def fetch_and_compute_historical(stock_id: str, ticker_nse: str):
    """
    Fetch 10 years of historical data for a stock, compute all indicators
    and signals, and bulk upsert into stock_prices.

    Called as a BackgroundTask when a stock is first added to any watchlist.

    Args:
        stock_id:   UUID of the stock record in stocks table
        ticker_nse: NSE ticker symbol (e.g., "RELIANCE.NS")
    """
    started_at = datetime.now(timezone.utc)
    logger.info(f"[BG] Starting historical computation for {ticker_nse} (stock_id={stock_id})")

    try:
        # Mark as computing
        supabase.table("stocks").update({
            "compute_status": "computing",
            "compute_progress": 0,
            "updated_at": started_at.isoformat(),
        }).eq("id", stock_id).execute()

        # ── Step 1: Fetch 10 years of historical data ────────────────────
        to_date = date.today()
        from_date = to_date - timedelta(days=365 * 10)

        _update_progress(stock_id, 5, "Fetching historical data...")

        df = fetch_ohlcv_yfinance(ticker_nse, from_date, to_date)

        if df is None or df.empty:
            raise ValueError(f"No historical data returned for {ticker_nse}")

        total_rows = len(df)
        logger.info(f"[BG] Fetched {total_rows} rows for {ticker_nse} ({from_date} → {to_date})")
        _update_progress(stock_id, 20, f"Fetched {total_rows} rows")

        # ── Step 2: Compute indicators ───────────────────────────────────
        _update_progress(stock_id, 25, "Computing indicators...")
        df = compute_indicators(df)
        _update_progress(stock_id, 50, "Computing signals...")

        # ── Step 3: Compute signals ──────────────────────────────────────
        df = compute_signals(df)
        _update_progress(stock_id, 60, "Preparing data for storage...")

        # ── Step 4: Bulk upsert into stock_prices ────────────────────────
        rows_to_upsert = []
        for _, row in df.iterrows():
            row_date = row.get("date")
            if row_date is None:
                continue
            # Convert date to string if needed
            if hasattr(row_date, "isoformat"):
                date_str = row_date.isoformat() if hasattr(row_date, "isoformat") else str(row_date)
            else:
                date_str = str(row_date)
            # Only keep the date part (YYYY-MM-DD)
            date_str = date_str[:10]

            record = {
                "stock_id": stock_id,
                "price_date": date_str,
                "open": _safe_float(row.get("open")),
                "high": _safe_float(row.get("high")),
                "low": _safe_float(row.get("low")),
                "close": _safe_float(row.get("close")),
                "volume": int(row.get("volume", 0)) if row.get("volume") and not _is_nan(row.get("volume")) else None,
                "ch55_high": _safe_float(row.get("ch55_high")),
                "ch55_low": _safe_float(row.get("ch55_low")),
                "ch20_high": _safe_float(row.get("ch20_high")),
                "ch20_low": _safe_float(row.get("ch20_low")),
                "adx_20": _safe_float(row.get("adx_20")),
                "adx_rising": bool(row.get("adx_rising")) if row.get("adx_rising") is not None and not _is_nan(row.get("adx_rising")) else None,
                "ch55_high_flat_days": int(row.get("ch55_high_flat_days", 0)) if not _is_nan(row.get("ch55_high_flat_days")) else 0,
                "ch55_low_flat_days": int(row.get("ch55_low_flat_days", 0)) if not _is_nan(row.get("ch55_low_flat_days")) else 0,
                "buy_signal": bool(row.get("buy_signal", False)),
                "exit_trailing_stop": bool(row.get("exit_trailing_stop", False)),
                "exit_adx": bool(row.get("exit_adx", False)),
                "exit_rejection": False,
                "any_exit_signal": bool(row.get("any_exit_signal", False)),
                "hit_upper_circuit": bool(row.get("hit_upper_circuit", False)),
                "hit_lower_circuit": bool(row.get("hit_lower_circuit", False)),
            }
            rows_to_upsert.append(record)

        # Batch upsert
        total_batches = math.ceil(len(rows_to_upsert) / UPSERT_BATCH_SIZE)
        for batch_idx in range(total_batches):
            start = batch_idx * UPSERT_BATCH_SIZE
            end = start + UPSERT_BATCH_SIZE
            batch = rows_to_upsert[start:end]

            supabase.table("stock_prices").upsert(
                batch,
                on_conflict="stock_id,price_date"
            ).execute()

            # Update progress (60% → 95%)
            progress = 60 + int(35 * (batch_idx + 1) / total_batches)
            _update_progress(stock_id, min(progress, 95), f"Stored batch {batch_idx + 1}/{total_batches}")

        # ── Step 5: Mark complete ────────────────────────────────────────
        actual_dates = df["date"].dropna()
        history_from = str(actual_dates.min())[:10] if len(actual_dates) > 0 else str(from_date)
        history_to = str(actual_dates.max())[:10] if len(actual_dates) > 0 else str(to_date)

        supabase.table("stocks").update({
            "compute_status": "complete",
            "compute_progress": 100,
            "history_fetched": True,
            "history_from_date": history_from,
            "history_to_date": history_to,
            "data_fetched_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", stock_id).execute()

        elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
        logger.info(
            f"[BG] ✅ Historical computation complete for {ticker_nse}: "
            f"{len(rows_to_upsert)} rows in {elapsed:.1f}s"
        )

    except Exception as e:
        logger.error(f"[BG] ❌ Historical computation FAILED for {ticker_nse}: {e}")
        try:
            supabase.table("stocks").update({
                "compute_status": "failed",
                "compute_progress": 0,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", stock_id).execute()
        except Exception as update_err:
            logger.error(f"[BG] Failed to update stock status to 'failed': {update_err}")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _update_progress(stock_id: str, progress: int, message: str = ""):
    """Update compute_progress on the stocks table."""
    try:
        supabase.table("stocks").update({
            "compute_progress": progress,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", stock_id).execute()
        if message:
            logger.info(f"[BG] Progress {progress}%: {message}")
    except Exception as e:
        logger.warning(f"[BG] Progress update failed: {e}")


def _safe_float(val):
    """Convert value to float, handling NaN and None."""
    if val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, 4)
    except (ValueError, TypeError):
        return None


def _is_nan(val):
    """Check if a value is NaN."""
    if val is None:
        return True
    try:
        return math.isnan(float(val))
    except (ValueError, TypeError):
        return False
