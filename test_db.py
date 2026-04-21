import json
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv("backend/.env")
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(url, key)

res = supabase.table("backtest_runs").select("*").order("created_at", desc=True).limit(1).execute()
if res.data:
    print(json.dumps(res.data[0], indent=2))
else:
    print("No runs found")
