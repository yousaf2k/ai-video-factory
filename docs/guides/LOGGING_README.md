# Logging Documentation

## Overview

The AI Video Factory now includes comprehensive logging infrastructure using Python's built-in `logging` module. This provides persistent error tracking, API call auditing, and agent operation monitoring.

## Log Files

All log files are stored in the `logs/` directory:

- **app.log** - General application logs (INFO level and above)
- **errors.log** - Error-only logs (ERROR level and above)
- **api_calls.log** - Gemini API calls (DEBUG level)
- **agents.log** - Agent operations (DEBUG level)

### Log Format

```
YYYY-MM-DD HH:MM:SS | LEVEL | module:function():line | message
```

Example:
```
2026-02-14 10:30:15 | DEBUG    | gemini_engine:ask():50 | API CALL: ask()
2026-02-14 10:30:15 | DEBUG    | gemini_engine:ask():50 |   Args: prompt="Expand this story...", response_format="application/json"
2026-02-14 10:30:16 | DEBUG    | gemini_engine:ask():50 |   Response: {"title": "Ocean's Wrath"...}
2026-02-14 10:30:16 | DEBUG    | gemini_engine:ask():50 |   Success in 1.23s
```

## Configuration

Logging is configured in `config.py`:

```python
# ==========================================
# LOGGING CONFIGURATION
# ==========================================
LOG_DIR = "logs"
CONSOLE_LOG_LEVEL = "INFO"
FILE_LOG_LEVEL = "DEBUG"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5
```

- **LOG_DIR**: Directory for log files (default: "logs")
- **CONSOLE_LOG_LEVEL**: Minimum level for console output (DEBUG, INFO, WARNING, ERROR)
- **FILE_LOG_LEVEL**: Minimum level for file output
- **LOG_MAX_BYTES**: Maximum size of each log file before rotation (default: 10MB)
- **LOG_BACKUP_COUNT**: Number of backup files to keep (default: 5)

## Log Rotation

Log files automatically rotate when they reach `LOG_MAX_BYTES`:

- Current log: `app.log`
- Backups: `app.log.1`, `app.log.2`, ..., `app.log.5`

When `app.log` reaches 10MB:
- `app.log` → `app.log.1`
- `app.log.1` → `app.log.2`
- ...
- `app.log.5` is deleted
- New `app.log` is created

## Usage

### In Your Code

```python
from core.logger_config import get_logger

# Get a logger for your module
logger = get_logger(__name__)

# Use standard logging methods
logger.debug("Detailed diagnostic info")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred")
```

### Decorators

Three decorators are available for automatic logging:

#### @log_api_call

Logs API calls with timing, request/response preview, and errors:

```python
from core.log_decorators import log_api_call

@log_api_call
def api_function(param1, param2):
    # Automatically logs:
    # - Function call with parameters
    # - Execution time
    # - Response preview
    # - Any errors with traceback
    return result
```

#### @log_agent_call

Logs agent operations with parameters and results:

```python
from core.log_decorators import log_agent_call

@log_agent_call
def load_agent_prompt(agent_type, agent_name):
    # Automatically logs:
    # - Agent type and name
    # - Prompt length
    # - File path
    # - Execution status
    return prompt
```

#### @log_errors

Catches and logs exceptions with full traceback:

```python
from core.log_decorators import log_errors

@log_errors
def risky_operation(value):
    # Automatically logs:
    # - Function name and location
    # - Full exception traceback
    # - Parameters that caused error
    if value < 0:
        raise ValueError("Invalid value")
    return result
```

## Implementation Status

### Completed Modules

✅ **core/logger_config.py** - Logging infrastructure setup
✅ **core/log_decorators.py** - Decorators for automatic logging
✅ **config.py** - Logging configuration section
✅ **core/gemini_engine.py** - API calls with @log_api_call
✅ **core/agent_loader.py** - Agent operations with @log_agent_call
✅ **core/shot_planner.py** - Shot planning with @log_agent_call
✅ **core/image_generator.py** - Image generation logging
✅ **core/narration_generator.py** - TTS operations logging
✅ **core/comfy_client.py** - ComfyUI API interactions logging
✅ **core/session_manager.py** - Session state and file operations logging
✅ **core/main.py** - Pipeline orchestration logging

### What Gets Logged

#### API Calls (api_calls.log)
- Gemini API requests/responses
- Execution time for each call
- Request parameters (truncated to 200 chars)
- Response preview (truncated to 200 chars)
- All errors with full traceback

#### Agent Operations (agents.log)
- Agent type (story, narration, image, video)
- Agent name (default, dramatic, documentary, etc.)
- File paths for agent prompts
- Prompt/response lengths
- Loading status

#### Application Logs (app.log)
- Session lifecycle (creation, updates, completion)
- Workflow step progression
- Image/video generation parameters
- TTS operations
- General INFO and WARNING messages

#### Errors (errors.log)
- All ERROR level messages
- Complete exception tracebacks
- API failures
- File operation errors
- All critical issues

## Testing

### Test Logging Infrastructure

```bash
# Run logging test
python core/logger_config.py

# Check logs were created
ls -la logs/

# View log files
cat logs/app.log
cat logs/api_calls.log
cat logs/agents.log
cat logs/errors.log
```

### Test with Actual Operations

```bash
# Test story generation (logs to api_calls.log and agents.log)
python -c "from core.story_engine import build_story; print(build_story('A cat dancing'))"

# Test agent loading (logs to agents.log)
python -c "from core.agent_loader import AgentLoader; AgentLoader().list_agents('story')"
```

## Troubleshooting

### Logs Not Created

1. Check `LOG_DIR` in config.py exists
2. Ensure directory is writable
3. Run: `python core/logger_config.py`

### Too Much Log Output

1. Increase `CONSOLE_LOG_LEVEL` to "WARNING" or "ERROR"
2. Keep `FILE_LOG_LEVEL` at "DEBUG" for troubleshooting

### Log Files Too Large

1. Check `LOG_MAX_BYTES` setting (default: 10MB)
2. Increase if needed: `LOG_MAX_BYTES = 50 * 1024 * 1024` (50MB)
3. Old logs automatically rotate based on `LOG_BACKUP_COUNT`

## Best Practices

1. **Always use get_logger()** - Don't create loggers directly
2. **Use appropriate log levels**:
   - DEBUG: Detailed diagnostic info (parameters, data structures)
   - INFO: General information (step completion, status updates)
   - WARNING: Warnings that don't stop execution (fallbacks, missing files)
   - ERROR: Errors that affect functionality (exceptions, failures)
3. **Use decorators for consistency** - @log_api_call, @log_agent_call, @log_errors
4. **Keep user-facing print()** - Console output for user interaction remains as print()
5. **Don't log sensitive data** - API keys, passwords, personal information
