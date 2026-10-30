"""
Configuration API endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, BeforeValidator
from typing import Annotated, Optional
import sys
import os
import re
import logging
from typing import Optional, Dict, Tuple

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))

from core.director_loader import list_directors, get_director_loader
from core.workflow_loader import get_workflow_loader
from core.config_utils import update_env_config
import asyncio
import threading
import subprocess
import time

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/config", tags=["config"])

# --------------------------------------------------------------------------
# Declarative registry of environment-backed settings editable from the Web UI
# Configuration page. field name (lowercase env key) -> (ENV_KEY, config
# attribute, python type). "attr" differs from ENV_KEY only where config.py
# names the constant differently (e.g. GEMINI_MODEL -> GEMINI_TEXT_MODEL).
# The GET endpoint returns every field; POST writes to .env, the config
# module and os.environ so changes apply live and persist across restarts.
# --------------------------------------------------------------------------
_CONFIG_FIELDS: Dict[str, Tuple[str, str, str]] = {
    # LLM providers
    "llm_provider":                 ("LLM_PROVIDER", "LLM_PROVIDER", "str"),
    "gemini_model":                 ("GEMINI_MODEL", "GEMINI_TEXT_MODEL", "str"),
    "gemini_base_url":              ("GEMINI_BASE_URL", "GEMINI_BASE_URL", "str"),
    "openai_model":                 ("OPENAI_MODEL", "OPENAI_MODEL", "str"),
    "openai_base_url":              ("OPENAI_BASE_URL", "OPENAI_BASE_URL", "str"),
    "zhipu_base_url":               ("ZHIPU_BASE_URL", "ZHIPU_BASE_URL", "str"),
    "qwen_model":                   ("QWEN_MODEL", "QWEN_MODEL", "str"),
    "qwen_base_url":                ("QWEN_BASE_URL", "QWEN_BASE_URL", "str"),
    "kimi_model":                   ("KIMI_MODEL", "KIMI_MODEL", "str"),
    "kimi_base_url":                ("KIMI_BASE_URL", "KIMI_BASE_URL", "str"),
    "zhipu_model":                  ("ZHIPU_MODEL", "ZHIPU_MODEL", "str"),
    "deepseek_model":               ("DEEPSEEK_MODEL", "DEEPSEEK_MODEL", "str"),
    "deepseek_base_url":            ("DEEPSEEK_BASE_URL", "DEEPSEEK_BASE_URL", "str"),
    "ollama_base_url":              ("OLLAMA_BASE_URL", "OLLAMA_BASE_URL", "str"),
    "ollama_model":                 ("OLLAMA_MODEL", "OLLAMA_MODEL", "str"),
    "lmstudio_base_url":            ("LMSTUDIO_BASE_URL", "LMSTUDIO_BASE_URL", "str"),
    "lmstudio_model":               ("LMSTUDIO_MODEL", "LMSTUDIO_MODEL", "str"),
    "llm_max_tokens":               ("LLM_MAX_TOKENS", "LLM_MAX_TOKENS", "int"),
    "shot_generation_batch_size":   ("SHOT_GENERATION_BATCH_SIZE", "SHOT_GENERATION_BATCH_SIZE", "int"),
    "max_parallel_batch_threads":   ("MAX_PARALLEL_BATCH_THREADS", "MAX_PARALLEL_BATCH_THREADS", "int"),
    # Per-provider tuning overrides (empty string = inherit the global value)
    "gemini_max_tokens":            ("GEMINI_MAX_TOKENS", "GEMINI_MAX_TOKENS", "str"),
    "gemini_shot_batch_size":       ("GEMINI_SHOT_BATCH_SIZE", "GEMINI_SHOT_BATCH_SIZE", "str"),
    "gemini_parallel_batch_threads": ("GEMINI_PARALLEL_BATCH_THREADS", "GEMINI_PARALLEL_BATCH_THREADS", "str"),
    "openai_max_tokens":            ("OPENAI_MAX_TOKENS", "OPENAI_MAX_TOKENS", "str"),
    "openai_shot_batch_size":       ("OPENAI_SHOT_BATCH_SIZE", "OPENAI_SHOT_BATCH_SIZE", "str"),
    "openai_parallel_batch_threads": ("OPENAI_PARALLEL_BATCH_THREADS", "OPENAI_PARALLEL_BATCH_THREADS", "str"),
    "zhipu_max_tokens":             ("ZHIPU_MAX_TOKENS", "ZHIPU_MAX_TOKENS", "str"),
    "zhipu_shot_batch_size":        ("ZHIPU_SHOT_BATCH_SIZE", "ZHIPU_SHOT_BATCH_SIZE", "str"),
    "zhipu_parallel_batch_threads": ("ZHIPU_PARALLEL_BATCH_THREADS", "ZHIPU_PARALLEL_BATCH_THREADS", "str"),
    "qwen_max_tokens":              ("QWEN_MAX_TOKENS", "QWEN_MAX_TOKENS", "str"),
    "qwen_shot_batch_size":         ("QWEN_SHOT_BATCH_SIZE", "QWEN_SHOT_BATCH_SIZE", "str"),
    "qwen_parallel_batch_threads":  ("QWEN_PARALLEL_BATCH_THREADS", "QWEN_PARALLEL_BATCH_THREADS", "str"),
    "kimi_max_tokens":              ("KIMI_MAX_TOKENS", "KIMI_MAX_TOKENS", "str"),
    "kimi_shot_batch_size":         ("KIMI_SHOT_BATCH_SIZE", "KIMI_SHOT_BATCH_SIZE", "str"),
    "kimi_parallel_batch_threads":  ("KIMI_PARALLEL_BATCH_THREADS", "KIMI_PARALLEL_BATCH_THREADS", "str"),
    "deepseek_max_tokens":          ("DEEPSEEK_MAX_TOKENS", "DEEPSEEK_MAX_TOKENS", "str"),
    "deepseek_shot_batch_size":     ("DEEPSEEK_SHOT_BATCH_SIZE", "DEEPSEEK_SHOT_BATCH_SIZE", "str"),
    "deepseek_parallel_batch_threads": ("DEEPSEEK_PARALLEL_BATCH_THREADS", "DEEPSEEK_PARALLEL_BATCH_THREADS", "str"),
    "ollama_max_tokens":            ("OLLAMA_MAX_TOKENS", "OLLAMA_MAX_TOKENS", "str"),
    "ollama_shot_batch_size":       ("OLLAMA_SHOT_BATCH_SIZE", "OLLAMA_SHOT_BATCH_SIZE", "str"),
    "ollama_parallel_batch_threads": ("OLLAMA_PARALLEL_BATCH_THREADS", "OLLAMA_PARALLEL_BATCH_THREADS", "str"),
    "lmstudio_max_tokens":          ("LMSTUDIO_MAX_TOKENS", "LMSTUDIO_MAX_TOKENS", "str"),
    "lmstudio_shot_batch_size":     ("LMSTUDIO_SHOT_BATCH_SIZE", "LMSTUDIO_SHOT_BATCH_SIZE", "str"),
    "lmstudio_parallel_batch_threads": ("LMSTUDIO_PARALLEL_BATCH_THREADS", "LMSTUDIO_PARALLEL_BATCH_THREADS", "str"),
    # Generation engines
    "image_generation_mode":        ("IMAGE_GENERATION_MODE", "IMAGE_GENERATION_MODE", "str"),
    "image_workflow":               ("IMAGE_WORKFLOW", "IMAGE_WORKFLOW", "str"),
    "video_generation_mode":        ("VIDEO_GENERATION_MODE", "VIDEO_GENERATION_MODE", "str"),
    "video_workflow":               ("VIDEO_WORKFLOW", "VIDEO_WORKFLOW", "str"),
    "soundfx_workflow":             ("SOUNDFX_WORKFLOW", "SOUNDFX_WORKFLOW", "str"),
    "prompt_mode":                  ("PROMPT_MODE", "DEFAULT_PROMPT_MODE", "str"),
    # ComfyUI
    "comfy_url":                    ("COMFY_URL", "COMFY_URL", "str"),
    "comfy_output_dir":             ("COMFY_OUTPUT_DIR", "COMFY_OUTPUT_DIR", "str"),
    "comfy_input_dir":              ("COMFY_INPUT_DIR", "COMFY_INPUT_DIR", "str"),
    # Image & video defaults
    "image_aspect_ratio":           ("IMAGE_ASPECT_RATIO", "IMAGE_ASPECT_RATIO", "str"),
    "image_resolution":             ("IMAGE_RESOLUTION", "IMAGE_RESOLUTION", "str"),
    "video_aspect_ratio":           ("VIDEO_ASPECT_RATIO", "VIDEO_ASPECT_RATIO", "str"),
    "video_resolution":             ("VIDEO_RESOLUTION", "VIDEO_RESOLUTION", "str"),
    "target_video_length":          ("TARGET_VIDEO_LENGTH", "TARGET_VIDEO_LENGTH", "int"),
    "default_shot_length":          ("DEFAULT_SHOT_LENGTH", "DEFAULT_SHOT_LENGTH", "float"),
    # Narration / TTS
    "generate_narration":           ("GENERATE_NARRATION", "GENERATE_NARRATION", "bool"),
    "tts_method":                   ("TTS_METHOD", "TTS_METHOD", "str"),
    "tts_voice":                    ("TTS_VOICE", "TTS_VOICE", "str"),
    "elevenlabs_model":             ("ELEVENLABS_MODEL", "ELEVENLABS_MODEL", "str"),
    "elevenlabs_stability":         ("ELEVENLABS_STABILITY", "ELEVENLABS_STABILITY", "float"),
    "elevenlabs_similarity":        ("ELEVENLABS_SIMILARITY", "ELEVENLABS_SIMILARITY", "float"),
    # Performance & reliability
    "concurrent_comfyui_limit":     ("CONCURRENT_COMFYUI_LIMIT", "CONCURRENT_COMFYUI_LIMIT", "int"),
    "concurrent_gemini_limit":      ("CONCURRENT_GEMINI_LIMIT", "CONCURRENT_GEMINI_LIMIT", "int"),
    "concurrent_geminiweb_limit":   ("CONCURRENT_GEMINIWEB_LIMIT", "CONCURRENT_GEMINIWEB_LIMIT", "int"),
    "concurrent_default_limit":     ("CONCURRENT_DEFAULT_LIMIT", "CONCURRENT_DEFAULT_LIMIT", "int"),
    "concurrent_generation_limit":  ("CONCURRENT_GENERATION_LIMIT", "CONCURRENT_GENERATION_LIMIT", "int"),
    "flow_project_concurrency":     ("FLOW_PROJECT_CONCURRENCY", "FLOW_PROJECT_CONCURRENCY", "int"),
    "video_render_timeout":         ("VIDEO_RENDER_TIMEOUT", "VIDEO_RENDER_TIMEOUT", "int"),
    "image_generation_max_retries": ("IMAGE_GENERATION_MAX_RETRIES", "IMAGE_GENERATION_MAX_RETRIES", "int"),
    "image_generation_retry_delay": ("IMAGE_GENERATION_RETRY_DELAY", "IMAGE_GENERATION_RETRY_DELAY", "int"),
    "continue_on_partial_image_failure": ("CONTINUE_ON_PARTIAL_IMAGE_FAILURE", "CONTINUE_ON_PARTIAL_IMAGE_FAILURE", "bool"),
    # Browser automation (GeminiWeb / Flow)
    "geminiweb_model":              ("GEMINIWEB_MODEL", "GEMINIWEB_MODEL", "str"),
    "geminiweb_thinking":           ("GEMINIWEB_THINKING", "GEMINIWEB_THINKING", "str"),
    "geminiweb_default_mode":       ("GEMINIWEB_DEFAULT_MODE", "GEMINIWEB_DEFAULT_MODE", "str"),
    "geminiweb_timeout":            ("GEMINIWEB_TIMEOUT", "GEMINIWEB_TIMEOUT", "int"),
    "geminiweb_chat_lock_timeout":  ("GEMINIWEB_CHAT_LOCK_TIMEOUT", "GEMINIWEB_CHAT_LOCK_TIMEOUT", "int"),
    "geminiweb_chrome_profile":     ("GEMINIWEB_CHROME_PROFILE", "GEMINIWEB_CHROME_PROFILE", "str"),
    "flowweb_url":                  ("FLOWWEB_URL", "FLOWWEB_URL", "str"),
    "flowweb_timeout":              ("FLOWWEB_TIMEOUT", "FLOWWEB_TIMEOUT", "int"),
    "flow_image_model":             ("FLOW_IMAGE_MODEL", "FLOW_IMAGE_MODEL", "str"),
    "flow_image_outputs":           ("FLOW_IMAGE_OUTPUTS", "FLOW_IMAGE_OUTPUTS", "str"),
    # Watermark removal
    "watermark_removal_method":     ("WATERMARK_REMOVAL_METHOD", "WATERMARK_REMOVAL_METHOD", "str"),
    "gemini_watermark_tool_image":  ("GEMINI_WATERMARK_TOOL_IMAGE", "GEMINI_WATERMARK_TOOL_IMAGE", "str"),
    "gemini_watermark_tool_video":  ("GEMINI_WATERMARK_TOOL_VIDEO", "GEMINI_WATERMARK_TOOL_VIDEO", "str"),
    # Paths & storage
    "output_dir":                   ("OUTPUT_DIR", "OUTPUT_DIR", "str"),
    "asset_library_dirs":           ("ASSET_LIBRARY_DIRS", "ASSET_LIBRARY_DIRS", "str"),
    # Web UI server
    "web_ui_enabled":               ("WEB_UI_ENABLED", "WEB_UI_ENABLED", "bool"),
    "backend_host":                 ("BACKEND_HOST", "BACKEND_HOST", "str"),
    "backend_port":                 ("BACKEND_PORT", "BACKEND_PORT", "int"),
    "backend_bind_host":            ("BACKEND_BIND_HOST", "BACKEND_BIND_HOST", "str"),
    "frontend_host":                ("FRONTEND_HOST", "FRONTEND_HOST", "str"),
    "frontend_port":                ("FRONTEND_PORT", "FRONTEND_PORT", "int"),
    "frontend_bind_host":           ("FRONTEND_BIND_HOST", "FRONTEND_BIND_HOST", "str"),
    "web_ui_cors_origins":          ("WEB_UI_CORS_ORIGINS", "WEB_UI_CORS_ORIGINS", "str"),
}

# Write-only secret fields (API keys). GET never returns their values, only
# "<field>_set": true/false flags. POST only applies non-empty values.
_SECRET_FIELDS: Dict[str, str] = {
    "gemini_api_key":     "GEMINI_API_KEY",
    "openai_api_key":     "OPENAI_API_KEY",
    "zhipu_api_key":      "ZHIPU_API_KEY",
    "qwen_api_key":       "QWEN_API_KEY",
    "kimi_api_key":       "KIMI_API_KEY",
    "deepseek_api_key":   "DEEPSEEK_API_KEY",
    "elevenlabs_api_key": "ELEVENLABS_API_KEY",
}

def _stringify(v):
    """Coerce JSON numbers/bools to string before str validation (Pydantic v2
    refuses int->str). Number inputs for override fields send numbers."""
    return v if v is None or isinstance(v, str) else str(v)


_FIELD_TYPE_MAP = {"str": (str, Optional[Annotated[str, BeforeValidator(_stringify)]]),
                   "int": (int, Optional[int]),
                   "float": (float, Optional[float]), "bool": (bool, Optional[bool])}


def _build_update_model():
    """Generate UpdateConfigRequest from the registry so the request model
    always matches the editable fields (plus the special playwright_browser)."""
    import pydantic
    fields = {}
    for name, (_, _, ftype) in _CONFIG_FIELDS.items():
        fields[name] = (_FIELD_TYPE_MAP[ftype][1], None)
    for name in _SECRET_FIELDS:
        fields[name] = (Optional[str], None)
    fields["playwright_browser"] = (Optional[str], None)
    return pydantic.create_model("UpdateConfigRequest", **fields)


UpdateConfigRequest = _build_update_model()


def _coerce_value(value, ftype: str):
    """Coerce an incoming value to the field's python type."""
    if ftype == "int":
        return int(float(value))
    if ftype == "float":
        return float(value)
    if ftype == "bool":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ("1", "true", "yes", "on")
    return str(value)


