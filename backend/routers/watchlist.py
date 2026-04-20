"""
/me/watchlist routes — Add, deactivate, list watchlisted stocks
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from auth import get_current_user
from config import supabase
from datetime import datetime, timezone

router = APIRouter()

WATCHLIST_MAX = 30


class AddWatchlistRequest(BaseModel):
    stock_id: str


class UpdateWatchlistRequest(BaseModel):
    is_active: bool


@router.get("/me/watchlist")
async def get_watchlist(user=Depends(get_current_user)):
    """Get user's full watchlist split into active/inactive."""
    result = supabase.table("watchlists") \
        .select("*, stocks(id, ticker_nse, ticker_bse, company_name, exchange, sector)") \
        .eq("user_id", user["id"]) \
        .order("added_at", desc=True) \
        .execute()

    items = result.data or []
    active   = [i for i in items if i.get("is_active")]
    inactive = [i for i in items if not i.get("is_active")]

    # Flatten stock info into each item
    def flatten(item):
        s = item.get("stocks") or {}
        return {
            "stock_id": item["stock_id"],
            "is_active": item["is_active"],
            "added_at": item["added_at"],
            "ticker_nse": s.get("ticker_nse"),
            "company_name": s.get("company_name"),
            "exchange": s.get("exchange"),
            "sector": s.get("sector"),
        }

    return {
        "active": [flatten(i) for i in active],
        "inactive": [flatten(i) for i in inactive],
        "total_active": len(active),
        "limit": WATCHLIST_MAX
    }


@router.post("/me/watchlist")
async def add_to_watchlist(req: AddWatchlistRequest, user=Depends(get_current_user)):
    """Add a stock to watchlist (max 30 active)."""
    # Check current active count
    count = supabase.table("watchlists") \
        .select("id", count="exact") \
        .eq("user_id", user["id"]) \
        .eq("is_active", True) \
        .execute()

    if (count.count or 0) >= WATCHLIST_MAX:
        raise HTTPException(status_code=400, detail=f"Maximum {WATCHLIST_MAX} active stocks reached")

    # Verify stock exists
    stock = supabase.table("stocks").select("id, ticker_nse").eq("id", req.stock_id).maybeSingle().execute()
    if not stock.data:
        raise HTTPException(status_code=404, detail="Stock not found")

    # Upsert (re-activate if previously deactivated)
    supabase.table("watchlists").upsert({
        "user_id": user["id"],
        "stock_id": req.stock_id,
        "is_active": True,
        "added_at": datetime.now(timezone.utc).isoformat(),
        "deactivated_at": None
    }, on_conflict="user_id,stock_id").execute()

    return {"message": f"Added {stock.data['ticker_nse']} to watchlist"}


@router.patch("/me/watchlist/{stock_id}")
async def update_watchlist_item(stock_id: str, req: UpdateWatchlistRequest, user=Depends(get_current_user)):
    """Activate or deactivate a watchlist entry."""
    # Cannot deactivate if open position exists
    if not req.is_active:
        open_pos = supabase.table("positions") \
            .select("id") \
            .eq("user_id", user["id"]) \
            .eq("stock_id", stock_id) \
            .eq("status", "open") \
            .execute()
        if open_pos.data:
            raise HTTPException(status_code=400, detail="Cannot deactivate — you have an open position in this stock")

    updates = {
        "is_active": req.is_active,
        "deactivated_at": datetime.now(timezone.utc).isoformat() if not req.is_active else None
    }
    supabase.table("watchlists").update(updates) \
        .eq("user_id", user["id"]).eq("stock_id", stock_id).execute()

    return {"message": "Watchlist updated"}


@router.get("/stocks/search")
async def search_stocks(q: str, user=Depends(get_current_user)):
    """Search stocks by ticker or name."""
    if len(q) < 2:
        return []

    q_upper = q.upper()
    result = supabase.table("stocks") \
        .select("id, ticker_nse, ticker_bse, company_name, exchange, sector") \
        .eq("is_active", True) \
        .eq("is_suspended", False) \
        .or_(f"ticker_nse.ilike.%{q_upper}%,company_name.ilike.%{q}%") \
        .limit(10) \
        .execute()

    return result.data or []
