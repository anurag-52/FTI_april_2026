"""
AGENT 5 — INTEGRATIONS-ENG
bse_bhavcopy.py — BSE Bhavcopy CSV parser (Tier 3 backup data source)

Downloads and parses the daily BSE Bhavcopy file:
  URL pattern: https://www.bseindia.com/download/BhseCsv/Equity/EQ{DDMMYY}_CSV.ZIP

Output: pandas DataFrame compatible with stock_prices schema columns:
  ticker_bse, company_name, price_date, open, high, low, close, volume
"""

import io
import logging
import zipfile
from datetime import date
from typing import Optional

import httpx
import pandas as pd

logger = logging.getLogger(__name__)

# ── BSE URL Templates ────────────────────────────────────────────────────────
BSE_BHAVCOPY_URL = (
    "https://www.bseindia.com/download/BhavCopy/Equity/EQ{ddmmyy}_CSV.ZIP"
)

# Alternative URL pattern
BSE_BHAVCOPY_ALT_URL = (
    "https://www.bseindia.com/download/BhavCopy/Equity/eq{ddmmyy}_csv.zip"
)

# Another variation used by BSE
BSE_BHAVCOPY_V2_URL = (
    "https://www.bseindia.com/download/BhavCopy/Equity/BhavCopy_BSE_CM_0_0_0_{yyyymmdd}_F_0000.CSV"
)

BSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.bseindia.com/",
}


# ── Download + Parse ─────────────────────────────────────────────────────────

def _build_url(fetch_date: date, variant: int = 0) -> str:
    """Build the BSE bhavcopy download URL for a given date."""
    ddmmyy = fetch_date.strftime("%d%m%y")  # e.g. 180426
    yyyymmdd = fetch_date.strftime("%Y%m%d")  # e.g. 20260418

    if variant == 0:
        return BSE_BHAVCOPY_URL.format(ddmmyy=ddmmyy)
    elif variant == 1:
        return BSE_BHAVCOPY_ALT_URL.format(ddmmyy=ddmmyy)
    else:
        return BSE_BHAVCOPY_V2_URL.format(yyyymmdd=yyyymmdd)


def _download_file(url: str) -> Optional[bytes]:
    """Download file from BSE, returning raw bytes or None."""
    try:
        with httpx.Client(
            timeout=30.0,
            headers=BSE_HEADERS,
            follow_redirects=True,
        ) as client:
            resp = client.get(url)

            if resp.status_code == 200 and len(resp.content) > 100:
                logger.info(f"BSE Bhavcopy downloaded: {len(resp.content)} bytes from {url}")
                return resp.content
            else:
                logger.warning(f"BSE Bhavcopy download failed: HTTP {resp.status_code} from {url}")
                return None

    except Exception as e:
        logger.error(f"BSE Bhavcopy download error from {url}: {e}")
        return None


def _parse_zip_csv(zip_bytes: bytes, fetch_date: date) -> Optional[pd.DataFrame]:
    """
    Extract CSV from BSE ZIP and parse into standardized DataFrame.

    BSE Bhavcopy CSV columns (typical):
      SC_CODE, SC_NAME, SC_GROUP, SC_TYPE, OPEN, HIGH, LOW, CLOSE, LAST,
      PREVCLOSE, NO_TRADES, NO_OF_SHRS, NET_TURNOV, ...

    We filter to SC_GROUP='A' or 'B' or 'T' (equity groups).
    """
    try:
        zip_buffer = io.BytesIO(zip_bytes)
        with zipfile.ZipFile(zip_buffer, "r") as zf:
            csv_files = [f for f in zf.namelist() if f.lower().endswith(".csv")]
            if not csv_files:
                logger.error("No CSV file found in BSE Bhavcopy ZIP")
                return None

            csv_name = csv_files[0]
            with zf.open(csv_name) as csv_file:
                df = pd.read_csv(csv_file)

    except zipfile.BadZipFile:
        logger.error("Corrupt ZIP file from BSE")
        return None
    except Exception as e:
        logger.error(f"Error extracting BSE Bhavcopy CSV: {e}")
        return None

    return _normalize_dataframe(df, fetch_date)


def _parse_direct_csv(csv_bytes: bytes, fetch_date: date) -> Optional[pd.DataFrame]:
    """Parse a direct (non-zipped) CSV from BSE v2 URL."""
    try:
        df = pd.read_csv(io.BytesIO(csv_bytes))
        return _normalize_dataframe(df, fetch_date)
    except Exception as e:
        logger.error(f"Error parsing BSE direct CSV: {e}")
        return None


