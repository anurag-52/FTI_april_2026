"""
AGENT 5 — INTEGRATIONS-ENG
whatsapp.py — MSG91 WhatsApp Business API integration

All 9 notification templates:
  DAILY_SIGNAL, NO_SIGNAL_DAY, MARKET_HOLIDAY, REMINDER,
  INACTIVITY_DAY5, INACTIVITY_DAY12, AUTO_SUSPENDED,
  SCAN_FAILURE, STOCK_SUSPENDED

Rules:
  - Only send if trader's notify_whatsapp=TRUE
  - Log every send in notification_log (provider_ref = MSG91 message ID)
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
import os

from config import FRONTEND_URL, supabase

logger = logging.getLogger(__name__)

# ── MSG91 API Configuration ──────────────────────────────────────────────────
def _get_msg91_creds():
    api_key_env = os.getenv("MSG91_API_KEY", "")
    sender_id_env = os.getenv("MSG91_SENDER_ID", "")
    try:
        res = supabase.table("system_settings").select("msg91_api_key, msg91_sender_id").eq("id", "global").maybeSingle().execute()
        if res.data:
            api_key = res.data.get("msg91_api_key") or api_key_env
            sender_id = res.data.get("msg91_sender_id") or sender_id_env
            return api_key, sender_id
    except Exception as e:
        logger.error(f"Error fetching msg91 settings: {e}")
    return api_key_env, sender_id_env
MSG91_BASE_URL = "https://api.msg91.com/api/v5/whatsapp/whatsapp-outbound-message/bulk/"

# Template slug names — must match MSG91-approved templates
TEMPLATE_SLUGS = {
    "DAILY_SIGNAL":     "fti_daily_signal",
    "NO_SIGNAL_DAY":    "fti_no_signal_day",
    "MARKET_HOLIDAY":   "fti_market_holiday",
    "REMINDER":         "fti_reminder",
    "INACTIVITY_DAY5":  "fti_inactivity_day5",
    "INACTIVITY_DAY12": "fti_inactivity_day12",
    "AUTO_SUSPENDED":   "fti_auto_suspended",
    "SCAN_FAILURE":     "fti_scan_failure",
    "STOCK_SUSPENDED":  "fti_stock_suspended",
}


# ── Core Send Function ───────────────────────────────────────────────────────

def _normalize_mobile(mobile: str) -> str:
    """Normalize to 91XXXXXXXXXX (no + prefix, India country code)."""
    clean = mobile.replace("+", "").replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if clean.startswith("0"):
        clean = clean[1:]
    if not clean.startswith("91"):
        clean = "91" + clean
    return clean


def _log_notification(
    user_id: str,
    notification_type: str,
    subject: Optional[str],
    body_preview: str,
    status: str,
    provider_ref: Optional[str] = None,
):
    """Insert a row into notification_log."""
    try:
        supabase.table("notification_log").insert({
            "user_id":           user_id,
            "channel":           "WHATSAPP",
            "notification_type": notification_type,
            "subject":           subject,
            "body_preview":      body_preview[:300] if body_preview else None,
            "status":            status,
            "provider_ref":      provider_ref,
            "sent_at":           datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:
        logger.error(f"Failed to log WhatsApp notification: {e}")


def send_whatsapp(
    mobile: str,
    template_key: str,
    variables: dict,
    user_id: Optional[str] = None,
    notification_type: str = "SYSTEM",
) -> bool:
    """
    Send a WhatsApp message via MSG91.

    Args:
        mobile: Phone number (any format, will be normalized to 91XXXXXXXXXX)
        template_key: One of the TEMPLATE_SLUGS keys (e.g. "DAILY_SIGNAL")
        variables: Template variable dict — values become ordered parameters
        user_id: Supabase user UUID for notification_log
        notification_type: Matches notification_log.notification_type enum

    Returns:
        True if sent successfully, False otherwise
    """
    api_key, sender_id = _get_msg91_creds()
    if not api_key or not sender_id:
        logger.warning("MSG91 credentials not configured — skipping WhatsApp send")
        if user_id:
            _log_notification(user_id, notification_type, None,
                              f"SKIPPED (no credentials): {template_key}", "failed")
        return False

    template_slug = TEMPLATE_SLUGS.get(template_key, template_key)
    mobile_clean = _normalize_mobile(mobile)
    params = list(variables.values())

    payload = {
        "integrated_number": sender_id,
        "content_type": "template",
        "payload": {
            "to": mobile_clean,
            "type": "template",
            "template": {
                "name": template_slug,
                "language": {"code": "en"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": str(p)} for p in params
                        ],
                    }
                ],
            },
        },
    }

    body_preview = f"{template_key}: {', '.join(str(v) for v in params)}"

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                MSG91_BASE_URL,
                json=payload,
                headers={
                    "accept": "application/json",
                    "content-type": "application/json",
                    "authkey": api_key,
                },
            )

        success = resp.status_code in (200, 201)
        resp_data = resp.json() if resp.status_code < 500 else {}
        provider_ref = resp_data.get("request_id") or resp_data.get("data", {}).get("request_id")

        if user_id:
            _log_notification(
                user_id, notification_type, template_key,
                body_preview,
                "sent" if success else "failed",
                provider_ref,
            )

        if success:
            logger.info(f"✅ WhatsApp sent → {mobile_clean} [{template_key}] ref={provider_ref}")
        else:
            logger.error(f"❌ WhatsApp failed → {mobile_clean} [{template_key}]: {resp.text}")

        return success

    except Exception as e:
        logger.error(f"MSG91 exception for {mobile_clean}: {e}")
        if user_id:
            _log_notification(user_id, notification_type, template_key,
                              f"EXCEPTION: {str(e)[:200]}", "failed")
        return False


# ── Convenience Template Senders ─────────────────────────────────────────────

def send_daily_signal(user: dict, session_token: str, buy_count: int, exit_count: int) -> bool:
    """Template 1: DAILY_SIGNAL — signals ready, includes confirmation link."""
    if not user.get("notify_whatsapp") or not user.get("mobile"):
        return False
    link = f"{FRONTEND_URL}/confirm/{session_token}"
    return send_whatsapp(
        user["mobile"], "DAILY_SIGNAL",
        {"name": user["full_name"].split()[0], "buy_count": str(buy_count),
         "exit_count": str(exit_count), "link": link},
        user["id"], "DAILY_SIGNAL",
    )


def send_no_signal_day(user: dict) -> bool:
    """Template 2: NO_SIGNAL_DAY — scan complete, no signals, no link."""
    if not user.get("notify_whatsapp") or not user.get("mobile"):
        return False
    return send_whatsapp(
        user["mobile"], "NO_SIGNAL_DAY",
        {"name": user["full_name"].split()[0]},
        user["id"], "NO_SIGNAL_DAY",
    )


def send_market_holiday(user: dict, holiday_name: str) -> bool:
    """Template 3: MARKET_HOLIDAY — market closed today."""
    if not user.get("notify_whatsapp") or not user.get("mobile"):
        return False
    return send_whatsapp(
        user["mobile"], "MARKET_HOLIDAY",
        {"name": user["full_name"].split()[0], "holiday_name": holiday_name},
        user["id"], "MARKET_HOLIDAY",
    )


def send_reminder(user: dict, session_token: str) -> bool:
    """Template 4: REMINDER — yesterday's signals still unconfirmed."""
    if not user.get("notify_whatsapp") or not user.get("mobile"):
        return False
    link = f"{FRONTEND_URL}/confirm/{session_token}"
    return send_whatsapp(
        user["mobile"], "REMINDER",
        {"name": user["full_name"].split()[0], "link": link},
        user["id"], "REMINDER",
    )


