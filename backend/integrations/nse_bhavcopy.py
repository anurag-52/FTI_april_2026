"""
AGENT 5 — INTEGRATIONS-ENG
nse_bhavcopy.py — NSE Bhavcopy CSV parser (Tier 2 backup data source)

Downloads and parses the daily NSE Bhavcopy file:
  URL pattern: https://nsearchives.nseindia.com/content/historical/EQUITIES/{YYYY}/{MON}/cm{DDMONYYYY}bhav.csv.zip

Output: pandas DataFrame compatible with stock_prices schema columns:
  ticker_nse, price_date, open, high, low, close, volume
"""

import io
import logging
import zipfile
from datetime import date, datetime
from typing import Optional

import httpx
import pandas as pd

logger = logging.getLogger(__name__)

# ── NSE URL Templates ────────────────────────────────────────────────────────
# Primary: NSE Archives (historical EQUITIES section)
NSE_BHAVCOPY_URL = (
    "https://nsearchives.nseindia.com/content/historical/EQUITIES"
    "/{year}/{month}/cm{ddmonyyyy}bhav.csv.zip"
)

# Alternate URL pattern (some dates use different path)
NSE_BHAVCOPY_ALT_URL = (
    "https://www.nseindia.com/content/historical/EQUITIES"
    "/{year}/{month}/cm{ddmonyyyy}bhav.csv.zip"
)

# Headers to mimic browser (NSE blocks non-browser requests)
NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com/",
    "Connection": "keep-alive",
}


# ── Download + Parse ─────────────────────────────────────────────────────────

def _build_url(fetch_date: date, alt: bool = False) -> str:
    """Build the NSE bhavcopy download URL for a given date."""
    year = str(fetch_date.year)
    month = fetch_date.strftime("%b").upper()  # JAN, FEB, MAR, etc.
    ddmonyyyy = fetch_date.strftime("%d%b%Y").upper()  # e.g. 18APR2026

    template = NSE_BHAVCOPY_ALT_URL if alt else NSE_BHAVCOPY_URL
    return template.format(year=year, month=month, ddmonyyyy=ddmonyyyy)


def _download_zip(url: str) -> Optional[bytes]:
    """Download ZIP file from NSE, returning raw bytes or None."""
    try:
        with httpx.Client(
            timeout=30.0,
            headers=NSE_HEADERS,
            follow_redirects=True,
        ) as client:
            # First hit NSE homepage to get session cookies
            try:
                client.get("https://www.nseindia.com/", timeout=10.0)
            except Exception:
                pass  # Session cookie is optional for archives

            resp = client.get(url)

            if resp.status_code == 200 and len(resp.content) > 100:
                logger.info(f"NSE Bhavcopy downloaded: {len(resp.content)} bytes from {url}")
                return resp.content
            else:
                logger.warning(f"NSE Bhavcopy download failed: HTTP {resp.status_code} from {url}")
                return None

    except Exception as e:
        logger.error(f"NSE Bhavcopy download error: {e}")
        return None


def _parse_csv_from_zip(zip_bytes: bytes, fetch_date: date) -> Optional[pd.DataFrame]:
    """
    Extract CSV from ZIP and parse into standardized DataFrame.

    NSE Bhavcopy CSV columns:
      SYMBOL, SERIES, OPEN, HIGH, LOW, CLOSE, LAST, PREVCLOSE, TOTTRDQTY, TOTTRDVAL, TIMESTAMP, ...

    We only want SERIES='EQ' rows (equity segment).
    """
    try:
        zip_buffer = io.BytesIO(zip_bytes)
        with zipfile.ZipFile(zip_buffer, "r") as zf:
            csv_files = [f for f in zf.namelist() if f.endswith(".csv")]
            if not csv_files:
                logger.error("No CSV file found in NSE Bhavcopy ZIP")
                return None

            csv_name = csv_files[0]
            with zf.open(csv_name) as csv_file:
                df = pd.read_csv(csv_file)

    except zipfile.BadZipFile:
        logger.error("Corrupt ZIP file from NSE")
        return None
    except Exception as e:
        logger.error(f"Error extracting NSE Bhavcopy CSV: {e}")
        return None

    # ── Clean and transform ──────────────────────────────────────────────
    # Strip whitespace from column names
    df.columns = df.columns.str.strip()

    # Filter to equity series only
    if "SERIES" in df.columns:
        df = df[df["SERIES"].str.strip() == "EQ"].copy()

    # Check required columns
    required = {"SYMBOL", "OPEN", "HIGH", "LOW", "CLOSE"}
    if not required.issubset(set(df.columns)):
        logger.error(f"NSE Bhavcopy missing columns. Found: {list(df.columns)}")
        return None

    # Map to standardized schema
    volume_col = "TOTTRDQTY" if "TOTTRDQTY" in df.columns else "TOTALTRADEDQUANTITY"
    if volume_col not in df.columns:
        volume_col = None

    result = pd.DataFrame({
        "ticker_nse":  df["SYMBOL"].str.strip(),
        "price_date":  fetch_date,
        "open":        pd.to_numeric(df["OPEN"], errors="coerce"),
        "high":        pd.to_numeric(df["HIGH"], errors="coerce"),
        "low":         pd.to_numeric(df["LOW"], errors="coerce"),
        "close":       pd.to_numeric(df["CLOSE"], errors="coerce"),
        "volume":      pd.to_numeric(df[volume_col], errors="coerce").astype("Int64") if volume_col else None,
    })

    # Drop rows with missing price data
    result = result.dropna(subset=["high", "low", "close"])

    logger.info(f"NSE Bhavcopy parsed: {len(result)} equity stocks for {fetch_date}")
    return result


# ── Public API ───────────────────────────────────────────────────────────────

def fetch_nse_bhavcopy(fetch_date: Optional[date] = None) -> Optional[pd.DataFrame]:
    """
    Download and parse NSE Bhavcopy for the given date.

    Args:
        fetch_date: Date to fetch (default: today)

    Returns:
        DataFrame with columns [ticker_nse, price_date, open, high, low, close, volume]
        compatible with stock_prices schema, or None on failure.
    """
    if fetch_date is None:
        fetch_date = date.today()

    logger.info(f"Fetching NSE Bhavcopy for {fetch_date}...")

    # Try primary URL
    url = _build_url(fetch_date, alt=False)
    zip_bytes = _download_zip(url)

    # Try alternate URL if primary failed
    if zip_bytes is None:
        url = _build_url(fetch_date, alt=True)
        zip_bytes = _download_zip(url)

    if zip_bytes is None:
        logger.error(f"NSE Bhavcopy not available for {fetch_date}")
        return None

    return _parse_csv_from_zip(zip_bytes, fetch_date)


def get_price_for_ticker(df: pd.DataFrame, ticker_nse: str) -> Optional[dict]:
    """
    Extract a single stock's OHLCV from a parsed bhavcopy DataFrame.

    Returns:
        {"open": ..., "high": ..., "low": ..., "close": ..., "volume": ...}
        or None if ticker not found.
    """
    if df is None or df.empty:
        return None

    row = df[df["ticker_nse"] == ticker_nse]
    if row.empty:
        return None

    r = row.iloc[0]
    return {
        "open":   float(r["open"]) if pd.notna(r["open"]) else None,
        "high":   float(r["high"]),
        "low":    float(r["low"]),
        "close":  float(r["close"]),
        "volume": int(r["volume"]) if pd.notna(r.get("volume")) else None,
    }
