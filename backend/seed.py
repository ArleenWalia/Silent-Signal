"""
seed.py — Populate the database with realistic demo signals
Run once before your demo: python seed.py
"""
import sqlite3
import json
from datetime import datetime, timezone, timedelta
import random

DB_PATH = "signals.db"

barriers_pool = [
    "Couldn't join a club or event",
    "Skipped something for my wellbeing to keep up",
    "Felt behind despite genuinely trying",
    "Didn't ask for help — felt it wouldn't matter",
    "Felt isolated, no words for it",
    "Compared myself to successful peers unfairly",
    "Felt like I was the only one struggling",
    "Campus resources felt inaccessible",
]

visibility_pool = [
    "invisible", "invisible", "invisible",
    "partial", "partial",
    "visible"
]

year_pool = ["1", "1", "2", "2", "2", "3", "3", "4"]

conn = sqlite3.connect(DB_PATH)
conn.execute("""
    CREATE TABLE IF NOT EXISTS signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        year TEXT NOT NULL,
        barriers TEXT NOT NULL,
        workload INTEGER NOT NULL,
        visibility TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
""")

inserted = 0
for i in range(300):
    days_ago = random.randint(0, 77)  # ~11 weeks back
    hours_ago = random.randint(0, 23)
    created = (datetime.now(timezone.utc) - timedelta(days=days_ago, hours=hours_ago)).isoformat()

    barriers = random.sample(barriers_pool, random.randint(2, 5))

    conn.execute(
        "INSERT INTO signals (year, barriers, workload, visibility, created_at) VALUES (?,?,?,?,?)",
        (
            random.choice(year_pool),
            json.dumps(barriers),
            random.randint(24, 58),
            random.choice(visibility_pool),
            created,
        ),
    )
    inserted += 1

conn.commit()
conn.close()
print(f"✓ {inserted} signals seeded into {DB_PATH}")
print("✓ Run: uvicorn main:app --reload")