# UI Wireframes v3.0 — Final — Approved for Production
## Courtney Smith Channel Breakout Trading Platform
**Stack:** React.js + Vite + TailwindCSS → Vercel
**Theme:** White dominant — #FFFFFF primary, #0F4C81 accent blue
**Priority:** Mobile-first. Confirmation, Dashboard, Portfolio are critical mobile screens.

---

## GLOBAL DESIGN TOKENS

```css
/* Paste into tailwind.config.js → theme → extend → colors */
colors: {
  brand:   '#0F4C81',   /* primary blue — buttons, active nav */
  success: '#16A34A',   /* green — buy signals, positive P&L */
  danger:  '#DC2626',   /* red — exit alerts, negative P&L */
  warning: '#D97706',   /* amber — pending, circuit alerts */
  bg:      '#F8FAFC',   /* page background */
  card:    '#FFFFFF',   /* card background */
  border:  '#E2E8F0',   /* card/input borders */
  text:    '#1E293B',   /* primary text */
  muted:   '#64748B',   /* secondary text, labels */
}
/* Font: Inter from Google Fonts */
/* Card: rounded-xl shadow-sm border border-border bg-card */
/* Button primary: bg-brand text-white rounded-lg px-4 py-3 min-h-[48px] */
/* Button success: bg-success text-white rounded-lg px-4 py-3 min-h-[48px] */
/* Button danger:  bg-danger  text-white rounded-lg px-4 py-3 min-h-[48px] */
/* Input: border border-border rounded-lg px-3 py-3 w-full text-base */
```

---

## MOBILE NAVIGATION (all trader screens)
```
Bottom tab bar — fixed at bottom on mobile:
┌─────────────────────────────────────────┐
│  🏠      📊      🔍      📈      👤     │
│ Home  Portfolio Watchlist Backtest Profile│
└─────────────────────────────────────────┘

Desktop: Left sidebar — same 5 items + logo at top + Logout at bottom
Sidebar width: 240px, white background, brand blue active state
```

---

## SCREEN 1 — LOGIN
**Route:** `/login` | Public | Mobile + Desktop

```
White page, centered card (max-width 400px)

┌─────────────────────────────────────────┐
│                                         │
│    [Logo — Chart icon + App Name]       │
│  Courtney Smith Channel Breakout        │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │                                   │  │
│  │  Email Address                    │  │
│  │  [_________________________________] │
│  │                                   │  │
│  │  Password              [Show/Hide]│  │
│  │  [_________________________________] │
│  │                                   │  │
│  │  [        LOGIN         ]         │  │
│  │   (full width, brand blue button) │  │
│  │                                   │  │
│  │  Forgot Password?                 │  │
│  └───────────────────────────────────┘  │
│                                         │
│  ⓘ Accounts are created by admin only. │
│    Contact: aaanurag@yahoo.com          │
└─────────────────────────────────────────┘
```
**Behaviour:**
- Error: red border on field + error text below
- On success: redirect to `/first-login` if first_login_complete=false, else `/dashboard`
- Forgot password → Supabase Auth reset email

---

## SCREEN 2 — FIRST LOGIN ONBOARDING
**Route:** `/first-login` | Forced on first login | Mobile + Desktop

```
Step 1 of 2 shown as progress dots at top

STEP 1 — CHANGE PASSWORD
┌─────────────────────────────────────────┐
│  Welcome, [Name]! 👋                    │
│  Let's get your account set up.         │
│                                         │
│  ● ○  Step 1 of 2                       │
│                                         │
│  New Password                           │
│  [_____________________________________]│
│  Confirm Password                       │
│  [_____________________________________]│
│                                         │
│  [     SET PASSWORD & CONTINUE    ]     │
└─────────────────────────────────────────┘

STEP 2 — ENTER STARTING CAPITAL
┌─────────────────────────────────────────┐
│  ○ ●  Step 2 of 2                       │
│                                         │
│  Enter Your Starting Capital            │
│  This is the amount you will trade with │
│                                         │
│  ₹  [_______________________________]   │
│     (numeric keyboard on mobile)        │
│                                         │
│  Risk % Per Trade (default 1%)          │
│  [1.0] % (editable, range 0.5 - 5.0)   │
│                                         │
│  [     SAVE & GO TO DASHBOARD     ]     │
│                                         │
│  You can change these anytime in        │
│  your profile.                          │
└─────────────────────────────────────────┘
```

