"""
AGENT 5 — INTEGRATIONS
email_resend.py

Email notifications using Resend (free tier: 3,000/month, 100/day).
https://resend.com
"""
import requests
from config import RESEND_API_KEY, RESEND_FROM_EMAIL
from config import supabase
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def send_email(to_email: str, subject: str, html_body: str, user_id: str = None, notification_type: str = "SYSTEM") -> bool:
    """
    Send email via Resend API.
    Returns True if successful, False if failed.
    """
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not configured — skipping email")
        return False

    try:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": RESEND_FROM_EMAIL,
                "to": [to_email],
                "subject": subject,
                "html": html_body,
            },
            timeout=15
        )

        success = resp.status_code in [200, 201]
        provider_ref = resp.json().get("id") if success else None

        # Log to notification_log
        if user_id:
            supabase.table("notification_log").insert({
                "user_id": user_id,
                "channel": "EMAIL",
                "notification_type": notification_type,
                "subject": subject,
                "body_preview": html_body[:200] if html_body else None,
                "status": "sent" if success else "failed",
                "provider_ref": provider_ref,
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }).execute()

        if success:
            logger.info(f"Email sent to {to_email}: {subject}")
        else:
            logger.error(f"Email failed for {to_email}: {resp.text}")

        return success

    except Exception as e:
        logger.error(f"Resend error: {e}")
        return False


# ── Email Templates ──────────────────────────────────────────────────────────

def _base_html(content: str, title: str) -> str:
    return f"""
    <!DOCTYPE html><html>
    <head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title}</title></head>
    <body style="margin:0;padding:0;background:#F8FAFC;font-family:Inter,Arial,sans-serif;">
    <div style="max-width:540px;margin:24px auto;background:#fff;border-radius:12px;border:1px solid #E2E8F0;overflow:hidden;">
      <div style="background:#0F4C81;padding:20px 24px;">
        <h1 style="color:#fff;margin:0;font-size:18px;">📊 Channel Breakout Signals</h1>
      </div>
      <div style="padding:24px">{content}</div>
      <div style="background:#F8FAFC;padding:16px 24px;border-top:1px solid #E2E8F0;font-size:12px;color:#64748B;">
        Courtney Smith Channel Breakout Trading Platform · Reply to unsubscribe
      </div>
    </div></body></html>
    """


def email_daily_signals(user: dict, session_token: str, buy_count: int, exit_count: int) -> bool:
    link = f"{__import__('config').FRONTEND_URL}/confirm/{session_token}"
    buy_section = f'<div style="color:#16A34A;font-size:24px;font-weight:bold">{buy_count} BUY Signal{"s" if buy_count != 1 else ""}</div>' if buy_count else ''
    exit_section = f'<div style="color:#DC2626;font-size:24px;font-weight:bold">{exit_count} Exit Alert{"s" if exit_count != 1 else ""}</div>' if exit_count else ''

    content = f"""
    <p style="color:#1E293B">Hello {user['full_name'].split()[0]},</p>
    <p style="color:#64748B">Today's signals are ready. Please confirm your actions before end of day.</p>
    {buy_section}{exit_section}
    <div style="margin:24px 0">
      <a href="{link}" style="background:#0F4C81;color:#fff;padding:14px 28px;border-radius:8px;text-decoration:none;font-weight:600;display:inline-block">
        ✅ Confirm My Signals →
      </a>
    </div>
    <p style="color:#64748B;font-size:13px">This link is permanent and unique to you. Do not share it.</p>
    """
    return send_email(
        user["email"],
        f"📊 {buy_count + exit_count} Signal{'s' if buy_count + exit_count != 1 else ''} Ready — Confirm Now",
        _base_html(content, "Daily Signals"),
        user["id"],
        "DAILY_SIGNAL"
    )


def email_no_signal_day(user: dict, reason: str = "No signals today") -> bool:
    content = f"""
    <p style="color:#1E293B">Hello {user['full_name'].split()[0]},</p>
    <p style="color:#64748B">{reason}</p>
    <p style="color:#64748B">The scan ran successfully — watchlisted stocks showed no new channel breakout signals today.</p>
    """
    return send_email(
        user["email"],
        "No Signals Today — All Clear",
        _base_html(content, "No Signals"),
        user["id"],
        "NO_SIGNAL_DAY"
    )


def email_market_holiday(user: dict, holiday_name: str) -> bool:
    content = f"""
    <p style="color:#1E293B">Hello {user['full_name'].split()[0]},</p>
    <p style="color:#64748B">Today ({holiday_name}) is a market holiday. No scan was run and no signals will be generated.</p>
    <p style="color:#64748B">Regular scanning resumes on the next trading day.</p>
    """
    return send_email(
        user["email"],
        f"🏖️ Market Holiday: {holiday_name}",
        _base_html(content, "Market Holiday"),
        user["id"],
        "MARKET_HOLIDAY"
    )


def email_inactivity_warning(user: dict, day: int) -> bool:
    content = f"""
    <p style="color:#1E293B">Hello {user['full_name'].split()[0]},</p>
    <div style="background:#FEF3C7;border:1px solid #D97706;border-radius:8px;padding:16px;margin:16px 0">
      <strong>⚠️ Inactivity Warning — Day {day}</strong>
      <p style="margin:8px 0 0">You have {15 - day} days remaining before account suspension.</p>
    </div>
    <p style="color:#64748B">You have unconfirmed signals. Please log in and confirm your actions.</p>
    {'<p style="color:#DC2626;font-weight:bold">Your account will be auto-paused in 2 days if no action is taken.</p>' if day == 5 else ''}
    {'<p style="color:#DC2626;font-weight:bold">Your account will be auto-suspended in 3 days if no action is taken.</p>' if day == 12 else ''}
    """
    return send_email(
        user["email"],
        f"⚠️ Action Required — Day {day} Inactivity Warning",
        _base_html(content, "Inactivity Warning"),
        user["id"],
        f"INACTIVITY_DAY{day}"
    )


def email_scan_failure(admin: dict, error_msg: str) -> bool:
    content = f"""
    <p style="color:#1E293B">Hello Admin,</p>
    <div style="background:#FEE2E2;border:1px solid #DC2626;border-radius:8px;padding:16px;margin:16px 0">
      <strong>🚨 Scan Failure</strong>
      <pre style="margin:8px 0 0;font-size:12px;color:#7F1D1D;white-space:pre-wrap">{error_msg}</pre>
    </div>
    <p style="color:#64748B">Please check the system dashboard and trigger a manual scan.</p>
    """
    return send_email(
        admin["email"],
        "🚨 URGENT: Daily Scan Failed",
        _base_html(content, "Scan Failure"),
        admin["id"],
        "SCAN_FAILURE"
    )
