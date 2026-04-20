"""
AGENT 3 — SCAN ENGINE
data_fetcher.py

3-Source Data Cascade for EOD OHLCV data:
  Tier 1: yfinance  (primary, no API key)
  Tier 2: NSE Bhavcopy ZIP  (official NSE data)
  Tier 3: BSE Bhavcopy ZIP  (official BSE data)

Every fetch attempt is logged to data_source_log table.
Retry scheduling (15-min intervals) is managed by the caller (scan_runner).
"""
import yfinance as yf
import pandas as pd
import requests
import zipfile
import io
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional, List

logger = logging.getLogger(__name__)

# ─── Constants ───────────────────────────────────────────────────────────────

REQUIRED_COLS = ["date", "open", "high", "low", "close", "volume"]

NSE_BHAVCOPY_URL = (
    "https://archives.nseindia.com/content/historical/EQUITIES/{year}/{mon}/"
    "cm{day}{mon}{year}bhav.csv.zip"
)
BSE_BHAVCOPY_URL = "https://www.bseindia.com/download/BhavCopy/Equity/EQ{dt_str}_CSV.ZIP"

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


# ─── Data Source Logging ─────────────────────────────────────────────────────

def _log_data_source(supabase, fetch_date: date, stock_id: Optional[str],
                     source: str, attempt: int, status: str,
                     error_msg: Optional[str] = None,
                     triggered_by: str = "AUTO",
                     triggered_by_user: Optional[str] = None):
    """Write every fetch attempt to data_source_log for admin visibility."""
    try:
        supabase.table("data_source_log").insert({
            "fetch_date": str(fetch_date),
            "stock_id": stock_id,
            "source": source,
            "attempt_number": attempt,
            "status": status,
            "error_message": error_msg,
            "triggered_by": triggered_by,
            "triggered_by_user": triggered_by_user,
        }).execute()
    except Exception as e:
        logger.error(f"Failed to log data source attempt: {e}")


# ─── Tier 1: yfinance ───────────────────────────────────────────────────────

def fetch_ohlcv_yfinance(
    ticker_nse: Optional[str],
    ticker_bse: Optional[str],
    from_date: date,
    to_date: date,
) -> Optional[pd.DataFrame]:
    """
    Fetch OHLCV data from yfinance.
    Tries NSE (.NS suffix) first, then BSE (.BO suffix) if NSE fails.
    Returns standardized DataFrame sorted by date, or None on failure.
    """
    symbols_to_try = []
    if ticker_nse:
        symbols_to_try.append(f"{ticker_nse}.NS")
    if ticker_bse:
        symbols_to_try.append(f"{ticker_bse}.BO")
    # If no BSE ticker but NSE given, also try .BO with same ticker
    if ticker_nse and not ticker_bse:
        symbols_to_try.append(f"{ticker_nse}.BO")

    for symbol in symbols_to_try:
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(
                start=from_date.strftime("%Y-%m-%d"),
                end=(to_date + timedelta(days=1)).strftime("%Y-%m-%d"),
                auto_adjust=True,
                timeout=30,
            )
            if df is not None and not df.empty:
                df = df.reset_index()
                df.columns = [c.lower() for c in df.columns]
                df["date"] = pd.to_datetime(df["date"]).dt.date
                df = df[["date", "open", "high", "low", "close", "volume"]]
                df = df.dropna(subset=["close"])
                df = df.sort_values("date").reset_index(drop=True)
                logger.info(f"yfinance: fetched {len(df)} rows for {symbol}")
                return df
        except Exception as e:
            logger.warning(f"yfinance attempt for {symbol} failed: {e}")
            continue

    return None


# ─── Tier 2: NSE Bhavcopy ───────────────────────────────────────────────────

