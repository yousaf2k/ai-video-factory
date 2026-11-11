"""
Reference-sheet aspect spec: character sheets and backgrounds always render
16:9 regardless of the project's aspect ratio; shot images keep project aspect.
"""
import asyncio
from types import SimpleNamespace

import pytest

from web_ui.backend.models.queue import GenerationType


class _FakeProjectManager:
    def __init__(self, project_dir, meta):
        self._project_dir = project_dir
        self._meta = meta

    def get_project_dir(self, project_id):
        return self._project_dir

    def load_project(self, project_id):
        return self._meta


@pytest.fixture
def svc(tmp_path, monkeypatch):
    """A minimal GenerationService-like self with a captured generate_image."""
    import web_ui.backend.services.generation_service as gs

    captured = {}
    written = []

    def fake_generate_image(**kwargs):
        captured.update(kwargs)
        with open(kwargs["output_path"], "wb") as f:
            f.write(b"png")
        return kwargs["output_path"]

    monkeypatch.setattr("core.image_generator.generate_image", fake_generate_image)
    monkeypatch.setattr(gs.random, "randint", lambda a, b: 42)

    self_like = SimpleNamespace(
        project_manager=_FakeProjectManager(str(tmp_path), {"aspect_ratio": "9:16"}),
        cancelled_shots={},
        cancelled_projects=set(),
        _get_next_image_version=lambda *a, **k: 1,
    )
    return self_like, captured


def _run(svc_pair, **kwargs):
    self_like, captured = svc_pair
    shot = {"index": 1, "image_prompt": "a castle"}
    from web_ui.backend.services.generation_service import (
        GenerationType, GenerationService,
    )
    path = GenerationService._generate_single_image(
        self_like, "proj_test", shot, None, None,
        generation_type=kwargs.pop("generation_type", None), **kwargs)
    return path, captured


def test_character_sheet_forces_16_9(svc):
    _, captured = _run(svc, aspect_ratio="16:9",
                       generation_type=GenerationType.CHARACTER_IMAGE)
    assert captured["aspect_ratio"] == "16:9"


def test_background_forces_16_9(svc):
    _, captured = _run(svc, aspect_ratio="16:9",
                       generation_type=GenerationType.BACKGROUND)
    assert captured["aspect_ratio"] == "16:9"


def test_shot_image_uses_project_aspect(svc):
    """Without the override (regular shot images), project aspect wins."""
    _, captured = _run(svc)
    assert captured["aspect_ratio"] == "9:16"
