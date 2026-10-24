"""
Pass-1 master script resolution and Pass-2 merge priority in build_story.

Each story family ships <family>/_base/master_script.md (movie, documentary);
families without one fall back to the documentary master script. The Pass-2
director is authoritative for title/style, with Pass 1 filling gaps.
"""
import json

import core.story_engine as story_engine
from core.story_engine import build_story, resolve_master_script_director


class FakeProvider:
    """Sequential LLM stub: pops one canned response per ask() call."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    def ask(self, prompt, response_format=None):
        self.prompts.append(prompt)
        return json.dumps(self.responses.pop(0))


def test_family_override_used_for_movie_directors():
    assert resolve_master_script_director("movie/horror") == "movie/_base/master_script"
    assert resolve_master_script_director("movie/action") == "movie/_base/master_script"


def test_families_with_override_use_their_own_master_script():
    assert resolve_master_script_director("documentary/default") == "documentary/_base/master_script"
    assert resolve_master_script_director("movie/horror") == "movie/_base/master_script"


def test_families_without_override_fall_back_to_documentary():
    assert resolve_master_script_director("then_vs_now/then_vs_now") == "documentary/_base/master_script"
    assert resolve_master_script_director("asmr/asmr_glass_cutting") == "documentary/_base/master_script"


def test_bare_director_name_falls_back_to_documentary():
    assert resolve_master_script_director("default") == "documentary/_base/master_script"


def test_build_story_uses_family_master_script_and_pass2_wins(monkeypatch):
    provider = FakeProvider([
        {  # Pass 1 (master script) output
            "title": "Master Title",
            "style": "ultra cinematic documentary",
            "master_script": "A haunted lighthouse keeper's tale.",
        },
        {  # Pass 2 (genre director) output
            "title": "Director Title",
            "style": "gothic horror",
            "scenes": [
                {"scene_id": 0, "narration": "x", "scene_duration": 30},
                {"scene_id": 1, "narration": "y", "scene_duration": 30},
            ],
        },
    ])
    monkeypatch.setattr(story_engine, "get_provider", lambda: provider)

    story = json.loads(build_story(
        "a haunted lighthouse", director_name="movie/horror", target_length=60
    ))

    # Pass 1 prompt came from the movie family override, not the documentary fallback
    assert "screenwriter" in provider.prompts[0].lower()
    assert "documentary" not in provider.prompts[0].lower()
    # Placeholders were substituted: 60s * 2.5 words/s = 150 words
    assert "150" in provider.prompts[0]
    assert "{MASTER_WORD_COUNT}" not in provider.prompts[0]
    assert "haunted lighthouse" in provider.prompts[0]
    # Pass 2 director is authoritative for title/style; Pass 1 fills gaps
    assert story["title"] == "Director Title"
    assert story["style"] == "gothic horror"
    assert story["master_script"] == "A haunted lighthouse keeper's tale."


def test_build_story_master_fills_missing_pass2_fields(monkeypatch):
    provider = FakeProvider([
        {"title": "Master Title", "style": "slow-burn thriller", "master_script": "script"},
        {"title": "", "style": "", "scenes": [
            {"scene_id": 0, "narration": "x", "scene_duration": 60},
        ]},
    ])
    monkeypatch.setattr(story_engine, "get_provider", lambda: provider)

    story = json.loads(build_story(
        "an idea", director_name="movie/thriller", target_length=60
    ))

    # Empty Pass 2 values fall through to the master pass
    assert story["title"] == "Master Title"
    assert story["style"] == "slow-burn thriller"
