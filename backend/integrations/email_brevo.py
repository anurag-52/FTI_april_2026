"""
AGENT 5 — INTEGRATIONS-ENG
email_brevo.py — Brevo (Sendinblue) transactional email API

All 9 notification templates as HTML emails:
  DAILY_SIGNAL, NO_SIGNAL_DAY, MARKET_HOLIDAY, REMINDER,
  INACTIVITY_DAY5, INACTIVITY_DAY12, AUTO_SUSPENDED,
  SCAN_FAILURE, STOCK_SUSPENDED

Rules:
  - Only send if trader's notify_email=TRUE
  - Respect 300 emails/day free tier (tracked in-memory + DB fallback)
  - Log every send in notification_log (provider_ref = Brevo messageId)
"""

import logging
from datetime import datetime, date, timezone
from typing import Optional

import httpx

from config import supabase, FRONTEND_URL

logger = logging.getLogger(__name__)

# ── Brevo Configuration ──────────────────────────────────────────────────────
# Read from environment via config.py — we add these to config if missing
import os

BREVO_API_KEY: str = os.getenv("BREVO_API_KEY", "")
BREVO_SENDER_NAME: str = os.getenv("BREVO_SENDER_NAME", "Channel Breakout Signals")
BREVO_SENDER_EMAIL: str = os.getenv("BREVO_SENDER_EMAIL", "signals@yourdomain.com")

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
DAILY_LIMIT = 300  # Brevo free tier

# In-memory daily counter (resets on dyno restart — also checked via DB)
_daily_send_count = 0
_daily_send_date: Optional[date] = None


# ── Rate Limiting ────────────────────────────────────────────────────────────

def _check_daily_limit() -> bool:
    """Return True if under the 300/day Brevo free-tier limit."""
    global _daily_send_count, _daily_send_date

    today = date.today()
    if _daily_send_date != today:
        _daily_send_count = 0
        _daily_send_date = today

    if _daily_send_count >= DAILY_LIMIT:
        logger.warning(f"Brevo daily limit reached ({DAILY_LIMIT} emails/day)")
        return False

    return True


def _increment_daily_counter():
    global _daily_send_count
    _daily_send_count += 1


# ── Notification Logging ─────────────────────────────────────────────────────

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
            "channel":           "EMAIL",
            "notification_type": notification_type,
            "subject":           subject,
            "body_preview":      body_preview[:300] if body_preview else None,
            "status":            status,
            "provider_ref":      provider_ref,
            "sent_at":           datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:
        logger.error(f"Failed to log email notification: {e}")


# ── Core Send Function ───────────────────────────────────────────────────────

def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    user_id: Optional[str] = None,
    notification_type: str = "SYSTEM",
) -> bool:
    """
    Send email via Brevo transactional SMTP API.

    Args:
        to_email: Recipient email address
        subject: Email subject line
        html_body: Full HTML content
        user_id: Supabase user UUID for notification_log
        notification_type: Matches notification_log.notification_type enum

    Returns:
        True if sent successfully, False otherwise
    """
    if not BREVO_API_KEY:
        logger.warning("BREVO_API_KEY not configured — skipping email send")
        if user_id:
            _log_notification(user_id, notification_type, subject,
                              "SKIPPED (no credentials)", "failed")
        return False

    if not _check_daily_limit():
        if user_id:
            _log_notification(user_id, notification_type, subject,
                              "RATE_LIMITED (300/day)", "failed")
        return False

    payload = {
        "sender": {"name": BREVO_SENDER_NAME, "email": BREVO_SENDER_EMAIL},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_body,
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                BREVO_API_URL,
                json=payload,
                headers={
                    "accept": "application/json",
                    "content-type": "application/json",
                    "api-key": BREVO_API_KEY,
                },
            )

        success = resp.status_code in (200, 201)
        resp_data = resp.json() if resp.status_code < 500 else {}
        provider_ref = resp_data.get("messageId")

        if success:
            _increment_daily_counter()

        if user_id:
            _log_notification(
                user_id, notification_type, subject,
                html_body[:300] if html_body else "",
                "sent" if success else "failed",
                provider_ref,
            )

        if success:
            logger.info(f"✅ Email sent → {to_email} [{subject[:50]}] ref={provider_ref}")
        else:
            logger.error(f"❌ Email failed → {to_email}: {resp.text}")

        return success

    except Exception as e:
        logger.error(f"Brevo exception for {to_email}: {e}")
        if user_id:
            _log_notification(user_id, notification_type, subject,
                              f"EXCEPTION: {str(e)[:200]}", "failed")
        return False


