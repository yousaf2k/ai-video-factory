"""
Unit tests for duration-driven shot planning and the per-project max shot
duration cap.

Covers:
- normalize_shot_duration_cap (defaults, clamping, garbage input)
- get_shot_duration_instruction (cap-aware ranges and duration bands)
- extract_scene_durations (scene_length / scene_duration spellings)
- build_scene_duration_plan (budget text, no exact shot counts, safety cap)
- ensure_shot_durations (project cap clamping)
- CreateProjectRequest / ReplanShotsRequest validation of the field
"""
import math
import os
import sys

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.shot_planner import (
    MIN_SHOT_DURATION,
    MAX_SHOT_DURATION,
    build_scene_duration_plan,
    ensure_shot_durations,
    extract_scene_durations,
    get_shot_duration_instruction,
    normalize_shot_duration_cap,
)


class TestNormalizeShotDurationCap:
    def test_none_means_full_range(self):
        assert normalize_shot_duration_cap(None) == float(MAX_SHOT_DURATION)

    def test_cap_passthrough(self):
        assert normalize_shot_duration_cap(5) == 5.0
        assert normalize_shot_duration_cap(7.5) == 7.5

    def test_cap_above_max_clamped(self):
        assert normalize_shot_duration_cap(30) == float(MAX_SHOT_DURATION)

    def test_cap_below_min_raised(self):
        assert normalize_shot_duration_cap(0) == float(MIN_SHOT_DURATION)

    def test_garbage_falls_back_to_max(self):
        assert normalize_shot_duration_cap("eight") == float(MAX_SHOT_DURATION)


class TestGetShotDurationInstruction:
    def test_uncapped_instruction_mentions_full_range(self):
        text = get_shot_duration_instruction(None)
        assert f"between {MIN_SHOT_DURATION} and {MAX_SHOT_DURATION}" in text
        assert "complex multi-beat sequences" in text

    def test_capped_instruction_uses_cap(self):
        text = get_shot_duration_instruction(5)
        assert "between 1 and 5" in text
        assert "Never exceed 5 seconds" in text

    def test_capped_instruction_hides_long_clip_band(self):
        text = get_shot_duration_instruction(5)
        assert "complex multi-beat sequences" not in text

    def test_cap_8_keeps_multi_beat_band(self):
        text = get_shot_duration_instruction(8)
        assert "between 1 and 8" in text
        assert "complex multi-beat sequences 8-8" in text


class TestExtractSceneDurations:
    def test_scene_length_and_duration_spellings(self):
        scenes = [
            {"scene_id": 0, "scene_length": 45},
            {"scene_id": 1, "scene_duration": 50.5},
            {"scene_id": 2},                      # no field -> skipped
            {"scene_id": 3, "scene_length": 0},   # zero -> skipped
            {"scene_id": 4, "scene_length": "bad"},  # garbage -> skipped
        ]
        assert extract_scene_durations(scenes) == [(0, 45.0), (1, 50.5)]


class TestBuildSceneDurationPlan:
    def test_budget_text_without_exact_counts(self):
        budgets = [(0, 45.0), (1, 50.0)]
        instruction, cap = build_scene_duration_plan(budgets, 5)

        assert "Scene 0: ~45s total" in instruction
        assert "Scene 1: ~50s total" in instruction
        # Durations-first: the LLM decides the count, no exact mandate
        assert "exactly" not in instruction
        assert "MUST generate" not in instruction
        assert "between 1 and 5 seconds" in instruction
        assert "sum to approximately that scene's duration" in instruction
        assert cap == math.ceil(45 / MIN_SHOT_DURATION) + math.ceil(50 / MIN_SHOT_DURATION)

    def test_safety_cap_allows_short_inserts(self):
        budgets = [(0, 45.0)]
        _, cap = build_scene_duration_plan(budgets, 5)
        # 45 one-second shots fit the budget, so truncation can never clip a
        # duration-valid plan
        assert cap == 45

    def test_total_preserved_in_text(self):
        budgets = [(0, 45.0), (1, 55.0)]
        instruction, _ = build_scene_duration_plan(budgets, 15)
        assert "~100s across 2 scene(s)" in instruction


class TestEnsureShotDurationsWithCap:
    def test_cap_clamps_long_shots(self):
        shots = [{"duration": 8}, {"duration": 12}]
        ensure_shot_durations(shots, max_duration=5)
        assert shots[0]["duration"] == 5.0
        assert shots[1]["duration"] == 5.0

    def test_cap_clamps_default_fill(self):
        shots = [{}]  # missing duration defaults, then must respect the cap
        ensure_shot_durations(shots, max_duration=3)
        assert shots[0]["duration"] == 3.0

    def test_no_cap_keeps_full_range(self):
        shots = [{"duration": 12}]
        ensure_shot_durations(shots, max_duration=None)
        assert shots[0]["duration"] == 12.0


class TestBackendRequestValidation:
    def test_create_project_request_accepts_and_coerces(self):
        from web_ui.backend.models.project import CreateProjectRequest
        req = CreateProjectRequest(idea="x", max_shot_duration="5")
        assert req.max_shot_duration == 5.0

    def test_create_project_request_rejects_out_of_range(self):
        from web_ui.backend.models.project import CreateProjectRequest
        with pytest.raises(Exception):
            CreateProjectRequest(idea="x", max_shot_duration=16)
        with pytest.raises(Exception):
            CreateProjectRequest(idea="x", max_shot_duration=0.5)

    def test_replan_request_validates_cap(self):
        from web_ui.backend.models.shot import ReplanShotsRequest
        assert ReplanShotsRequest(shots_agent="default").max_shot_duration is None
        assert ReplanShotsRequest(shots_agent="default", max_shot_duration=8).max_shot_duration == 8.0
        with pytest.raises(Exception):
            ReplanShotsRequest(shots_agent="default", max_shot_duration=20)
