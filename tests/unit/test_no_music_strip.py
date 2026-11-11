"""
"No H3 Music" option: strip_non_diegetic_music removes the trailing
non_diegetic_music section from MiniMax H3 video prompts.
"""
from core.r2v_composer import strip_non_diegetic_music


def test_strips_trailing_section_i2v_format():
    prompt = (
        "For the target video, at 0.00 seconds into the target video, <Picture 1> is fully referenced.\n"
        "integrated_multimodal_description:\n"
        "[Shot 1] A soldier walks across the courtyard.\n"
        "overall_soundscape:\n"
        "Wind howling, gravel crunching, distant thunder.\n"
        "non_diegetic_music:\n"
        "Slow melancholic piano with ambient pads, 70 BPM, builds to warm strings."
    )
    cleaned = strip_non_diegetic_music(prompt)
    assert "non_diegetic_music" not in cleaned
    assert "melancholic piano" not in cleaned
    assert "overall_soundscape:" in cleaned
    assert "distant thunder" in cleaned
    assert cleaned.rstrip() == cleaned


def test_strips_section_with_same_line_content():
    prompt = (
        "integrated_multimodal_description:\n"
        "[Shot 1] The city sleeps.\n"
        "overall_soundscape: rain on asphalt\n"
        "non_diegetic_music: Uplifting orchestral score"
    )
    cleaned = strip_non_diegetic_music(prompt)
    assert "orchestral" not in cleaned
    assert "rain on asphalt" in cleaned


def test_keeps_sections_after_music_header():
    # Defensive: only the music section goes even if another section follows
    prompt = (
        "overall_soundscape:\n"
        "Wind and rain.\n"
        "non_diegetic_music:\n"
        "Dark drones.\n"
        "custom_section:\n"
        "Keep me."
    )
    cleaned = strip_non_diegetic_music(prompt)
    assert "non_diegetic_music" not in cleaned
    assert "Dark drones" not in cleaned
    assert "custom_section:" in cleaned
    assert "Keep me." in cleaned


def test_noop_when_section_absent():
    prompt = "A simple motion prompt with no H3 sections."
    assert strip_non_diegetic_music(prompt) == prompt


def test_handles_empty_and_none():
    assert strip_non_diegetic_music("") == ""
    assert strip_non_diegetic_music(None) == ""


def test_compile_workflow_receives_stripped_prompt():
    """compile_workflow re-reads video_prompt when prompt_type='video' — the
    service must strip BOTH fields so the compiled workflow gets no music."""
    import json

    import config
    from core.prompt_compiler import load_workflow, compile_workflow
    from core.r2v_composer import strip_non_diegetic_music

    music_section = (
        "\noverall_soundscape: rain on asphalt\n"
        "non_diegetic_music: Warm piano with soft ambient pads, 65 BPM."
    )
    video_prompt = (
        "integrated_multimodal_description:\n"
        "[Shot 1] The scene unfolds in the courtyard." + music_section
    )
    shot = {'index': 1, 'duration': 5, 'image_prompt': 'img',
            'motion_prompt': video_prompt, 'video_prompt': video_prompt,
            'prompt_type': 'video'}

    # Mirror the service's "No H3 Music" strip block (both fields)
    for field in ('motion_prompt', 'video_prompt'):
        shot[field] = strip_non_diegetic_music(shot.get(field) or '')

    wf_name = (config.VIDEO_WORKFLOW
               if getattr(config, 'VIDEO_WORKFLOW', None) in config.VIDEO_WORKFLOWS
               else 'default')
    wf_info = config.VIDEO_WORKFLOWS[wf_name]
    template = load_workflow(wf_info['workflow_path'], video_length_seconds=5,
                             workflow_config=wf_info)
    compiled = compile_workflow(template, shot, video_length_seconds=5,
                                workflow_config=wf_info)

    all_text = json.dumps(compiled)
    assert 'non_diegetic_music' not in all_text
    assert '[Shot 1] The scene unfolds in the courtyard.' in all_text
