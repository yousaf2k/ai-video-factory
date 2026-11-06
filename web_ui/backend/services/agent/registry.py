"""
Agent tool registry — the Web UI backend exposed as LLM tools.

Every tool is a plain function `handler(args: dict)` (sync or async) plus a
JSON-schema parameter definition. The same registry powers:

- the in-app AI Agent Assistant (engine.py),
- the project MCP server (mcp_server/server.py),

so external MCP clients (Claude Desktop, IDEs, other agents) get the exact
same capabilities.
"""
import asyncio
import json
import os
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import config

# --------------------------------------------------------------------- types


@dataclass
class Tool:
    name: str
    description: str
    category: str
    parameters: Dict[str, Any]
    handler: Optional[Callable[[dict], Any]] = None
    dangerous: bool = False
    default_enabled: bool = True
    source: str = "builtin"   # "builtin" or "mcp"
    server: Optional[str] = None

    def to_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "dangerous": self.dangerous,
            "source": self.source,
            "server": self.server,
            "parameters": self.parameters,
        }


TOOLS: Dict[str, Tool] = {}


def tool(name: str, category: str, description: str,
         parameters: Optional[Dict[str, Any]] = None,
         dangerous: bool = False, default_enabled: bool = True):
    """Register a handler as an agent tool."""
    def decorator(fn: Callable[[dict], Any]) -> Callable[[dict], Any]:
        TOOLS[name] = Tool(
            name=name,
            description=description,
            category=category,
            parameters=parameters or {"type": "object", "properties": {}},
            handler=fn,
            dangerous=dangerous,
            default_enabled=default_enabled,
        )
        return fn
    return decorator


def _obj(properties: Dict[str, Any], required: Optional[List[str]] = None) -> Dict[str, Any]:
    schema = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def _s(description: str = "", enum: Optional[List[str]] = None,
       default: Any = None) -> Dict[str, Any]:
    t: Dict[str, Any] = {"type": "string", "description": description}
    if enum:
        t["enum"] = enum
    if default is not None:
        t["default"] = default
    return t


def _i(description: str = "", default: Any = None) -> Dict[str, Any]:
    t = {"type": "integer", "description": description}
    if default is not None:
        t["default"] = default
    return t


def _b(description: str = "", default: Any = None) -> Dict[str, Any]:
    t = {"type": "boolean", "description": description}
    if default is not None:
        t["default"] = default
    return t


# ------------------------------------------------------------------- helpers


def _pm():
    from core.project_manager import ProjectManager
    return ProjectManager()


def _svc():
    from web_ui.backend.services.project_service import ProjectService
    return ProjectService()


def _gen():
    from web_ui.backend.services.generation_service import get_generation_service
    return get_generation_service()


def _qs():
    from web_ui.backend.services.queue_service import get_queue_service
    return get_queue_service()


def _require(args: dict, *names: str):
    missing = [n for n in names if args.get(n) in (None, "")]
    if missing:
        raise ValueError(f"Missing required argument(s): {', '.join(missing)}")
    return tuple(args[n] for n in names)


def _resolve_shot(shot_ref: Any, shots: List[dict]) -> Optional[dict]:
    """Resolve a shot by stable id first, then 1-based index."""
    if isinstance(shot_ref, int):
        idx = shot_ref
        if 1 <= idx <= len(shots):
            return shots[idx - 1]
        return None
    ref = str(shot_ref)
    for shot in shots:
        if str(shot.get("id")) == ref:
            return shot
    if ref.isdigit():
        idx = int(ref)
        if 1 <= idx <= len(shots):
            return shots[idx - 1]
    return None


def _summarize_shot(shot: dict) -> dict:
    """Lean shot index entry — deliberately NO prompt text (get_shot returns it)."""
    keep = ("id", "index", "scene_id", "scene_name", "character_name", "characters",
            "camera", "duration", "prompt_type",
            "image_generated", "video_rendered", "soundfx_generated")
    out = {k: shot.get(k) for k in keep if shot.get(k) is not None}
    takes = len(shot.get("video_paths") or [])
    if takes:
        out["takes"] = takes
    return out


def _generation_mode(project_id: str) -> str:
    """Project visual-input strategy: 'i2v' (default), 'r2v' or 't2v'."""
    try:
        meta = _pm().load_project(project_id) or {}
        return (meta.get("video_generation_type") or "i2v").lower()
    except Exception:  # noqa: BLE001 — treat unreadable meta as default
        return "i2v"


_R2V_IMAGE_TOOL_ERROR = (
    "This is a {mode} project — shots have NO first-frame images. Visuals come from "
    "references: character sheets (generate_character_reference), scene backgrounds "
    "(generate_scene_background) and prop sheets (generate_prop_reference); video is "
    "rendered from those references with generate_shot_video. To change what happens "
    "in the shot, update_shot its video_prompt/motion_prompt instead."
)


# ========================================================== PROJECTS category

@tool(
    "list_projects", "projects",
    "Compact project INDEX: id, truncated idea, type, completion and progress counts. "
    "Use get_project_overview / get_story for one project's details.",
    _obj({"include_stories": _b("Include the full story JSON per project (very large)"),
          "limit": _i("Max projects to return (default 50)")}),
)
def tool_list_projects(args: dict) -> Any:
    items = _svc().list_projects()
    include = bool(args.get("include_stories"))
    limit = int(args.get("limit") or 50)
    out = []
    for it in items[:limit]:
        entry = it.dict() if hasattr(it, "dict") else dict(it)
        if not include:
            entry.pop("story", None)
        idea = entry.get("idea") or ""
        entry["idea"] = idea if len(idea) <= 120 else idea[:120] + "…"
        entry.pop("thumbnail_url", None)
        entry.pop("timestamp", None)
        out.append(entry)
    return {"projects": out, "count": len(out), "total": len(items)}


_PROJECT_TYPE_ALIASES = {
    "1": 1, "2": 2, "3": 3, "4": 4,
    "documentary": 1, "doc": 1, "documentry": 1,
    "then_vs_now": 2, "thenvsnow": 2, "then-vs-now": 2, "then vs now": 2, "comparison": 2,
    "movie": 3, "film": 3, "cinematic": 3, "cinematic movie": 3, "movie/film": 3,
    "asmr": 4, "asmr glass cutting": 4, "glass cutting": 4,
}


def _resolve_project_type(value) -> int:
    """Accept friendly names ('movie'), ints (3) or ints-as-strings ('3')."""
    if value is None or value == "":
        return 1  # documentary default (CreateProjectRequest default)
    key = str(value).strip().lower()
    if key in _PROJECT_TYPE_ALIASES:
        return _PROJECT_TYPE_ALIASES[key]
    raise ValueError(
        f"Unknown project_type '{value}'. Use one of: 'documentary' (1), "
        "'then_vs_now' (2), 'movie' (3), 'asmr' (4).")


_PROJECT_TYPE_NAMES = {1: "documentary", 2: "then_vs_now", 3: "movie", 4: "asmr"}


@tool(
    "create_project", "projects",
    "Create a new project (optionally blank — just an idea and settings). "
    "Use generate_story afterwards to produce scenes/shots via LLM. project_type "
    "takes a NAME: 'documentary' | 'movie' | 'then_vs_now' | 'asmr'.",
    _obj({
        "idea": _s("The video idea/description (required)"),
        "project_type": _s("documentary, movie, then_vs_now or asmr (cinematic films = 'movie')",
                           enum=["documentary", "movie", "then_vs_now", "asmr"]),
        "story_director": _s("Story director name/path", default="default"),
        "shots_director": _s("Shots director name/path", default="default"),
        "prompt_mode": _s("'video' (timestamped H3) or 'motion'", enum=["video", "motion"]),
        "video_generation_type": _s("t2v, i2v or r2v", enum=["t2v", "i2v", "r2v"]),
        "r2v_mode": _s("r2v prompt mode", enum=["standard", "singularity"]),
        "total_duration": _i("Target video length in seconds"),
        "max_shot_duration": {"type": "number", "description": "Max seconds per shot (1-15)"},
        "aspect_ratio": _s("16:9, 9:16 or 21:8", default="16:9"),
    }, ["idea"]),
)
def tool_create_project(args: dict) -> Any:
    from web_ui.backend.models.project import CreateProjectRequest
    project_type = _resolve_project_type(args.get("project_type"))
    prompt_mode = args.get("prompt_mode")
    if prompt_mode is not None and prompt_mode not in ("video", "motion"):
        raise ValueError(f"prompt_mode must be 'video' or 'motion' (got {prompt_mode!r})")
    fields = {k: args[k] for k in (
        "idea", "story_director", "shots_director", "prompt_mode",
        "video_generation_type", "r2v_mode", "total_duration", "max_shot_duration",
        "aspect_ratio") if args.get(k) is not None}
    fields["project_type"] = project_type
    detail = _svc().create_project(CreateProjectRequest(**fields))
    data = detail.dict() if hasattr(detail, "dict") else detail
    return {"created": True,
            "project_type": _PROJECT_TYPE_NAMES.get(project_type, project_type),
            "project": {k: data.get(k) for k in (
                "project_id", "idea", "aspect_ratio", "story_director", "shots_director",
                "video_generation_type", "r2v_mode", "prompt_mode")}}


