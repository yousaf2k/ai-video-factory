"""Offline unit tests for FlowWeb tile-attribution matching.

Covers the label-hint path added for non-Latin prompts: Flow summarizes
every tile with an English aria-label, so an Urdu (or other non-Latin)
prompt can never word-match its own tile without translated keywords.
"""
from unittest import mock

import core.flowweb_image_subprocess as fis


URDU_PROMPT = (
    "wide establishing shot of پہاڑی راستہ، جیپ کے اندر اور باہر، جھاڑیاں، چٹانیں. "
    "An empty environment reference: no characters or people present, "
    "clear view of the space, key props and architecture, "
    "ultra cinematic documentary with dramatic reenactments, cinematic, high detail."
)

CANDIDATES = [
    {"src": "a", "w": 1376, "h": 768, "label": "Road trip to Gilgit Baltistan"},
    {"src": "b", "w": 1376, "h": 768, "label": "Shops on roadside in sunlight"},
    {"src": "c", "w": 1376, "h": 768, "label": "Jeep driving on mountain path"},
]


def setup_function(_):
    fis._LABEL_HINTS_CACHE.clear()


def test_ascii_prompt_skips_llm():
    with mock.patch("core.llm_engine.get_provider") as gp:
        assert fis._label_hints_for_prompt("a boy at a tea stall") is None
        gp.assert_not_called()


def test_non_ascii_prompt_gets_hints():
    with mock.patch("core.llm_engine.get_provider") as gp:
        gp.return_value.ask.return_value = (
            "Jeep on a mountain path with bushes and rocks\nsome extra line")
        hints = fis._label_hints_for_prompt(URDU_PROMPT)
    assert hints == "Jeep on a mountain path with bushes and rocks"
    # cached: second call makes no LLM request
    with mock.patch("core.llm_engine.get_provider") as gp:
        assert fis._label_hints_for_prompt(URDU_PROMPT) == hints
        gp.assert_not_called()


def test_non_ascii_prompt_llm_failure_returns_none():
    with mock.patch("core.llm_engine.get_provider") as gp:
        gp.side_effect = RuntimeError("no api key")
        assert fis._label_hints_for_prompt(URDU_PROMPT) is None


def test_urdu_prompt_never_matches_without_hints():
    # Old behavior: the worker waits out the full timeout (returns None).
    assert fis._pick_own_candidate(CANDIDATES, URDU_PROMPT) is None


def test_urdu_prompt_matches_own_tile_with_hints():
    hints = "Jeep on a mountain path with bushes and rocks"
    chosen = fis._pick_own_candidate(CANDIDATES, URDU_PROMPT, hints)
    assert chosen is not None
    assert chosen["src"] == "c"


def test_hints_do_not_override_a_direct_match():
    # English prompts keep using direct prompt-word matching.
    prompt = "character reference sheet for a villager holding a lantern"
    cands = [
        {"src": "x", "w": 1376, "h": 768,
         "label": "Villager character reference sheet"},
        {"src": "y", "w": 1376, "h": 768, "label": "Jeep driving on mountain path"},
    ]
    chosen = fis._pick_own_candidate(cands, prompt, hints="jeep mountain path")
    assert chosen["src"] == "x"


def test_unrelated_hints_still_reject_foreign_tiles():
    # Low-scoring hints must not claim another worker's tile.
    assert fis._pick_own_candidate(
        CANDIDATES, URDU_PROMPT, hints="a crowded fish market at dawn") is None
