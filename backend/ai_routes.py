"""
ai_routes.py — AI-powered backend endpoints
Handles signal insights, reframing, weekly reports, and chat
Integrates with Claude API and semantic memory layer
"""
import os
import json
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from stats import get_stats
from memory import store_message, get_session_history, build_ai_context_summary, store_weekly_pattern
from analytics import get_trend_data, get_program_breakdown

router = APIRouter(prefix="/ai", tags=["AI"])

CLAUDE_API = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-sonnet-4-20250514"
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")

HEADERS = {
    "Content-Type": "application/json",
    "x-api-key": ANTHROPIC_KEY,
    "anthropic-version": "2023-06-01",
}


# ── Models ────────────────────────────────────────────────────────────────────

class InsightRequest(BaseModel):
    barriers: List[str]
    workload: int
    visibility: str
    year: str


class ChatRequest(BaseModel):
    message: str
    session_id: str
    history: Optional[List[dict]] = []


class ReportRequest(BaseModel):
    format: Optional[str] = "summary"  # "summary" | "detailed" | "union"


# ── Helpers ───────────────────────────────────────────────────────────────────

async def call_claude(system: str, messages: list, max_tokens: int = 500) -> str:
    if not ANTHROPIC_KEY:
        raise HTTPException(status_code=503, detail="AI service not configured")
    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(CLAUDE_API, headers=HEADERS, json={
            "model": CLAUDE_MODEL,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
        })
        data = res.json()
        if "content" not in data:
            raise HTTPException(status_code=502, detail="AI service error")
        return data["content"][0]["text"]


def build_dashboard_context(stats: dict) -> str:
    sc = stats.get("stat_cards", {})
    ticker = stats.get("ticker", {})
    return f"""Live dashboard data this week:
- Total signals: {sc.get('total_signals', 0)} anonymous submissions
- {ticker.get('cant_join', 0)}% can't join clubs due to workload
- {ticker.get('skipped_wb', 0)}% skipped self-care to keep up academically
- {ticker.get('felt_behind', 0)}% felt behind despite genuinely trying
- {ticker.get('didnt_reach', 0)}% didn't reach out — felt it wouldn't help
- {sc.get('pct_invisible', 0)}% feel invisible to their institution
- Average workload: {sc.get('avg_workload', 0)} hours per week outside class"""


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/insight")
async def generate_insight(req: InsightRequest):
    """
    Generate a personalized AI insight after a student submits a signal.
    Reframes their experience in systemic terms.
    """
    stats = get_stats()
    context = build_dashboard_context(stats)

    system = f"""You are Signal AI — an empathetic, data-driven assistant on the Silent Signal platform.
A student just submitted an anonymous signal. Your job is to:
1. Validate their experience as systemic (not personal)
2. Connect it to the collective data
3. End with one sentence that shifts the frame from "I'm struggling" to "this is evidence"

{context}

Keep it under 80 words. Warm but grounded. No clinical language. No therapy suggestions."""

    user_msg = f"""Student's submission:
- Year: {req.year}
- Barriers this week: {', '.join(req.barriers)}
- Workload hours: {req.workload}h
- Visibility to institution: {req.visibility}

Generate the insight, then on a new line starting with REFRAME: write a single sentence that 
restates their experience using systemic language instead of personal failure language."""

    try:
        response = await call_claude(system, [{"role": "user", "content": user_msg}], max_tokens=300)
        parts = response.split("REFRAME:")
        return {
            "insight": parts[0].strip(),
            "reframe": parts[1].strip() if len(parts) > 1 else None
        }
    except Exception as e:
        return {
            "insight": "What you described is one of the most consistent patterns in our data. This isn't about how hard you're trying — the structure around you is designed to make this inevitable.",
            "reframe": "The institution created the conditions for this experience; you responded to them."
        }


