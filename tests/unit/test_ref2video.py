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
from core.director_loader import DirectorLoader
from core.shot_planner import (
    validate_video_prompt,
    effective_shots_director,
    effective_r2v_video_workflow,
    normalize_r2v_mode,
)


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

    def test_r2v_singularity_mode_targets_singularity_base(self):
        assert (effective_shots_director("default", "r2v", "singularity")
                == "base/base_shots_r2v_singularity")
        assert (effective_shots_director(None, "r2v", "singularity")
                == "base/base_shots_r2v_singularity")
        assert (effective_shots_director("base/base_shots_standard", "r2v", "singularity")
                == "base/base_shots_r2v_singularity")

    def test_r2v_mode_change_swaps_sibling_r2v_base(self):
        # switching modes after creation re-targets the matching base
        assert (effective_shots_director("base/base_shots_r2v", "r2v", "singularity")
                == "base/base_shots_r2v_singularity")
        assert (effective_shots_director("base/base_shots_r2v_singularity", "r2v", "standard")
                == "base/base_shots_r2v")

    def test_r2v_unset_or_unknown_mode_stays_standard(self):
        assert effective_shots_director("default", "r2v", None) == "base/base_shots_r2v"
        assert effective_shots_director("default", "r2v", "weird") == "base/base_shots_r2v"

    def test_r2v_singularity_keeps_packs_after_base(self):
        assert (effective_shots_director(
            "default, cameras/gopro, styles/ghibli", "r2v", "singularity")
            == "base/base_shots_r2v_singularity, cameras/gopro, styles/ghibli")

    def test_singularity_mode_ignored_for_other_types(self):
        assert effective_shots_director("default", "i2v", "singularity") == "default"
        assert effective_shots_director("default", "t2v", "singularity") == "base/base_shots_t2v"


class TestNormalizeR2vMode:
    def test_unknown_and_unset_values_resolve_to_standard(self):
        assert normalize_r2v_mode(None) == "standard"
        assert normalize_r2v_mode("") == "standard"
        assert normalize_r2v_mode("weird") == "standard"

    def test_singularity_spelling_normalized(self):
        assert normalize_r2v_mode("singularity") == "singularity"
        assert normalize_r2v_mode(" Singularity ") == "singularity"


class TestEffectiveR2vVideoWorkflow:
    _STD = "minimax_h3_r2v"
    _SING_V20 = "minimax_h3_r2v_singularity_v20_4s"

    def test_standard_mode_uses_standard_workflow(self):
        aliases = {self._STD, self._SING_V20}
        assert effective_r2v_video_workflow("standard", aliases) == self._STD
        assert effective_r2v_video_workflow(None, aliases) == self._STD

    def test_singularity_mode_prefers_v20_checkpoint(self):
        aliases = {self._STD, "minimax_h3_r2v_singularity_v13_4s",
                   "minimax_h3_r2v_singularity_v13_8s", self._SING_V20}
        assert effective_r2v_video_workflow("singularity", aliases) == self._SING_V20

    def test_singularity_mode_falls_back_to_other_singularity_variants(self):
        aliases = {self._STD, "minimax_h3_r2v_singularity_v13_4s",
                   "minimax_h3_r2v_singularity_v13_8s"}
        assert (effective_r2v_video_workflow("singularity", aliases)
                == "minimax_h3_r2v_singularity_v13_4s")

    def test_singularity_mode_falls_back_to_standard_workflow(self):
        # no Singularity checkpoint installed: prompts stay valid on the
        # standard H3 r2v model, only the tuned weights are lost
        assert effective_r2v_video_workflow("singularity", {self._STD}) == self._STD

    def test_no_r2v_workflow_available_returns_none(self):
        assert effective_r2v_video_workflow("standard", {"wan22_workflow"}) is None
        assert effective_r2v_video_workflow("singularity", {}) is None


class TestLoaderBaseOverride:
    """r2v/t2v planning must convert named directors that compose the I2VA
    base (e.g. horror_movie) by swapping that include at expansion time."""

    def test_named_director_defaults_to_i2va(self):
        prompt = DirectorLoader().load_prompt("shots", "horror_movie")
        assert "For the target video, at 0.00 seconds" in prompt
        assert "subject_definitions" not in prompt

    def test_named_director_converted_for_r2v(self):
        prompt = DirectorLoader().load_prompt(
            "shots", "horror_movie", base_override="base/base_shots_r2v")
        assert "subject_definitions" in prompt
        assert "For the target video, at 0.00 seconds" not in prompt
        # the director's own packs and input placeholder survive the swap
        assert "{USER_INPUT}" in prompt
        assert "horror" in prompt.lower()

    def test_default_director_converted_for_t2v(self):
        prompt = DirectorLoader().load_prompt(
            "shots", "default", base_override="base/base_shots_t2v")
        assert "For the target video, at 0.00 seconds" not in prompt

    def test_missing_base_include_left_alone_without_override(self):
        loader = DirectorLoader()
        default_prompt = loader.load_prompt("shots", "default")
        assert "For the target video, at 0.00 seconds" in default_prompt

    def test_named_director_passes_through_string_resolution(self):
        # string-level resolution leaves named directors alone; the loader
        # override is what converts their format
        assert effective_shots_director("horror_movie", "r2v") == "horror_movie"


class TestSingularityDirectors:
    """The r2v Singularity mode must load its own base/videoprompt pair and
    convert I2VA-composing directors with the enhanced format."""

    def test_singularity_base_loads_with_enhanced_rules(self):
        prompt = DirectorLoader().load_prompt("shots", "base/base_shots_r2v_singularity")
        assert "subject_definitions" in prompt
        assert "{USER_INPUT}" in prompt
        # enhanced-format markers from the Singularity specification
        assert "Action chains" in prompt
        assert "retention_analysis" in prompt
        assert "overall_soundscape" in prompt

    def test_named_director_converted_for_singularity(self):
        prompt = DirectorLoader().load_prompt(
            "shots", "horror_movie", base_override="base/base_shots_r2v_singularity")
        assert "subject_definitions" in prompt
        assert "For the target video, at 0.00 seconds" not in prompt
        # the director's own packs and input placeholder survive the swap
        assert "{USER_INPUT}" in prompt
        assert "horror" in prompt.lower()
        assert "Action chains" in prompt

    def test_singularity_prompt_passes_r2v_validation(self):
        # the enhanced format keeps the six named sections, so the r2v
        # structural validation accepts it unchanged
        singularity_prompt = (
            'id="x1"\n\n'
            'subject_definitions:\n<Subject 1>: the warrior in <Picture 1>\n'
            '<Environment>: the courtyard in <Picture 2>\n\n'
            'summary:\n[reference generation] the warrior charges.\n\n'
            'retention_analysis:\n<Subject 1> (appears in [Shot 1]): fully_preserved - keeps identity\n\n'
            'detailed_description:\nThe target video is live-action.\n'
            '[Shot 1] A wide shot establishes the courtyard.\n\n'
            'overall_soundscape: wind, footsteps, metal.\n\n'
            'non_diegetic_music: N/A'
        )
        assert validate_video_prompt(singularity_prompt, prompt_kind="r2v") == []