---

## SCREEN 3 — TRADER DASHBOARD (HOME)
**Route:** `/dashboard` | Trader | MOBILE PRIORITY

### Mobile Layout
```
┌─────────────────────────────────────────┐
│  Good evening, Rajesh 👋        [🔔 2]  │
│  Sunday, 19 Apr 2026                    │
├─────────────────────────────────────────┤
│                                         │
│  [DATA FEED STATUS BAR — if issue]      │
│  ⚠️ Last fetch: yfinance 4:47 PM ✅     │
│                                         │
│  ┌──────────┐  ┌──────────┐             │
│  │Available │  │Invested  │             │
│  │Capital   │  │          │             │
│  │₹75,500   │  │₹1,24,500 │             │
│  └──────────┘  └──────────┘             │
│  ┌──────────┐  ┌──────────┐             │
│  │Total P&L │  │Slots Used│             │
│  │+₹8,200   │  │ 5 / 30   │             │
│  │+6.2% 📈  │  │          │             │
│  └──────────┘  └──────────┘             │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │ 🟢 BUY SIGNALS TODAY (3)        │    │
│  │ ⚠️ Action required              │    │
│  │                                 │    │
│  │ TATAMOTOR  ₹924.50  ADX 28↑    │    │
│  │ INFY       ₹1,842   ADX 31↑    │    │
│  │ HDFCBANK   ₹1,654   ADX 26↑    │    │
│  │                                 │    │
│  │ [  GO TO CONFIRMATION  →  ]     │    │
│  └─────────────────────────────────┘    │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │ 🔴 EXIT ALERTS TODAY (1)        │    │
│  │ WIPRO — Rejection Rule          │    │
│  │ [  GO TO CONFIRMATION  →  ]     │    │
│  └─────────────────────────────────┘    │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │ OPEN POSITIONS (5)  [View All→] │    │
│  │ RELIANCE  +4.2%  ₹28,900       │    │
│  │ TCS       +1.8%  ₹27,600       │    │
│  │ + 3 more...                     │    │
│  └─────────────────────────────────┘    │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │ DATA FEED   Last: 4:32 PM ✅    │    │
│  │ Source: yfinance  [Re-fetch]    │    │
│  └─────────────────────────────────┘    │
├─────────────────────────────────────────┤
│  🏠    📊    🔍    📈    👤             │
└─────────────────────────────────────────┘
```
**Market closed banner (holidays):**
```
┌─────────────────────────────────────────┐
│  🏛️  Market Closed Today — Diwali       │
│     No signals generated.               │
└─────────────────────────────────────────┘
```

---

## SCREEN 4 — CONFIRMATION SCREEN
**Route:** `/confirm/:token` | Trader | HIGHEST MOBILE PRIORITY
**Access:** Via permanent link in WhatsApp/Email OR direct from dashboard