class UpdateDirectorRequest(BaseModel):
    """Request to update an director prompt file"""
    content: str


class UpdateWorkflowRequest(BaseModel):
    """Request to update a workflow JSON file"""
    content: str


@router.get("/styles")
async def get_styles():
    """Named generation styles (styles.json) for the UI dropdowns. The file is
    re-read on every call, so edits apply without a backend restart."""
    import config
    return {"background_styles": config.load_background_styles()}


@router.get("/directors")
async def get_directors():
    """Get list of available directors for each stage"""
    try:
        # List all directors
        all_directors = list_directors()

        # Group by type
        directors_by_type = {
            "story": [],
            "shots": [],
        }

        for director_info in all_directors:
            director_type = director_info.get("type", "unknown")
            director_id = director_info.get("id", "unknown")
            director_name = director_info.get("name", director_id)

            category = None
            if "/" in director_id:
                category, name = director_id.split("/", 1)
                director_name = name.replace('_', ' ').title()

            if director_type in directors_by_type:
                item = {
                    "id": director_id,
                    "name": director_name,
                    "type": director_type
                }
                if category:
                    item["category"] = category
                directors_by_type[director_type].append(item)

        # Sort alphabetically by name
        for director_type in directors_by_type:
            directors_by_type[director_type].sort(key=lambda x: x["name"])

        return directors_by_type

    except Exception as e:
        logger.error(f"Error listing directors: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list directors: {str(e)}"
        )


