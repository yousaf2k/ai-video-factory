"""
Model registry — loads models.json (PI models.json format) as the canonical
source of LLM provider/model configuration.

The file (project root, next to config.py) defines per provider: baseUrl, api
kind, apiKey as an environment-variable reference ("${GEMINI_API_KEY}"), and
the available models with their reasoning metadata (compat.thinkingFormat,
thinkingLevelMap, contextWindow, maxTokens).

API keys are NEVER stored here — the file holds the env var NAME and the value
is read from the environment (.env) at provider construction time.

Missing or invalid models.json degrades gracefully to an empty registry:
callers fall back to their hardcoded defaults.
"""
import json
import os
import threading
from typing import Any, Dict, List, Optional

from core.logger_config import get_logger

logger = get_logger(__name__)

MODELS_CONFIG_FILENAME = "models.json"

_lock = threading.Lock()
_cache: Dict[str, Any] = {}
_cache_sig = None
_warned = False


def _models_config_path() -> str:
    import config
    return os.path.join(getattr(config, 'PROJECT_ROOT', os.getcwd()), MODELS_CONFIG_FILENAME)


def load_models_config(force: bool = False) -> Dict[str, Any]:
    """Load and cache models.json. Returns {"providers": {...}} (empty on error).

    Re-reads when the file's mtime+size changes; pass force=True to bypass
    the cache entirely.
    """
    global _cache, _cache_sig, _warned
    path = _models_config_path()
    try:
        stat = os.stat(path)
        sig = (stat.st_mtime_ns, stat.st_size)
    except OSError:
        sig = None

    with _lock:
        if not force and sig == _cache_sig and _cache_sig is not None:
            return _cache
        if sig is None:
            if not _warned:
                logger.warning(f"{MODELS_CONFIG_FILENAME} not found at {path} - "
                               "using built-in provider defaults")
                _warned = True
            _cache = {"providers": {}}
            _cache_sig = None
            return _cache
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            providers = data.get("providers") if isinstance(data, dict) else None
            if not isinstance(providers, dict):
                raise ValueError("'providers' object missing")
            _cache = {"providers": providers}
            _cache_sig = sig
            _warned = False
            logger.debug(f"Loaded model registry from {path} "
                         f"({len(providers)} providers)")
        except Exception as e:
            if not _warned:
                logger.warning(f"Failed to parse {path}: {e} - "
                               "using built-in provider defaults")
                _warned = True
            _cache = {"providers": {}}
            _cache_sig = None
        return _cache


def get_provider_entry(provider: str) -> Optional[Dict[str, Any]]:
    """Full provider entry from models.json, or None when not registered."""
    provider = (provider or "").lower()
    return load_models_config()["providers"].get(provider)


def get_model_ids(provider: str) -> List[str]:
    """Model ids available for a provider per models.json ([] when unknown)."""
    entry = get_provider_entry(provider)
    if not entry:
        return []
    models = entry.get("models") or []
    return [m.get("id") for m in models if isinstance(m, dict) and m.get("id")]


def get_model_entry(provider: str, model_id: str) -> Optional[Dict[str, Any]]:
    """A single model entry, or None when the provider/model is not registered."""
    entry = get_provider_entry(provider)
    if not entry:
        return None
    for m in entry.get("models") or []:
        if isinstance(m, dict) and m.get("id") == model_id:
            return m
    return None


def get_model_reasoning(provider: str, model_id: Optional[str]) -> Optional[bool]:
    """The model's "reasoning" flag from models.json (PI default: false).

    True = the model supports thinking. None = the provider/model is not
    registered (no information — callers fall back to passthrough).
    """
    model = get_model_entry(provider, model_id or "")
    if not model:
        return None
    return bool(model.get("reasoning", False))


def resolve_api_key_ref(ref: Any) -> tuple:
    """Resolve an apiKey reference from models.json.

    Returns (env_var_name_or_None, ok_literal). Never returns or logs the
    actual key value — the caller reads it from the environment.

    Accepted shapes:
      "${NAME}" / "$NAME" -> ("NAME", True)   read NAME from the environment
      "none" (case-insensitive) -> (None, True)  dummy key, local providers
      any other literal -> (None, True)       used verbatim by the caller
    """
    if ref is None:
        return None, True
    ref = str(ref).strip()
    if not ref:
        return None, True
    if ref.lower() == "none":
        return None, True
    if ref.startswith("${") and ref.endswith("}"):
        return ref[2:-1], True
    if ref.startswith("$") and len(ref) > 1 and not ref.startswith("$$"):
        return ref[1:], True
    return None, True  # literal value; caller uses it as-is