@tool(
    "update_project", "projects",
    "Update project settings: idea, directors, prompt mode, video generation type, r2v mode, aspect ratio.",
    _obj({
        "project_id": _s("Project ID"), "idea": _s(), "completed": _b(),
        "story_director": _s(), "shots_director": _s(),
        "prompt_mode": _s(enum=["video", "motion"]),
        "video_generation_type": _s(enum=["t2v", "i2v", "r2v"]),
        "r2v_mode": _s(enum=["standard", "singularity"]),
        "aspect_ratio": _s(enum=["16:9", "9:16", "21:8"]),
        "max_shot_duration": {"type": "number"},
    }, ["project_id"]),
)
def tool_update_project(args: dict) -> Any:
    from web_ui.backend.models.project import UpdateProjectRequest
    (project_id,) = _require(args, "project_id")
    fields = {k: args[k] for k in (
        "idea", "completed", "story_director", "shots_director", "prompt_mode",
        "video_generation_type", "r2v_mode", "aspect_ratio", "max_shot_duration")
        if args.get(k) is not None}
    _svc().update_project(project_id, UpdateProjectRequest(**fields))
    return {"updated": True, "project_id": project_id, "changed_fields": fields}


@tool(
    "delete_project", "projects",
    "DANGEROUS: permanently delete a project folder and all its data.",
    _obj({"project_id": _s("Project ID to delete")}, ["project_id"]),
    dangerous=True,
)
def tool_delete_project(args: dict) -> Any:
    (project_id,) = _require(args, "project_id")
    _svc().delete_project(project_id)
    return {"deleted": True, "project_id": project_id}


@tool(
    "duplicate_project", "projects",
    "Duplicate a project (copies story, shots and generated media).",
    _obj({"project_id": _s(), "new_project_id": _s("Optional custom ID for the copy")}, ["project_id"]),
)
def tool_duplicate_project(args: dict) -> Any:
    (project_id,) = _require(args, "project_id")
    detail = _svc().duplicate_project(project_id, args.get("new_project_id"))
    data = detail.dict() if hasattr(detail, "dict") else detail
    return {"duplicated": True, "new_project_id": data.get("project_id")}


# ============================================================== STORY category

@tool(
    "get_story", "story",
    "Get the project's story JSON (the detail source). Optionally fetch only some "
    "parts to save context: 'characters', 'scenes', 'props', 'youtube_metadata' — "
    "default returns everything.",
    _obj({
        "project_id": _s(),
        "parts": {"type": "array", "items": {"type": "string"},
                  "description": "Subset to return, e.g. ['characters']"},
    }, ["project_id"]),
)
def tool_get_story(args: dict) -> Any:
    (project_id,) = _require(args, "project_id")
    story = _pm().get_story(project_id)
    if not story:
        raise ValueError(f"Project '{project_id}' has no story yet — use generate_story first.")
    parts = args.get("parts")
    if parts:
        if not isinstance(parts, list) or not parts:
            raise ValueError("parts must be a non-empty array like ['characters','scenes']")
        unknown = [p for p in parts if p not in story]
        if unknown:
            raise ValueError(
                f"Unknown story part(s): {', '.join(map(str, unknown))}. "
                f"Available: {', '.join(story.keys())}")
        return {k: story[k] for k in parts}
    return story


@tool(
    "update_story", "story",
    "Replace the full story JSON (must contain a 'scenes' array). Scene ids are re-pinned "
    "to array positions automatically.",
    _obj({"project_id": _s(), "story": {"type": "object", "description": "Full story object"}},
         ["project_id", "story"]),
)
def tool_update_story(args: dict) -> Any:
    from core.story_engine import normalize_scene_ids
    (project_id, story) = _require(args, "project_id", "story")
    if not isinstance(story, dict) or not isinstance(story.get("scenes"), list):
        raise ValueError("story must be a dict containing a 'scenes' array")
    for scene in story["scenes"]:
        dur = scene.get("scene_duration")
        if dur is not None and (not isinstance(dur, int) or dur < 5):
            raise ValueError(f"Invalid scene_duration {dur} — must be an int >= 5")
    normalize_scene_ids(story)
    _pm().save_story(project_id, json.dumps(story, ensure_ascii=False, indent=2))
    return {"updated": True, "scenes": len(story["scenes"])}


@tool(
    "generate_story", "story",
    "Generate (or regenerate) the story + shots for a project via its story director. "
    "LLM call — takes 10-60s. This overwrites the existing story and shots.",
    _obj({
        "project_id": _s(),
        "director": _s("Story director override (default: the project's director)", default=""),
    }, ["project_id"]),
)
def tool_generate_story(args: dict) -> Any:
    (project_id,) = _require(args, "project_id")
    director = args.get("director") or ""

    def broadcast(message: dict) -> None:
        try:
            from web_ui.backend.websocket.manager import manager
            manager.broadcast_sync(project_id, {"project_id": project_id, **message})
        except Exception:  # noqa: BLE001 — progress events are best-effort
            pass

    broadcast({"type": "progress", "generation_type": "story", "progress": 10})
    try:
        pm = _pm()
        meta = pm.load_project(project_id)
        idea = meta["idea"]
        target_length = meta.get("total_duration") or getattr(config, "TARGET_VIDEO_LENGTH", None)
        aspect_ratio = meta.get("aspect_ratio", "16:9")

        from web_ui.backend.models.story import ProjectType
        is_then = (meta.get("project_type") == ProjectType.THEN_VS_NOW
                   or director.startswith("then_vs_now"))
        is_asmr = (meta.get("project_type") == ProjectType.ASMR_GLASS_CUTTING
                   or director == "asmr_glass_cutting" or director.startswith("asmr/"))

        if is_asmr:
            from core.story_engine import build_story_asmr_glass_cutting
            story_json = build_story_asmr_glass_cutting(
                idea=idea, director_name=director or "asmr/asmr_glass_cutting",
                shot_duration=meta.get("shot_duration", 5), aspect_ratio=aspect_ratio)
        elif is_then:
            from core.story_engine import build_story_then_vs_now
            story_json = build_story_then_vs_now(
                movie_name=idea, director_name=director or "then_vs_now",
                target_length=target_length, aspect_ratio=aspect_ratio)
        else:
            from core.story_engine import build_story
            story_json = build_story(idea, director or meta.get("story_director", "default"),
                                     target_length, aspect_ratio)
        story = json.loads(story_json)
        shots = story.pop("shots", [])
        pm.save_story(project_id, json.dumps(story, ensure_ascii=False, indent=2))
        if shots:
            pm.save_shots(project_id, shots)

        def mark(m):
            m["steps"]["story"] = True
            if shots:
                m["steps"]["scene_graph"] = True
                m["steps"]["shots"] = True
                m["stats"]["total_shots"] = len(shots)
        pm.update_meta_safely(project_id, mark)
    except Exception:
        broadcast({"type": "cancelled", "generation_type": "story"})
        raise
    # Let any open project page pick the new story up automatically.
    broadcast({"type": "story_updated"})
    broadcast({"type": "completed", "generation_type": "story"})
    return {"generated": True, "title": story.get("title"),
            "scenes": len(story.get("scenes", [])), "shots": len(shots)}


