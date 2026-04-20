# 🧪 AGENT 6 — QA-TESTER Progress Log
## QA Tester — Courtney Smith Channel Breakout Platform

**Codename:** QA-TESTER  
**Status:** ⏳ RUNNING CONTINUOUSLY AS FEATURES COMPLETE  
**Last Updated:** 2026-04-19

---

## Testing Strategy
- Run each suite as the relevant agent marks features [DONE]
- P1 bugs = blockers (stop everything, must fix before proceeding)
- P2 bugs = fix before production deploy
- P3 bugs = fix in first patch after launch

---

## Suite 1 — Database Integrity
_Runs after: DB-ARCH complete_

- [ ] All 14 tables exist with correct column names and types
- [ ] All CHECK constraints enforced (role, status, signal_type, etc.)
- [ ] All UNIQUE constraints enforced (email, ticker, user+stock watchlist, etc.)
- [ ] All foreign keys valid (no orphaned rows)
- [ ] All 9 indexes exist
- [ ] RLS enabled on all 14 tables
- [ ] Cross-trader isolation: Trader A cannot read Trader B's positions
- [ ] Cross-trader isolation: Trader A cannot read Trader B's signals
- [ ] Cross-trader isolation: Trader A cannot read Trader B's capital_log
- [ ] Super admin seed data present (aaanurag@yahoo.com, role=admin)

**Suite 1 Status:** ⏳ Not started  
**Bugs found:** 0

---

## Suite 2 — Authentication
_Runs after: BACKEND-ENG /auth routes complete_

