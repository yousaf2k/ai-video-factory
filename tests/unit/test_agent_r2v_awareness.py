"""
r2v awareness: tool gating, overview reference readiness, engine mode briefing.
"""
import asyncio
import json

import pytest

from web_ui.backend.services.agent import registry
from web_ui.backend.services.agent.engine import _project_context_block
from web_ui.backend.services.agent.registry import execute_tool


@pytest.fixture
def project(tmp_path, monkeypatch):
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    monkeypatch.setattr("config.ABS_PROJECTS_DIR", str(projects_dir))
    from core.project_manager import ProjectManager
    pm = ProjectManager(projects_dir=str(projects_dir))
    pm.create_project(idea="r2v idea", project_id="proj_r2v",
                      video_generation_type="r2v", r2v_mode="singularity")
    pm.create_project(idea="i2v idea", project_id="proj_i2v")
    pm.save_story("proj_r2v", json.dumps({
        "title": "T", "scenes": [
            {"scene_id": 0, "location": "Rome", "characters": "Maximus",
             "action": "fights", "emotion": "anger"},
        ],
        "characters": [{"name": "Maximus", "image_prompt": "a general"}],
        "props": [{"name": "sword", "category": "weapon", "image_prompt": "a gladius"}],
    }))
    pm.save_shots("proj_r2v", [
        {"id": "aaaa1111", "image_prompt": "img", "motion_prompt": "walk",
         "video_prompt": "subject_definitions:...", "camera": "static",
         "narration": "", "batch_number": 1, "reference_asset_ids": ["p/x/references/char_0.png"]},
    ])
    return "proj_r2v"


CFG = {"dangerous_tools_allowed": False, "enabled_tools": {}}


def _run(tool_name, args):
    return asyncio.run(execute_tool(tool_name, args, CFG))


def test_generate_shot_image_blocked_on_r2v(project):
    result = _run("generate_shot_image", {"project_id": project, "shot": 1})
    assert result["ok"] is False
    assert "NO first-frame images" in result["error"]
    assert "generate_character_reference" in result["error"]


def test_batch_images_blocked_on_r2v(project):
    result = _run("batch_regenerate_shots",
                  {"project_id": project, "regenerate_images": True})
    assert result["ok"] is False
    assert "regenerate_images=false" in result["error"]


def test_generate_shot_video_allowed_on_r2v(project):
    """Video generation must NOT be blocked (monkeypatch the queue add)."""
    from web_ui.backend.services.agent import registry as reg
    original = reg.TOOLS["generate_shot_video"].handler

    def fake_gen_service():
        class FakeGen:
            def add_single_shot_to_queue(self, project_id, shot, gtype, request):
                class I: item_id = "queue_fake"
                return [I()]
        return FakeGen()

    import web_ui.backend.services.agent.registry as r
    real_gen = r._gen
    r._gen = fake_gen_service
    try:
        result = _run("generate_shot_video", {"project_id": project, "shot": 1})
    finally:
        r._gen = real_gen
    assert result["ok"] is True
    assert result["result"]["queued"] is True


def test_generate_shot_image_allowed_on_i2v(tmp_path, monkeypatch):
    projects_dir = tmp_path / "p2"
    projects_dir.mkdir()
    monkeypatch.setattr("config.ABS_PROJECTS_DIR", str(projects_dir))
    from core.project_manager import ProjectManager
    ProjectManager(projects_dir=str(projects_dir)).create_project(idea="x", project_id="proj_i2v")

    import web_ui.backend.services.agent.registry as r
    def fake_gen_service():
        class FakeGen:
            def add_single_shot_to_queue(self, *a, **k):
                return []
        return FakeGen()
    real_gen = r._gen
    r._gen = fake_gen_service
    try:
        result = _run("generate_shot_image", {"project_id": "proj_i2v", "shot": 1})
    finally:
        r._gen = real_gen
    # no shots exist -> shot resolution error, NOT the r2v mode error
    assert result["ok"] is False
    assert "NO first-frame images" not in result["error"]


def test_overview_shows_reference_readiness(project):
    out = _run("get_project_overview", {"project_id": project})
    ov = out["result"]
    assert ov["video_generation_type"] == "r2v"
    assert ov["r2v_mode"] == "singularity"
    assert ov["characters"][0] == {"index": 0, "name": "Maximus", "reference_ready": False}
    assert ov["props"][0]["name"] == "sword" and ov["props"][0]["reference_ready"] is False
    assert ov["scenes"][0]["background_ready"] is False
    assert "auto-attach" in ov["reference_flow"]


def test_engine_context_contains_r2v_briefing(project, monkeypatch):
    monkeypatch.setattr("config.ABS_PROJECTS_DIR",
                        str(project and __import__("pathlib").Path(
                            __import__("core.project_manager", fromlist=["ProjectManager"])
                            .ProjectManager().projects_dir)))
    block = _project_context_block(project)
    assert "REFERENCE-TO-VIDEO" in block
    assert "NEVER call generate_shot_image" in block
    assert "singularity mode" in block
    assert "r2v-workflow" in block


def test_prop_reference_tool_validates_index(project):
    result = _run("generate_prop_reference", {"project_id": project, "prop_index": 5})
    assert result["ok"] is False
    assert "out of range" in result["error"]
