# Logging Module Usage Summary

## Overview
Your codebase uses two main logging modules:
- **`core/logger_config.py`** - Logger configuration and setup functions
- **`core/log_decorators.py`** - Decorators for automatic logging

---

## 1. logger_config.py Usage

### Setup Functions Imported:
- `get_logger()` - Standard logger
- `setup_agent_logger()` - Agent-specific logger
- `setup_api_logger()` - API-specific logger
- `setup_llm_io_logger()` - LLM input/output logger

### Files Using logger_config.py:

#### core/main.py
```python
from core.logger_config import get_logger
logger = get_logger(__name__)
```
**Purpose**: Pipeline orchestration logging

#### core/shot_planner.py (typo: file is named shot_planner.py)
```python
from core.logger_config import setup_agent_logger
logger = setup_agent_logger(__name__)
```
**Purpose**: Agent operation logging for shot planning

#### core/agent_loader.py
```python
from core.logger_config import setup_agent_logger
logger = setup_agent_logger(__name__)
```
**Purpose**: Agent loading operations

#### core/gemini_engine.py
```python
from core.logger_config import get_logger
logger = get_logger(__name__)
```
**Purpose**: Gemini API operations

#### core/comfy_client.py
```python
from core.logger_config import get_logger
logger = get_logger(__name__)
```
**Purpose**: ComfyUI client operations

#### core/session_manager.py
```python
from core.logger_config import get_logger
logger = get_logger(__name__)
```
**Purpose**: Session management operations

#### core/narration_generator.py
```python
from core.logger_config import get_logger
logger = get_logger(__name__)
```
**Purpose**: Narration/TTS operations

#### core/image_generator.py
```python
from core.logger_config import get_logger
logger = get_logger(__name__)
```
**Purpose**: Image generation operations

#### core/llm_engine.py
```python
from core.logger_config import setup_llm_io_logger
```
**Purpose**: LLM input/output logging (conditional import)

#### core/log_decorators.py
```python
from core.logger_config import get_logger, setup_api_logger, setup_agent_logger
```
**Purpose**: Decorators need access to logger setup functions

---

## 2. log_decorators.py Usage

### Decorators Available:
- `@log_agent_call` - Logs agent function calls
- `@log_api_call` - Logs API function calls
- `@log_errors` - Logs errors (though no active usage found)

### Files Using log_decorators.py:

#### core/shot_planner.py
```python
from core.log_decorators import log_agent_call

@log_agent_call
def plan_shots(scene_graph, max_shots=None, ...):
    """Plan cinematic shots..."""
```
**Purpose**: Automatically logs shot planning operations (input params, results, timing)

#### core/agent_loader.py
```python
from core.log_decorators import log_agent_call
```
**Purpose**: Ready for use on agent loading functions

#### core/gemini_engine.py
```python
from core.log_decorators import log_api_call

@log_api_call
def ask(prompt: str, response_format: str = None) -> str:
    """Send prompt to Gemini API..."""
```
**Purpose**: Automatically logs API calls to Gemini (prompt, response, timing)

---

## 3. Active Usage Summary

### Currently Active Decorators:
1. **`@log_agent_call`** in:
   - `core/shot_planner.py:plan_shots()` - Logs shot planning operations

2. **`@log_api_call`** in:
   - `core/gemini_engine.py:ask()` - Logs Gemini API calls

### Currently Inactive/Available:
- `@log_errors` decorator exists but no active usage found
- `agent_loader.py` imports `@log_agent_call` but doesn't use it on functions yet

---

## 4. Logging Flow Example

### Example 1: Shot Planning (core/shot_planner.py)
```python
# Import decorator and logger setup
from core.log_decorators import log_agent_call
from core.logger_config import setup_agent_logger

# Setup logger for this module
logger = setup_agent_logger(__name__)

# Decorated function - automatically logs:
# - Function entry with parameters
# - Function exit with results
# - Execution time
# - Any errors
@log_agent_call
def plan_shots(scene_graph, max_shots=None, ...):
    """Plan cinematic shots..."""
    # Function body logs via logger
    logger.info(f"Planning shots with max_shots={max_shots}")
    ...
```

### Example 2: Gemini API Call (core/gemini_engine.py)
```python
# Import decorator and logger setup
from core.log_decorators import log_api_call
from core.logger_config import get_logger

# Setup logger for this module
logger = get_logger(__name__)

# Decorated function - automatically logs:
# - API prompt input
# - API response output
# - Execution time
# - Any errors
@log_api_call
def ask(prompt: str, response_format: str = None) -> str:
    """Send prompt to Gemini API..."""
    logger.debug(f"Sending prompt to Gemini...")
    ...
```