# ── HTML Template Engine ─────────────────────────────────────────────────────

def _base_html(content: str, title: str) -> str:
    """Wrap content in the platform-branded HTML email shell."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background:#F8FAFC;font-family:'Inter',Arial,Helvetica,sans-serif;-webkit-font-smoothing:antialiased;">
  <div style="max-width:560px;margin:24px auto;background:#FFFFFF;border-radius:12px;border:1px solid #E2E8F0;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
    <!-- Header -->
    <div style="background:#0F4C81;padding:20px 24px;">
      <h1 style="color:#FFFFFF;margin:0;font-size:18px;font-weight:600;letter-spacing:-0.02em;">
        📊 Channel Breakout Signals
      </h1>
    </div>
    <!-- Body -->
    <div style="padding:24px 24px 32px;">
      {content}
    </div>
    <!-- Footer -->
    <div style="background:#F8FAFC;padding:16px 24px;border-top:1px solid #E2E8F0;">
      <p style="margin:0;font-size:12px;color:#64748B;line-height:1.5;">
        Courtney Smith Channel Breakout Trading Platform<br>
        This is an automated notification. Reply to admin at aaanurag@yahoo.com
      </p>
    </div>
  </div>
</body>
</html>"""


def _cta_button(label: str, url: str) -> str:
    """Render a prominent call-to-action button."""
    return f"""
    <div style="margin:24px 0;text-align:center;">
      <a href="{url}"
         style="background:#0F4C81;color:#FFFFFF;padding:14px 32px;border-radius:8px;
                text-decoration:none;font-weight:600;font-size:15px;display:inline-block;
                letter-spacing:0.02em;">
        {label}
      </a>
    </div>"""


def _warning_box(icon: str, title: str, message: str, border_color: str = "#D97706", bg_color: str = "#FEF3C7") -> str:
    """Render a styled warning/alert box."""
    return f"""
    <div style="background:{bg_color};border:1px solid {border_color};border-radius:8px;
                padding:16px;margin:16px 0;">
      <strong style="color:#1E293B;">{icon} {title}</strong>
      <p style="margin:8px 0 0;color:#1E293B;font-size:14px;line-height:1.5;">{message}</p>
    </div>"""


def _danger_box(icon: str, title: str, message: str) -> str:
    return _warning_box(icon, title, message, "#DC2626", "#FEE2E2")


# ── Template 1: DAILY_SIGNAL ────────────────────────────────────────────────

def send_daily_signal(user: dict, session_token: str, buy_count: int, exit_count: int) -> bool:
    """Signals ready — includes confirmation link."""
    if not user.get("notify_email"):
        return False

    link = f"{FRONTEND_URL}/confirm/{session_token}"
    name = user["full_name"].split()[0]
    total = buy_count + exit_count

    buy_badge = f'<span style="color:#16A34A;font-size:22px;font-weight:700;">{buy_count} BUY Signal{"s" if buy_count != 1 else ""}</span>' if buy_count else ""
    exit_badge = f'<span style="color:#DC2626;font-size:22px;font-weight:700;">{exit_count} Exit Alert{"s" if exit_count != 1 else ""}</span>' if exit_count else ""
    separator = '<span style="color:#64748B;padding:0 8px;">•</span>' if buy_count and exit_count else ""

    content = f"""
    <p style="color:#1E293B;font-size:15px;margin:0 0 8px;">Hello {name},</p>
    <p style="color:#64748B;font-size:14px;margin:0 0 20px;line-height:1.5;">
      Today's Channel Breakout signals from your watchlist are ready.
      Please confirm your actions.
    </p>
    <div style="text-align:center;margin:20px 0;">
      {buy_badge}{separator}{exit_badge}
    </div>
    {_cta_button("✅ Confirm My Signals →", link)}
    <p style="color:#64748B;font-size:12px;margin:16px 0 0;text-align:center;">
      This link is permanent and unique to you. Do not share it.
    </p>"""

    return send_email(
        user["email"],
        f"📊 {total} Signal{'s' if total != 1 else ''} Ready — Confirm Now",
        _base_html(content, "Daily Signals"),
        user["id"], "DAILY_SIGNAL",
    )


# ── Template 2: NO_SIGNAL_DAY ───────────────────────────────────────────────

