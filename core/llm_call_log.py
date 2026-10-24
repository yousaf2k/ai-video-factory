"""
Structured LLM call logging (JSONL) backing the "Logs" page in the web UI.

Every provider in core/llm_engine.py reports its traffic here through the
LLMProvider.log_request_full / log_response_full / log_error hooks. Each call
is appended as a single JSON line to <LOG_DIR>/llm_calls.jsonl:

    {"id": "...", "timestamp": "...", "provider": "Gemini", "model": "...",
     "response_format": "application/json", "prompt": "...", "prompt_chars": 1234,
     "status": "success", "output": "...", "output_chars": 567,
     "elapsed_sec": 3.42, "thread": "MainThread"}

The web backend reads that file and serves it at /api/logs/llm.

Request/response pairing uses thread-local state, so concurrent batched calls
(MAX_PARALLEL_BATCH_THREADS) each record their own pair. Logging failures are
swallowed — this module must never break generation.
"""
import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

_write_lock = threading.Lock()
_pending = threading.local()

LOG_FILENAME = "llm_calls.jsonl"


def _log_path() -> str:
    import config
    return config.resolve_path(os.path.join(config.LOG_DIR, LOG_FILENAME))


def begin_call(provider, prompt: str, response_format: Optional[str] = None) -> None:
    """Record the start of an LLM call on the current thread."""
    _pending.record = {
        "id": f"{int(time.time() * 1000):x}-{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.now().isoformat(timespec="milliseconds"),
        "provider": provider.name,
        "model": getattr(provider, "model", "") or "",
        "response_format": response_format,
        "prompt": prompt or "",
        "prompt_chars": len(prompt or ""),
        "thread": threading.current_thread().name,
    }


def complete_call(response: Optional[str], elapsed: float) -> None:
    """Complete the pending call on the current thread with a successful response."""
    record = getattr(_pending, "record", None)
    if not record:
        return
    _pending.record = None
    record["status"] = "success"
    record["output"] = response or ""
    record["output_chars"] = len(response or "")
    record["elapsed_sec"] = round(elapsed, 3)
    _append(record)


def fail_call(error: Exception, elapsed: float) -> None:
    """Complete the pending call on the current thread with a failure."""
    record = getattr(_pending, "record", None)
    if not record:
        return
    _pending.record = None
    record["status"] = "error"
    record["error"] = str(error)
    record["elapsed_sec"] = round(elapsed, 3)
    _append(record)


def _append(record: dict) -> None:
    try:
        line = json.dumps(record, ensure_ascii=False)
        path = _log_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with _write_lock:
            with open(path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception as e:
        logger.warning("Failed to write LLM call log entry: %s", e)
