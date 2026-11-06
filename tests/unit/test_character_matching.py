"""
Unit tests for tolerant character-name matching between the story cast and
shot/scene data.

The story pass-2 LLM names top-level characters with display qualifiers
("Chi She (Red Snake)") while scenes and shots carry short forms
("Chi She"). These tests cover the shared resolver in
core.character_matching and its consumers:

- resolve/normalize tiers: exact, normalized, word containment, ambiguity
- ProjectManager.sync_character_asset_refs: short-form shot names attach
  refs and get canonicalized to story display names
- ProjectManager.sync_shot_video_refs: same for r2v character sheets and
  props
- r2v_composer voice-text binding for short-form names
- scene cast canonicalization used by the shot planner
"""
import json
import os
import sys

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.character_matching import (
    canonicalize_name_list,
    canonicalize_scene_cast,
    normalize_character_key,
    resolve_character_name,
)
from core.project_manager import ProjectManager
from core.r2v_composer import _voice_texts_for_shot


CAST = ["Bai Suzhen (White Snake)", "Xiao Qing (Green Snake)", "Chi She (Red Snake)"]


# ---------------------------------------------------------------- normalize

class TestNormalizeCharacterKey:
    def test_strips_parenthesized_qualifier(self):
        assert normalize_character_key("Chi She (Red Snake)") == "chi she"

    def test_case_and_punctuation(self):
        assert normalize_character_key("  Chi_She!! ") == "chi she"

    def test_cjk_survives(self):
        assert normalize_character_key("白素贞（白蛇）") == "白素贞"

    def test_empty(self):
        assert normalize_character_key(None) == ""
        assert normalize_character_key("   ") == ""


# ----------------------------------------------------------------- resolve

class TestResolveCharacterName:
    def test_exact_match(self):
        assert resolve_character_name("Chi She (Red Snake)", CAST) == "Chi She (Red Snake)"

    def test_case_insensitive_exact(self):
        assert resolve_character_name("chi she (red snake)", CAST) == "Chi She (Red Snake)"

    def test_short_form_resolves_to_qualified_display_name(self):
        # The project_20261031_093759 regression: shots say "Chi She",
        # the story cast says "Chi She (Red Snake)"
        assert resolve_character_name("Chi She", CAST) == "Chi She (Red Snake)"
        assert resolve_character_name("Bai Suzhen", CAST) == "Bai Suzhen (White Snake)"
        assert resolve_character_name("Xiao Qing", CAST) == "Xiao Qing (Green Snake)"

    def test_normalized_qualifier_only_form_resolves(self):
        # Shot carries just the qualifier ("Red Snake") — also unambiguous
        assert resolve_character_name("red snake", CAST) == "Chi She (Red Snake)"

    def test_ambiguous_qualifier_returns_none(self):
        # Two casts share the word "Snake" beyond the distinct qualifiers —
        # "Snake" alone must not attach to either
        cast = ["White Snake", "Green Snake"]
        assert resolve_character_name("Snake", cast) is None

    def test_unknown_name_returns_none(self):
        assert resolve_character_name("Xu Xian", CAST) is None

    def test_empty_inputs(self):
        assert resolve_character_name("", CAST) is None
        assert resolve_character_name(None, CAST) is None
        assert resolve_character_name("Chi She", []) is None
        assert resolve_character_name("Chi She", None) is None


# ----------------------------------------------------------- canonicalize

class TestCanonicalizeNameList:
    def test_rewrites_resolved_names_keeps_unknown(self):
        canonical, changed = canonicalize_name_list(
            ["Chi She", "Xu Xian", "bai suzhen"], CAST)
        assert canonical == ["Chi She (Red Snake)", "Xu Xian", "Bai Suzhen (White Snake)"]
        assert changed is True

    def test_no_change_when_all_exact(self):
        canonical, changed = canonicalize_name_list(["Chi She (Red Snake)"], CAST)
        assert canonical == ["Chi She (Red Snake)"]
        assert changed is False

    def test_drops_blank_entries(self):
        assert canonicalize_name_list(["Chi She", "", "  "], CAST)[0] == \
            ["Chi She (Red Snake)"]


