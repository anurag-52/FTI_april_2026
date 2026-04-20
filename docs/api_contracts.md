# API Contracts
## Shared Reference — BACKEND-ENG ↔ FRONTEND-ENG

_This file is the single source of truth for all API request/response shapes._
_Updated by BACKEND-ENG as routes are built. Read by FRONTEND-ENG for wiring._

---

## Base URL
```
Development: http://localhost:8000
Production:  https://{render-service}.onrender.com
```

## Auth Header
```
Authorization: Bearer {JWT_TOKEN}
```
All routes except `/auth/login` and `/confirm/:token` require this header.

---

## AUTH

### POST /auth/login
**Request:**
```json
{ "email": "trader@email.com", "password": "password123" }
```
**Response 200:**
```json
{
  "access_token": "eyJ...",
  "user": {
    "id": "uuid",
    "full_name": "Rajesh Kumar",
    "role": "trader",
    "status": "active",
    "first_login_complete": false
  }
}
```
**Response 401:** `{ "detail": "Invalid credentials" }`

---

### POST /auth/change-password
**Request:**
```json
{ "new_password": "NewPass123!", "confirm_password": "NewPass123!" }
```
**Response 200:** `{ "message": "Password updated" }`

---

## TRADER PROFILE

### GET /me
**Response 200:**
```json
{
  "id": "uuid",
  "full_name": "Rajesh Kumar",
  "email": "rajesh@email.com",
  "mobile": "+91 98765 43210",
  "status": "active",
  "starting_capital": 200000.00,
  "available_capital": 75500.00,
  "risk_percent": 1.00,
  "notify_email": true,
  "notify_whatsapp": false,
  "inactivity_days": 0,
  "first_login_complete": true
}
```

---

### POST /me/capital
**Request:**
```json
{ "amount": 50000.00, "type": "DEPOSIT" }
```
`type`: `"DEPOSIT"` or `"WITHDRAWAL"`  
**Response 200:**
```json
{ "new_available_capital": 125500.00, "logged": true }
```

---

## SIGNALS

### GET /me/signals/today
**Response 200:**
```json
{
  "signal_date": "2026-04-19",
  "session_token": "perm_token_abc123",
  "total_rows": 4,
  "actioned_rows": 0,
  "submitted": false,
  "buy_signals": [
    {
      "id": "uuid",
      "stock": { "ticker_nse": "TATAMOTOR", "company_name": "Tata Motors" },
      "trigger_price": 924.50,
      "ch55_high_at_signal": 921.00,
      "ch20_low_at_signal": 887.50,
      "adx_at_signal": 28.4,
      "flat_days": 7,
      "suggested_qty": 50,
      "suggested_cost": 46225.00,
      "circuit_warning": false,
      "circuit_type": null,
      "confirmed": null,
      "confirmed_qty": null
    }
  ],
  "exit_signals": [
    {
      "id": "uuid",
      "stock": { "ticker_nse": "WIPRO", "company_name": "Wipro Ltd" },
      "signal_type": "EXIT_REJECTION",
      "trigger_price": 281.50,
      "gap_risk_warning": true,
      "gap_down_pct": 3.2,
      "open_positions": [
        { "entry_date": "2026-01-05", "qty": 100, "entry_price": 285.00 },
        { "entry_date": "2026-02-12", "qty": 50,  "entry_price": 291.00 }
      ],
      "total_qty": 150,
      "entry_value": 42750.00,
      "estimated_pnl": -1050.00,
      "confirmed": null
    }
  ]
}
```

---

### POST /me/signals/confirm
**Request:**
```json
{
  "session_token": "perm_token_abc123",
  "confirmations": [
    { "signal_id": "uuid", "actioned": true,  "qty": 50,  "price": 924.50 },
    { "signal_id": "uuid", "actioned": false, "qty": null, "price": null },
    { "signal_id": "uuid", "actioned": true,  "qty": 150, "price": 281.50 }
  ]
}
```
`actioned`: `true` = I Bought/Sold It | `false` = I Did Not Buy/Sell  
**Response 200:** `{ "submitted": true, "submitted_at": "2026-04-19T18:42:00Z" }`  
**Response 400:** `{ "detail": "All signals must be actioned before submitting" }`  
**Response 409:** `{ "detail": "Session already submitted and locked" }`

---

## POSITIONS

### GET /me/positions
**Response 200:**
```json
{
  "open": [
    {
      "id": "uuid",
      "stock": { "ticker_nse": "RELIANCE", "company_name": "Reliance Industries" },
      "source": "SIGNAL",
      "entry_date": "2026-04-10",
      "entry_price": 2890.00,
      "quantity": 10,
      "total_invested": 28900.00,
      "current_price": 3012.00,
      "current_value": 30120.00,
      "pnl_amount": 1220.00,
      "pnl_percent": 4.22,
      "trailing_stop": 2810.00,
      "days_held": 7,
      "exit_signal_active": false
    }
  ],
  "closed": [],
  "summary": {
    "total_invested": 124500.00,
    "total_current_value": 132700.00,
    "total_pnl": 8200.00,
    "total_pnl_percent": 6.59,
    "available_capital": 75500.00,
    "slots_used": 5
  }
}
```

---

## DATA

### GET /data/status
**Response 200:**
```json
{
  "last_scan_date": "2026-04-19",
  "last_scan_time": "2026-04-19T11:02:00Z",
  "source_used": "yfinance",
  "stocks_scanned": 234,
  "errors": 0,
  "status": "completed",
  "retry_active": false,
  "retry_attempt": null,
  "next_scan": "2026-04-22T11:00:00Z"
}
```

---

_This document is a living reference. BACKEND-ENG updates as routes are built and tested._  
_FRONTEND-ENG should not hard-code shapes — always reference this file._
