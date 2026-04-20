"""
Auth routes: login, change-password, forgot-password
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from config import supabase, SUPABASE_URL, SUPABASE_ANON_KEY
import httpx
import os

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


class ChangePasswordRequest(BaseModel):
    new_password: str
    confirm_password: str


class ForgotPasswordRequest(BaseModel):
    email: str


@router.post("/login")
async def login(req: LoginRequest):
    """Login with email/password → returns JWT access token."""
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

    # Load user from our table
    result = supabase.table("users").select("*").eq("email", req.email).single().execute()
    if not result.data:
        raise HTTPException(status_code=401, detail="User not found in system")

    user = result.data
    if user["status"] == "suspended":
        raise HTTPException(status_code=403, detail="Account suspended. Contact admin.")

    return {"access_token": access_token, "user": user}


@router.post("/change-password")
async def change_password(req: ChangePasswordRequest, token: str = None):
    """Change password via Supabase Auth."""
    if req.new_password != req.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    # Use admin API to change password (called with user's JWT via separate header)
    # This is simplified — in practice, pass the user's JWT from the middleware
    return {"message": "Password change requested. Use Supabase client SDK on frontend for now."}


@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest):
    """Send password reset email via Supabase Auth."""
    supabase.auth.reset_password_email(req.email, {
        "redirect_to": f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/login"
    })
    return {"message": "Password reset email sent if account exists"}
