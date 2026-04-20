"""
AGENT 5 — INTEGRATIONS-ENG
notifications.py — Central notification dispatcher

Routes notifications to WhatsApp and/or Email per trader preferences.

Usage:
    from integrations.notifications import dispatch, dispatch_bulk

    # Single trader
    dispatch(user_id, "DAILY_SIGNAL", {"session_token": "abc123", "buy_count": 2, "exit_count": 1})

    # All active traders
    dispatch_bulk("NO_SIGNAL_DAY", {})

Supported notification_types:
    DAILY_SIGNAL, NO_SIGNAL_DAY, MARKET_HOLIDAY, REMINDER,
    INACTIVITY_DAY5, INACTIVITY_DAY12, AUTO_SUSPENDED,
    SCAN_FAILURE, STOCK_SUSPENDED
"""

import logging
from typing import Optional

from config import supabase

logger = logging.getLogger(__name__)


# ── Lazy Imports (avoid circular) ────────────────────────────────────────────

def _wa():
    from integrations import whatsapp
    return whatsapp


def _em():
    from integrations import email_resend
    return email_resend


# ── User Fetcher ─────────────────────────────────────────────────────────────

def _get_user(user_id: str) -> Optional[dict]:
    """Fetch user record from DB."""
    try:
        result = supabase.table("users") \
            .select("*") \
            .eq("id", user_id) \
            .maybe_single() \
            .execute()
        return result.data
    except Exception as e:
        logger.error(f"Failed to fetch user {user_id}: {e}")
        return None


def _get_admin() -> Optional[dict]:
    """Fetch the Super Admin user."""
    try:
        result = supabase.table("users") \
            .select("*") \
            .eq("role", "admin") \
            .limit(1) \
            .execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Failed to fetch admin: {e}")
        return None


def _get_active_traders() -> list[dict]:
    """Fetch all active traders."""
    try:
        result = supabase.table("users") \
            .select("*") \
            .eq("role", "trader") \
            .eq("status", "active") \
            .execute()
        return result.data or []
    except Exception as e:
        logger.error(f"Failed to fetch active traders: {e}")
        return []


# ── Core Dispatcher ──────────────────────────────────────────────────────────

def dispatch(
    user_id: str,
    notification_type: str,
    variables: dict,
) -> dict:
    """
    Send notification to a single user via their preferred channels.

    Args:
        user_id: Supabase user UUID
        notification_type: One of the 9 template types
        variables: Template-specific variables:
            DAILY_SIGNAL:     {session_token, buy_count, exit_count}
            NO_SIGNAL_DAY:    {}
            MARKET_HOLIDAY:   {holiday_name}
            REMINDER:         {session_token}
            INACTIVITY_DAY5:  {session_token}
            INACTIVITY_DAY12: {session_token}
            AUTO_SUSPENDED:   {}
            SCAN_FAILURE:     {scan_date, attempt, source, error_msg}
            STOCK_SUSPENDED:  {stock_name, ticker}

    Returns:
        {"whatsapp": True/False/None, "email": True/False/None}
        None means channel was skipped (user pref disabled or no contact info)
    """
    user = _get_user(user_id)
    if not user:
        logger.error(f"Cannot dispatch — user {user_id} not found")
        return {"whatsapp": None, "email": None}

    return _dispatch_to_user(user, notification_type, variables)


def _dispatch_to_user(user: dict, notification_type: str, variables: dict) -> dict:
    """Internal: dispatch to a fetched user dict."""
    wa = _wa()
    em = _em()

    result = {"whatsapp": None, "email": None}

    # ── Route by notification type ───────────────────────────────────
    try:
        if notification_type == "DAILY_SIGNAL":
            session_token = variables.get("session_token", "")
            buy_count = int(variables.get("buy_count", 0))
            exit_count = int(variables.get("exit_count", 0))
            result["whatsapp"] = wa.send_daily_signal(user, session_token, buy_count, exit_count)
            result["email"] = em.send_daily_signal(user, session_token, buy_count, exit_count)

        elif notification_type == "NO_SIGNAL_DAY":
            result["whatsapp"] = wa.send_no_signal_day(user)
            result["email"] = em.send_no_signal_day(user)

        elif notification_type == "MARKET_HOLIDAY":
            holiday_name = variables.get("holiday_name", "Market Holiday")
            result["whatsapp"] = wa.send_market_holiday(user, holiday_name)
            result["email"] = em.send_market_holiday(user, holiday_name)

        elif notification_type == "REMINDER":
            session_token = variables.get("session_token", "")
            result["whatsapp"] = wa.send_reminder(user, session_token)
            result["email"] = em.send_reminder(user, session_token)

        elif notification_type == "INACTIVITY_DAY5":
            session_token = variables.get("session_token", "")
            result["whatsapp"] = wa.send_inactivity_day5(user, session_token)
            result["email"] = em.send_inactivity_day5(user, session_token)

        elif notification_type == "INACTIVITY_DAY12":
            session_token = variables.get("session_token", "")
            result["whatsapp"] = wa.send_inactivity_day12(user, session_token)
            result["email"] = em.send_inactivity_day12(user, session_token)

        elif notification_type == "AUTO_SUSPENDED":
            result["whatsapp"] = wa.send_auto_suspended(user)
            result["email"] = em.send_auto_suspended(user)

        elif notification_type == "SCAN_FAILURE":
            # Super Admin only
            scan_date = variables.get("scan_date", "")
            attempt = int(variables.get("attempt", 1))
            source = variables.get("source", "unknown")
            error_msg = variables.get("error_msg", "")
            result["whatsapp"] = wa.send_scan_failure(user, scan_date, attempt, source)
            result["email"] = em.send_scan_failure(user, scan_date, attempt, source, error_msg)

        elif notification_type == "STOCK_SUSPENDED":
            stock_name = variables.get("stock_name", "Unknown")
            ticker = variables.get("ticker", "N/A")
            result["whatsapp"] = wa.send_stock_suspended(user, stock_name, ticker)
            result["email"] = em.send_stock_suspended(user, stock_name, ticker)

        else:
            logger.warning(f"Unknown notification_type: {notification_type}")

    except Exception as e:
        logger.error(f"Dispatch error for user {user.get('id')} type={notification_type}: {e}")

    # Log dispatch even if both channels were disabled (for audit)
    if result["whatsapp"] is None and result["email"] is None:
        if not user.get("notify_whatsapp") and not user.get("notify_email"):
            logger.info(f"Both channels disabled for user {user.get('id')} — notification logged but not sent")
            _log_skipped(user, notification_type)

    return result


