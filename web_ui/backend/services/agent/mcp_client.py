"""
MCP (Model Context Protocol) client support for the AI Agent Assistant.

Implements the MCP JSON-RPC protocol directly — no external `mcp` package
required:

- stdio transport: spawns the server command (npx / uvx / python ...) and
  speaks newline-delimited JSON-RPC over stdin/stdout.
- http transport: streamable HTTP (POST JSON-RPC; handles application/json
  and text/event-stream responses; keeps the Mcp-Session-Id header).

External MCP servers configured in the agent settings expose their tools to
the agent under the name mcp__<server>__<tool>.
"""
import asyncio
import json
import shlex
import threading
from typing import Any, Dict, List, Optional

PROTOCOL_VERSION = "2024-11-05"
REQUEST_TIMEOUT = 60.0
START_TIMEOUT = 30.0


class MCPError(Exception):
    pass


# --------------------------------------------------------------- stdio client
class StdioMCPClient:
    """One MCP server process, spoken to over stdin/stdout JSON lines."""

    def __init__(self, name: str, command: str, args: Optional[List[str]] = None,
                 env: Optional[Dict[str, str]] = None, cwd: Optional[str] = None):
        self.name = name
        self.command = command
        self.args = list(args or [])
        self.env = dict(env or {})
        self.cwd = cwd
        self._proc: Optional[asyncio.subprocess.Process] = None
        self._pending: Dict[int, asyncio.Future] = {}
        self._next_id = 0
        self._reader_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._started = False

    def signature(self) -> str:
        return json.dumps({"command": self.command, "args": self.args,
                           "env": self.env, "cwd": self.cwd}, sort_keys=True)

    async def start(self) -> None:
        async with self._lock:
            if self._started and self._proc and self._proc.returncode is None:
                return
            await self._stop_locked()
            cmd = self._build_command()
            import os
            env = {**os.environ, **self.env}
            self._proc = await asyncio.create_subprocess_exec(
                *cmd, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL, env=env, cwd=self.cwd,
            )
            self._reader_task = asyncio.create_task(self._read_loop())
            await self._request("initialize", {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "ai-video-factory-agent", "version": "1.0.0"},
            }, timeout=START_TIMEOUT)
            self._notify("notifications/initialized")
            self._started = True

    def _build_command(self) -> List[str]:
        if not self.args and (" " in self.command or shutil_wildcard(self.command)):
            parts = shlex.split(self.command, posix=True)
            if len(parts) > 1:
                return parts
        return [self.command, *self.args]

    async def _read_loop(self) -> None:
        proc = self._proc
        try:
            while proc is not None and proc.returncode is None:
                line = await proc.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    message = json.loads(line.decode("utf-8", errors="replace"))
                except json.JSONDecodeError:
                    continue
                self._dispatch(message)
        finally:
            # Process died: fail every pending request so callers see the error.
            for future in list(self._pending.values()):
                if not future.done():
                    future.set_exception(MCPError(f"MCP server '{self.name}' closed the connection"))
            self._pending.clear()

    def _dispatch(self, message: dict) -> None:
        msg_id = message.get("id")
        if msg_id is None:
            return  # notification from server — ignored
        future = self._pending.pop(msg_id, None)
        if future is None or future.done():
            return
        if "error" in message and message["error"] is not None:
            future.set_exception(MCPError(str(message["error"].get("message") or message["error"])))
        else:
            future.set_result(message.get("result", {}))

    async def _request(self, method: str, params: dict, timeout: float = REQUEST_TIMEOUT) -> dict:
        if not self._proc or self._proc.returncode is not None:
            raise MCPError(f"MCP server '{self.name}' is not running")
        self._next_id += 1
        req_id = self._next_id
        future: asyncio.Future = asyncio.get_running_loop().create_future()
        self._pending[req_id] = future
        payload = json.dumps({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params})
        try:
            self._proc.stdin.write((payload + "\n").encode("utf-8"))
            await self._proc.stdin.drain()
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._pending.pop(req_id, None)
            raise MCPError(f"MCP request '{method}' to server '{self.name}' timed out")
        except (ConnectionResetError, BrokenPipeError) as exc:
            self._pending.pop(req_id, None)
            raise MCPError(f"MCP server '{self.name}' connection lost: {exc}")

    def _notify(self, method: str, params: Optional[dict] = None) -> None:
        if not self._proc or self._proc.stdin is None:
            return
        payload = {"jsonrpc": "2.0", "method": method}
        if params:
            payload["params"] = params
        try:
            self._proc.stdin.write((json.dumps(payload) + "\n").encode("utf-8"))
        except (ConnectionResetError, BrokenPipeError):
            pass

    async def list_tools(self) -> List[dict]:
        result = await self._request("tools/list", {})
        tools = []
        for tool in result.get("tools", []) or []:
            tools.append({
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "inputSchema": tool.get("inputSchema") or {"type": "object", "properties": {}},
            })
        return tools

    async def call_tool(self, tool: str, arguments: Dict[str, Any]) -> dict:
        result = await self._request("tools/call", {"name": tool, "arguments": arguments or {}})
        content = result.get("content", [])
        text_parts = [
            block.get("text", "") for block in content if isinstance(block, dict) and "text" in block
        ]
        return {
            "content": "\n".join(text_parts) or json.dumps(content)[:4000],
            "isError": bool(result.get("isError", False)),
        }

    async def stop(self) -> None:
        async with self._lock:
            await self._stop_locked()

    async def _stop_locked(self) -> None:
        self._started = False
        if self._reader_task:
            self._reader_task.cancel()
            self._reader_task = None
        if self._proc and self._proc.returncode is None:
            try:
                self._proc.kill()
            except ProcessLookupError:
                pass
        self._proc = None


