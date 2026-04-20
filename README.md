# Courtney Smith Channel Breakout Trading Platform

A cloud-based trading signal and portfolio management platform built strictly around **Courtney Smith's Channel Breakout technique**.

## Overview
- **Users:** 10–20 private traders (NSE/BSE Indian markets)
- **Signals:** End-of-day channel breakout signals (BUY + EXIT)
- **Notifications:** WhatsApp (MSG91) + Email (Resend)
- **Markets:** NSE / BSE — EOD only

## Tech Stack
| Layer | Technology | Deployment |
|---|---|---|
| Frontend | React 18 + Vite + TailwindCSS | Vercel |
| Backend | Python FastAPI | Render.com |
| Database | Supabase (PostgreSQL + Auth + RLS) | Supabase |
| Stock Data | yfinance → NSE Bhavcopy → BSE Bhavcopy | — |
| Email | Resend (free tier) | — |
| WhatsApp | MSG91 | — |
| Scheduler | Render Cron Jobs | — |

## Project Structure
```
/frontend      → React app (13 screens, mobile-first)
/backend       → FastAPI (all routes + scan engine + integrations)
/agents        → Agent progress tracking files
/docs          → API contracts, deployment URLs
```

## Trading Logic — Courtney Smith Channel Breakout

**BUY Signal** (all 3 must be TRUE simultaneously):
1. 55-day channel high flat/declining for ≥5 consecutive days
2. Today's close breaks above the 55-day channel high
3. ADX(20) is rising today vs yesterday

**EXIT Signal** (any 1 triggers full exit):
1. Rejection Rule: no close above breakout level within 2 days
2. Trailing Stop: close below 20-day channel low
3. ADX Exit: ADX turns down from 40+

## Setup
See [docs/deployment_urls.md](docs/deployment_urls.md) for environment variables and live URLs.