@router.get("")
async def get_config():
    """Get all configuration values (secrets excluded, only *_set flags)"""
    try:
        import config

        safe_config = {}
        for name, (_, attr, ftype) in _CONFIG_FIELDS.items():
            value = getattr(config, attr, None)
            if value is None:
                value = os.environ.get(_CONFIG_FIELDS[name][0], "")
            safe_config[name] = value

        # Extra read-only context for the UI dropdowns and defaults
        safe_config.update({
            "default_story_director": getattr(config, 'DEFAULT_STORY_DIRECTOR', 'default'),
            "default_shots_director": getattr(config, 'DEFAULT_SHOTS_DIRECTOR', 'default'),
            "default_max_shots": getattr(config, 'DEFAULT_MAX_SHOTS', 0),
            "available_video_workflows": list(getattr(config, 'VIDEO_WORKFLOWS', {}).keys()),
            "available_image_workflows": list(getattr(config, 'IMAGE_WORKFLOWS', {}).keys()),
            "available_soundfx_workflows": list(getattr(config, 'SOUNDFX_WORKFLOWS', {}).keys()),
            # playwright_browser combines PLAYWRIGHT_BROWSER + PLAYWRIGHT_CHANNEL
            "playwright_browser": (
                getattr(config, 'PLAYWRIGHT_CHANNEL', '') if getattr(config, 'PLAYWRIGHT_CHANNEL', '') in ['chrome', 'msedge']
                else getattr(config, 'PLAYWRIGHT_BROWSER', 'chromium')
            ),
        })

        # WEB_UI_CORS_ORIGINS is a list in config; expose it comma-separated
        if isinstance(safe_config.get("web_ui_cors_origins"), (list, tuple)):
            safe_config["web_ui_cors_origins"] = ",".join(safe_config["web_ui_cors_origins"])

        # Secret fields: only expose whether a value is configured
        for name, env_key in _SECRET_FIELDS.items():
            safe_config[f"{name}_set"] = bool(getattr(config, env_key, "") or os.environ.get(env_key, ""))

        return safe_config

    except Exception as e:
        logger.error(f"Error getting config: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get config: {str(e)}"
        )


