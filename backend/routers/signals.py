"""
/me/signals routes — Today's signals, signal history, confirmation submission
/confirm/:token — Token-based confirmation (no auth, via WhatsApp/Email link)

Business Rules:
- SUBMIT requires ALL rows actioned (Rule 5)
- EXIT signal → ALL positions in that stock exit simultaneously (Rule 6)
- Once SUBMIT clicked → all entries locked permanently for that day (Rule 5)
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from auth import get_current_user
from config import supabase
from datetime import date, datetime, timezone
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Exit type mapping: signal_type → positions.exit_reason (must match DB CHECK constraint)
EXIT_REASON_MAP = {
    "EXIT_REJECTION": "REJECTION_RULE",
    "EXIT_TRAILING": "TRAILING_STOP",
    "EXIT_ADX": "ADX_EXIT",
}


# ─── Signal views ────────────────────────────────────────────────────────────

@router.get("/me/signals/today")
async def get_signals_today(user=Depends(get_current_user)):
    """Get today's signals + session state."""
    today = str(date.today())

    session = supabase.table("notification_sessions") \
        .select("*") \
        .eq("user_id", user["id"]) \
        .eq("signal_date", today) \
        .maybeSingle() \
        .execute().data

    if not session:
        return {
            "has_signals": False,
            "submitted": False,
            "total_rows": 0,
            "actioned_rows": 0,
            "buy_signals": [],
            "exit_signals": [],
        }

    # Get signals with stock info
    signals = supabase.table("signals") \
        .select("*, stocks(id, ticker_nse, company_name)") \
        .eq("user_id", user["id"]) \
        .eq("signal_date", today) \
        .execute().data or []

    buy_signals  = [s for s in signals if s["signal_type"] == "BUY"]
    exit_signals = [s for s in signals if s["signal_type"].startswith("EXIT")]

    # Enrich exit signals with open position data
    for s in exit_signals:
        positions = supabase.table("positions") \
            .select("id, entry_date, entry_price, quantity, total_invested") \
            .eq("user_id", user["id"]) \
            .eq("stock_id", s["stock_id"]) \
            .eq("status", "open") \
            .execute().data or []
        s["open_positions"] = positions
        s["total_qty"] = sum(p.get("quantity", 0) for p in positions)
        if positions:
            total_invested = sum(p["entry_price"] * p["quantity"] for p in positions)
            avg_entry = total_invested / s["total_qty"] if s["total_qty"] else 0
            s["estimated_pnl"] = round((s["trigger_price"] - avg_entry) * s["total_qty"], 2)
            s["entry_value"] = round(total_invested, 2)

    return {
        **session,
        "signal_date": today,
        "user_name": user["full_name"],
        "buy_signals": buy_signals,
        "exit_signals": exit_signals,
    }


@router.get("/me/signals/history")
async def get_signal_history(user=Depends(get_current_user)):
    """Get last 90 days of signals."""
    result = supabase.table("signals") \
        .select("*, stocks(ticker_nse, company_name)") \
        .eq("user_id", user["id"]) \
        .order("signal_date", desc=True) \
        .limit(200) \
        .execute()
    return result.data or []


# ─── Confirmation submission ──────────────────────────────────────────────────

class ConfirmItem(BaseModel):
    signal_id: str
    actioned: bool   # True = "I Bought/Sold It", False = "I Did Not"
    qty: Optional[int] = None
    price: Optional[float] = None


class ConfirmRequest(BaseModel):
    session_token: str
    confirmations: List[ConfirmItem]


@router.post("/me/signals/confirm")
async def submit_confirmations(req: ConfirmRequest, user=Depends(get_current_user)):
    """Submit confirmations for today's signals (authenticated trader). Rule 5."""
    session = supabase.table("notification_sessions") \
        .select("*") \
        .eq("session_token", req.session_token) \
        .eq("user_id", user["id"]) \
        .maybeSingle() \
        .execute().data

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.get("submitted"):
        raise HTTPException(status_code=400, detail="Session already submitted — entries are permanently locked")

    return await _process_confirmations(session, req.confirmations, user["id"])


# ─── Token-based confirmation (no-auth, via email/WhatsApp link) ──────────────

