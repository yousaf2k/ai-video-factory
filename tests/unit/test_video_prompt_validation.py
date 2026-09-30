"""
Unit tests for MiniMax H3 video_prompt validation and per-shot clip duration.

Covers:
- parse_video_prompt_cut_times / validate_video_prompt (multishot structure,
  cut time ordering, duration fit with safety margin)
- ensure_shot_durations (defaults + clamping to the configured range)
- compile_workflow duration injection into the MiniMax H3 [duration] node
"""
import json
import os
import sys

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.shot_planner import (
    parse_video_prompt_cut_times,
    validate_video_prompt,
    ensure_shot_durations,
    validate_and_repair_shots,
)
from core.prompt_compiler import compile_workflow


SINGLE_SHOT_PROMPT = (
    "For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.\n\n"
    "integrated_multimodal_description: [Shot 1] Live-action, cinematic, a medium-wide shot frames a baker "
    "opening the shutters of a small street bakery before sunrise. The camera pushes in as he places a loaf "
    "on the counter.\n\n"
    "overall_soundscape: Quiet morning street ambience with distant traffic.\n\n"
    "non_diegetic_music: N/A"
)

MULTI_SHOT_PROMPT = (
    "For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.\n\n"
    "integrated_multimodal_description: [Shot 1] Live-action, cinematic, a medium-wide shot frames a baker "
    "opening the shutters of a small street bakery before sunrise. The camera pushes in as he places a loaf "
    "on the counter and says: <d>[English] First batch of the morning.</d> "
    "[Shot 2] At 00:05.000, the camera cuts to a close-up of steam rising from the sliced bread while the "
    "baker's final words carry over from the previous shot.\n\n"
    "overall_soundscape: Quiet morning street ambience with distant traffic.\n\n"
    "non_diegetic_music: N/A"
)


class TestParseCutTimes:
    def test_single_shot_has_no_cuts(self):
        assert parse_video_prompt_cut_times(SINGLE_SHOT_PROMPT) == []

    def test_multishot_cut_time_parsed(self):
        cuts = parse_video_prompt_cut_times(MULTI_SHOT_PROMPT)
        assert cuts == [(2, 5.0)]

    def test_lenient_time_formats(self):
        text = "[Shot 1] intro [Shot 2] At 0:01.500 cut [Shot 3] At 00:03.250 cut"
        cuts = parse_video_prompt_cut_times(text)
        assert cuts == [(2, 1.5), (3, 3.25)]


class TestValidateVideoPrompt:
    def test_valid_single_shot(self):
        assert validate_video_prompt(SINGLE_SHOT_PROMPT, clip_duration=5) == []

    def test_valid_multishot(self):
        # Cut at 5.0s leaves 3.0s in an 8s clip (margin is 0.7s)
        assert validate_video_prompt(MULTI_SHOT_PROMPT, clip_duration=8) == []

    def test_missing_required_fields(self):
        problems = validate_video_prompt("integrated_multimodal_description: [Shot 1] something")
        assert any("first-frame" in p for p in problems)
        assert any("overall_soundscape" in p for p in problems)
        assert any("non_diegetic_music" in p for p in problems)

    def test_empty_prompt(self):
        assert validate_video_prompt("") == ["video_prompt is empty"]
        assert validate_video_prompt(None) == ["video_prompt is empty"]

    def test_non_sequential_shot_numbers(self):
        text = MULTI_SHOT_PROMPT.replace("[Shot 2]", "[Shot 3]")
        problems = validate_video_prompt(text, clip_duration=8)
        assert any("sequential" in p for p in problems)

    def test_cut_time_outside_clip(self):
        problems = validate_video_prompt(MULTI_SHOT_PROMPT, clip_duration=4)
        assert any("outside the 4s clip" in p for p in problems)

    def test_cut_time_inside_margin(self):
        # 5.0s cut in a 5.5s clip: inside the clip but inside the 0.7s margin
        problems = validate_video_prompt(MULTI_SHOT_PROMPT, clip_duration=5.5)
        assert any("at or before" in p for p in problems)

    def test_non_increasing_cut_times(self):
        text = (
            "[Shot 1] intro [Shot 2] At 00:04.000 the camera cuts. "
            "[Shot 3] At 00:03.000 the camera cuts again."
        )
        problems = validate_video_prompt(text, clip_duration=10)
        assert any("not after the previous cut" in p for p in problems)


class TestEnsureShotDurations:
    def test_missing_duration_gets_default(self):
        shots = [{"index": 1}]
        ensure_shot_durations(shots)
        assert shots[0]["duration"] == 5

    def test_clamped_to_config_range(self):
        shots = [{"index": 1, "duration": 30}, {"index": 2, "duration": 0}]
        ensure_shot_durations(shots)
        assert shots[0]["duration"] == 15
        assert shots[1]["duration"] == 1

    def test_valid_duration_untouched(self):
        shots = [{"index": 1, "duration": 8}]
        ensure_shot_durations(shots)
        assert shots[0]["duration"] == 8

    def test_non_numeric_duration_gets_default(self):
        shots = [{"index": 1, "duration": "eight"}]
        ensure_shot_durations(shots)
        assert shots[0]["duration"] == 5