@router.post("")
async def update_config(request: UpdateConfigRequest):
    """Update global configuration (writes .env and applies live)"""
    try:
        import config

        updates = request.model_dump(exclude_unset=True)
        env_updates = {}   # ENV_KEY -> string value written to .env / os.environ
        attr_updates = {}  # config attribute -> coerced python value

        for name, value in updates.items():
            if value is None:
                continue

            if name in _SECRET_FIELDS:
                if str(value).strip() == "":
                    continue  # empty means "keep existing key"
                env_key = _SECRET_FIELDS[name]
                env_updates[env_key] = str(value)
                attr_updates[env_key] = str(value)
                continue

            if name == "playwright_browser":
                # Browser + channel are set together: chrome/msedge select the
                # chromium engine with a channel, everything else stands alone
                browser = str(value)
                if browser in ["chrome", "msedge"]:
                    env_updates["PLAYWRIGHT_BROWSER"] = "chromium"
                    env_updates["PLAYWRIGHT_CHANNEL"] = browser
                    attr_updates["PLAYWRIGHT_BROWSER"] = "chromium"
                    attr_updates["PLAYWRIGHT_CHANNEL"] = browser
                else:
                    env_updates["PLAYWRIGHT_BROWSER"] = browser
                    env_updates["PLAYWRIGHT_CHANNEL"] = ""
                    attr_updates["PLAYWRIGHT_BROWSER"] = browser
                    attr_updates["PLAYWRIGHT_CHANNEL"] = ""
                continue

            env_key, attr, ftype = _CONFIG_FIELDS[name]
            coerced = _coerce_value(value, ftype)
            if name == "web_ui_cors_origins":
                # config stores CORS origins as a list
                coerced = [c.strip() for c in str(coerced).split(",") if c.strip()]
            if ftype == "bool":
                env_updates[env_key] = "true" if coerced else "false"
            else:
                env_updates[env_key] = str(coerced)
            attr_updates[attr] = coerced

        if env_updates:
            env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.env"))
            update_env_config(env_updates, env_path=env_path)

            # Reload config in the current process and environment for subprocesses
            for attr, value in attr_updates.items():
                if hasattr(config, attr):
                    setattr(config, attr, value)
            for env_key, env_value in env_updates.items():
                os.environ[env_key] = env_value

        return {"status": "success", "message": "Configuration updated. Restart may be required for some changes."}

    except Exception as e:
        logger.error(f"Error updating config: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update config: {str(e)}"
        )


