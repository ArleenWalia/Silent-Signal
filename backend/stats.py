import json
from database import get_connection

def get_stats():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT() as total FROM signals")
    total = cursor.fetchone()["total"]

    if total == 0:
        return { "total": 0, "barriers": {}, "avg_workload": 0, "visibility": {} }

    cursor.execute("SELECT barriers, workload, visibility FROM signals")
    rows = cursor.fetchall()

    barrier_counts = {}
    visibility_counts = {}
    total_workload = 0

    for row in rows:
        barriers = json.loads(row["barriers"])
        for b in barriers:
            barrier_counts[b] = barrier_counts.get(b, 0) + 1

        total_workload += row["workload"]

        v = row["visibility"]
        visibility_counts[v] = visibility_counts.get(v, 0) + 1

    barrier_pcts = {
        b: round((count / total) * 100)
        for b, count in barrier_counts.items()
    }

    conn.close()

    return {
        "total": total,
        "barriers": barrier_pcts,
        "avg_workload": round(total_workload / total),
        "visibility": {
            k: round((v / total) * 100)
            for k, v in visibility_counts.items()
        }
    }

def get_feed():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT year, barriers, created_at
        FROM signals
        ORDER BY created_at DESC
        LIMIT 10
    """)
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "year": row["year"],
            "barriers": json.loads(row["barriers"]),
            "time": row["created_at"]
        }
        for row in rows
    ]