"""
/data routes — Data feed status and manual re-fetch trigger
"""
from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from auth import get_current_user
from config import supabase
from datetime import date

router = APIRouter()


class RefetchRequest(BaseModel):
    source: Optional[str] = None  # yfinance | nse_bhavcopy | bse_bhavcopy


@router.get("/data/status")
async def get_data_status(user=Depends(get_current_user)):
    """Get today's scan status and data source info."""
    today = str(date.today())

    scan = supabase.table("scan_log") \
        .select("*") \
        .eq("scan_date", today) \
        .order("started_at", desc=True) \
        .limit(1) \
        .execute().data

    if scan:
        s = scan[0]
        return {
            "status": s["status"],
            "source_used": s.get("data_source"),
            "stocks_scanned": s.get("stocks_scanned"),
            "signals_generated": s.get("signals_generated"),
            "last_scan_date": s["scan_date"],
            "completed_at": s.get("completed_at"),
            "errors": s.get("errors"),
        }

    # Check if holiday
    holiday = supabase.table("market_holidays") \
        .select("holiday_name") \
        .eq("holiday_date", today) \
        .maybeSingle() \
        .execute().data

    if holiday:
        return {
            "status": "skipped_holiday",
            "source_used": None,
            "stocks_scanned": 0,
            "signals_generated": 0,
            "last_scan_date": today,
            "holiday_name": holiday["holiday_name"],
        }

    return {
        "status": "not_run",
        "source_used": None,
        "stocks_scanned": 0,
        "signals_generated": 0,
        "last_scan_date": None,
    }


@router.post("/data/refetch")
async def refetch_data(background_tasks: BackgroundTasks, user=Depends(get_current_user)):
    """
    Trader-triggered re-fetch. Limited to traders who have pending missing data.
    Full scan is only triggered by cron or admin.
    """
    from scan_engine.scan_runner import run_daily_scan

    background_tasks.add_task(
        run_daily_scan,
        "TRADER",
        user["id"]
    )
    return {"status": "queued", "message": "Re-fetch started in background"}