### Mobile Layout — Card per stock
```
┌─────────────────────────────────────────┐
│  ← Back    CONFIRM TODAY'S SIGNALS      │
│            19 Apr 2026                  │
├─────────────────────────────────────────┤
│                                         │
│  ┌─── PROGRESS ─────────────────────┐  │
│  │  2 of 4 signals actioned         │  │
│  │  ████████░░░░░░░  50%            │  │
│  └───────────────────────────────────┘  │
│                                         │
│  ════ BUY SIGNALS (3) ════              │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │ 🟢 TATA MOTORS (TATAMOTOR)      │    │
│  │ Signal Price:  ₹924.50          │    │
│  │ 55-Day High:   ₹921.00          │    │
│  │ Trailing Stop: ₹887.50          │    │
│  │ ADX: 28.4 ↑   Flat: 7 days      │    │
│  │                                 │    │
│  │ Suggested Qty:  50 shares       │    │
│  │ Est. Cost: ₹46,225              │    │
│  │                                 │    │
│  │ Your Qty: [___50___]            │    │
│  │           (tap to edit)         │    │
│  │                                 │    │
│  │ [✅ I BOUGHT IT ]               │    │
│  │ [❌ I DID NOT BUY]              │    │
│  └─────────────────────────────────┘    │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │ 🟢 INFOSYS (INFY)               │    │
│  │ ⚠️ Upper Circuit Warning        │    │
│  │ Signal Price: ₹1,842.00         │    │
│  │ ADX: 31.2 ↑   Flat: 6 days      │    │
│  │                                 │    │
│  │ Your Qty: [___20___]            │    │
│  │                                 │    │
│  │ [✅ I BOUGHT IT ]               │    │
│  │ [❌ I DID NOT BUY]              │    │
│  └─────────────────────────────────┘    │
│                                         │
│  ════ EXIT ALERTS (1) ════              │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │ 🔴 WIPRO                        │    │
│  │ Exit Reason: Rejection Rule     │    │
│  │ ⚠️ Gap Risk: Opened 3.2% lower  │    │
│  │                                 │    │
│  │ All Open Positions:             │    │
│  │ Jan 5 — 100 qty @ ₹285.00      │    │
│  │ Feb 12 — 50 qty @ ₹291.00      │    │
│  │                                 │    │
│  │ Total Qty to Sell: [__150__]    │    │
│  │ Entry Value:  ₹42,750           │    │
│  │ Exit Price:   ₹281.50           │    │
│  │ Est. P&L:     -₹1,050 (-2.4%)  │    │
│  │                                 │    │
│  │ [✅ I SOLD IT    ]              │    │
│  │ [❌ I DID NOT SELL]             │    │
│  └─────────────────────────────────┘    │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │  [SUBMIT ALL CONFIRMATIONS]     │    │
│  │  (greyed out — 2 rows pending)  │    │
│  │  "Complete 2 more entries       │    │
│  │   above to enable submit"       │    │
│  └─────────────────────────────────┘    │
│                                         │
│  ⓘ Once submitted, entries are locked. │
│    Tomorrow's tips sent after submit.  │
└─────────────────────────────────────────┘
```
**When all rows actioned — SUBMIT activates:**
```
│  [  ✅ SUBMIT ALL CONFIRMATIONS  ]      │
│     (green, full width, large button)  │
```
**After SUBMIT — locked screen:**
```
│  ✅ Submitted at 6:42 PM                │
│  All entries locked. Tomorrow's tips   │
│  will be sent at 5 PM.                 │
```

---

## SCREEN 5 — PORTFOLIO
**Route:** `/portfolio` | Trader | MOBILE PRIORITY

### Mobile Layout — Cards
```
┌─────────────────────────────────────────┐
│  MY PORTFOLIO                [Export ↓] │
├─────────────────────────────────────────┤
│  ┌─────────────────────────────────┐    │
│  │ Invested   Current    P&L       │    │
│  │ ₹1,24,500  ₹1,32,700  +₹8,200  │    │
│  │                        +6.6% 📈 │    │
│  │ Available: ₹75,500  Slots: 5/30 │    │
│  └─────────────────────────────────┘    │
│                                         │
│  OPEN POSITIONS                         │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │ RELIANCE · NSE        +4.2% 📈  │    │
│  │ Entry: ₹2,890 · Qty: 10         │    │
│  │ Current: ₹3,012 · +₹1,220      │    │
│  │ Held: 8 days                    │    │
│  │ Stop: ₹2,810 (20-day low)       │    │
│  └─────────────────────────────────┘    │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │ WIPRO · NSE     🔴 EXIT ALERT   │    │
│  │ Rejection Rule triggered        │    │
│  │ Entry: ₹285.00 · Qty: 150       │    │
│  │ Current: ₹281.50 · -₹525       │    │
│  │ [GO TO CONFIRMATION →]          │    │
│  └─────────────────────────────────┘    │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │ 🖊️ BAJAJFINSV · MANUAL ENTRY   │    │
│  │ Entry: ₹7,200 · Qty: 5          │    │
│  │ Current: ₹7,450 · +₹1,250      │    │
│  └─────────────────────────────────┘    │
│                                         │
│  CLOSED POSITIONS ─────────────────     │
│  [Last 30 days ▾]                       │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │ BAJAJ · Closed 15 Apr  +9.6%   │    │
│  │ ₹7,200 → ₹7,890 · 18 days      │    │
│  │ Exit: Trailing Stop             │    │
│  └─────────────────────────────────┘    │
├─────────────────────────────────────────┤
│  🏠    📊    🔍    📈    👤             │
└─────────────────────────────────────────┘
```

