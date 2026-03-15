"""
main.py — Silent Signal API v2
Run: uvicorn main:app --reload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import json
from datetime import datetime, timezone

from database import get_db, init_db
from stats import get_stats
from analytics import get_trend_data, get_program_breakdown, get_peak_signal_times, get_online_count
from ai_routes import router as ai_router
from models import SignalIn

app = FastAPI(title="Silent Signal API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai_router)

# Initialize DB tables on startup
init_db()


# ── Core signal endpoints ─────────────────────────────────────────────────────

@app.post("/signals", status_code=201)
def submit_signal(payload: SignalIn):
    """
    Receive and store one anonymous signal.
    Returns updated aggregate stats so the frontend updates immediately.
    """
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    conn.execute(
        "INSERT INTO signals (year, barriers, workload, visibility, created_at) VALUES (?,?,?,?,?)",
        (payload.year, json.dumps(payload.barriers), payload.workload, payload.visibility, now)
    )
    conn.commit()
    conn.close()
    return get_stats()


@app.get("/stats")
def stats():
    """Full aggregated stats for the dashboard"""
    return get_stats()


# ── Analytics endpoints ───────────────────────────────────────────────────────

@app.get("/analytics/trends")
def trends():
    """This week vs last week comparison"""
    return get_trend_data()


@app.get("/analytics/breakdown")
def breakdown():
    """Signal breakdown by year of study"""
    return get_program_breakdown()


@app.get("/analytics/timing")
def timing():
    """Peak signal submission times by day of week"""
    return get_peak_signal_times()


@app.get("/online")
def online():
    """Estimated currently active users"""
    return {"count": get_online_count()}


@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}