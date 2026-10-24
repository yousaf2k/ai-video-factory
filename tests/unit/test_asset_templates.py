"""Templates (t) asset type: registration, text routing, read_text, tree.

Templates are text assets (.txt/.md) under the Templates folder holding
prompt templates with {placeholder} fields; the generate dialog fills them
client-side. These tests pin the backend behavior the dialog relies on:
- 't' is a text-type category (like Guides 'g')
- text uploads stay in whichever text category is browsed (no g<->t reroute)
- non-text uploads into 't' reroute to the extension's own type folder
- read_text works for both text letters
"""
import io
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import config
from web_ui.backend.services.asset_service import AssetService


@pytest.fixture
def library(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSET_LIBRARY_DIRS", str(tmp_path))
    return AssetService(), str(tmp_path)


def test_templates_type_registered():
    assert config.ASSET_TYPES["t"]["folder"] == "Templates"
    assert config.ASSET_TYPES["t"]["type"] == "text"


def test_txt_upload_stays_in_templates(library):
    svc, _ = library
    result = svc.upload([("scene.txt", io.BytesIO(b"{subject} at {location}"))], "t/ImagePrompts")
    assert len(result["saved"]) == 1
    assert result["rerouted"] == []
    entry = result["saved"][0]
    assert entry["ref"].startswith("t/")
    assert entry["cat"] == "t/ImagePrompts"


def test_txt_upload_stays_in_guides(library):
    svc, _ = library
    result = svc.upload([("guide.md", io.BytesIO(b"# Guide"))], "g")
    assert result["saved"][0]["ref"].startswith("g/")
    assert result["rerouted"] == []


def test_image_upload_into_templates_reroutes(library):
    svc, _ = library
    result = svc.upload([("photo.png", io.BytesIO(b"png-bytes"))], "t")
    assert result["saved"][0]["ref"].startswith("i/")
    assert result["saved"][0]["cat"] == "i"
    assert len(result["rerouted"]) == 1


def test_read_text_accepts_templates_letter(library):
    svc, _ = library
    ref = svc.upload([("tpl.txt", io.BytesIO("A {subject} at {location}".encode()))], "t")["saved"][0]["ref"]
    text = svc.read_text(ref)
    assert "{subject}" in text["content"]
    assert text["ext"] == "txt"


def test_tree_exposes_templates_category(library):
    svc, _ = library
    svc.upload([("tpl.txt", io.BytesIO(b"x"))], "t")
    letters = [node.get("letter") for node in svc.get_tree()]
    assert "t" in letters


def test_create_text_asset(library):
    svc, _ = library
    entry = svc.create_text("t/Image Prompts", "Cinematic Shot", "{subject} at {location}")
    assert entry["ref"].startswith("t/")
    assert entry["type"] == "text"
    assert svc.read_text(entry["ref"])["content"] == "{subject} at {location}"


def test_create_text_rejects_non_text_category(library):
    svc, _ = library
    with pytest.raises(ValueError):
        svc.create_text("i", "Nope", "x")


def test_create_text_requires_title(library):
    svc, _ = library
    with pytest.raises(ValueError):
        svc.create_text("t", "  ", "x")


def test_write_text_round_trip(library):
    svc, _ = library
    entry = svc.create_text("g/Notes", "Note", "first")
    updated = svc.write_text(entry["ref"], "second {placeholder}")
    assert updated["content"] == "second {placeholder}"
    assert svc.read_text(entry["ref"])["content"] == "second {placeholder}"


def test_write_text_rejects_non_text_asset(library):
    svc, _ = library
    entry = svc.upload([("photo.png", io.BytesIO(b"png"))], "i")["saved"][0]
    with pytest.raises(ValueError):
        svc.write_text(entry["ref"], "x")


def test_expand_template_inlines_reference(library):
    svc, _ = library
    style = svc.create_text("t/Styles", "Style", "{Style:Studio Ghibli|3D Pixar}")
    parent = svc.create_text("t", "Scene", "{@Styles\\Style}, {subject} walking")
    expanded = svc.expand_template(parent["ref"])
    assert expanded["content"] == "{Style:Studio Ghibli|3D Pixar}, {subject} walking"
    assert expanded["title"] == "Scene"
    assert style["ref"].startswith("t/")


def test_expand_template_is_recursive(library):
    svc, _ = library
    svc.create_text("t/Styles", "Mood", "{Mood:calm|tense}")
    svc.create_text("t/Styles", "Style", "{@Styles\\Mood}, {Style:Ghibli|Pixar}")
    parent = svc.create_text("t", "Deep", "{@Styles\\Style} — {subject}")
    expanded = svc.expand_template(parent["ref"])
    assert expanded["content"] == "{Mood:calm|tense}, {Style:Ghibli|Pixar} — {subject}"


def test_expand_template_unresolved_reference_stays_literal(library):
    svc, _ = library
    parent = svc.create_text("t", "Broken", "{@Styles\\Missing} and {subject}")
    expanded = svc.expand_template(parent["ref"])
    assert expanded["content"] == "{@Styles\\Missing} and {subject}"


def test_expand_template_detects_cycles(library):
    svc, _ = library
    a = svc.create_text("t", "A", "A({@B})")
    b = svc.create_text("t", "B", "B({@A})")
    assert "B(" in svc.expand_template(a["ref"])["content"]
    assert "A(" in svc.expand_template(b["ref"])["content"]


def test_expand_template_forward_slash_reference(library):
    svc, _ = library
    svc.create_text("t/Styles", "Style", "{Style:Ghibli}")
    parent = svc.create_text("t", "Slash", "{@Styles/Style}, done")
    assert svc.expand_template(parent["ref"])["content"] == "{Style:Ghibli}, done"


def test_asset_folder_name():
    from web_ui.backend.services.asset_generation import asset_folder_name

    assert asset_folder_name("i", ["Characters", "City"]) == "Assets Images Characters City"
    assert asset_folder_name("t", ["Image Prompts"]) == "Assets Templates Image Prompts"
    assert asset_folder_name("v", []) == "Assets Videos"


class _FakeQueue:
    def __init__(self):
        self.items = []

    def add_items(self, items):
        self.items.extend(items)
        return items


def _asset_request(**overrides):
    from types import SimpleNamespace

    defaults = dict(
        kind="image", prompt="a car", cat="i/Characters", library=None,
        title=None, mode="comfyui", workflow=None, aspect_ratio="16:9",
        seed=None, duration=None, image_ref=None, video_ref=None,
        reference_refs=None, gemini_model=None, gemini_thinking=None,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_asset_image_start_enqueues_queue_item(tmp_path, monkeypatch):
    import asyncio
    from web_ui.backend.services import asset_generation as ag

    fake = _FakeQueue()
    monkeypatch.setattr(ag, "get_queue_service", lambda: fake)
    monkeypatch.setenv("ASSET_LIBRARY_DIRS", str(tmp_path))

    svc = ag.AssetGenerationService()
    status = asyncio.run(svc.start(_asset_request()))

    assert len(fake.items) == 1
    item = fake.items[0]
    assert item.generation_type.value == "asset_image"
    assert item.project_id == "__assets__"
    assert item.asset_gen_id == status["id"]
    assert item.prompt_override == "a car"
    assert item.image_mode == "comfyui"
    assert item.output_path.endswith(".png")
    assert status["queue_item_id"] == item.item_id
    assert status["status"] == "queued"
    # registry entry exists so the processor can mirror status immediately
    assert svc.get(status["id"])["status"] == "queued"
    # the processor reads the internal entry — it must carry the output path
    assert svc.get_internal(status["id"])["path"].endswith(".png")


def test_asset_video_start_enqueues_queue_item(tmp_path, monkeypatch):
    import asyncio
    from web_ui.backend.services import asset_generation as ag

    fake = _FakeQueue()
    monkeypatch.setattr(ag, "get_queue_service", lambda: fake)
    monkeypatch.setenv("ASSET_LIBRARY_DIRS", str(tmp_path))

    svc = ag.AssetGenerationService()
    status = asyncio.run(svc.start(_asset_request(
        kind="video", prompt="drive", cat="v", image_ref="i/abcdef01",
        reference_refs=["i/abcdef02", "i/abcdef03"],
    )))

    assert len(fake.items) == 1
    item = fake.items[0]
    assert item.generation_type.value == "asset_video"
    assert item.source_ref == "i/abcdef01"
    assert item.reference_refs == ["i/abcdef02", "i/abcdef03"]
    assert status["queue_item_id"] == item.item_id


def test_registry_mirrors_queue_settlement(tmp_path, monkeypatch):
    import asyncio
    from web_ui.backend.services import asset_generation as ag

    fake = _FakeQueue()
    monkeypatch.setattr(ag, "get_queue_service", lambda: fake)
    monkeypatch.setenv("ASSET_LIBRARY_DIRS", str(tmp_path))

    svc = ag.AssetGenerationService()
    status = asyncio.run(svc.start(_asset_request()))
    gen_id = status["id"]

    svc.mark_running(gen_id)
    svc.set_progress(gen_id, 40)
    assert svc.get(gen_id)["status"] == "running"
    assert svc.get(gen_id)["progress"] == 40
    svc.finalize_success(gen_id)
    assert svc.get(gen_id)["status"] == "completed"

    # finalize guards: a cancelled run never flips back to completed
    status2 = asyncio.run(svc.start(_asset_request(title="Second")))
    gen2 = status2["id"]
    svc.finalize_cancelled(gen2)
    svc.finalize_success(gen2)
    assert svc.get(gen2)["status"] == "cancelled"