@router.get("/confirm/{token}")
async def get_session_by_token(token: str):
    """Get session and signals by notification token (no auth). Permanent link."""
    session = supabase.table("notification_sessions") \
        .select("*") \
        .eq("session_token", token) \
        .maybeSingle() \
        .execute().data

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check if user is paused/suspended — deactivate link
    user = supabase.table("users") \
        .select("full_name, email, status") \
        .eq("id", session["user_id"]) \
        .single() \
        .execute().data

    if user["status"] == "suspended":
        raise HTTPException(status_code=403, detail="Account suspended. Contact admin.")
    if user["status"] == "paused":
        # Paused users CAN still access link to reactivate by confirming
        pass

    signals = supabase.table("signals") \
        .select("*, stocks(id, ticker_nse, company_name)") \
        .eq("user_id", session["user_id"]) \
        .eq("signal_date", session["signal_date"]) \
        .execute().data or []

    # For exit signals, fetch open positions in the relevant stocks
    exit_signal_stock_ids = {s["stock_id"] for s in signals if s["signal_type"].startswith("EXIT")}
    open_positions = {}
    if exit_signal_stock_ids:
        positions = supabase.table("positions") \
            .select("stock_id, id, entry_date, entry_price, quantity, total_invested") \
            .eq("user_id", session["user_id"]) \
            .eq("status", "open") \
            .in_("stock_id", list(exit_signal_stock_ids)) \
            .execute().data or []
        for p in positions:
            open_positions.setdefault(p["stock_id"], []).append(p)

    # Enrich exit signals with position data
    for s in signals:
        if s["signal_type"].startswith("EXIT"):
            pos = open_positions.get(s["stock_id"], [])
            s["open_positions"] = pos
            s["total_qty"] = sum(p.get("quantity", 0) for p in pos)
            if pos:
                total_invested = sum(p["entry_price"] * p["quantity"] for p in pos)
                avg_entry = total_invested / s["total_qty"] if s["total_qty"] else 0
                s["estimated_pnl"] = round((s["trigger_price"] - avg_entry) * s["total_qty"], 2)
                s["entry_value"] = round(total_invested, 2)

    buy_signals  = [s for s in signals if s["signal_type"] == "BUY"]
    exit_signals = [s for s in signals if s["signal_type"].startswith("EXIT")]

    return {
        **session,
        "user_name": user["full_name"],
        "user_status": user["status"],
        "buy_signals": buy_signals,
        "exit_signals": exit_signals,
    }


class TokenConfirmRequest(BaseModel):
    confirmations: List[ConfirmItem]


@router.post("/confirm/{token}/submit")
async def submit_by_token(token: str, req: TokenConfirmRequest):
    """Submit confirmations via WhatsApp/Email link token (no auth). Rule 5."""
    session = supabase.table("notification_sessions") \
        .select("*") \
        .eq("session_token", token) \
        .maybeSingle() \
        .execute().data

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.get("is_active"):
        raise HTTPException(status_code=400, detail="Session is no longer active")
    if session.get("submitted"):
        raise HTTPException(status_code=400, detail="Already submitted — entries are permanently locked")

    return await _process_confirmations(session, req.confirmations, session["user_id"])


# ─── Shared confirmation processor ───────────────────────────────────────────

async def _process_confirmations(session: dict, confirmations: list, user_id: str):
    """
    Process signal confirmations, update positions and capital.
    
    Rule 5: ALL rows must be actioned before SUBMIT is accepted.
    Rule 6: EXIT signal → ALL positions in that stock exit simultaneously.
    """
    # RULE 5: Validate that ALL signal rows have been actioned
    total_signals = session.get("total_rows", 0)
    if len(confirmations) < total_signals:
        raise HTTPException(
            status_code=400,
            detail=f"All {total_signals} signals must be actioned. You provided {len(confirmations)}."
        )

    now = datetime.now(timezone.utc).isoformat()
    actioned_count = 0

    for item in confirmations:
        signal = supabase.table("signals") \
            .select("*") \
            .eq("id", item.signal_id) \
            .eq("user_id", user_id) \
            .maybeSingle() \
            .execute().data

        if not signal:
            continue

        # Update signal confirmation status — BOTH "I did it" and "I did not" count as actioned
        supabase.table("signals").update({
            "confirmed": item.actioned,
            "confirmed_at": now,
            "confirmed_qty": item.qty,
            "confirmed_price": item.price,
        }).eq("id", item.signal_id).execute()

        # Every row counts as actioned (both "bought" and "did not buy")
        actioned_count += 1

        # Only process position changes if trader DID act
        if item.actioned:
            if signal["signal_type"] == "BUY" and item.qty and item.price:
                await _open_position(user_id, signal, item)

            elif signal["signal_type"].startswith("EXIT") and item.price:
                await _close_positions(user_id, signal, item)

    # Update session — PERMANENTLY LOCKED
    supabase.table("notification_sessions").update({
        "actioned_rows": actioned_count,
        "submitted": True,
        "submitted_at": now,
        "is_active": False,
    }).eq("id", session["id"]).execute()

    # Reset inactivity counter — trader responded!
    supabase.table("users").update({
        "inactivity_days": 0,
        "confirmation_pending": False,
        "last_confirmed_at": now,
        "warned_day5": False,
        "warned_day12": False,
    }).eq("id", user_id).execute()

    return {
        "status": "submitted",
        "actioned": actioned_count,
        "total": total_signals,
        "message": "All confirmations locked permanently for this day."
    }


