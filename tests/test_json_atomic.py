"""
Offline regression tests for lock-protected, atomic JSON read-modify-write.

Covers the reported bug: two parallel image generations updating shots.json —
the second completion must never overwrite the first one's update, because
every writer re-reads the latest file from disk inside the lock (no stale
in-memory snapshot write-backs) and every write is atomic (temp + os.replace).
"""
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import uuid

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import json_atomic
from core.json_atomic import atomic_write_json, file_lock, read_json, update_json
from core.project_manager import ProjectManager


@pytest.fixture()
def projects_dir():
    d = os.path.join(tempfile.gettempdir(), f"pm_test_{uuid.uuid4().hex[:8]}")
    os.makedirs(d, exist_ok=True)
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture()
def pm(projects_dir):
    return ProjectManager(projects_dir=projects_dir)


@pytest.fixture()
def project_id(pm):
    pid, _ = pm.create_project("test idea", project_id=f"project_{uuid.uuid4().hex[:8]}")
    return pid


def _make_shots(pm, project_id, count=3):
    shots = [{"id": f"shot{i:03d}", "image_prompt": f"prompt {i}"} for i in range(1, count + 1)]
    pm.save_shots(project_id, shots)
    return pm.get_shots(project_id)


# =====================================================================
# json_atomic primitives
# =====================================================================