# ============================================================== SCENES tools

_SCENE_FIELDS = ("scene_name", "location", "characters", "action", "emotion",
                 "narration_text", "scene_duration", "visual_description",
                 "background_prompt")


@tool(
    "update_scene", "scenes",
    "Edit one scene of the story by its 0-based scene_id: location, characters, action, "
    "emotion, narration_text, scene_duration, etc.",
    _obj({
        "project_id": _s(), "scene_id": _i("0-based scene index"),
        "fields": {"type": "object", "description": "Scene fields to update, e.g. {\"action\": \"...\"}"},
    }, ["project_id", "scene_id", "fields"]),
)
def tool_update_scene(args: dict) -> Any:
    (project_id, scene_id, fields) = _require(args, "project_id", "scene_id", "fields")
    if not isinstance(fields, dict) or not fields:
        raise ValueError("fields must be a non-empty object")
    pm = _pm()
    story = pm.get_story(project_id)
    if not story:
        raise ValueError("Project has no story yet.")
    scenes = story.get("scenes", [])
    if not (0 <= int(scene_id) < len(scenes)):
        raise ValueError(f"scene_id {scene_id} out of range (0-{len(scenes) - 1})")
    scenes[int(scene_id)].update(fields)
    pm.save_story(project_id, json.dumps(story, ensure_ascii=False, indent=2))
    return {"updated": True, "scene_id": int(scene_id), "scene": scenes[int(scene_id)]}


@tool(
    "add_scene", "scenes",
    "Append (or insert) a new scene into the story. Requires at least location and action.",
    _obj({
        "project_id": _s(),
        "scene": {"type": "object", "description": "New scene object (location, characters, action, emotion, ...)"},
        "position": _i("Insert position (0-based); omit to append at the end"),
    }, ["project_id", "scene"]),
)
def tool_add_scene(args: dict) -> Any:
    (project_id, scene) = _require(args, "project_id", "scene")
    if not isinstance(scene, dict) or not scene.get("location") or not scene.get("action"):
        raise ValueError("scene must include at least 'location' and 'action'")
    scene.setdefault("characters", "")
    scene.setdefault("emotion", "")
    pm = _pm()
    story = pm.get_story(project_id)
    if not story:
        raise ValueError("Project has no story yet.")
    scenes = story.setdefault("scenes", [])
    pos = args.get("position")
    scenes.insert(int(pos), scene) if isinstance(pos, int) and 0 <= pos <= len(scenes) else scenes.append(scene)
    from core.story_engine import normalize_scene_ids
    normalize_scene_ids(story)
    pm.save_story(project_id, json.dumps(story, ensure_ascii=False, indent=2))
    return {"added": True, "scene_id": scenes.index(scene), "total_scenes": len(scenes)}


@tool(
    "delete_scene", "scenes",
    "DANGEROUS: remove a scene from the story. Shots referencing it are NOT removed — "
    "run replan_shots afterwards if needed.",
    _obj({"project_id": _s(), "scene_id": _i("0-based scene index")}, ["project_id", "scene_id"]),
    dangerous=True,
)
def tool_delete_scene(args: dict) -> Any:
    (project_id, scene_id) = _require(args, "project_id", "scene_id")
    pm = _pm()
    story = pm.get_story(project_id)
    if not story:
        raise ValueError("Project has no story yet.")
    scenes = story.get("scenes", [])
    if not (0 <= int(scene_id) < len(scenes)):
        raise ValueError(f"scene_id {scene_id} out of range")
    removed = scenes.pop(int(scene_id))
    from core.story_engine import normalize_scene_ids
    normalize_scene_ids(story)
    pm.save_story(project_id, json.dumps(story, ensure_ascii=False, indent=2))
    return {"deleted": True, "removed_scene": removed.get("location"), "remaining": len(scenes)}


@tool(
    "generate_scene_background", "scenes",
    "Queue background image generation for a scene (non-blocking; check the queue tool). "
    "In r2v projects scene backgrounds are reference inputs for every shot in the scene.",
    _obj({
        "project_id": _s(), "scene_id": _i("0-based scene index"),
        "prompt": _s("Prompt override (optional)"),
        "background_style": _s("Named style from styles.json"),
        "workflow": _s("ComfyUI workflow override"), "seed": _i(),
    }, ["project_id", "scene_id"]),
)
def tool_generate_scene_background(args: dict) -> Any:
    from web_ui.backend.models.story import BackgroundGenerationRequest
    (project_id, scene_id) = _require(args, "project_id", "scene_id")
    request = BackgroundGenerationRequest(
        **{k: args[k] for k in ("prompt", "background_style", "workflow", "seed") if args.get(k) is not None})
    items = _gen().add_background_to_queue(project_id, int(scene_id), request)
    return {"queued": True, "scene_id": int(scene_id),
            "queue_item_ids": [getattr(i, "item_id", None) for i in items]}


@tool(
    "generate_scene_narration", "scenes",
    "Start TTS narration generation for one scene (non-blocking background task).",
    _obj({
        "project_id": _s(), "scene_id": _i(),
        "tts_method": _s(), "tts_workflow": _s(), "voice": _s(),
    }, ["project_id", "scene_id"]),
)
async def tool_generate_scene_narration(args: dict) -> Any:
    (project_id, scene_id) = _require(args, "project_id", "scene_id")
    task = asyncio.create_task(_gen().regenerate_scene_narration(
        project_id, int(scene_id),
        tts_method=args.get("tts_method"), tts_workflow=args.get("tts_workflow"),
        voice=args.get("voice")))
    # Detach but surface immediate failures (bad scene id etc.) within 1s.
    await asyncio.sleep(0)
    try:
        await asyncio.wait_for(asyncio.shield(task), timeout=1.0)
    except asyncio.TimeoutError:
        pass
    return {"started": True, "project_id": project_id, "scene_id": int(scene_id)}


# ========================================================= CHARACTERS category

@tool(
    "list_characters", "characters",
    "List the story's characters with their prompts and reference image status.",
    _obj({"project_id": _s()}, ["project_id"]),
)
def tool_list_characters(args: dict) -> Any:
    (project_id,) = _require(args, "project_id")
    story = _pm().get_story(project_id)
    if not story:
        raise ValueError("Project has no story yet.")
    chars = story.get("characters", [])
    out = []
    for i, ch in enumerate(chars):
        out.append({
            "index": i,
            "name": ch.get("name"),
            "image_prompt": (ch.get("image_prompt") or "")[:200] or None,
            "has_reference": bool(ch.get("character_reference_image_path")
                                  or ch.get("then_reference_image_path")),
        })
    return {"characters": out, "count": len(out)}


@tool(
    "add_character", "characters",
    "Add a character to the story (name + image_prompt describing face/body consistently).",
    _obj({
        "project_id": _s(),
        "character": {"type": "object", "description": "Character object: name, image_prompt, personality, attire, voice_type, ..."},
    }, ["project_id", "character"]),
)
def tool_add_character(args: dict) -> Any:
    (project_id, character) = _require(args, "project_id", "character")
    if not isinstance(character, dict) or not character.get("name"):
        raise ValueError("character must include a 'name'")
    pm = _pm()
    story = pm.get_story(project_id)
    if not story:
        raise ValueError("Project has no story yet.")
    story.setdefault("characters", []).append(character)
    pm.save_story(project_id, json.dumps(story, ensure_ascii=False, indent=2))
    return {"added": True, "index": len(story["characters"]) - 1, "name": character["name"]}


@tool(
    "update_character", "characters",
    "Update fields of one character by index (image_prompt, name, personality, attire, ...).",
    _obj({
        "project_id": _s(), "character_index": _i("0-based character index"),
        "fields": {"type": "object", "description": "Fields to update"},
    }, ["project_id", "character_index", "fields"]),
)
def tool_update_character(args: dict) -> Any:
    (project_id, character_index, fields) = _require(args, "project_id", "character_index", "fields")
    if not isinstance(fields, dict) or not fields:
        raise ValueError("fields must be a non-empty object")
    pm = _pm()
    story = pm.get_story(project_id)
    if not story:
        raise ValueError("Project has no story yet.")
    chars = story.get("characters", [])
    if not (0 <= int(character_index) < len(chars)):
        raise ValueError(f"character_index {character_index} out of range (0-{len(chars) - 1})")
    chars[int(character_index)].update(fields)
    pm.save_story(project_id, json.dumps(story, ensure_ascii=False, indent=2))
    return {"updated": True, "character": chars[int(character_index)]}