async def _open_position(user_id: str, signal: dict, item):
    """Open a new position from a BUY signal confirmation."""
    total_cost = round(item.qty * item.price, 2)
    now = datetime.now(timezone.utc).isoformat()

    # Deduct capital
    user = supabase.table("users").select("available_capital").eq("id", user_id).single().execute().data
    current_capital = float(user["available_capital"] or 0)
    new_capital = current_capital - total_cost

    if new_capital < 0:
        logger.warning(f"User {user_id} has insufficient capital for BUY. Proceeding anyway (trader confirmed).")
        new_capital = 0

    supabase.table("users").update({"available_capital": new_capital}).eq("id", user_id).execute()

    # Insert position
    pos = supabase.table("positions").insert({
        "user_id": user_id,
        "stock_id": signal["stock_id"],
        "signal_id": signal["id"],
        "entry_date": str(signal.get("signal_date", date.today())),
        "entry_price": item.price,
        "quantity": item.qty,
        "total_invested": total_cost,
        "source": "SIGNAL",
        "status": "open",
    }).execute().data[0]

    # Capital log
    supabase.table("capital_log").insert({
        "user_id": user_id,
        "change_type": "BUY",
        "amount": -total_cost,
        "balance_after": new_capital,
        "position_id": pos["id"],
        "signal_id": signal["id"],
        "changed_by": user_id,
        "source": "SIGNAL",
    }).execute()

    logger.info(f"Position opened: {item.qty} shares @ ₹{item.price} for user {user_id}")


async def _close_positions(user_id: str, signal: dict, item):
    """
    Close ALL open positions in this stock from EXIT signal confirmation.
    Rule 6: Any EXIT signal → ALL positions in that stock exit simultaneously.
    """
    open_positions = supabase.table("positions") \
        .select("*") \
        .eq("user_id", user_id) \
        .eq("stock_id", signal["stock_id"]) \
        .eq("status", "open") \
        .execute().data or []

    if not open_positions:
        return

    user = supabase.table("users").select("available_capital").eq("id", user_id).single().execute().data
    current_capital = float(user["available_capital"] or 0)
    now = datetime.now(timezone.utc).isoformat()

    # Map signal_type to exit_reason (matching DB CHECK constraint)
    exit_reason = EXIT_REASON_MAP.get(signal["signal_type"], "MANUAL")

    for pos in open_positions:
        qty = pos["quantity"]
        exit_value = round(qty * item.price, 2)
        invested = float(pos["total_invested"] or (pos["entry_price"] * qty))
        pnl_amount = round(exit_value - invested, 2)
        pnl_pct = round((pnl_amount / invested) * 100, 4) if invested else 0
        days = (date.today() - date.fromisoformat(pos["entry_date"])).days

        supabase.table("positions").update({
            "status": "closed",
            "exit_date": str(signal.get("signal_date", date.today())),
            "exit_price": item.price,
            "exit_reason": exit_reason,
            "exit_signal_id": signal["id"],
            "total_exit_value": exit_value,
            "pnl_amount": pnl_amount,
            "pnl_percent": pnl_pct,
            "days_held": days,
            "gap_risk_on_exit": signal.get("gap_risk_warning", False),
            "updated_at": now,
        }).eq("id", pos["id"]).execute()

        # Add exit proceeds back to capital
        current_capital += exit_value
        supabase.table("users").update({"available_capital": current_capital}).eq("id", user_id).execute()

        supabase.table("capital_log").insert({
            "user_id": user_id,
            "change_type": "SELL",
            "amount": exit_value,
            "balance_after": current_capital,
            "position_id": pos["id"],
            "signal_id": signal["id"],
            "changed_by": user_id,
            "source": "SIGNAL",
        }).execute()

    logger.info(f"Closed {len(open_positions)} positions in stock {signal['stock_id']} for user {user_id}")
