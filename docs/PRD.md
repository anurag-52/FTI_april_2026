# Product Requirements Document (PRD)
## Courtney Smith Channel Breakout Trading Platform
**Version:** 3.0 — FINAL — APPROVED FOR PRODUCTION
**Date:** April 2026
**Super Admin:** aaanurag@yahoo.com | Anurag75* | +91 9303121500
**Target Users:** 10–20 traders (private group, Indian markets NSE/BSE)
**Market:** NSE / BSE — End of Day (EOD) trading signals only
**Deployment:** Single full rollout — complete application built and deployed at once

---

## DESIGN SYSTEM

**Theme:** White-dominant, clean, professional financial application

```
Primary Background:   #FFFFFF  (white — dominant)
Secondary Background: #F8FAFC  (off-white — page backgrounds, card fills)
Sidebar/Header:       #FFFFFF  with subtle #E2E8F0 border
Primary Accent:       #0F4C81  (deep blue — buttons, links, highlights)
Success/Buy:          #16A34A  (green — buy signals, positive P&L)
Danger/Exit:          #DC2626  (red — exit alerts, negative P&L, warnings)
Warning:              #D97706  (amber — pending confirmation, circuit alerts)
Text Primary:         #1E293B  (near black)
Text Muted:           #64748B  (grey — labels, secondary info)
Border:               #E2E8F0  (light grey — card borders, dividers)
Card Shadow:          0 1px 3px rgba(0,0,0,0.08)
Font:                 Inter (Google Fonts)
Border Radius:        12px (cards), 8px (buttons/inputs)
```

