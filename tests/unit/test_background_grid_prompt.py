"""
Unit tests for the 2x2 multi-angle background grid prompt builder
(core.sheet_generator.background_grid_prompt).
"""
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.sheet_generator import background_grid_prompt, background_base_text


class TestBackgroundGridPrompt:
    def test_wraps_description_and_aspect_ratio(self):
        prompt = background_grid_prompt("a smoky 1990s arcade interior", "16:9")
        assert prompt.startswith(
            "A 2x2 grid of four panels showing the same a smoky 1990s arcade interior "
            "background from four different camera angles.")
        assert "Aspect ratio of each panel: 16:9," in prompt
        # template structure preserved
        for fragment in ("Panel 1 (top left)", "Panel 2 (top right)",
                         "Panel 3 (bottom left)", "Panel 4 (bottom right)",
                         "no text, no labels, no watermarks"):
            assert fragment in prompt

    def test_strips_leading_wide_establishing_wording(self):
        # the exact wording the story directors emit
        prompt = background_grid_prompt(
            "A WIDE ESTABLISHING VIEW of a dark, smoke-filled arcade interior", "9:16")
        assert "wide establishing view" not in prompt.lower().split("panel")[0]
        assert prompt.startswith(
            "A 2x2 grid of four panels showing the same a dark, smoke-filled arcade "
            "interior background")

    def test_strips_case_and_variant_prefixes(self):
        for variant in ("a wide establishing shot of a plaza",
                        "A Wide Establishing Frame of a plaza"):
            assert background_grid_prompt(variant).startswith(
                "A 2x2 grid of four panels showing the same a plaza background")

    def test_plain_description_without_prefix(self):
        prompt = background_grid_prompt("neon-lit alley with puddles.", "16:9")
        assert "the same neon-lit alley with puddles background" in prompt
        # no double period where the description met the template sentence
        assert "puddles.. background" not in prompt

    def test_defaults_and_empty_description(self):
        assert "Aspect ratio of each panel: 16:9," in background_grid_prompt("a plaza", None)
        assert "the same scene environment background" in background_grid_prompt("", "16:9")


class TestBackgroundBaseText:
    def test_prefers_set_prompt_over_location(self):
        scene = {"set_prompt": "A WIDE ESTABLISHING VIEW of an arena", "location": "Arena"}
        assert background_base_text(scene) == "A WIDE ESTABLISHING VIEW of an arena"

    def test_falls_back_to_location(self):
        assert background_base_text({"location": "Arena"}) == "Arena"