def _log_skipped(user: dict, notification_type: str):
    """Log a skipped notification (both channels disabled) for audit trail."""
    try:
        supabase.table("notification_log").insert({
            "user_id":           user["id"],
            "channel":           "EMAIL",  # Log under email as default
            "notification_type": notification_type,
            "subject":           f"SKIPPED — both channels disabled",
            "body_preview":      f"User has notify_email=False, notify_whatsapp=False",
            "status":            "pending",
            "sent_at":           __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
        }).execute()
    except Exception as e:
        logger.error(f"Failed to log skipped notification: {e}")


# ── Bulk Dispatchers ─────────────────────────────────────────────────────────

def dispatch_bulk(
    notification_type: str,
    variables: dict,
    user_ids: Optional[list[str]] = None,
) -> dict:
    """
    Send notification to multiple users.

    Args:
        notification_type: Template type
        variables: Template variables (same for all users)
        user_ids: Specific user IDs, or None for all active traders

    Returns:
        {"sent": N, "failed": N, "skipped": N, "total": N}
    """
    if user_ids:
        users = []
        for uid in user_ids:
            u = _get_user(uid)
            if u:
                users.append(u)
    else:
        users = _get_active_traders()

    sent = 0
    failed = 0
    skipped = 0

    for user in users:
        result = _dispatch_to_user(user, notification_type, variables)

        wa_ok = result.get("whatsapp")
        em_ok = result.get("email")

        if wa_ok is None and em_ok is None:
            skipped += 1
        elif wa_ok is False and em_ok is False:
            failed += 1
        else:
            sent += 1

    summary = {"sent": sent, "failed": failed, "skipped": skipped, "total": len(users)}
    logger.info(f"Bulk dispatch [{notification_type}]: {summary}")
    return summary


def dispatch_admin(notification_type: str, variables: dict) -> dict:
    """Send notification to Super Admin only."""
    admin = _get_admin()
    if not admin:
        logger.error("No admin found for admin notification")
        return {"whatsapp": None, "email": None}
    return _dispatch_to_user(admin, notification_type, variables)


# ── Convenience Functions ────────────────────────────────────────────────────

def notify_daily_signals(user_id: str, session_token: str, buy_count: int, exit_count: int) -> dict:
    """Convenience: send daily signal notification."""
    return dispatch(user_id, "DAILY_SIGNAL", {
        "session_token": session_token,
        "buy_count": buy_count,
        "exit_count": exit_count,
    })


def notify_no_signal_day(user_id: str) -> dict:
    """Convenience: send no-signal-day notification."""
    return dispatch(user_id, "NO_SIGNAL_DAY", {})


def notify_market_holiday(holiday_name: str) -> dict:
    """Convenience: notify ALL active traders about market holiday."""
    return dispatch_bulk("MARKET_HOLIDAY", {"holiday_name": holiday_name})


def notify_reminder(user_id: str, session_token: str) -> dict:
    """Convenience: send confirmation reminder."""
    return dispatch(user_id, "REMINDER", {"session_token": session_token})


def notify_inactivity(user_id: str, day: int, session_token: str = "") -> dict:
    """Convenience: send inactivity warning (day 5 or day 12)."""
    if day <= 5:
        return dispatch(user_id, "INACTIVITY_DAY5", {"session_token": session_token})
    else:
        return dispatch(user_id, "INACTIVITY_DAY12", {"session_token": session_token})


def notify_auto_suspended(user_id: str) -> dict:
    """Convenience: notify trader of account suspension."""
    return dispatch(user_id, "AUTO_SUSPENDED", {})


def notify_scan_failure(scan_date: str, attempt: int, source: str, error_msg: str = "") -> dict:
    """Convenience: alert admin about scan failure."""
    return dispatch_admin("SCAN_FAILURE", {
        "scan_date": scan_date,
        "attempt": attempt,
        "source": source,
        "error_msg": error_msg,
    })


def notify_stock_suspended(user_id: str, stock_name: str, ticker: str) -> dict:
    """Convenience: alert trader about possible stock suspension."""
    return dispatch(user_id, "STOCK_SUSPENDED", {
        "stock_name": stock_name,
        "ticker": ticker,
    })