# provider -> (model attr, api-key attr or None for local, base-url attr).
# Used to overlay unsaved form values onto the saved config for live tests.
_PROVIDER_ATTRS: Dict[str, Tuple[str, Optional[str], Optional[str]]] = {
    "gemini":   ("GEMINI_TEXT_MODEL", "GEMINI_API_KEY", "GEMINI_BASE_URL"),
    "openai":   ("OPENAI_MODEL", "OPENAI_API_KEY", "OPENAI_BASE_URL"),
    "zhipu":    ("ZHIPU_MODEL", "ZHIPU_API_KEY", "ZHIPU_BASE_URL"),
    "qwen":     ("QWEN_MODEL", "QWEN_API_KEY", "QWEN_BASE_URL"),
    "kimi":     ("KIMI_MODEL", "KIMI_API_KEY", "KIMI_BASE_URL"),
    "deepseek": ("DEEPSEEK_MODEL", "DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL"),
    "ollama":   ("OLLAMA_MODEL", None, "OLLAMA_BASE_URL"),
    "lmstudio": ("LMSTUDIO_MODEL", None, "LMSTUDIO_BASE_URL"),
}


class TestLLMRequest(BaseModel):
    provider: str
    model: Optional[str] = None      # blank = use saved value
    api_key: Optional[str] = None    # blank = use saved key
    base_url: Optional[str] = None   # blank = saved/default endpoint


