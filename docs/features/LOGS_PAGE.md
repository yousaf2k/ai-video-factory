# Logs Page

A structured, read-only view of pipeline logs in the web UI, available at **`/log`** in the header navigation.

## Phase 1: LLM Call Log

Every text LLM call (story generation, scene graph, shot planning, JSON repair, narration summaries — anything that goes through the providers in `core/llm_engine.py`) is recorded with its **full input prompt and output**.

### UI

- **Top section** — list of LLM calls, newest first. Each row shows status (green/red dot), time, provider, model, duration, an input preview (the error message for failed calls), and the output size.
- **Bottom section** — detail of the selected call: provider/model/timestamp/duration/char counts/response format, an error banner for failures, and **Output / Input** tabs showing the full bodies. Copy button copies the visible tab.
- **Center splitter** — drag to resize the two sections (clamped 15–85%), double-click to reset to 45%. The position persists in `localStorage`.
- The list auto-refreshes every 10s; the newest entry is auto-selected on load. **Clear** wipes the whole log (confirm dialog).

### Where the data lives

Calls are appended as JSON lines to `output/logs/llm_calls.jsonl` (via `config.LOG_DIR`), written by `core/llm_call_log.py`. Recording is paired per-thread, so batched/parallel LLM calls are logged independently, and logging failures never break generation. Both CLI runs and web-UI generations write to the same file; the backend only reads it.

### API

| Endpoint | Description |
| --- | --- |
| `GET /api/logs/llm?limit=&status=&provider=` | Summaries (newest first, 300-char prompt preview), default limit 200 |
| `GET /api/logs/llm/{entry_id}` | Full detail: complete input prompt and output/error |
| `DELETE /api/logs/llm` | Clear the log |

### Code map

- `core/llm_call_log.py` — JSONL recorder; hooked into `LLMProvider.log_request_full` / `log_response_full` / `log_error` in `core/llm_engine.py`
- `web_ui/backend/api/logs.py` + `web_ui/backend/services/log_service.py` + `web_ui/backend/models/log.py` — API layer (mtime/size-cached parsing)
- `web_ui/frontend/src/app/log/page.tsx`, `src/hooks/useLLMLogs.ts` — UI
- Tests: `tests/unit/test_llm_call_log.py`

## Future phases (not implemented)

Generation/image/video logging tabs, filtering by project or call purpose, and log rotation/size caps.
