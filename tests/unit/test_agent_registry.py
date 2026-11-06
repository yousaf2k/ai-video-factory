"""
Unit tests for the agent tool registry: catalog, gating and real tool calls
against a temp project.
"""
import asyncio
import json

import pytest

from web_ui.backend.services.agent import registry
from web_ui.backend.services.agent.registry import (
    TOOLS, catalog, execute_tool, get_effective_tools,
)


@pytest.fixture
def project(tmp_path, monkeypatch):
    """A real ProjectManager project in a temp dir, wired into config."""
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    monkeypatch.setattr("config.ABS_PROJECTS_DIR", str(projects_dir))
    from core.project_manager import ProjectManager
    pm = ProjectManager(projects_dir=str(projects_dir))
    pm.create_project(idea="Test idea", project_id="proj_test")
    pm.save_story("proj_test", json.dumps({
        "title": "T", "scenes": [
            {"scene_id": 0, "location": "Rome", "characters": "Maximus",
             "action": "fights", "emotion": "anger"},
        ],
        "characters": [{"name": "Maximus", "image_prompt": "a general"}],
    }))
    pm.save_shots("proj_test", [
        {"id": "aaaa1111", "image_prompt": "img", "motion_prompt": "walk",
         "camera": "static", "narration": "", "batch_number": 1},
        {"id": "bbbb2222", "image_prompt": "img2", "motion_prompt": "run",
         "camera": "pan", "narration": "", "batch_number": 1},
    ])
    return "proj_test"


# ------------------------------------------------------------------ registry

def test_tools_registered():
    expected = {
        "list_projects", "create_project", "update_project",
        "delete_project", "duplicate_project",
        "get_story", "update_story", "generate_story",
        "update_scene", "add_scene", "delete_scene",
        "list_characters", "add_character", "update_character", "delete_character",
        "list_shots", "get_shot", "update_shot", "add_shot", "delete_shot",
        "generate_shot_image", "generate_shot_video", "generate_shot_soundfx",
        "replan_shots", "get_queue", "queue_action",
        "list_workflows", "read_workflow", "write_workflow",
        "list_directors", "read_director", "write_director",
        "get_app_config", "search_assets",
        "list_files", "read_file", "write_file", "edit_file", "delete_file",
        "search_files", "list_skills", "read_skill", "get_project_overview",
    }
    assert expected.issubset(set(TOOLS))
    for tool in TOOLS.values():
        assert tool.description
        assert tool.parameters.get("type") == "object"
        assert callable(tool.handler)


def test_dangerous_tools_gated_off_by_default():
    effective = get_effective_tools({"dangerous_tools_allowed": False, "enabled_tools": {}})
    assert "delete_project" not in effective
    assert "delete_shot" not in effective
    assert "update_shot" in effective
    effective_on = get_effective_tools({"dangerous_tools_allowed": True, "enabled_tools": {}})
    assert "delete_project" in effective_on


def test_enabled_tools_toggle():
    cfg = {"dangerous_tools_allowed": True, "enabled_tools": {"update_shot": False}}
    assert "update_shot" not in get_effective_tools(cfg)
    # catalog reports blocked state for the UI
    cat = {t["name"]: t for t in catalog(cfg)}
    assert cat["update_shot"]["enabled"] is False
    assert cat["delete_project"]["enabled"] is True


# --------------------------------------------------------------- execution

def _run(tool_name, args):
    cfg = {"dangerous_tools_allowed": False, "enabled_tools": {}}
    return asyncio.run(execute_tool(tool_name, args, cfg))


def test_list_shots_is_lean_index(project):
    result = _run("list_shots", {"project_id": project})
    assert result["ok"] is True
    shots = result["result"]["shots"]
    assert result["result"]["count"] == 2
    # Index only — no prompt text anywhere in the listing
    for shot in shots:
        for key in shot:
            assert "prompt" not in key, f"list_shots leaked {key}"
    assert {"id", "index", "camera"} <= set(shots[0])


def test_list_projects_is_lean_index():
    result = _run("list_projects", {})
    assert result["ok"] is True
    for entry in result["result"]["projects"]:
        assert "thumbnail_url" not in entry and "timestamp" not in entry
        assert len(entry.get("idea") or "") <= 122  # 120 + ellipsis
        assert "story" not in entry


def test_list_directors_is_compact():
    result = _run("list_directors", {})
    assert result["ok"] is True
    tree = result["result"]
    assert set(tree) == {"story", "shots"}
    assert "documentary/default" in tree["story"]
    assert all(isinstance(v, list) for v in tree.values())
    assert len(json.dumps(tree)) < 8000


def test_get_story_parts(project):
    result = _run("get_story", {"project_id": "proj_test", "parts": ["characters"]})
    assert result["ok"] is True
    assert set(result["result"]) == {"characters"}
    bad = _run("get_story", {"project_id": "proj_test", "parts": ["bogus"]})
    assert bad["ok"] is False and "Unknown story part" in bad["error"]


