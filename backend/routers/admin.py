"""
/admin routes — User management, system overview (admin only)

Business Rules:
- No self-registration — admin creates all accounts (Rule 1)
- Admin can confirm signals on behalf of any trader
- Admin can adjust capital (all changes logged)
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from auth import get_admin_user
from config import supabase, FRONTEND_URL
from datetime import datetime, timezone, date
import secrets
import string
import logging

logger = logging.getLogger(__name__)
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
    starting_capital: Optional[float] = None
    available_capital: Optional[float] = None


class AdminConfirmItem(BaseModel):
    signal_id: str
    actioned: bool
    qty: Optional[int] = None
    price: Optional[float] = None


class AdminConfirmRequest(BaseModel):
    confirmations: List[AdminConfirmItem]


def _gen_temp_password(length: int = 12) -> str:
    chars = string.ascii_letters + string.digits + "!@#$"
    return ''.join(secrets.choice(chars) for _ in range(length))


# ─── User management ─────────────────────────────────────────────────────────

@router.post("/admin/users")
async def create_user(req: CreateUserRequest, admin=Depends(get_admin_user)):
    """Create a new trader account. Generates temp password + sends welcome email."""
    # Check email not already in use
    result = supabase.table("users").select("id").eq("email", req.email).maybe_single().execute()
    if result and result.data:
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
    result = supabase.table("users").insert({
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
    }).execute()
    
    if not result or not result.data:
        raise HTTPException(status_code=500, detail="Failed to create user record")
    
    user_row = result.data[0]

    # Log initial capital deposit if any
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
                <div><strong>URL:</strong> {FRONTEND_URL}/login</div>
                <div><strong>Email:</strong> {req.email}</div>
                <div><strong>Temp Password:</strong> <code style="background:#e2e8f0;padding:2px 6px;border-radius:4px">{temp_password}</code></div>
              </div>
              <p>⚠️ You will be required to change your password on first login.</p>
              {f'<p>Your starting capital of ₹{req.starting_capital:,.0f} has been set up.</p>' if req.starting_capital > 0 else '<p>Please enter your starting capital after login.</p>'}
            </div>
            """,
            user_row["id"],
            "SYSTEM"
        )
    except Exception as e:
        logger.warning(f"Welcome email failed for {req.email}: {e}")

    return {
        "message": f"Trader {req.full_name} created successfully",
        "user_id": user_row["id"],
        "temp_password": temp_password,
    }


@router.get("/admin/users")
async def get_users(admin=Depends(get_admin_user)):
    """Get all traders with summary stats."""
    result = supabase.table("users") \
        .select("id, full_name, email, mobile, role, status, starting_capital, available_capital, risk_percent, inactivity_days, warned_day5, warned_day12, confirmation_pending, last_confirmed_at, notify_email, notify_whatsapp, first_login_complete, password_changed, capital_entered, created_at") \
        .order("created_at", desc=True) \
        .execute()
    return result.data or []

@router.post("/admin/hydrate/{stock_id}")
async def admin_hydrate_stock(stock_id: str, background_tasks: BackgroundTasks, admin=Depends(get_admin_user)):
    """Force an immediate 10-year historical backfill for any stock."""
    stock = supabase.table("stocks").select("*").eq("id", stock_id).maybe_single().execute().data
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
        
    from scan_engine.background_jobs import fetch_and_compute_historical
    background_tasks.add_task(
        fetch_and_compute_historical, 
        stock_id=stock["id"], 
        ticker_nse=stock.get("ticker_nse"), 
        ticker_bse=stock.get("ticker_bse")
    )
    return {"message": f"Historical hydration started for {stock.get('ticker_nse')}"}


@router.get("/admin/users/{user_id}")
async def get_user_detail(user_id: str, admin=Depends(get_admin_user)):
    """Get full user detail with positions, signals, watchlist, capital log."""
    user = supabase.table("users").select("*").eq("id", user_id).maybe_single().execute().data
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Positions (last 30)
    positions = supabase.table("positions") \
        .select("*, stocks(ticker_nse, company_name)") \
        .eq("user_id", user_id) \
        .order("entry_date", desc=True) \
        .limit(30) \
        .execute().data or []

    # Signals (last 50)
    signals = supabase.table("signals") \
        .select("*, stocks(ticker_nse, company_name)") \
        .eq("user_id", user_id) \
        .order("signal_date", desc=True) \
        .limit(50) \
        .execute().data or []

    # Capital log (last 50)
    capital_log = supabase.table("capital_log") \
        .select("*") \
        .eq("user_id", user_id) \
        .order("created_at", desc=True) \
        .limit(50) \
        .execute().data or []

    # Watchlist
    watchlist = supabase.table("watchlists") \
        .select("*, stocks(ticker_nse, company_name, exchange)") \
        .eq("user_id", user_id) \
        .order("added_at", desc=True) \
        .execute().data or []

    return {
        **user,
        "positions": positions,
        "signals": signals,
        "capital_log": capital_log,
        "watchlist": watchlist,
    }


