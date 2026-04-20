# 🎨 AGENT 4 — FRONTEND-ENG Progress Log
## Frontend Engineer — Courtney Smith Channel Breakout Platform

**Codename:** FRONTEND-ENG  
**Status:** ⏳ CAN START WITH MOCKED API  
**Last Updated:** 2026-04-19

---

## Dependencies
- [ ] BACKEND-ENG routes ready (for real API wiring — can mock initially)
- [ ] Vercel account access
- [ ] Supabase Anon Key (for Auth)

---

## Setup Checklist
- [ ] `npm create vite@latest frontend -- --template react`
- [ ] TailwindCSS installed and configured
- [ ] tailwind.config.js — custom color tokens added
- [ ] Google Fonts (Inter) added to index.html
- [ ] React Router v6 configured
- [ ] axios configured with base URL + auth header interceptor
- [ ] react-hook-form installed
- [ ] Recharts installed

---

## Screen Build Checklist

### Screen 1 — /login
- [ ] [SCAFFOLDED] Centered card, 400px max-width, white bg
- [ ] [STYLED] Email + password inputs, show/hide toggle
- [ ] [STYLED] Full-width LOGIN button (brand blue, 48px min)
- [ ] [STYLED] Error: red border + error text on failed login
- [ ] [STYLED] "Accounts created by admin only" note
- [ ] [WIRED-API] POST /auth/login → on success redirect
- [ ] [MOBILE-TESTED] Responsive at 375px
- [ ] [DONE]

### Screen 2 — /first-login
- [ ] [SCAFFOLDED] 2-step progress dots
- [ ] [STYLED] Step 1: New + Confirm password fields
- [ ] [STYLED] Step 2: Starting capital (₹ numeric) + Risk % input
- [ ] [WIRED-API] POST /auth/change-password + PATCH /me
- [ ] [MOBILE-TESTED]
- [ ] [DONE]

### Screen 3 — /dashboard ⭐ MOBILE PRIORITY
- [ ] [SCAFFOLDED] Greeting + date + notification badge
- [ ] [STYLED] 2×2 capital summary cards (Available/Invested/P&L/Slots)
- [ ] [STYLED] BUY SIGNALS TODAY card (green header)
- [ ] [STYLED] EXIT ALERTS TODAY card (red header)
- [ ] [STYLED] OPEN POSITIONS preview (2 items + count)
- [ ] [STYLED] Data feed status + re-fetch button
- [ ] [STYLED] Market closed holiday banner
- [ ] [WIRED-API] GET /me, /me/signals/today, /me/positions, /data/status
- [ ] [MOBILE-TESTED] Bottom tab bar visible
- [ ] [DONE]

### Screen 4 — /confirm/:token ⭐⭐ HIGHEST PRIORITY
- [ ] [SCAFFOLDED] Progress bar: "X of Y signals actioned"
- [ ] [STYLED] BUY SIGNAL cards (all fields from wireframe)
- [ ] [STYLED] EXIT ALERT cards (all fields, gap risk + circuit badges)
- [ ] [STYLED] Editable qty input → opens numeric keyboard on mobile
- [ ] [STYLED] [✅ I BOUGHT IT] [❌ I DID NOT BUY] buttons (48px min)
- [ ] [STYLED] [✅ I SOLD IT] [❌ I DID NOT SELL] buttons (48px min)
- [ ] [STYLED] SUBMIT ALL button — FIXED at bottom, greyed until all actioned
- [ ] [STYLED] Green SUBMIT when all rows actioned
- [ ] [STYLED] Locked screen after submit with timestamp
- [ ] [WIRED-API] GET + POST /me/signals/confirm (via token auth)
- [ ] [MOBILE-TESTED] SUBMIT stays fixed at bottom while scrolling
- [ ] [DONE]

### Screen 5 — /portfolio ⭐ MOBILE PRIORITY
- [ ] [SCAFFOLDED] Sticky summary header card
- [ ] [STYLED] Open positions as cards (not tables on mobile)
- [ ] [STYLED] Exit alert badge (red) + GO TO CONFIRMATION link
- [ ] [STYLED] Manual entry icon 🖊️
- [ ] [STYLED] Closed positions with date filter
- [ ] [STYLED] Export CSV button
- [ ] [WIRED-API] GET /me/positions
- [ ] [MOBILE-TESTED]
- [ ] [DONE]

