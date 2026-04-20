"""
Courtney Smith Channel Breakout Trading Platform
FastAPI Backend — Main Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(
    title="Courtney Smith Channel Breakout API",
    description="Trading signal and portfolio management platform for NSE/BSE markets",
    version="1.0.0"
)

# CORS — allow frontend (Vercel) to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_URL", "http://localhost:5173"),
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check — Render uses this to verify service is up
@app.get("/health")
async def health():
    return {"status": "ok", "service": "courtney-smith-trading-platform"}

# TODO: Import and mount routers as they are built
# from routers import auth, me, watchlist, signals, positions, backtest, data, admin, internal
# app.include_router(auth.router, prefix="/auth", tags=["Auth"])
# app.include_router(me.router, prefix="/me", tags=["Trader Profile"])
# app.include_router(watchlist.router, prefix="/me/watchlist", tags=["Watchlist"])
# app.include_router(signals.router, prefix="/me/signals", tags=["Signals"])
# app.include_router(positions.router, prefix="/me/positions", tags=["Positions"])
# app.include_router(backtest.router, prefix="/backtest", tags=["Backtest"])
# app.include_router(data.router, prefix="/data", tags=["Data Feed"])
# app.include_router(admin.router, prefix="/admin", tags=["Admin"])
# app.include_router(internal.router, prefix="/internal", tags=["Internal"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