---

## SCREEN 6 — MANUAL TRADE ENTRY
**Route:** `/portfolio/manual-entry` | Trader | Mobile + Desktop

```
┌─────────────────────────────────────────┐
│  ← Back    MANUAL TRADE ENTRY           │
│            🖊️ Independent of signals    │
├─────────────────────────────────────────┤
│                                         │
│  Trade Type                             │
│  ● BUY     ○ SELL                       │
│                                         │
│  Stock                                  │
│  [Search NSE/BSE stock...          🔍]  │
│                                         │
│  Date of Trade                          │
│  [19 Apr 2026  📅]                      │
│                                         │
│  Price Per Share (₹)                    │
│  [_____________________________________]│
│                                         │
│  Quantity                               │
│  [_____________________________________]│
│                                         │
│  Total Value: ₹0                        │
│  (auto-calculated)                      │
│                                         │
│  Notes (optional)                       │
│  [_____________________________________]│
│                                         │
│  [      SAVE MANUAL TRADE       ]       │
│                                         │
│  ⓘ Manual trades are tagged with 🖊️    │
│    and do not affect signal generation. │
└─────────────────────────────────────────┘
```
**For SELL — additional field:**
```
│  Select Position to Close               │
│  ┌─────────────────────────────────┐    │
│  │ ● RELIANCE — Jan 5 — 100 qty   │    │
│  │ ○ RELIANCE — Feb 12 — 50 qty   │    │
│  └─────────────────────────────────┘    │
│  Qty to Sell (partial allowed)          │
│  [____50____]  of 100 available         │
```

---

## SCREEN 7 — WATCHLIST
**Route:** `/watchlist` | Trader | Mobile + Desktop

```
┌─────────────────────────────────────────┐
│  MY WATCHLIST         18 / 30 active    │
├─────────────────────────────────────────┤
│                                         │
│  [🔍 Search to add stock...        ]    │
│                                         │
│  ACTIVE STOCKS (18)                     │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │ RELIANCE · NSE    Added 01 Jan  │    │
│  │ [Deactivate]                    │    │
│  └─────────────────────────────────┘    │
│  ┌─────────────────────────────────┐    │
│  │ TCS · NSE         Added 01 Jan  │    │
│  │ [Deactivate]                    │    │
│  └─────────────────────────────────┘    │
│                                         │
│  INACTIVE STOCKS (3)                    │
│  ┌─────────────────────────────────┐    │
│  │ WIPRO · NSE  Deactivated 10 Mar │    │
│  │ [Reactivate]                    │    │
│  └─────────────────────────────────┘    │
│                                         │
│  SEARCH RESULTS (shown on search)       │
│  ┌─────────────────────────────────┐    │
│  │ TATAMOTOR · Tata Motors · NSE   │    │
│  │ [+ Add to Watchlist]            │    │
│  └─────────────────────────────────┘    │
│                                         │
│  ⓘ Cannot deactivate stocks with open  │
│    positions. Max 30 active at once.   │
└─────────────────────────────────────────┘
```

---

## SCREEN 8 — BACKTEST
**Route:** `/backtest` | Trader | Mobile + Desktop

