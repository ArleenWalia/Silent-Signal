"""
memory.py — Semantic memory layer for Signal AI
Stores conversation history and weekly pattern data for longitudinal AI context.
Inspired by Moorcheh-style semantic memory: stateful, retrievable, context-aware.
"""
from datetime import datetime, timezone
from database import get_db


def store_message(session_id: str, role: str, content: str):
    """Persist a chat message for session continuity"""
    conn = get_db()
    conn.execute(
        "INSERT INTO ai_memory (session_id, role, content, created_at) VALUES (?,?,?,?)",
        (session_id, role, content, datetime.now(timezone.utc).isoformat())
    )
    conn.commit()
    conn.close()


def get_session_history(session_id: str, limit: int = 20):
    """Retrieve recent messages for a session"""
    conn = get_db()
    rows = conn.execute(
        "SELECT role, content FROM ai_memory WHERE session_id=? ORDER BY id DESC LIMIT ?",
        (session_id, limit)
    ).fetchall()
    conn.close()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def store_weekly_pattern(week_start: str, patterns: dict):
    """
    Persist weekly aggregate patterns for longitudinal memory.
    This enables the AI to compare trends across weeks.
    """
    conn = get_db()
    for key, val in patterns.items():
        conn.execute(
            """INSERT OR REPLACE INTO weekly_patterns 
               (week_start, pattern_key, pattern_val, created_at) 
               VALUES (?,?,?,?)""",
            (week_start, key, float(val) if isinstance(val, (int, float)) else 0,
             datetime.now(timezone.utc).isoformat())
        )
    conn.commit()
    conn.close()


def get_longitudinal_context(weeks: int = 6) -> str:
    """
    Build a string summary of pattern history for the last N weeks.
    Injected into AI system prompt for contextual awareness.
    """
    conn = get_db()
    rows = conn.execute(
        "SELECT week_start, pattern_key, pattern_val FROM weekly_patterns ORDER BY week_start DESC LIMIT ?",
        (weeks * 10,)
    ).fetchall()
    conn.close()

    weeks_data: dict = {}
    for r in rows:
        w = r["week_start"]
        if w not in weeks_data:
            weeks_data[w] = {}
        weeks_data[w][r["pattern_key"]] = r["pattern_val"]

    if not weeks_data:
        return ""

    lines = ["Historical pattern memory (past weeks):"]
    for w, p in sorted(weeks_data.items(), reverse=True)[:4]:
        parts = []
        if "total" in p:
            parts.append(f"{int(p['total'])} signals")
        if "pct_invisible" in p:
            parts.append(f"{int(p['pct_invisible'])}% invisible")
        if "avg_workload" in p:
            parts.append(f"{int(p['avg_workload'])}h avg workload")
        lines.append(f"  {w}: {', '.join(parts)}")

    return "\n".join(lines)


def build_ai_context_summary(session_id: str = None) -> str:
    """Full context string: longitudinal history + recent session"""
    parts = []
    longitudinal = get_longitudinal_context()
    if longitudinal:
        parts.append(longitudinal)

    if session_id:
        history = get_session_history(session_id, limit=6)
        if history:
            parts.append("\nRecent conversation context:")
            for msg in history[-4:]:
                snippet = msg["content"][:120].replace("\n", " ")
                parts.append(f"  {msg['role'].upper()}: {snippet}...")

    return "\n".join(parts)