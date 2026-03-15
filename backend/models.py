"""
models.py — Pydantic request/response models
"""
from pydantic import BaseModel
from typing import List, Optional


class SignalIn(BaseModel):
    year: str           # "1" | "2" | "3" | "4"
    barriers: List[str]
    workload: int       # 0–60
    visibility: str     # "invisible" | "partial" | "visible"


class ChatRequest(BaseModel):
    message: str
    session_id: str
    history: Optional[List[dict]] = []


class InsightRequest(BaseModel):
    barriers: List[str]
    workload: int
    visibility: str
    year: str


class ReportRequest(BaseModel):
    format: Optional[str] = "summary"  # "summary" | "detailed" | "union"