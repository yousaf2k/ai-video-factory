# AI Agent Assistant

An in-app AI agent that can see and operate the entire AI Video Factory pipeline.
Ask it anything about your projects in natural language and it executes real
actions through tools: creating projects, generating and fixing stories, scenes,
characters, shots, queueing image/video/SFX/narration generation, managing the
render queue, editing workflows and directors, and reading/writing/searching
project files.

> "Shot 4's video prompt has the character doing the wrong action — fix it and
> regenerate" → the agent reads shot 4, rewrites the prompt, saves it and queues
> the regeneration, then tells you exactly what changed.

## Where to find it

- **Left dock (every page)** — a robot handle on the left edge opens a slide-in
  chat panel. Open-state persists per browser.
- **Agent page** — `/agent` (also in the top nav): full-size chat plus the
  settings panel (LLM, Tools, MCP, Skills).
- The chat automatically attaches the **currently open project** (when you are
  on `/projects/{id}`) as context, so "shot 4" means that project's shot 4.

## How it works

```
Chat (WS) ──► AgentEngine ──► LLM (any provider, JSON tool-call protocol)
                 │  ▲
                 ▼  │ tool results
             Tool registry (56 built-in tools wrapping the backend services)
                 ├── Projects / Story / Scenes / Characters / Shots
                 ├── Generation queue (images, videos, SFX, narration, replan)
                 ├── Workflows / Directors / App config / Asset library
                 ├── Files (sandboxed read/write/edit/search)
                 ├── Skills (agent_skills/*/SKILL.md)
                 └── MCP servers (external tools, mcp__server__tool)
```

- **Provider-agnostic**: the agent works with every supported LLM (Gemini,
  OpenAI, Zhipu, DeepSeek, Qwen, Kimi, Ollama, LM Studio) — native
  function-calling is not required; tool calls travel as JSON in the prompt.
- **Streaming**: chat runs over WebSocket (`/api/agent/ws`); the UI shows each
  tool call and result live while the agent works. A blocking
  `POST /api/agent/chat` fallback exists.
- **Transparent**: every turn (including tool calls + results) is persisted to
  `output/agent/conversations/*.json` and rendered in the UI.
- **Bounded**: max tool iterations per message (default 12), tool results
  truncated (`AGENT_MAX_TOOL_RESULT_CHARS`).

## Configuration

### Agent LLM

Independent of the story LLM. In **Agent → Settings → General** (persisted to
`output/agent/config.json`) or via environment. The **Effort / thinking**
dropdown appears only where the selected provider+model supports it — Zhipu
GLM-5.x (Default/Low/High/Max) and OpenAI reasoning models (Minimal/Low/Medium/
High). *Auto* (the default) sends no parameter and the model picks its own
default; DeepSeek/Gemini/Qwen/Kimi/local models have no effort setting and the
control is hidden.

| Env var | Default | Meaning |
|---|---|---|
| `AGENT_LLM_PROVIDER` | *(follows `LLM_PROVIDER`)* | gemini, openai, zhipu, deepseek, qwen, kimi, ollama, lmstudio |
| `AGENT_LLM_MODEL` | *(provider default)* | Model override for the agent |
| `ZHIPU_REASONING_EFFORT` | *(auto)* | GLM-5.x thinking effort: default/low/high/max (sent as `thinking.effort`; empty = model auto) |
| `OPENAI_REASONING_EFFORT` | *(auto)* | OpenAI reasoning models (o-series/gpt-5*): minimal/low/medium/high |
| `AGENT_MAX_ITERATIONS` | `12` | Max tool round-trips per message |
| `AGENT_MAX_TOOL_RESULT_CHARS` | `32768` | Per-tool-result cap fed back to the agent |
| `AGENT_ALLOW_DANGEROUS_TOOLS` | `false` | Enables `delete_*` tools |
| `AGENT_FILE_SEARCH_USE_SHELL` | `true` | PowerShell/grep for file search |
| `AGENT_SKILLS_DIR` | `agent_skills` | Skills folder |
| `AGENT_DATA_DIR` | `output/agent` | Config + conversations storage |
| `AGENT_HISTORY_MAX_MESSAGES` | `40` | History window per prompt |

API keys/base URLs come from the regular Configuration page per provider.

### Tools (enable/disable)

56 built-in tools grouped by category — toggle any of them in
**Agent → Settings → Tools**. Dangerous tools (delete project/shot/scene/
character/file) are hidden behind a master switch in **General**.

<details>
<summary>Full tool catalog</summary>

