"""
/me routes — Current trader's profile, capital management

Business Rules:
- First login gate: password + capital must both be done (Rule 2)
- Capital changes are free, no approval, all logged (Rule 11 in PRD)
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
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


class CapitalRequest(BaseModel):
    amount: float
    type: str  # DEPOSIT | WITHDRAWAL
    notes: Optional[str] = None


class FirstLoginCapitalRequest(BaseModel):
    """Special request for first-login capital entry."""
    starting_capital: float


@router.get("/me")
async def get_me(user=Depends(get_current_user)):
    """Get current user's full profile."""
    # Remove internal fields before sending to frontend
    safe_user = {k: v for k, v in user.items() if not k.startswith("_")}
    return safe_user


@router.patch("/me")
async def update_me(req: UpdateProfileRequest, user=Depends(get_current_user)):
    """Update profile fields. Traders can edit: name, mobile, risk%, notifications."""
    if req.risk_percent is not None and not (0.5 <= req.risk_percent <= 5.0):
        raise HTTPException(status_code=400, detail="Risk % must be between 0.5 and 5.0")

    updates = {k: v for k, v in req.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = supabase.table("users").update(updates).eq("id", user["id"]).execute()
    return result.data[0] if result.data else {"message": "Updated"}


@router.post("/me/capital")
async def add_capital(req: CapitalRequest, user=Depends(get_current_user)):
    """
    Add or withdraw capital. Free — no approval needed.
    Every change is logged with amount, type, date, time, who made change.
    """
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    if req.type not in ("DEPOSIT", "WITHDRAWAL"):
        raise HTTPException(status_code=400, detail="Type must be DEPOSIT or WITHDRAWAL")

    current_balance = float(user.get("available_capital") or 0)
    current_starting = float(user.get("starting_capital") or 0)

    if req.type == "WITHDRAWAL" and req.amount > current_balance:
        raise HTTPException(status_code=400, detail="Insufficient available capital")

    sign = 1 if req.type == "DEPOSIT" else -1
    new_balance = current_balance + (sign * req.amount)
    now = datetime.now(timezone.utc).isoformat()

    # Update user capital
    user_updates = {
        "available_capital": new_balance,
        "updated_at": now,
    }

    # If this is the first deposit (capital was 0), also set starting_capital
    # and mark capital_entered = True for first-login gate
    if req.type == "DEPOSIT":
        if current_starting == 0:
            user_updates["starting_capital"] = req.amount
        else:
            user_updates["starting_capital"] = current_starting + req.amount
        user_updates["capital_entered"] = True

        # If password is already changed, mark first_login_complete
        if user.get("password_changed"):
            user_updates["first_login_complete"] = True

    supabase.table("users").update(user_updates).eq("id", user["id"]).execute()

    # Log the capital change
    supabase.table("capital_log").insert({
        "user_id": user["id"],
        "change_type": req.type,
        "amount": sign * req.amount,
        "balance_after": new_balance,
        "notes": req.notes or f"{req.type.title()} by trader",
        "source": "MANUAL",
        "changed_by": user["id"],
    }).execute()

    return {"available_capital": new_balance, "message": f"{req.type} of ₹{req.amount:,.2f} recorded"}


@router.get("/me/capital-log")
async def get_capital_log(user=Depends(get_current_user)):
    """Get full capital transaction history (last 100 entries)."""
    result = supabase.table("capital_log") \
        .select("*") \
        .eq("user_id", user["id"]) \
        .order("created_at", desc=True) \
        .limit(100) \
        .execute()
    return result.data or []
