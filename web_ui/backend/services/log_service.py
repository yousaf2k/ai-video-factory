"""
Log Service - reads the structured LLM call log written by core/llm_call_log.py

The log is a JSONL file (<LOG_DIR>/llm_calls.jsonl) appended to by the LLM
providers (CLI runs and web-UI generations alike). This service parses it and
serves summaries (list view) and full entries (detail view) to /api/logs/llm.
"""
import json
import os
import threading
from typing import List, Optional, Tuple

import config
from web_ui.backend.models.log import LLMLogEntryDetail, LLMLogEntrySummary

PREVIEW_CHARS = 300


class LogService:
    def __init__(self):
        self._cache_lock = threading.Lock()
        self._cache: Tuple[float, int, List[dict]] = (0.0, 0, [])

    # ------------------------------------------------------------------
    # File access
    # ------------------------------------------------------------------
    def _log_file(self) -> str:
        return config.resolve_path(os.path.join(config.LOG_DIR, "llm_calls.jsonl"))

    def _read_entries(self) -> List[dict]:
        """Read all entries, newest last (file order). Cached on file mtime+size."""
        path = self._log_file()
        if not os.path.exists(path):
            return []

        try:
            stat = os.stat(path)
            stamp = (stat.st_mtime, stat.st_size)
        except OSError:
            return []

        with self._cache_lock:
            cached_stamp, cached_entries = self._cache[0:2], self._cache[2]
            if cached_stamp == stamp:
                return cached_entries

        entries: List[dict] = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue  # tolerate a partially-written trailing line
                    if isinstance(entry, dict) and entry.get("id"):
                        entries.append(entry)
        except OSError as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to read LLM call log: {e}")
            return []

        with self._cache_lock:
            self._cache = (stamp[0], stamp[1], entries)
        return entries

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def list_llm_logs(
        self,
        limit: int = 200,
        status: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> Tuple[List[LLMLogEntrySummary], int]:
        entries = self._read_entries()
        entries.reverse()  # newest first

        if status:
            entries = [e for e in entries if e.get("status") == status]
        if provider:
            entries = [e for e in entries if e.get("provider", "").lower() == provider.lower()]

        total = len(entries)
        summaries = [self._to_summary(e) for e in entries[:limit]]
        return summaries, total

    def get_llm_log(self, entry_id: str) -> Optional[LLMLogEntryDetail]:
        for entry in self._read_entries():
            if entry.get("id") == entry_id:
                return self._to_detail(entry)
        return None

    def clear_llm_logs(self) -> None:
        path = self._log_file()
        if os.path.exists(path):
            with self._cache_lock:
                self._cache = (0.0, 0, [])
            with open(path, "w", encoding="utf-8"):
                pass

    # ------------------------------------------------------------------
    # Shaping
    # ------------------------------------------------------------------
    def _to_summary(self, entry: dict) -> LLMLogEntrySummary:
        prompt = entry.get("prompt", "") or ""
        return LLMLogEntrySummary(
            id=entry.get("id", ""),
            timestamp=entry.get("timestamp", ""),
            provider=entry.get("provider", ""),
            model=entry.get("model", ""),
            status=entry.get("status", "success"),
            elapsed_sec=float(entry.get("elapsed_sec", 0.0) or 0.0),
            prompt_chars=int(entry.get("prompt_chars", len(prompt)) or 0),
            output_chars=int(entry.get("output_chars", 0) or 0),
            prompt_preview=prompt[:PREVIEW_CHARS],
            response_format=entry.get("response_format"),
            error=entry.get("error"),
        )

    def _to_detail(self, entry: dict) -> LLMLogEntryDetail:
        prompt = entry.get("prompt", "") or ""
        return LLMLogEntryDetail(
            id=entry.get("id", ""),
            timestamp=entry.get("timestamp", ""),
            provider=entry.get("provider", ""),
            model=entry.get("model", ""),
            status=entry.get("status", "success"),
            elapsed_sec=float(entry.get("elapsed_sec", 0.0) or 0.0),
            prompt_chars=int(entry.get("prompt_chars", len(prompt)) or 0),
            output_chars=int(entry.get("output_chars", 0) or 0),
            prompt_preview=prompt[:PREVIEW_CHARS],
            response_format=entry.get("response_format"),
            prompt=prompt,
            output=entry.get("output"),
            error=entry.get("error"),
            thread=entry.get("thread"),
        )


_log_service: Optional[LogService] = None


def get_log_service() -> LogService:
    global _log_service
    if _log_service is None:
        _log_service = LogService()
    return _log_service
