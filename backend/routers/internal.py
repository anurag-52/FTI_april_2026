"""
Internal routes: called by Render Cron Jobs only (protected by CRON_SECRET header).
These are NOT exposed to traders or admins directly.

Endpoints:
- POST /scan/run — Daily EOD scan (4:30 PM IST)
- POST /scan/manual — Admin manual trigger
- POST /refresh-holidays — Weekly holiday calendar refresh (Monday 8 AM IST)
"""
from fastapi import APIRouter, Depends, BackgroundTasks
from auth import get_cron_auth
import logging

logger = logging.getLogger(__name__)
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
    from scan_engine.scan_runner import run_daily_scan

    try:
        background_tasks.add_task(run_daily_scan, "AUTO", None)
        logger.info("Daily scan triggered by cron")
        return {"status": "scan_queued", "message": "Daily scan started in background"}
    except Exception as e:
        logger.error(f"Failed to queue scan: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/scan/manual")
async def trigger_manual_scan(
    background_tasks: BackgroundTasks,
    _: bool = Depends(get_cron_auth)
):
    """Manual scan trigger — admin use only via cron secret."""
    from scan_engine.scan_runner import run_daily_scan

    try:
        background_tasks.add_task(run_daily_scan, "ADMIN", None)
        logger.info("Manual scan triggered")
        return {"status": "scan_queued", "message": "Manual scan started"}
    except Exception as e:
        logger.error(f"Failed to queue manual scan: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/refresh-holidays")
async def refresh_holidays(_: bool = Depends(get_cron_auth)):
    """
    Refresh NSE market holiday calendar.
    Called by Render Cron Job every Monday at 8:00 AM IST.
    """
    try:
        from integrations.holiday_calendar import refresh_holiday_calendar
        result = refresh_holiday_calendar()
        logger.info(f"Holiday calendar refreshed: {result}")
        return {"status": "ok", **result}
    except Exception as e:
        logger.error(f"Holiday refresh failed: {e}")
        return {"status": "error", "message": str(e)}
