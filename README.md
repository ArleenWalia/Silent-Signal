# Silent Signal 📡

> *Universities track grades. Nobody tracks the cost of getting there.*

---

## The problem

Every university promises the same thing — community, growth, support. And every year, the structure they've built makes that promise nearly impossible to keep for most students. The workload is too heavy. The social environment is too competitive. And when students can't keep up with the version of university they were sold, the institution points to the students who somehow do it all — which lands less like inspiration and more like a quiet accusation.

So students go silent. Not because they're fine, but because the environment makes struggle feel like a personal failure rather than a systemic one. That silence has real consequences — on mental health, on sense of belonging, on whether students feel like they can ask for help at all.

The data on this exists in pieces — counseling wait times, dropout rates, anonymous surveys buried in annual reports. But nothing captures it in real time, from students themselves, in a way that's honest about what their weeks actually look like.

---

## What Silent Signal does

It gives students a 90-second anonymous check-in. Not "how are you feeling?" — that points inward. Instead: "what got in your way this week?" That points at the system.

Those signals get aggregated across the student body and made visible — not as individual confessions, but as collective patterns. When a student submits and sees that 74% of their peers reported the same friction point this semester, something shifts. The shame lifts. What felt like a personal failing starts to look like what it actually is — a structural problem that a lot of people are quietly carrying.

That reframe isn't just emotionally useful. It's the difference between a student who isolates and one who reaches out. Between someone who drops a course thinking they're not cut out for it, and someone who understands the conditions weren't designed for them to succeed.

---

## Why it's different

Most mental health tools ask students to reflect on their mindset. Silent Signal doesn't touch mindset at all. It treats students as reporters, not patients — their submissions build a live picture of what university actually feels like from the inside, week by week.

The AI doesn't offer coping strategies. It contextualizes. After you submit, it connects your experience to the aggregate — putting your specific friction points into systemic language instead of personal failure language. The goal is clarity, not comfort.

---

## Features

- Anonymous 4-step check-in — no account, no email, no tracking
- AI insight after each submission — systemic reframing, not wellness advice
- Live dashboard — real-time aggregated stats, weekly trends, friction breakdowns
- Signal AI chat — ask questions about the live data, get answers grounded in real submissions
- Signal Leagues — shows which pattern group your submission falls into
- My Logs — local submission history so you can track your own patterns over time
- Badges + NYT-style trivia quiz built in

---

## Tech stack

**Frontend** — HTML/CSS/JS single-file SPA, Google Fonts (Syne, DM Sans)

**Backend** — Python 3.11, FastAPI, SQLite, Uvicorn, Pydantic, httpx

**AI** — Anthropic Claude (`claude-haiku-4-5-20251001`) for insight generation, systemic reframing, dashboard chat, and weekly reports with semantic memory for longitudinal pattern context

---

## Setup

```bash
git clone https://github.com/ArleenWalia/Silent-Signal.git
cd Silent-Signal/backend
pip install -r requirements.txt
python seed.py
uvicorn main:app --reload
```

Then open `frontend/index.html` with Live Server in VS Code.

---

Built by Arleen Walia & Eqraa Khan — GenAI Genesis 2026, University of Toronto.
