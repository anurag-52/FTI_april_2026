# 🔌 AGENT 5 — INTEGRATIONS-ENG Progress Log
## Integrations Engineer — Courtney Smith Channel Breakout Platform

**Codename:** INTEGRATIONS-ENG  
**Status:** ⏳ WAITING FOR CREDENTIALS  
**Last Updated:** 2026-04-19

---

## Credentials Required Before Testing
- [ ] MSG91 API Key
- [ ] MSG91 WhatsApp sender number / Business account ID
- [ ] Brevo API Key
- [ ] Brevo verified sender email address

---

## Module Build Checklist

### whatsapp.py (MSG91)
- [ ] [BUILT] send_whatsapp(mobile, template_name, variables) function
- [ ] [BUILT] Template: DAILY_SIGNAL
- [ ] [BUILT] Template: NO_SIGNAL_DAY
- [ ] [BUILT] Template: MARKET_HOLIDAY
- [ ] [BUILT] Template: REMINDER
- [ ] [BUILT] Template: INACTIVITY_DAY5
- [ ] [BUILT] Template: INACTIVITY_DAY12
- [ ] [BUILT] Template: AUTO_SUSPENDED
- [ ] [BUILT] Template: SCAN_FAILURE (Super Admin only)
- [ ] [BUILT] Template: STOCK_SUSPENDED
- [ ] [BUILT] Only sends if trader.notify_whatsapp == True
- [ ] [BUILT] Logs every send in notification_log (success + provider_ref)
- [ ] [BUILT] Logs failures in notification_log (status='failed')
- [ ] [CREDENTIALS-TESTED] Test message → +91 9303121500
- [ ] [LIVE-TESTED]
- [ ] [DONE]

### email_brevo.py (Brevo)
- [ ] [BUILT] send_email(to_email, template_name, variables) function
- [ ] [BUILT] HTML template: DAILY_SIGNAL
- [ ] [BUILT] HTML template: NO_SIGNAL_DAY
- [ ] [BUILT] HTML template: MARKET_HOLIDAY
- [ ] [BUILT] HTML template: REMINDER
- [ ] [BUILT] HTML template: INACTIVITY_DAY5
- [ ] [BUILT] HTML template: INACTIVITY_DAY12
- [ ] [BUILT] HTML template: AUTO_SUSPENDED
- [ ] [BUILT] HTML template: SCAN_FAILURE (Super Admin only)
- [ ] [BUILT] HTML template: STOCK_SUSPENDED
- [ ] [BUILT] Only sends if trader.notify_email == True
- [ ] [BUILT] Respect 300 emails/day Brevo free limit (with counter)
- [ ] [BUILT] Logs every send in notification_log
- [ ] [CREDENTIALS-TESTED] Test email → aaanurag@yahoo.com
- [ ] [LIVE-TESTED]
- [ ] [DONE]

### holiday_calendar.py (NSE Official)
- [ ] [BUILT] Annual fetch from NSE official source
- [ ] [BUILT] Monday 8:00 AM IST re-fetch (scheduled)
- [ ] [BUILT] Compare new vs stored — detect any changes
- [ ] [BUILT] If change: update market_holidays + log + alert Super Admin
- [ ] [BUILT] Store source='AUTO' in market_holidays table
- [ ] [LIVE-TESTED] At least 1 full calendar match verified
- [ ] [DONE]

### nse_bhavcopy.py
- [ ] [BUILT] Download ZIP from NSE archives URL
- [ ] [BUILT] Extract and parse CSV (Symbol, OPEN, HIGH, LOW, CLOSE, TOTTRDQTY)
- [ ] [BUILT] Map to standard OHLCV DataFrame format
- [ ] [BUILT] Handle missing/corrupt files gracefully
- [ ] [LIVE-TESTED] Successfully parsed a real Bhavcopy file
- [ ] [DONE]

### bse_bhavcopy.py
- [ ] [BUILT] Download ZIP from BSE website URL
- [ ] [BUILT] Extract and parse CSV (SC_CODE, OPEN, HIGH, LOW, CLOSE, NO_OF_SHRS)
- [ ] [BUILT] Map BSE SC_CODE to ticker in stocks table
- [ ] [BUILT] Map to standard OHLCV DataFrame format
- [ ] [BUILT] Handle missing/corrupt files gracefully
- [ ] [LIVE-TESTED] Successfully parsed a real Bhavcopy file
- [ ] [DONE]

### notifications.py (Dispatcher)
- [ ] [BUILT] dispatch(user_id, notification_type, variables) function
- [ ] [BUILT] Routes to WhatsApp if notify_whatsapp=True
- [ ] [BUILT] Routes to Email if notify_email=True
- [ ] [BUILT] Sends to BOTH if both enabled
- [ ] [BUILT] Sends to NEITHER if both disabled (but still logs)
- [ ] [BUILT] Bulk dispatch for all active traders (scan completion)
- [ ] [DONE]

---

## Notification Templates Quick Reference
| Type | Audience | Channel | Link? |
|---|---|---|---|
| DAILY_SIGNAL | Trader | Email + WA | ✅ Yes |
| NO_SIGNAL_DAY | Trader | Email + WA | ❌ No |
| MARKET_HOLIDAY | Trader | Email + WA | ❌ No |
| REMINDER | Trader | Email + WA | ✅ Yes |
| INACTIVITY_DAY5 | Trader | Email + WA | ✅ Yes |
| INACTIVITY_DAY12 | Trader | Email + WA | ✅ Yes |
| AUTO_SUSPENDED | Trader | Email + WA | ❌ No |
| SCAN_FAILURE | Super Admin | Email + WA | ✅ Admin link |
| STOCK_SUSPENDED | Trader + Admin | Email + WA | ❌ No |

---

## Activity Log
<!-- Format: [YYYY-MM-DD HH:MM IST] [STATUS] Description -->

[2026-04-19 23:46 IST] [INITIALIZED] Progress file created. Awaiting MSG91 + Brevo credentials.

---

## Blockers
_Waiting for MSG91 API Key and Brevo API Key_

## Bugs / Issues
_None yet_
