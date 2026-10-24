"""
Unit tests for the ref2video (r2v) / text-to-video (t2v) pipeline pieces:

- compile_workflow r2v reference injection: [ref_N] slot filling, unfilled
  slot pruning, `value` prompt input for PrimitiveStringMultiline prompt
  nodes, image_path injection guard
- r2v workflow discovery flags (is_ref2video / reference_image_node_ids)
- r2v_composer: <Picture> pruning, voice-text embedding, audio definitions,
  six-section + 7000-char validation
- validate_video_prompt r2v/t2v variants
"""
import copy
import os
import sys

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.prompt_compiler import compile_workflow
from core.r2v_composer import (
    compose_video_prompt,
    embed_voice_texts,
    prune_picture_labels,
    append_audio_definitions,
    validate_composed_prompt,
    R2V_PROMPT_CHAR_LIMIT,
)
from core.shot_planner import validate_video_prompt, effective_shots_director


def _r2v_template():
    """Minimal MiniMax H3 R2V workflow in API format with 3 wired ref slots."""
    wf = {}
    for i in range(3):
        wf[str(100 + i)] = {
            "inputs": {"image": f"placeholder_{i}.png"},
            "class_type": "LoadImage",
            "_meta": {"title": f"[ref_{i}] Load Image (Reference)"},
        }
    wf["10"] = {
        "inputs": {"value": "template prompt"},
        "class_type": "PrimitiveStringMultiline",
        "_meta": {"title": "[prompt] Input Text (Prompt)"},
    }
    gen_inputs = {
        "prompt": ["10", 0],
        "width": 1280, "height": 720, "length": ["11", 1],
    }
    for i in range(3):
        gen_inputs[f"ref_images.ref_image_{i}"] = [str(100 + i), 0]
    wf["20"] = {
        "inputs": gen_inputs,
        "class_type": "MiniMaxH3ReferenceToVideo",
        "_meta": {"title": "MiniMax H3 Reference to Video"},
    }
    return wf


def _r2v_config():
    return {
        "is_ref2video": True,
        "reference_image_node_ids": ["100", "101", "102"],
        "motion_prompt_node_id": "10",
        "wan_video_node_id": "20",
        "duration_node_id": None,
    }


class TestCompileWorkflowR2V:
    def test_value_prompt_input(self, monkeypatch):
        monkeypatch.setattr("core.comfy_client.prepare_comfyui_input_image", lambda p: p)
        wf = compile_workflow(_r2v_template(), {
            "video_prompt": "subject_definitions:\nsummary:\nretention_analysis:\ndetailed_description:\noverall_soundscape:\nnon_diegetic_music:",
            "prompt_type": "video", "index": 1,
        }, workflow_config=_r2v_config(), reference_images=["a.png"])
        # PrimitiveStringMultiline prompt node takes `value`, not text/prompt
        assert wf["10"]["inputs"]["value"].startswith("subject_definitions:")
        assert "text" not in wf["10"]["inputs"]

    def test_reference_injection_and_pruning(self, monkeypatch):
        monkeypatch.setattr("core.comfy_client.prepare_comfyui_input_image", lambda p: p)
        wf = compile_workflow(_r2v_template(), {
            "video_prompt": "x", "prompt_type": "video", "index": 1,
        }, workflow_config=_r2v_config(), reference_images=["one.png", "two.png"])
        # first two slots filled in order
        assert wf["100"]["inputs"]["image"] == "one.png"
        assert wf["101"]["inputs"]["image"] == "two.png"
        # unfilled third slot: node pruned + link removed
        assert "102" not in wf
        assert "ref_images.ref_image_2" not in wf["20"]["inputs"]
        assert "ref_images.ref_image_0" in wf["20"]["inputs"]

    def test_more_refs_than_slots_drops_extras(self, monkeypatch):
        monkeypatch.setattr("core.comfy_client.prepare_comfyui_input_image", lambda p: p)
        wf = compile_workflow(_r2v_template(), {
            "video_prompt": "x", "prompt_type": "video", "index": 1,
        }, workflow_config=_r2v_config(),
            reference_images=["a.png", "b.png", "c.png", "d.png"])
        # only the 3 wired slots receive refs
        assert wf["100"]["inputs"]["image"] == "a.png"
        assert wf["101"]["inputs"]["image"] == "b.png"
        assert wf["102"]["inputs"]["image"] == "c.png"

    def test_no_image_path_injection_for_r2v(self, monkeypatch):
        monkeypatch.setattr("core.comfy_client.prepare_comfyui_input_image", lambda p: p)
        wf = compile_workflow(_r2v_template(), {
            "video_prompt": "x", "prompt_type": "video", "index": 1,
            "image_path": "first_frame.png",
        }, workflow_config=_r2v_config(), reference_images=["a.png"])
        # image_path must NOT leak into a reference slot
        assert all(wf[nid]["inputs"]["image"] != "first_frame.png" for nid in ("100",))

    def test_zero_refs_keeps_gen_node_links_clean(self, monkeypatch):
        monkeypatch.setattr("core.comfy_client.prepare_comfyui_input_image", lambda p: p)
        wf = compile_workflow(_r2v_template(), {
            "video_prompt": "x", "prompt_type": "video", "index": 1,
        }, workflow_config=_r2v_config(), reference_images=None)
        # t2v: no refs attached, all links pruned, generation node intact
        for i in range(3):
            assert str(100 + i) not in wf
            assert f"ref_images.ref_image_{i}" not in wf["20"]["inputs"]
        assert wf["20"]["class_type"] == "MiniMaxH3ReferenceToVideo"


