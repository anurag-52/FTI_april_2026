"""
/me/watchlist routes — Add, deactivate, delete, list watchlisted stocks

Business Rules:
- Max 30 active stocks (Rule 3)
- Cannot deactivate/delete stock with open positions — 409 Conflict (Rule 4)
"""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from auth import get_current_user
from config import supabase
from datetime import datetime, timezone
import requests
import logging
from stock_resolver import resolve_stock_id

logger = logging.getLogger(__name__)

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
        .select("*, stocks(id, ticker_nse, ticker_bse, company_name, exchange, sector, compute_status, compute_progress)") \
        .eq("user_id", user["id"]) \
        .order("added_at", desc=True) \
        .execute()

    items = result.data or []
    active   = [i for i in items if i.get("is_active")]
    inactive = [i for i in items if not i.get("is_active")]

    def flatten(item):
        s = item.get("stocks") or {}
        return {
            "id": item.get("id"),
            "stock_id": item["stock_id"],
            "is_active": item["is_active"],
            "added_at": item["added_at"],
            "deactivated_at": item.get("deactivated_at"),
            "ticker_nse": s.get("ticker_nse"),
            "ticker_bse": s.get("ticker_bse"),
            "company_name": s.get("company_name"),
            "exchange": s.get("exchange"),
            "sector": s.get("sector"),
            "compute_status": s.get("compute_status"),
            "compute_progress": s.get("compute_progress"),
        }

    return {
        "active": [flatten(i) for i in active],
        "inactive": [flatten(i) for i in inactive],
        "total_active": len(active),
        "limit": WATCHLIST_MAX
    }


@router.post("/me/watchlist")
async def add_to_watchlist(
    req: AddWatchlistRequest,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user)
):
    """Add a stock to watchlist (max 30 active). Rule 3."""
    # Resolve any dynamic yfinance IDs to true Database UUIDs before insertion
    req.stock_id = resolve_stock_id(req.stock_id)

    # Check current active count
    count = supabase.table("watchlists") \
        .select("id", count="exact") \
        .eq("user_id", user["id"]) \
        .eq("is_active", True) \
        .execute()

    if (count.count or 0) >= WATCHLIST_MAX:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {WATCHLIST_MAX} active stocks reached. Deactivate a stock to make room."
        )

    # Verify stock exists and is not suspended
    stock = supabase.table("stocks") \
        .select("id, ticker_nse, company_name, is_suspended, history_fetched") \
        .eq("id", req.stock_id) \
        .maybe_single() \
        .execute()
    if not stock.data:
        raise HTTPException(status_code=404, detail="Stock not found")
    if stock.data.get("is_suspended"):
        raise HTTPException(status_code=400, detail="Stock is suspended and cannot be added to watchlist")

    # Upsert (re-activate if previously deactivated)
    now = datetime.now(timezone.utc).isoformat()
    supabase.table("watchlists").upsert({
        "user_id": user["id"],
        "stock_id": req.stock_id,
        "is_active": True,
        "added_at": now,
        "deactivated_at": None,
    }, on_conflict="user_id,stock_id").execute()

    # Trigger background historical data computation if not already done
    if not stock.data.get("history_fetched"):
        from scan_engine.background_jobs import fetch_and_compute_historical
        background_tasks.add_task(
            fetch_and_compute_historical,
            stock.data["id"],
            stock.data.get("ticker_nse", "")
        )

    return {"message": f"Added {stock.data['ticker_nse'] or stock.data['company_name']} to watchlist"}


def _check_open_position(user_id: str, stock_id: str):
    """Check if user has open position in this stock. Returns 409 if yes."""
    open_pos = supabase.table("positions") \
        .select("id") \
        .eq("user_id", user_id) \
        .eq("stock_id", stock_id) \
        .eq("status", "open") \
        .execute()
    if open_pos.data:
        raise HTTPException(
            status_code=409,
            detail="Cannot deactivate — you have an open position in this stock. Confirm exit first."
        )


@router.patch("/me/watchlist/{stock_id}")
async def update_watchlist_item(stock_id: str, req: UpdateWatchlistRequest, user=Depends(get_current_user)):
    """Activate or deactivate a watchlist entry. 409 if open position exists (Rule 4)."""
    if not req.is_active:
        _check_open_position(user["id"], stock_id)

    now = datetime.now(timezone.utc).isoformat()
    updates = {
        "is_active": req.is_active,
        "deactivated_at": now if not req.is_active else None,
    }
    supabase.table("watchlists").update(updates) \
        .eq("user_id", user["id"]).eq("stock_id", stock_id).execute()

    return {"message": "Watchlist updated"}


