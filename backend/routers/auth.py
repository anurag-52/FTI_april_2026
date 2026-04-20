"""
Auth routes: login, change-password, forgot-password

Business Rules:
- No self-registration (Rule 1)
- First login must set password + capital before dashboard (Rule 2)
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from config import supabase, SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY, FRONTEND_URL
from auth import get_current_user
import httpx
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


class ChangePasswordRequest(BaseModel):
    new_password: str
    confirm_password: str


class ForgotPasswordRequest(BaseModel):
    email: str


@router.post("/auth/login")
async def login(req: LoginRequest):
    """
    Login with email/password → returns JWT access token + user profile.
    Frontend uses first_login_complete, password_changed, capital_entered
    to enforce the first-login gate (Rule 2).
    """
    # Authenticate via Supabase Auth
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            json={"email": req.email, "password": req.password},
            headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
            timeout=15
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    auth_data = resp.json()
    access_token = auth_data.get("access_token")
    refresh_token = auth_data.get("refresh_token")

    # Load user from our table
    result = supabase.table("users").select("*").eq("email", req.email).maybeSingle().execute()
    if not result.data:
        raise HTTPException(status_code=401, detail="User not found in system")

    user = result.data

    # Suspended users cannot login at all
    if user["status"] == "suspended":
        raise HTTPException(
            status_code=403,
            detail="Account suspended. Contact admin at aaanurag@yahoo.com or +91 9303121500"
        )

    # Paused users CAN login (to confirm pending signals and reactivate)
    # but frontend should show a banner

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": user["id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "mobile": user.get("mobile"),
            "role": user["role"],
            "status": user["status"],
            "starting_capital": user["starting_capital"],
            "available_capital": user["available_capital"],
            "risk_percent": user["risk_percent"],
            "notify_email": user["notify_email"],
            "notify_whatsapp": user["notify_whatsapp"],
            "first_login_complete": user["first_login_complete"],
            "password_changed": user["password_changed"],
            "capital_entered": user["capital_entered"],
            "confirmation_pending": user["confirmation_pending"],
            "inactivity_days": user["inactivity_days"],
            "created_at": user["created_at"],
        }
    }


@router.post("/auth/change-password")
async def change_password(req: ChangePasswordRequest, user=Depends(get_current_user)):
    """
    Change password via Supabase Admin API.
    On first login, this must be called before accessing the dashboard (Rule 2).
    """
    if req.new_password != req.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    try:
        # Get Supabase auth user ID
        auth_uid = user.get("_auth_uid")
        if not auth_uid:
            # Fallback: look up by email
            auth_response = supabase.auth.admin.list_users()
            auth_users_list = auth_response.users if hasattr(auth_response, 'users') else auth_response
            auth_user = next((u for u in auth_users_list if u.email == user["email"]), None)
            if not auth_user:
                raise HTTPException(status_code=404, detail="Auth user not found")
            auth_uid = auth_user.id

        # Update password via Admin API (service role key bypasses checks)
        supabase.auth.admin.update_user_by_id(auth_uid, {"password": req.new_password})

        # Mark password_changed in our users table
        now = datetime.now(timezone.utc).isoformat()
        updates = {
            "password_changed": True,
            "updated_at": now,
        }

        # If capital is also entered, mark first_login_complete
        if user.get("capital_entered"):
            updates["first_login_complete"] = True

        supabase.table("users").update(updates).eq("id", user["id"]).execute()

        logger.info(f"Password changed for user {user['email']}")
        return {"message": "Password changed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to change password: {str(e)}")


@router.post("/auth/forgot-password")
async def forgot_password(req: ForgotPasswordRequest):
    """
    Send password reset email via Supabase Auth.
    Always returns success (don't leak whether email exists).
    """
    try:
        supabase.auth.reset_password_for_email(req.email, {
            "redirect_to": f"{FRONTEND_URL}/login"
        })
    except Exception as e:
        logger.error(f"Forgot password error: {e}")
        # Don't expose the error — always return success for security

    return {"message": "Password reset email sent if account exists"}
