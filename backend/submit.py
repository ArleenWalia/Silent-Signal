import json
from database import get_connection

def submit_signal(signal):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO signals (year, barriers, workload, visibility)
        VALUES (?, ?, ?, ?)
    """, (
        signal.year,
        json.dumps(signal.barriers),
        signal.workload,
        signal.visibility
    ))
    conn.commit()
    conn.close()
    return { "message": "signal received" }