@tool(
    "delete_character", "characters",
    "DANGEROUS: remove a character from the story.",
    _obj({"project_id": _s(), "character_index": _i()}, ["project_id", "character_index"]),
    dangerous=True,
)
def tool_delete_character(args: dict) -> Any:
    (project_id, character_index) = _require(args, "project_id", "character_index")
    pm = _pm()
    story = pm.get_story(project_id)
    if not story:
        raise ValueError("Project has no story yet.")
    chars = story.get("characters", [])
    if not (0 <= int(character_index) < len(chars)):
        raise ValueError(f"character_index {character_index} out of range")
    removed = chars.pop(int(character_index))
    pm.save_story(project_id, json.dumps(story, ensure_ascii=False, indent=2))
    return {"deleted": True, "name": removed.get("name"), "remaining": len(chars)}


@tool(
    "generate_character_reference", "characters",
    "Queue the 8-view character reference sheet generation for a character (non-blocking). "
    "In r2v projects this is THE way to change how a character looks — videos are rendered "
    "from these sheets, not from shot images.",
    _obj({
        "project_id": _s(), "character_index": _i(),
        "variant": _s("'character' (normal), 'then' or 'now' (ThenVsNow)", enum=["character", "then", "now"], default="character"),
        "prompt_override": _s(), "image_workflow": _s(), "seed": _i(),
    }, ["project_id", "character_index"]),
)
def tool_generate_character_reference(args: dict) -> Any:
    from web_ui.backend.api.stories import GenerateCharacterReferenceRequest
    (project_id, character_index) = _require(args, "project_id", "character_index")
    request = GenerateCharacterReferenceRequest(
        variant=args.get("variant") or "character",
        **{k: args[k] for k in ("prompt_override", "image_workflow", "seed") if args.get(k) is not None})
    _gen().queue_character_image(project_id, int(character_index), request)
    return {"queued": True, "character_index": int(character_index)}


@tool(
    "generate_prop_reference", "characters",
    "Queue the reference sheet for a story PROP (r2v projects — product-style image, "
    "stored on props[].reference_image_path). Non-blocking.",
    _obj({
        "project_id": _s(), "prop_index": _i("0-based index into story.props"),
        "prompt_override": _s(), "image_workflow": _s(), "seed": _i(),
    }, ["project_id", "prop_index"]),
)
def tool_generate_prop_reference(args: dict) -> Any:
    from web_ui.backend.api.stories import GenerateCharacterReferenceRequest
    from web_ui.backend.models.queue import QueueItem, QueueItemStatus, GenerationType
    from web_ui.backend.services.queue_service import get_queue_service
    (project_id, prop_index) = _require(args, "project_id", "prop_index")
    story = _pm().get_story(project_id) or {}
    props = story.get("props") or []
    if not (0 <= int(prop_index) < len(props)):
        raise ValueError(f"prop_index {prop_index} out of range (story has {len(props)} props)")
    request = GenerateCharacterReferenceRequest(
        variant="character",
        **{k: args[k] for k in ("prompt_override", "image_workflow", "seed") if args.get(k) is not None})
    gen = _gen()
    gen._ensure_queue_processor_started()
    item = QueueItem(
        item_id="", project_id=project_id, character_index=int(prop_index),
        generation_type=GenerationType.PROP_IMAGE,
        prompt_override=request.prompt_override,
        image_mode=request.image_mode, image_workflow=request.image_workflow,
        seed=request.seed, gemini_mode=request.gemini_mode,
        status=QueueItemStatus.PENDING, progress=0,
    )
    added = get_queue_service().add_items([item])
    gen._wake_up_processor()
    return {"queued": True, "prop_index": int(prop_index),
            "prop_name": props[int(prop_index)].get("name"),
            "queue_item_ids": [getattr(i, "item_id", None) for i in added]}


# ============================================================== SHOTS category

_SHOT_EDIT_FIELDS = ("image_prompt", "motion_prompt", "video_prompt", "prompt_type",
                     "camera", "narration", "duration", "scene_id", "scene_name",
                     "character_name", "soundfx_prompt", "gemini_mode",
                     "reference_asset_ids")


@tool(
    "list_shots", "shots",
    "Compact shot INDEX: id, index, scene, camera, duration, characters and generation "
    "status — NO prompt text. Use get_shot (by id or index) for a shot's full prompts.",
    _obj({"project_id": _s("Project ID")}, ["project_id"]),
)
def tool_list_shots(args: dict) -> Any:
    (project_id,) = _require(args, "project_id")
    shots = _pm().get_shots(project_id) or []
    return {"shots": [_summarize_shot(s) for s in shots], "count": len(shots)}


@tool(
    "get_shot", "shots",
    "Get one shot with FULL prompt text (image_prompt, motion_prompt, video_prompt, "
    "narration, soundfx_prompt, paths, references). Shot is resolved by stable id or 1-based index.",
    _obj({"project_id": _s(), "shot": _s("Shot id (8 hex chars) or 1-based index")}, ["project_id", "shot"]),
)
def tool_get_shot(args: dict) -> Any:
    (project_id, shot_ref) = _require(args, "project_id", "shot")
    shots = _pm().get_shots(project_id) or []
    shot = _resolve_shot(shot_ref, shots)
    if shot is None:
        raise ValueError(f"Shot '{shot_ref}' not found (project has {len(shots)} shots)")
    return shot


@tool(
    "update_shot", "shots",
    "Edit one shot's fields — the tool for prompt fixes (e.g. 'the character action is "
    "wrong in shot 4': get_shot, then update_shot with a corrected video_prompt/motion_prompt).",
    _obj({
        "project_id": _s(), "shot": _s("Shot id or 1-based index"),
        "fields": {"type": "object", "description": "Fields to update: image_prompt, motion_prompt, video_prompt, camera, narration, duration, soundfx_prompt, prompt_type ('motion'|'video'), scene_id, reference_asset_ids, ..."},
    }, ["project_id", "shot", "fields"]),
)
def tool_update_shot(args: dict) -> Any:
    (project_id, shot_ref, fields) = _require(args, "project_id", "shot", "fields")
    if not isinstance(fields, dict) or not fields:
        raise ValueError("fields must be a non-empty object")
    unknown = [k for k in fields if k not in _SHOT_EDIT_FIELDS]
    if unknown:
        raise ValueError(f"Unknown shot field(s): {', '.join(unknown)}. Allowed: {', '.join(_SHOT_EDIT_FIELDS)}")
    pm = _pm()
    updated = {}

    def modify(shots: List[dict]) -> List[dict]:
        shot = _resolve_shot(shot_ref, shots)
        if shot is None:
            raise ValueError(f"Shot '{shot_ref}' not found ({len(shots)} shots in project)")
        shot.update(fields)
        updated.update(shot)
        return shots

    pm.update_shots_safely(project_id, modify)
    return {"updated": True, "shot_id": updated.get("id"), "index": updated.get("index"),
            "changed_fields": fields, "shot": _summarize_shot(updated)}


