"""
Music generation support: workflow discovery, request models, filename
versioning, and scene-graph music_prompt passthrough.
"""
import json
import os

import pytest


def test_music_workflows_discovered_from_sample_workflow():
    """The sample ACE-Step workflow must resolve prompt/lyrics/duration/output nodes."""
    import config

    assert "acestep_t2m" in config.MUSIC_WORKFLOWS
    info = config.MUSIC_WORKFLOWS["acestep_t2m"]
    assert os.path.isfile(info["workflow_path"])

    with open(info["workflow_path"], "r", encoding="utf-8") as f:
        wf = json.load(f)

    # All four roles must resolve to real nodes with the right classes
    assert info["prompt_node_id"] in wf
    assert wf[info["prompt_node_id"]]["class_type"] == "TextEncodeAceStepAudio"
    assert info["lyrics_node_id"] in wf
    assert "lyrics" in wf[info["lyrics_node_id"]]["inputs"]
    assert info["duration_node_id"] in wf
    assert wf[info["duration_node_id"]]["class_type"] == "EmptyAceStepLatentAudio"
    assert info["output_node_id"] in wf
    assert wf[info["output_node_id"]]["class_type"].startswith("SaveAudio")
    assert "filename_prefix" in wf[info["output_node_id"]]["inputs"]


def test_music_workflows_default_alias():
    import config

    assert "default" in config.MUSIC_WORKFLOWS
    assert config.MUSIC_WORKFLOWS["default"]["workflow_path"] == \
        config.MUSIC_WORKFLOWS["acestep_t2m"]["workflow_path"]


def test_music_generation_mode_config():
    import config

    assert config.MUSIC_GENERATION_MODE in ("comfyui", "geminiweb")
    assert config.MUSIC_WORKFLOW


def test_sample_workflow_json_is_valid_api_format():
    path = os.path.join(os.path.dirname(__file__), "..", "..", "workflow", "music", "acestep_t2m.json")
    with open(path, "r", encoding="utf-8") as f:
        wf = json.load(f)
    # API format: dict of node_id -> {class_type, inputs}
    assert isinstance(wf, dict)

    encoders = [n for n in wf.values() if n.get("class_type") == "TextEncodeAceStepAudio"]
    assert encoders, "TextEncodeAceStepAudio node missing"
    # Prompt input is "description" (older ComfyUI) or "tags" (0.44+); the
    # service injector supports both
    assert any("description" in n["inputs"] or "tags" in n["inputs"] for n in encoders)
    assert any("lyrics" in n["inputs"] for n in encoders)

    latents = [n for n in wf.values() if n.get("class_type") == "EmptyAceStepLatentAudio"]
    assert latents, "EmptyAceStepLatentAudio node missing"
    assert any("duration" in n["inputs"] or "seconds" in n["inputs"] for n in latents)

    savers = [n for n in wf.values() if n.get("class_type", "").startswith("SaveAudio")]
    assert savers, "SaveAudio output node missing"


def test_music_prompt_injection_matches_workflow_inputs():
    """The injector must write into an input key the workflow node actually has."""
    import config

    info = config.MUSIC_WORKFLOWS["acestep_t2m"]
    with open(info["workflow_path"], "r", encoding="utf-8") as f:
        wf = json.load(f)

    node_inputs = wf[info["prompt_node_id"]]["inputs"]
    supported = ("description", "tags", "prompt", "text")
    assert any(k in node_inputs for k in supported), \
        f"Workflow prompt node has none of {supported}: {list(node_inputs)}"


def test_regeneration_music_request_model():
    from web_ui.backend.models.shot import RegenerateMusicRequest

    req = RegenerateMusicRequest(force=True, mode="geminiweb", workflow="acestep_t2m", prompt_override="calm piano")
    assert req.force is True
    assert req.mode == "geminiweb"
    assert req.workflow == "acestep_t2m"
    assert req.prompt_override == "calm piano"

    # Defaults
    req2 = RegenerateMusicRequest()
    assert req2.force is False
    assert req2.mode is None


def test_batch_request_music_fields():
    from web_ui.backend.models.shot import BatchRegenerateRequest

    req = BatchRegenerateRequest(
        shot_ids=["abc"],
        regenerate_images=False,
        regenerate_videos=False,
        generate_music=True,
        music_mode="comfyui",
        music_workflow="acestep_t2m",
        music_prompt="epic orchestral",
    )
    assert req.generate_music is True
    assert req.music_prompt == "epic orchestral"


def test_scene_music_request_model():
    from web_ui.backend.models.story import GenerateSceneMusicRequest

    req = GenerateSceneMusicRequest(prompt_override="warm strings")
    assert req.force is False
    assert req.prompt_override == "warm strings"


def test_scene_music_fields_on_models():
    from web_ui.backend.models.story import Scene
    from web_ui.backend.models.shot import Shot

    scene = Scene(location="l", characters="c", action="a", emotion="e", narration="n")
    assert scene.music_generated is False
    assert scene.music_paths == []

    shot = Shot(index=1, image_prompt="i", motion_prompt="m", camera="c")
    assert shot.music_generated is False
    assert shot.music_prompt is None