class TestAtomicWrite:
    def test_roundtrip_unicode(self, tmp_path):
        path = str(tmp_path / "data.json")
        data = {"title": "绿灯侠", "nested": {"items": [1, 2, 3]}}
        atomic_write_json(path, data)
        assert read_json(path) == data

    def test_no_temp_files_left_behind(self, tmp_path):
        path = str(tmp_path / "data.json")
        atomic_write_json(path, {"a": 1})
        atomic_write_json(path, {"a": 2})
        leftovers = [f for f in os.listdir(tmp_path) if ".tmp-" in f]
        assert leftovers == []
        assert read_json(path) == {"a": 2}

    def test_read_json_missing_returns_default(self, tmp_path):
        assert read_json(str(tmp_path / "nope.json"), default=[]) == []
        assert read_json(str(tmp_path / "nope.json")) is None

    def test_read_json_corrupt_returns_default(self, tmp_path):
        path = str(tmp_path / "bad.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write("{not valid json")
        assert read_json(path, default={}) == {}


class TestFileLock:
    def test_mutual_exclusion_between_threads(self, tmp_path):
        lock_path = str(tmp_path / ".lock")
        counter = {"value": 0}
        errors = []

        def worker():
            for _ in range(50):
                try:
                    with file_lock(lock_path, timeout=10):
                        current = counter["value"]
                        time.sleep(0.001)  # widen the race window
                        counter["value"] = current + 1
                except Exception as e:  # pragma: no cover
                    errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert counter["value"] == 200
        assert not os.path.exists(lock_path)  # released

    def test_reentrant_within_thread(self, tmp_path):
        lock_path = str(tmp_path / ".lock")
        with file_lock(lock_path, timeout=5):
            with file_lock(lock_path, timeout=5):  # must not deadlock
                pass
        # Outer release removed the lock dir
        assert not os.path.exists(lock_path)

    def test_nested_project_lock_and_transaction(self, pm, project_id):
        """assets.py pattern: hold lock_project() then call update_shots_safely()."""
        _make_shots(pm, project_id, 2)
        with pm.lock_project(project_id):
            pm.update_shots_safely(
                project_id, lambda shots: shots[0].update({"image_generated": True})
            )
        shots = pm.get_shots(project_id)
        assert shots[0]["image_generated"] is True

    def test_stale_lock_is_recovered(self, tmp_path):
        lock_path = str(tmp_path / ".lock")
        os.makedirs(lock_path)
        # Backdate the lock beyond the stale threshold
        stale_time = time.time() - 3600
        os.utime(lock_path, (stale_time, stale_time))

        acquired = {"ok": False}

        def grab():
            with file_lock(lock_path, timeout=5, stale_after=10):
                acquired["ok"] = True

        t = threading.Thread(target=grab)
        t.start()
        t.join(timeout=10)
        assert acquired["ok"], "stale lock was not recovered"


class TestUpdateJson:
    def test_concurrent_increments_all_land(self, tmp_path):
        path = str(tmp_path / "counters.json")
        atomic_write_json(path, {"a": 0, "b": 0})

        def bump(field):
            for _ in range(25):
                def modify(data):
                    data[field] += 1
                update_json(path, modify, default={"a": 0, "b": 0})

        threads = [
            threading.Thread(target=bump, args=("a",)),
            threading.Thread(target=bump, args=("a",)),
            threading.Thread(target=bump, args=("b",)),
            threading.Thread(target=bump, args=("b",)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert read_json(path) == {"a": 50, "b": 50}

    def test_missing_file_uses_default(self, tmp_path):
        path = str(tmp_path / "new.json")

        def modify(data):
            data["created"] = True
            return data

        result = update_json(path, modify, default={"created": False})
        assert result == {"created": True}
        assert read_json(path) == {"created": True}


# =====================================================================
# ProjectManager — the reported bug scenario
# =====================================================================

class TestParallelImageGenerationUpdates:
    def test_two_parallel_generations_both_survive(self, pm, project_id):
        """
        Exact reported bug: two image generations complete in parallel.
        Each completion updates its own shot; the second writer must see the
        first writer's update because it re-reads shots.json inside the lock.
        """
        _make_shots(pm, project_id, 2)

        def complete_generation(shot_id, image_path):
            # Simulate generation latency, then mark like the queue worker does
            time.sleep(0.05)
            pm.update_shot_metadata(
                project_id,
                {"image_generated": True, "image_path": image_path},
                shot_id=shot_id,
            )

        t1 = threading.Thread(
            target=complete_generation, args=("shot001", "output/projects/p/images/shot_001_001.png")
        )
        t2 = threading.Thread(
            target=complete_generation, args=("shot002", "output/projects/p/images/shot_002_001.png")
        )
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        shots = pm.get_shots(project_id)
        by_id = {s["id"]: s for s in shots}
        assert by_id["shot001"]["image_generated"] is True
        assert by_id["shot001"]["image_path"]
        assert by_id["shot002"]["image_generated"] is True
        assert by_id["shot002"]["image_path"]

        meta = pm.load_project(project_id)
        assert meta["stats"]["images_generated"] == 2

    def test_repeated_concurrent_updates_never_lose_writes(self, pm, project_id):
        """Stress: 4 threads × 15 updates to distinct shots — all must land."""
        _make_shots(pm, project_id, 4)
        errors = []

        def worker(shot_id):
            for i in range(15):
                try:
                    pm.update_shot_metadata(
                        project_id,
                        {"image_generated": True, "image_path": f"img/{shot_id}_{i}.png"},
                        shot_id=shot_id,
                    )
                except Exception as e:  # pragma: no cover
                    errors.append(e)

        threads = [
            threading.Thread(target=worker, args=(f"shot{i:03d}",)) for i in range(1, 5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        shots = pm.get_shots(project_id)
        by_id = {s["id"]: s for s in shots}
        for i in range(1, 5):
            assert by_id[f"shot{i:03d}"]["image_generated"] is True
        meta = pm.load_project(project_id)
        assert meta["stats"]["images_generated"] == 4

    def test_stale_snapshot_append_does_not_drop_others(self, pm, project_id):
        """
        The old FLFI2V pattern: a writer holding a stale shot dict must not be
        able to clobber a path another writer appended in the meantime.
        append_shot_media_paths dedupes against the FRESH list inside the lock.
        """
        _make_shots(pm, project_id, 1)

        # Writer A appends its path
        pm.append_shot_media_paths(
            project_id, ["output/projects/p/images/shot_001_then_001.png"], shot_id="shot001"
        )

        # Writer B appends a different path "from a stale snapshot" — must not
        # remove writer A's entry
        pm.append_shot_media_paths(
            project_id, ["output/projects/p/images/shot_001_now_001.png"], shot_id="shot001"
        )

        # Re-appending an existing path (different slash style) must not duplicate
        pm.append_shot_media_paths(
            project_id, ["output/projects/p/images/shot_001_then_001.png"], shot_id="shot001"
        )

        shot = pm.get_shots(project_id)[0]
        basenames = [os.path.basename(p) for p in shot["image_paths"]]
        assert basenames == ["shot_001_then_001.png", "shot_001_now_001.png"]

    def test_concurrent_appends_all_survive(self, pm, project_id):
        _make_shots(pm, project_id, 1)
        paths = [f"output/projects/p/images/shot_001_v{i:03d}.png" for i in range(10)]
        threads = [
            threading.Thread(
                target=pm.append_shot_media_paths, args=(project_id, [p]), kwargs={"shot_id": "shot001"}
            )
            for p in paths
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        shot = pm.get_shots(project_id)[0]
        assert len(shot["image_paths"]) == 10


class TestParallelStoryUpdates:
    def test_two_character_completions_both_survive(self, pm, project_id):
        """
        Old bug pattern on story.json: two parallel character-image completions
        each wrote the whole story.json from their own stale snapshot, wiping
        the other's character_reference_image_path. update_story_safely fixes it.
        """
        story = {
            "title": "t",
            "characters": [
                {"name": "Alice", "image_prompt": "a"},
                {"name": "Bob", "image_prompt": "b"},
            ],
            "scenes": [],
        }
        atomic_write_json(os.path.join(pm.get_project_dir(project_id), "story.json"), story)

        def complete_character(index, path):
            time.sleep(0.05)

            def apply(story_data):
                story_data["characters"][index]["character_reference_image_path"] = path

            pm.update_story_safely(project_id, apply)

        t1 = threading.Thread(target=complete_character, args=(0, "output/projects/p/refs/a.png"))
        t2 = threading.Thread(target=complete_character, args=(1, "output/projects/p/refs/b.png"))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        final = pm.get_story(project_id)
        chars = final["characters"]
        assert chars[0]["character_reference_image_path"] == "output/projects/p/refs/a.png"
        assert chars[1]["character_reference_image_path"] == "output/projects/p/refs/b.png"

    def test_update_story_safely_missing_story_returns_none(self, pm, project_id):
        assert pm.update_story_safely(project_id, lambda s: None) is None


class TestAtomicProjectWrites:
    def test_save_shots_full_write_is_locked_and_atomic(self, pm, project_id):
        """save_shots (full replacement for replanning) writes valid JSON and updates stats."""
        _make_shots(pm, project_id, 2)
        new_shots = [{"id": "x1", "image_prompt": "p"}, {"id": "x2", "image_prompt": "q"}]
        pm.save_shots(project_id, new_shots)

        shots = pm.get_shots(project_id)
        assert [s["id"] for s in shots] == ["x1", "x2"]
        assert pm.load_project(project_id)["stats"]["total_shots"] == 2
        # No temp leftovers in the project dir
        leftovers = [f for f in os.listdir(pm.get_project_dir(project_id)) if ".tmp-" in f]
        assert leftovers == []

    def test_meta_step_marks_are_transactional(self, pm, project_id):
        _make_shots(pm, project_id, 1)
        # update_shot_metadata recomputes the meta stats in the same transaction
        pm.update_shot_metadata(
            project_id, {"image_generated": True, "image_path": "img/s1.png"}, shot_id="shot001"
        )
        pm.mark_step_complete(project_id, "images")

        meta = pm.load_project(project_id)
        assert meta["steps"]["images"] is True
        shots = pm.get_shots(project_id)
        assert shots[0]["image_generated"] is True
        assert meta["stats"]["images_generated"] == 1

    def test_cross_process_lock_mutual_exclusion(self, pm, project_id, projects_dir):
        """
        Simulate a second process: a subprocess acquires the same project lock
        while the parent holds it — the subprocess must wait, not corrupt.
        """
        _make_shots(pm, project_id, 1)
        script = (
            "import sys, time, json\n"
            f"sys.path.insert(0, {os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))!r})\n"
            "from core.project_manager import ProjectManager\n"
            f"pm = ProjectManager(projects_dir={projects_dir!r})\n"
            "time.sleep(0.2)\n"
            "def modify(shots):\n"
            "    shots[0]['image_generated'] = True\n"
            f"pm.update_shots_safely({project_id!r}, modify)\n"
            "print('CHILD_DONE')\n"
        )

        results = {}

        def parent_writer():
            with pm.lock_project(project_id, timeout=10):
                time.sleep(0.6)  # hold the lock while the child tries to write
                def modify(shots):
                    shots[0]["video_rendered"] = True
                pm.update_shots_safely(project_id, modify)

        p = threading.Thread(target=parent_writer)
        p.start()
        import subprocess
        out = subprocess.run(
            [sys.executable, "-c", script], capture_output=True, text=True, timeout=30
        )
        p.join()
        results["child"] = out.stdout.strip()
        results["rc"] = out.returncode

        assert results["rc"] == 0, out.stderr
        assert results["child"] == "CHILD_DONE"
        shot = pm.get_shots(project_id)[0]
        assert shot["image_generated"] is True
        assert shot["video_rendered"] is True


# =====================================================================
# PUT /shots stale-client merge protection
# =====================================================================

class TestStaleClientMerge:
    """
    The shot editor PUTs its full shots list, which may be a snapshot fetched
    before parallel generations finished. merge_fresh_generation_status (used
    by the PUT /shots endpoint inside the lock) must restore backend-owned
    status fields from the fresh on-disk state so a stale save cannot wipe
    generation results, while client edits (prompts, index, inserts) stand.
    """

    @pytest.fixture()
    def merge(self):
        from web_ui.backend.api.shots import merge_fresh_generation_status
        return merge_fresh_generation_status

    def test_stale_save_does_not_wipe_image_result(self, merge):
        fresh = [{
            "id": "a1", "index": 1, "image_prompt": "old prompt",
            "image_generated": True, "image_path": "C:/out/images/shot_001_001.png",
            "image_paths": ["C:/out/images/shot_001_001.png"],
        }]
        # Client snapshot taken BEFORE the image finished
        incoming = [{
            "id": "a1", "index": 1, "image_prompt": "edited prompt",
            "image_generated": False, "image_path": None, "image_paths": [],
        }]
        merge(incoming, fresh, [])
        assert incoming[0]["image_generated"] is True
        assert incoming[0]["image_path"] == os.path.abspath("C:/out/images/shot_001_001.png")
        # Client-owned edit survives
        assert incoming[0]["image_prompt"] == "edited prompt"

    def test_concurrent_variation_preserved(self, merge):
        fresh = [{
            "id": "a1", "index": 1,
            "image_generated": True,
            "image_path": "C:/out/images/shot_001_002.png",
            "image_paths": [
                "C:/out/images/shot_001_001.png",
                "C:/out/images/shot_001_002.png",  # generated after client fetched
            ],
        }]
        incoming = [{
            "id": "a1", "index": 1,
            "image_generated": True,
            "image_path": "C:/out/images/shot_001_001.png",
            "image_paths": ["C:/out/images/shot_001_001.png"],
        }]
        merge(incoming, fresh, [])
        assert len(incoming[0]["image_paths"]) == 2
        assert incoming[0]["image_path"] == os.path.abspath("C:/out/images/shot_001_002.png")

    def test_renamed_path_is_preserved(self, merge):
        # Shot moved 1 -> 5: the endpoint renamed the file and rewrote the
        # client's path; the fresh on-disk state still has the OLD name.
        images_dir = "C:/out/images"
        fresh = [{
            "id": "a1", "index": 5,
            "image_generated": True, "image_path": f"{images_dir}/shot_001_001.png",
            "image_paths": [f"{images_dir}/shot_001_001.png"],
        }]
        incoming = [{
            "id": "a1", "index": 5, "image_generated": True,
            "image_path": f"{images_dir}/shot_005_001.png",
            "image_paths": [f"{images_dir}/shot_005_001.png"],
        }]
        renames = [(
            os.path.join(images_dir, "shot_001_001.png"),
            os.path.join(images_dir, "shot_005_001.png.tmp-x"),
            os.path.join(images_dir, "shot_005_001.png"),
        )]
        merge(incoming, fresh, renames)
        expected_new = os.path.abspath(os.path.join(images_dir, "shot_005_001.png"))
        assert incoming[0]["image_path"] == expected_new
        assert incoming[0]["image_paths"] == [expected_new]

    def test_inserted_shot_keeps_client_values(self, merge):
        fresh = [{"id": "a1", "index": 1, "image_generated": True,
                  "image_path": "C:/out/images/shot_001_001.png"}]
        incoming = [
            {"id": "a1", "index": 1, "image_generated": True,
             "image_path": "C:/out/images/shot_001_001.png"},
            {  # just inserted by the editor — no on-disk state
                "id": "zz9", "index": 2, "image_prompt": "new",
                "image_generated": False, "image_path": None,
            },
        ]
        merge(incoming, fresh, [])
        assert incoming[1]["image_generated"] is False
        assert incoming[1]["image_prompt"] == "new"

    def test_flfi2v_and_soundfx_fields_restored(self, merge):
        fresh = [{
            "id": "a1", "index": 1,
            "then_image_generated": True, "then_image_path": "C:/out/images/shot_001_then_001.png",
            "now_image_generated": True, "now_image_path": "C:/out/images/shot_001_now_001.png",
            "soundfx_generated": True, "soundfx_path": "soundfx/shot_001.wav",
        }]
        incoming = [{"id": "a1", "index": 1}]
        merge(incoming, fresh, [])
        assert incoming[0]["then_image_generated"] is True
        assert incoming[0]["now_image_generated"] is True
        # soundfx_path is stored relative and copied verbatim
        assert incoming[0]["soundfx_path"] == "soundfx/shot_001.wav"
        assert incoming[0]["soundfx_generated"] is True

    def test_end_to_end_locked_save_with_merge(self, pm, project_id, merge):
        """Full flow: concurrent generation completes while the editor saves."""
        _make_shots(pm, project_id, 2)

        # Client snapshot: stale (shot001 has no image yet in its copy)
        client_shots = [
            {"id": "shot001", "index": 1, "image_prompt": "edited while generating",
             "image_generated": False, "image_path": None},
            {"id": "shot002", "index": 2, "image_prompt": "prompt 2",
             "image_generated": False, "image_path": None},
        ]

        # Generation for shot002 completes before the save's locked section runs
        pm.update_shot_metadata(
            project_id,
            {"image_generated": True, "image_path": "C:/out/images/shot_002_001.png"},
            shot_id="shot002",
        )

        def stale_client_save(current_shots):
            merge(client_shots, current_shots, [])
            current_shots[:] = client_shots

        pm.update_shots_safely(project_id, stale_client_save)

        shots = {s["id"]: s for s in pm.get_shots(project_id)}
        assert shots["shot001"]["image_prompt"] == "edited while generating"  # client edit kept
        assert shots["shot001"]["image_generated"] is False                   # correctly still false
        assert shots["shot002"]["image_generated"] is True                    # concurrent result kept
        assert shots["shot002"]["image_path"] == "C:/out/images/shot_002_001.png"


# =====================================================================
# Character references -> shot asset references
# =====================================================================

class TestSyncCharacterAssetRefs:
    """Character reference images attach to their shots as project-media asset
    references (reference_asset_ids) so image generation consumes asset
    references instead of matching characters by name at generation time."""

    def _save_story(self, pm, project_id, characters):
        pm.save_story(project_id, json.dumps({"title": "t", "characters": characters}))

    def test_attaches_ref_to_matching_shots(self, pm, project_id):
        _make_shots(pm, project_id, 2)
        pm.update_shots_safely(project_id, lambda shots: shots[0].update(
            {"character_name": "Elena"}))
        self._save_story(pm, project_id, [
            {"name": "Elena", "character_reference_image_path":
                f"output/projects/{project_id}/references/ab12cd34_character_ref.png"},
        ])

        updated = pm.sync_character_asset_refs(project_id)

        assert updated == 1
        shots = {s["id"]: s for s in pm.get_shots(project_id)}
        assert shots["shot001"]["reference_asset_ids"] == [
            f"p/{project_id}/references/ab12cd34_character_ref.png"]
        assert not shots["shot002"].get("reference_asset_ids")  # other character's shot untouched

    def test_generated_ref_in_images_dir(self, pm, project_id):
        _make_shots(pm, project_id, 1)
        pm.update_shots_safely(project_id, lambda shots: shots[0].update(
            {"character_name": "Elena"}))
        self._save_story(pm, project_id, [
            {"name": "Elena", "character_reference_image_path":
                f"output/projects/{project_id}/images/char_001_character_001.png"},
        ])

        pm.sync_character_asset_refs(project_id)

        shots = pm.get_shots(project_id)
        assert shots[0]["reference_asset_ids"] == [
            f"p/{project_id}/images/char_001_character_001.png"]

    def test_idempotent_and_keeps_user_refs(self, pm, project_id):
        _make_shots(pm, project_id, 1)
        pm.update_shots_safely(project_id, lambda shots: shots[0].update(
            {"character_name": "Elena",
             "reference_asset_ids": ["i/9f3ab21c"]}))
        self._save_story(pm, project_id, [
            {"name": "Elena", "character_reference_image_path":
                f"output/projects/{project_id}/references/ab12cd34_character_ref.png"},
        ])

        assert pm.sync_character_asset_refs(project_id) == 1
        # Second run must not duplicate
        assert pm.sync_character_asset_refs(project_id) == 0

        refs = pm.get_shots(project_id)[0]["reference_asset_ids"]
        assert refs == ["i/9f3ab21c", f"p/{project_id}/references/ab12cd34_character_ref.png"]

    def test_skips_flfi2v_shots(self, pm, project_id):
        _make_shots(pm, project_id, 1)
        pm.update_shots_safely(project_id, lambda shots: shots[0].update(
            {"character_name": "Elena", "is_flfi2v": True}))
        self._save_story(pm, project_id, [
            {"name": "Elena", "character_reference_image_path":
                f"output/projects/{project_id}/references/ab12cd34_character_ref.png"},
        ])

        assert pm.sync_character_asset_refs(project_id) == 0
        assert not pm.get_shots(project_id)[0].get("reference_asset_ids")

    def test_ignores_paths_outside_project_media(self, pm, project_id):
        _make_shots(pm, project_id, 1)
        pm.update_shots_safely(project_id, lambda shots: shots[0].update(
            {"character_name": "Elena"}))
        self._save_story(pm, project_id, [
            {"name": "Elena", "character_reference_image_path": "E:/elsewhere/ref.png"},
            {"name": "NoRef"},  # no reference image
        ])

        assert pm.sync_character_asset_refs(project_id) == 0
        assert not pm.get_shots(project_id)[0].get("reference_asset_ids")

    def test_no_characters(self, pm, project_id):
        _make_shots(pm, project_id, 1)
        self._save_story(pm, project_id, [])
        assert pm.sync_character_asset_refs(project_id) == 0

    def test_character_name_whitespace_tolerant(self, pm, project_id):
        _make_shots(pm, project_id, 1)
        pm.update_shots_safely(project_id, lambda shots: shots[0].update(
            {"character_name": "  Elena  "}))
        self._save_story(pm, project_id, [
            {"name": "Elena", "character_reference_image_path":
                f"output/projects/{project_id}/references/ab12cd34_character_ref.png"},
        ])

        assert pm.sync_character_asset_refs(project_id) == 1

    def test_regenerated_ref_replaces_old(self, pm, project_id):
        """Regenerating a character image produces a new filename — the sync must
        swap the attached ref, not accumulate old versions."""
        _make_shots(pm, project_id, 1)
        pm.update_shots_safely(project_id, lambda shots: shots[0].update(
            {"character_name": "Elena"}))
        self._save_story(pm, project_id, [
            {"name": "Elena", "character_reference_image_path":
                f"output/projects/{project_id}/images/char_001_character_001.png"},
        ])
        pm.sync_character_asset_refs(project_id)

        self._save_story(pm, project_id, [
            {"name": "Elena", "character_reference_image_path":
                f"output/projects/{project_id}/images/char_001_character_002.png"},
        ])
        assert pm.sync_character_asset_refs(project_id) == 1

        shot = pm.get_shots(project_id)[0]
        assert shot["reference_asset_ids"] == [
            f"p/{project_id}/images/char_001_character_002.png"]
        assert shot["synced_character_asset_refs"] == [
            f"p/{project_id}/images/char_001_character_002.png"]

    def test_removed_ref_cleans_up_attached_refs(self, pm, project_id):
        """Clearing the character's reference image also detaches it from shots."""
        _make_shots(pm, project_id, 1)
        pm.update_shots_safely(project_id, lambda shots: shots[0].update(
            {"character_name": "Elena"}))
        self._save_story(pm, project_id, [
            {"name": "Elena", "character_reference_image_path":
                f"output/projects/{project_id}/references/ab12cd34_character_ref.png"},
        ])
        pm.sync_character_asset_refs(project_id)

        self._save_story(pm, project_id, [{"name": "Elena"}])
        assert pm.sync_character_asset_refs(project_id) == 1
        assert not pm.get_shots(project_id)[0].get("reference_asset_ids")

    def test_prompt_fallback_attach(self, pm, project_id):
        """Shots without character attribution get refs via name-in-prompt
        matching (movie shot planners don't emit character_name)."""
        _make_shots(pm, project_id, 3)
        pm.update_shots_safely(project_id, lambda shots: shots[0].update(
            {"image_prompt": "A lone detective in a trench coat"}))
        pm.update_shots_safely(project_id, lambda shots: shots[1].update(
            {"image_prompt": "Inspector Jamshed walks down the street"}))
        pm.update_shots_safely(project_id, lambda shots: shots[2].update(
            {"image_prompt": "a rusty knife glinting"}))
        self._save_story(pm, project_id, [
            {"name": "Inspector Jamshed", "character_reference_image_path":
                f"output/projects/{project_id}/references/ab12cd34_character_ref.png"},
        ])

        assert pm.sync_character_asset_refs(project_id) == 1
        shots = pm.get_shots(project_id)
        assert shots[1]["reference_asset_ids"] == [
            f"p/{project_id}/references/ab12cd34_character_ref.png"]
        assert not shots[0].get("reference_asset_ids")  # "detective" alone doesn't match
        assert not shots[2].get("reference_asset_ids")

    def test_prompt_fallback_word_match(self, pm, project_id):
        """A significant name word matches as a whole word ('Jamshed' alone)."""
        _make_shots(pm, project_id, 1)
        pm.update_shots_safely(project_id, lambda shots: shots[0].update(
            {"image_prompt": "close-up of Jamshed in the rain, the cat sleeps"}))
        self._save_story(pm, project_id, [
            {"name": "Inspector Jamshed", "character_reference_image_path":
                f"output/projects/{project_id}/references/ab12cd34_character_ref.png"},
        ])
        assert pm.sync_character_asset_refs(project_id) == 1

    def test_multiple_characters_on_one_shot(self, pm, project_id):
        _make_shots(pm, project_id, 1)
        pm.update_shots_safely(project_id, lambda shots: shots[0].update(
            {"characters": ["Elena", "Marco"]}))
        self._save_story(pm, project_id, [
            {"name": "Elena", "character_reference_image_path":
                f"output/projects/{project_id}/references/elena_ref.png"},
            {"name": "Marco", "character_reference_image_path":
                f"output/projects/{project_id}/references/marco_ref.png"},
        ])
        assert pm.sync_character_asset_refs(project_id) == 1
        refs = pm.get_shots(project_id)[0]["reference_asset_ids"]
        assert refs == [f"p/{project_id}/references/elena_ref.png",
                        f"p/{project_id}/references/marco_ref.png"]

    def test_adopts_matching_user_ref_into_tracking(self, pm, project_id):
        """A ref the user attached manually that equals the character's current
        image is adopted into the sync tracking (future regens swap it)."""
        ref_path = f"output/projects/{project_id}/references/ab12cd34_character_ref.png"
        _make_shots(pm, project_id, 1)
        pm.update_shots_safely(project_id, lambda shots: shots[0].update(
            {"character_name": "Elena",
             "reference_asset_ids": [f"p/{project_id}/references/ab12cd34_character_ref.png"]}))
        self._save_story(pm, project_id, [
            {"name": "Elena", "character_reference_image_path": ref_path},
        ])

        assert pm.sync_character_asset_refs(project_id) == 1  # marker adoption counts
        shot = pm.get_shots(project_id)[0]
        assert shot["reference_asset_ids"] == [f"p/{project_id}/references/ab12cd34_character_ref.png"]
        assert shot["synced_character_asset_refs"] == [f"p/{project_id}/references/ab12cd34_character_ref.png"]
        # And it's now stable
        assert pm.sync_character_asset_refs(project_id) == 0


    def test_short_words_ignored(self, pm, project_id):
        """'The Shadow' must not match a prompt merely because it contains 'the'."""
        _make_shots(pm, project_id, 2)
        pm.update_shots_safely(project_id, lambda shots: shots[0].update(
            {"image_prompt": "the harbor at night, long shadows between the cranes"}))
        pm.update_shots_safely(project_id, lambda shots: shots[1].update(
            {"image_prompt": "The Shadow waits on the pier"}))
        self._save_story(pm, project_id, [
            {"name": "The Shadow", "character_reference_image_path":
                f"output/projects/{project_id}/references/shadow_ref.png"},
        ])
        assert pm.sync_character_asset_refs(project_id) == 1
        shots = pm.get_shots(project_id)
        assert not shots[0].get("reference_asset_ids")  # scenery 'shadows' ≠ the character
        assert shots[1]["reference_asset_ids"] == [f"p/{project_id}/references/shadow_ref.png"]

    def test_common_noun_lowercase_not_matched(self, pm, project_id):
        """'rich shadow detail' in an otherwise capitalized prompt must not
        attach The Shadow — word matches require the capitalized proper noun."""
        _make_shots(pm, project_id, 1)
        pm.update_shots_safely(project_id, lambda shots: shots[0].update(
            {"image_prompt": "Moody wide shot of a dark harbor at night, rich shadow detail"}))
        self._save_story(pm, project_id, [
            {"name": "The Shadow", "character_reference_image_path":
                f"output/projects/{project_id}/references/shadow_ref.png"},
        ])
        assert pm.sync_character_asset_refs(project_id) == 0
        assert not pm.get_shots(project_id)[0].get("reference_asset_ids")

    def test_sync_persists_matched_characters(self, pm, project_id):
        """Matched names are written to shot['characters'] so the UI can show
        them; existing attribution is never overwritten."""
        _make_shots(pm, project_id, 2)
        pm.update_shots_safely(project_id, lambda shots: shots[0].update(
            {"image_prompt": "Inspector Jamshed at the dock"}))
        pm.update_shots_safely(project_id, lambda shots: shots[1].update(
            {"image_prompt": "Inspector Jamshed again", "characters": ["Custom"]}))
        self._save_story(pm, project_id, [{"name": "Inspector Jamshed"}])

        def set_ref(story):
            story["characters"][0]["character_reference_image_path"] = (
                f"output/projects/{project_id}/references/ab12cd34_character_ref.png")
        pm.update_story_safely(project_id, set_ref)

        assert pm.sync_character_asset_refs(project_id) == 1
        shots = pm.get_shots(project_id)
        assert shots[0]["characters"] == ["Inspector Jamshed"]
        assert shots[0]["reference_asset_ids"] == [
            f"p/{project_id}/references/ab12cd34_character_ref.png"]
        # explicit attribution the sync can't resolve is left alone entirely
        assert shots[1]["characters"] == ["Custom"]
        assert not shots[1].get("reference_asset_ids")
        # Idempotent
        assert pm.sync_character_asset_refs(project_id) == 0

    def test_save_shots_preserves_character_fields(self, pm, project_id):
        """Replanning must not strip character attribution or sync markers."""
        _make_shots(pm, project_id, 1)
        pm.update_shots_safely(project_id, lambda shots: shots[0].update(
            {"character_name": "Elena", "characters": ["Elena"], "props": ["Lantern"],
             "synced_character_asset_refs": ["p/x/references/e.png"],
             "synced_video_ref_asset_refs": ["p/x/backgrounds/b.png"]}))

        pm.save_shots(project_id, pm.get_shots(project_id))  # full-list rewrite
        shot = pm.get_shots(project_id)[0]
        assert shot["character_name"] == "Elena"
        assert shot["characters"] == ["Elena"]
        assert shot["props"] == ["Lantern"]
        assert shot["synced_character_asset_refs"] == ["p/x/references/e.png"]
        assert shot["synced_video_ref_asset_refs"] == ["p/x/backgrounds/b.png"]


class TestBuildCharactersBlock:
    """Story cast injection into shot planning prompts."""

    def test_block_lists_names_and_descriptions(self):
        from core.shot_planner import build_characters_block
        block = build_characters_block([
            {"name": "Inspector Jamshed", "image_prompt": "A rugged man in his 40s",
             "attire": "dark trench coat"},
            {"name": "The Shadow", "image_prompt": "A faceless figure"},
            {"name": ""},
        ])
        assert "Inspector Jamshed: A rugged man in his 40s dark trench coat" in block
        assert "The Shadow: A faceless figure" in block
        assert "'characters'" in block  # instructs the LLM to emit the field

    def test_empty_when_no_characters(self):
        from core.shot_planner import build_characters_block
        assert build_characters_block([]) == ""
        assert build_characters_block(None) == ""
        assert build_characters_block([{"image_prompt": "no name"}]) == ""

