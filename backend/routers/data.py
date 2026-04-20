"""
/data routes — Data feed status and manual re-fetch trigger

Business Rules:
- Both Super Admin AND any trader can trigger manual re-fetch (applies to entire app)
- Data cascade: yfinance → NSE Bhavcopy → BSE Bhavcopy (12 retries × 15 min)
"""
from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from auth import get_current_user
from config import supabase
from datetime import date, datetime, timedelta
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class RefetchRequest(BaseModel):
    source: Optional[str] = None  # yfinance | nse_bhavcopy | bse_bhavcopy


@router.get("/data/status")
async def get_data_status(user=Depends(get_current_user)):
    """Get today's scan status, data source info, and recent fetch log."""
    today = str(date.today())

    # Get latest scan log for today
    scan = supabase.table("scan_log") \
        .select("*") \
        .eq("scan_date", today) \
        .order("started_at", desc=True) \
        .limit(1) \
        .execute().data

    # Check if today is a holiday
    holiday = supabase.table("market_holidays") \
        .select("holiday_name") \
        .eq("holiday_date", today) \
        .maybe_single() \
        .execute().data

    # Get recent data source logs (last 24 hrs)
    yesterday = str(date.today() - timedelta(days=1))
    data_logs = supabase.table("data_source_log") \
        .select("*") \
        .gte("fetch_date", yesterday) \
        .order("attempted_at", desc=True) \
        .limit(20) \
        .execute().data or []

    # Get last successful scan (any date)
    last_success = supabase.table("scan_log") \
        .select("scan_date, completed_at, data_source, stocks_scanned, signals_generated") \
        .eq("status", "completed") \
        .order("scan_date", desc=True) \
        .limit(1) \
        .execute().data

    if holiday:
        return {
            "status": "skipped_holiday",
            "holiday_name": holiday["holiday_name"],
            "source_used": None,
            "stocks_scanned": 0,
            "signals_generated": 0,
            "last_scan_date": today,
            "data_fetch_logs": data_logs,
            "last_successful_scan": last_success[0] if last_success else None,
        }

    if scan:
        s = scan[0]
        return {
            "status": s["status"],
            "source_used": s.get("data_source"),
            "stocks_scanned": s.get("stocks_scanned"),
            "signals_generated": s.get("signals_generated"),
            "last_scan_date": s["scan_date"],
            "completed_at": s.get("completed_at"),
            "retry_attempt": s.get("retry_attempt", 1),
            "errors": s.get("errors"),
            "data_fetch_logs": data_logs,
            "last_successful_scan": last_success[0] if last_success else None,
        }

    return {
        "status": "not_run",
        "source_used": None,
        "stocks_scanned": 0,
        "signals_generated": 0,
        "last_scan_date": None,
        "data_fetch_logs": data_logs,
        "last_successful_scan": last_success[0] if last_success else None,
    }


@router.post("/data/refetch")
async def refetch_data(req: RefetchRequest, background_tasks: BackgroundTasks, user=Depends(get_current_user)):
    """
    Any user (trader or admin) triggers re-fetch for the entire application.
    Runs scan in background.
    """
    from scan_engine.scan_runner import run_daily_scan

    triggered_by = "ADMIN" if user.get("role") == "admin" else "TRADER"

    background_tasks.add_task(
        run_daily_scan,
        triggered_by,
        user["id"]
    )

    logger.info(f"Data refetch triggered by {user['email']} (role={user['role']})")
    return {
        "status": "queued",
        "message": "Re-fetch started in background. Check /data/status for progress.",
        "triggered_by": user["email"],
    }
