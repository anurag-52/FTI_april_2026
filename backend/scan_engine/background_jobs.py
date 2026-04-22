"""
AGENT 3 — SCAN ENGINE
background_jobs.py — Heavy long-running background tasks.
"""
import logging
from datetime import date, timedelta
from typing import Optional
import json

from config import supabase
from scan_engine.indicator_engine import compute_indicators
from scan_engine.signal_engine import compute_buy_signals, compute_exit_signals

logger = logging.getLogger(__name__)


async def fetch_and_compute_historical(stock_id: str, ticker_nse: str, ticker_bse: Optional[str] = None):
    """
    1. Fetch 10 years historical data from yfinance
    2. Compute indicators using indicator_engine.compute_indicators()
    3. Compute signals using indicator_engine.compute_signals()
    4. Bulk upsert into stock_prices table
    5. Update stocks table: compute_status='complete', history_fetched=True
    6. Handle errors: set compute_status='failed' on error
    """
    logger.info(f"Starting historical fetch and compute for {stock_id} ({ticker_nse})")
    try:
        from scan_engine.data_fetcher import fetch_ohlcv_yfinance

        # Set status to running
        supabase.table("stocks").update({"compute_status": "running"}).eq("id", stock_id).execute()

        from scan_engine.data_fetcher import fetch_historical
        
        df = fetch_historical(ticker_nse, ticker_bse, years=10)
        if df is None or df.empty:
            raise ValueError("Both yfinance and NSE Bhavcopy fallback failed")

        # Compute
        df = compute_indicators(df)
        df = compute_buy_signals(df)
        df = compute_exit_signals(df)

        # Prepare for bulk upsert
        records = []
        for _, row in df.iterrows():
            def _sfloat(v):
                import math
                if v is None or math.isnan(v): return None
                return float(v)

            def _sint(v):
                import math
                if v is None or math.isnan(v): return None
                return int(v)

            records.append({
                "stock_id": stock_id,
                "price_date": str(row["date"]),
                "open": _sfloat(row.get("open")),
                "high": _sfloat(row.get("high")),
                "low": _sfloat(row.get("low")),
                "close": _sfloat(row.get("close")),
                "volume": _sint(row.get("volume")),
                "ch55_high": _sfloat(row.get("ch55_high")),
                "ch55_low": _sfloat(row.get("ch55_low")),
                "ch20_high": _sfloat(row.get("ch20_high")),
                "ch20_low": _sfloat(row.get("ch20_low")),
                "adx_20": _sfloat(row.get("adx_20")),
                "adx_rising": bool(row.get("adx_rising")) if "adx_rising" in row else None,
                "ch55_high_flat_days": _sint(row.get("ch55_high_flat_days")),
                "ch55_low_flat_days": _sint(row.get("ch55_low_flat_days")),
                "buy_signal": bool(row.get("buy_signal")) if "buy_signal" in row else False,
                "exit_trailing_stop": bool(row.get("exit_trailing_stop")) if "exit_trailing_stop" in row else False,
                "exit_adx": bool(row.get("exit_adx")) if "exit_adx" in row else False,
                "exit_rejection": False,
                "any_exit_signal": bool(row.get("any_exit_signal")) if "any_exit_signal" in row else False,
                "hit_upper_circuit": bool(row.get("hit_upper_circuit")) if "hit_upper_circuit" in row else False,
                "hit_lower_circuit": bool(row.get("hit_lower_circuit")) if "hit_lower_circuit" in row else False,
                "circuit_limit_pct": _sfloat(row.get("circuit_limit_pct")),
                "is_post_holiday": bool(row.get("is_post_holiday")) if "is_post_holiday" in row else False,
                "gap_down_pct": _sfloat(row.get("gap_down_pct")),
                "gap_risk_warning": bool(row.get("gap_risk_warning")) if "gap_risk_warning" in row else False,
            })

        # Insert in chunks of 500 to avoid payload size limits
        chunk_size = 500
        for i in range(0, len(records), chunk_size):
            chunk = records[i:i + chunk_size]
            supabase.table("stock_prices").upsert(
                chunk, 
                on_conflict="stock_id,price_date"
            ).execute()

        # Update success status
        supabase.table("stocks").update({
            "compute_status": "complete", 
            "history_fetched": True,
            "missing_data_days": 0
        }).eq("id", stock_id).execute()

        logger.info(f"Historical compute success for {stock_id}: {len(records)} days processed")

    except Exception as e:
        logger.error(f"Historical compute failed for {stock_id}: {e}")
        supabase.table("stocks").update({
            "compute_status": "failed"
        }).eq("id", stock_id).execute()