class TestCanonicalizeSceneCast:
    def test_characters_string_canonicalized(self):
        scene = {"characters": "Bai Suzhen, Xiao Qing, Chi She"}
        canonicalize_scene_cast(scene, CAST)
        assert scene["characters"] == \
            "Bai Suzhen (White Snake), Xiao Qing (Green Snake), Chi She (Red Snake)"

    def test_characters_list_canonicalized(self):
        scene = {"characters": ["Chi She"]}
        canonicalize_scene_cast(scene, CAST)
        assert scene["characters"] == ["Chi She (Red Snake)"]

    def test_props_use_prop_names_not_cast(self):
        scene = {"characters": "Chi She", "props": ["Sword", "Unknown Prop"]}
        canonicalize_scene_cast(scene, CAST, ["Blood Sword"])
        assert scene["characters"] == "Chi She (Red Snake)"
        # "Sword" is a distinct word subset of "Blood Sword" — resolves;
        # unknown props are kept verbatim
        assert scene["props"] == ["Blood Sword", "Unknown Prop"]

    def test_noop_without_cast(self):
        scene = {"characters": "Chi She"}
        canonicalize_scene_cast(scene, [])
        assert scene["characters"] == "Chi She"


# ------------------------------------------------------------ sync fixtures

@pytest.fixture
def projects_dir(tmp_path):
    d = tmp_path / "projects"
    d.mkdir()
    return str(d)


def _make_project(pm, projects_dir, project_id, vgt="i2v"):
    pm.create_project("test idea", project_id=project_id, video_generation_type=vgt)
    pdir = os.path.join(projects_dir, project_id)
    os.makedirs(os.path.join(pdir, "images"), exist_ok=True)
    os.makedirs(os.path.join(pdir, "backgrounds"), exist_ok=True)
    return pdir


def _write_story(projects_dir, project_id, story):
    with open(os.path.join(projects_dir, project_id, "story.json"), "w", encoding="utf-8") as f:
        json.dump(story, f)


def _write_shots(projects_dir, project_id, shots):
    with open(os.path.join(projects_dir, project_id, "shots.json"), "w", encoding="utf-8") as f:
        json.dump(shots, f)


def _read_shots(projects_dir, project_id):
    with open(os.path.join(projects_dir, project_id, "shots.json"), encoding="utf-8") as f:
        return json.load(f)


def _touch(projects_dir, project_id, media_dir, filename):
    path = os.path.join(projects_dir, project_id, media_dir, filename)
    with open(path, "wb") as f:
        f.write(b"x")
    return f"output/projects/{project_id}/{media_dir}/{filename}"


def _shot(index, **kw):
    shot = {
        "id": f"shot_{index:03d}", "index": index, "duration": 5,
        "image_prompt": "prompt", "scene_id": 0,
        "characters": [], "props": [],
        "reference_asset_ids": [],
    }
    shot.update(kw)
    return shot


def _snake_story(projects_dir, pid):
    white = _touch(projects_dir, pid, "images", "character_00_001.png")
    green = _touch(projects_dir, pid, "images", "character_01_001.png")
    red = _touch(projects_dir, pid, "images", "character_02_001.png")
    return {
        "characters": [
            {"name": "Bai Suzhen (White Snake)", "character_reference_image_path": white},
            {"name": "Xiao Qing (Green Snake)", "character_reference_image_path": green},
            {"name": "Chi She (Red Snake)", "character_reference_image_path": red},
        ],
        "scenes": [{"scene_id": 0, "location": "temple"}],
    }


# ----------------------------------------------- sync_character_asset_refs