@tool(
    "add_shot", "shots",
    "Manually add a shot after a position (default: end). Requires image_prompt, "
    "motion_prompt and camera.",
    _obj({
        "project_id": _s(),
        "image_prompt": _s(), "motion_prompt": _s(), "camera": _s("Camera movement"),
        "video_prompt": _s("Timestamped H3 video prompt (optional)"),
        "narration": _s(), "duration": {"type": "number"},
        "scene_id": _i("0-based scene this shot belongs to"),
        "position": _i("1-based position to insert AFTER; omit to append"),
    }, ["project_id", "image_prompt", "motion_prompt", "camera"]),
)
def tool_add_shot(args: dict) -> Any:
    (project_id, image_prompt, motion_prompt, camera) = _require(
        args, "project_id", "image_prompt", "motion_prompt", "camera")
    pm = _pm()
    new_shot = {
        "id": uuid.uuid4().hex[:8],
        "image_prompt": image_prompt,
        "motion_prompt": motion_prompt,
        "video_prompt": args.get("video_prompt"),
        "prompt_type": None,
        "camera": camera,
        "narration": args.get("narration", ""),
        "duration": args.get("duration"),
        "scene_id": args.get("scene_id"),
        "batch_number": 1,
        "image_generated": False, "video_rendered": False,
        "soundfx_generated": False,
    }
    created = {}

    def modify(shots: List[dict]) -> List[dict]:
        shots = shots or []
        position = args.get("position")
        if isinstance(position, int) and 1 <= position <= len(shots):
            shots.insert(position, new_shot)
        else:
            shots.append(new_shot)
        # Reindex 1..n
        for i, s in enumerate(shots, start=1):
            s["index"] = i
        created.update(new_shot)
        created["index"] = shots.index(new_shot) + 1
        return shots

    pm.update_shots_safely(project_id, modify)
    return {"added": True, "shot_id": created.get("id"), "index": created.get("index")}


@tool(
    "delete_shot", "shots",
    "DANGEROUS: remove a shot (media files stay on disk but are unlinked).",
    _obj({"project_id": _s(), "shot": _s("Shot id or 1-based index")}, ["project_id", "shot"]),
    dangerous=True,
)
def tool_delete_shot(args: dict) -> Any:
    (project_id, shot_ref) = _require(args, "project_id", "shot")
    pm = _pm()
    removed = {}

    def modify(shots: List[dict]) -> List[dict]:
        shot = _resolve_shot(shot_ref, shots or [])
        if shot is None:
            raise ValueError(f"Shot '{shot_ref}' not found")
        shots.remove(shot)
        removed.update(shot)
        for i, s in enumerate(shots, start=1):
            s["index"] = i
        return shots

    pm.update_shots_safely(project_id, modify)
    return {"deleted": True, "shot_id": removed.get("id")}


@tool(
    "update_shots_bulk", "shots",
    "Replace the whole shots array (for reordering or mass edits). Pass complete shot objects.",
    _obj({"project_id": _s(), "shots": {"type": "array", "description": "Full shots array"}},
         ["project_id", "shots"]),
)
def tool_update_shots_bulk(args: dict) -> Any:
    (project_id, shots) = _require(args, "project_id", "shots")
    if not isinstance(shots, list):
        raise ValueError("shots must be an array")
    pm = _pm()
    pm.update_shots_safely(project_id, lambda _current: shots)
    return {"updated": True, "count": len(shots)}


@tool(
    "select_shot_media", "shots",
    "Set the active image or video variation for a shot (path from image_paths/video_paths).",
    _obj({
        "project_id": _s(), "shot": _s(),
        "type": _s(enum=["image", "video"]),
        "path": _s("Path of the variation to activate"),
    }, ["project_id", "shot", "type", "path"]),
)
def tool_select_shot_media(args: dict) -> Any:
    (project_id, shot_ref, media_type, path) = _require(args, "project_id", "shot", "type", "path")
    pm = _pm()
    result = {}

    def modify(shots: List[dict]) -> List[dict]:
        shot = _resolve_shot(shot_ref, shots or [])
        if shot is None:
            raise ValueError(f"Shot '{shot_ref}' not found")
        key = "image_path" if media_type == "image" else "video_path"
        shot[key] = path
        result.update(shot)
        return shots

    pm.update_shots_safely(project_id, modify)
    return {"selected": True, "shot_id": result.get("id"), media_type: path}


# ========================================================= GENERATION category

@tool(
    "generate_shot_image", "generation",
    "Queue image generation for a shot (non-blocking — poll get_queue for progress). "
    "i2v projects ONLY — r2v/t2v projects render from references and have no shot images.",
    _obj({
        "project_id": _s("Project ID"), "shot": _s("Shot id or 1-based index"),
        "force": _b("Regenerate even if an image exists"),
        "image_workflow": _s("Workflow override"), "seed": _i(),
        "prompt_override": _s("One-off prompt override"),
    }, ["project_id", "shot"]),
)
def tool_generate_shot_image(args: dict) -> Any:
    from web_ui.backend.models.shot import RegenerateImageRequest
    from web_ui.backend.models.queue import GenerationType
    (project_id, shot_ref) = _require(args, "project_id", "shot")
    mode = _generation_mode(project_id)
    if mode in ("r2v", "t2v"):
        raise ValueError(_R2V_IMAGE_TOOL_ERROR.format(mode=mode))
    request = RegenerateImageRequest(
        **{k: args[k] for k in ("force", "image_workflow", "seed", "prompt_override")
           if args.get(k) is not None})
    items = _gen().add_single_shot_to_queue(project_id, shot_ref, GenerationType.IMAGE, request)
    if not items:
        raise ValueError(f"Shot '{shot_ref}' could not be resolved in project '{project_id}'")
    return {"queued": True, "shot": shot_ref,
            "queue_item_ids": [getattr(i, "item_id", None) for i in items]}


@tool(
    "generate_shot_video", "generation",
    "Queue video generation for a shot (non-blocking — poll get_queue for progress).",
    _obj({
        "project_id": _s(), "shot": _s(),
        "force": _b(), "video_workflow": _s(), "seed": _i(),
        "prompt_override": _s("One-off motion/video prompt override"),
        "prompt_type": _s("Which prompt to use", enum=["motion", "video"]),
        "resolution": _s("e.g. '480p', '720p'"),
        "generate_soundfx": _b("Also generate sound FX after the video"),
    }, ["project_id", "shot"]),
)
def tool_generate_shot_video(args: dict) -> Any:
    from web_ui.backend.models.shot import RegenerateVideoRequest
    from web_ui.backend.models.queue import GenerationType
    (project_id, shot_ref) = _require(args, "project_id", "shot")
    request = RegenerateVideoRequest(
        **{k: args[k] for k in ("force", "video_workflow", "seed", "prompt_override",
                                "prompt_type", "resolution", "generate_soundfx")
           if args.get(k) is not None})
    items = _gen().add_single_shot_to_queue(project_id, shot_ref, GenerationType.VIDEO, request)
    if not items:
        raise ValueError(f"Shot '{shot_ref}' could not be resolved in project '{project_id}'")
    return {"queued": True, "shot": shot_ref,
            "queue_item_ids": [getattr(i, "item_id", None) for i in items]}


@tool(
    "generate_shot_soundfx", "generation",
    "Queue sound FX generation for a shot's video (non-blocking).",
    _obj({
        "project_id": _s(), "shot": _s(),
        "force": _b(), "workflow": _s(), "prompt_override": _s(),
    }, ["project_id", "shot"]),
)
def tool_generate_shot_soundfx(args: dict) -> Any:
    from web_ui.backend.models.shot import RegenerateSoundFXRequest
    from web_ui.backend.models.queue import GenerationType
    (project_id, shot_ref) = _require(args, "project_id", "shot")
    request = RegenerateSoundFXRequest(
        **{k: args[k] for k in ("force", "workflow", "prompt_override") if args.get(k) is not None})
    items = _gen().add_single_shot_to_queue(project_id, shot_ref, GenerationType.SOUNDFX, request)
    if not items:
        raise ValueError(f"Shot '{shot_ref}' could not be resolved in project '{project_id}'")
    return {"queued": True, "shot": shot_ref,
            "queue_item_ids": [getattr(i, "item_id", None) for i in items]}


