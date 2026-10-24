"""
Log Pydantic models for the Logs page
"""
from typing import List, Optional
from pydantic import BaseModel


class LLMLogEntrySummary(BaseModel):
    """Summary of a single LLM call (list view — no full prompt/output bodies)"""
    id: str
    timestamp: str
    provider: str
    model: str
    status: str  # "success" | "error"
    elapsed_sec: float
    prompt_chars: int
    output_chars: int
    prompt_preview: str
    response_format: Optional[str] = None
    error: Optional[str] = None


class LLMLogEntryDetail(LLMLogEntrySummary):
    """Full detail of a single LLM call (input + output)"""
    prompt: str
    output: Optional[str] = None
    error: Optional[str] = None
    thread: Optional[str] = None


class LLMLogListResponse(BaseModel):
    """Paginated list of LLM call summaries, newest first"""
    entries: List[LLMLogEntrySummary]
    total: int
    returned: int