def send_inactivity_day5(user: dict, session_token: str) -> bool:
    """Template 5: INACTIVITY_DAY5 — 5 days inactive, auto-pause in 2 days."""
    if not user.get("notify_whatsapp") or not user.get("mobile"):
        return False
    link = f"{FRONTEND_URL}/confirm/{session_token}"
    return send_whatsapp(
        user["mobile"], "INACTIVITY_DAY5",
        {"name": user["full_name"].split()[0], "link": link},
        user["id"], "INACTIVITY_DAY5",
    )


def send_inactivity_day12(user: dict, session_token: str) -> bool:
    """Template 6: INACTIVITY_DAY12 — 12 days inactive, auto-suspend in 3 days."""
    if not user.get("notify_whatsapp") or not user.get("mobile"):
        return False
    link = f"{FRONTEND_URL}/confirm/{session_token}"
    return send_whatsapp(
        user["mobile"], "INACTIVITY_DAY12",
        {"name": user["full_name"].split()[0], "link": link},
        user["id"], "INACTIVITY_DAY12",
    )


def send_auto_suspended(user: dict) -> bool:
    """Template 7: AUTO_SUSPENDED — account suspended due to 15-day inactivity."""
    if not user.get("notify_whatsapp") or not user.get("mobile"):
        return False
    return send_whatsapp(
        user["mobile"], "AUTO_SUSPENDED",
        {"name": user["full_name"].split()[0],
         "admin_email": "aaanurag@yahoo.com",
         "admin_mobile": "+91 9303121500"},
        user["id"], "AUTO_SUSPENDED",
    )


def send_scan_failure(admin: dict, scan_date: str, attempt: int, source: str) -> bool:
    """Template 8: SCAN_FAILURE — Super Admin only, scan failed alert."""
    if not admin.get("notify_whatsapp") or not admin.get("mobile"):
        return False
    link = f"{FRONTEND_URL}/admin/system"
    return send_whatsapp(
        admin["mobile"], "SCAN_FAILURE",
        {"date": scan_date, "attempt": str(attempt), "max_attempts": "12",
         "source": source, "link": link},
        admin["id"], "SCAN_FAILURE",
    )


def send_stock_suspended(user: dict, stock_name: str, ticker: str) -> bool:
    """Template 9: STOCK_SUSPENDED — stock missing data for 3+ days."""
    if not user.get("notify_whatsapp") or not user.get("mobile"):
        return False
    return send_whatsapp(
        user["mobile"], "STOCK_SUSPENDED",
        {"name": user["full_name"].split()[0],
         "stock_name": stock_name, "ticker": ticker},
        user["id"], "STOCK_SUSPENDED",
    )
