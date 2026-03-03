# Bugfix: WinError 10055 (Socket Buffer Space Exhaustion)

## Symptoms

After running the backend for extended periods, or when generating long complex stories, the application crashed with:
`OSError: [WinError 10055] An operation on a socket could not be performed because the system lacked sufficient buffer space or because a queue was full`

## Root Cause

The backend was executing thousands of stateless HTTP requests (`requests.get()` and `requests.post()`) in rapid succession:

1. ComfyUI progress polling was running constantly without multiplexing connections.
2. The `core.llm_engine` and `core.narration_generator` modules were instantly connecting and dropping connections to LLM/TTS providers.

Because Windows holds closed sockets in a `TIME_WAIT` state for minutes to ensure delayed packets arrive, thousands of closed sockets tied up the OS socket buffer, leading to resource exhaustion.

## Resolution

Implemented an application-wide connection pooling mechanism:

1. Initialized a shared `http_session = requests.Session()` in `core.comfy_client`.
2. Replaced raw `requests.*()` calls throughout `core.comfy_client`, `core.comfyui_image_generator`, and `core.llm_engine` with `http_session`.
3. The underlying `urllib3` connection pool automatically handles connection reuse and keeps TLS handshakes alive, drastically lowering network overhead and preventing socket leaks.

## Affected Files

- `core/comfy_client.py`
- `core/comfyui_image_generator.py`
- `core/llm_engine.py`