@router.patch("/admin/users/{user_id}")
async def update_user(user_id: str, req: UpdateUserRequest, admin=Depends(get_admin_user)):
    """Update a trader's profile, status, or capital."""
    updates = {k: v for k, v in req.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    if "status" in updates and updates["status"] not in ("active", "paused", "suspended"):
        raise HTTPException(status_code=400, detail="Invalid status. Must be: active, paused, suspended")

    if "risk_percent" in updates and not (0.5 <= updates["risk_percent"] <= 5.0):
        raise HTTPException(status_code=400, detail="Risk % must be between 0.5 and 5.0")

    # Reactivation resets inactivity
    if "status" in updates and updates["status"] == "active":
        updates.setdefault("inactivity_days", 0)
        updates["warned_day5"] = False
        updates["warned_day12"] = False

    # Load current user for capital change logging
    if "starting_capital" in updates or "available_capital" in updates:
        current = supabase.table("users").select("starting_capital, available_capital").eq("id", user_id).maybe_single().execute().data
        if not current:
            raise HTTPException(status_code=404, detail="User not found")

        # Log capital adjustment
        if "available_capital" in updates:
            diff = updates["available_capital"] - (current["available_capital"] or 0)
            if diff != 0:
                supabase.table("capital_log").insert({
                    "user_id": user_id,
                    "change_type": "ADMIN_ADJUST",
                    "amount": diff,
                    "balance_after": updates["available_capital"],
                    "notes": "Capital adjusted by admin",
                    "changed_by": admin["id"],
                    "source": "ADMIN",
                }).execute()

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = supabase.table("users").update(updates).eq("id", user_id).execute()
    return result.data[0] if result.data else {"message": "Updated"}


@router.post("/admin/users/{user_id}/confirm")
async def admin_confirm_signals(user_id: str, req: AdminConfirmRequest, admin=Depends(get_admin_user)):
    """
    Admin confirms signals on behalf of a trader.
    Same logic as trader confirmation, but triggered by admin.
    """
    # Verify target user exists
    target_user = supabase.table("users").select("*").eq("id", user_id).maybe_single().execute().data
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get today's session for this trader
    today = str(date.today())
    session = supabase.table("notification_sessions") \
        .select("*") \
        .eq("user_id", user_id) \
        .eq("signal_date", today) \
        .maybe_single() \
        .execute().data

    if not session:
        raise HTTPException(status_code=404, detail="No signal session found for this trader today")
    if session.get("submitted"):
        raise HTTPException(status_code=400, detail="Session already submitted")

    # Process confirmations using shared logic
    from routers.signals import _process_confirmations
    result = await _process_confirmations(session, req.confirmations, user_id)

    logger.info(f"Admin {admin['email']} confirmed signals for user {user_id}")
    return result


class UpdateSettingsRequest(BaseModel):
    msg91_api_key: Optional[str] = None
    msg91_sender_id: Optional[str] = None
    resend_api_key: Optional[str] = None
    resend_from_email: Optional[str] = None


@router.get("/admin/settings")
async def get_system_settings(admin=Depends(get_admin_user)):
    """Fetch global system settings (integrations API keys)."""
    result = supabase.table("system_settings").select("*").eq("id", "global").maybe_single().execute()
    if not result.data:
        # DB returns None if empty, return empty dict or defaults
        return {}
    return result.data


@router.patch("/admin/settings")
async def update_system_settings(req: UpdateSettingsRequest, admin=Depends(get_admin_user)):
    """Update global system settings (integrations API keys)."""
    updates = {k: v for k, v in req.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No settings to update")
    
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    # Upsert to 'global' row
    updates["id"] = "global"
    
    result = supabase.table("system_settings").upsert(updates).execute()
    logger.info(f"Admin {admin['email']} updated system settings")
    return result.data[0] if result.data else {"message": "Settings updated"}

# ─── System dashboard ────────────────────────────────────────────────────────

@router.get("/admin/system")
async def get_system_overview(admin=Depends(get_admin_user)):
    """Get system-level stats: scan history, pending confirmations, notification log."""
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

    # Pending confirmations (any date, not submitted)
    pending_sessions = supabase.table("notification_sessions") \
        .select("*, users(full_name, email)") \
        .eq("submitted", False) \
        .eq("has_signals", True) \
        .order("signal_date", desc=True) \
        .limit(20) \
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

    # Users approaching inactivity thresholds
    at_risk = supabase.table("users") \
        .select("id, full_name, email, inactivity_days, status") \
        .eq("role", "trader") \
        .gte("inactivity_days", 3) \
        .order("inactivity_days", desc=True) \
        .execute().data or []

    # Background jobs (stocks being computed)
    computing = supabase.table("stocks") \
        .select("ticker_nse, company_name, compute_status, compute_progress") \
        .in_("compute_status", ["pending", "running"]) \
        .execute().data or []

    return {
        "scan_logs": scan_logs,
        "notification_log": notif_log,
        "pending_sessions": pending_sessions,
        "upcoming_holidays": holidays,
        "suspended_stocks": suspended,
        "at_risk_traders": at_risk,
        "computing_stocks": computing,
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
