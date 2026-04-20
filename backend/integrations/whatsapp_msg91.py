"""
MSG91 WhatsApp integration — stub until API key is provided.
Follows MSG91 WhatsApp Business API format.
"""
import requests
from config import MSG91_API_KEY, MSG91_SENDER_ID
from config import supabase
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

# WhatsApp template names (must match MSG91 approved templates)
TEMPLATES = {
    "DAILY_SIGNAL": "fti_daily_signal",
    "NO_SIGNAL":    "fti_no_signal",
    "HOLIDAY":      "fti_holiday",
    "INACTIVITY":   "fti_inactivity_warning",
    "PAUSED":       "fti_account_paused",
    "SUSPENDED":    "fti_account_suspended",
}


def send_whatsapp(
    mobile: str,
    template_name: str,
    variables: dict,
    user_id: str = None,
    notification_type: str = "SYSTEM"
) -> bool:
    """
    Send WhatsApp message via MSG91.
    mobile: format "919XXXXXXXXX" (country code + number, no +)
    """
    if not MSG91_API_KEY or not MSG91_SENDER_ID:
        logger.warning("MSG91 credentials not configured — skipping WhatsApp")
        return False

    # Normalize mobile (remove +, spaces, dashes)
    mobile_clean = mobile.replace("+", "").replace(" ", "").replace("-", "")
    if not mobile_clean.startswith("91"):
        mobile_clean = "91" + mobile_clean

    # Build template variables as ordered list
    params = list(variables.values())

    payload = {
        "integrated_number": MSG91_SENDER_ID,
        "content_type": "template",
        "payload": {
            "to": mobile_clean,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": "en"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": str(p)} for p in params
                        ]
                    }
                ]
            }
        }
    }

    try:
        resp = requests.post(
            "https://api.msg91.com/api/v5/whatsapp/whatsapp-outbound-message/bulk/",
            json=payload,
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "authkey": MSG91_API_KEY,
            },
            timeout=15
        )
        success = resp.status_code in [200, 201]
        provider_ref = resp.json().get("request_id") if success else None

        if user_id:
            supabase.table("notification_log").insert({
                "user_id": user_id,
                "channel": "WHATSAPP",
                "notification_type": notification_type,
                "body_preview": str(variables)[:200],
                "status": "sent" if success else "failed",
                "provider_ref": provider_ref,
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }).execute()

        if success:
            logger.info(f"WhatsApp sent to {mobile_clean}: {template_name}")
        else:
            logger.error(f"WhatsApp failed for {mobile_clean}: {resp.text}")

        return success

    except Exception as e:
        logger.error(f"MSG91 error: {e}")
        return False


# ── Convenience senders ──────────────────────────────────────────────────────

def whatsapp_daily_signals(user: dict, session_token: str, buy_count: int, exit_count: int) -> bool:
    if not user.get("mobile") or not user.get("notify_whatsapp"):
        return False

    from config import FRONTEND_URL
    link = f"{FRONTEND_URL}/confirm/{session_token}"

    return send_whatsapp(
        user["mobile"],
        TEMPLATES["DAILY_SIGNAL"],
        {
            "name": user["full_name"].split()[0],
            "buy_count": buy_count,
            "exit_count": exit_count,
            "link": link,
        },
        user["id"],
        "DAILY_SIGNAL"
    )


def whatsapp_market_holiday(user: dict, holiday_name: str) -> bool:
    if not user.get("mobile") or not user.get("notify_whatsapp"):
        return False

    return send_whatsapp(
        user["mobile"],
        TEMPLATES["HOLIDAY"],
        {"name": user["full_name"].split()[0], "holiday": holiday_name},
        user["id"],
        "MARKET_HOLIDAY"
    )
