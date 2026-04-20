# Deployment URLs
## Courtney Smith Channel Breakout Trading Platform

_Filled by DEVOPS-ENG as services go live_

---

| Service | URL | Status |
|---|---|---|
| **Frontend (Vercel)** | — | ⏳ Not deployed |
| **Backend (Render)** | — | ⏳ Not deployed |
| **Supabase Dashboard** | — | ⏳ Not configured |
| **GitHub Repo** | — | ⏳ Not created |

---

## Environment Variables Summary

### Backend (Render)
| Variable | Value | Notes |
|---|---|---|
| SUPABASE_URL | — | From Supabase dashboard |
| SUPABASE_SERVICE_KEY | — | Settings → API → service_role |
| SUPABASE_ANON_KEY | — | Settings → API → anon |
| MSG91_API_KEY | — | From MSG91 dashboard |
| MSG91_SENDER_ID | — | WhatsApp Business number |
| BREVO_API_KEY | — | From Brevo dashboard |
| BREVO_SENDER_EMAIL | — | Verified sender email |
| FRONTEND_URL | — | Vercel production URL |
| SECRET_KEY | — | Generate: `openssl rand -hex 32` |
| CRON_SECRET | — | Generate: `openssl rand -hex 32` |

### Frontend (Vercel)
| Variable | Value |
|---|---|
| VITE_API_BASE_URL | Render backend URL |
| VITE_SUPABASE_URL | Supabase project URL |
| VITE_SUPABASE_ANON_KEY | Supabase anon key |

---

## Cron Job Schedule Reference
| Job | Schedule (UTC) | IST Time |
|---|---|---|
| Daily EOD Scan | `0 11 * * 1-5` | 4:30 PM IST Mon-Fri |
| Holiday Calendar Refresh | `30 2 * * 1` | 8:00 AM IST Monday |

---

_Updated by DEVOPS-ENG (AGENT 7)_
