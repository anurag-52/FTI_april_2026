"""
Internal routes: called by Render Cron Jobs only (protected by CRON_SECRET header).
These are NOT exposed to traders or admins directly.
"""
from fastapi import APIRouter, Depends, BackgroundTasks
from auth import get_cron_auth
from scan_engine.scan_runner import run_daily_scan

router = APIRouter()


@router.post("/scan/run")
async def trigger_scan(
    background_tasks: BackgroundTasks,
    _: bool = Depends(get_cron_auth)
):
    """
    Trigger the daily EOD scan.
    Called by Render Cron Job at 4:30 PM IST (11:00 UTC) Mon-Fri.
    Runs in background to return immediately to the cron scheduler.
    """
    background_tasks.add_task(run_daily_scan, "AUTO", None)
    return {"status": "scan_queued", "message": "Daily scan started in background"}


@router.post("/scan/manual")
async def trigger_manual_scan(
    background_tasks: BackgroundTasks,
    _: bool = Depends(get_cron_auth)
):
    """Manual scan trigger — admin use only via cron secret."""
    background_tasks.add_task(run_daily_scan, "ADMIN", None)
    return {"status": "scan_queued", "message": "Manual scan started"}


@router.post("/refresh-holidays")
async def refresh_holidays(_: bool = Depends(get_cron_auth)):
    """
    Refresh NSE market holiday calendar.
    Called by Render Cron Job every Monday at 8:00 AM IST.
    """
    try:
        from integrations.holiday_calendar import refresh_holiday_calendar
        result = refresh_holiday_calendar()
        return {"status": "ok", **result}
    except Exception as e:
        return {"status": "error", "message": str(e)}
