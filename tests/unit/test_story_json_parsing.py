"""
Unit tests for story JSON parsing robustness (core.story_engine):

- parse_llm_json repair fallback: key missing its opening quote (observed in
  the wild from Gemini), trailing commas; valid JSON still parses untouched;
  hopeless text still raises
- parse_story_json_with_retry: one LLM repair pass on invalid output, and a
  ValueError (never the raw invalid text) when recovery fails
"""
import json
import os
import sys

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.story_engine import parse_llm_json, parse_story_json_with_retry, normalize_scene_ids


# The exact malformation seen in project_20261025_001610: repeated keys
# truncated to `emotion":` (opening quote missing), twice in one response
BROKEN_STORY_JSON = """{
  "title": "Neon Resurrection",
  "style": "gritty action",
  "scenes": [
    {
      "scene_id": 1,
      "location": "Dark 1990s Arcade Interior",
      "action": "A copper quarter plummets into the steel slot.",
      emotion": "Intense anticipation and raw awakening",
      "scene_duration": 45
    },
    {
      "scene_id": 2,
      "action": "The screen violently fractures into polygons.",
      emotion": "Savage escalation and mechanical evolution",
      "scene_duration": 45
    }
  ]
}"""


# Unbalanced braces defeat fence/span extraction and every repair fallback
UNREPAIRABLE_JSON = '{"title": "Broken", "scenes": [{"scene_id": 1'


class _FakeProvider:
    """Records prompts, replays scripted responses."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    def ask(self, prompt, response_format=None):
        self.prompts.append(prompt)
        return self.responses.pop(0)


class TestParseLlmJsonRepair:
    def test_repairs_missing_key_quote(self):
        story = parse_llm_json(BROKEN_STORY_JSON)
        assert story["title"] == "Neon Resurrection"
        assert story["scenes"][0]["emotion"] == "Intense anticipation and raw awakening"
        assert story["scenes"][1]["emotion"] == "Savage escalation and mechanical evolution"

    def test_repairs_trailing_comma(self):
        text = '{"title": "x", "scenes": [{"scene_id": 1,}],}'
        assert parse_llm_json(text)["scenes"][0]["scene_id"] == 1

    def test_valid_json_untouched(self):
        text = '{"title": "ok", "a: b": "comma\", inside": 1}'
        assert parse_llm_json(text)["title"] == "ok"

    def test_fenced_json_still_parses(self):
        text = '```json\n{"title": "fenced"}\n```'
        assert parse_llm_json(text)["title"] == "fenced"

    def test_hopeless_text_still_raises(self):
        with pytest.raises(json.JSONDecodeError):
            parse_llm_json("not json at all")


class TestParseStoryJsonWithRetry:
    def test_llm_repair_pass_recovers(self):
        fixed = json.dumps({"title": "Fixed", "scenes": []})
        provider = _FakeProvider([fixed])
        story = parse_story_json_with_retry(provider, UNREPAIRABLE_JSON)
        assert story["title"] == "Fixed"
        # exactly one repair call, and the broken text was handed to the LLM
        assert len(provider.prompts) == 1
        assert "Broken" in provider.prompts[0]

    def test_unrecoverable_raises_valueerror_not_raw_text(self):
        provider = _FakeProvider(["still not json"])
        with pytest.raises(ValueError):
            parse_story_json_with_retry(provider, UNREPAIRABLE_JSON)

    def test_valid_json_skips_llm_call(self):
        provider = _FakeProvider([])
        story = parse_story_json_with_retry(provider, '{"title": "clean"}')
        assert story["title"] == "clean"
        assert provider.prompts == []


class TestNormalizeSceneIds:
    def test_reindexes_llm_one_based_ids(self):
        story = {"scenes": [{"scene_id": 1, "location": "a"},
                            {"scene_id": 2, "location": "b"},
                            {"scene_id": 3, "location": "c"}]}
        normalize_scene_ids(story)
        assert [s["scene_id"] for s in story["scenes"]] == [0, 1, 2]

    def test_keeps_scene_fields(self):
        story = {"scenes": [{"scene_id": 7, "location": "a",
                             "background_image_path": "backgrounds/background_001_001.png"}]}
        normalize_scene_ids(story)
        scene = story["scenes"][0]
        assert scene["scene_id"] == 0
        assert scene["background_image_path"] == "backgrounds/background_001_001.png"

    def test_fills_missing_ids_and_tolerates_junk(self):
        story = {"scenes": [{"location": "a"}, {"scene_id": 5}, "junk", None]}
        normalize_scene_ids(story)
        assert story["scenes"][0]["scene_id"] == 0
        assert story["scenes"][1]["scene_id"] == 1

    def test_safe_on_degenerate_input(self):
        assert normalize_scene_ids({}) == {}
        assert normalize_scene_ids({"scenes": None})["scenes"] is None
        assert normalize_scene_ids("not a dict") == "not a dict"