def test_create_project_type_accepts_names_and_aliases(tmp_path, monkeypatch):
    """The agent passes 'movie' (a string), not the int enum — must map cleanly."""
    projects_dir = tmp_path / "pp"
    projects_dir.mkdir()
    monkeypatch.setattr("config.ABS_PROJECTS_DIR", str(projects_dir))
    from core.project_manager import ProjectManager
    ProjectManager(projects_dir=str(projects_dir))

    cfg = {"dangerous_tools_allowed": False, "enabled_tools": {}}
    result = asyncio.run(execute_tool("create_project",
                                      {"idea": "x", "project_type": "movie"}, cfg))
    assert result["ok"] is True
    assert result["result"]["project_type"] == "movie"
    assert ProjectManager(projects_dir=str(projects_dir)).load_project(
        result["result"]["project"]["project_id"])["project_type"] == 3

    for alias, expected in [("cinematic", 3), ("then_vs_now", 2), ("asmr", 4),
                            ("3", 3), (3, 3), (None, 1)]:
        r = asyncio.run(execute_tool("create_project",
                                     {"idea": "x", "project_type": alias}, cfg))
        assert r["ok"] is True, (alias, r)
        assert r["result"]["project_type"] == {1: "documentary", 2: "then_vs_now",
                                               3: "movie", 4: "asmr"}[expected]

    bad = asyncio.run(execute_tool("create_project",
                                   {"idea": "x", "project_type": "space western"}, cfg))
    assert bad["ok"] is False
    assert "documentary" in bad["error"] and "movie" in bad["error"]

    pm_mode = asyncio.run(execute_tool("create_project",
                                       {"idea": "x", "prompt_mode": "master"}, cfg))
    assert pm_mode["ok"] is False and "prompt_mode" in pm_mode["error"]


def test_get_and_update_shot(project):
    result = _run("get_shot", {"project_id": project, "shot": 1})
    assert result["ok"] is True
    assert result["result"]["id"] == "aaaa1111"
    # resolve by id too
    by_id = _run("get_shot", {"project_id": project, "shot": "bbbb2222"})
    assert by_id["ok"] is True
    assert "run" in by_id["result"]["motion_prompt"]

    updated = _run("update_shot", {
        "project_id": project, "shot": 1,
        "fields": {"motion_prompt": "rides a horse", "camera": "aerial"},
    })
    assert updated["ok"] is True
    check = _run("get_shot", {"project_id": project, "shot": 1})
    assert check["result"]["motion_prompt"] == "rides a horse"
    assert check["result"]["camera"] == "aerial"


def test_update_shot_rejects_unknown_fields(project):
    result = _run("update_shot", {"project_id": project, "shot": 1, "fields": {"bogus": 1}})
    assert result["ok"] is False
    assert "Unknown shot field" in result["error"]


def test_missing_project_returns_error():
    result = _run("get_shot", {"project_id": "nope", "shot": 1})
    assert result["ok"] is False
    assert "error" in result


def test_disabled_tool_rejected():
    cfg = {"dangerous_tools_allowed": True, "enabled_tools": {"list_projects": False}}
    result = asyncio.run(execute_tool("list_projects", {}, cfg))
    assert result["ok"] is False
    assert "disabled" in result["error"]


def test_dangerous_tool_blocked_without_flag():
    result = _run("delete_project", {"project_id": "x"})
    assert result["ok"] is False
    assert "dangerous" in result["error"]


def test_unknown_tool():
    result = _run("no_such_tool", {})
    assert result["ok"] is False
    assert "Unknown tool" in result["error"]


def test_story_tools(project):
    scenes = _run("update_scene", {
        "project_id": project, "scene_id": 0, "fields": {"location": "Carthage"}})
    assert scenes["ok"] is True
    assert scenes["result"]["scene"]["location"] == "Carthage"

    added = _run("add_character", {
        "project_id": project,
        "character": {"name": "Lucilla", "image_prompt": "a queen"}})
    assert added["ok"] is True
    chars = _run("list_characters", {"project_id": project})
    assert chars["result"]["count"] == 2

    out = _run("get_project_overview", {"project_id": project})
    assert out["ok"] is True
    assert out["result"]["scenes"][0]["location"] == "Carthage"


def test_add_and_delete_shot(project):
    added = _run("add_shot", {
        "project_id": project, "image_prompt": "new", "motion_prompt": "fly",
        "camera": "zoom", "position": 1})
    assert added["ok"] is True
    new_id = added["result"]["shot_id"]
    listing = _run("list_shots", {"project_id": project})
    assert listing["result"]["count"] == 3

    cfg = {"dangerous_tools_allowed": True, "enabled_tools": {}}
    deleted = asyncio.run(execute_tool("delete_shot", {"project_id": project, "shot": new_id}, cfg))
    assert deleted["ok"] is True
    assert _run("list_shots", {"project_id": project})["result"]["count"] == 2
