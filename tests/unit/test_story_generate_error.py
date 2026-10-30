"""Offline unit tests: /story/generate records and clears the story step error.

The project detail UI shows a retry banner keyed off ``steps.story`` and the
persisted ``errors['story']`` message, so a failed LLM call must leave a
visible trace in project meta instead of silently "In Progress" forever.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from web_ui.backend.api import stories as stories_module

PROJECT_ID = "project_errtest"


def _make_project(projects_dir):
    pdir = os.path.join(projects_dir, PROJECT_ID)
    os.makedirs(pdir, exist_ok=True)
    meta = {
        "project_id": PROJECT_ID,
        "timestamp": "20261026_000000",
        "idea": "test idea",
        "story_director": "movie/mystery",
        "shots_director": "default",
        "started_at": "2026-10-26T00:00:00",
        "completed": False,
        "steps": {"story": False, "scene_graph": False, "shots": False,
                  "images": False, "videos": False, "narration": False},
        "stats": {"total_shots": 0, "images_generated": 0,
                  "videos_rendered": 0, "narration_generated": False},
        "project_type": 3,
    }
    with open(os.path.join(pdir, f"{PROJECT_ID}_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f)
    return pdir


def _read_meta(projects_dir):
    with open(os.path.join(projects_dir, PROJECT_ID, f"{PROJECT_ID}_meta.json"),
              encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture()
def story_env(tmp_path, monkeypatch):
    projects_dir = str(tmp_path / "projects")
    os.makedirs(projects_dir, exist_ok=True)
    _make_project(projects_dir)
    # stories.py holds two ProjectManager instances; point both at the sandbox
    monkeypatch.setattr(stories_module.project_manager, "projects_dir", projects_dir)
    monkeypatch.setattr(stories_module.project_service.project_manager, "projects_dir", projects_dir)

    app = FastAPI()
    app.include_router(stories_module.router)
    yield TestClient(app), projects_dir


def test_failed_story_generation_records_error(story_env, monkeypatch):
    client, projects_dir = story_env

    def boom(*args, **kwargs):
        raise RuntimeError('HTTP 400: {"error":{"code":"1211","message":"Unknown Model"}}')

    monkeypatch.setattr(stories_module, "build_story", boom)
    resp = client.post(f"/api/projects/{PROJECT_ID}/story/generate",
                       json={"director": "movie/mystery"})
    assert resp.status_code == 500

    meta = _read_meta(projects_dir)
    assert "Unknown Model" in meta["errors"]["story"]
    assert meta["steps"]["story"] is False


def test_successful_story_generation_clears_error(story_env, monkeypatch):
    client, projects_dir = story_env
    # Seed a stale error from a previous failed attempt
    stories_module.project_manager.update_meta_safely(
        PROJECT_ID,
        lambda meta: meta.setdefault("errors", {}).update({"story": "stale failure"}))

    story = {"title": "T", "scenes": [{"scene_id": 0, "title": "s", "description": "d",
                                       "duration": 10, "scene_prompt": "p"}],
             "total_duration": 10}
    monkeypatch.setattr(stories_module, "build_story",
                        lambda *a, **k: json.dumps(story))
    resp = client.post(f"/api/projects/{PROJECT_ID}/story/generate",
                       json={"director": "movie/mystery"})
    assert resp.status_code == 200

    meta = _read_meta(projects_dir)
    assert meta["steps"]["story"] is True
    assert "story" not in meta.get("errors", {})