@tool(
    "batch_regenerate_shots", "generation",
    "Queue batch image/video regeneration for selected shots (or all shots).",
    _obj({
        "project_id": _s(),
        "shot_ids": {"type": "array", "items": {"type": "string"}, "description": "Shot ids to regenerate (omit = all)"},
        "regenerate_images": _b(), "regenerate_videos": _b(),
        "force_images": _b(), "force_videos": _b(),
        "image_workflow": _s(), "video_workflow": _s(),
    }, ["project_id"]),
)
async def tool_batch_regenerate(args: dict) -> Any:
    from web_ui.backend.models.shot import BatchRegenerateRequest
    (project_id,) = _require(args, "project_id")
    mode = _generation_mode(project_id)
    wants_images = args.get("regenerate_images", True)
    if mode in ("r2v", "t2v") and wants_images:
        raise ValueError(
            _R2V_IMAGE_TOOL_ERROR.format(mode=mode)
            + " For batch video regeneration pass regenerate_images=false."
        )
    if mode in ("r2v", "t2v"):
        args = {**args, "regenerate_images": False}
    request = BatchRegenerateRequest(
        **{k: args[k] for k in ("shot_ids", "regenerate_images", "regenerate_videos",
                                "force_images", "force_videos", "image_workflow",
                                "video_workflow") if args.get(k) is not None})
    asyncio.create_task(_gen().run_batch_generation(project_id, request))
    return {"queued": True, "project_id": project_id,
            "shot_ids": args.get("shot_ids") or "all"}


@tool(
    "replan_shots", "generation",
    "Re-plan ALL shots from the story via the shots director (LLM call, overwrites "
    "shots.json; generated media is re-linked by prompt match where possible).",
    _obj({
        "project_id": _s(),
        "shots_director": _s("Director override", default="default"),
        "max_shots": _i(), "max_shot_duration": {"type": "number"},
    }, ["project_id"]),
)
async def tool_replan_shots(args: dict) -> Any:
    (project_id,) = _require(args, "project_id")
    shots = await _gen().replan_shots(
        project_id, max_shots=args.get("max_shots"),
        shots_director=args.get("shots_director") or "default",
        max_shot_duration=args.get("max_shot_duration"))
    return {"replanned": True, "shots": len(shots) if isinstance(shots, list) else shots}


@tool(
    "generate_project_thumbnail", "generation",
    "Queue the project thumbnail/poster generation.",
    _obj({"project_id": _s(), "force": _b(), "is_poster": _b()}, ["project_id"]),
)
async def tool_generate_thumbnail(args: dict) -> Any:
    (project_id,) = _require(args, "project_id")
    item_id = await _gen().generate_thumbnail(
        project_id, force=bool(args.get("force")), is_poster=bool(args.get("is_poster")))
    return {"queued": True, "item_id": item_id}


# =============================================================== QUEUE category

@tool(
    "get_queue", "queue",
    "List generation queue items. DEFAULT: only actionable items (pending/active/paused/"
    "failed) plus a status summary — pass status='completed' (or include_completed=true) "
    "to see history.",
    _obj({
        "project_id": _s(), "status": _s(enum=["pending", "active", "completed", "failed", "paused", "cancelled"]),
        "include_completed": _b("Include completed items even without status filter"),
    }),
)
def tool_get_queue(args: dict) -> Any:
    status = args.get("status")
    status = status.lower() if status else None
    items = _qs().get_queue(project_id=args.get("project_id") or None, status=status)
    all_items = _qs().get_queue(project_id=args.get("project_id") or None)
    counts = {}
    for it in all_items:
        st = str(getattr(it, "status", "")) or "unknown"
        counts[st] = counts.get(st, 0) + 1
    if status is None and not args.get("include_completed"):
        items = [it for it in items
                 if str(getattr(it, "status", "")) not in ("completed", "cancelled")]
    out = []
    for it in items:
        data = it.dict() if hasattr(it, "dict") else dict(it)
        keep = {k: data.get(k) for k in (
            "item_id", "project_id", "generation_type", "status", "progress",
            "priority", "error_message", "shot_id", "shot_index", "created_at") if data.get(k) is not None}
        err = keep.get("error_message")
        if err and len(err) > 200:
            keep["error_message"] = err[:200] + "…"
        out.append(keep)
    return {"items": out, "count": len(out), "summary": counts}


@tool(
    "queue_action", "queue",
    "Control a queue item: cancel, pause, resume, requeue, or force-start it.",
    _obj({
        "action": _s(enum=["cancel", "pause", "resume", "requeue", "force_start"]),
        "item_id": _s("Queue item id (queue_xxxxxxxx)"),
    }, ["action", "item_id"]),
)
async def tool_queue_action(args: dict) -> Any:
    (action, item_id) = _require(args, "action", "item_id")
    qs = _qs()
    if action == "cancel":
        ok = qs.mark_cancelled(item_id)
        from core import comfy_client
        try:
            comfy_client.interrupt_generation()
        except Exception:
            pass
    elif action == "pause":
        ok = qs.mark_paused(item_id)
    elif action == "resume":
        ok = qs.resume_item(item_id)
    elif action == "requeue":
        ok = qs.requeue_item(item_id)
    elif action == "force_start":
        await _gen().force_start_item(item_id)
        ok = True
    else:
        raise ValueError(f"Unknown action '{action}'")
    if not ok:
        raise ValueError(f"Queue item '{item_id}' not found or action not applicable")
    _gen()._wake_up_processor()
    return {"action": action, "item_id": item_id, "ok": True}


@tool(
    "cancel_project_generation", "queue",
    "Cancel all running/pending generation for a project.",
    _obj({"project_id": _s()}, ["project_id"]),
)
def tool_cancel_project_generation(args: dict) -> Any:
    (project_id,) = _require(args, "project_id")
    _gen().cancel_project(project_id)
    return {"cancelled": True, "project_id": project_id}


# ========================================================== WORKFLOWS category

@tool(
    "list_workflows", "workflows",
    "List ComfyUI workflows by category (video, image, soundfx, voice).",
)
def tool_list_workflows(args: dict) -> Any:
    from core.workflow_loader import get_workflow_loader
    loader = get_workflow_loader()
    result = {}
    for category in loader.list_categories():
        result[category] = loader.list_workflows(category)
    return {"workflows": result}


@tool(
    "read_workflow", "workflows",
    "Read a workflow JSON file (category: video/image/soundfx/voice).",
    _obj({"category": _s(), "filename": _s()}, ["category", "filename"]),
)
def tool_read_workflow(args: dict) -> Any:
    from core.workflow_loader import get_workflow_loader
    (category, filename) = _require(args, "category", "filename")
    content = get_workflow_loader().load_workflow(category, filename)
    return {"category": category, "filename": filename, "content": content[:30_000],
            "truncated": len(content) > 30_000}


@tool(
    "write_workflow", "workflows",
    "Create or overwrite a workflow JSON file.",
    _obj({"category": _s(), "filename": _s(), "content": _s("Full workflow JSON text")},
         ["category", "filename", "content"]),
)
def tool_write_workflow(args: dict) -> Any:
    from core.workflow_loader import get_workflow_loader
    (category, filename, content) = _require(args, "category", "filename", "content")
    try:
        json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Workflow content is not valid JSON: {exc}")
    get_workflow_loader().save_workflow(category, filename, content)
    return {"saved": True, "category": category, "filename": filename}


# ========================================================== DIRECTORS category

@tool(
    "list_directors", "directors",
    "Compact index of story/shots director ids (flat lists — ids are full paths like "
    "'documentary/netflix_documentary'). Use read_director for a director's content.",
)
def tool_list_directors(args: dict) -> Any:
    from core.director_loader import get_director_loader
    tree = get_director_loader().list_director_tree()
    compact = {}
    for director_type, groups in tree.items():
        ids = []

        def walk(nodes):
            for node in nodes or []:
                for d in node.get("directors", []) or []:
                    if d.get("id"):
                        ids.append(d["id"])
                walk(node.get("children") or node.get("subcategories"))

        walk(groups if isinstance(groups, list) else groups.get("groups", []))
        compact[director_type] = sorted(set(ids))
    return compact


@tool(
    "read_director", "directors",
    "Read a director's raw markdown prompt (director_type: 'story' or 'shots').",
    _obj({"director_type": _s(enum=["story", "shots"]), "director_id": _s("Director name/path")},
         ["director_type", "director_id"]),
)
def tool_read_director(args: dict) -> Any:
    from core.director_loader import get_director_loader
    (director_type, director_id) = _require(args, "director_type", "director_id")
    content = get_director_loader().load_prompt_raw(director_type, director_id)
    return {"director_type": director_type, "director_id": director_id,
            "content": content[:30_000], "truncated": len(content) > 30_000}


