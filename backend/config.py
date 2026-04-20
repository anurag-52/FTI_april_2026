"""
Supabase client configuration.
Backend always uses SERVICE ROLE key — bypasses RLS for all admin/scan operations.
"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL: str = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY: str = os.environ["SUPABASE_SERVICE_KEY"]
SUPABASE_ANON_KEY: str = os.environ["SUPABASE_ANON_KEY"]
SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "")

FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
CRON_SECRET: str = os.getenv("CRON_SECRET", "change-cron-secret")
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

# MSG91 (WhatsApp)
MSG91_API_KEY: str = os.getenv("MSG91_API_KEY", "")
MSG91_SENDER_ID: str = os.getenv("MSG91_SENDER_ID", "")

# Brevo (Email — free tier 300/day)
BREVO_API_KEY: str = os.getenv("BREVO_API_KEY", "")
BREVO_SENDER_NAME: str = os.getenv("BREVO_SENDER_NAME", "Channel Breakout Signals")
BREVO_SENDER_EMAIL: str = os.getenv("BREVO_SENDER_EMAIL", "signals@yourdomain.com")

# Service-role client (used by backend for all DB operations)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
