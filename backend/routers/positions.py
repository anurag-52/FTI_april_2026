"""
/me/positions routes — Open/closed positions, manual entry, live P&L
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from auth import get_current_user
from config import supabase
from datetime import date, datetime, timezone

router = APIRouter()


class ManualBuyRequest(BaseModel):
    stock_id: str
    entry_date: str  # YYYY-MM-DD
    entry_price: float
    quantity: int
    notes: Optional[str] = None


class ManualSellRequest(BaseModel):
    position_id: str
    exit_price: float
    quantity: Optional[int] = None  # None = close entire position


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
    open_stock_ids = [p["stock_id"] for p in open_positions]
    latest_prices = {}
    trailing_stops = {}

    if open_stock_ids:
        today = str(date.today())
        price_rows = supabase.table("stock_prices") \
            .select("stock_id, close, ch20_low, any_exit_signal") \
            .in_("stock_id", open_stock_ids) \
            .eq("price_date", today) \
            .execute().data or []

        for pr in price_rows:
            latest_prices[pr["stock_id"]] = pr["close"]
            trailing_stops[pr["stock_id"]] = pr.get("ch20_low")

    # Enrich open positions with live P&L
    total_invested = 0
    total_current_value = 0
    total_pnl = 0

    for pos in open_positions:
        stock_id = pos["stock_id"]
        current_price = latest_prices.get(stock_id) or pos["entry_price"]
        current_value = current_price * pos["quantity"]
        pnl = current_value - pos["total_invested"]
        pnl_pct = round((pnl / pos["total_invested"]) * 100, 4) if pos["total_invested"] else 0
        days = (date.today() - date.fromisoformat(pos["entry_date"])).days

        pos["current_price"] = current_price
        pos["current_value"] = round(current_value, 2)
        pos["pnl_amount"] = round(pnl, 2)
        pos["pnl_percent"] = pnl_pct
        pos["days_held"] = days
        pos["trailing_stop"] = trailing_stops.get(stock_id)
        pos["exit_signal_active"] = bool(trailing_stops.get(stock_id) and current_price < trailing_stops[stock_id])

        total_invested += pos["total_invested"] or 0
        total_current_value += current_value
        total_pnl += pnl

    # Summary
    user_data = supabase.table("users").select("available_capital").eq("id", user_id).single().execute().data
    total_pnl_pct = round((total_pnl / total_invested) * 100, 4) if total_invested else 0

    # Get today's session token if exists
    today = str(date.today())
    session = supabase.table("notification_sessions") \
        .select("session_token") \
        .eq("user_id", user_id) \
        .eq("signal_date", today) \
        .maybeSingle() \
        .execute().data

    return {
        "open": open_positions,
        "closed": closed_positions,
        "session_token": session["session_token"] if session else None,
        "summary": {
            "total_invested": round(total_invested, 2),
            "total_current_value": round(total_current_value, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_percent": total_pnl_pct,
            "available_capital": user_data.get("available_capital", 0),
            "slots_used": len(open_positions),
        }
    }


@router.post("/me/positions/manual")
async def add_manual_buy(req: ManualBuyRequest, user=Depends(get_current_user)):
    """Record a manual buy (entered outside of signal system)."""
    if req.quantity <= 0 or req.entry_price <= 0:
        raise HTTPException(status_code=400, detail="Invalid quantity or price")

    # Validate stock
    stock = supabase.table("stocks").select("id, ticker_nse").eq("id", req.stock_id).maybeSingle().execute()
    if not stock.data:
        raise HTTPException(status_code=404, detail="Stock not found")

    total_cost = round(req.quantity * req.entry_price, 2)

    # Check capital
    user_data = supabase.table("users").select("available_capital").eq("id", user["id"]).single().execute().data
    if total_cost > (user_data["available_capital"] or 0):
        raise HTTPException(status_code=400, detail=f"Insufficient capital. Need {total_cost}, have {user_data['available_capital']}")

    new_capital = (user_data["available_capital"] or 0) - total_cost
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
        "notes": req.notes or "Manual entry",
        "source": "MANUAL"
    }).execute()

    return {"message": f"Manual buy recorded: {req.quantity} shares @ ₹{req.entry_price}", "position_id": pos["id"]}


@router.post("/me/positions/manual-sell")
async def add_manual_sell(req: ManualSellRequest, user=Depends(get_current_user)):
    """Record a manual sell."""
    pos = supabase.table("positions") \
        .select("*") \
        .eq("id", req.position_id) \
        .eq("user_id", user["id"]) \
        .eq("status", "open") \
        .maybeSingle() \
        .execute().data

    if not pos:
        raise HTTPException(status_code=404, detail="Open position not found")

    qty = req.quantity or pos["quantity"]
    if qty > pos["quantity"]:
        raise HTTPException(status_code=400, detail="Cannot sell more than held quantity")

    exit_value = round(qty * req.exit_price, 2)
    pnl = round(exit_value - (pos["entry_price"] * qty), 2)
    pnl_pct = round((pnl / (pos["entry_price"] * qty)) * 100, 4)
    days = (date.today() - date.fromisoformat(pos["entry_date"])).days
    now = datetime.now(timezone.utc).isoformat()

    supabase.table("positions").update({
        "status": "closed",
        "exit_date": str(date.today()),
        "exit_price": req.exit_price,
        "exit_reason": "MANUAL",
        "total_exit_value": exit_value,
        "pnl_amount": pnl,
        "pnl_percent": pnl_pct,
        "days_held": days,
        "updated_at": now
    }).eq("id", req.position_id).execute()

    user_data = supabase.table("users").select("available_capital").eq("id", user["id"]).single().execute().data
    new_capital = (user_data["available_capital"] or 0) + exit_value
    supabase.table("users").update({"available_capital": new_capital}).eq("id", user["id"]).execute()

    supabase.table("capital_log").insert({
        "user_id": user["id"],
        "change_type": "SELL",
        "amount": exit_value,
        "balance_after": new_capital,
        "position_id": req.position_id,
        "notes": "Manual sell",
        "source": "MANUAL"
    }).execute()

    return {"message": f"Sale recorded: {qty} shares @ ₹{req.exit_price} | P&L: ₹{pnl}"}
