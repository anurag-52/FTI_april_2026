"""
/me/positions routes — Open/closed positions, manual buy/sell, live P&L

Business Rules:
- Manual trade entry available anytime independent of signals (tagged MANUAL)
- Partial sell creates remainder position
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from auth import get_current_user
from config import supabase
from datetime import date, datetime, timezone
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class ManualBuyRequest(BaseModel):
    stock_id: str
    entry_date: str  # YYYY-MM-DD
    entry_price: float
    quantity: int
    notes: Optional[str] = None


class ManualSellRequest(BaseModel):
    position_id: str
    exit_date: Optional[str] = None  # YYYY-MM-DD, defaults to today
    exit_price: float
    quantity: Optional[int] = None  # None = close entire position
    notes: Optional[str] = None


@router.get("/me/positions")
async def get_positions(user=Depends(get_current_user)):
    """Get open and closed positions with live P&L."""
    user_id = user["id"]

    open_positions = supabase.table("positions") \
        .select("*, stocks(id, ticker_nse, company_name)") \
        .eq("user_id", user_id) \
        .eq("status", "open") \
        .order("entry_date", desc=True) \
        .execute().data or []

    closed_positions = supabase.table("positions") \
        .select("*, stocks(id, ticker_nse, company_name)") \
        .eq("user_id", user_id) \
        .eq("status", "closed") \
        .order("exit_date", desc=True) \
        .limit(50) \
        .execute().data or []

    # Get latest prices for open positions
    open_stock_ids = list(set(p["stock_id"] for p in open_positions))
    latest_prices = {}
    trailing_stops = {}
    exit_signals_active = {}

    if open_stock_ids:
        today_str = str(date.today())
        price_rows = supabase.table("stock_prices") \
            .select("stock_id, close, ch20_low, any_exit_signal") \
            .in_("stock_id", open_stock_ids) \
            .eq("price_date", today_str) \
            .execute().data or []

        for pr in price_rows:
            latest_prices[pr["stock_id"]] = float(pr["close"]) if pr["close"] else None
            trailing_stops[pr["stock_id"]] = float(pr["ch20_low"]) if pr.get("ch20_low") else None
            exit_signals_active[pr["stock_id"]] = bool(pr.get("any_exit_signal"))

    # Enrich open positions with live P&L
    total_invested = 0
    total_current_value = 0
    total_pnl = 0

    for pos in open_positions:
        stock_id = pos["stock_id"]
        current_price = latest_prices.get(stock_id) or float(pos["entry_price"])
        qty = pos["quantity"]
        invested = float(pos["total_invested"] or (float(pos["entry_price"]) * qty))
        current_value = current_price * qty
        pnl = current_value - invested
        pnl_pct = round((pnl / invested) * 100, 4) if invested else 0
        days = (date.today() - date.fromisoformat(pos["entry_date"])).days

        pos["current_price"] = round(current_price, 2)
        pos["current_value"] = round(current_value, 2)
        pos["pnl_amount"] = round(pnl, 2)
        pos["pnl_percent"] = pnl_pct
        pos["days_held"] = days
        pos["trailing_stop"] = trailing_stops.get(stock_id)
        pos["exit_signal_active"] = exit_signals_active.get(stock_id, False)

        total_invested += invested
        total_current_value += current_value
        total_pnl += pnl

    # Summary
    total_pnl_pct = round((total_pnl / total_invested) * 100, 4) if total_invested else 0

    # Get today's session token if exists
    today_str = str(date.today())
    session = supabase.table("notification_sessions") \
        .select("session_token, submitted") \
        .eq("user_id", user_id) \
        .eq("signal_date", today_str) \
        .maybe_single() \
        .execute().data

    return {
        "open": open_positions,
        "closed": closed_positions,
        "session_token": session["session_token"] if session else None,
        "session_submitted": session["submitted"] if session else None,
        "summary": {
            "total_invested": round(total_invested, 2),
            "total_current_value": round(total_current_value, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_percent": total_pnl_pct,
            "available_capital": float(user.get("available_capital", 0) or 0),
            "open_positions_count": len(open_positions),
        }
    }


@router.post("/me/positions/manual")
async def add_manual_buy(req: ManualBuyRequest, user=Depends(get_current_user)):
    """Record a manual buy (entered outside of signal system). Tagged with source=MANUAL (🖊️)."""
    if req.quantity <= 0 or req.entry_price <= 0:
        raise HTTPException(status_code=400, detail="Invalid quantity or price")

    # Validate stock exists
    stock = supabase.table("stocks").select("id, ticker_nse").eq("id", req.stock_id).maybe_single().execute()
    if not stock.data:
        raise HTTPException(status_code=404, detail="Stock not found")

    total_cost = round(req.quantity * req.entry_price, 2)

    # Check capital
    available = float(user.get("available_capital") or 0)
    if total_cost > available:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient capital. Need ₹{total_cost:,.2f}, have ₹{available:,.2f}"
        )

    new_capital = available - total_cost
    now = datetime.now(timezone.utc).isoformat()

    pos = supabase.table("positions").insert({
        "user_id": user["id"],
        "stock_id": req.stock_id,
        "entry_date": req.entry_date,
        "entry_price": req.entry_price,
        "quantity": req.quantity,
        "total_invested": total_cost,
        "source": "MANUAL",
        "status": "open",
    }).execute().data[0]

    supabase.table("users").update({"available_capital": new_capital}).eq("id", user["id"]).execute()

    supabase.table("capital_log").insert({
        "user_id": user["id"],
        "change_type": "BUY",
        "amount": -total_cost,
        "balance_after": new_capital,
        "position_id": pos["id"],
        "notes": req.notes or "Manual buy entry 🖊️",
        "changed_by": user["id"],
        "source": "MANUAL",
    }).execute()

    logger.info(f"Manual buy: {req.quantity} shares of {stock.data['ticker_nse']} @ ₹{req.entry_price}")
    return {
        "message": f"Manual buy recorded: {req.quantity} shares @ ₹{req.entry_price}",
        "position_id": pos["id"],
    }


@router.post("/me/positions/manual-sell")
async def add_manual_sell(req: ManualSellRequest, user=Depends(get_current_user)):
    """
    Record a manual sell. Supports partial sells.
    - Full sell: closes the position
    - Partial sell: reduces qty on original, creates capital log for partial
    """
    pos = supabase.table("positions") \
        .select("*") \
        .eq("id", req.position_id) \
        .eq("user_id", user["id"]) \
        .eq("status", "open") \
        .maybe_single() \
        .execute().data

    if not pos:
        raise HTTPException(status_code=404, detail="Open position not found")

    sell_qty = req.quantity or pos["quantity"]
    if sell_qty > pos["quantity"]:
        raise HTTPException(status_code=400, detail="Cannot sell more than held quantity")
    if sell_qty <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")

    exit_date_str = req.exit_date or str(date.today())
    exit_value = round(sell_qty * req.exit_price, 2)
    entry_cost = round(float(pos["entry_price"]) * sell_qty, 2)
    pnl = round(exit_value - entry_cost, 2)
    pnl_pct = round((pnl / entry_cost) * 100, 4) if entry_cost else 0
    days = (date.fromisoformat(exit_date_str) - date.fromisoformat(pos["entry_date"])).days
    now = datetime.now(timezone.utc).isoformat()

    available = float(user.get("available_capital") or 0)

    if sell_qty == pos["quantity"]:
        # Full sell — close the position
        supabase.table("positions").update({
            "status": "closed",
            "exit_date": exit_date_str,
            "exit_price": req.exit_price,
            "exit_reason": "MANUAL",
            "total_exit_value": exit_value,
            "pnl_amount": pnl,
            "pnl_percent": pnl_pct,
            "days_held": days,
            "updated_at": now,
        }).eq("id", req.position_id).execute()

        change_type = "SELL"
    else:
        # Partial sell — reduce quantity on original position
        remaining_qty = pos["quantity"] - sell_qty
        remaining_invested = round(float(pos["entry_price"]) * remaining_qty, 2)

        supabase.table("positions").update({
            "quantity": remaining_qty,
            "total_invested": remaining_invested,
            "updated_at": now,
        }).eq("id", req.position_id).execute()

        change_type = "PARTIAL_SELL"

    new_capital = available + exit_value
    supabase.table("users").update({"available_capital": new_capital}).eq("id", user["id"]).execute()

    supabase.table("capital_log").insert({
        "user_id": user["id"],
        "change_type": change_type,
        "amount": exit_value,
        "balance_after": new_capital,
        "position_id": req.position_id,
        "notes": req.notes or f"Manual {'sell' if sell_qty == pos['quantity'] else 'partial sell'} 🖊️",
        "changed_by": user["id"],
        "source": "MANUAL",
    }).execute()

    return {
        "message": f"{'Full' if sell_qty == pos['quantity'] else 'Partial'} sell recorded: {sell_qty} shares @ ₹{req.exit_price} | P&L: ₹{pnl}",
    }
