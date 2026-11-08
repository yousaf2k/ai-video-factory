"""
Thinking wire formats (PI compat.thinkingFormat implementations).

build(format, level) translates a mapped thinking level into the request-body
field(s) a model's API expects. The level arriving here is either:
  - "off"            — hard disable (story generation / hard-off sentinel)
  - a mapped value   — already translated through the model's thinkingLevelMap
                       in models.json (e.g. "low", "none", "max", "true")
  - a custom value   — passes through the map unchanged

Formats (same ids as PI's openai-completions compat.thinkingFormat):
  openai             reasoning_effort                       (off -> "none" = no reasoning tokens)
  openrouter         reasoning.effort                       (off -> nothing)
  deepseek           thinking.type enabled/disabled
  together           reasoning.enabled
  baseten            chat_template_kwargs.thinking
  zai                thinking.type + thinking.effort        (GLM-5.x)
  qwen               top-level enable_thinking + reasoning_effort when the
                     mapped value is a real level (boolean map values keep
                     the request pure enable_thinking for DashScope)
  chat-template      chat_template_kwargs.thinking
  qwen-chat-template chat_template_kwargs.enable_thinking
  string-thinking    top-level thinking (bool or level string)
  ant-ling           reasoning.effort                       (off -> nothing)

Unknown formats / unmapped situations return {} — nothing is sent and the
model default applies.
"""
from typing import Any, Dict, Optional

# Levels that mean "no thinking" for bool-style formats
_FALSEY = ("off", "disabled", "false", "no", "none", "0")
_TRUTHY = ("true", "on", "yes", "1", "enabled")


def _as_bool(value: Any, default: bool = True) -> bool:
    """Bool-parse a mapped level ('true'/'false' strings from maps, custom
    values fall back to the default)."""
    v = str(value).strip().lower()
    if v in _FALSEY:
        return False
    if v in _TRUTHY:
        return True
    return default


def _as_bool_or_str(value: Any) -> Any:
    """For string-thinking: bool-parse true/false, pass other levels (e.g.
    'high'/'medium' for gpt-oss-style models) through as strings."""
    v = str(value).strip().lower()
    if v in _FALSEY:
        return False
    if v in _TRUTHY:
        return True
    return str(value)


def build(fmt: Optional[str], level: str) -> Dict[str, Any]:
    """Request-body field(s) for the given format and mapped level.

    Returns {} when nothing should be sent (unknown format or a format with
    no off-representation receiving a hard off).
    """
    if not fmt or not level:
        return {}
    fmt = str(fmt).strip().lower()
    off = level == "off"

    if fmt == "openai":
        # reasoning_effort="none" completely disables hidden reasoning tokens;
        # mapped values pass through verbatim.
        return {"reasoning_effort": "none" if off else level}

    if fmt == "openrouter":
        return {} if off else {"reasoning": {"effort": level}}

    if fmt == "deepseek":
        return {"thinking": {"type": "disabled" if off else "enabled"}}

    if fmt == "together":
        return {"reasoning": {"enabled": not off}}

    if fmt == "baseten":
        return {"chat_template_kwargs": {"thinking": not off}}

    if fmt == "zai":
        if off:
            return {"thinking": {"type": "disabled"}}
        return {"thinking": {"type": "enabled", "effort": level}}

    if fmt == "qwen":
        # enable_thinking is the on/off switch; when the mapped value is a
        # real effort level (low/medium/high/custom - not true/false), it is
        # also passed as reasoning_effort for OpenAI-compatible servers
        # (Strata/vLLM) that support effort levels on qwen models.
        v = str(level).strip().lower()
        fields: Dict[str, Any] = {"enable_thinking": v not in _FALSEY}
        if v not in _FALSEY and v not in _TRUTHY:
            fields["reasoning_effort"] = level
        return fields

    if fmt == "chat-template":
        return {"chat_template_kwargs": {"thinking": not off}}

    if fmt == "qwen-chat-template":
        return {"chat_template_kwargs": {"enable_thinking": not off}}

    if fmt == "string-thinking":
        return {"thinking": False if off else _as_bool_or_str(level)}

    if fmt == "ant-ling":
        return {} if off else {"reasoning": {"effort": level}}

    return {}