def _normalize_dataframe(df: pd.DataFrame, fetch_date: date) -> Optional[pd.DataFrame]:
    """Normalize BSE bhavcopy DataFrame into standard schema."""
    # Strip whitespace from column names
    df.columns = df.columns.str.strip()

    # ── Handle two known BSE CSV formats ─────────────────────────────
    # Format 1: SC_CODE, SC_NAME, SC_GROUP, OPEN, HIGH, LOW, CLOSE, NO_OF_SHRS
    # Format 2: SCRIP_CD, SCRIP_NAME, SCRIP_GRP, OPEN, HIGH, LOW, CLOSE, TDCLOINDI

    # Normalize column names
    col_map = {}
    for col in df.columns:
        upper = col.upper()
        if upper in ("SC_CODE", "SCRIP_CD", "SCRIP CODE"):
            col_map[col] = "SC_CODE"
        elif upper in ("SC_NAME", "SCRIP_NAME", "SCRIP NAME"):
            col_map[col] = "SC_NAME"
        elif upper in ("SC_GROUP", "SCRIP_GRP", "SCRIP GROUP", "GROUP"):
            col_map[col] = "SC_GROUP"
        elif upper == "OPEN":
            col_map[col] = "OPEN"
        elif upper == "HIGH":
            col_map[col] = "HIGH"
        elif upper == "LOW":
            col_map[col] = "LOW"
        elif upper == "CLOSE":
            col_map[col] = "CLOSE"
        elif upper in ("NO_OF_SHRS", "TTL_TRD_QNTY", "VOLUME", "QTY"):
            col_map[col] = "VOLUME"

    df = df.rename(columns=col_map)

    # Check required columns
    required = {"SC_CODE", "OPEN", "HIGH", "LOW", "CLOSE"}
    if not required.issubset(set(df.columns)):
        logger.error(f"BSE Bhavcopy missing columns. Found: {list(df.columns)}")
        return None

    # Filter equity groups (A, B, T, X, XT, XC, Z) — exclude preference shares etc.
    equity_groups = {"A", "B", "T", "X", "XT", "XC", "Z"}
    if "SC_GROUP" in df.columns:
        df["SC_GROUP"] = df["SC_GROUP"].astype(str).str.strip()
        df = df[df["SC_GROUP"].isin(equity_groups)].copy()

    # Build result DataFrame
    result = pd.DataFrame({
        "ticker_bse":    df["SC_CODE"].astype(str).str.strip(),
        "company_name":  df["SC_NAME"].str.strip() if "SC_NAME" in df.columns else None,
        "price_date":    fetch_date,
        "open":          pd.to_numeric(df["OPEN"], errors="coerce"),
        "high":          pd.to_numeric(df["HIGH"], errors="coerce"),
        "low":           pd.to_numeric(df["LOW"], errors="coerce"),
        "close":         pd.to_numeric(df["CLOSE"], errors="coerce"),
        "volume":        pd.to_numeric(df.get("VOLUME"), errors="coerce").astype("Int64") if "VOLUME" in df.columns else None,
    })

    # Drop rows with missing price data
    result = result.dropna(subset=["high", "low", "close"])

    logger.info(f"BSE Bhavcopy parsed: {len(result)} equity stocks for {fetch_date}")
    return result


# ── Public API ───────────────────────────────────────────────────────────────

def fetch_bse_bhavcopy(fetch_date: Optional[date] = None) -> Optional[pd.DataFrame]:
    """
    Download and parse BSE Bhavcopy for the given date.

    Args:
        fetch_date: Date to fetch (default: today)

    Returns:
        DataFrame with columns [ticker_bse, company_name, price_date, open, high, low, close, volume]
        compatible with stock_prices schema, or None on failure.
    """
    if fetch_date is None:
        fetch_date = date.today()

    logger.info(f"Fetching BSE Bhavcopy for {fetch_date}...")

    # Try ZIP variants first (variant 0 and 1)
    for variant in range(2):
        url = _build_url(fetch_date, variant=variant)
        file_bytes = _download_file(url)
        if file_bytes is not None:
            result = _parse_zip_csv(file_bytes, fetch_date)
            if result is not None and not result.empty:
                return result

    # Try direct CSV (v2 format)
    url = _build_url(fetch_date, variant=2)
    file_bytes = _download_file(url)
    if file_bytes is not None:
        result = _parse_direct_csv(file_bytes, fetch_date)
        if result is not None and not result.empty:
            return result

    logger.error(f"BSE Bhavcopy not available for {fetch_date}")
    return None


def get_price_for_scrip(df: pd.DataFrame, scrip_code: str) -> Optional[dict]:
    """
    Extract a single stock's OHLCV from a parsed BSE bhavcopy DataFrame.

    Args:
        df: Parsed bhavcopy DataFrame
        scrip_code: BSE scrip code (e.g. "500325" for Reliance)

    Returns:
        {"open": ..., "high": ..., "low": ..., "close": ..., "volume": ...}
        or None if scrip not found.
    """
    if df is None or df.empty:
        return None

    row = df[df["ticker_bse"] == str(scrip_code).strip()]
    if row.empty:
        return None

    r = row.iloc[0]
    return {
        "open":         float(r["open"]) if pd.notna(r["open"]) else None,
        "high":         float(r["high"]),
        "low":          float(r["low"]),
        "close":        float(r["close"]),
        "volume":       int(r["volume"]) if pd.notna(r.get("volume")) else None,
        "company_name": r.get("company_name"),
    }


def map_bse_to_nse(df: pd.DataFrame, bse_to_nse_map: dict[str, str]) -> pd.DataFrame:
    """
    Map BSE scrip codes to NSE tickers using a provided mapping dict.
    Useful when BSE data needs to be matched to stocks stored with NSE tickers.

    Args:
        df: BSE bhavcopy DataFrame
        bse_to_nse_map: {"500325": "RELIANCE", "532540": "TCS", ...}

    Returns:
        DataFrame with an added 'ticker_nse' column
    """
    df = df.copy()
    df["ticker_nse"] = df["ticker_bse"].map(bse_to_nse_map)
    return df
