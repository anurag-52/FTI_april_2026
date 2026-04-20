# 🚀 AGENT 7 — DEVOPS-ENG Progress Log
## DevOps Engineer — Courtney Smith Channel Breakout Platform

**Codename:** DEVOPS-ENG  
**Status:** ⏳ WAITING FOR FIRST WORKING BUILDS  
**Last Updated:** 2026-04-19

---

## Dependencies
- [ ] GitHub access (repo creation + PAT)
- [ ] Vercel account (connect to GitHub)
- [ ] Render account (connect to GitHub)
- [ ] Backend first working build from BACKEND-ENG
- [ ] Frontend first working build from FRONTEND-ENG

---

## Phase 1 — GitHub Repository Setup

- [ ] Create monorepo: `courtney-smith-trading-platform`
- [ ] Push initial folder structure:
  - /frontend
  - /backend
  - /agents
  - /docs
- [ ] Configure .gitignore (exclude .env files, __pycache__, node_modules)
- [ ] Protect main branch (require PR + review before merge)
- [ ] Create branches: main / develop / frontend / backend / scan-engine
- [ ] Add README.md at root level
- [ ] Add .env.example for backend
- [ ] Add .env.example for frontend

---

## Phase 2 — Environment Variables

### Backend .env
```
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
SUPABASE_ANON_KEY=
MSG91_API_KEY=
MSG91_SENDER_ID=
BREVO_API_KEY=
BREVO_SENDER_EMAIL=
FRONTEND_URL=
SECRET_KEY=
CRON_SECRET=
```
- [ ] backend .env.example committed to repo (without values)
- [ ] All values entered in Render dashboard (Environment tab)

### Frontend .env
```
VITE_API_BASE_URL=
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
```
- [ ] frontend .env.example committed to repo (without values)
- [ ] All VITE_* values entered in Vercel dashboard (Environment Variables)

---

## Phase 3 — Vercel Deployment (Frontend)

- [ ] Connect GitHub repo to Vercel
- [ ] Set root directory: /frontend
- [ ] Framework preset: Vite
- [ ] Build command: `npm run build`
- [ ] Output directory: `dist`
- [ ] Set environment variables (VITE_*)
- [ ] First deploy successful — no build errors
- [ ] /login page loads on Vercel URL
- [ ] Configure custom domain (if provided by user)
- [ ] Automatic redeploy on push to main: ✅ enabled

**Vercel URL:** _TBD_  
**Status:** ⏳ Not started

---

## Phase 4 — Render Deployment (Backend)

### Web Service
- [ ] Connect GitHub repo to Render
- [ ] Set root directory: /backend
- [ ] Runtime: Python 3.11
- [ ] Build command: `pip install -r requirements.txt`
- [ ] Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- [ ] Set all environment variables in Render dashboard
- [ ] First deploy successful — no errors
- [ ] GET /health → 200 ✅
- [ ] Note: Free tier spins down after 15 min — cron jobs will keep alive

### Cron Job 1 — Daily EOD Scan
- [ ] Create Render Cron Job service
- [ ] Schedule: `30 11 * * 1-5` (11:30 UTC = 4:30 PM IST, Mon-Fri)
  > NOTE: IST = UTC+5:30, so 4:30 PM IST = 11:00 UTC
  > Use `0 11 * * 1-5` for exactly 4:30 PM IST
- [ ] Command: `curl -X POST https://{BACKEND_URL}/internal/scan/run -H "X-Cron-Secret: {CRON_SECRET}"`
- [ ] Test fire manually → confirm scan_log entry created in Supabase
- [ ] Status: ⏳ Not started

### Cron Job 2 — Holiday Calendar Refresh
- [ ] Create second Render Cron Job service
- [ ] Schedule: `30 2 * * 1` (2:30 UTC = 8:00 AM IST, every Monday)
- [ ] Command: `curl -X POST https://{BACKEND_URL}/internal/refresh-holidays -H "X-Cron-Secret: {CRON_SECRET}"`
- [ ] Test fire manually → confirm calendar checked + change log entry (if any)
- [ ] Status: ⏳ Not started

**Render Backend URL:** _TBD_  
**Status:** ⏳ Not started

---

## Phase 5 — Supabase Configuration

- [ ] Email auth enabled in Supabase Auth settings
- [ ] Password reset redirect URL configured (→ production frontend URL /login)
- [ ] JWT expiry set to 7 days
- [ ] Test: login with anon key → RLS blocks cross-trader access
- [ ] Test: login with service_role key → all data accessible (for backend use)

---

## Phase 6 — Production Deployment Checklist
_All must be ✅ before announcing DONE_

- [ ] GET /health returns 200 on Render backend URL
- [ ] Frontend /login page loads on Vercel URL
- [ ] Supabase has all 14 tables + super admin seeded
- [ ] Test cron fire → new entry in scan_log
- [ ] Test WhatsApp message sent → received on +91 9303121500
- [ ] Test email sent → received at aaanurag@yahoo.com
- [ ] Super Admin login works at production URL
- [ ] Trader account creation by admin works end-to-end
- [ ] First-login flow completes for new trader
- [ ] At least one manual scan run completes successfully

---

## Deployment URLs (fill as services go live)
```
Frontend (Vercel):   https://_________________.vercel.app
Backend (Render):    https://_________________.onrender.com
Supabase Dashboard:  https://supabase.com/dashboard/project/_________
GitHub Repo:         https://github.com/_________/courtney-smith-trading-platform
```

---

## Activity Log
<!-- Format: [YYYY-MM-DD HH:MM IST] [STATUS] Description -->

[2026-04-19 23:46 IST] [INITIALIZED] Progress file created. Awaiting GitHub credentials and first builds.

---

## Blockers
_Waiting for GitHub + Vercel + Render account access_

## Bugs / Issues
_None yet_
