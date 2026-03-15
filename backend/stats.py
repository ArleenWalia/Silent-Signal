"""
stats.py — Signal aggregation and statistics
All percentages, weekly breakdowns, donut data, friction points, live feed
"""
import json
from datetime import datetime, timezone, timedelta
from database import get_db


def _empty_stats():
    return {
        "total": 0,
        "ticker": {"cant_join": 0, "skipped_wb": 0, "felt_behind": 0, "didnt_reach": 0},
        "stat_cards": {"total_signals": 0, "avg_workload": 0, "pct_invisible": 0, "pct_skipped": 0},
        "bar_chart": [0] * 11,
        "donut": [
            {"label": "First year",   "pct": 0, "color": "#b89dff"},
            {"label": "Second year",  "pct": 0, "color": "#93c5fd"},
            {"label": "Third year",   "pct": 0, "color": "#fbbf24"},
            {"label": "Fourth year+", "pct": 0, "color": "#f87171"},
        ],
        "friction": [],
        "feed": [],
    }


def get_stats():
    conn = get_db()
    rows = conn.execute("SELECT * FROM signals").fetchall()
    conn.close()

    total = len(rows)
    if total == 0:
        return _empty_stats()

    now = datetime.now(timezone.utc)
    barriers_all = []
    for r in rows:
        barriers_all.extend(json.loads(r["barriers"]))

    def pct(keyword):
        count = sum(1 for b in barriers_all if keyword.lower() in b.lower())
        return round(count / total * 100)

    invisible_count = sum(1 for r in rows if r["visibility"] in ("invisible", "partial"))
    skipped_count   = sum(1 for b in barriers_all if "wellbeing" in b.lower())

    # Weekly bar chart — last 11 weeks
    weekly = []
    for w in range(10, -1, -1):
        week_start = (now - timedelta(weeks=w+1)).isoformat()
        week_end   = (now - timedelta(weeks=w)).isoformat()
        count = sum(1 for r in rows if week_start <= r["created_at"] <= week_end)
        weekly.append(count)

    # Year breakdown
    year_counts = {"1": 0, "2": 0, "3": 0, "4": 0}
    for r in rows:
        key = r["year"] if r["year"] in year_counts else "4"
        year_counts[key] += 1

    donut = [
        {"label": "First year",   "pct": round(year_counts["1"] / total * 100), "color": "#b89dff"},
        {"label": "Second year",  "pct": round(year_counts["2"] / total * 100), "color": "#93c5fd"},
        {"label": "Third year",   "pct": round(year_counts["3"] / total * 100), "color": "#fbbf24"},
        {"label": "Fourth year+", "pct": round(year_counts["4"] / total * 100), "color": "#f87171"},
    ]

    # Friction breakdown
    barrier_map = [
        ("Felt invisible to institution",    "invisible",  "#b89dff"),
        ("Skipped wellbeing for coursework", "wellbeing",  "#f87171"),
        ("Couldn't join clubs/events",       "club",       "#93c5fd"),
        ("Felt behind despite trying",       "behind",     "#6ee7b7"),
        ("Didn't reach out for help",        "reach out",  "#a78bfa"),
        ("Isolated, no words for it",        "isolated",   "#f9a8d4"),
        ("Compared to successful peers",     "compared",   "#fbbf24"),
        ("Campus resources inaccessible",    "resources",  "#38bdf8"),
    ]

    friction = []
    for name, keyword, color in barrier_map:
        count = sum(1 for b in barriers_all if keyword.lower() in b.lower())
        friction.append({"name": name, "pct": round(count / total * 100), "color": color})
    friction.sort(key=lambda x: x["pct"], reverse=True)

    # Live feed — last 10 submissions
    conn = get_db()
    recent = conn.execute("SELECT * FROM signals ORDER BY id DESC LIMIT 10").fetchall()
    conn.close()

    year_labels = {"1": "1st year", "2": "2nd year", "3": "3rd year", "4": "4th year+"}
    colors = ["#b89dff", "#93c5fd", "#fbbf24", "#f87171", "#a78bfa", "#f9a8d4"]
    feed = []
    for i, r in enumerate(recent):
        b = json.loads(r["barriers"])
        top = b[0] if b else "submitted a signal"
        label = year_labels.get(r["year"], "Student")
        try:
            created = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
            mins_ago = max(0, int((now - created).total_seconds() / 60))
            time_str = "just now" if mins_ago < 1 else f"{mins_ago} min ago"
        except Exception:
            time_str = "recently"
        feed.append({
            "text":  f"<strong>{label}</strong> — {top.lower()}",
            "color": colors[i % len(colors)],
            "time":  time_str,
        })

    return {
        "total":      total,
        "ticker": {
            "cant_join":   pct("club"),
            "skipped_wb":  pct("wellbeing"),
            "felt_behind": pct("behind"),
            "didnt_reach": pct("reach out"),
        },
        "stat_cards": {
            "total_signals": total,
            "avg_workload":  round(sum(r["workload"] for r in rows) / total),
            "pct_invisible": round(invisible_count / total * 100),
            "pct_skipped":   round(skipped_count / total * 100),
        },
        "bar_chart":  weekly,
        "donut":      donut,
        "friction":   friction,
        "feed":       feed,
    }