```
┌─────────────────────────────────────────┐
│  BACKTEST — Channel Breakout Strategy   │
├─────────────────────────────────────────┤
│                                         │
│  SETUP                                  │
│  Stocks (up to 7)                       │
│  [+ Add Stock] [RELIANCE ×] [TCS ×]    │
│                                         │
│  Date Range                             │
│  From [01 Apr 2015]  To [19 Apr 2025]  │
│                                         │
│  Starting Capital (₹)                   │
│  [1,00,000]  (shared across all stocks) │
│                                         │
│  Position Size                          │
│  ● Fixed ₹ [20,000]                    │
│  ○ % of capital [20%]                  │
│                                         │
│  Risk % [1.0]                           │
│                                         │
│  [        RUN BACKTEST        ]         │
│                                         │
│  ─────── COMBINED RESULTS ──────────   │
│                                         │
│  ┌───────┐ ┌───────┐ ┌───────┐ ┌─────┐ │
│  │Trades │ │Win    │ │Max    │ │Total│ │
│  │  42   │ │Rate   │ │Draw-  │ │Rtrn │ │
│  │       │ │54.8%  │ │down   │ │     │ │
│  │       │ │       │ │-18.4% │ │+84% │ │
│  └───────┘ └───────┘ └───────┘ └─────┘ │
│                                         │
│  EQUITY CURVE                           │
│  ┌─────────────────────────────────┐    │
│  │ 📈 [Combined equity line chart] │    │
│  │ Buy markers: 🟢  Exit: 🔴       │    │
│  └─────────────────────────────────┘    │
│                                         │
│  DAY-BY-DAY LOG          [Export CSV ↓]│
│  ┌─────────────────────────────────┐    │
│  │Date│Stock│Close│55H│55L│20L│ADX│    │
│  │    │     │     │   │   │   │↑↓ │    │
│  ├────┴─────┴─────┴───┴───┴───┴───┤    │
│  │12Jan│RELI│2890 │2880│..│..│26↑│    │
│  │ BUY ✅ Qty:10 Cost:₹28,900      │    │
│  ├────┴─────┴─────┴───┴───┴───┴───┤    │
│  │13Jan│RELI│2910 │2880│..│..│28↑│    │
│  │ HOLD —                          │    │
│  └─────────────────────────────────┘    │
│  (all days shown, actions highlighted) │
└─────────────────────────────────────────┘
```

---

## SCREEN 9 — TRADER PROFILE
**Route:** `/profile` | Trader | Mobile + Desktop

```
┌─────────────────────────────────────────┐
│  MY PROFILE                             │
├─────────────────────────────────────────┤
│                                         │
│  PERSONAL DETAILS         [Save]        │
│  Full Name  [Rajesh Kumar          ]    │
│  Mobile     [+91 98765 43210       ]    │
│  Email      rajesh@email.com (locked)   │
│                                         │
│  NOTIFICATIONS                          │
│  Email Alerts     [ON  ●───]            │
│  WhatsApp Alerts  [OFF ───○]            │
│                                         │
│  RISK SETTING                           │
│  Risk % per trade  [1.0] %              │
│  Range: 0.5% – 5.0%                    │
│                                         │
│  CAPITAL                                │
│  Starting Capital:  ₹2,00,000           │
│  Available Capital: ₹75,500             │
│                                         │
│  Add Capital  ₹[___________] [Add +]   │
│  Reduce Capital ₹[_________] [Reduce -]│
│                                         │
│  CAPITAL HISTORY                        │
│  ┌─────────────────────────────────┐    │
│  │ 01 Apr  Deposit   +₹2,00,000   │    │
│  │         By: You                 │    │
│  │ 05 Apr  BUY RELI  -₹28,900     │    │
│  │         Signal — System         │    │
│  │ 10 Apr  BUY TCS   -₹27,600     │    │
│  │         🖊️ Manual Entry — You   │    │
│  └─────────────────────────────────┘    │
│                                         │
│  ACCOUNT                                │
│  [Change Password]                      │
│  [Pause My Account — stops all tips]    │
│                                         │
└─────────────────────────────────────────┘
```

---

## SCREEN 10 — SUPER ADMIN: USER MANAGEMENT
**Route:** `/admin/users` | Admin only

