"""
Logs API endpoints - structured view of LLM calls (input/output)
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from web_ui.backend.models.log import LLMLogEntryDetail, LLMLogListResponse
from web_ui.backend.services.log_service import get_log_service

router = APIRouter(prefix="/api/logs", tags=["logs"])

log_service = get_log_service()


@router.get("/llm", response_model=LLMLogListResponse)
async def list_llm_logs(
    limit: int = Query(200, ge=1, le=5000, description="Max entries to return (newest first)"),
    status: Optional[str] = Query(None, description="Filter by status: success | error"),
    provider: Optional[str] = Query(None, description="Filter by provider name"),
):
    """
    List LLM call summaries (newest first).

    Returns compact summaries (prompt preview only); fetch /api/logs/llm/{id}
    for the full input and output of a call.
    """
    try:
        entries, total = log_service.list_llm_logs(limit=limit, status=status, provider=provider)
        return LLMLogListResponse(entries=entries, total=total, returned=len(entries))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/llm/{entry_id}", response_model=LLMLogEntryDetail)
async def get_llm_log(entry_id: str):
    """
    Get the full detail of a single LLM call: complete input prompt and output.
    """
    try:
        entry = log_service.get_llm_log(entry_id)
        if entry is None:
            raise HTTPException(status_code=404, detail=f"Log entry {entry_id} not found")
        return entry
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/llm")
async def clear_llm_logs():
    """
    Clear all LLM call log entries.
    """
    try:
        log_service.clear_llm_logs()
        return {"message": "LLM call log cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