def test_generation_type_music_value():
    from web_ui.backend.models.queue import GenerationType

    assert GenerationType.MUSIC.value == "music"


def test_scene_graph_passes_music_prompt():
    from core.scene_graph import build_scene_graph

    story = {
        "scenes": [
            {"location": "Rooftop", "action": "Chase", "emotion": "Tense",
             "characters": "Alex", "narration": "...", "music_prompt": "pulsing synths, 120 BPM"},
        ]
    }
    graph = build_scene_graph(story)
    assert len(graph) == 1
    assert graph[0]["music_prompt"] == "pulsing synths, 120 BPM"


def test_get_next_music_version(tmp_path):
    import web_ui.backend.services.generation_service as gs

    svc = object.__new__(gs.GenerationService)

    music_dir = str(tmp_path / "music")
    os.makedirs(music_dir)
    # Fresh dir -> version 1
    assert svc._get_next_music_version(music_dir, 3, kind='shot') == 1

    for name in ("shot_003_001.mp3", "shot_003_002.mp3", "shot_004_001.mp3"):
        open(os.path.join(music_dir, name), "w").close()

    assert svc._get_next_music_version(music_dir, 3, kind='shot') == 3
    assert svc._get_next_music_version(music_dir, 4, kind='shot') == 2
    assert svc._get_next_music_version(music_dir, 5, kind='shot') == 1

    # Scene counter is independent of the shot counter at the same index
    open(os.path.join(music_dir, "scene_003_005.mp3"), "w").close()
    assert svc._get_next_music_version(music_dir, 3, kind='scene') == 6
    assert svc._get_next_music_version(music_dir, 3, kind='shot') == 3

    # Uploaded files keep their original extension and count toward versions
    open(os.path.join(music_dir, "shot_003_003.wav"), "w").close()
    assert svc._get_next_music_version(music_dir, 3, kind='shot') == 4

    # kind=None matches both families
    assert svc._get_next_music_version(music_dir, 3) == 6


def test_save_uploaded_music(tmp_path, monkeypatch):
    """save_uploaded_music preserves the original extension and versions files."""
    from core.project_manager import ProjectManager
    import web_ui.backend.services.generation_service as gs

    projects_dir = str(tmp_path / "projects")
    os.makedirs(projects_dir, exist_ok=True)
    svc = object.__new__(gs.GenerationService)
    svc.project_manager = ProjectManager(projects_dir=projects_dir)

    pid = "proj_upload"
    os.makedirs(os.path.join(projects_dir, pid), exist_ok=True)

    abs_path, rel_path = svc.save_uploaded_music(pid, "shot", 2, "my song.WAV", b"RIFFdata")
    assert abs_path.endswith("shot_002_001.WAV") or abs_path.endswith("shot_002_001.wav")
    assert "music/" in rel_path.replace("\\", "/")
    assert open(abs_path, "rb").read() == b"RIFFdata"

    # Second upload bumps the version
    abs2, _ = svc.save_uploaded_music(pid, "shot", 2, "again.mp3", b"ID3")
    assert abs2.endswith("shot_002_002.mp3")

    # Unsupported format is rejected
    with pytest.raises(ValueError):
        svc.save_uploaded_music(pid, "shot", 2, "evil.exe", b"MZ")


def test_convert_music_to_mp3_copies_mp3(tmp_path):
    import shutil
    import web_ui.backend.services.generation_service as gs

    svc = object.__new__(gs.GenerationService)

    src = tmp_path / "src.mp3"
    src.write_bytes(b"ID3fakemp3data")
    dest = tmp_path / "dest.mp3"

    result = svc._convert_music_to_mp3(str(src), str(dest))
    assert result == str(dest)
    assert dest.read_bytes() == b"ID3fakemp3data"


def test_save_shots_normalization_keeps_music_fields(tmp_path, monkeypatch):
    """ProjectManager.save_shots must persist the music trio."""
    from core.project_manager import ProjectManager

    pm = ProjectManager(projects_dir=str(tmp_path))
    pid = "proj_music"
    os.makedirs(os.path.join(str(tmp_path), pid), exist_ok=True)

    shots = [{
        "scene_id": 0,
        "duration": 5,
        "image_prompt": "i",
        "motion_prompt": "m",
        "camera": "static",
        "music_prompt": "calm piano",
        "music_generated": True,
        "music_path": "output/projects/proj_music/music/shot_001_001.mp3",
    }]
    pm.save_shots(pid, shots)

    saved = pm.get_shots(pid)
    assert saved[0]["music_prompt"] == "calm piano"
    assert saved[0]["music_generated"] is True
    assert saved[0]["music_path"] == "output/projects/proj_music/music/shot_001_001.mp3"


def test_project_media_asset_ref_accepts_music_dir():
    from core.project_manager import ProjectManager

    ref = ProjectManager._project_media_asset_ref("p1", "output/projects/p1/music/shot_001_001.mp3")
    assert ref == "p/p1/music/shot_001_001.mp3"
