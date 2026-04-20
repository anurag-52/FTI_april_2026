from config import supabase
import uuid
import logging

logger = logging.getLogger(__name__)

def resolve_stock_id(stock_id: str) -> str:
    """
    If stock_id is a yfinance tag (e.g. yfinance:RELIANCE.NS),
    insert it into the DB if missing, and return its true UUID.
    If it's already a UUID, return it directly.
    """
    if not stock_id.startswith("yfinance:"):
        return stock_id
        
    symbol = stock_id.split("yfinance:")[1]
    ticker = symbol.replace(".NS", "").replace(".BO", "")
    exchange = "NSE" if symbol.endswith(".NS") else "BSE"
    
    try:
        # Check if already exists in DB (to prevent duplicates)
        ext = supabase.table("stocks").select("id").eq("ticker_nse", ticker).execute()
        if ext.data:
            return ext.data[0]["id"]
            
        # Generate UUID and insert
        new_id = str(uuid.uuid4())
        supabase.table("stocks").insert({
            "id": new_id,
            "ticker_nse": ticker,
            "ticker_bse": ticker if exchange == "BSE" else None,
            "company_name": ticker,
            "exchange": exchange,
            "compute_status": "pending",
            "history_fetched": False,
            "is_active": True,
            "is_suspended": False
        }).execute()
        
        logger.info(f"Auto-registered new stock: {ticker} ({exchange}) with ID: {new_id}")
        return new_id
        
    except Exception as e:
        logger.error(f"Failed to auto-register stock {symbol}: {str(e)}")
        # Fallback: Just return the string and let the calling function crash
        return stock_id