@router.delete("/me/watchlist/{stock_id}")
async def delete_watchlist_item(stock_id: str, user=Depends(get_current_user)):
    """
    Deactivate a stock from the watchlist. 409 if open position exists (Rule 4).
    Stocks are deactivated, not deleted, to preserve history.
    """
    _check_open_position(user["id"], stock_id)

    now = datetime.now(timezone.utc).isoformat()
    supabase.table("watchlists").update({
        "is_active": False,
        "deactivated_at": now,
    }).eq("user_id", user["id"]).eq("stock_id", stock_id).execute()

    return {"message": "Stock deactivated from watchlist"}


@router.get("/stocks/search")
async def search_stocks(q: str, imported_only: bool = False, user=Depends(get_current_user)):
    """Search stocks by ticker or company name. Returns up to 15 results."""
    if len(q) < 2:
        return []

    q_upper = q.upper()
    query = supabase.table("stocks") \
        .select("id, ticker_nse, ticker_bse, company_name, exchange, sector, history_fetched, compute_status, compute_progress") \
        .eq("is_active", True) \
        .eq("is_suspended", False)

    if imported_only:
        query = query.eq("history_fetched", True)

    result = query.or_(f"ticker_nse.ilike.%{q_upper}%,company_name.ilike.%{q}%") \
        .limit(15) \
        .execute()

    local_results = result.data or []

    # If imported_only is true, we strictly do NOT poll yfinance
    if imported_only:
        return local_results[:15]

    # If we have space, dynamically poll Yahoo Finance to expand available stocks!
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(
            f"https://query2.finance.yahoo.com/v1/finance/search",
            params={"q": q, "quotesCount": 10},
            headers=headers,
            timeout=4
        )
        if resp.status_code == 200:
            quotes = resp.json().get("quotes", [])
            local_tickers = {s.get("ticker_nse") for s in local_results if s.get("ticker_nse")}
            for qObj in quotes:
                symbol = qObj.get("symbol", "")
                if symbol.endswith(".NS") or symbol.endswith(".BO"):
                    ticker = symbol.replace(".NS", "").replace(".BO", "")
                    if ticker not in local_tickers:
                        local_results.append({
                            "id": f"yfinance:{symbol}",
                            "ticker_nse": ticker,
                            "ticker_bse": ticker if symbol.endswith(".BO") else None,
                            "company_name": qObj.get("longname") or qObj.get("shortname") or ticker,
                            "exchange": "NSE" if symbol.endswith(".NS") else "BSE",
                            "sector": qObj.get("sector", "Unknown"),
                            "history_fetched": False
                        })
                        local_tickers.add(ticker)
    except Exception as e:
        logger.error(f"Yahoo search failed for query '{q}': {e}")

    return local_results[:15]


@router.get("/stocks/imported")
async def get_imported_stocks(user=Depends(get_current_user)):
    """List all stocks that have 10-year historical data ready in the central DB."""
    result = supabase.table("stocks") \
        .select("id, ticker_nse, ticker_bse, company_name, exchange, sector") \
        .eq("history_fetched", True) \
        .order("ticker_nse") \
        .execute()
    return result.data or []


@router.post("/stocks/import/{stock_id}")
async def import_stock_data(stock_id: str, background_tasks: BackgroundTasks, user=Depends(get_current_user)):
    """Trigger a 10-year historical backfill for any stock. Resolves yfinance IDs first."""
    # We run the resolve and compute in the background to avoid frontend timeouts
    background_tasks.add_task(_background_resolve_and_fetch, stock_id)
    return {"message": "Request received. Starting historical hydration in background."}


async def _background_resolve_and_fetch(stock_id: str):
    """Internal helper to resolve ID and trigger fetch without blocking the API response."""
    try:
        from stock_resolver import resolve_stock_id
        from scan_engine.background_jobs import fetch_and_compute_historical
        
        real_id = resolve_stock_id(stock_id)
        stock = supabase.table("stocks").select("*").eq("id", real_id).maybe_single().execute().data
        
        if stock and not stock.get("history_fetched"):
            await fetch_and_compute_historical(
                stock_id=stock["id"], 
                ticker_nse=stock.get("ticker_nse"), 
                ticker_bse=stock.get("ticker_bse")
            )
            logger.info(f"Background hydration initiated for {stock.get('ticker_nse')}")
    except Exception as e:
        logger.error(f"Failed in background import task: {e}")