H3_WORKFLOW_PATH = os.path.join(project_root, "workflow", "video", "minimax_h3_i2v.json")
H3_DURATION_NODE = "105_111"


class TestValidateAndRepairShots:
    def _fake_provider(self, responses):
        class FakeProvider:
            def __init__(self):
                self.calls = 0

            def ask(self, prompt, response_format=None):
                resp = responses[min(self.calls, len(responses) - 1)]
                self.calls += 1
                return resp
        return FakeProvider()

    def test_valid_shots_untouched(self, monkeypatch):
        shots = [{"index": 1, "duration": 5, "video_prompt": SINGLE_SHOT_PROMPT}]
        monkeypatch.setattr("core.shot_planner.get_provider", lambda: self._fake_provider([]))
        validate_and_repair_shots(shots, "default")
        assert shots[0]["video_prompt"] == SINGLE_SHOT_PROMPT

    def test_invalid_prompt_repaired_by_position(self, monkeypatch):
        # No duration -> ensure_shot_durations defaults it to 5s; then the
        # 5.0s cut violates the 0.7s end margin and gets repaired
        broken = MULTI_SHOT_PROMPT
        fixed = SINGLE_SHOT_PROMPT
        shots = [{"duration": None, "video_prompt": broken}]
        provider = self._fake_provider([json.dumps([{"position": 0, "video_prompt": fixed}])])
        monkeypatch.setattr("core.shot_planner.get_provider", lambda: provider)
        validate_and_repair_shots(shots, "default")
        assert provider.calls == 1
        assert shots[0]["video_prompt"] == fixed
        assert shots[0]["duration"] == 5

    def test_repair_keeps_original_when_llm_reply_also_invalid(self, monkeypatch):
        still_broken = MULTI_SHOT_PROMPT.replace("00:05.000", "00:09.000")
        shots = [{"duration": 8, "video_prompt": "integrated_multimodal_description: [Shot 1] x"}]
        provider = self._fake_provider([json.dumps([{"position": 0, "video_prompt": still_broken}])])
        monkeypatch.setattr("core.shot_planner.get_provider", lambda: provider)
        validate_and_repair_shots(shots, "default")
        # Original (structurally incomplete) prompt kept; no crash
        assert shots[0]["video_prompt"] == "integrated_multimodal_description: [Shot 1] x"

    def test_repair_with_unknown_position_ignored(self, monkeypatch):
        shots = [{"duration": 5, "video_prompt": "integrated_multimodal_description: [Shot 1] x"}]
        provider = self._fake_provider([json.dumps([{"position": 99, "video_prompt": SINGLE_SHOT_PROMPT}])])
        monkeypatch.setattr("core.shot_planner.get_provider", lambda: provider)
        validate_and_repair_shots(shots, "default")
        assert shots[0]["video_prompt"] == "integrated_multimodal_description: [Shot 1] x"


@pytest.mark.skipif(not os.path.exists(H3_WORKFLOW_PATH), reason="H3 workflow file missing")
class TestCompileWorkflowDurationInjection:
    def _compile(self, duration, workflow_config):
        shot = {
            "index": 1,
            "image_prompt": "a baker in a bakery",
            "motion_prompt": "camera pushes in",
            "video_prompt": SINGLE_SHOT_PROMPT,
            "prompt_type": "video",
            "camera": "static",
        }
        if duration is not None:
            shot["duration"] = duration
        template = json.load(open(H3_WORKFLOW_PATH, encoding="utf-8"))
        return compile_workflow(template, shot, video_length_seconds=5, workflow_config=workflow_config)

    def _h3_config(self):
        return {
            "duration_node_id": H3_DURATION_NODE,
            "motion_prompt_node_id": "105_104",
            "min_duration": 1,
            "max_duration": 15,
        }

    def test_per_shot_duration_injected(self):
        wf = self._compile(12, self._h3_config())
        assert wf[H3_DURATION_NODE]["inputs"]["value"] == 12.0

    def test_duration_clamped_to_workflow_max(self):
        wf = self._compile(30, self._h3_config())
        assert wf[H3_DURATION_NODE]["inputs"]["value"] == 15.0

    def test_duration_clamped_to_workflow_min(self):
        wf = self._compile(0.2, self._h3_config())
        assert wf[H3_DURATION_NODE]["inputs"]["value"] == 1.0

    def test_missing_duration_falls_back_to_default(self):
        wf = self._compile(None, self._h3_config())
        assert wf[H3_DURATION_NODE]["inputs"]["value"] == 5.0

    def test_workflow_without_opt_in_untouched(self):
        # A workflow that did not opt in to per-shot durations keeps its
        # baked-in duration value
        baked_in = json.load(open(H3_WORKFLOW_PATH, encoding="utf-8"))[H3_DURATION_NODE]["inputs"]["value"]
        wf = self._compile(12, {})
        assert wf[H3_DURATION_NODE]["inputs"]["value"] == baked_in
