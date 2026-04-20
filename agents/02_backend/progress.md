# ⚙️ AGENT 2 — BACKEND-ENG Progress Log
## Backend Engineer — Courtney Smith Channel Breakout Platform

**Codename:** BACKEND-ENG  
**Status:** ⏳ WAITING FOR DB-ARCH HANDOFF  
**Last Updated:** 2026-04-19

---

## Dependencies
- [ ] DB-ARCH handoff received (SUPABASE_URL + keys)
- [ ] MSG91 API Key (from INTEGRATIONS-ENG or directly)
- [ ] Brevo API Key (from INTEGRATIONS-ENG or directly)

---

## Route Build Checklist

### AUTH
- [ ] POST /auth/login
- [ ] POST /auth/change-password
- [ ] POST /auth/forgot-password

### ADMIN — User Management
- [ ] POST   /admin/users           (create trader)
- [ ] GET    /admin/users           (list all traders)
- [ ] GET    /admin/users/:id       (trader detail)
- [ ] PATCH  /admin/users/:id       (update status/capital/profile)
- [ ] POST   /admin/users/:id/confirm (admin confirms on behalf)

### TRADER — Profile & Capital
- [ ] GET    /me                    (current user)
- [ ] PATCH  /me                    (update profile)
- [ ] POST   /me/capital            (add/reduce capital → always logged)
- [ ] GET    /me/capital-log        (full history)

### WATCHLIST
- [ ] GET    /me/watchlist
- [ ] POST   /me/watchlist          (add stock, trigger historical fetch if new)
- [ ] PATCH  /me/watchlist/:stock_id (activate/deactivate)
- [ ] DELETE /me/watchlist/:stock_id (blocked if open position)

### SIGNALS
- [ ] GET    /me/signals/today
- [ ] GET    /me/signals/history
- [ ] POST   /me/signals/confirm    (ALL rows must be actioned, then locked)

### POSITIONS
- [ ] GET    /me/positions          (open + closed)
- [ ] POST   /me/positions/manual   (manual buy)
- [ ] POST   /me/positions/manual-sell (partial or full)

### BACKTEST
- [ ] POST   /backtest              (run, up to 7 stocks, shared capital)
- [ ] GET    /backtest/:id          (results)

### DATA
- [ ] POST   /data/refetch          (any user triggers for all)
- [ ] GET    /data/status           (last fetch, source, retry)

### INTERNAL
- [ ] POST   /internal/scan/run     (called by Render Cron at 4:30 PM IST)
- [ ] POST   /internal/refresh-holidays (called by Render Cron Monday 8AM)
- [ ] GET    /health                (Render health check)

---

## Business Rules Implementation Checklist
- [ ] Rule 1: No self-registration — admin creates only
- [ ] Rule 2: First-login gate (password + capital mandatory)
- [ ] Rule 3: Max 30 active watchlist stocks enforced (400 error)
- [ ] Rule 4: Deactivate blocked if open position (409 error)
- [ ] Rule 5: SUBMIT locked after all rows actioned
- [ ] Rule 6: EXIT signal → ALL positions in that stock exit
- [ ] Rule 7: New BUY skipped if unconfirmed pending signal exists
- [ ] Rule 8: Position sizing formula implemented
- [ ] Rule 9: Inactivity = market open days + signal days only
- [ ] Rule 10: Auto-pause day 7, auto-suspend day 15

---

## File Structure
```
backend/
├── main.py
├── requirements.txt
├── config.py
├── database.py         (Supabase client, service_role)
├── auth.py             (JWT validation middleware)
├── routers/
│   ├── auth.py
│   ├── admin.py
│   ├── me.py
│   ├── watchlist.py
│   ├── signals.py
│   ├── positions.py
│   ├── backtest.py
│   ├── data.py
│   └── internal.py
├── models/             (Pydantic schemas)
├── services/           (business logic layer)
└── scan_engine/        (AGENT 3's work plugged in here)
```

---

## Activity Log
<!-- Format: [YYYY-MM-DD HH:MM IST] [STATUS] Description -->

[2026-04-19 23:46 IST] [INITIALIZED] Progress file created. Awaiting DB-ARCH handoff.

---

## Handoff Output
When all routes are built and tested, share with AGENT 4:
```
VITE_API_BASE_URL=https://{render-service-name}.onrender.com
API_STATUS=READY
```

## Blockers
_Waiting for DB-ARCH (AGENT 1) to complete_

## Bugs / Issues
_None yet_
