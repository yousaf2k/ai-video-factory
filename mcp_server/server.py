#!/usr/bin/env python
"""
AI Video Factory — MCP server (Model Context Protocol, stdio transport).

Exposes the exact same tool registry as the in-app AI Agent Assistant to
external MCP clients (Claude Desktop, IDE agents, other assistants):

    projects, story, scenes, characters, shots, generation queue, workflows,
    directors, config, assets, project files (read/write/search), skills.

Pure Python — no `mcp` package required (JSON-RPC over stdin/stdout).

Run (from the repository root):
    python mcp_server/server.py

Claude Desktop config example (claude_desktop_config.json):
    {
      "mcpServers": {
        "ai-video-factory": {
          "command": "python",
          "args": ["C:/AI/ai_video_factory_v1/mcp_server/server.py"]
        }
      }
    }

Add it to the in-app agent (Agent → Settings → MCP Servers, stdio):
    command: python   args: ["mcp_server/server.py"]
"""
import argparse
import asyncio
import json
import os
import sys

# Make the repository root importable regardless of the working directory.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "ai-video-factory", "version": "1.0.0"}


def _load_registry(all_tools: bool):
    from web_ui.backend.services.agent.registry import TOOLS, Tool
    if all_tools:
        return dict(TOOLS)
    from web_ui.backend.services.agent.config_store import get_agent_config_store
    from web_ui.backend.services.agent.registry import get_effective_tools
    return get_effective_tools(get_agent_config_store().load())


def _tool_schema(tool) -> dict:
    return {
        "name": tool.name,
        "description": tool.description,
        "inputSchema": tool.parameters or {"type": "object", "properties": {}},
    }


class MCPServer:
    def __init__(self, all_tools: bool = False):
        self.all_tools = all_tools
        self.tools = {}
        # Protocol output MUST be the only thing on stdout; route library prints to stderr.
        self._stdout = sys.stdout
        sys.stdout = sys.stderr
        sys.stderr = sys.stderr
        self._loop = asyncio.new_event_loop()

    # ------------------------------------------------------------ protocol
    def send(self, payload: dict) -> None:
        self._stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self._stdout.flush()

    def reply(self, req_id, result: dict) -> None:
        self.send({"jsonrpc": "2.0", "id": req_id, "result": result})

    def reply_error(self, req_id, code: int, message: str) -> None:
        self.send({"jsonrpc": "2.0", "id": req_id,
                   "error": {"code": code, "message": message}})

    # ------------------------------------------------------------- methods
    def handle(self, message: dict) -> None:
        method = message.get("method", "")
        req_id = message.get("id")

        if method == "initialize":
            self.reply(req_id, {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            })
        elif method == "notifications/initialized":
            pass  # notification — no response
        elif method == "ping":
            self.reply(req_id, {})
        elif method == "tools/list":
            self.tools = _load_registry(self.all_tools)
            self.reply(req_id, {"tools": [_tool_schema(t) for t in self.tools.values()]})
        elif method == "tools/call":
            self._call_tool(req_id, message.get("params") or {})
        elif req_id is not None:
            self.reply_error(req_id, -32601, f"Method not found: {method}")

    def _call_tool(self, req_id, params: dict) -> None:
        name = params.get("name", "")
        arguments = params.get("arguments") or {}
        if name not in self.tools:
            self.tools = _load_registry(self.all_tools)
        tool = self.tools.get(name)
        if tool is None:
            self.reply_error(req_id, -32602,
                             f"Unknown tool '{name}'. Call tools/list for available tools.")
            return
        try:
            if asyncio.iscoroutinefunction(tool.handler):
                result = self._loop.run_until_complete(tool.handler(arguments))
            else:
                result = tool.handler(arguments)
            text = result if isinstance(result, str) else json.dumps(
                result, ensure_ascii=False, default=str)
            self.reply(req_id, {"content": [{"type": "text", "text": text}],
                                "isError": False})
        except Exception as exc:  # noqa: BLE001 — errors travel as tool results
            self.reply(req_id, {"content": [{"type": "text", "text": f"Error: {exc}"}],
                                "isError": True})

    # ------------------------------------------------------------ run loop
    def run(self) -> None:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(message, dict):
                try:
                    self.handle(message)
                except Exception as exc:  # noqa: BLE001 — never kill the server
                    self.send({"jsonrpc": "2.0", "error": {
                        "code": -32603, "message": f"Internal error: {exc}"}})


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Video Factory MCP server (stdio)")
    parser.add_argument("--all-tools", action="store_true",
                        help="Expose every tool including dangerous ones (trusted local use); "
                             "default respects the agent settings gates.")
    args = parser.parse_args()
    MCPServer(all_tools=args.all_tools).run()


if __name__ == "__main__":
    main()
