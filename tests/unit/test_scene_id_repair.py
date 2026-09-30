"""
Unit tests for shot scene_id repair.

Covers:
- repair_batch_scene_ids (single-scene pinning, multi-scene reassignment)
- plan_shots_batch end-to-end with a provider that echoes scene_id 0 for
  every batch (the observed failure: a re-planned story lost scene_id 1)
"""
import json
import os
import sys

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.shot_planner import plan_shots_batch, repair_batch_scene_ids


VALID_VIDEO_PROMPT = (
    "For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.\n\n"
    "integrated_multimodal_description: [Shot 1] Live-action, cinematic, a medium shot frames a boxer in the rain.\n\n"
    "overall_soundscape: Rain and distant traffic.\n\n"
    "non_diegetic_music: N/A"
)


def _shot(scene_id, index=1):
    return {
        "scene_id": scene_id,
        "duration": 5,
        "image_prompt": "a boxer",
        "motion_prompt": "jab",
        "video_prompt": VALID_VIDEO_PROMPT,
        "soundfx_prompt": "",
        "camera": "static",
        "index": index,
    }


class TestRepairBatchSceneIds:
    def test_single_scene_batch_pins_wrong_ids(self):
        # The observed failure: batch for scene 1 comes back labeled 0
        scenes = [{"scene_id": 1, "location": "fighting club"}]
        shots = [_shot(0, 1), _shot(0, 2), _shot(0, 3)]
        repair_batch_scene_ids(shots, scenes, 2, 3)
        assert [s["scene_id"] for s in shots] == [1, 1, 1]

    def test_single_scene_batch_fills_missing_ids(self):
        scenes = [{"scene_id": 2, "location": "stadium"}]
        shots = [_shot(None, 1), _shot(2, 2)]
        repair_batch_scene_ids(shots, scenes, 3, 3)
        assert [s["scene_id"] for s in shots] == [2, 2]

    def test_correct_ids_untouched(self):
        scenes = [{"scene_id": 0, "location": "alley"}]
        shots = [_shot(0, 1), _shot(0, 2)]
        repair_batch_scene_ids(shots, scenes, 1, 3)
        assert [s["scene_id"] for s in shots] == [0, 0]

    def test_multi_scene_batch_reassigns_out_of_batch_ids(self):
        # Out-of-batch ids go to whichever batch scene has the fewest shots
        # (ties go to the earlier scene)
        scenes = [{"scene_id": 0, "location": "alley"}, {"scene_id": 1, "location": "club"}]
        shots = [_shot(0, 1), _shot(0, 2), _shot(5, 3), _shot(None, 4), _shot(1, 5)]
        repair_batch_scene_ids(shots, scenes, 1, 1)
        assert [s["scene_id"] for s in shots] == [0, 0, 1, 0, 1]

    def test_multi_scene_batch_valid_ids_untouched(self):
        scenes = [{"scene_id": 0, "location": "alley"}, {"scene_id": 1, "location": "club"}]
        shots = [_shot(0, 1), _shot(1, 2)]
        repair_batch_scene_ids(shots, scenes, 1, 1)
        assert [s["scene_id"] for s in shots] == [0, 1]

    def test_degenerate_inputs_no_crash(self):
        assert repair_batch_scene_ids(None, [{"scene_id": 0}]) is None
        assert repair_batch_scene_ids([], []) == []
        shots = [_shot(0, 1)]
        assert repair_batch_scene_ids(shots, ["not-a-dict"]) == shots


class TestPlanShotsBatchSceneRepair:
    def test_echoed_scene_id_zero_repaired(self, monkeypatch):
        """Batch 2 of 3 (scene_id 1) whose provider response echoes scene_id 0
        must come out with scene_id 1 - this is the regression that dropped
        the 2nd scene from re-planned shots."""
        scenes_batch = [{
            "scene_id": 1,
            "location": "fighting club",
            "action": "Kira steps into the wired cage.",
            "scene_duration": 45,
        }]

        class EchoingProvider:
            def ask(self, prompt, response_format=None):
                # Simulates the LLM mislabeling every shot as scene 0
                return json.dumps([_shot(0, i + 1) for i in range(9)])

        monkeypatch.setattr("core.shot_planner.get_provider", lambda: EchoingProvider())
        shots = plan_shots_batch(
            scenes_batch=scenes_batch,
            batch_num=2,
            total_batches=3,
            max_shots_instruction="Generate 9 shots.",
            shots_agent="default",
        )

        assert len(shots) == 9
        assert all(s["scene_id"] == 1 for s in shots)