@router.post("/test-llm")
async def test_llm(request: TestLLMRequest):
    """Send a tiny prompt through a provider to verify its configuration.

    Uses the saved .env values overlaid with any unsaved form values, so the
    user can test a key/endpoint before saving it.
    """
    try:
        import types as _types
        import config
        from core.llm_engine import get_provider

        attrs = _PROVIDER_ATTRS.get(request.provider)
        if attrs is None:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {request.provider}")

        # Config shim: every saved constant plus the unsaved form overrides
        shim = _types.SimpleNamespace()
        for attr in dir(config):
            if attr.isupper():
                setattr(shim, attr, getattr(config, attr))

        model_attr, key_attr, base_attr = attrs
        if request.model:
            setattr(shim, model_attr, request.model)
        if key_attr and request.api_key:
            setattr(shim, key_attr, request.api_key)
        if base_attr and request.base_url:
            setattr(shim, base_attr, request.base_url)

        provider = get_provider(request.provider, config_module=shim)
        provider.timeout = min(provider.timeout, 60)

        def _ask():
            return provider.ask("Reply with exactly one word: PONG")

        start = time.time()
        try:
            reply = await asyncio.wait_for(asyncio.to_thread(_ask), timeout=90)
        except asyncio.TimeoutError:
            return {"status": "error", "error": "Timed out after 90 seconds", "elapsed_ms": 90000}
        elapsed_ms = int((time.time() - start) * 1000)
        reply_text = (reply or "").strip()

        if "pong" in reply_text.lower():
            return {
                "status": "success",
                "provider": request.provider,
                "model": provider.model,
                "reply": reply_text[:200],
                "elapsed_ms": elapsed_ms,
            }
        return {
            "status": "unexpected_reply",
            "provider": request.provider,
            "model": provider.model,
            "reply": reply_text[:200] or "(empty reply)",
            "elapsed_ms": elapsed_ms,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"LLM connection test failed: {e}")
        return {"status": "error", "error": str(e)}