@tool(
    "write_director", "directors",
    "Create or overwrite a director markdown file. Use {USER_INPUT} for the dynamic slot "
    "and {{include:name}} for composition.",
    _obj({
        "director_type": _s(enum=["story", "shots"]),
        "director_id": _s("Path under directors/<type>/, e.g. 'movie/horror'"),
        "content": _s("Markdown content"),
    }, ["director_type", "director_id", "content"]),
)
def tool_write_director(args: dict) -> Any:
    from core.director_loader import get_director_loader
    (director_type, director_id, content) = _require(args, "director_type", "director_id", "content")
    get_director_loader().save_prompt(director_type, director_id, content)
    return {"saved": True, "director_type": director_type, "director_id": director_id}


# ============================================================== CONFIG tools

@tool(
    "get_app_config", "config",
    "Read the app's pipeline configuration (LLM provider, generation modes, default "
    "workflows, ComfyUI URL). Secrets are never returned.",
)
def tool_get_app_config(args: dict) -> Any:
    fields = {
        "llm_provider": config.LLM_PROVIDER,
        "image_generation_mode": getattr(config, "IMAGE_GENERATION_MODE", None),
        "video_generation_mode": getattr(config, "VIDEO_GENERATION_MODE", None),
        "image_workflow": getattr(config, "IMAGE_WORKFLOW", None),
        "video_workflow": getattr(config, "VIDEO_WORKFLOW", None),
        "comfy_url": getattr(config, "COMFY_URL", None),
        "aspect_ratio_default": getattr(config, "DEFAULT_ASPECT_RATIO", "16:9"),
        "target_video_length": getattr(config, "TARGET_VIDEO_LENGTH", None),
        "concurrent_limits": getattr(config, "CONCURRENT_GENERATION_LIMITS", {}),
    }
    return fields


@tool(
    "update_app_config", "config",
    "Update non-secret pipeline configuration (persists to .env and applies live). "
    "Keys: llm_provider, image_generation_mode, video_generation_mode, image_workflow, "
    "video_workflow, comfy_url.",
    _obj({"updates": {"type": "object", "description": "Config key -> new value"}}, ["updates"]),
)
def tool_update_app_config(args: dict) -> Any:
    from core.config_utils import update_env_config
    (updates,) = _require(args, "updates")
    if not isinstance(updates, dict) or not updates:
        raise ValueError("updates must be a non-empty object")
    from web_ui.backend.api.config_api import _CONFIG_FIELDS, _SECRET_FIELDS
    unknown = [k for k in updates if k in _SECRET_FIELDS or k not in _CONFIG_FIELDS]
    if unknown:
        raise ValueError(f"Unknown or not editable here: {', '.join(unknown)}")
    env_updates = {}
    for name, value in updates.items():
        if value is None:
            continue
        env_key, attr, _ftype = _CONFIG_FIELDS[name]
        env_updates[env_key] = "true" if isinstance(value, bool) else str(value)
    if not env_updates:
        raise ValueError("No values to update")
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.env"))
    update_env_config(env_updates, env_path=env_path)
    for name, value in updates.items():
        if value is None:
            continue
        _env_key, attr, ftype = _CONFIG_FIELDS[name]
        coerced = value
        if ftype == "int":
            coerced = int(value)
        elif ftype == "float":
            coerced = float(value)
        elif ftype == "bool":
            coerced = str(value).lower() in ("1", "true", "yes", "on")
        if hasattr(config, attr):
            setattr(config, attr, coerced)
        os.environ[_CONFIG_FIELDS[name][0]] = env_updates[_CONFIG_FIELDS[name][0]]
    return {"updated": True, "keys": sorted(updates.keys())}


# =============================================================== ASSETS tools

@tool(
    "search_assets", "assets",
    "Search the global asset library (Images/Videos/Audio/Music/Guides/Templates) by title.",
    _obj({"query": _s("Search text (empty = list all)"), "category": _s("i, v, a, m, g or t")}, []),
)
def tool_search_assets(args: dict) -> Any:
    from web_ui.backend.services.asset_service import get_asset_service
    query = (args.get("query") or "").strip().lower()
    entries = get_asset_service().list_all()
    out = []
    for e in entries:
        data = e.dict() if hasattr(e, "dict") else dict(e)
        if args.get("category") and str(data.get("category", "")).lower() != args["category"].lower():
            continue
        if query and query not in str(data.get("title", "")).lower():
            continue
        out.append({k: data.get(k) for k in ("ref", "title", "category", "extension") if data.get(k) is not None})
        if len(out) >= 100:
            break
    return {"assets": out, "count": len(out)}


@tool(
    "read_asset_text", "assets",
    "Read the text content of a library Guide/Template asset (ref like 'g/9f3ab21c').",
    _obj({"ref": _s("Asset ref, e.g. 'g/9f3ab21c'")}, ["ref"]),
)
def tool_read_asset_text(args: dict) -> Any:
    from web_ui.backend.services.asset_service import get_asset_service
    (ref,) = _require(args, "ref")
    content = get_asset_service().read_text(ref)
    return {"ref": ref, "content": content[:20_000], "truncated": len(content) > 20_000}


@tool(
    "write_asset_text", "assets",
    "Create or overwrite a text asset (Guide/Template) in the library.",
    _obj({
        "title": _s("Asset title"), "content": _s("Text content"),
        "category": _s(enum=["g", "t"], default="g"),
        "sub_category": _s("Optional nested category path"),
    }, ["title", "content"]),
)
def tool_write_asset_text(args: dict) -> Any:
    from web_ui.backend.services.asset_service import get_asset_service
    (title, content) = _require(args, "title", "content")
    entry = get_asset_service().create_text(
        title=title, content=content, category=args.get("category") or "g",
        sub_category=args.get("sub_category"))
    return {"created": True, "ref": getattr(entry, "ref", None), "title": title}


# ================================================================ FILES tools

@tool(
    "list_files", "files",
    "List files in the project output folder (or a repo/docs path). Set project_id to "
    "list inside that project; use recursive=true for the full tree.",
    _obj({
        "path": _s("Relative path (default: project/output root)"),
        "project_id": _s("Scope to this project's folder"),
        "recursive": _b("Walk subdirectories"),
    }),
)
def tool_list_files(args: dict) -> Any:
    from web_ui.backend.services.agent import file_ops
    return file_ops.list_dir(args.get("path") or "", args.get("project_id"),
                             recursive=bool(args.get("recursive")))


@tool(
    "read_file", "files",
    "Read a text/JSON file from the project output folder or repo (docs, directors, "
    "workflows). Use offset for paging large files.",
    _obj({
        "path": _s("File path (project-relative when project_id is given)"),
        "project_id": _s("Scope to this project's folder"),
        "offset": _i("Character offset to start reading from"),
    }, ["path"]),
)
def tool_read_file(args: dict) -> Any:
    from web_ui.backend.services.agent import file_ops
    (path,) = _require(args, "path")
    return file_ops.read_file(path, args.get("project_id"), offset=int(args.get("offset") or 0))


@tool(
    "write_file", "files",
    "Write a text/JSON file inside the output folder (project dirs, assets, editor data).",
    _obj({
        "path": _s("File path (project-relative when project_id is given)"),
        "content": _s("Full file content"),
        "project_id": _s("Scope to this project's folder"),
    }, ["path", "content"]),
)
def tool_write_file(args: dict) -> Any:
    from web_ui.backend.services.agent import file_ops
    (path, content) = _require(args, "path", "content")
    return file_ops.write_file(path, content, args.get("project_id"))


@tool(
    "edit_file", "files",
    "Edit a file by exact string replacement (safer than rewriting whole files). "
    "Fails if the find-text is absent or ambiguous unless replace_all=true.",
    _obj({
        "path": _s(), "find": _s("Exact text to find"),
        "replace": _s("Replacement text"),
        "project_id": _s(), "replace_all": _b("Replace every occurrence"),
    }, ["path", "find", "replace"]),
)
def tool_edit_file(args: dict) -> Any:
    from web_ui.backend.services.agent import file_ops
    (path, find, replace) = _require(args, "path", "find", "replace")
    return file_ops.edit_file(path, find, replace, args.get("project_id"),
                              replace_all=bool(args.get("replace_all")))