def fetch_nse_bhavcopy(target_date: date) -> Optional[pd.DataFrame]:
    """
    Download NSE Bhavcopy ZIP for a given date.
    Returns DataFrame with columns [ticker, date, open, high, low, close, volume]
    for ALL EQ-series stocks on that date, or None if unavailable.
    """
    try:
        mon = target_date.strftime("%b").upper()
        day = target_date.strftime("%d")
        year = target_date.strftime("%Y")
        url = NSE_BHAVCOPY_URL.format(year=year, mon=mon, day=day)

        resp = requests.get(url, headers=BROWSER_HEADERS, timeout=30)
        if resp.status_code != 200:
            logger.warning(f"NSE Bhavcopy HTTP {resp.status_code} for {target_date}")
            return None

        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            csv_files = [n for n in z.namelist() if n.endswith(".csv")]
            if not csv_files:
                return None
            df = pd.read_csv(z.open(csv_files[0]))

        df.columns = [c.strip().upper() for c in df.columns]

        # Filter to EQ series only (ignore derivatives, ETFs marked differently)
        if "SERIES" in df.columns:
            df = df[df["SERIES"].str.strip() == "EQ"]

        df = df.rename(columns={
            "SYMBOL": "ticker",
            "OPEN": "open",
            "HIGH": "high",
            "LOW": "low",
            "CLOSE": "close",
            "TOTTRDQTY": "volume",
        })
        df["date"] = target_date

        required = ["ticker", "date", "open", "high", "low", "close", "volume"]
        for col in required:
            if col not in df.columns:
                logger.warning(f"NSE Bhavcopy missing column: {col}")
                return None

        df = df[required].dropna(subset=["close"])
        logger.info(f"NSE Bhavcopy: {len(df)} EQ rows for {target_date}")
        return df

    except Exception as e:
        logger.error(f"NSE Bhavcopy error for {target_date}: {e}")
        return None


# ─── Tier 3: BSE Bhavcopy ───────────────────────────────────────────────────

def fetch_bse_bhavcopy(target_date: date) -> Optional[pd.DataFrame]:
    """
    Download BSE Bhavcopy for a given date.
    Returns DataFrame with columns [sc_code, sc_name, date, open, high, low, close, volume]
    for all stocks, or None if unavailable.
    """
    try:
        dt_str = target_date.strftime("%d%m%y")
        url = BSE_BHAVCOPY_URL.format(dt_str=dt_str)

        headers = {**BROWSER_HEADERS, "Referer": "https://www.bseindia.com"}
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            logger.warning(f"BSE Bhavcopy HTTP {resp.status_code} for {target_date}")
            return None

        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            csv_files = [n for n in z.namelist()
                         if n.upper().endswith(".CSV")]
            if not csv_files:
                return None
            df = pd.read_csv(z.open(csv_files[0]))

        df.columns = [c.strip().upper() for c in df.columns]
        df = df.rename(columns={
            "SC_CODE": "sc_code",
            "SC_NAME": "sc_name",
            "OPEN": "open",
            "HIGH": "high",
            "LOW": "low",
            "CLOSE": "close",
            "NO_OF_SHRS": "volume",
        })
        df["date"] = target_date

        required = ["sc_code", "date", "open", "high", "low", "close", "volume"]
        for col in required:
            if col not in df.columns:
                logger.warning(f"BSE Bhavcopy missing column: {col}")
                return None

        df = df[required].dropna(subset=["close"])
        logger.info(f"BSE Bhavcopy: {len(df)} rows for {target_date}")
        return df

    except Exception as e:
        logger.error(f"BSE Bhavcopy error for {target_date}: {e}")
        return None


# ─── Single-Stock EOD Fetch (with cascade + logging) ────────────────────────

