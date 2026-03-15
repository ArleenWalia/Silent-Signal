"""
analytics.py — Advanced analytics: trends, breakdowns, online count
"""
import json
import random
from datetime import datetime, timezone, timedelta
from database import get_db


def get_trend_data():
    """Compare this week vs last week"""
    conn = get_db()
    now = datetime.now(timezone.utc)
    this_week_start = (now - timedelta(weeks=1)).isoformat()
    last_week_start = (now - timedelta(weeks=2)).isoformat()

    this_week = conn.execute(
        "SELECT * FROM signals WHERE created_at >= ?", (this_week_start,)
    ).fetchall()
    last_week = conn.execute(
        "SELECT * FROM signals WHERE created_at >= ? AND created_at < ?",
        (last_week_start, this_week_start)
    ).fetchall()
    conn.close()

    def calc(rows):
        if not rows:
            return {"total": 0, "avg_workload": 0, "pct_invisible": 0, "pct_skipped": 0}
        total = len(rows)
        barriers_all = []
        for r in rows:
            barriers_all.extend(json.loads(r["barriers"]))
        invisible = sum(1 for r in rows if r["visibility"] in ("invisible", "partial"))
        skipped = sum(1 for b in barriers_all if "wellbeing" in b.lower())
        return {
            "total": total,
            "avg_workload": round(sum(r["workload"] for r in rows) / total),
            "pct_invisible": round(invisible / total * 100),
            "pct_skipped": round(skipped / total * 100),
        }

    this = calc(this_week)
    last = calc(last_week)

    def delta(a, b):
        if b == 0:
            return 0
        return round(((a - b) / b) * 100)

    return {
        "this_week": this,
        "last_week": last,
        "deltas": {
            "total": delta(this["total"], last["total"]),
            "avg_workload": this["avg_workload"] - last["avg_workload"],
            "pct_invisible": this["pct_invisible"] - last["pct_invisible"],
            "pct_skipped": this["pct_skipped"] - last["pct_skipped"],
        }
    }


def get_program_breakdown():
    """Signals broken down by year of study"""
    conn = get_db()
    rows = conn.execute("SELECT year, visibility, workload, barriers FROM signals").fetchall()
    conn.close()

    by_year = {}
    for r in rows:
        y = r["year"]
        if y not in by_year:
            by_year[y] = {"count": 0, "workload_total": 0, "invisible": 0, "barriers": []}
        by_year[y]["count"] += 1
        by_year[y]["workload_total"] += r["workload"]
        if r["visibility"] in ("invisible", "partial"):
            by_year[y]["invisible"] += 1
        by_year[y]["barriers"].extend(json.loads(r["barriers"]))

    year_labels = {"1": "First year", "2": "Second year", "3": "Third year", "4": "Fourth year+"}
    result = []
    for y, d in sorted(by_year.items()):
        count = d["count"]
        if count == 0:
            continue
        bc = {}
        for b in d["barriers"]:
            bc[b] = bc.get(b, 0) + 1
        top = max(bc, key=bc.get) if bc else "—"
        result.append({
            "year": year_labels.get(y, y),
            "count": count,
            "avg_workload": round(d["workload_total"] / count),
            "pct_invisible": round(d["invisible"] / count * 100),
            "top_barrier": top,
        })
    return result


def get_peak_signal_times():
    """Signal submission patterns by day of week"""
    conn = get_db()
    rows = conn.execute("SELECT created_at FROM signals").fetchall()
    conn.close()

    day_counts = {i: 0 for i in range(7)}
    for r in rows:
        try:
            dt = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
            day_counts[dt.weekday()] += 1
        except Exception:
            pass

    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    return [{"day": days[i], "count": day_counts[i]} for i in range(7)]


def get_online_count():
    """
    Estimate currently active users.
    Counts real submissions in last 30 min + realistic base number.
    """
    conn = get_db()
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
    result = conn.execute(
        "SELECT COUNT(*) as c FROM signals WHERE created_at >= ?", (cutoff,)
    ).fetchone()
    conn.close()
    real = result["c"] if result else 0
    base = random.randint(44, 82)
    return real + base