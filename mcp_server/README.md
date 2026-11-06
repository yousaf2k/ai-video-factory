# AI Video Factory MCP Server

A Model Context Protocol server that exposes the whole AI Video Factory
pipeline to ANY MCP client — Claude Desktop, Claude Code, Cursor, ZCode, other
agents. It reuses the exact same tool registry as the in-app AI Agent
Assistant (56+ tools): projects, stories, scenes, characters, shots,
generation queue, workflows, directors, app config, asset library, project
file read/write/search, and skills.

Pure Python stdio JSON-RPC — no `mcp` package or extra dependencies needed.

## Run it

From the repository root (the backend's Python environment):

```bash
python mcp_server/server.py             # respects agent tool gates
python mcp_server/server.py --all-tools # trusted local use: everything exposed
```

## Claude Desktop

`claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ai-video-factory": {
      "command": "python",
      "args": ["C:/AI/ai_video_factory_v1/mcp_server/server.py"]
    }
  }
}
```

## Cursor / ZCode / other MCP clients

```json
{
  "mcpServers": {
    "ai-video-factory": {
      "command": "python",
      "args": ["C:/AI/ai_video_factory_v1/mcp_server/server.py"],
      "cwd": "C:/AI/ai_video_factory_v1"
    }
  }
}
```

## Inside the in-app agent

The agent itself supports external MCP servers (Agent → Settings → MCP). To let
the in-app agent call this project's own MCP server (rarely needed — it already
has the tools natively — but useful for testing):

- Transport: `stdio`
- Command: `python`
- Args: `["mcp_server/server.py"]`

## Example tool calls from an MCP client

```
tools/call  get_project_overview   {"project_id": "project_20260101_120000"}
tools/call  update_shot            {"project_id": "...", "shot": "4",
                                    "fields": {"video_prompt": "..."}}
tools/call  generate_shot_video    {"project_id": "...", "shot": "4", "force": true}
tools/call  search_files           {"pattern": "arrival", "root": "project",
                                    "project_id": "...", "file_glob": "*.json"}
```

## Notes

- The server must run with the repository's Python environment (same one the
  web backend uses) so `config.py`/`core/*` resolve.
- Tool availability: without `--all-tools`, the agent settings gates apply
  (dangerous tools like `delete_project` stay hidden unless enabled in
  `output/agent/config.json` or `AGENT_ALLOW_DANGEROUS_TOOLS=true`).
- Only stdout is used for protocol frames; library log output is rerouted to
  stderr automatically.