def fetch_stock_eod(
    supabase,
    stock: dict,
    target_date: date,
    triggered_by: str = "AUTO",
    triggered_by_user: Optional[str] = None,
) -> dict:
    """
    Fetch today's EOD data for a single stock using the 3-tier cascade.
    Does NOT do retry scheduling — only attempts each tier once.
    The 15-min retry loop is managed by scan_runner.

    Args:
        supabase: Supabase client
        stock: dict with keys: id, ticker_nse, ticker_bse, exchange
        target_date: the trading date to fetch
        triggered_by: 'AUTO', 'ADMIN', or 'TRADER'
        triggered_by_user: UUID of the user who triggered (for ADMIN/TRADER)

    Returns:
        {
            "data": DataFrame or None,
            "source": "yfinance" | "nse_bhavcopy" | "bse_bhavcopy" | None,
            "error": str or None,
        }
    """
    stock_id = stock["id"]
    ticker_nse = stock.get("ticker_nse")
    ticker_bse = stock.get("ticker_bse")

    # ── Tier 1: yfinance ──────────────────────────────────────────────────
    _log_data_source(supabase, target_date, stock_id, "yfinance", 1,
                     "retrying", triggered_by=triggered_by,
                     triggered_by_user=triggered_by_user)

    # Fetch enough history for indicator computation (need 120 days for 55-day channel + ADX warmup)
    from_date = target_date - timedelta(days=180)
    df = fetch_ohlcv_yfinance(ticker_nse, ticker_bse, from_date, target_date)
    if df is not None and not df.empty:
        _log_data_source(supabase, target_date, stock_id, "yfinance", 1,
                         "success", triggered_by=triggered_by,
                         triggered_by_user=triggered_by_user)
        return {"data": df, "source": "yfinance", "error": None}

    _log_data_source(supabase, target_date, stock_id, "yfinance", 1,
                     "failed", error_msg="No data returned",
                     triggered_by=triggered_by,
                     triggered_by_user=triggered_by_user)

    # ── Tier 2: NSE Bhavcopy ─────────────────────────────────────────────
    if ticker_nse:
        _log_data_source(supabase, target_date, stock_id, "nse_bhavcopy", 2,
                         "retrying", triggered_by=triggered_by,
                         triggered_by_user=triggered_by_user)

        nse_df = fetch_nse_bhavcopy(target_date)
        if nse_df is not None:
            stock_rows = nse_df[nse_df["ticker"] == ticker_nse]
            if not stock_rows.empty:
                result_df = stock_rows.drop(columns=["ticker"]).reset_index(drop=True)
                _log_data_source(supabase, target_date, stock_id, "nse_bhavcopy", 2,
                                 "success", triggered_by=triggered_by,
                                 triggered_by_user=triggered_by_user)
                return {"data": result_df, "source": "nse_bhavcopy", "error": None}

        _log_data_source(supabase, target_date, stock_id, "nse_bhavcopy", 2,
                         "failed", error_msg="Stock not found in Bhavcopy",
                         triggered_by=triggered_by,
                         triggered_by_user=triggered_by_user)

    # ── Tier 3: BSE Bhavcopy ─────────────────────────────────────────────
    if ticker_bse:
        _log_data_source(supabase, target_date, stock_id, "bse_bhavcopy", 3,
                         "retrying", triggered_by=triggered_by,
                         triggered_by_user=triggered_by_user)

        bse_df = fetch_bse_bhavcopy(target_date)
        if bse_df is not None:
            stock_rows = bse_df[bse_df["sc_code"].astype(str) == str(ticker_bse)]
            if not stock_rows.empty:
                result_df = stock_rows.drop(columns=["sc_code", "sc_name"],
                                            errors="ignore").reset_index(drop=True)
                _log_data_source(supabase, target_date, stock_id, "bse_bhavcopy", 3,
                                 "success", triggered_by=triggered_by,
                                 triggered_by_user=triggered_by_user)
                return {"data": result_df, "source": "bse_bhavcopy", "error": None}

        _log_data_source(supabase, target_date, stock_id, "bse_bhavcopy", 3,
                         "failed", error_msg="Stock not found in BSE Bhavcopy",
                         triggered_by=triggered_by,
                         triggered_by_user=triggered_by_user)

    error = f"All 3 sources failed for {ticker_nse or ticker_bse} on {target_date}"
    logger.error(error)
    return {"data": None, "source": None, "error": error}


# ─── Historical Data Fetch (for new stocks — 10 years) ──────────────────────

def fetch_historical(
    ticker_nse: Optional[str],
    ticker_bse: Optional[str],
    years: int = 10,
) -> Optional[pd.DataFrame]:
    """
    Fetch up to 10 years of historical OHLCV data for a newly added stock.
    Used by background_jobs.py when a stock is first added to any watchlist.
    Only uses yfinance (Bhavcopy archives are not reliably available for 10yr).
    """
    to_date = date.today()
    from_date = to_date - timedelta(days=years * 365)

    df = fetch_ohlcv_yfinance(ticker_nse, ticker_bse, from_date, to_date)
    if df is not None:
        logger.info(
            f"Historical fetch: {len(df)} rows for "
            f"{ticker_nse or ticker_bse} from {from_date} to {to_date}"
        )
    return df


# ─── Get existing price history from DB ─────────────────────────────────────

def get_existing_prices(supabase, stock_id: str, from_date: date,
                        to_date: date) -> pd.DataFrame:
    """
    Retrieve already-stored price data from stock_prices table.
    Used to assemble the rolling window needed for indicator computation
    without re-fetching from yfinance.
    """
    result = supabase.table("stock_prices") \
        .select("price_date, open, high, low, close, volume") \
        .eq("stock_id", stock_id) \
        .gte("price_date", str(from_date)) \
        .lte("price_date", str(to_date)) \
        .order("price_date") \
        .execute()

    if not result.data:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

    df = pd.DataFrame(result.data)
    df = df.rename(columns={"price_date": "date"})
    df["date"] = pd.to_datetime(df["date"]).dt.date
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0).astype(int)
    return df.sort_values("date").reset_index(drop=True)