def send_no_signal_day(user: dict) -> bool:
    """Scan complete, no signals today — no link sent."""
    if not user.get("notify_email"):
        return False

    name = user["full_name"].split()[0]
    content = f"""
    <p style="color:#1E293B;font-size:15px;margin:0 0 8px;">Hello {name},</p>
    <p style="color:#64748B;font-size:14px;margin:0 0 16px;line-height:1.5;">
      Today's scan is complete. No Channel Breakout signals from your watchlist today.
      No exit signals. No action required.
    </p>
    <div style="background:#F0FDF4;border:1px solid #16A34A;border-radius:8px;padding:14px;text-align:center;">
      <span style="color:#16A34A;font-weight:600;">✅ All Clear — No Action Needed</span>
    </div>"""

    return send_email(
        user["email"],
        "📊 No Signals Today — All Clear",
        _base_html(content, "No Signals Today"),
        user["id"], "NO_SIGNAL_DAY",
    )


# ── Template 3: MARKET_HOLIDAY ──────────────────────────────────────────────

def send_market_holiday(user: dict, holiday_name: str) -> bool:
    """Market closed today for a holiday."""
    if not user.get("notify_email"):
        return False

    name = user["full_name"].split()[0]
    content = f"""
    <p style="color:#1E293B;font-size:15px;margin:0 0 8px;">Hello {name},</p>
    <p style="color:#64748B;font-size:14px;margin:0 0 16px;line-height:1.5;">
      Market is closed today for <strong>{holiday_name}</strong>.
      No scan was run and no signals will be generated.
    </p>
    <div style="background:#EFF6FF;border:1px solid #0F4C81;border-radius:8px;padding:14px;text-align:center;">
      <span style="color:#0F4C81;font-weight:600;">🏖️ Market Holiday — See you on the next trading day!</span>
    </div>"""

    return send_email(
        user["email"],
        f"🏖️ Market Holiday: {holiday_name}",
        _base_html(content, "Market Holiday"),
        user["id"], "MARKET_HOLIDAY",
    )


# ── Template 4: REMINDER ────────────────────────────────────────────────────

def send_reminder(user: dict, session_token: str) -> bool:
    """Yesterday's signals still unconfirmed."""
    if not user.get("notify_email"):
        return False

    name = user["full_name"].split()[0]
    link = f"{FRONTEND_URL}/confirm/{session_token}"
    content = f"""
    <p style="color:#1E293B;font-size:15px;margin:0 0 8px;">Hello {name},</p>
    {_warning_box("⏰", "Pending Confirmation",
                   "Yesterday's signals are still unconfirmed. Please update your confirmations to continue receiving today's signals.")}
    {_cta_button("📋 Confirm Now →", link)}"""

    return send_email(
        user["email"],
        "⏰ Reminder — Signals Awaiting Your Confirmation",
        _base_html(content, "Confirmation Reminder"),
        user["id"], "REMINDER",
    )


# ── Template 5: INACTIVITY_DAY5 ─────────────────────────────────────────────

def send_inactivity_day5(user: dict, session_token: str) -> bool:
    """5 trading days without confirmation — auto-pause warning."""
    if not user.get("notify_email"):
        return False

    name = user["full_name"].split()[0]
    link = f"{FRONTEND_URL}/confirm/{session_token}"
    content = f"""
    <p style="color:#1E293B;font-size:15px;margin:0 0 8px;">Hello {name},</p>
    {_warning_box("⚠️", "Inactivity Warning — Day 5",
                   "You have not confirmed signals for 5 trading days. "
                   "Your account will be <strong>auto-paused in 2 days</strong>. "
                   "Please log in and confirm your actions.")}
    {_cta_button("🔑 Log In & Confirm →", link)}
    <p style="color:#DC2626;font-weight:600;font-size:13px;text-align:center;">
      After auto-pause, you will stop receiving signals until you re-confirm.
    </p>"""

    return send_email(
        user["email"],
        "⚠️ Action Required — Day 5 Inactivity Warning",
        _base_html(content, "Inactivity Warning"),
        user["id"], "INACTIVITY_DAY5",
    )


# ── Template 6: INACTIVITY_DAY12 ────────────────────────────────────────────

