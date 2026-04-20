"""
/me routes — Current trader's profile, capital, notifications
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
from auth import get_current_user
from config import supabase
from datetime import datetime, timezone

router = APIRouter()


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    mobile: Optional[str] = None
    risk_percent: Optional[float] = None
    notify_email: Optional[bool] = None
    notify_whatsapp: Optional[bool] = None
    first_login_complete: Optional[bool] = None
    capital_entered: Optional[bool] = None


class CapitalRequest(BaseModel):
    amount: float
    type: str  # DEPOSIT | WITHDRAWAL


class ChangePasswordRequest(BaseModel):
    new_password: str
    confirm_password: str


@router.get("/me")
async def get_me(user=Depends(get_current_user)):
    """Get current user's full profile."""
    return user


@router.patch("/me")
async def update_me(req: UpdateProfileRequest, user=Depends(get_current_user)):
    """Update profile fields."""
    if req.risk_percent is not None and not (0.5 <= req.risk_percent <= 5.0):
        raise HTTPException(status_code=400, detail="Risk % must be between 0.5 and 5.0")

    updates = {k: v for k, v in req.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = supabase.table("users").update(updates).eq("id", user["id"]).execute()
    return result.data[0]


@router.post("/me/capital")
async def add_capital(req: CapitalRequest, user=Depends(get_current_user)):
    """Add or withdraw capital."""
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    if req.type not in ("DEPOSIT", "WITHDRAWAL"):
        raise HTTPException(status_code=400, detail="Type must be DEPOSIT or WITHDRAWAL")

    current = supabase.table("users").select("available_capital").eq("id", user["id"]).single().execute().data
    current_balance = current["available_capital"] or 0

    if req.type == "WITHDRAWAL" and req.amount > current_balance:
        raise HTTPException(status_code=400, detail="Insufficient available capital")

    sign = 1 if req.type == "DEPOSIT" else -1
    new_balance = current_balance + (sign * req.amount)

    supabase.table("users").update({
        "available_capital": new_balance,
        "starting_capital": new_balance if req.type == "DEPOSIT" and current_balance == 0 else supabase.table("users").select("starting_capital").eq("id", user["id"]).single().execute().data["starting_capital"],
    }).eq("id", user["id"]).execute()

    # Log the capital change
    supabase.table("capital_log").insert({
        "user_id": user["id"],
        "change_type": req.type,
        "amount": sign * req.amount,
        "balance_after": new_balance,
        "source": "MANUAL",
        "changed_by": user["id"]
    }).execute()

    return {"available_capital": new_balance, "message": f"{req.type} recorded"}


@router.get("/me/capital-log")
async def get_capital_log(user=Depends(get_current_user)):
    """Get last 50 capital transactions."""
    result = supabase.table("capital_log") \
        .select("*") \
        .eq("user_id", user["id"]) \
        .order("created_at", desc=True) \
        .limit(50) \
        .execute()
    return result.data


@router.post("/auth/change-password")
async def change_password(req: ChangePasswordRequest, user=Depends(get_current_user)):
    """Change password via Supabase Admin API."""
    if req.new_password != req.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    import httpx, os
    from config import SUPABASE_URL, SUPABASE_SERVICE_KEY

    # Get Supabase auth user ID for this email
    auth_users = supabase.auth.admin.list_users()
    auth_user = next((u for u in auth_users if u.email == user["email"]), None)
    if not auth_user:
        raise HTTPException(status_code=404, detail="Auth user not found")

    # Update password via Admin API
    supabase.auth.admin.update_user_by_id(auth_user.id, {"password": req.new_password})

    # Mark password_changed
    supabase.table("users").update({
        "password_changed": True,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", user["id"]).execute()

    return {"message": "Password changed successfully"}