class TestWorkflowDiscovery:
    def test_r2v_workflows_discovered(self):
        import config
        wf = config.VIDEO_WORKFLOWS.get("minimax_h3_r2v")
        assert wf, "r2v workflow not discovered"
        assert wf.get("is_ref2video") is True
        ref_ids = wf.get("reference_image_node_ids") or []
        assert len(ref_ids) == 9, f"expected 9 wired ref slots, got {len(ref_ids)}"
        assert wf.get("motion_prompt_node_id") == "138"
        # FLFI2V-style image mappings must not apply to r2v workflows
        assert "load_image_first_node_id" not in wf
        assert "load_image_last_node_id" not in wf
        assert "load_image_node_id" not in wf

    def test_i2v_workflow_untouched(self):
        import config
        wf = config.VIDEO_WORKFLOWS.get("minimax_h3_i2v")
        assert wf and not wf.get("is_ref2video")
        assert wf.get("load_image_node_id") == "114"


R2V_PROMPT = """subject_definitions:
<Subject 1> is the baker in <Picture 1>, with a flour-dusted apron.
<Subject 2> is the bakery environment in <Picture 2>: wooden counter, brass scale.

summary:
[reference generation] The baker opens the bakery at dawn.

retention_analysis:
<Subject 1> (appears in [Shot 1]): fully_preserved - apron retained.

detailed_description:
The target video is live-action, cinematic.
[Shot 1] Inside <Subject 2>, a medium shot frames <Subject 1> as he says in a calm, slightly raspy voice (S1): <d>[English] First batch of the morning.</d>

overall_soundscape:
Cold morning street tone through the glass.

non_diegetic_music:
A sparse solo piano motif, slow tempo.
"""