def send_inactivity_day12(user: dict, session_token: str) -> bool:
    """12 trading days without action — auto-suspend warning."""
    if not user.get("notify_email"):
        return False

    name = user["full_name"].split()[0]
    link = f"{FRONTEND_URL}/confirm/{session_token}"
    content = f"""
    <p style="color:#1E293B;font-size:15px;margin:0 0 8px;">Hello {name},</p>
    {_danger_box("🚨", "Critical Warning — Day 12",
                  "Your account is currently paused. It will be "
                  "<strong>auto-suspended in 3 days</strong> if no action is taken. "
                  "Once suspended, you will not be able to log in.")}
    {_cta_button("🔑 Log In Now →", link)}
    <p style="color:#DC2626;font-weight:600;font-size:13px;text-align:center;">
      Contact admin at aaanurag@yahoo.com or +91 9303121500 if you need help.
    </p>"""

    return send_email(
        user["email"],
        "🚨 URGENT — Account Suspension in 3 Days",
        _base_html(content, "Suspension Warning"),
        user["id"], "INACTIVITY_DAY12",
    )


# ── Template 7: AUTO_SUSPENDED ──────────────────────────────────────────────

def send_auto_suspended(user: dict) -> bool:
    """Account suspended due to 15-day inactivity."""
    if not user.get("notify_email"):
        return False

    name = user["full_name"].split()[0]
    content = f"""
    <p style="color:#1E293B;font-size:15px;margin:0 0 8px;">Hello {name},</p>
    {_danger_box("🔒", "Account Suspended",
                  "Your account has been suspended due to inactivity (15 trading days with no confirmation). "
                  "You will no longer be able to log in or receive signals.")}
    <p style="color:#1E293B;font-size:14px;line-height:1.5;margin:16px 0;">
      To reactivate your account, please contact the administrator:
    </p>
    <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;padding:16px;margin:16px 0;">
      <p style="margin:0 0 4px;font-size:14px;"><strong>Email:</strong> aaanurag@yahoo.com</p>
      <p style="margin:0;font-size:14px;"><strong>Mobile:</strong> +91 9303121500</p>
    </div>"""

    return send_email(
        user["email"],
        "🔒 Account Suspended — Contact Admin to Reactivate",
        _base_html(content, "Account Suspended"),
        user["id"], "AUTO_SUSPENDED",
    )


# ── Template 8: SCAN_FAILURE (Super Admin only) ─────────────────────────────

def send_scan_failure(admin: dict, scan_date: str, attempt: int, source: str, error_msg: str = "") -> bool:
    """Alert Super Admin about scan failure."""
    if not admin.get("notify_email"):
        return False

    link = f"{FRONTEND_URL}/admin/system"
    content = f"""
    <p style="color:#1E293B;font-size:15px;margin:0 0 8px;">Hello Admin,</p>
    {_danger_box("🚨", "Daily Scan Failed",
                  f"The daily scan failed at 4:30 PM on {scan_date}.<br>"
                  f"Retry attempt: <strong>{attempt}/12</strong><br>"
                  f"Data source: <strong>{source}</strong>"
                  + (f"<br>Error: <code style='font-size:12px;'>{error_msg[:200]}</code>" if error_msg else ""))}
    {_cta_button("🔧 Open System Dashboard →", link)}
    <p style="color:#64748B;font-size:12px;text-align:center;">
      Next retry in 15 minutes. System will auto-cascade to backup sources if retries exhaust.
    </p>"""

    return send_email(
        admin["email"],
        f"🚨 URGENT: Daily Scan Failed — Attempt {attempt}/12",
        _base_html(content, "Scan Failure Alert"),
        admin["id"], "SCAN_FAILURE",
    )


# ── Template 9: STOCK_SUSPENDED ─────────────────────────────────────────────

def send_stock_suspended(user: dict, stock_name: str, ticker: str) -> bool:
    """Stock missing price data for 3+ consecutive days."""
    if not user.get("notify_email"):
        return False

    name = user["full_name"].split()[0]
    content = f"""
    <p style="color:#1E293B;font-size:15px;margin:0 0 8px;">Hello {name},</p>
    {_warning_box("⚠️", f"Stock Alert: {stock_name} ({ticker})",
                   f"No price data has been received for <strong>{stock_name} ({ticker})</strong> "
                   f"for 3 consecutive trading days. This stock may have been suspended or delisted.")}
    <p style="color:#1E293B;font-size:14px;line-height:1.5;margin:16px 0;">
      <strong>Recommended action:</strong> Please check with your broker whether this stock
      has been suspended, delisted, or if there is a corporate action in progress.
    </p>
    <p style="color:#64748B;font-size:13px;">
      No new signals will be generated for this stock until data resumes.
    </p>"""

    return send_email(
        user["email"],
        f"⚠️ Stock Alert: {stock_name} ({ticker}) — No Data for 3 Days",
        _base_html(content, "Stock Suspension Alert"),
        user["id"], "STOCK_SUSPENDED",
    )