- [ ] POST /auth/login with correct credentials → 200 + JWT
- [ ] POST /auth/login with wrong password → 401
- [ ] POST /auth/login with unknown email → 401
- [ ] Accessing /dashboard without JWT → 401
- [ ] first_login_complete=false → redirected to /first-login
- [ ] Cannot skip /first-login without completing both steps
- [ ] Password reset email received via Supabase Auth
- [ ] Paused account CAN login (status=paused)
- [ ] Suspended account CANNOT login (status=suspended)
- [ ] Admin JWT gives access to /admin/* routes
- [ ] Trader JWT denied at /admin/* routes

**Suite 2 Status:** ⏳ Not started  
**Bugs found:** 0

---

## Suite 3 — Signal Accuracy ⚠️ MOST CRITICAL
_Runs after: SCAN-ENG [VERIFIED-ACCURATE]_

BUY Signal Verification:
- [ ] BUY fires when ALL 3 conditions TRUE simultaneously
- [ ] BUY does NOT fire when ch55_high_flat_days < 5
- [ ] BUY does NOT fire when close <= previous ch55_high
- [ ] BUY does NOT fire when adx_rising = False
- [ ] BUY does NOT fire if that trader has unconfirmed pending signal for stock
- [ ] BUY DOES fire even if confirmed open position exists in same stock

EXIT Signal Verification:
- [ ] REJECTION: fires on day 2 if no close above breakout level
- [ ] REJECTION: does NOT fire on day 1 (too early)
- [ ] TRAILING STOP: fires when close < ch20_low (20-day low)
- [ ] TRAILING STOP: does NOT fire when close >= ch20_low
- [ ] ADX EXIT: fires when adx was >= 40 yesterday AND today adx < yesterday
- [ ] ADX EXIT: does NOT fire when adx was < 40 yesterday
- [ ] ALL positions in same stock exit simultaneously on any exit signal

Real NSE Historical Verification:
| Stock | Date | Expected | Actual | Match |
|---|---|---|---|---|
| TBD | TBD | BUY | | [ ] |
| TBD | TBD | BUY | | [ ] |
| TBD | TBD | EXIT-TRAILING | | [ ] |

**Suite 3 Status:** ⏳ Not started  
**Bugs found:** 0

---

## Suite 4 — Confirmation Workflow
_Runs after: BACKEND-ENG signals routes + FRONTEND-ENG Screen 4_

- [ ] Permanent link from WhatsApp opens confirmation screen without manual login
- [ ] SUBMIT button disabled (greyed) when any row unactioned
- [ ] Counter "X of Y signals still need your input" decrements correctly
- [ ] SUBMIT activates (turns green) when ALL rows actioned
- [ ] After SUBMIT: all rows locked, cannot change
- [ ] After SUBMIT: Next day's tips flow
- [ ] Admin CAN submit on behalf of trader via /admin/users/:id/confirm

**Suite 4 Status:** ⏳ Not started  
**Bugs found:** 0

---

## Suite 5 — Capital & Position Tracking
_Runs after: BACKEND-ENG positions + capital routes_

- [ ] BUY confirmed: total_invested deducted from available_capital
- [ ] SELL confirmed: exit_value returned to available_capital
- [ ] Partial sell: only partial amount returned, position qty reduced
- [ ] Manual BUY: deducted + tagged MANUAL in capital_log
- [ ] Manual SELL: added + tagged MANUAL in capital_log
- [ ] Admin adjustment: tagged ADMIN_ADJUST in capital_log
- [ ] capital_log entry exists for EVERY capital change
- [ ] available_capital = starting + deposits - withdrawals - open positions (verify formula)

**Suite 5 Status:** ⏳ Not started  
**Bugs found:** 0

---

## Suite 6 — Auto-Pause / Suspend Rules
_Runs after: SCAN-ENG scan_runner.py complete_

- [ ] Inactivity counter increments: market days with pending signals only
- [ ] Inactivity counter: does NOT increment on weekends
- [ ] Inactivity counter: does NOT increment on market holidays
- [ ] Inactivity counter: does NOT increment on no-signal days
- [ ] Day 5: warning message sent (WhatsApp + Email)
- [ ] Day 7: account auto-paused, notifications stop completely
- [ ] Day 12: warning message sent from paused state
- [ ] Day 15: account auto-suspended, login blocked
- [ ] Admin can reactivate (set status=active, reset inactivity_days=0)
- [ ] When paused: zero signals, zero notifications, zero exit alerts

**Suite 6 Status:** ⏳ Not started  
**Bugs found:** 0

---

## Suite 7 — Data Cascade & Retry
_Runs after: SCAN-ENG data_fetcher.py complete_

- [ ] yfinance succeeds → logged as success in data_source_log
- [ ] yfinance fails → retry scheduled in 15 min
- [ ] yfinance retry count reaches 12 → moves to NSE Bhavcopy
- [ ] NSE Bhavcopy succeeds → logged as success
- [ ] NSE Bhavcopy fails → moves to BSE Bhavcopy
- [ ] BSE Bhavcopy succeeds → logged as success
- [ ] All 3 sources fail → Super Admin alerted immediately
- [ ] All attempts (success + fail) in data_source_log

**Suite 7 Status:** ⏳ Not started  
**Bugs found:** 0

---

## Suite 8 — Mobile UI
_Runs after: FRONTEND-ENG all 13 screens complete_

- [ ] Screen 1 /login: renders at 375px, no horizontal scroll
- [ ] Screen 2 /first-login: renders at 375px
- [ ] Screen 3 /dashboard: capital cards stack vertically, bottom tab bar visible
- [ ] Screen 4 /confirm: BUY/SELL buttons ≥48px height
- [ ] Screen 4 /confirm: SUBMIT button stays FIXED at bottom while scrolling
- [ ] Screen 4 /confirm: qty input opens numeric keyboard (inputmode=numeric)
- [ ] Screen 5 /portfolio: positions as cards (no wide tables)
- [ ] Screen 6 /manual-entry: full-width inputs
- [ ] Screen 7 /watchlist: renders at 375px
- [ ] Screen 8 /backtest: equity chart scrollable horizontally only if needed
- [ ] Screen 9 /profile: renders at 375px
- [ ] All screens: minimum 14px font on mobile
- [ ] Bottom tab bar: all 5 items visible at 375px

**Suite 8 Status:** ⏳ Not started  
**Bugs found:** 0

---

## Suite 9 — Edge Cases
_Runs after: all agents complete_

- [ ] Upper circuit on BUY day → amber warning shown on confirmation screen
- [ ] Lower circuit on EXIT day → amber warning shown on confirmation screen
- [ ] Bhavcopy circuit level reflected correctly
- [ ] Post-holiday gap down >2% → gap risk warning shown on EXIT card
- [ ] No price data for stock for 3 consecutive days → suspension detected
- [ ] Stock suspension: Super Admin WhatsApp + Email alert sent
- [ ] Stock suspension: trader alerted to check with broker
- [ ] Stock suspension: red ⚠️ badge in trader portfolio
- [ ] Stock suspension: no new signals generated for suspended stock
- [ ] Super Admin manually adds today as holiday after scan started → scan aborted
- [ ] Trader tries to add 31st watchlist stock → blocked with clear error
- [ ] Trader tries to deactivate stock with open position → 409 + clear error message

**Suite 9 Status:** ⏳ Not started  
**Bugs found:** 0

---

## Bug Log
| Date | Severity | Agent | Bug | Status |
|---|---|---|---|---|
| — | — | — | None yet | — |

---

## Activity Log
<!-- Format: [YYYY-MM-DD HH:MM IST] [STATUS] Description -->

[2026-04-19 23:46 IST] [INITIALIZED] Progress file created. Will begin Suite 1 after DB-ARCH completes.

---

## Current Blockers
_Waiting for agents to complete their features_
