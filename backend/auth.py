"""
JWT Authentication Middleware.
Validates Supabase JWT tokens and injects the current user into request state.
"""
from fastapi import Depends, HTTPException, Header
from config import SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_JWT_SECRET, CRON_SECRET, supabase
import httpx
import logging

logger = logging.getLogger(__name__)


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
                    "apikey": SUPABASE_ANON_KEY,
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

        # Check status — suspended users cannot access anything
        if user["status"] == "suspended":
            raise HTTPException(status_code=403, detail="Account suspended. Contact admin at aaanurag@yahoo.com or +91 9303121500")

        # Attach the raw JWT token for downstream use (e.g. password change)
        user["_access_token"] = token
        user["_auth_uid"] = auth_user.get("id")

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auth error: {e}")
        raise HTTPException(status_code=401, detail=f"Authentication error: {str(e)}")


async def get_admin_user(user=Depends(get_current_user)):
    """Require admin role."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def get_cron_auth(x_cron_secret: str = Header(None)):
    """Validate cron secret for internal endpoints."""
    if x_cron_secret != CRON_SECRET:
        raise HTTPException(status_code=403, detail="Invalid cron secret")
    return True
