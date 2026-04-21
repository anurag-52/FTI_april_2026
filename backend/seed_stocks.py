import os
import requests
from dotenv import load_dotenv

# Load local .env (if it exists) to get URL and KEY
load_dotenv(".env")
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")

if not url or not key:
    print("Skipping - Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in .env")
    exit(0)

# We will directly hit the REST API
rest_url = f"{url}/rest/v1/stocks"

headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
    "Prefer": "resolution=ignore-duplicates"
}

stocks = [
    {"ticker_nse": "RELIANCE", "company_name": "Reliance Industries", "exchange": "NSE"},
    {"ticker_nse": "TCS", "company_name": "Tata Consultancy Services", "exchange": "NSE"},
    {"ticker_nse": "HDFCBANK", "company_name": "HDFC Bank", "exchange": "NSE"},
    {"ticker_nse": "INFY", "company_name": "Infosys", "exchange": "NSE"},
    {"ticker_nse": "ICICIBANK", "company_name": "ICICI Bank", "exchange": "NSE"},
    {"ticker_nse": "HUL", "company_name": "Hindustan Unilever", "exchange": "NSE"},
    {"ticker_nse": "SBIN", "company_name": "State Bank of India", "exchange": "NSE"},
    {"ticker_nse": "BHARTIARTL", "company_name": "Bharti Airtel", "exchange": "NSE"},
    {"ticker_nse": "ITC", "company_name": "ITC Limited", "exchange": "NSE"},
    {"ticker_nse": "BAJFINANCE", "company_name": "Bajaj Finance", "exchange": "NSE"},
    {"ticker_nse": "LART", "company_name": "Larsen & Toubro", "exchange": "NSE"},
    {"ticker_nse": "KOTAKBANK", "company_name": "Kotak Mahindra Bank", "exchange": "NSE"},
    {"ticker_nse": "TATAMOTORS", "company_name": "Tata Motors", "exchange": "NSE"},
    {"ticker_nse": "AXISBANK", "company_name": "Axis Bank", "exchange": "NSE"},
    {"ticker_nse": "SUNPHARMA", "company_name": "Sun Pharma", "exchange": "NSE"},
    {"ticker_nse": "MARUTI", "company_name": "Maruti Suzuki", "exchange": "NSE"},
    {"ticker_nse": "TATASTEEL", "company_name": "Tata Steel", "exchange": "NSE"},
    {"ticker_nse": "WIPRO", "company_name": "Wipro", "exchange": "NSE"},
    {"ticker_nse": "HCLTECH", "company_name": "HCL Tech", "exchange": "NSE"},
    {"ticker_nse": "ONGC", "company_name": "ONGC", "exchange": "NSE"},
    {"ticker_nse": "NTPC", "company_name": "NTPC", "exchange": "NSE"},
    {"ticker_nse": "BAJAJFINSV", "company_name": "Bajaj Finserv", "exchange": "NSE"},
    {"ticker_nse": "ASIANPAINT", "company_name": "Asian Paints", "exchange": "NSE"},
    {"ticker_nse": "TITAN", "company_name": "Titan Company", "exchange": "NSE"},
    {"ticker_nse": "M&M", "company_name": "Mahindra & Mahindra", "exchange": "NSE"},
    {"ticker_nse": "POWERGRID", "company_name": "Power Grid", "exchange": "NSE"},
    {"ticker_nse": "ULTRACEMCO", "company_name": "UltraTech Cement", "exchange": "NSE"},
    {"ticker_nse": "NESTLEIND", "company_name": "Nestle India", "exchange": "NSE"},
    {"ticker_nse": "TECHM", "company_name": "Tech Mahindra", "exchange": "NSE"},
    {"ticker_nse": "JSWSTEEL", "company_name": "JSW Steel", "exchange": "NSE"}
]

print(f"Seeding {len(stocks)} stocks...")

resp = requests.post(rest_url, headers=headers, json=stocks)
if resp.status_code in [201, 200]:
    print("Seeded successfully!")
else:
    print("Error:", resp.status_code, resp.text)
