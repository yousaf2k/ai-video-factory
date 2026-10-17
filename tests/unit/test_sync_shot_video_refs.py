"""
Unit tests for ProjectManager.sync_shot_video_refs and the core asset-ref
resolver (r2v pipeline).

Covers:
- priority fill order (characters -> background -> props) incl. shot
  `characters` list vs legacy `character_name` fallback
- idempotency, regeneration swap, manual/user refs preserved
- scoping: only r2v projects; FLFI2V shots untouched
- core.asset_refs: project ref + library ref resolution, image filtering
"""
import json
import os
import sys

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.project_manager import ProjectManager


@pytest.fixture
def projects_dir(tmp_path):
    d = tmp_path / "projects"
    d.mkdir()
    return str(d)


def _make_project(pm, projects_dir, project_id, vgt="r2v"):
    pm.create_project("test idea", project_id=project_id, video_generation_type=vgt)
    pdir = os.path.join(projects_dir, project_id)
    os.makedirs(os.path.join(pdir, "images"), exist_ok=True)
    os.makedirs(os.path.join(pdir, "backgrounds"), exist_ok=True)
    os.makedirs(os.path.join(pdir, "references"), exist_ok=True)
    return pdir


def _write_story(projects_dir, project_id, story):
    with open(os.path.join(projects_dir, project_id, "story.json"), "w", encoding="utf-8") as f:
        json.dump(story, f)


def _touch(projects_dir, project_id, media_dir, filename):
    path = os.path.join(projects_dir, project_id, media_dir, filename)
    with open(path, "wb") as f:
        f.write(b"x")
    return f"output/projects/{project_id}/{media_dir}/{filename}"


def _write_shots(projects_dir, project_id, shots):
    with open(os.path.join(projects_dir, project_id, "shots.json"), "w", encoding="utf-8") as f:
        json.dump(shots, f)