class TestComposer:
    def test_prune_dropped_picture_citations(self):
        # 2 pictures attached, prompt cites Picture 2 (the background) which
        # got dropped by the slot budget -> citation stripped, subject kept
        pruned, dropped = prune_picture_labels(R2V_PROMPT, 1)
        assert dropped == 1
        assert "<Picture 2>" not in pruned
        # the kept citation stays
        assert "<Picture 1>" in pruned
        # the subject definition text survives
        assert "bakery environment" in pruned

    def test_prune_noop_when_all_attached(self):
        pruned, dropped = prune_picture_labels(R2V_PROMPT, 2)
        assert dropped == 0
        assert pruned == R2V_PROMPT

    def test_voice_embedding_idempotent(self):
        # exact verbatim substring of the prompt's voice phrase
        voice_text = "calm, slightly raspy voice"
        once, missing = embed_voice_texts(R2V_PROMPT, [("Baker", voice_text)])
        assert missing == []  # already verbatim in the prompt
        twice, _ = embed_voice_texts(once, [("Baker", voice_text)])
        assert twice == once
        # a voice the director lost gets injected into subject_definitions
        injected, missing2 = embed_voice_texts(R2V_PROMPT, [("Baker", "A husky deep elderly male voice")])
        assert missing2 == ["Baker"]  # was missing -> injected
        assert "The voice of Baker: A husky deep elderly male voice." in injected
        assert "subject_definitions:" in injected and "summary:" in injected

    def test_audio_definitions_appended(self):
        result = append_audio_definitions(R2V_PROMPT, [{"name": "Baker", "speaker": "(S1)"}])
        assert "<Audio 1> is the voice-timbre reference for Baker (S1)." in result
        # inserted inside subject_definitions, before summary
        assert result.index("subject_definitions:") < result.index("<Audio 1>") < result.index("summary:")

    def test_compose_end_to_end(self):
        story = {"characters": [{"name": "Baker", "voice": {"type": "text", "text": "calm, slightly raspy voice", "ref": None}}]}
        shot = {"characters": ["Baker"], "video_prompt": R2V_PROMPT}
        composed, problems = compose_video_prompt(shot, story, attached_picture_count=2, r2v_six_sections=True)
        assert problems == []
        assert composed == R2V_PROMPT.strip()  # nothing to fix (strip only)

    def test_char_limit_and_sections(self):
        assert validate_composed_prompt(R2V_PROMPT, r2v_six_sections=True) == []
        problems = validate_composed_prompt("not a valid prompt", r2v_six_sections=True)
        assert any("subject_definitions" in p for p in problems)
        problems = validate_composed_prompt("x" * (R2V_PROMPT_CHAR_LIMIT + 1))
        assert any("7000" in p for p in problems)


class TestValidatorVariants:
    def test_r2v_kind_requires_six_sections(self):
        problems = validate_video_prompt(R2V_PROMPT, prompt_kind="r2v")
        assert problems == []
        # the I2VA prompt must NOT validate as r2v (no six sections)
        i2va = ("For the target video, at 0.00 seconds into the target video, <Picture 1> is fully referenced.\n\n"
                "integrated_multimodal_description: [Shot 1] ...\n\noverall_soundscape: x\n\nnon_diegetic_music: N/A")
        assert validate_video_prompt(i2va, prompt_kind="r2v") != []

    def test_t2v_kind(self):
        t2v = ("integrated_multimodal_description: [Shot 1] Live-action, cinematic, a wide shot...\n\n"
               "overall_soundscape: wind.\n\nnon_diegetic_music: N/A")
        assert validate_video_prompt(t2v, prompt_kind="t2v") == []
        # must not demand the first-frame instruction line
        assert validate_video_prompt(t2v, prompt_kind="i2v") != []

    def test_r2v_char_cap(self):
        long_prompt = R2V_PROMPT + " " + "x" * 7000
        problems = validate_video_prompt(long_prompt, prompt_kind="r2v")
        assert any("7000" in p for p in problems)


class TestEffectiveShotsDirector:
    def test_r2v_swaps_unset_and_standard_base(self):
        assert effective_shots_director("default", "r2v") == "base/base_shots_r2v"
        assert effective_shots_director(None, "r2v") == "base/base_shots_r2v"
        assert effective_shots_director("base/base_shots_standard", "r2v") == "base/base_shots_r2v"

    def test_r2v_keeps_packs_after_base(self):
        assert (effective_shots_director(
            "base/base_shots_standard, cameras/gopro, styles/ghibli", "r2v")
            == "base/base_shots_r2v, cameras/gopro, styles/ghibli")

    def test_t2v_uses_t2v_base(self):
        assert effective_shots_director("default", "t2v") == "base/base_shots_t2v"

    def test_i2v_and_unknown_types_untouched(self):
        assert effective_shots_director("base/base_shots_standard", "i2v") == "base/base_shots_standard"
        assert effective_shots_director("default", None) == "default"
        assert effective_shots_director("default", "weird") == "default"

    def test_explicit_ref_director_untouched(self):
        assert effective_shots_director("base/base_shots_r2v", "r2v") == "base/base_shots_r2v"
