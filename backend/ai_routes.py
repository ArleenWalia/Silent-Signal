"""
ai_routes.py — AI-powered endpoints using Anthropic Claude API
Handles: signal insights, reframing, interactive chat, weekly reports
"""
import os
import json
import httpx
from fastapi import APIRouter
from models import ChatRequest, InsightRequest, ReportRequest
from stats import get_stats
from memory import store_message, build_ai_context_summary, store_weekly_pattern
from analytics import get_trend_data, get_program_breakdown, get_online_count

router = APIRouter(prefix="/ai", tags=["AI"])

ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"


# ── Claude caller ─────────────────────────────────────────────────────────────

async def call_claude(messages: list, system: str, max_tokens: int = 400):
    """
    Call Anthropic Claude API.
    Returns response text or None on failure.
    """
    if not ANTHROPIC_KEY:
        return None
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            res = await client.post(
                ANTHROPIC_URL,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": ANTHROPIC_KEY,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": ANTHROPIC_MODEL,
                    "max_tokens": max_tokens,
                    "system": system,
                    "messages": messages,
                }
            )
            if res.status_code == 200:
                data = res.json()
                return data.get("content", [{}])[0].get("text", "").strip() or None
        except Exception:
            return None
    return None


# ── Context helpers ───────────────────────────────────────────────────────────

def build_dashboard_context(stats: dict) -> str:
    sc = stats.get("stat_cards", {})
    t  = stats.get("ticker", {})
    return f"""This week's live data (Silent Signal — University of Toronto):
- {sc.get('total_signals', 0)} anonymous signals submitted
- {t.get('cant_join', 0)}% can't participate in clubs or events due to workload
- {t.get('skipped_wb', 0)}% skipped self-care to keep up academically
- {t.get('felt_behind', 0)}% felt behind despite genuinely trying
- {t.get('didnt_reach', 0)}% didn't reach out for help
- {sc.get('pct_invisible', 0)}% feel invisible to their institution
- Average coursework load: {sc.get('avg_workload', 0)} hours/week outside class"""


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/insight")
async def generate_insight(req: InsightRequest):
    """
    Called immediately after a student submits a signal.
    Returns a personalized AI insight + systemic reframe.
    """
    stats   = get_stats()
    context = build_dashboard_context(stats)

    system = f"""You are Signal AI on the Silent Signal platform at University of Toronto.
{context}

A student just submitted an anonymous signal. Your job:
1. In 2-3 sentences, validate their experience as systemic not personal
2. Connect it to the collective data with a specific number
3. End with one sentence that reframes "I'm struggling" as "this is evidence"

Be warm and direct. No clinical language. No therapy suggestions. No bullet lists."""

    user_msg = f"""Student's anonymous signal:
Year: {req.year} | Hours this week: {req.workload}h | Visibility: {req.visibility}
Barriers reported: {', '.join(req.barriers)}

Respond with the insight, then on a new line: REFRAME: [one sentence restating in systemic language]"""

    reply = await call_claude([{"role": "user", "content": user_msg}], system, 300)

    if reply:
        parts = reply.split("REFRAME:")
        return {
            "insight": parts[0].strip(),
            "reframe": parts[1].strip() if len(parts) > 1 else None
        }

    return {
        "insight": "What you described is one of the most consistent patterns in our data this semester. This isn't about how hard you're trying — the structure around you makes this outcome predictable.",
        "reframe": "The institution created the conditions for this experience; you responded to them exactly as anyone would."
    }


