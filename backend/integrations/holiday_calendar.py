"""
Holiday calendar — fetches NSE market holidays and loads them into the DB.
Runs every Monday via Render cron job.
"""
import requests
from datetime import date, datetime, timezone
from config import supabase
import logging

logger = logging.getLogger(__name__)

# Known 2025-2026 NSE holidays (hardcoded fallback)
KNOWN_HOLIDAYS = [
    ("2025-01-26", "Republic Day"),
    ("2025-02-26", "Mahashivratri"),
    ("2025-03-14", "Holi"),
    ("2025-04-10", "Shri Ram Navami"),
    ("2025-04-14", "Dr. Baba Saheb Ambedkar Jayanti"),
    ("2025-04-18", "Good Friday"),
    ("2025-05-01", "Maharashtra Day"),
    ("2025-08-15", "Independence Day"),
    ("2025-08-27", "Ganesh Chaturthi"),
    ("2025-10-02", "Gandhi Jayanti"),
    ("2025-10-02", "Mahatma Gandhi Jayanti"),
    ("2025-10-21", "Diwali Laxmi Pujan"),
    ("2025-10-22", "Diwali Balipratipada"),
    ("2025-11-05", "Prakash Gurpurb"),
    ("2025-11-15", "Gurunanak Jayanti"),
    ("2025-12-25", "Christmas"),
    ("2026-01-26", "Republic Day"),
    ("2026-03-20", "Holi"),
    ("2026-04-03", "Good Friday"),
    ("2026-04-14", "Dr. Baba Saheb Ambedkar Jayanti"),
    ("2026-04-30", "Shri Ram Navami"),
    ("2026-05-01", "Maharashtra Day"),
    ("2026-08-15", "Independence Day"),
    ("2026-10-02", "Gandhi Jayanti"),
    ("2026-10-19", "Diwali"),
    ("2026-11-24", "Gurunanak Jayanti"),
    ("2026-12-25", "Christmas"),
]


def refresh_holiday_calendar() -> dict:
    """
    Sync holidays to DB. Uses hardcoded list as primary source.
    Could be extended to scrape NSE website.
    """
    inserted = 0
    skipped = 0

    for holiday_date, holiday_name in KNOWN_HOLIDAYS:
        try:
            supabase.table("market_holidays").upsert({
                "holiday_date": holiday_date,
                "holiday_name": holiday_name,
                "exchange": "BOTH",
                "source": "AUTO",
            }, on_conflict="holiday_date").execute()
            inserted += 1
        except Exception as e:
            logger.warning(f"Skipping holiday {holiday_date}: {e}")
            skipped += 1

    logger.info(f"Holiday calendar refreshed: {inserted} upserted, {skipped} skipped")
    return {"inserted": inserted, "skipped": skipped, "total": len(KNOWN_HOLIDAYS)}


def is_trading_day(check_date: date = None) -> bool:
    """Return True if the given date (default today) is a trading day."""
    if check_date is None:
        check_date = date.today()

    # Weekend check
    if check_date.weekday() >= 5:  # Saturday=5, Sunday=6
        return False

    # Holiday check
    result = supabase.table("market_holidays") \
        .select("holiday_name") \
        .eq("holiday_date", str(check_date)) \
        .maybe_single() \
        .execute()

    return result.data is None  # True if NOT a holiday