@tool(
    "delete_file", "files",
    "DANGEROUS: delete a file inside the output folder.",
    _obj({"path": _s(), "project_id": _s()}, ["path"]),
    dangerous=True,
)
def tool_delete_file(args: dict) -> Any:
    from web_ui.backend.services.agent import file_ops
    (path,) = _require(args, "path")
    return file_ops.delete_file(path, args.get("project_id"))


@tool(
    "search_files", "files",
    "Search file CONTENTS. Uses PowerShell Select-String on Windows and grep on Linux, "
    "with a Python fallback. Roots: 'project' (needs project_id), 'projects', 'output', "
    "'repo', 'docs', 'skills'.",
    _obj({
        "pattern": _s("Text or regex pattern"),
        "root": _s(enum=["project", "projects", "output", "repo", "docs", "skills"], default="output"),
        "project_id": _s("Required when root='project'"),
        "file_glob": _s("Filename filter, e.g. '*.json' or '*.md'"),
        "regex": _b("Treat pattern as regex (default plain text)"),
        "ignore_case": _b("Case-insensitive match (default true)"),
        "max_results": _i(default=50),
    }, ["pattern"]),
)
def tool_search_files(args: dict) -> Any:
    from web_ui.backend.services.agent import file_ops
    (pattern,) = _require(args, "pattern")
    return file_ops.search_files(
        pattern, root=args.get("root") or "output", project_id=args.get("project_id"),
        file_glob=args.get("file_glob"), regex=bool(args.get("regex")),
        ignore_case=args.get("ignore_case", True), max_results=int(args.get("max_results") or 50))


# ================================================================ SKILLS tools

@tool(
    "list_skills", "skills",
    "List agent skills (reusable instruction playbooks in the agent_skills folder).",
)
def tool_list_skills(args: dict) -> Any:
    from web_ui.backend.services.agent.skills import get_skill_store
    skills = get_skill_store().list_skills()
    return {"skills": skills, "count": len(skills)}


@tool(
    "read_skill", "skills",
    "Read a skill's full instructions. ALWAYS call this before following a skill.",
    _obj({"name": _s("Skill name from list_skills")}, ["name"]),
)
def tool_read_skill(args: dict) -> Any:
    from web_ui.backend.services.agent.skills import get_skill_store
    (name,) = _require(args, "name")
    return get_skill_store().read_skill(name)


@tool(
    "read_skill_file", "skills",
    "Read an auxiliary file shipped inside a skill folder.",
    _obj({"name": _s("Skill name"), "path": _s("Relative file path inside the skill")}, ["name", "path"]),
)
def tool_read_skill_file(args: dict) -> Any:
    from web_ui.backend.services.agent.skills import get_skill_store
    (name, path) = _require(args, "name", "path")
    content = get_skill_store().read_skill_file(name, path)
    return {"name": name, "path": path, "content": content[:20_000]}


# ============================================================ system/diagnostics

@tool(
    "get_project_overview", "system",
    "One-shot compact overview: project metadata + scene titles + per-shot status grid. "
    "For r2v projects also shows reference readiness (character sheets, scene backgrounds, "
    "prop sheets) per shot. Great starting point before editing shots.",
    _obj({"project_id": _s()}, ["project_id"]),
)
def tool_project_overview(args: dict) -> Any:
    (project_id,) = _require(args, "project_id")
    pm = _pm()
    meta = pm.load_project(project_id)
    story = pm.get_story(project_id) or {}
    shots = pm.get_shots(project_id) or []
    mode = (meta.get("video_generation_type") or "i2v").lower()
    scenes = [
        {"scene_id": i, "scene_name": s.get("scene_name"), "location": s.get("location"),
         "characters": s.get("characters"),
         **({"background_ready": bool(s.get("background_image_path"))}
            if mode == "r2v" else {})}
        for i, s in enumerate(story.get("scenes", []))
    ]
    overview = {
        "project_id": project_id,
        "idea": meta.get("idea"),
        "project_type": meta.get("project_type"),
        "story_director": meta.get("story_director"),
        "shots_director": meta.get("shots_director"),
        "video_generation_type": mode,
        "r2v_mode": meta.get("r2v_mode"),
        "prompt_mode": meta.get("prompt_mode"),
        "aspect_ratio": meta.get("aspect_ratio"),
        "title": story.get("title"),
        "style": story.get("style"),
        "scenes": scenes,
        "shots": [_summarize_shot(s) for s in shots[:40]],
        "shots_truncated": len(shots) > 40,
        "stats": meta.get("stats"),
        "errors": meta.get("errors"),
    }
    if mode == "r2v":
        overview["characters"] = [
            {"index": i, "name": c.get("name"),
             "reference_ready": bool(c.get("character_reference_image_path"))}
            for i, c in enumerate(story.get("characters", []))
        ]
        overview["props"] = [
            {"index": i, "name": p.get("name"),
             "reference_ready": bool(p.get("reference_image_path"))}
            for i, p in enumerate(story.get("props", []))
        ]
        overview["reference_flow"] = (
            "r2v: videos are rendered from references (characters -> scene background "
            "-> props, auto-attached to shots, max 9 image slots). No per-shot images."
        )
    return overview


# ------------------------------------------------------------- dispatch layer


def get_effective_tools(agent_cfg: Optional[dict] = None) -> Dict[str, Tool]:
    """Built-in tools filtered by enable/disable toggles and the dangerous gate."""
    from web_ui.backend.services.agent.config_store import get_agent_config_store
    cfg = agent_cfg if agent_cfg is not None else get_agent_config_store().load()
    dangerous_allowed = cfg.get("dangerous_tools_allowed") or (
        cfg.get("dangerous_tools_allowed") is None and config.AGENT_ALLOW_DANGEROUS_TOOLS)
    enabled_map = cfg.get("enabled_tools") or {}
    effective: Dict[str, Tool] = {}
    for name, t in TOOLS.items():
        if t.dangerous and not dangerous_allowed:
            continue
        enabled = enabled_map.get(name, t.default_enabled)
        if not enabled:
            continue
        effective[name] = t
    return effective


async def execute_tool(name: str, arguments: Dict[str, Any],
                       agent_cfg: Optional[dict] = None) -> Dict[str, Any]:
    """Execute a built-in tool by name. Returns {ok, tool, result|error}."""
    arguments = arguments or {}
    try:
        tool_def = TOOLS.get(name)
        if tool_def is None:
            raise ValueError(f"Unknown tool '{name}'")
        effective = get_effective_tools(agent_cfg)
        if name not in effective:
            reason = ("dangerous tools are disabled" if tool_def.dangerous
                      else "the tool is disabled in agent settings")
            raise ValueError(f"Tool '{name}' is not available: {reason}")
        if asyncio.iscoroutinefunction(tool_def.handler):
            result = await tool_def.handler(arguments)
        else:
            result = await asyncio.to_thread(tool_def.handler, arguments)
        return {"ok": True, "tool": name, "result": result}
    except Exception as exc:  # noqa: BLE001 — errors go back to the LLM as tool results
        return {"ok": False, "tool": name, "error": str(exc)}


def catalog(agent_cfg: Optional[dict] = None) -> List[Dict[str, Any]]:
    """Tool catalog for the UI: every built-in tool with its enabled state."""
    from web_ui.backend.services.agent.config_store import get_agent_config_store
    cfg = agent_cfg if agent_cfg is not None else get_agent_config_store().load()
    dangerous_allowed = cfg.get("dangerous_tools_allowed") or (
        cfg.get("dangerous_tools_allowed") is None and config.AGENT_ALLOW_DANGEROUS_TOOLS)
    enabled_map = cfg.get("enabled_tools") or {}
    out = []
    for name, t in sorted(TOOLS.items(), key=lambda kv: (kv[1].category, kv[0])):
        enabled = enabled_map.get(name, t.default_enabled)
        blocked = t.dangerous and not dangerous_allowed
        out.append({
            "name": name,
            "category": t.category,
            "description": t.description,
            "dangerous": t.dangerous,
            "enabled": bool(enabled) and not blocked,
            "blocked_by_dangerous_gate": bool(blocked),
            "source": "builtin",
        })
    return out
