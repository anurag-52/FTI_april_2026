"""
FastAPI Application — Courtney Smith Channel Breakout Trading Platform
Author: AGENT 2 (Backend Engineer)

Startup: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
Production (Render): uvicorn main:app --host 0.0.0.0 --port $PORT
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import FRONTEND_URL

# ── Router imports ────────────────────────────────────────────────────────────
from routers.auth      import router as auth_router
from routers.me        import router as me_router
from routers.watchlist import router as watchlist_router
from routers.signals   import router as signals_router
from routers.positions import router as positions_router
from routers.backtest  import router as backtest_router
from routers.data      import router as data_router
from routers.admin     import router as admin_router
from routers.internal  import router as internal_router

app = FastAPI(
    title="Courtney Smith Channel Breakout API",
    description="Private trading signals platform — Courtney Smith Strategy",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_URL,
        "https://fti-frontend.vercel.app",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register Routers ─────────────────────────────────────────────────────────
app.include_router(auth_router,      tags=["Auth"])
app.include_router(me_router,        tags=["Me"])
app.include_router(watchlist_router, tags=["Watchlist"])
app.include_router(signals_router,   tags=["Signals"])
app.include_router(positions_router, tags=["Positions"])
app.include_router(backtest_router,  tags=["Backtest"])
app.include_router(data_router,      tags=["Data"])
app.include_router(admin_router,     tags=["Admin"])
app.include_router(internal_router,  prefix="/internal", tags=["Internal"])


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {"status": "ok", "service": "Courtney Smith Channel Breakout API", "version": "1.0.0"}


@app.get("/health")
async def health():
    """Render health check endpoint."""
    return {"status": "healthy"}