| Category | Tools |
|---|---|
| projects | list_projects, create_project, update_project, delete_project†, duplicate_project |
| story | get_story, update_story, generate_story |
| scenes | update_scene, add_scene, delete_scene†, generate_scene_background, generate_scene_narration |
| characters | list_characters, add_character, update_character, delete_character†, generate_character_reference |
| shots | list_shots, get_shot, update_shot, add_shot, delete_shot†, update_shots_bulk, select_shot_media |
| generation | generate_shot_image, generate_shot_video, generate_shot_soundfx, batch_regenerate_shots, replan_shots, generate_project_thumbnail |
| queue | get_queue, queue_action (cancel/pause/resume/requeue/force_start), cancel_project_generation |
| workflows | list_workflows, read_workflow, write_workflow |
| directors | list_directors, read_director, write_director |
| config | get_app_config, update_app_config |
| assets | search_assets, read_asset_text, write_asset_text |
| files | list_files, read_file, write_file, edit_file, delete_file†, search_files |
| skills | list_skills, read_skill, read_skill_file |
| system | get_project_overview |

† dangerous — gated behind *Allow dangerous tools*.
</details>

### File sandbox

- **Read**: repository (docs, directors, workflows, …) + whole output folder.
  `.env` is never readable.
- **Write**: only inside the output folder (project dirs, assets, editor data).
  Repo areas (`docs/`, `directors/`, `workflow/`, …) are rejected with a pointer
  to the dedicated `write_director` / `write_workflow` tools. Path traversal
  (`..`) is rejected.
- **Search** (`search_files`): searches file contents with the platform's native
  tools — **PowerShell** `Get-ChildItem + Select-String` on Windows, **grep -r**
  on Linux/macOS — with an automatic pure-Python fallback. Roots: `project`,
  `projects`, `output`, `repo`, `docs`, `skills`.

### Skills

Skills are instruction playbooks in `agent_skills/<name>/SKILL.md` (YAML
frontmatter `name`/`description` + markdown body). The agent sees every
skill's name/description in its system prompt and calls `read_skill` before
following one. Create them in **Agent → Settings → Skills** or by hand — see
`agent_skills/README.md`. Shipped examples: `fix-shot-prompt`,
`new-project-wizard`, `project-health-check`.

### MCP support

**Add external MCP servers** (filesystem, browser, databases, anything MCP) in
**Agent → Settings → MCP**:

- `stdio` — a local command, e.g. command `npx`, args `-y @modelcontextprotocol/server-filesystem C:/data`
- `http` — streamable-HTTP MCP endpoint URL

Their tools appear to the agent as `mcp__<server>__<tool>`. No extra Python
dependencies — the MCP client (stdio + HTTP) is implemented in-repo.

**This project is itself an MCP server**: `mcp_server/server.py` exposes the
same 56-tool registry to Claude Desktop, Cursor, ZCode, etc. over stdio JSON-RPC
(see `mcp_server/README.md` for client configs).

## API

| Method | Path | Purpose |
|---|---|---|
| GET/PUT | `/api/agent/config` | Agent settings + tool catalog + skills + conversations |
| GET | `/api/agent/tools` | Tool catalog |
| POST | `/api/agent/test` | Test the agent LLM |
| GET | `/api/agent/mcp/{server}/tools` | Probe an MCP server |
| GET/POST | `/api/agent/skills` | List/create skills |
| GET/DELETE | `/api/agent/skills/{name}` | Read/delete a skill |
| GET/POST | `/api/agent/conversations` | List/create conversations |
| GET/PATCH/DELETE | `/api/agent/conversations/{id}` | Load/rename/delete |
| POST | `/api/agent/chat` | Blocking chat (WS fallback) |
| WS | `/api/agent/ws` | Streaming chat (chat/stop messages; llm_start/tool_start/tool_result/final/error events) |

## Security notes

- The agent runs with the backend's permissions — treat it like a logged-in
  user of the Web UI.
- `.env` (API keys) is never readable through file tools; `update_app_config`
  cannot write secret keys.
- Destructive tools are opt-in; the system prompt instructs the agent to
  confirm intent before using them.
- Consider a dedicated low-cost provider (e.g. a local Ollama/LM Studio model)
  for casual chat and a strong cloud model for complex editing.

## Suggested future enhancements

1. **Streaming token output** — pipe provider streaming into the WS for
   word-by-word answers (needs streaming support in `core/llm_engine.py`).
2. **Native function-calling** for OpenAI-compatible providers (`tools=`/
   `tool_choice`) — fewer JSON parse edge cases, parallel tool calls.
3. **Vision input** — let the agent *look* at a shot's image/video when the
   user says "this looks wrong" (multimodal providers already support it).
4. **Approval mode** — require a UI click before each destructive/d costly
   tool executes (queue regeneration spend guard).
5. **Agent prompt library** — per-director system-prompt fragments (e.g. a
   Singularity-mode prompt-writing coach) injected automatically per project.
6. **Scheduled tasks** — "every night at 2am regenerate failed renders"
   (cron-style jobs driving the agent).
7. **Multi-agent review** — a second model critiques shot prompts before
   generation (cheap quality gate).
8. **Undo log** — record every agent mutation (old→new) so the UI can offer
   one-click revert of an agent edit session.
9. **Voice chat** — reuse the narration TTS/ASR stack to talk to the agent.
10. **Skill marketplace folder** — git-submodule/zip import of shared skills.
