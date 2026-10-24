"""
Unit tests for structured LLM call logging (core/llm_call_log.py) and the
web backend LogService that serves it to the Logs page.

Covers:
- success / error call recording to JSONL
- orphan fail_call (no pending begin) is ignored
- list ordering (newest first) + preview truncation
- detail lookup (full prompt + output) and missing ids
- corrupt JSONL lines are tolerated
- clear empties the log
"""
import json
import os
import sys

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core import llm_call_log
from web_ui.backend.services.log_service import LogService


class _FakeProvider:
    name = "Gemini"
    model = "gemini-test"


@pytest.fixture
def log_file(tmp_path, monkeypatch):
    path = tmp_path / "llm_calls.jsonl"
    monkeypatch.setattr(llm_call_log, "_log_path", lambda: str(path))
    yield path
    # Reset thread-local pending state between tests
    llm_call_log._pending.record = None


@pytest.fixture
def service(log_file):
    svc = LogService()
    svc._log_file = lambda: str(log_file)
    return svc


def _record_success(prompt="hello", output="world", elapsed=1.0):
    llm_call_log.begin_call(_FakeProvider(), prompt, "application/json")
    llm_call_log.complete_call(output, elapsed)


def _record_error(prompt="bad prompt", error="boom", elapsed=0.5):
    llm_call_log.begin_call(_FakeProvider(), prompt, None)
    llm_call_log.fail_call(Exception(error), elapsed)


class TestLLMCallLogRecorder:
    def test_success_entry_written(self, log_file):
        _record_success(prompt="my prompt", output="my output", elapsed=1.234)

        entries = [json.loads(l) for l in log_file.read_text(encoding="utf-8").splitlines()]
        assert len(entries) == 1
        entry = entries[0]
        assert entry["provider"] == "Gemini"
        assert entry["model"] == "gemini-test"
        assert entry["status"] == "success"
        assert entry["prompt"] == "my prompt"
        assert entry["prompt_chars"] == 9
        assert entry["output"] == "my output"
        assert entry["output_chars"] == 9
        assert entry["elapsed_sec"] == 1.234
        assert entry["response_format"] == "application/json"
        assert entry["id"]

    def test_error_entry_written(self, log_file):
        _record_error(prompt="bad", error="exploded", elapsed=0.25)

        entry = json.loads(log_file.read_text(encoding="utf-8").splitlines()[0])
        assert entry["status"] == "error"
        assert entry["error"] == "exploded"
        assert entry["elapsed_sec"] == 0.25

    def test_fail_without_begin_is_ignored(self, log_file):
        llm_call_log.fail_call(Exception("orphan"), 1.0)
        assert not log_file.exists()

    def test_multiple_calls_append(self, log_file):
        _record_success("a", "b", 0.1)
        _record_error("c", "d", 0.2)
        _record_success("e", "f", 0.3)
        assert len(log_file.read_text(encoding="utf-8").splitlines()) == 3


class TestLogService:
    def test_list_newest_first_and_preview(self, service):
        _record_success("x" * 500, "short", 1.0)
        _record_success("newest prompt", "out", 2.0)

        entries, total = service.list_llm_logs()
        assert total == 2
        assert entries[0].prompt_preview == "newest prompt"
        assert entries[1].prompt_preview.startswith("xxx")
        assert len(entries[1].prompt_preview) == 300  # truncated preview

    def test_list_ascending_returns_oldest_first(self, service):
        _record_success("oldest", "a", 1.0)
        _record_success("middle", "b", 1.0)
        _record_success("newest", "c", 1.0)

        entries, total = service.list_llm_logs(order="asc")
        assert total == 3
        assert [e.prompt_preview for e in entries] == ["oldest", "middle", "newest"]

        entries, total = service.list_llm_logs(order="desc")
        assert total == 3
        assert [e.prompt_preview for e in entries] == ["newest", "middle", "oldest"]

    def test_get_detail_returns_full_bodies(self, service):
        _record_success("full prompt body", "full output body", 0.75)
        entries, _ = service.list_llm_logs()

        detail = service.get_llm_log(entries[0].id)
        assert detail is not None
        assert detail.prompt == "full prompt body"
        assert detail.output == "full output body"
        assert detail.status == "success"

    def test_get_missing_entry_returns_none(self, service):
        assert service.get_llm_log("does-not-exist") is None

    def test_corrupt_lines_are_skipped(self, service, log_file):
        _record_success("good", "entry", 1.0)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write('{"id": "broken", "prompt": "trunca\n')  # partial write
        _record_success("after", "corruption", 1.0)

        entries, total = service.list_llm_logs()
        assert total == 2
        assert {e.prompt_preview for e in entries} == {"good", "after"}

    def test_clear_empties_log(self, service):
        _record_success("a", "b", 1.0)
        assert service.list_llm_logs()[1] == 1

        service.clear_llm_logs()
        entries, total = service.list_llm_logs()
        assert total == 0 and entries == []

    def test_repeated_calls_keep_stable_order(self, service):
        # Regression: list_llm_logs must not reverse the shared cache in place
        # (that flipped the list order on every consecutive call).
        _record_success("a-first", "1", 0.1)
        _record_success("b-second", "2", 0.1)

        first, _ = service.list_llm_logs()
        second, _ = service.list_llm_logs()
        assert [e.id for e in first] == [e.id for e in second]
        assert [e.prompt_preview for e in first] == ["b-second", "a-first"]

        again_desc, _ = service.list_llm_logs(order="desc")
        assert [e.prompt_preview for e in again_desc] == ["b-second", "a-first"]

    def test_status_filter(self, service):
        _record_success("ok", "yes", 1.0)
        _record_error("nope", "failed", 0.1)

        ok_entries, total = service.list_llm_logs(status="success")
        assert total == 1
        assert ok_entries[0].prompt_preview == "ok"