def _read_shots(projects_dir, project_id):
    with open(os.path.join(projects_dir, project_id, "shots.json"), encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def r2v_project(projects_dir):
    pm = ProjectManager(projects_dir=projects_dir)
    pid = "project_r2v"
    pdir = _make_project(pm, projects_dir, pid, vgt="r2v")

    baker_sheet = _touch(projects_dir, pid, "images", "character_00_001.png")
    daughter_sheet = _touch(projects_dir, pid, "images", "character_01_001.png")
    bg_sheet = _touch(projects_dir, pid, "backgrounds", "background_000_001.png")
    prop_sheet = _touch(projects_dir, pid, "references", "prop_00_001.png")

    _write_story(projects_dir, pid, {
        "characters": [
            {"name": "Baker", "character_reference_image_path": baker_sheet},
            {"name": "Daughter", "character_reference_image_path": daughter_sheet},
        ],
        "props": [{"name": "Bicycle", "reference_image_path": prop_sheet}],
        "scenes": [{"scene_id": 0, "location": "bakery", "background_image_path": bg_sheet}],
    })
    _write_shots(projects_dir, pid, [
        {"index": 1, "scene_id": 0, "characters": ["Baker", "Daughter"], "props": ["Bicycle"]},
        {"index": 2, "scene_id": 0, "character_name": "Baker"},  # legacy single-name field
        {"index": 3, "scene_id": 0, "characters": ["Baker"], "is_flfi2v": True},
    ])
    return pm, pid


class TestSyncShotVideoRefs:
    def test_priority_fill_order(self, r2v_project, projects_dir):
        pm, pid = r2v_project
        updated = pm.sync_shot_video_refs(pid)
        assert updated == 2  # shots 1+2; the FLFI2V shot is skipped by design
        shots = _read_shots(projects_dir, pid)
        # characters (in shot order) -> background -> props
        assert shots[0]["reference_asset_ids"] == [
            f"p/{pid}/images/character_00_001.png",
            f"p/{pid}/images/character_01_001.png",
            f"p/{pid}/backgrounds/background_000_001.png",
            f"p/{pid}/references/prop_00_001.png",
        ]
        # legacy character_name fallback works; no props listed
        assert shots[1]["reference_asset_ids"] == [
            f"p/{pid}/images/character_00_001.png",
            f"p/{pid}/backgrounds/background_000_001.png",
        ]
        # FLFI2V shots untouched
        assert "reference_asset_ids" not in shots[2]

    def test_idempotent(self, r2v_project):
        pm, pid = r2v_project
        assert pm.sync_shot_video_refs(pid) == 2
        assert pm.sync_shot_video_refs(pid) == 0  # second run changes nothing

    def test_user_refs_preserved_and_swap(self, r2v_project, projects_dir):
        pm, pid = r2v_project
        user_ref = "i/deadbeef"
        shots = _read_shots(projects_dir, pid)
        shots[0]["reference_asset_ids"] = [user_ref]
        _write_shots(projects_dir, pid, shots)

        pm.sync_shot_video_refs(pid)
        shots = _read_shots(projects_dir, pid)
        # user ref kept in position, synced refs appended
        assert shots[0]["reference_asset_ids"][0] == user_ref
        assert len(shots[0]["reference_asset_ids"]) == 5

        # regenerating a character sheet swaps the ref instead of accumulating
        new_sheet = _touch(projects_dir, pid, "images", "character_00_002.png")
        pm.update_story_safely(pid, lambda s: s["characters"][0].__setitem__(
            "character_reference_image_path", new_sheet))
        pm.sync_shot_video_refs(pid)
        shots = _read_shots(projects_dir, pid)
        refs = shots[0]["reference_asset_ids"]
        assert refs[1] == f"p/{pid}/images/character_00_002.png"
        assert refs.count(f"p/{pid}/images/character_00_001.png") == 0
        assert user_ref in refs and len(refs) == 5

    def test_skips_non_r2v_projects(self, projects_dir):
        pm = ProjectManager(projects_dir=projects_dir)
        pid = "project_i2v"
        _make_project(pm, projects_dir, pid, vgt="i2v")
        _write_story(projects_dir, pid, {
            "characters": [{"name": "Baker", "character_reference_image_path": "x"}],
        })
        _write_shots(projects_dir, pid, [{"index": 1, "scene_id": 0, "character_name": "Baker"}])
        assert pm.sync_shot_video_refs(pid) == 0


class TestAssetRefs:
    def test_project_ref_resolution(self, r2v_project, projects_dir, monkeypatch):
        import config
        monkeypatch.setattr(config, "ABS_PROJECTS_DIR", projects_dir)
        from core.asset_refs import resolve_ref, resolve_refs_to_paths, resolve_shot_video_reference_paths

        pid = "project_r2v"
        path = resolve_ref(f"p/{pid}/images/character_00_001.png")
        assert path == os.path.join(projects_dir, pid, "images", "character_00_001.png")

        # missing files drop out, order preserved
        paths = resolve_refs_to_paths([
            f"p/{pid}/images/character_00_001.png",
            f"p/{pid}/images/does_not_exist.png",
            f"p/{pid}/backgrounds/background_000_001.png",
        ])
        assert len(paths) == 2

        # shot helper filters to images and caps at max_refs
        shot = {"reference_asset_ids": [
            f"p/{pid}/images/character_00_001.png",
            f"p/{pid}/backgrounds/background_000_001.png",
        ]}
        assert len(resolve_shot_video_reference_paths(shot, max_refs=1)) == 1

    def test_library_ref_resolution(self, tmp_path, monkeypatch):
        import config
        lib = tmp_path / "MyLib"
        (lib / "Images" / "props").mkdir(parents=True)
        target = lib / "Images" / "props" / "9f3ab21c-Red Mustang.png"
        target.write_bytes(b"x")
        monkeypatch.setattr(config, "get_asset_library_dirs", lambda: [str(tmp_path / "MyLib")])

        from core.asset_refs import resolve_ref
        assert resolve_ref("i/9f3ab21c") == str(target)
        assert resolve_ref("mylib/i/9f3ab21c") == str(target)  # slug match is case-insensitive
        assert resolve_ref("i/00000000") is None