```
┌──────────────────────────────────────────────────────┐
│ ADMIN PANEL                     [+ Create New User]  │
│                                                      │
│ [🔍 Search traders by name or email...          ]    │
│                                                      │
│ ┌──────────────────────────────────────────────┐     │
│ │ Name      │Email    │Status  │Capital │Action│     │
│ ├──────────────────────────────────────────────┤     │
│ │ Rajesh K  │raj@..   │🟢Active│₹75,500 │[View]│     │
│ │ Priya S   │pri@..   │🟡Paused│₹12,000 │[View]│     │
│ │ Amir K    │ami@..   │🔴Susp. │₹0      │[View]│     │
│ └──────────────────────────────────────────────┘     │
│                                                      │
│ CREATE NEW USER                                      │
│ ┌──────────────────────────────────────────────┐     │
│ │ Full Name   [_____________________________]  │     │
│ │ Email       [_____________________________]  │     │
│ │ Mobile      [_____________________________]  │     │
│ │ Capital ₹   [_____________________________]  │     │
│ │ Email Notif [✓]   WhatsApp Notif [✓]         │     │
│ │                                              │     │
│ │ [  CREATE ACCOUNT & SEND WELCOME EMAIL  ]    │     │
│ └──────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────┘
```

---

## SCREEN 11 — SUPER ADMIN: TRADER DETAIL VIEW
**Route:** `/admin/users/:id` | Admin only

```
┌──────────────────────────────────────────────────────┐
│ ← Back    RAJESH KUMAR                               │
│           rajesh@email.com · +91 98765 43210         │
├──────────────────────────────────────────────────────┤
│ ┌──────────┐ ┌───────────┐ ┌──────────────────────┐  │
│ │ 🟢 Active│ │ ₹75,500   │ │ Email: ON             │  │
│ │[Change ▾]│ │[Adjust ₹] │ │ WhatsApp: OFF         │  │
│ └──────────┘ └───────────┘ └──────────────────────┘  │
│                                                      │
│ [Reset Password]  [Pause]  [Suspend]                 │
│ [Enter Confirmation Screen on behalf]                │
│ [Add Manual Trade on behalf]                         │
│                                                      │
│ WATCHLIST (18 active)            [Edit Watchlist]    │
│ RELIANCE, TCS, INFY, HDFC... +14 more               │
│                                                      │
│ OPEN POSITIONS (5)                                   │
│ [Same card layout as portfolio screen]               │
│                                                      │
│ CAPITAL LOG                                          │
│ [Same table as profile capital history]              │
│                                                      │
│ SIGNAL HISTORY (last 30 days)                        │
│ NOTIFICATION LOG                                     │
└──────────────────────────────────────────────────────┘
```

---

## SCREEN 12 — SUPER ADMIN: SYSTEM DASHBOARD
**Route:** `/admin/system` | Admin only

```
┌──────────────────────────────────────────────────────┐
│ SYSTEM OVERVIEW                                      │
├──────────────────────────────────────────────────────┤
│ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────────────┐  │
│ │Traders │ │Active  │ │Central │ │Signals Today   │  │
│ │  18    │ │  15    │ │Stocks  │ │     47         │  │
│ │        │ │        │ │  234   │ │                │  │
│ └────────┘ └────────┘ └────────┘ └────────────────┘  │
│                                                      │
│ DATA FEED STATUS                                     │
│ ┌──────────────────────────────────────────────┐     │
│ │ Last Scan:  19 Apr 2026  4:32 PM  ✅          │     │
│ │ Source: yfinance   Stocks: 234   Errors: 0   │     │
│ │                                              │     │
│ │ Manual Re-fetch:                             │     │
│ │ [yfinance] [NSE Bhavcopy] [BSE Bhavcopy]    │     │
│ │                                              │     │
│ │ Retry Status: ✅ Not retrying                │     │
│ └──────────────────────────────────────────────┘     │
│                                                      │
│ MARKET HOLIDAYS                                      │
│ ┌──────────────────────────────────────────────┐     │
│ │ Next Holiday: 01 May — Labour Day            │     │
│ │ [+ Add Holiday]  [Edit Calendar]             │     │
│ │ Last calendar refresh: Mon 14 Apr 8:00 AM    │     │
│ └──────────────────────────────────────────────┘     │
│                                                      │
│ PENDING CONFIRMATIONS                                │
│ ┌──────────────────────────────────────────────┐     │
│ │ Trader        │ Days Pending │ Action         │     │
│ ├──────────────────────────────────────────────┤     │
│ │ Priya Sharma  │ Day 5 ⚠️     │ [Send Warning] │     │
│ │ Amir Khan     │ Day 2        │ [Send Remind]  │     │
│ └──────────────────────────────────────────────┘     │
│                                                      │
│ BACKGROUND JOBS (new stocks computing)               │
│ ┌──────────────────────────────────────────────┐     │
│ │ ADANIPORTS  Computing 10yr history  67% ████░│     │
│ └──────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────┘
```