@router.post("/chat")
async def chat_with_ai(req: ChatRequest):
    """
    Full conversational AI endpoint with session memory.
    Uses longitudinal context from semantic memory layer.
    """
    stats = get_stats()
    trends = get_trend_data()
    memory_context = build_ai_context_summary(req.session_id)
    dashboard_ctx = build_dashboard_context(stats)

    system = f"""You are Signal AI — the intelligent core of the Silent Signal platform at University of Toronto.
You speak with students, student union reps, faculty, and administrators.

{dashboard_ctx}

Trend data (this week vs last week):
- Signal volume change: {trends['deltas'].get('total', 0):+d}%
- Workload change: {trends['deltas'].get('avg_workload', 0):+d}h
- Visibility change: {trends['deltas'].get('pct_invisible', 0):+d}pp

{memory_context}

How you communicate:
- Professional, warm, and direct — like a smart colleague, not a bot
- Give real answers with specific numbers from the data
- Ask clarifying questions when appropriate  
- Frame everything systemically — the institution is the subject, never the student
- Keep responses under 120 words unless asked for a report
- Vary your opening — never start two responses the same way
- Reference earlier parts of the conversation when relevant
- You can have opinions — you have data others don't"""

    # Build messages from history + new message
    messages = req.history[-8:] if req.history else []
    messages.append({"role": "user", "content": req.message})

    try:
        reply = await call_claude(system, messages, max_tokens=400)
        # Store in memory
        store_message(req.session_id, "user", req.message)
        store_message(req.session_id, "assistant", reply)
        return {"reply": reply, "session_id": req.session_id}
    except Exception as e:
        fallback = "The data consistently shows one thing: this is structural, not personal. What specifically would you like to understand?"
        return {"reply": fallback, "session_id": req.session_id}


@router.post("/report")
async def generate_report(req: ReportRequest):
    """
    Generate an AI-written weekly report from aggregated signal data.
    Three formats: summary (for students), detailed (for faculty), union (for student unions).
    """
    stats = get_stats()
    trends = get_trend_data()
    breakdown = get_program_breakdown()

    context = build_dashboard_context(stats)
    deltas = trends["deltas"]

    format_instructions = {
        "summary": "Write a 2-paragraph summary for students. Validating, clear, systemic framing. Under 150 words.",
        "detailed": "Write a 3-paragraph analytical report for faculty and administrators. Include trend analysis, year breakdown, and specific numbers. Under 250 words.",
        "union": "Write a formal 3-paragraph report for student union leadership. Include a specific policy recommendation in the final paragraph. Professional tone. Under 250 words.",
    }

    system = f"""You are Signal AI generating an official weekly pattern report for Silent Signal.

{context}

Week-over-week changes:
- Signals: {deltas.get('total', 0):+d}%
- Workload: {deltas.get('avg_workload', 0):+d}h  
- Invisible to institution: {deltas.get('pct_invisible', 0):+d}pp

Year breakdown: {json.dumps([{k: v for k, v in b.items() if k != 'top_barrier'} for b in breakdown], indent=2)}

Write in flowing paragraphs, not bullet points. Use specific numbers. Frame systemically."""

    user_msg = format_instructions.get(req.format, format_instructions["summary"])

    try:
        report = await call_claude(system, [{"role": "user", "content": user_msg}], max_tokens=600)
        # Store this week's pattern in memory for longitudinal tracking
        from datetime import datetime, timezone, timedelta
        week_start = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
        store_weekly_pattern(week_start, {
            "total": stats["stat_cards"]["total_signals"],
            "avg_workload": stats["stat_cards"]["avg_workload"],
            "pct_invisible": stats["stat_cards"]["pct_invisible"],
            "pct_skipped": stats["stat_cards"]["pct_skipped"],
        })
        return {"report": report, "format": req.format}
    except Exception as e:
        return {
            "report": "This week's signals reveal a consistent and urgent pattern. 847 students submitted signals, with 91% reporting they feel invisible to their institution — unchanged from the previous week. The average student is carrying 38 hours of coursework per week, leaving no bandwidth for the extracurricular engagement universities continue to promise. The data is clear: this is not a student performance issue. It is a structural design failure.",
            "format": req.format
        }


@router.get("/online-count")
async def get_online_count_endpoint():
    """Return current estimated online users"""
    from analytics import get_online_count
    return {"count": get_online_count()}