def get_api_key(provider: str) -> str:
    """Resolve a provider's API key value from models.json + the environment.

    Literal "none" -> "" (local providers). Env references resolve via
    os.environ (the .env file is loaded into the environment by config.py).
    """
    entry = get_provider_entry(provider)
    if not entry:
        return ""
    ref = entry.get("apiKey")
    env_name, is_literal = resolve_api_key_ref(ref)
    if env_name:
        return os.environ.get(env_name, "") or ""
    if is_literal and ref and str(ref).strip().lower() != "none":
        return str(ref).strip()
    return ""


def map_thinking_level(provider: str, model_id: Optional[str], level: Optional[str]) -> Optional[str]:
    """Map a configured thinking level through the model's thinkingLevelMap.

    Returns the provider value to send, or None when the level is marked
    unsupported (null in the map) — the caller then sends nothing.
    Levels absent from the map (custom values) pass through unchanged, as do
    models/providers without a map entry.
    """
    if not level:
        return None
    model = get_model_entry(provider, model_id or "")
    if not model:
        return level
    # "reasoning": false declares the model cannot think at all — no level
    # is sent regardless of any (stale) thinkingLevelMap.
    if not model.get("reasoning", False):
        return None
    level_map = model.get("thinkingLevelMap")
    if not isinstance(level_map, dict):
        return level
    mapped = level_map.get(level)
    if mapped is None:
        # null marks the level unsupported for this model; a genuinely missing
        # key (custom value) passes through — distinguish via the raw map
        return level if level not in level_map else None
    return str(mapped)


def get_thinking_format(provider: str, model_id: Optional[str]) -> Optional[str]:
    """The model's compat.thinkingFormat from models.json (None when unset).

    The engine falls back to the provider class's default wire format when
    this returns None — per-model declarations override the class default
    (e.g. a qwen model loaded in Strata declares "qwen").
    """
    model = get_model_entry(provider, model_id or "")
    if not model:
        return None
    compat = model.get("compat")
    if isinstance(compat, dict):
        fmt = compat.get("thinkingFormat")
        if fmt:
            return str(fmt).strip().lower()
    return None


def supported_thinking_levels(provider: str, model_id: Optional[str],
                              levels: Optional[List[str]] = None) -> List[str]:
    """Standard thinking levels the model actually supports (dropdown filter).

    A level is unsupported — and excluded — when the model's thinkingLevelMap
    maps it to null. Models/providers without a map entry support every
    standard level (levels pass through unchanged).
    """
    if levels is None:
        import config
        levels = getattr(config, 'THINKING_LEVELS',
                         ["off", "minimal", "low", "medium", "high", "xhigh"])
    model = get_model_entry(provider, model_id or "")
    if not model:
        return list(levels)
    # "reasoning": false -> the model cannot think; offer no levels at all
    if not model.get("reasoning", False):
        return []
    level_map = model.get("thinkingLevelMap")
    if not isinstance(level_map, dict):
        return list(levels)
    # null marks unsupported; a missing key passes through (still shown)
    return [lvl for lvl in levels if level_map.get(lvl) is not None]


def get_thinking_level_maps() -> Dict[str, Dict[str, Dict[str, Any]]]:
    """{provider: {model_id: thinkingLevelMap}} for every registered model.

    Served to the UI so the thinking dropdown can filter levels live as the
    selected model changes.
    """
    result: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for provider, entry in load_models_config().get("providers", {}).items():
        maps: Dict[str, Dict[str, Any]] = {}
        for m in entry.get("models") or []:
            if isinstance(m, dict) and m.get("id") and isinstance(m.get("thinkingLevelMap"), dict):
                maps[m["id"]] = m["thinkingLevelMap"]
        if maps:
            result[provider] = maps
    return result
