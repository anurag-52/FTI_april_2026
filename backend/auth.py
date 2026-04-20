"""
JWT Authentication Middleware.
Validates Supabase JWT tokens and injects the current user into request state.
"""
from fastapi import Depends, HTTPException, Header
from jose import jwt, JWTError
from config import SUPABASE_URL, supabase
import httpx
import os

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")


async def get_current_user(authorization: str = Header(None)):
    """Extract and validate JWT from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization.split(" ")[1]

    try:
        # Use Supabase's user endpoint to validate token and get user
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{SUPABASE_URL}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": os.environ["SUPABASE_ANON_KEY"],
                },
                timeout=10
            )
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        auth_user = resp.json()
        email = auth_user.get("email")
        if not email:
            raise HTTPException(status_code=401, detail="Token has no email")

        # Load user from our users table
        result = supabase.table("users").select("*").eq("email", email).single().execute()
        if not result.data:
            raise HTTPException(status_code=401, detail="User not found in system")

        user = result.data

        # Check status
        if user["status"] == "suspended":
            raise HTTPException(status_code=403, detail="Account suspended. Contact admin.")

        return user

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication error: {str(e)}")


async def get_admin_user(user=Depends(get_current_user)):
    """Require admin role."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def get_cron_auth(x_cron_secret: str = Header(None)):
    """Validate cron secret for internal endpoints."""
    from config import CRON_SECRET
    if x_cron_secret != CRON_SECRET:
        raise HTTPException(status_code=403, detail="Invalid cron secret")
    return True