---

## SCREEN 13 — SUPER ADMIN: PROFILE
**Route:** `/admin/profile` | Admin only

```
┌──────────────────────────────────────────────────────┐
│ SUPER ADMIN PROFILE                                  │
├──────────────────────────────────────────────────────┤
│ Full Name:   Anurag                                  │
│ Email:       aaanurag@yahoo.com  (locked)            │
│ Mobile:      9303121500                              │
│                                                      │
│ [Change Password]                                    │
│                                                      │
│ Current Password  [_____________________________]    │
│ New Password      [_____________________________]    │
│ Confirm Password  [_____________________________]    │
│                                                      │
│ [    SAVE NEW PASSWORD    ]                          │
└──────────────────────────────────────────────────────┘
```

---

## NOTIFICATION MESSAGES — FINAL TEMPLATES

### Daily Signal (5 PM — signals exist)
```
Hi [Name], today's Channel Breakout signals
from your watchlist are ready.

Click to take action:
[https://app.yourdomain.com/confirm/TOKEN]
```

### Daily — No Signal Day (5 PM)
```
Hi [Name], today's scan is complete.
No Channel Breakout signals from your
watchlist today. No exit signals.
No action required.
```

### Market Holiday
```
Hi [Name], market is closed today for
[Holiday Name]. No signals today.
See you tomorrow!
```

### Reminder (9 AM — unconfirmed)
```
Hi [Name], yesterday's signals are still
unconfirmed. Please update to receive
today's tips:
[https://app.yourdomain.com/confirm/TOKEN]
```

### Inactivity Day 5
```
Hi [Name], you have not confirmed signals
for 5 trading days. Your account will be
auto-paused in 2 days. Please log in:
[https://app.yourdomain.com/confirm/TOKEN]
```

### Inactivity Day 12
```
Hi [Name], your account is currently paused.
It will be auto-suspended in 3 days if no
action is taken. Log in now:
[https://app.yourdomain.com/confirm/TOKEN]
```

### Auto-Suspended Day 15
```
Hi [Name], your account has been suspended
due to inactivity. Please contact admin
to reactivate:
aaanurag@yahoo.com | +91 9303121500
```

### Scan Failure (Super Admin only)
```
ALERT: Daily scan failed at 4:30 PM on
[Date]. Retry [X/12] in 15 minutes.
Source: [yfinance/NSE/BSE].
Login: [ADMIN LINK]
```

---

## AI DEVELOPER PROMPT — COPY THIS ENTIRE BLOCK

```
Build a complete full-stack web application using these files
in this project folder:
- PRD.md        → full product requirements (PRD v3.0)
- schema.sql    → complete Supabase PostgreSQL database schema
- wireframes.md → all UI screen specifications (this file)

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

BUILD ORDER:
1. Supabase: run schema.sql to create all 14 tables
2. Backend FastAPI: scan engine, signal logic, API routes
3. Frontend React: all 13 screens per wireframes
4. Integrations: MSG91, Brevo, yfinance, NSE/BSE Bhavcopy
5. Scheduler: Render Cron Job for 4:30 PM daily scan
6. Deploy: Vercel (frontend) + Render (backend) + Supabase (DB)

Read all 3 files completely before writing any code.
Ask for clarification on anything unclear before starting.
```
