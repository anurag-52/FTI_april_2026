"""
/admin routes — User management, system overview (admin only)
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from auth import get_admin_user
from config import supabase
from datetime import datetime, timezone
import uuid
import secrets
import string

router = APIRouter()


class CreateUserRequest(BaseModel):
    full_name: str
    email: str
    mobile: Optional[str] = None
    starting_capital: float = 0
    risk_percent: float = 1.0
    notify_email: bool = True
    notify_whatsapp: bool = False


class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    mobile: Optional[str] = None
    status: Optional[str] = None
    risk_percent: Optional[float] = None
    notify_email: Optional[bool] = None
    notify_whatsapp: Optional[bool] = None
    inactivity_days: Optional[int] = None
    warned_day5: Optional[bool] = None
    warned_day12: Optional[bool] = None


def _gen_temp_password(length: int = 12) -> str:
    chars = string.ascii_letters + string.digits + "!@#$"
    return ''.join(secrets.choice(chars) for _ in range(length))


# ─── User management ─────────────────────────────────────────────────────────

@router.get("/admin/users")
async def get_users(admin=Depends(get_admin_user)):
    """Get all traders with summary stats."""
    result = supabase.table("users") \
        .select("id, full_name, email, mobile, role, status, starting_capital, available_capital, risk_percent, inactivity_days, warned_day5, warned_day12, confirmation_pending, last_confirmed_at, notify_email, notify_whatsapp, created_at") \
        .order("created_at", desc=True) \
        .execute()
    return result.data or []


@router.get("/admin/users/{user_id}")
async def get_user_detail(user_id: str, admin=Depends(get_admin_user)):
    """Get full user detail with positions, signals, capital log."""
    user = supabase.table("users").select("*").eq("id", user_id).maybeSingle().execute().data
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    positions = supabase.table("positions") \
        .select("*, stocks(ticker_nse, company_name)") \
        .eq("user_id", user_id) \
        .order("entry_date", desc=True) \
        .limit(20) \
        .execute().data or []

    signals = supabase.table("signals") \
        .select("*, stocks(ticker_nse)") \
        .eq("user_id", user_id) \
        .order("signal_date", desc=True) \
        .limit(30) \
        .execute().data or []

    capital_log = supabase.table("capital_log") \
        .select("*") \
        .eq("user_id", user_id) \
        .order("created_at", desc=True) \
        .limit(30) \
        .execute().data or []

    return {**user, "positions": positions, "signals": signals, "capital_log": capital_log}


@router.post("/admin/users")
async def create_user(req: CreateUserRequest, admin=Depends(get_admin_user)):
    """Create a new trader account. Generates temp password + sends welcome email."""
    # Check email not already in use
    existing = supabase.table("users").select("id").eq("email", req.email).maybeSingle().execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Email already exists")

    temp_password = _gen_temp_password()

    # Create Supabase Auth user
    try:
        auth_result = supabase.auth.admin.create_user({
            "email": req.email,
            "password": temp_password,
            "email_confirm": True,
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create auth user: {str(e)}")

    # Create user in our table
    now = datetime.now(timezone.utc).isoformat()
    user_row = supabase.table("users").insert({
        "full_name": req.full_name,
        "email": req.email,
        "mobile": req.mobile,
        "role": "trader",
        "status": "active",
        "starting_capital": req.starting_capital,
        "available_capital": req.starting_capital,
        "risk_percent": req.risk_percent,
        "notify_email": req.notify_email,
        "notify_whatsapp": req.notify_whatsapp,
        "first_login_complete": False,
        "password_changed": False,
        "capital_entered": req.starting_capital > 0,
        "created_by": admin["id"],
    }).execute().data[0]

    # Log initial capital deposit
    if req.starting_capital > 0:
        supabase.table("capital_log").insert({
            "user_id": user_row["id"],
            "change_type": "DEPOSIT",
            "amount": req.starting_capital,
            "balance_after": req.starting_capital,
            "notes": "Initial capital set by admin",
            "changed_by": admin["id"],
            "source": "ADMIN"
        }).execute()

    # Send welcome email
    try:
        from integrations.email_resend import send_email
        send_email(
            req.email,
            "Welcome to Channel Breakout Signals — Your Account is Ready",
            f"""
            <div style="font-family: Inter, Arial, sans-serif; max-width:540px; margin:0 auto">
              <h2>Welcome, {req.full_name.split()[0]}! 🎉</h2>
              <p>Your trading signals account has been created. Use the credentials below to login:</p>
              <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:16px; margin:16px 0">
                <div><strong>URL:</strong> {__import__('config').FRONTEND_URL}/login</div>
                <div><strong>Email:</strong> {req.email}</div>
                <div><strong>Temp Password:</strong> <code style="background:#e2e8f0;padding:2px 6px;border-radius:4px">{temp_password}</code></div>
              </div>
              <p>⚠️ You will be required to change your password on first login.</p>
              <p>Your starting capital of ₹{req.starting_capital:,.0f} has been set up.</p>
            </div>
            """,
            user_row["id"],
            "SYSTEM"
        )
    except Exception:
        pass  # Don't fail if email fails

    return {
        "message": f"Trader {req.full_name} created successfully",
        "user_id": user_row["id"],
        "temp_password": temp_password,  # Return to admin so they can share manually if email fails
    }


@router.patch("/admin/users/{user_id}")
async def update_user(user_id: str, req: UpdateUserRequest, admin=Depends(get_admin_user)):
    """Update a trader's profile or status."""
    updates = {k: v for k, v in req.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    if "status" in updates and updates["status"] not in ("active", "paused", "suspended"):
        raise HTTPException(status_code=400, detail="Invalid status")

    if "status" in updates and updates["status"] == "active":
        # Reactivation resets inactivity
        updates.setdefault("inactivity_days", 0)

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = supabase.table("users").update(updates).eq("id", user_id).execute()
    return result.data[0] if result.data else {"message": "Updated"}


# ─── System dashboard ────────────────────────────────────────────────────────

@router.get("/admin/system")
async def get_system_overview(admin=Depends(get_admin_user)):
    """Get system-level stats: scan history, pending confirmations, notification log."""
    from datetime import date

    today = str(date.today())

    # Last 7 scan logs
    scan_logs = supabase.table("scan_log") \
        .select("*") \
        .order("scan_date", desc=True) \
        .limit(7) \
        .execute().data or []

    # Today's notification log (last 50)
    notif_log = supabase.table("notification_log") \
        .select("*") \
        .order("sent_at", desc=True) \
        .limit(50) \
        .execute().data or []

    # Pending confirmations
    pending_sessions = supabase.table("notification_sessions") \
        .select("*, users(full_name, email)") \
        .eq("signal_date", today) \
        .eq("submitted", False) \
        .execute().data or []

    # Market holidays (next 30 days)
    from datetime import timedelta
    future_date = (date.today() + timedelta(days=30)).isoformat()
    holidays = supabase.table("market_holidays") \
        .select("*") \
        .gte("holiday_date", today) \
        .lte("holiday_date", future_date) \
        .order("holiday_date") \
        .execute().data or []

    # Suspended stocks
    suspended = supabase.table("stocks") \
        .select("ticker_nse, company_name, suspended_at") \
        .eq("is_suspended", True) \
        .execute().data or []

    return {
        "scan_logs": scan_logs,
        "notification_log": notif_log,
        "pending_sessions": pending_sessions,
        "upcoming_holidays": holidays,
        "suspended_stocks": suspended,
    }


@router.get("/admin/notifications")
async def get_notifications(admin=Depends(get_admin_user)):
    """Get all notification logs."""
    result = supabase.table("notification_log") \
        .select("*, users(full_name, email)") \
        .order("sent_at", desc=True) \
        .limit(100) \
        .execute()
    return result.data or []