**Design Principles:**
- White is the dominant colour on every screen — no dark backgrounds on any trader screen
- Blue accent used sparingly — primary buttons, active nav, key highlights only
- Green and red used only for signal status — never decoratively
- Clean, minimal, uncluttered — no gradients, no heavy shadows
- Data-dense screens (portfolio, backtest) use subtle alternating row shading (#F8FAFC)
- All trader screens mobile-first — desktop is an expanded version of mobile layout

---

## 1. Product Overview

A cloud-based trading signal and portfolio management platform built strictly around Courtney Smith's Channel Breakout technique. The system scans each trader's personal watchlist of up to 30 active NSE/BSE stocks daily, identifies valid breakout and exit signals, notifies traders via WhatsApp and Email, tracks their individual portfolio and available capital, and enforces a discipline loop — traders must confirm all previous signals before new ones are issued. The entire trader UI is mobile-first and fully responsive.

---

## 2. Core Trading Logic

### 2.1 BUY Signal — All 3 Conditions Must Be TRUE Simultaneously

| # | Condition | Rule |
|---|---|---|
| 1 | **55-Day Channel High — Flat/Declining** | The 55-day high must have been flat or declining for at least **5 consecutive days** before today |
| 2 | **Price Breakout** | Today's closing price breaks **above** the 55-day channel high |
| 3 | **ADX Filter** | ADX(20) is **rising today** compared to yesterday (trend gaining strength) |

### 2.2 EXIT Signal — Any 1 Condition Triggers Full Exit of ALL Positions in That Stock

| # | Exit Trigger | Rule |
|---|---|---|
| 1 | **Rejection Rule** | After entry, price does not close above the breakout channel level within **2 days** — exit immediately |
| 2 | **20-Day Trailing Stop** | Price closes below the **20-day channel low** |
| 3 | **ADX Reversal** | ADX turns **down from a reading of 40 or above** |

### 2.3 Multiple Positions in Same Stock
- A trader **can hold multiple open positions** in the same stock if fresh BUY signals fire while a previous position is still open and confirmed
- When **any exit signal fires** on a stock — **ALL open positions** in that stock exit simultaneously (Courtney Smith's market-condition-based exit philosophy)
- If trader has an **unconfirmed pending signal** for a stock — no new signal is generated for that stock until all previous signals are confirmed
- A fresh BUY signal IS generated even if a confirmed open position exists — trader can hold multiple lots of same stock
- When a position is confirmed closed → system treats fresh future signals as brand new trades

### 2.4 Position Sizing — Suggested Quantity (Courtney Smith Fixed Fractional)
- System calculates a **suggested quantity** for each BUY signal using Courtney Smith's Fixed Fractional formula (Chapter 7 — *How to Make a Living Trading Foreign Exchange*):

```
Suggested Qty = (Available Capital × Risk%) ÷ (Entry Price − 20-day low)
```

- Default Risk% = **1%**, editable by trader in profile (range 0.5%–5%)
- Trader can **override the suggested qty** before confirming purchase
- Suggested qty and estimated cost shown clearly on confirmation screen

---

## 3. Data Architecture

### 3.1 Stock Data — Primary & Backup Sources (3-Tier Cascade)

| Tier | Source | Method | Notes |
|---|---|---|---|
| 1 (Primary) | **yfinance** (Yahoo Finance) | Python library, no API key | NSE: `TICKER.NS`, BSE: `TICKER.BO` |
| 2 (Backup 1) | **NSE Bhavcopy CSV** | Direct download from nseindia.com | Official NSE EOD data, free |
| 3 (Backup 2) | **BSE Bhavcopy CSV** | Direct download from bseindia.com | Official BSE EOD data, free |

### 3.2 Automatic Retry Logic
- Daily scan runs at **4:30 PM IST** (Mon–Fri, market days only)
- If yfinance fetch fails → system **automatically retries every 15 minutes for up to 12 attempts** (3 hours total — covering 4:30 PM to 7:30 PM)
- If yfinance still fails after 12 attempts → system **automatically cascades to NSE Bhavcopy**
- If NSE Bhavcopy fails → system **automatically cascades to BSE Bhavcopy**
- Every retry attempt, success, failure, source used, and timestamp is **logged and visible** on both Super Admin and Trader dashboards
- Super Admin receives **WhatsApp + Email alert** immediately if the 4:30 PM scan fails to complete

### 3.3 Manual Re-fetch
- Both **Super Admin AND any trader** can manually trigger a data re-fetch from the dashboard
- When triggered by anyone → applies to the **entire application** (not just that user)
- Manual trigger screen shows **3 source buttons**: yfinance | NSE Bhavcopy | BSE Bhavcopy
- System shows which source was used and timestamp of last successful fetch on dashboard for all users

### 3.4 Central Stock Data Store
- When any trader adds a stock to their watchlist → system checks if stock exists in central store
- If not → system fetches **last 10 years of EOD OHLC data** centrally (shared across all traders)
- Daily EOD data fetched **once per stock** regardless of how many traders hold it
- All indicators and signals are **pre-computed once per stock per day** and stored centrally — never recalculated per trader or per backtest run
- Trader-specific logic (qty suggestion, capital check, portfolio check) is applied on top of the pre-computed central signal

**Fields stored per stock per trading day:**

| Field | Description |
|---|---|
| `date` | Trading date |
| `open`, `high`, `low`, `close` | Raw OHLC price data |
| `volume` | Daily traded volume |
| `ch55_high` | 55-day channel high (highest high of last 55 days) |
| `ch55_low` | 55-day channel low (lowest low of last 55 days) |
| `ch20_high` | 20-day channel high |
| `ch20_low` | 20-day channel low — **this IS the trailing stop level** |
| `adx_20` | ADX(20) value for the day |
| `adx_rising` | Boolean — TRUE if today's ADX > yesterday's ADX |
| `ch55_high_flat_days` | Count of consecutive days 55-day high has been flat or declining |
| `ch55_low_flat_days` | Count of consecutive days 55-day low has been flat or rising |
| `buy_signal` | Boolean — TRUE if ALL 3 buy conditions met today |
| `exit_rejection` | Boolean — TRUE if rejection rule condition met |
| `exit_trailing_stop` | Boolean — TRUE if close < 20-day channel low today |
| `exit_adx` | Boolean — TRUE if ADX turned down from 40+ today |
| `any_exit_signal` | Boolean — TRUE if any of the 3 exit conditions met today |
| `hit_upper_circuit` | Boolean — TRUE if stock hit upper circuit today |
| `hit_lower_circuit` | Boolean — TRUE if stock hit lower circuit today |
| `gap_risk_warning` | Boolean — TRUE if gap down >2% after holiday |

**How this is used:**
- **Daily scan:** reads pre-computed flags — no recalculation. Checks each trader's watchlist stocks for `buy_signal = TRUE` and open positions for `any_exit_signal = TRUE`
- **Backtesting:** reads pre-computed fields day by day — no recalculation per run
- **Multiple traders:** all share the exact same pre-computed values — only capital, risk%, and portfolio state differ per trader

### 3.5 New Stock Added to Central Store — Full Historical Computation
- When any trader adds a stock not yet in central store → system fetches **10 years of EOD OHLC data**
- System then **computes all indicators and signal flags for every single trading day** in that 10-year history
- Runs as a **background job** — does not block the daily scan
- Super Admin dashboard shows background job status: stock name, % complete, estimated time remaining
- Stock available for **live signals immediately** once today's data is computed
- Historical backtest available once full 10-year computation is complete

### 3.6 Gap Risk Warning — Post-Holiday Exit Signals
- When an exit signal fires on the **first trading day after a market holiday** AND stock has **gapped down by more than 2%** from pre-holiday close → gap risk warning shown on confirmation screen:
  > ⚠️ *"Gap Risk Alert: This exit signal was triggered after a market closure. The stock opened significantly lower than the previous close. Your actual sell price may differ from the signal price shown. Please verify with your broker before confirming."*
- Warning shown per affected stock row in EXIT ALERTS section
- Gap risk warnings logged in signal log for Super Admin visibility

### 3.7 Indian Market Special Conditions

**Upper/Lower Circuit Handling**
- System detects circuit hits daily by comparing close against circuit limit thresholds in EOD data
- If stock hits **lower circuit** on exit signal day → confirmation screen shows:
  > ⚠️ *"Lower Circuit Alert: [STOCK] hit its lower circuit limit today. You may not have been able to sell at the signal price. Confirm what actually happened with your broker."*
- If stock hits **upper circuit** on buy signal day → confirmation screen shows:
  > ⚠️ *"Upper Circuit Alert: [STOCK] hit its upper circuit limit today. You may not have been able to purchase at the signal price. Confirm your actual purchase with your broker."*
- Circuit warnings included in 5 PM notification and logged in signal log
- Trader still confirms normally — system does not auto-cancel the signal

**Stock Suspension or Delisting**
- If EOD data returns no price for a stock for **3 consecutive trading days** → detected as possible suspension/delisting
- Super Admin receives **immediate WhatsApp + Email alert**
- Affected trader receives alert to check with their broker
- Stock flagged with red ⚠️ badge in portfolio — no new signals generated
- If stock in watchlist with no open position → automatically **deactivated** with note
- Super Admin can manually mark a stock as suspended from admin panel

---

## 4. Market Holiday Handling

### 4.1 Holiday Calendar — 3-Layer System

**Layer 1 — Annual Fetch + Weekly Auto-Refresh**
- NSE official holiday calendar fetched once at **start of each year** and stored centrally
- Every **Monday at 8:00 AM IST** → system re-fetches NSE holiday calendar and compares with stored version
- If any change detected → calendar updated automatically + change logged with date, time, and what changed
- Super Admin receives **WhatsApp + Email alert at 8:00 AM** if any calendar change is detected

**Layer 2 — Super Admin Manual Override**
- Super Admin can **add, remove, or edit any holiday** from the admin panel at any time
- Handles same-day surprise holidays (national mourning, SEBI special declaration etc.)
- Every manual change logged with timestamp and admin tag
- When Super Admin adds a holiday manually → system immediately sends WhatsApp + Email to all active traders

**Layer 3 — Pre-Scan Safety Check**
- Every day at **4:25 PM IST** (5 minutes before scan) → system checks if today is a holiday
- If today IS a holiday → scan skipped, traders notified
- If Super Admin adds today as a holiday **after scan already started** → scan immediately aborted, partial results discarded, traders notified

### 4.2 Holiday Day Behaviour
- Scan engine does **not run** on market holidays and weekends
- Dashboard shows prominent banner: *"Market closed today — [Holiday Name] — No signals generated"*
- System sends **WhatsApp + Email** to all active traders
- No signals, no confirmations required on market holidays
- **Inactivity counter counts only market open days** — weekends and holidays completely ignored
- Example: if trader last confirmed Thursday and Monday/Tuesday are holidays, Day 1 of inactivity starts Wednesday

---

## 5. User Roles

### 5.1 Super Admin
- Single super admin: **aaanurag@yahoo.com** | Password: **Anurag75*** | Mobile: **9303121500**
- Creates and manages all trader accounts — **no self-registration allowed**
- Full access to any trader's profile, portfolio, watchlist, signals, capital log
- Can reset passwords, change profile details, adjust capital, activate/pause/suspend accounts
- **Can change their own password** from the Super Admin profile page
- Can manually trigger data re-fetch for entire application
- Can enter any trader's confirmation screen and submit on their behalf
- Can add manual trades on behalf of any trader
- Receives automatic alerts: scan failures, trader auto-pause, trader auto-suspension, holiday calendar changes, stock suspensions
- System-wide analytics dashboard: active traders, total signals, pending confirmations, data feed status
- Can override any trader's risk % setting

### 5.2 Trader
- Cannot self-register — account created by Super Admin only
- On first login: **forced** to change password and enter starting capital before accessing dashboard
- Watchlist building on first login is optional — can be done anytime
- Can manage own profile, capital, watchlist, notifications, risk % setting
- Can trigger manual data re-fetch (applies to all users)
- Receives signals via WhatsApp and/or Email per their preference
- Can pause their own account anytime
- Can enter manual trades at any time independent of system signals

---

## 6. Trader Profile

| Field | Details | Editable By |
|---|---|---|
| Full Name | Text | Trader + Admin |
| Email Address | Unique, login + notifications | Admin only |
| Mobile Number | WhatsApp alerts | Trader + Admin |
| Password | Encrypted, bcrypt | Trader (forced change on first login) |
| Account Status | Active / Paused / Suspended | Trader (pause only) + Admin (all) |
| Starting Capital (₹) | Entered on first login | Trader + Admin |
| Available Capital (₹) | Auto-calculated | System only |
| Risk % Per Trade | Default 1%, range 0.5%–5% | Trader + Admin |
| Notification: Email | ON/OFF | Trader + Admin |
| Notification: WhatsApp | ON/OFF | Trader + Admin |
| Watchlist | Up to 30 active NSE/BSE stocks | Trader + Admin |
| Date Joined | Set at account creation | Admin only |

### 6.1 Capital Management
- Trader can **freely add or reduce capital** anytime — no approval needed
- **Every capital change is logged** with: amount, type (deposit/withdrawal/buy/sell/admin-adjust), date, time, and who made the change (trader or admin)
- Full capital history visible to trader in profile and to admin in trader detail view
- Available capital = Starting capital + all deposits − all withdrawals − total value of open positions

### 6.2 Watchlist Rules
- Maximum **30 active stocks** at any time
- Trader can **deactivate** a stock to make room for a new one
- **Cannot deactivate a stock with an open position** — trader must first confirm exit of that position
- Deactivated stocks remain in system history but do not receive signals
- Stock search by company name or NSE/BSE ticker symbol
- System validates ticker exists in NSE/BSE before adding
- On adding new stock → 10 years of historical data fetched centrally if not already stored
- Watchlist changes take effect from **next day's scan**

---

## 7. Account Status & Lifecycle

| Status | Who Sets | Trader Can Login | Tips Sent | Portfolio Tracked |
|---|---|---|---|---|
| Active | Admin / System | ✅ Yes | ✅ Yes | ✅ Yes |
| Paused | Trader (self) or System (auto) | ✅ Yes | ❌ No | ✅ Yes |
| Suspended | System (auto) or Admin | ❌ No | ❌ No | ✅ Yes |

### 7.1 Auto-Pause & Auto-Suspend Rules
- **Day 5** of no signal confirmation (market open days only) → WhatsApp + Email warning:
  *"You have not confirmed signals for 5 trading days — your account will be auto-paused in 2 days. Please log in and confirm."*
- **Day 7** → account **auto-paused**. Tips stop. Super Admin notified.
- **Day 12** (5 open days after pause) → WhatsApp + Email warning:
  *"Your account is paused — you will be auto-suspended in 3 days if no action taken."*
- **Day 15** → account **auto-suspended**. Trader cannot login. Final message sent:
  *"Your account has been suspended. Please contact admin at aaanurag@yahoo.com or +91 9303121500 to reactivate."* Super Admin notified.
- When paused: **complete silence** — no signals, no exit alerts, no notifications of any kind
- Trader can still **login while paused** and update pending confirmations to reactivate
- Inactivity counter does **not** increment on no-signal days or market holidays

---

## 8. Daily Signal Workflow

### 8.0 Manual Trade Entry — Independent of System Signals
- A trader can **manually record any buy or sell** at any time from their portfolio screen — completely independent of whether the system generated a signal
- Covers: personal judgement trades, circuit freeze situations, partial sells, additional purchases

**Manual Buy Entry fields:**
- Stock (searchable from any NSE/BSE stock), Date of purchase, Purchase price per share, Quantity, Notes (optional)

**Manual Sell Entry fields:**
- Stock (from open positions), Date of sale, Sale price per share, Quantity sold (partial allowed), Notes (optional)

**System behaviour on manual entry:**
- Manual buy → creates new position row, deducts cost from available capital, logs in capital log tagged *"Manual Entry"* with 🖊️ icon
- Manual sell (full) → closes position, returns capital, logs P&L
- Manual sell (partial) → reduces qty, returns partial capital, remaining position stays open and continues receiving exit signals
- Manual entries clearly marked with 🖊️ icon throughout portfolio and capital log
- Manual entries do NOT affect signal generation logic
- Super Admin can enter manual trades on behalf of any trader

### 8.1 End of Day Scan (4:30 PM IST, Mon–Fri, market days only)
1. Pre-scan check at 4:25 PM — verify today is not a holiday
2. Fetch latest EOD prices for all stocks across all watchlists (via cascade data sources)
3. Compute all indicators and signal flags — stored centrally in stock_prices table
4. For each **active trader's watchlist** → read pre-computed `buy_signal` flags
5. Check all **open positions** for `any_exit_signal` flags
6. Skip stocks with unconfirmed pending signals
7. Prepare per-trader signal list (BUY signals + EXIT alerts)
8. Log scan result: stocks scanned, signals generated, errors, source used, time completed

### 8.2 Notification (5:00 PM IST)

**When signals exist (buy or exit):**
- One WhatsApp AND/OR Email containing:
  - *"Hi [Name], today's Channel Breakout signals from your watchlist are ready."*
  - One clickable secure permanent link to open confirmation dashboard directly
  - No detailed stock information in message — all detail is on the dashboard

**When NO signals exist:**
- One WhatsApp AND/OR Email containing:
  - *"Hi [Name], today's scan is complete. No Channel Breakout signals from your watchlist today. No exit signals. No action required."*
  - **No link sent** on no-signal days — nothing to confirm
  - Inactivity counter does NOT increment on no-signal days

**Secure Link Rules:**
- Link contains a **permanent token** — no expiry, no time limit
- Same link stays active until trader clicks **[SUBMIT ALL CONFIRMATIONS]**
- Link deactivates on SUBMIT or account pause/suspension
- Link opens confirmation screen **directly without requiring manual login**
- Trader can return to same link hours or days later and change entries before submitting

### 8.3 Confirmation Dashboard

**Section 1 — BUY SIGNALS (top of page)**

Displayed as cards on mobile, table on desktop:

| Stock | Signal Price | 55D High | Trailing Stop | ADX | Flat Days | Suggested Qty | Your Qty | Est. Cost | Action |
|---|---|---|---|---|---|---|---|---|---|
| TATAMOTOR | ₹924.50 | ₹921.00 | ₹887.50 | 28.4↑ | 7 days | 50 | [_50_] | ₹46,225 | [✅ I Bought It] [❌ I Did Not Buy] |

**Section 2 — EXIT ALERTS (below buy signals)**

| Stock | Exit Reason | All Open Positions | Total Qty | Entry Value | Exit Price | Est. P&L | Action |
|---|---|---|---|---|---|---|---|
| WIPRO | Rejection Rule | Jan 5: 100 / Feb 12: 50 | [_150_] | ₹42,750 | ₹281.50 | −₹1,050 | [✅ I Sold It] [❌ I Did Not Sell] |

- All open positions in that stock shown and combined (exit-all rule)
- Qty editable — defaults to total of all open positions
- Circuit warnings and gap risk warnings shown as amber badges per stock row

### 8.4 Submit Rules
- Trader can freely change any row entry before submitting
- **[SUBMIT ALL CONFIRMATIONS]** button at bottom of page
- Button is **greyed out and unclickable** until every single row (buy AND exit) is actioned
- Live counter shown: *"X of Y signals still need your input"*
- Once all rows actioned → [SUBMIT] activates (turns green)
- Once [SUBMIT] clicked → all entries **locked permanently** for that day — no changes
- Only after [SUBMIT] → next day's tips and notifications begin flowing
- Trader can also access confirmation screen directly inside the app anytime (not just via notification link)

---

## 9. Portfolio Tracker

| Column | Details |
|---|---|
| Stock | Name + Ticker |
| Source | 🖊️ for manual, blank for signal |
| Entry Date | Date of each individual purchase |
| Entry Price | Price at signal/manual confirmation |
| Quantity | Shares held in this lot |
| Current Price | Latest EOD price |
| Current Value | Qty × Current Price |
| P&L (₹) | Gain/loss in rupees |
| P&L (%) | Percentage gain/loss |
| Trailing Stop | Current 20-day low (exit level) |
| Exit Signal | 🔴 if any exit condition active |
| Days Held | Trading days since entry |

Multiple open positions in same stock shown as **separate rows**.

Portfolio summary: Total invested, Total current value, Total unrealised P&L (₹ and %), Available cash, Active slots used (e.g. 18/30 stocks)

---

## 10. Backtesting Module

### 10.1 Inputs
- Select up to **7 stocks simultaneously** from central stock store
- Date range (up to 10 years)
- Starting capital (₹) — **shared pool** across all 7 stocks
- Position size: fixed ₹ amount OR % of capital per trade
- Risk % setting

### 10.2 Shared Capital Pool Logic
- Capital is shared — if RELIANCE uses ₹20,000 on Day 1, that ₹20,000 is unavailable for TCS same day
- System processes signals **day by day chronologically** across all selected stocks
- If insufficient capital for a signal → signal skipped and noted in trade log

### 10.3 Day-by-Day Simulation
Every single trading day shown in the table:

| Column | Description |
|---|---|
| Date | Trading date |
| Stock | Stock name + ticker |
| Close Price | EOD closing price |
| 55-Day High | Current 55-day channel high value |
| 55-Day Low | Current 55-day channel low value |
| 20-Day High | Current 20-day channel high value |
| 20-Day Low | Current 20-day channel low (trailing stop level) |
| ADX Value | ADX(20) reading for the day |
| ADX Rising | ↑ or ↓ indicator |
| Flat Days | Consecutive days 55-day high flat/declining |
| Buy Signal | ✅ Yes / — No |
| Exit: Rejection | ✅ Yes / — No |
| Exit: Trailing Stop | ✅ Yes / — No |
| Exit: ADX | ✅ Yes / — No |
| Action Taken | Buy / Sell / Hold / Skipped (capital) / — |
| Trade P&L | Shown on exit days only |

- All indicator values shown every day — even on no-signal days
- Days with buy/exit actions highlighted (green for buy, red for exit)
- Table exportable as CSV

### 10.4 Output — Combined Portfolio View
- Single combined equity curve chart (capital value over time across all 7 stocks)
- Buy/exit days marked on chart with annotations
- Summary: total trades, win rate, avg profit, avg loss, max drawdown, final capital, total return %
- Full trade log: date, stock, entry price, exit price, qty, days held, exit reason, P&L

---

## 11. Notifications — All Templates

| # | Type | Time | Content |
|---|---|---|---|
| 1 | Daily Signal | 5:00 PM | *"Hi [Name], today's Channel Breakout signals from your watchlist are ready. [LINK]"* |
| 2 | No Signal Day | 5:00 PM | *"Hi [Name], today's scan is complete. No Channel Breakout signals today. No exit signals. No action required."* (no link) |
| 3 | Market Holiday | Morning | *"Hi [Name], market is closed today for [Holiday Name]. No signals today. See you tomorrow!"* |
| 4 | Reminder | 9:00 AM | *"Hi [Name], yesterday's signals are still unconfirmed. Please update to receive today's tips: [LINK]"* |
| 5 | Inactivity Day 5 | Day 5 | *"Hi [Name], you have not confirmed signals for 5 trading days. Your account will be auto-paused in 2 days. Please log in: [LINK]"* |
| 6 | Inactivity Day 12 | Day 12 | *"Hi [Name], your account is currently paused. It will be auto-suspended in 3 days if no action is taken. Log in now: [LINK]"* |
| 7 | Auto-Suspended | Day 15 | *"Hi [Name], your account has been suspended due to inactivity. Please contact admin to reactivate: aaanurag@yahoo.com | +91 9303121500"* |
| 8 | Scan Failure | Immediate | Super Admin only: *"ALERT: Daily scan failed at 4:30 PM on [date]. Retry attempt [X/12] in 15 minutes. Source: [yfinance/NSE/BSE]. Login: [LINK]"* |
| 9 | Holiday Change | 8:00 AM Mon | Super Admin only: *"ALERT: NSE holiday calendar change detected. Please verify before market opens."* |
| 10 | Stock Suspended | Immediate | *"Important: No price data received for [STOCK] for 3 days. Please check with your broker whether this stock has been suspended or delisted."* |

---

## 12. Super Admin Panel

### 12.1 User Management
- Create trader accounts — system auto-sends welcome email with temporary password
- View/edit any trader's full profile
- Reset password, change status, adjust capital
- View any trader's watchlist, portfolio, signal history, capital log, notification log
- Enter any trader's confirmation screen and submit on their behalf
- Add manual trades on behalf of any trader

### 12.2 System Dashboard
- Live data feed status: last successful fetch, source used, time, next scheduled scan
- Manual re-fetch button with source selector (yfinance / NSE Bhavcopy / BSE Bhavcopy)
- Retry attempt counter (X/12) with live countdown if retrying
- Pending confirmations: list of traders with unconfirmed signals + how many days pending
- Auto-pause/suspend queue: traders approaching day 5, 7, 12, 15 thresholds
- Scan log: date, time, stocks scanned, signals generated, errors, source used
- Background job progress for new stocks computing historical data
- Notification log: all WhatsApp/Email sent across all traders

### 12.3 Market Holiday Management
- View NSE holiday calendar for current year (auto-fetched)
- Super Admin can manually add/remove/edit holidays anytime
- Every manual change logged with timestamp

### 12.4 Super Admin Profile
- Can change own password from Super Admin profile page
- Email locked (aaanurag@yahoo.com)
- Mobile number editable

---

## 13. Technology Stack (All Free Tier)

| Layer | Technology | Free Plan |
|---|---|---|
| Frontend | React.js + Vite + TailwindCSS | **Vercel** — free forever |
| Backend | Python FastAPI | **Render.com** — free tier |
| Database | PostgreSQL | **Supabase** — free (500MB, built-in auth) |
| Stock Data Primary | yfinance Python library | Free, no API key, NSE (.NS) / BSE (.BO) |
| Stock Data Backup 1 | NSE Bhavcopy CSV | Free, direct from nseindia.com |
| Stock Data Backup 2 | BSE Bhavcopy CSV | Free, direct from bseindia.com |
| WhatsApp | MSG91 WhatsApp Business API | Existing account |
| Email | Brevo (Sendinblue) | Free — 300 emails/day |
| Scheduler | Render Cron Jobs | Free — triggers 4:30 PM IST scan |
| Authentication | Supabase Auth (JWT) | Built-in, free |

---

## 14. Key Business Rules Summary

1. No trader self-registration — Super Admin creates all accounts
2. First login: trader must change password and enter starting capital (mandatory)
3. Maximum 30 **active** stocks per trader watchlist at any time
4. Cannot deactivate a stock with an open position — must confirm exit first
5. Trader must submit ALL confirmations before new signals are issued — partial submission does not count
6. All 3 BUY conditions must be TRUE simultaneously for a signal to fire
7. When any EXIT signal fires — ALL open positions in that stock exit simultaneously
8. New BUY signal for a stock is ignored if that stock has an unconfirmed pending signal
9. Fresh BUY signal valid even if confirmed open positions exist in same stock (multiple lots allowed)
10. Position sizing: `(Available Capital × Risk%) ÷ (Entry Price − 20-day low)` — always editable
11. Capital changes (add/reduce) are free — no approval — all logged with date, time, who made change
12. Auto-pause at day 7 inactivity, auto-suspend at day 15 — warnings at day 5 and day 12
13. Inactivity counter counts **market open days only** — holidays and weekends ignored
14. Inactivity counter does NOT increment on no-signal days
15. When paused — complete silence — no signals, no exit alerts, no notifications
16. Data retry: 12 attempts every 15 minutes → NSE Bhavcopy → BSE Bhavcopy (auto cascade)
17. Both Super Admin and any trader can trigger manual re-fetch (applies to entire application)
18. All stock indicators and signal flags pre-computed centrally once per day — never recalculated per trader or per backtest
19. Notification link is permanent — no expiry — deactivates only on SUBMIT or account pause/suspension
20. [SUBMIT] button activates only when every single buy AND sell row has been actioned
21. Once [SUBMIT] clicked — all entries locked permanently for that day
22. Manual trade entry available anytime independent of system signals — tagged with 🖊️
23. Upper/lower circuit warnings shown on confirmation screen — signal not auto-cancelled
24. Stock suspension detected after 3 consecutive days of missing price data
25. Gap risk warning shown when exit fires after holiday and stock gapped down >2%
26. All trader screens are mobile-first and fully responsive (minimum 375px width)

---

## 15. Mobile Responsiveness — Mandatory

### 15.1 Confirmation Screen (Highest Priority)
- Opens directly from WhatsApp/Email link on trader's phone
- Each buy/sell row displayed as a **card** on mobile — one card per stock, stacked vertically
- Buy/sell buttons minimum **48px height** — large enough to tap with thumb
- [SUBMIT] button fixed at **bottom of screen** — always visible while scrolling
- Live counter at top: *"X of Y signals still need your input"*
- [SUBMIT] button greyed out until all rows actioned → turns green when ready
- Qty input field opens **numeric keyboard** on mobile automatically

### 15.2 Dashboard (High Priority)
- Summary capital cards stack vertically on mobile (single column)
- Buy signals and exit alerts shown as cards
- **Bottom tab bar navigation** on mobile (Home, Portfolio, Watchlist, Backtest, Profile)
- Left sidebar on desktop

### 15.3 Portfolio Page (High Priority)
- Open positions displayed as **cards on mobile** — no wide tables
- Each card shows: stock name, entry price, current price, qty, P&L, exit alert badge
- Summary totals shown as sticky header card at top

### 15.4 All Other Trader Pages
- All pages responsive at minimum 375px width
- No horizontal scrolling on any page
- All forms use full-width inputs on mobile
- Minimum 14px font on mobile

---

## 16. Out of Scope (Version 1)

- Automatic order placement via broker API
- Options or futures trading
- Intraday signals (EOD only)
- Native mobile app (mobile-responsive web only)
- Payment / subscription billing
- US or global market data
- AI/ML stock recommendations
- SMS notifications (WhatsApp + Email only)

---

## 17. Developer Handoff — AI Build Prompt

*Copy the entire block below and paste into Claude Code or any AI coding assistant:*

```
Build a complete full-stack web application using these files
in this project folder:
- PRD.md        → full product requirements (PRD v3.0)
- schema.sql    → complete Supabase PostgreSQL database schema (14 tables)
- wireframes.md → all UI screen specifications (13 screens)

TECH STACK (all free tier):
- Frontend:   React.js + Vite + TailwindCSS → deploy Vercel
- Backend:    Python FastAPI → deploy Render.com
- Database:   Supabase (PostgreSQL + Auth + RLS)
- Stock Data: yfinance (primary), NSE Bhavcopy, BSE Bhavcopy
- WhatsApp:   MSG91 API
- Email:      Brevo (Sendinblue) free tier
- Scheduler:  Render Cron Job → 4:30 PM IST daily scan

DESIGN:
- White dominant (#FFFFFF backgrounds everywhere)
- Accent: #0F4C81 blue | Success: #16A34A | Danger: #DC2626
- Font: Inter (Google Fonts)
- Mobile-first. Confirmation + Dashboard + Portfolio = critical mobile.
- Bottom tab bar on mobile, left sidebar on desktop.

TRADING LOGIC — Courtney Smith Channel Breakout:
BUY signal (all 3 must be TRUE simultaneously):
  1. 55-day channel high flat or declining for 5+ consecutive days
  2. Today's close breaks above the 55-day channel high
  3. ADX(20) is rising today vs yesterday

EXIT signal (any 1 triggers full exit of ALL positions in that stock):
  1. Rejection Rule: no close above breakout channel within 2 days of entry
  2. Trailing Stop: close below 20-day channel low
  3. ADX Exit: ADX turns down from 40+

POSITION SIZING (Courtney Smith Fixed Fractional — Chapter 7):
  Suggested Qty = (Available Capital × Risk%) ÷ (Entry Price − 20-day low)
  Default Risk% = 1%, editable 0.5%–5%

ALL indicators and signal flags pre-computed once centrally per stock
per day and stored — never recalculated per trader or per backtest.

KEY BUSINESS RULES:
1.  No self-registration — Super Admin creates all accounts
2.  Super Admin: aaanurag@yahoo.com | Anurag75* | +91 9303121500
3.  First login: force password change + capital entry (mandatory)
4.  Max 30 active stocks per trader watchlist
5.  Cannot deactivate stock with open position — must exit first
6.  Must submit ALL confirmations (full SUBMIT) before new tips flow
7.  Any exit signal fires → ALL positions in that stock exit simultaneously
8.  New BUY signal ignored if that stock has unconfirmed pending signal
9.  Fresh BUY valid even if confirmed open position exists in same stock
10. Capital changes free, no approval, all logged with date/time/user
11. Inactivity counter counts market open days only (ignores holidays + no-signal days)
12. Auto-pause day 7 | Auto-suspend day 15
13. Warnings: day 5 (pause warning) and day 12 (suspend warning)
14. Complete silence when paused
15. Data cascade: yfinance → NSE Bhavcopy → BSE Bhavcopy
16. API retry: every 15 minutes, 12 attempts max (4:30 PM–7:30 PM)
17. Both Super Admin and any trader can trigger manual re-fetch
18. Holiday calendar: annual fetch + weekly Monday 8AM refresh + manual override
19. Pre-scan safety check at 4:25 PM
20. Upper/lower circuit warnings on confirmation screen
21. Stock suspension detected after 3 days missing data
22. Manual trade entry anytime independent of signals (tagged 🖊️)
23. Permanent notification link — deactivates only on SUBMIT or pause/suspension
24. No-signal days: different message, no link sent
25. SUBMIT button activates ONLY when every buy and sell row actioned
26. Once SUBMIT clicked — entries locked permanently for that day
27. All trader screens mobile-first, fully responsive (min 375px)
28. Gap risk warning when exit fires after holiday gap-down >2%
29. Super Admin can change own password from profile page

Read all 3 files completely before writing any code.
Ask for clarification on anything unclear before starting.
Build in this order:
1. Supabase: run schema.sql (14 tables)
2. Backend FastAPI: scan engine, signal logic, all API routes
3. Frontend React: all 13 screens per wireframes
4. Integrations: MSG91, Brevo, yfinance, NSE/BSE Bhavcopy
5. Scheduler: Render Cron Job 4:30 PM IST
6. Deploy: Vercel (frontend) + Render (backend) + Supabase (DB)
```