### Screen 6 — /portfolio/manual-entry
- [ ] [SCAFFOLDED] BUY/SELL toggle
- [ ] [STYLED] Stock search, date, price, qty, notes
- [ ] [STYLED] Auto-calculated total value
- [ ] [STYLED] SELL: position selector + partial qty
- [ ] [WIRED-API] POST /me/positions/manual + /manual-sell
- [ ] [MOBILE-TESTED]
- [ ] [DONE]

### Screen 7 — /watchlist
- [ ] [SCAFFOLDED] Count badge "X/30 active"
- [ ] [STYLED] Search + add new stock
- [ ] [STYLED] Active stocks list with [Deactivate] buttons
- [ ] [STYLED] Inactive stocks list with [Reactivate] buttons
- [ ] [STYLED] Inline error when deactivating stock with open position
- [ ] [WIRED-API] GET/POST/PATCH /me/watchlist
- [ ] [MOBILE-TESTED]
- [ ] [DONE]

### Screen 8 — /backtest
- [ ] [SCAFFOLDED] Stock multi-selector (up to 7)
- [ ] [STYLED] Date range, starting capital, position size, risk %
- [ ] [STYLED] 4 summary stat cards
- [ ] [STYLED] Recharts equity curve (buy 🟢 exit 🔴 markers)
- [ ] [STYLED] Day-by-day log table (all days, actions highlighted)
- [ ] [STYLED] Export CSV button
- [ ] [WIRED-API] POST /backtest + GET /backtest/:id
- [ ] [MOBILE-TESTED]
- [ ] [DONE]

### Screen 9 — /profile
- [ ] [SCAFFOLDED] Personal details (email locked)
- [ ] [STYLED] Notification toggles
- [ ] [STYLED] Risk % input (0.5–5.0)
- [ ] [STYLED] Add/Reduce capital inputs
- [ ] [STYLED] Capital history log (scrollable)
- [ ] [STYLED] Change Password + Pause My Account buttons
- [ ] [WIRED-API] GET/PATCH /me + POST /me/capital + GET /me/capital-log
- [ ] [MOBILE-TESTED]
- [ ] [DONE]

### Screen 10 — /admin/users
- [ ] [SCAFFOLDED] Trader table + search
- [ ] [STYLED] Status badges (🟢 Active, 🟡 Paused, 🔴 Suspended)
- [ ] [STYLED] CREATE NEW USER form
- [ ] [WIRED-API] GET/POST /admin/users
- [ ] [DONE]

### Screen 11 — /admin/users/:id
- [ ] [SCAFFOLDED] Trader header with admin action buttons
- [ ] [STYLED] Tabbed view: Watchlist / Positions / Capital Log / Signals / Notifications
- [ ] [WIRED-API] GET /admin/users/:id + PATCH for status/capital
- [ ] [DONE]

### Screen 12 — /admin/system
- [ ] [SCAFFOLDED] System stats + data feed status
- [ ] [STYLED] Manual re-fetch (3 source buttons)
- [ ] [STYLED] Market holidays widget
- [ ] [STYLED] Pending confirmations table
- [ ] [STYLED] Background jobs progress bars
- [ ] [WIRED-API] GET /data/status + GET /admin/users + admin routes
- [ ] [DONE]

### Screen 13 — /admin/profile
- [ ] [SCAFFOLDED] Name (locked email) + mobile
- [ ] [STYLED] Change password form
- [ ] [WIRED-API] PATCH /admin/users/:id
- [ ] [DONE]

---

## Global Components Checklist
- [ ] BottomTabBar (mobile — all trader screens)
- [ ] Sidebar (desktop — 240px)
- [ ] StatusBadge (Active/Paused/Suspended)
- [ ] SignalCard (BUY/EXIT card component)
- [ ] PositionCard (portfolio position card)
- [ ] CapitalSummaryCard
- [ ] DataFeedStatusBar
- [ ] CircuitWarningBadge (amber)
- [ ] GapRiskBadge (amber)
- [ ] LoadingSpinner
- [ ] ErrorBoundary

---

## Activity Log
<!-- Format: [YYYY-MM-DD HH:MM IST] [STATUS] Description -->

[2026-04-19 23:46 IST] [INITIALIZED] Progress file created. Can start scaffolding with mocked API.

---

## Handoff Output
When all screens are built and deployed:
```
VERCEL_URL=https://your-app.vercel.app
FRONTEND_STATUS=LIVE
```

## Blockers
_None — can start with mocked API immediately_

## Bugs / Issues
_None yet_
