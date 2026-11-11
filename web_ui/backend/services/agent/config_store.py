"""
Agent configuration store.

Persists agent runtime settings (tool enable/disable toggles, MCP servers,
provider overrides) to output/agent/config.json. The LLM provider/model can
also come from environment (AGENT_LLM_PROVIDER / AGENT_LLM_MODEL) — the JSON
config wins when set, so the Web UI settings page can override .env.
"""
import copy
import os
import threading
from typing import Any, Dict, List, Optional

import config
from core.json_atomic import atomic_write_json, read_json

_DEFAULT_CONFIG: Dict[str, Any] = {
    # "" = follow AGENT_LLM_PROVIDER / LLM_PROVIDER
    "provider": "",
    # "" = the provider's configured model
    "model": "",
    # Reasoning effort: "" = auto (don't send, model picks its default);
    # valid values per provider come from config.THINKING_OPTIONS (the same
    # options the Configuration page's thinking dropdown offers).
    "effort": "",
    "max_iterations": None,  # None = config.AGENT_MAX_ITERATIONS
    # Master gate for tools flagged dangerous=True (delete_project, ...)
    "dangerous_tools_allowed": None,  # None = config.AGENT_ALLOW_DANGEROUS_TOOLS
    # tool name -> bool. Missing key = the tool's default_enabled.
    "enabled_tools": {},
    # server name -> {transport, command, args, env, url, headers, enabled}
    "mcp_servers": {},
    # Appended verbatim to the agent system prompt (custom persona/rules).
    "extra_system_prompt": "",
    # Include a compact summary of the active project in the system prompt.
    "auto_include_project_context": True,
}

_MCP_SERVER_FIELDS = ("transport", "command", "args", "env", "url", "headers", "enabled")


class AgentConfigStore:
    """Thread-safe JSON-backed store for agent runtime configuration."""

    def __init__(self, path: Optional[str] = None):
        self.path = path or os.path.join(config.AGENT_DATA_DIR, "config.json")
        self._lock = threading.RLock()
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_mtime: Optional[float] = None

    # ------------------------------------------------------------------ load
    def _mtime(self) -> Optional[float]:
        try:
            return os.path.getmtime(self.path)
        except OSError:
            return None

    def load(self) -> Dict[str, Any]:
        with self._lock:
            mtime = self._mtime()
            if self._cache is None or mtime != self._cache_mtime:
                self._cache = self._read_disk()
                self._cache_mtime = mtime
            return copy.deepcopy(self._cache)

    def _read_disk(self) -> Dict[str, Any]:
        data = read_json(self.path, default=None)
        merged = copy.deepcopy(_DEFAULT_CONFIG)
        if isinstance(data, dict):
            for key in _DEFAULT_CONFIG:
                if key in data:
                    merged[key] = data[key]
        merged["enabled_tools"] = self._sanitize_tools(merged.get("enabled_tools"))
        merged["mcp_servers"] = self._sanitize_servers(merged.get("mcp_servers"))
        return merged

    @staticmethod
    def _sanitize_tools(value: Any) -> Dict[str, bool]:
        if not isinstance(value, dict):
            return {}
        return {str(k): bool(v) for k, v in value.items() if isinstance(k, str)}

    @staticmethod
    def _sanitize_servers(value: Any) -> Dict[str, Dict[str, Any]]:
        if not isinstance(value, dict):
            return {}
        servers: Dict[str, Dict[str, Any]] = {}
        for name, cfg in value.items():
            if not isinstance(name, str) or not name or not isinstance(cfg, dict):
                continue
            clean = {k: cfg.get(k) for k in _MCP_SERVER_FIELDS if k in cfg}
            clean["transport"] = clean.get("transport") or "stdio"
            clean["enabled"] = bool(clean.get("enabled", True))
            servers[name] = clean
        return servers

    # ------------------------------------------------------------------ save
    def save(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            current = self._cache = self._read_disk()
            for key in _DEFAULT_CONFIG:
                if key not in new_config:
                    continue
                value = new_config[key]
                if key == "enabled_tools":
                    current[key] = self._sanitize_tools(value)
                elif key == "mcp_servers":
                    current[key] = self._sanitize_servers(value)
                else:
                    current[key] = value
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            atomic_write_json(self.path, current, indent=2)
            self._cache_mtime = self._mtime()
            # MCP clients may need restarting when servers change.
            from web_ui.backend.services.agent.mcp_client import get_mcp_manager
            get_mcp_manager().invalidate()
            return copy.deepcopy(current)

    # ------------------------------------------------------------- resolvers
    def resolved(self) -> Dict[str, Any]:
        """Config with env defaults resolved into concrete values."""
        cfg = self.load()
        if not cfg.get("provider"):
            cfg["provider"] = config.AGENT_LLM_PROVIDER or config.LLM_PROVIDER
        if not cfg.get("model"):
            cfg["model"] = config.AGENT_LLM_MODEL or ""
        if cfg.get("max_iterations") is None:
            cfg["max_iterations"] = config.AGENT_MAX_ITERATIONS
        if cfg.get("dangerous_tools_allowed") is None:
            cfg["dangerous_tools_allowed"] = config.AGENT_ALLOW_DANGEROUS_TOOLS
        return cfg

    def is_tool_enabled(self, name: str, default_enabled: bool) -> bool:
        tools = self.load().get("enabled_tools") or {}
        if name in tools:
            return bool(tools[name])
        return default_enabled

    def enabled_mcp_servers(self) -> Dict[str, Dict[str, Any]]:
        return {n: s for n, s in (self.load().get("mcp_servers") or {}).items() if s.get("enabled", True)}


_store: Optional[AgentConfigStore] = None


def get_agent_config_store() -> AgentConfigStore:
    global _store
    if _store is None:
        _store = AgentConfigStore()
    return _store
