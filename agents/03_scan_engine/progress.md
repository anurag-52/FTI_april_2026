# 📡 AGENT 3 — SCAN-ENG Progress Log
## Scan Engine Specialist — Courtney Smith Channel Breakout Platform

**Codename:** SCAN-ENG  
**Status:** ⏳ WAITING FOR DB-ARCH HANDOFF  
**Last Updated:** 2026-04-19

> ⚠️ **CRITICAL MODULE** — Signal accuracy is the core product value.
> Do NOT mark [VERIFIED-ACCURATE] without testing against real NSE historical data.

---

## Dependencies
- [ ] DB-ARCH handoff (Supabase connection)
- [ ] yfinance installed (pip install yfinance)
- [ ] pandas-ta or ta-lib installed (for ADX computation)

---

## Module Build Checklist

### data_fetcher.py
- [ ] yfinance fetch — NSE tickers (.NS suffix)
- [ ] yfinance fetch — BSE tickers (.BO suffix)
- [ ] Retry logic: every 15 mins × 12 attempts
- [ ] NSE Bhavcopy fallback (parse ZIP → CSV)
- [ ] BSE Bhavcopy fallback (parse ZIP → CSV)
- [ ] All attempts logged in data_source_log table
- [ ] Returns standardized OHLCV DataFrame

### indicator_engine.py
- [ ] ch55_high: rolling max(high, 55 days)
- [ ] ch55_low:  rolling min(low, 55 days)
- [ ] ch20_high: rolling max(high, 20 days)
- [ ] ch20_low:  rolling min(low, 20 days) ← trailing stop
- [ ] adx_20: ADX with period=20
- [ ] adx_rising: today.adx > yesterday.adx (boolean)
- [ ] ch55_high_flat_days: consecutive days 55-high flat/declining
- [ ] ch55_low_flat_days: consecutive days 55-low flat/rising
- [ ] is_post_holiday: previous trading day was market holiday
- [ ] gap_down_pct: (prev_close - open) / prev_close × 100 on post-holiday days
- [ ] gap_risk_warning: is_post_holiday AND gap_down_pct > 2
- [ ] hit_upper_circuit: detect from OHLC patterns
- [ ] hit_lower_circuit: detect from OHLC patterns

### signal_engine.py
- [ ] BUY condition 1: ch55_high_flat_days >= 5 (days BEFORE today)
- [ ] BUY condition 2: today.close > prev_day.ch55_high (breakout)
- [ ] BUY condition 3: adx_rising == True
- [ ] BUY signal: ALL 3 conditions TRUE simultaneously
- [ ] EXIT rejection: no close above ch55_high_at_entry within 2 days of entry
- [ ] EXIT trailing stop: today.close < today.ch20_low
- [ ] EXIT ADX: yesterday.adx >= 40 AND today.adx < yesterday.adx
- [ ] any_exit_signal: any of the 3 exit conditions TRUE
- [ ] Write all flags to stock_prices table

### scan_runner.py
- [ ] Pre-scan at 4:25 PM: check market_holidays for today
- [ ] If holiday: log as skipped_holiday, notify all traders, stop
- [ ] Fetch EOD for all watchlist stocks (deduplicated across traders)
- [ ] Compute indicators and store in stock_prices
- [ ] Per active trader: check buy_signal and any_exit_signal
- [ ] Skip: stock with unconfirmed pending signal for that trader
- [ ] Generate per-trader signals in signals table
- [ ] Position sizing: (capital × risk%) ÷ (entry_price − ch20_low)
- [ ] Increment inactivity_days for traders with pending unconfirmed signals
- [ ] Auto-pause check (day 7), auto-suspend check (day 15)
- [ ] Warning check (day 5, day 12)
- [ ] Create notification_sessions per trader
- [ ] Trigger notification dispatch at 5:00 PM IST
- [ ] Log scan result in scan_log table

### background_jobs.py
- [ ] New stock added: check if in stocks table
- [ ] If new: fetch 10 years OHLC via yfinance
- [ ] Compute all indicators for every historical day
- [ ] Update stocks.compute_progress (0→100) every 5%
- [ ] Log to scan_log
- [ ] Stock available for live signals once today's data computed
- [ ] Full 10yr history needed for backtest only

---

## Signal Accuracy Verification
Test against known NSE breakouts before [VERIFIED-ACCURATE]:

| Stock | Known Breakout Date | Expected Signal | Verified |
|---|---|---|---|
| RELIANCE | TBD | BUY | [ ] |
| TCS | TBD | BUY | [ ] |
| HDFC | TBD | EXIT-TRAILING | [ ] |

---

## Activity Log
<!-- Format: [YYYY-MM-DD HH:MM IST] [STATUS] Description -->

[2026-04-19 23:46 IST] [INITIALIZED] Progress file created. Awaiting DB-ARCH handoff.

---

## Blockers
_Waiting for DB-ARCH (AGENT 1) to complete_

## Bugs / Issues
_None yet_