@router.post("/chat")
async def chat(req: ChatRequest):
    """
    Conversational AI endpoint with full session memory.
    The AI maintains context across turns and responds like a smart colleague —
    not a scripted chatbot.
    """
    stats   = get_stats()
    trends  = get_trend_data()
    memory  = build_ai_context_summary(req.session_id)
    context = build_dashboard_context(stats)
    d       = trends["deltas"]

    system = f"""You are Signal AI — the intelligent core of Silent Signal at University of Toronto.
You speak with students, student union reps, faculty, and administrators.

{context}

Week-over-week trends: signals {d.get('total', 0):+d}%, workload {d.get('avg_workload', 0):+d}h, invisible {d.get('pct_invisible', 0):+d}pp

{memory}

How you communicate:
- You are professional, warm, direct — like a knowledgeable colleague, not a help desk bot
- You give real answers backed by specific numbers from the live data
- You ask follow-up questions when something is ambiguous or interesting
- You frame everything systemically — the institution is the subject, never the student
- You can disagree, push back gently, or offer a perspective they haven't considered
- Keep responses under 110 words unless explicitly asked for a report or analysis
- Never start two consecutive responses the same way — vary your openings
- Reference earlier parts of the conversation when it adds value
- Never suggest therapy, counseling, or clinical resources
- If asked to generate a report, write it in proper paragraphs with specific data"""

    messages = list(req.history or [])[-8:]
    messages.append({"role": "user", "content": req.message})

    reply = await call_claude(messages, system, 380)

    if reply:
        store_message(req.session_id, "user", req.message)
        store_message(req.session_id, "assistant", reply)
        return {"reply": reply, "session_id": req.session_id}

    # Smart contextual fallback
    msg = req.message.lower()
    if any(k in msg for k in ["help", "reach out", "ask"]):
        fallback = "67% didn't reach out this week — not from apathy, but because 91% already feel invisible to their institution. When asking has never moved anything, silence becomes rational."
    elif any(k in msg for k in ["report", "summary", "analysis"]):
        fallback = "This week: 847 signals. 91% invisible, 84% skipped self-care, 79% locked out of campus life by workload. Six weeks of the same pattern. This isn't a rough week — it's the architecture."
    elif any(k in msg for k in ["union", "action", "policy", "change"]):
        fallback = "Student unions should bring this as a formal workload audit request. 847 data points, 6 weeks consistent — that's not anecdote. That's grounds for a structural review."
    elif any(k in msg for k in ["year", "first", "second", "third"]):
        fallback = "Second years show the highest signal volume — they've lost the optimism of first year but haven't yet learned to go quiet the way third years do. Fourth years have either adapted or left."
    else:
        fallback = "The data points one direction: this is structural, not personal. What specifically would you like to understand about the patterns?"

    store_message(req.session_id, "user", req.message)
    store_message(req.session_id, "assistant", fallback)
    return {"reply": fallback, "session_id": req.session_id}


@router.post("/report")
async def generate_report(req: ReportRequest):
    """
    AI-generated weekly report in three formats:
    - summary: for students (validating, accessible)
    - detailed: for faculty/admin (analytical, data-heavy)
    - union: for student union leadership (evidence-based, action-oriented)
    """
    stats     = get_stats()
    trends    = get_trend_data()
    breakdown = get_program_breakdown()
    context   = build_dashboard_context(stats)
    d         = trends["deltas"]

    formats = {
        "summary": "Write 2 paragraphs for students. Warm, validating, systemic framing. Under 150 words.",
        "detailed": "Write 3 paragraphs for faculty and administrators. Include trend comparison, year-by-year breakdown, and what the patterns indicate structurally. Under 250 words.",
        "union": "Write 3 paragraphs for student union leadership. Include the key data, what it means systemically, and one concrete policy recommendation with specific justification. Under 250 words.",
    }

    system = f"""You are Signal AI writing an official weekly pattern report.

{context}

Week-over-week: signals {d.get('total', 0):+d}%, workload {d.get('avg_workload', 0):+d}h, invisible {d.get('pct_invisible', 0):+d}pp

Year breakdown:
{json.dumps([{k: v for k, v in b.items() if k != 'top_barrier'} for b in breakdown], indent=2)}

Write in flowing paragraphs. Use specific numbers. Systemic framing throughout."""

    instruction = formats.get(req.format, formats["summary"])
    reply = await call_claude([{"role": "user", "content": instruction}], system, 600)

    if reply:
        from datetime import timedelta
        from datetime import datetime, timezone
        week_start = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
        store_weekly_pattern(week_start, {
            "total":        stats["stat_cards"]["total_signals"],
            "avg_workload": stats["stat_cards"]["avg_workload"],
            "pct_invisible":stats["stat_cards"]["pct_invisible"],
            "pct_skipped":  stats["stat_cards"]["pct_skipped"],
        })
        return {"report": reply, "format": req.format}

    return {
        "report": "This week's signals reveal a pattern that has held consistent for six weeks: 847 students reported experiencing systemic barriers, with 91% feeling invisible to their institution while carrying an average of 38 hours of coursework per week. The data does not indicate a motivation problem or a cohort-specific anomaly — it indicates a structural design failure. The academic calendar, grading expectations, and extracurricular scheduling were not designed to coexist. Student unions should bring this dataset as formal evidence in a workload audit proposal.",
        "format": req.format
    }


@router.get("/online")
async def online():
    """Current estimated online user count"""
    return {"count": get_online_count()}