class TestSyncCharacterAssetRefsShortNames:
    def test_short_form_shot_names_attach_refs_and_canonicalize(self, projects_dir):
        pm = ProjectManager(projects_dir=projects_dir)
        pid = "project_snake_i2v"
        _make_project(pm, projects_dir, pid, vgt="i2v")
        story = _snake_story(projects_dir, pid)
        _write_story(projects_dir, pid, story)

        # Shot 4 of project_20261031_093759: characters=["Chi She"] while the
        # cast entry is "Chi She (Red Snake)"
        shot4 = _shot(4, characters=["Chi She"])
        shot1 = _shot(1, characters=["Bai Suzhen", "Xiao Qing"])
        _write_shots(projects_dir, pid, [shot1, shot4])

        updated = pm.sync_character_asset_refs(pid)
        assert updated == 2
        shots = _read_shots(projects_dir, pid)
        assert shots[0]["characters"] == ["Bai Suzhen (White Snake)", "Xiao Qing (Green Snake)"]
        assert shots[0]["reference_asset_ids"] == [
            f"p/{pid}/images/character_00_001.png",
            f"p/{pid}/images/character_01_001.png",
        ]
        assert shots[1]["characters"] == ["Chi She (Red Snake)"]
        assert shots[1]["reference_asset_ids"] == [
            f"p/{pid}/images/character_02_001.png",
        ]

    def test_idempotent_on_second_sync(self, projects_dir):
        pm = ProjectManager(projects_dir=projects_dir)
        pid = "project_snake_i2v2"
        _make_project(pm, projects_dir, pid, vgt="i2v")
        _write_story(projects_dir, pid, _snake_story(projects_dir, pid))
        _write_shots(projects_dir, pid, [_shot(4, characters=["Chi She"])])

        assert pm.sync_character_asset_refs(pid) == 1
        assert pm.sync_character_asset_refs(pid) == 0
        shots = _read_shots(projects_dir, pid)
        assert shots[0]["characters"] == ["Chi She (Red Snake)"]

    def test_unresolvable_names_kept_verbatim_without_refs(self, projects_dir):
        pm = ProjectManager(projects_dir=projects_dir)
        pid = "project_snake_i2v3"
        _make_project(pm, projects_dir, pid, vgt="i2v")
        _write_story(projects_dir, pid, _snake_story(projects_dir, pid))
        _write_shots(projects_dir, pid, [_shot(2, characters=["Xu Xian"])])

        updated = pm.sync_character_asset_refs(pid)
        shots = _read_shots(projects_dir, pid)
        assert shots[0]["characters"] == ["Xu Xian"]
        assert shots[0]["reference_asset_ids"] == []
        # The shot changed only if something attached; nothing did, and the
        # name was already canonical (unresolved kept verbatim)
        assert updated == 0

    def test_prompt_matching_still_discovers_unattributed_shots(self, projects_dir):
        pm = ProjectManager(projects_dir=projects_dir)
        pid = "project_snake_i2v4"
        _make_project(pm, projects_dir, pid, vgt="i2v")
        white = _touch(projects_dir, pid, "images", "character_00_001.png")
        red = _touch(projects_dir, pid, "images", "character_02_001.png")
        _write_story(projects_dir, pid, {
            "characters": [
                # cast without a word shared across names — the single-word
                # fallback in _name_in_prompt otherwise cross-matches
                {"name": "Bai Suzhen (White Snake)", "character_reference_image_path": white},
                {"name": "Chi She", "character_reference_image_path": red},
            ],
            "scenes": [{"scene_id": 0, "location": "temple"}],
        })
        _write_shots(projects_dir, pid, [
            _shot(3, image_prompt="Chi She towers over the cracked altar, eyes glowing crimson."),
        ])

        updated = pm.sync_character_asset_refs(pid)
        assert updated == 1
        shots = _read_shots(projects_dir, pid)
        assert shots[0]["characters"] == ["Chi She"]
        assert shots[0]["reference_asset_ids"] == [f"p/{pid}/images/character_02_001.png"]