@router.get("/directors/tree")
async def get_directors_tree():
    """Get full director file tree grouped by type and category, including base/component files"""
    try:
        loader = get_director_loader()
        return loader.list_director_tree()
    except Exception as e:
        logger.error(f"Error listing director tree: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list director tree: {str(e)}"
        )


@router.get("/directors/{director_type}/{director_id:path}")
async def get_director_content(director_type: str, director_id: str, raw: bool = False, view: Optional[str] = None):
    """Get content of an director prompt file.

    raw=true returns the file content as-is (keeps {{include:...}} directives),
    along with the list of included files. Default returns the include-expanded
    prompt used at generation time.
    view=preview returns the raw content split into text/include segments,
    with every include resolved and nested, plus the fully expanded prompt —
    used by the Web UI preview mode to render each included file as its own
    collapsible section.
    """
    try:
        loader = get_director_loader()
        if view == "preview":
            return loader.load_prompt_segments(director_type, director_id)
        if raw:
            content = loader.load_prompt_raw(director_type, director_id)
            includes = re.findall(r'\{\{include:(.+?)\}\}', content)
            return {"content": content, "raw": True, "includes": [i.strip() for i in includes]}
        content = loader.load_prompt(director_type, director_id)
        return {"content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Director not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error loading director content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/directors/{director_type}/{director_id:path}")