def shutil_wildcard(command: str) -> bool:
    """True when the command string looks like it embeds arguments."""
    return bool(command and any(ch.isspace() for ch in command))


# ---------------------------------------------------------------- http client
class HttpMCPClient:
    """Streamable-HTTP MCP client using requests (run in a worker thread)."""

    def __init__(self, name: str, url: str, headers: Optional[Dict[str, str]] = None):
        self.name = name
        self.url = url
        self.headers = dict(headers or {})
        self.session_id: Optional[str] = None
        self._next_id = 0

    def signature(self) -> str:
        return json.dumps({"url": self.url, "headers": self.headers}, sort_keys=True)

    async def start(self) -> None:
        await self._request("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "ai-video-factory-agent", "version": "1.0.0"},
        })
        self._notify("notifications/initialized")

    async def _request(self, method: str, params: dict) -> dict:
        self._next_id += 1
        req_id = self._next_id
        payload = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
        return await asyncio.to_thread(self._post, payload)

    def _post(self, payload: dict) -> dict:
        import requests
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            **self.headers,
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        response = requests.post(self.url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
        session = response.headers.get("Mcp-Session-Id")
        if session:
            self.session_id = session
        if response.status_code >= 400:
            raise MCPError(f"MCP http '{self.name}' returned {response.status_code}: {response.text[:300]}")
        content_type = response.headers.get("Content-Type", "")
        if "text/event-stream" in content_type:
            body = self._parse_sse(response.text)
        else:
            body = response.json()
        if "error" in body and body["error"] is not None:
            raise MCPError(str(body["error"].get("message") or body["error"]))
        return body.get("result", {})

    @staticmethod
    def _parse_sse(text: str) -> dict:
        for line in text.splitlines():
            if line.startswith("data:"):
                data = line[len("data:"):].strip()
                try:
                    return json.loads(data)
                except json.JSONDecodeError:
                    continue
        raise MCPError("MCP http SSE response contained no JSON data line")

    def _notify(self, method: str) -> None:
        import requests
        headers = {"Content-Type": "application/json", **self.headers}
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        try:
            requests.post(self.url, json={"jsonrpc": "2.0", "method": method},
                          headers=headers, timeout=10)
        except requests.RequestException:
            pass

    async def list_tools(self) -> List[dict]:
        result = await self._request("tools/list", {})
        return [
            {
                "name": t.get("name", ""),
                "description": t.get("description", ""),
                "inputSchema": t.get("inputSchema") or {"type": "object", "properties": {}},
            }
            for t in result.get("tools", []) or []
        ]

    async def call_tool(self, tool: str, arguments: Dict[str, Any]) -> dict:
        result = await self._request("tools/call", {"name": tool, "arguments": arguments or {}})
        content = result.get("content", [])
        text_parts = [b.get("text", "") for b in content if isinstance(b, dict) and "text" in b]
        return {"content": "\n".join(text_parts) or json.dumps(content)[:4000],
                "isError": bool(result.get("isError", False))}

    async def stop(self) -> None:
        return


# ------------------------------------------------------------------- manager
class MCPManager:
    """Keeps one client per configured MCP server; restarts on config change."""

    def __init__(self):
        self._clients: Dict[str, Any] = {}
        self._signatures: Dict[str, str] = {}
        self._tool_cache: Dict[str, List[dict]] = {}
        self._lock = threading.RLock()

    def invalidate(self, server_name: Optional[str] = None) -> None:
        """Drop cached clients/tools (called when agent config changes)."""
        with self._lock:
            names = [server_name] if server_name else list(self._clients.keys())
            for name in names:
                client = self._clients.pop(name, None)
                self._signatures.pop(name, None)
                self._tool_cache.pop(name, None)
                if client is not None:
                    try:
                        try:
                            loop = asyncio.get_running_loop()
                        except RuntimeError:
                            loop = None  # no loop in this thread; process dies with backend
                        if loop is not None and loop.is_running():
                            asyncio.ensure_future(client.stop())
                    except RuntimeError:
                        pass  # no loop in this thread; process exits with backend

    def _build_client(self, name: str, server_cfg: dict):
        transport = (server_cfg.get("transport") or "stdio").lower()
        if transport == "stdio":
            command = server_cfg.get("command") or ""
            if not command:
                raise MCPError(f"MCP server '{name}': stdio transport needs a command")
            return StdioMCPClient(name, command, server_cfg.get("args"),
                                  server_cfg.get("env"), server_cfg.get("cwd"))
        if transport in ("http", "https", "streamable-http", "sse"):
            url = server_cfg.get("url") or ""
            if not url:
                raise MCPError(f"MCP server '{name}': http transport needs a url")
            return HttpMCPClient(name, url, server_cfg.get("headers"))
        raise MCPError(f"MCP server '{name}': unknown transport '{transport}'")

    async def get_client(self, name: str, server_cfg: dict):
        client = self._clients.get(name)
        signature = self._build_client(name, server_cfg).signature()
        if client is not None and self._signatures.get(name) == signature:
            return client
        if client is not None:
            await client.stop()
        client = self._build_client(name, server_cfg)
        await client.start()
        with self._lock:
            self._clients[name] = client
            self._signatures[name] = signature
        return client

    async def list_tools(self, servers: Dict[str, dict]) -> Dict[str, List[dict]]:
        """Tools for every enabled server. Failed servers get an error entry
        under the special key '_errors' so the UI/agent can report why."""
        result: Dict[str, List[dict]] = {}
        errors: Dict[str, str] = {}
        for name, server_cfg in servers.items():
            try:
                client = await self.get_client(name, server_cfg)
                result[name] = await client.list_tools()
            except Exception as exc:  # noqa: BLE001 — report, don't crash the loop
                errors[name] = str(exc)
        if errors:
            result["_errors"] = errors  # type: ignore[assignment]
        return result

    async def call(self, server: str, tool: str, arguments: Dict[str, Any],
                   servers: Dict[str, dict]) -> dict:
        server_cfg = servers.get(server)
        if server_cfg is None:
            raise MCPError(f"MCP server '{server}' is not configured")
        client = await self.get_client(server, server_cfg)
        return await client.call_tool(tool, arguments)


_manager: Optional[MCPManager] = None


def get_mcp_manager() -> MCPManager:
    global _manager
    if _manager is None:
        _manager = MCPManager()
    return _manager