# ------------------------------------------------- sync_shot_video_refs

class TestSyncShotVideoRefsShortNames:
    def test_short_form_character_and_prop_names_attach(self, projects_dir):
        pm = ProjectManager(projects_dir=projects_dir)
        pid = "project_snake_r2v"
        _make_project(pm, projects_dir, pid, vgt="r2v")
        story = _snake_story(projects_dir, pid)
        prop_sheet = _touch(projects_dir, pid, "images", "prop_00_001.png")
        bg_sheet = _touch(projects_dir, pid, "backgrounds", "background_000_001.png")
        story["props"] = [{"name": "Jade Teapot", "reference_image_path": prop_sheet}]
        story["scenes"][0]["background_image_path"] = bg_sheet
        _write_story(projects_dir, pid, story)

        shot4 = _shot(4, characters=["Chi She"], props=["jade teapot"])
        _write_shots(projects_dir, pid, [shot4])

        updated = pm.sync_shot_video_refs(pid)
        assert updated == 1
        shots = _read_shots(projects_dir, pid)
        # Priority order: character sheet -> background -> prop sheet
        assert shots[0]["reference_asset_ids"] == [
            f"p/{pid}/images/character_02_001.png",
            f"p/{pid}/backgrounds/background_000_001.png",
            f"p/{pid}/images/prop_00_001.png",
        ]
        assert shots[0]["characters"] == ["Chi She (Red Snake)"]
        assert shots[0]["props"] == ["Jade Teapot"]

    def test_idempotent_and_names_canonicalized_once(self, projects_dir):
        pm = ProjectManager(projects_dir=projects_dir)
        pid = "project_snake_r2v2"
        _make_project(pm, projects_dir, pid, vgt="r2v")
        _write_story(projects_dir, pid, _snake_story(projects_dir, pid))
        _write_shots(projects_dir, pid, [_shot(4, characters=["Chi She"])])

        assert pm.sync_shot_video_refs(pid) == 1
        assert pm.sync_shot_video_refs(pid) == 0
        shots = _read_shots(projects_dir, pid)
        assert shots[0]["characters"] == ["Chi She (Red Snake)"]


# ------------------------------------------------------- r2v voice texts

class TestVoiceTextsForShot:
    def test_short_form_name_binds_voice(self):
        story = {"characters": [
            {"name": "Chi She (Red Snake)", "voice": {"text": "a gravelly roar"}},
            {"name": "Bai Suzhen (White Snake)", "voice": {"text": "a serene tone"}},
        ]}
        shot = {"characters": ["Chi She"]}
        assert _voice_texts_for_shot(shot, story) == \
            [("Chi She (Red Snake)", "a gravelly roar")]

    def test_exact_name_still_binds(self):
        story = {"characters": [
            {"name": "Chi She (Red Snake)", "voice": {"text": "a gravelly roar"}},
        ]}
        shot = {"characters": ["Chi She (Red Snake)"]}
        assert _voice_texts_for_shot(shot, story) == \
            [("Chi She (Red Snake)", "a gravelly roar")]

    def test_character_name_fallback(self):
        story = {"characters": [
            {"name": "Chi She (Red Snake)", "voice": {"text": "a gravelly roar"}},
        ]}
        shot = {"character_name": "chi she"}
        assert _voice_texts_for_shot(shot, story) == \
            [("Chi She (Red Snake)", "a gravelly roar")]

    def test_no_voice_or_no_match(self):
        story = {"characters": [{"name": "Chi She (Red Snake)"}]}
        assert _voice_texts_for_shot({"characters": ["Chi She"]}, story) == []
        story2 = {"characters": [
            {"name": "Chi She (Red Snake)", "voice": {"text": "x"}}]}
        assert _voice_texts_for_shot({"characters": ["Xu Xian"]}, story2) == []