---

## 5. Logger Types

### get_logger(__name__)
- **Used in**: main.py, gemini_engine.py, comfy_client.py, session_manager.py, narration_generator.py, image_generator.py
- **Purpose**: General-purpose module logging
- **Logs to**: `logs/app.log`

### setup_agent_logger(__name__)
- **Used in**: shot_planner.py, agent_loader.py
- **Purpose**: Agent-specific operations (LLM agent calls)
- **Logs to**: `logs/agents.log`
- **Benefits**:
  - Structured JSON format
  - Request/response tracking
  - Easier debugging of agent interactions

### setup_api_logger(__name__)
- **Imported in**: log_decorators.py
- **Purpose**: API-specific operations (Gemini, ElevenLabs, etc.)
- **Logs to**: `logs/api.log`

### setup_llm_io_logger(__name__)
- **Used in**: llm_engine.py (conditional import)
- **Purpose**: LLM input/output logging
- **Logs to**: `logs/llm_io.log`
- **Usage**: Captures full LLM prompts and responses

---

## 6. What Gets Logged

### With @log_agent_call decorator:
- Function name called
- Input parameters
- Return value (if successful)
- Execution time
- Error details (if exception raised)

**Example log output**:
```
[2025-01-15 10:30:45] [AGENT_CALL] plan_shots called with:
  scene_graph: [...]
  max_shots: 20
  image_agent: default
  video_agent: default
[2025-01-15 10:30:47] [AGENT_CALL] plan_shots completed in 2.3s
  Result: 20 shots generated
```

### With @log_api_call decorator:
- API endpoint called
- Request payload (prompt)
- Response data
- Execution time
- Error details (if API error)

**Example log output**:
```
[2025-01-15 10:30:50] [API_CALL] ask called with:
  prompt: "Generate shots for documentary..."
  response_format: "application/json"
[2025-01-15 10:30:52] [API_CALL] ask completed in 1.8s
  Response: {"shots": [...]}
```

---

## 7. Configuration

From config.py:
```python
# Logging Configuration
LOG_DIR = "logs"
CONSOLE_LOG_LEVEL = "INFO"
FILE_LOG_LEVEL = "DEBUG"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5
```

### Log Files Generated:
- `logs/app.log` - General application logs
- `logs/agents.log` - Agent operations (structured JSON)
- `logs/api.log` - API calls
- `logs/llm_io.log` - LLM input/output

---

## 8. Benefits

### 1. **Automatic Logging**
Decorators automatically log without manual logger calls in each function

### 2. **Consistent Format**
All logs follow the same structure for easier parsing

### 3. **Debugging Support**
Full request/response logging helps debug:
- Why shots aren't generating correctly
- API failures
- LLM prompt issues

### 4. **Performance Tracking**
Execution time logged automatically helps identify bottlenecks

### 5. **Error Tracking**
All errors logged with full context for easier troubleshooting

---

## 9. Potential Improvements

### 1. Add @log_agent_call to more functions
Currently only used in:
- `plan_shots()`

Could add to:
- `build_story()` in story_engine.py
- `build_scene_graph()` in scene_graph.py
- `generate_narration_script()` in narration_generator.py

### 2. Add @log_api_call to more API functions
Currently only used in:
- `gemini_engine.ask()`

Could add to:
- ComfyUI API calls in comfy_client.py
- ElevenLabs API calls (if any)
- Other LLM provider APIs

### 3. Add @log_errors to critical functions
No active usage found, but decorator exists. Could add to:
- File I/O operations
- Network operations
- External service calls

---

## 10. File Path Note

**⚠️ Typo Alert**: Some imports reference `shot_planner.py` but the actual file may be named `shot_planner.py` (typo in original code).

Check if you have:
- `core/shot_planner.py` ✓ (correct)
- `core/shot_planner.py` ✗ (typo)

The git status shows:
```
M core/__pycache__/shot_planner.cpython-311.pyc
```

This suggests the file is `shot_planner.py` (with underscore).

---

## Summary

Your logging system is well-structured with:
- ✅ **11 files** using logger_config.py
- ✅ **3 files** using log_decorators.py
- ✅ **2 decorators** actively used (@log_agent_call, @log_api_call)
- ✅ **4 log types** (app, agents, api, llm_io)
- ✅ **Automatic logging** for critical operations (API calls, agent calls)

The decorators provide automatic, structured logging without cluttering function code with manual logger calls.