async def update_director_content(director_type: str, director_id: str, request: UpdateDirectorRequest):
    """Update content of an director prompt file"""
    try:
        loader = get_director_loader()
        loader.save_prompt(director_type, director_id, request.content)
        return {"status": "success", "message": f"Director {director_id} updated"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating director content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows")
async def get_workflows():
    """Get list of available workflows by category"""
    try:
        loader = get_workflow_loader()
        all_workflows = loader.get_all_workflows()
        
        # Group by category
        workflows_by_category = {}
        for workflow in all_workflows:
            category = workflow.get("category", "unknown")
            if category not in workflows_by_category:
                workflows_by_category[category] = []
            workflows_by_category[category].append(workflow)
            
        return workflows_by_category
    except Exception as e:
        logger.error(f"Error listing workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/{category}/{filename}")
async def get_workflow_content(category: str, filename: str):
    """Get content of a workflow JSON file"""
    try:
        loader = get_workflow_loader()
        content = loader.load_workflow(category, filename)
        return {"content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Workflow not found")
    except Exception as e:
        logger.error(f"Error loading workflow content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflows/{category}/{filename}")
async def update_workflow_content(category: str, filename: str, request: UpdateWorkflowRequest):
    """Update content of a workflow JSON file"""
    try:
        loader = get_workflow_loader()
        loader.save_workflow(category, filename, request.content)
        return {"status": "success", "message": f"Workflow {filename} updated"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating workflow content: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@router.post("/launch-browser")
async def launch_browser():
    """Launch a Playwright browser with persistent context and stealth"""
    try:
        def run_playwright():
            try:
                # Use a separate thread to run Playwright since it's interactive
                from playwright.sync_api import sync_playwright
                from playwright_stealth import stealth
                import config
                
                with sync_playwright() as p:
                    # Apply global hook if using version 2.0.x
                    try:
                        from playwright_stealth import Stealth
                        Stealth().hook_playwright_context(p)
                    except (ImportError, AttributeError):
                        pass
                        
                    # Determine profile path dynamically to avoid cached GEMINIWEB_CHROME_PROFILE
                    browser_type_name = getattr(config, 'PLAYWRIGHT_BROWSER', 'chromium').lower()
                    profile_name = "chrome_profile"
                    if browser_type_name == "firefox":
                        profile_name = "firefox_profile"
                    elif browser_type_name == "webkit":
                        profile_name = "webkit_profile"
                    else:
                        channel = getattr(config, 'PLAYWRIGHT_CHANNEL', 'chrome')
                        if "msedge" in channel:
                            profile_name = "edge_profile"
                            
                    output_dir = getattr(config, 'OUTPUT_DIR', 'output')
                    profile_path = os.path.abspath(os.path.join(output_dir, profile_name))
                    os.makedirs(profile_path, exist_ok=True)
                        
                    logger.info(f"Launching browser with profile: {profile_path}")
                    
                    # Launch persistent context with same settings as image generation
                    browser_type = getattr(p, browser_type_name, p.chromium)
                    
                    # Channel and args depend on browser type
                    channel = None
                    launch_args = []
                    
                    if browser_type_name == "chromium":
                        channel = getattr(config, 'PLAYWRIGHT_CHANNEL', 'chrome')
                        # Map to avoid "channel 'xxx' is not supported"
                        valid_chromium_channels = ["chrome", "chrome-beta", "chrome-dev", "chrome-canary", "msedge", "msedge-beta", "msedge-dev", "msedge-canary"]
                        if channel not in valid_chromium_channels:
                            channel = None
                            
                        launch_args = [
                            "--start-maximized", 
                            "--disable-blink-features=AutomationControlled",
                            "--no-first-run",
                            "--no-default-browser-check",
                        ]
                        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                    elif browser_type_name == "firefox":
                        launch_args = ["-start-maximized"]
                        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0"
                    else:
                        user_agent = None # Let Playwright decide

                    browser_context = browser_type.launch_persistent_context(
                        user_data_dir=profile_path,
                        headless=False,
                        channel=channel,
                        args=launch_args,
                        viewport={'width': 1280, 'height': 900},
                        user_agent=user_agent,
                        locale='en-US',
                        timezone_id='America/New_York',
                        ignore_default_args=['--enable-automation'],
                        no_viewport=False
                    )
                    
                    # Apply stealth to context
                    try:
                        from playwright_stealth import stealth_sync
                        stealth_sync(browser_context)
                    except Exception as e:
                        logger.warning(f"Failed to apply stealth: {e}")
                    
                    page = browser_context.new_page()
                    page.goto("https://accounts.google.com/signin/v2/identifier?service=lso&passive=1209600&continue=https%3A%2F%2Fgemini.google.com%2Fapp&followup=https%3A%2F%2Fgemini.google.com%2Fapp&ec=asw-gemini-v1")
                    
                    # Keep the browser open until the user closes it manually
                    # This is tricky in a backend process, but launch_persistent_context 
                    # will wait if we don't close it immediately. 
                    # However, to avoid blocking the whole thread forever, 
                    # we just let it run. In sync mode, it might block the thread.
                    
                    # We can use a simple loop or just page.pause() if we want it to stay
                    # but since it's a separate thread, blocking is fine.
                    # A better way is to wait for the page to be closed.
                    page.wait_for_event("close", timeout=0)
                    browser_context.close()
            except Exception as e:
                logger.error(f"Error in playwright thread: {e}")

        # Start browser in a background thread to not block the API response
        thread = threading.Thread(target=run_playwright, daemon=True)
        thread.start()
        
        return {"status": "success", "message": "Browser launched. Please check your desktop."}
    except ImportError:
        raise HTTPException(status_code=500, detail="playwright or playwright-stealth not installed. Please run pip install.")
    except Exception as e:
        logger.error(f"Error launching browser: {e}")
        raise HTTPException(status_code=500, detail=str(e))
