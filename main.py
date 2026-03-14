from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import sqlite3
import json
from datetime import datetime, timedelta, timezone

app = FastAPI(title="Silent Signal API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "signals.db"

# ── Database ──────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            year        TEXT    NOT NULL,
            barriers    TEXT    NOT NULL,
            workload    INTEGER NOT NULL,
            visibility  TEXT    NOT NULL,
            created_at  TEXT    NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ── Models ────────────────────────────────────────────────────────────────────

class SignalIn(BaseModel):
    year: str           # "1" | "2" | "3" | "4"
    barriers: List[str]
    workload: int       # 0–60
    visibility: str     # "invisible" | "partial" | "visible"

# ── Helpers ───────────────────────────────────────────────────────────────────

def _empty_stats():
    return {
        "total": 0,
        "ticker": {"cant_join": 0, "skipped_wb": 0, "felt_behind": 0, "didnt_reach": 0},
        "stat_cards": {"total_signals": 0, "avg_workload": 0, "pct_invisible": 0, "pct_skipped": 0},
        "bar_chart": [0] * 11,
        "donut": [
            {"label": "First year",   "pct": 0, "color": "#4ade80"},
            {"label": "Second year",  "pct": 0, "color": "#60a5fa"},
            {"label": "Third year",   "pct": 0, "color": "#f59e0b"},
            {"label": "Fourth year+", "pct": 0, "color": "#f87171"},
        ],
        "friction": [],
        "feed": [],
    }

# ── Routes ────────────────────────────────────────────────────────────────────

@app.post("/signals", status_code=201)
def submit_signal(payload: SignalIn):
    """Store one anonymous signal, return updated aggregate stats."""
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
def get_stats():
    """
    Returns all aggregated data the frontend needs:
      ticker      – 4 hero percentages
      stat_cards  – 4 dashboard numbers
      bar_chart   – weekly volume, last 11 weeks
      donut       – breakdown by year
      friction    – barrier percentages
      feed        – last 10 anonymous submissions
    """
    conn = get_db()
    rows = conn.execute("SELECT * FROM signals").fetchall()
    conn.close()

    total = len(rows)
    if total == 0:
        return _empty_stats()

    now = datetime.now(timezone.utc)

    # Flatten all barriers into one list
    barriers_all = []
    for r in rows:
        barriers_all.extend(json.loads(r["barriers"]))

    def pct_contains(keyword):
        count = sum(1 for b in barriers_all if keyword.lower() in b.lower())
        return round(count / total * 100)

    # ── Ticker ────────────────────────────────────────────────────────────────
    ticker = {
        "cant_join":   pct_contains("club"),
        "skipped_wb":  pct_contains("wellbeing"),
        "felt_behind": pct_contains("behind"),
        "didnt_reach": pct_contains("reach out"),
    }

    # ── Stat cards ────────────────────────────────────────────────────────────
    invisible_count = sum(1 for r in rows if r["visibility"] in ("invisible", "partial"))
    skipped_count   = sum(1 for b in barriers_all if "wellbeing" in b.lower())

    stat_cards = {
        "total_signals": total,
        "avg_workload":  round(sum(r["workload"] for r in rows) / total),
        "pct_invisible": round(invisible_count / total * 100),
        "pct_skipped":   round(skipped_count / total * 100),
    }

    # ── Bar chart – last 11 weeks ─────────────────────────────────────────────
    weekly = []
    for w in range(10, -1, -1):
        week_start = (now - timedelta(weeks=w+1)).isoformat()
        week_end   = (now - timedelta(weeks=w)).isoformat()
        count = sum(
            1 for r in rows
            if week_start <= r["created_at"] <= week_end
        )
        weekly.append(count)

    # ── Donut by year ─────────────────────────────────────────────────────────
    year_counts = {"1": 0, "2": 0, "3": 0, "4": 0}
    for r in rows:
        key = r["year"] if r["year"] in year_counts else "4"
        year_counts[key] += 1

    donut = [
        {"label": "First year",   "pct": round(year_counts["1"] / total * 100), "color": "#4ade80"},
        {"label": "Second year",  "pct": round(year_counts["2"] / total * 100), "color": "#60a5fa"},
        {"label": "Third year",   "pct": round(year_counts["3"] / total * 100), "color": "#f59e0b"},
        {"label": "Fourth year+", "pct": round(year_counts["4"] / total * 100), "color": "#f87171"},
    ]

    # ── Friction list ─────────────────────────────────────────────────────────
    barrier_map = [
        ("Skipped wellbeing for coursework",   "wellbeing",  "#f87171"),
        ("Felt invisible to the institution",  "invisible",  "#f59e0b"),
        ("Couldn't join clubs/events",         "club",       "#60a5fa"),
        ("Felt behind despite trying",         "behind",     "#4ade80"),
        ("Didn't reach out — felt pointless",  "reach out",  "#a78bfa"),
        ("Isolated, no words for it",          "isolated",   "#fb7185"),
        ("Compared to successful peers",       "compared",   "#38bdf8"),
        ("Campus resources inaccessible",      "resources",  "#e879f9"),
    ]

    friction = []
    for name, keyword, color in barrier_map:
        count = sum(1 for b in barriers_all if keyword.lower() in b.lower())
        friction.append({"name": name, "pct": round(count / total * 100), "color": color})
    friction.sort(key=lambda x: x["pct"], reverse=True)

    # ── Live feed – last 10 rows ──────────────────────────────────────────────
    conn = get_db()
    recent = conn.execute("SELECT * FROM signals ORDER BY id DESC LIMIT 10").fetchall()
    conn.close()

    year_labels = {"1": "1st year", "2": "2nd year", "3": "3rd year", "4": "4th year+"}
    colors = ["#4ade80", "#60a5fa", "#f59e0b", "#f87171", "#a78bfa", "#fb7185"]
    feed = []
    for i, r in enumerate(recent):
        b = json.loads(r["barriers"])
        top = b[0] if b else "submitted a signal"
        label = year_labels.get(r["year"], "Student")
        created = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
        mins_ago = max(0, int((now - created).total_seconds() / 60))
        time_str = "just now" if mins_ago < 1 else f"{mins_ago} min ago"
        feed.append({
            "text":  f"<strong>{label}</strong> — {top.lower()}",
            "color": colors[i % len(colors)],
            "time":  time_str,
        })

    return {
        "total":      total,
        "ticker":     ticker,
        "stat_cards": stat_cards,
        "bar_chart":  weekly,
        "donut":      donut,
        "friction":   friction,
        "feed":       feed,
    }
