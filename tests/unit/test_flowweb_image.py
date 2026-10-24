"""
Unit tests for the FlowWeb (Google Flow, flow.google.com) image mode:

- config defaults (URL, model, outputs, director mode off, timeout)
- subprocess pure helpers: text normalization, project registry round-trip,
  per-project lock acquire/release/stale-steal, selected-state heuristics
- image_generator dispatch: mode='flow' routes to generate_image_flowweb and
  reference images no longer force an auto-switch to comfyui in flow mode
- wrapper arg plumbing: model/outputs/profile flags reach the subprocess argv
"""
import os
import sys
from unittest import mock

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import config
import core.flowweb_image_subprocess as fsub
from core.image_generator import generate_image


# ── Config defaults ──────────────────────────────────────────────────────────

def test_flow_config_defaults():
    assert config.FLOWWEB_URL.startswith("https://flow.google.com")
    assert config.FLOW_IMAGE_MODEL == "Nano Banana 2.1"
    assert config.FLOW_IMAGE_OUTPUTS == "x1"
    assert config.FLOW_AGENT_MODE is False
    assert config.FLOWWEB_TIMEOUT >= 60


def test_flow_has_queue_engine_limit():
    """The queue processor resolves the engine from image_mode ('flow'); it
    must have its own entry in CONCURRENT_GENERATION_LIMITS instead of falling
    back to the default limit of 1 (which serialized all Flow shots)."""
    limits = config.CONCURRENT_GENERATION_LIMITS
    assert "flow" in limits, "flow must not fall through to the 'default' limit"
    # Flow drives the same browser worker pool as GeminiWeb
    assert limits["flow"] == limits["geminiweb"]
    assert limits["flow"] >= 1


def test_flow_choice_lists_match_flow_ui():
    assert fsub.FLOW_MODEL_CHOICES == ["Nano Banana Pro", "Nano Banana 2 Lite", "Nano Banana 2.1"]
    assert fsub.FLOW_OUTPUT_CHOICES == ["x1", "x2", "x3", "x4"]
    assert set(fsub.FLOW_ASPECT_RATIOS) == {"16:9", "4:3", "1:1", "3:4", "9:16"}


# ── Pure helpers ─────────────────────────────────────────────────────────────

def test_normalize_text_strips_emoji_and_case():
    assert fsub._normalize_text("🍌 Nano Banana 2.1") == "nano banana 2.1"
    assert fsub._normalize_text("  Outputs   per Prompt ") == "outputs per prompt"
    assert fsub._normalize_text("") == ""


def test_registry_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'OUTPUT_DIR', str(tmp_path))
    assert fsub._registry_get_project_url("proj") is None

    fsub._registry_set_project_url("proj", "https://flow.google.com/project/abc123?x=1")
    assert fsub._registry_get_project_url("proj") == "https://flow.google.com/project/abc123"

    # Non-project URLs must not be registered or returned
    fsub._registry_set_project_url("other", "https://flow.google.com/")
    assert fsub._registry_get_project_url("other") is None


def test_project_lock_acquire_release(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'OUTPUT_DIR', str(tmp_path))
    title = "locktest_project"
    try:
        assert fsub._acquire_project_lock(title) is True
        # Re-entrant: a second acquire in the same process keeps the slot
        assert fsub._acquire_project_lock(title) is True
        assert fsub._HELD_LOCK_PATH == fsub._slot_lock_path(title, 0)
    finally:
        fsub._release_project_lock(title)
    assert not os.path.exists(fsub._slot_lock_path(title, 0))
    assert fsub._HELD_LOCK_PATH is None


def test_project_lock_two_slots(tmp_path, monkeypatch):
    """FLOW_PROJECT_CONCURRENCY=2: when another worker holds slot 0, the
    second worker takes slot 1 instead of waiting."""
    monkeypatch.setattr(config, 'OUTPUT_DIR', str(tmp_path))
    monkeypatch.setattr(config, 'FLOW_PROJECT_CONCURRENCY', 2)
    title = "two_slots"
    other = fsub._slot_lock_path(title, 0)
    with open(other, 'w') as f:
        f.write("999999999 0")
    try:
        # Simulate a live holder: the dead-holder check must not steal slot 0
        with mock.patch.object(fsub, '_lock_holder_dead', return_value=False):
            assert fsub._acquire_project_lock(title, timeout=2) is True
            assert fsub._HELD_LOCK_PATH == fsub._slot_lock_path(title, 1)
    finally:
        fsub._release_project_lock(title)
    assert os.path.exists(other), "other worker's slot must stay untouched"
    os.remove(other)


def test_project_lock_steals_dead_holder(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'OUTPUT_DIR', str(tmp_path))
    title = "dead_holder"
    lock = fsub._slot_lock_path(title, 0)
    with open(lock, 'w') as f:
        f.write("999999999 0")  # PID that cannot exist on Windows/Linux CI
    # Force the dead-holder check to pass regardless of platform semantics
    with mock.patch.object(fsub, '_lock_holder_dead', return_value=True):
        assert fsub._acquire_project_lock(title, timeout=2) is True
    fsub._release_project_lock(title)
    assert not os.path.exists(lock)


def test_settings_lock_serializes(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'OUTPUT_DIR', str(tmp_path))
    title = "settings_lock"
    other = fsub._settings_lock_path(title)
    with open(other, 'w') as f:
        f.write("999999999 0")
    # Slot held by another worker -> settings lock cannot be acquired before
    # the (short) timeout, and must not steal a live-looking holder silently
    with mock.patch.object(fsub, '_lock_holder_dead', return_value=False):
        assert fsub._acquire_settings_lock(title, timeout=1) is True  # best-effort
        assert fsub._HELD_SETTINGS_LOCK is None  # proceeded WITHOUT the lock
    # Once free, it acquires
    os.remove(other)
    try:
        assert fsub._acquire_settings_lock(title, timeout=2) is True
        assert fsub._HELD_SETTINGS_LOCK == other
    finally:
        fsub._release_settings_lock(title)
    assert not os.path.exists(other)


def test_auto_name_pattern_matches_flow_timestamp_names():
    """Flow defaults new projects to names like 'Oct 16 - 12:57'; the
    rename-on-open heal must only touch those, never user-set names."""
    assert fsub._AUTO_NAME_RE.match("Oct 16 - 12:57")
    assert fsub._AUTO_NAME_RE.match("Mar 02 - 02:49")
    assert not fsub._AUTO_NAME_RE.match(
        "Luna's Departure: Earth Without a Moon - project_20261017_153734")
    assert not fsub._AUTO_NAME_RE.match("My Custom Name")


def test_candidate_attribution_prefers_own_prompt():
    """Tile labels derive from the prompt; the scorer must pick OUR tile."""
    ours = {
        'src': 'https://flow.google.com/asb/aaa',
        'w': 768, 'h': 1376,
        'label': 'Lighthouse on a cliff during a storm',
    }
    theirs = {
        'src': 'https://flow.google.com/asb/bbb',
        'w': 1376, 'h': 768,
        'label': 'Red sports car on a coastal highway',
    }
    prompt = "A lighthouse on a cliff during a storm, dramatic waves, moody sky"
    assert fsub._pick_own_candidate([theirs, ours], prompt)['src'] == ours['src']
    assert fsub._pick_own_candidate([theirs], prompt) is None  # keep waiting
    assert fsub._pick_own_candidate([], prompt) is None
    # Score itself: own tile high, foreign tile low
    assert fsub._score_candidate(ours, prompt) > 0.8
    assert fsub._score_candidate(theirs, prompt) < 0.2


def test_selected_hint_heuristics():
    assert fsub._selected_hint({'pressed': 'true'}) is True
    assert fsub._selected_hint({'checked': 'true'}) is True
    assert fsub._selected_hint({'state': 'checked'}) is True
    assert fsub._selected_hint({'cls': 'chip bg-white text-black'}) is True
    assert fsub._selected_hint({'pressed': 'false', 'cls': ''}) is False


def test_selected_hint_reads_parent_toggle_classes():
    """mat-button-toggle-checked sits on the wrapper, not the button."""
    assert fsub._selected_hint({'cls': '', 'pcls': 'mat-button-toggle checked'}) is True


def test_control_text_matches_icon_ligature_prefixes():
    """Flow toggle text concatenates the icon ligature without a space
    ('crop_16_916:9', 'imageimage'), so suffix matching is required."""
    assert fsub._control_text_matches({'text': '16:9'}, '16:9')
    assert fsub._control_text_matches({'text': 'crop_16_916:9'}, '16:9')
    assert fsub._control_text_matches({'text': 'crop_9_169:16'}, '9:16')
    assert fsub._control_text_matches({'text': 'imageimage'}, 'image')
    assert fsub._control_text_matches({'text': 'videocamvideo'}, 'video')
    assert fsub._control_text_matches({'text': 'x1'}, 'x1')
    # No cross-matches between similar ratios
    assert not fsub._control_text_matches({'text': 'crop_16_916:9'}, '9:16')
    assert not fsub._control_text_matches({'text': 'crop_9_169:16'}, '16:9')
    assert not fsub._control_text_matches({'text': 'nanobanana2.1x4'}, 'x1')


# ── _ensure_flow_project on a mocked page ────────────────────────────────────

def _mock_page_with_prompt_box():
    page = mock.MagicMock()
    box = mock.MagicMock()
    box.is_visible.return_value = True
    page.query_selector.return_value = box
    page.url = "https://flow.google.com/project/new-id"
    return page


def test_ensure_project_uses_registry_url_first(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'OUTPUT_DIR', str(tmp_path))
    fsub._registry_set_project_url("reg_proj", "https://flow.google.com/project/reg-uuid")
    page = _mock_page_with_prompt_box()

    with mock.patch.object(fsub, '_dismiss_overlays'):
        assert fsub._ensure_flow_project(page, "reg_proj") is True
    page.goto.assert_called_once_with(
        "https://flow.google.com/project/reg-uuid",
        wait_until='domcontentloaded', timeout=45000)


def test_ensure_project_creates_new_when_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'OUTPUT_DIR', str(tmp_path))
    page = _mock_page_with_prompt_box()
    # Home page has no matching card: locator count == 0
    locator = mock.MagicMock()
    locator.count.return_value = 0
    locator.is_visible.return_value = False
    page.locator.return_value = locator

    with mock.patch.object(fsub, '_dismiss_overlays'), \
         mock.patch.object(fsub, '_open_existing_project_card', return_value=False), \
         mock.patch.object(fsub, '_create_new_project', return_value=True) as create:
        assert fsub._ensure_flow_project(page, "brand_new_proj") is True
        create.assert_called_once()


# ── Dispatch ─────────────────────────────────────────────────────────────────

def test_generate_image_dispatches_flow_mode():
    with mock.patch('core.flowweb_image_generator.generate_image_flowweb') as gen:
        gen.return_value = "/tmp/out.png"
        result = generate_image("a sunset", "/tmp/out.png", mode="flow", project_title="P")
    assert result == "/tmp/out.png"
    gen.assert_called_once()
    kwargs = gen.call_args.kwargs
    assert kwargs['project_title'] == "P"


def test_generate_image_keeps_flow_mode_with_reference_images():
    """Reference images must NOT auto-switch flow mode to comfyui."""
    with mock.patch('core.flowweb_image_generator.generate_image_flowweb') as gen:
        gen.return_value = "/tmp/out.png"
        generate_image("a sunset", "/tmp/out.png", mode="flow",
                       reference_images=["/tmp/ref.png"])
    gen.assert_called_once()
    assert gen.call_args.kwargs.get('reference_image_path') == ["/tmp/ref.png"]


# ── Wrapper argv plumbing ────────────────────────────────────────────────────

def test_wrapper_builds_expected_subprocess_command(tmp_path, monkeypatch):
    out = str(tmp_path / "shot.png")
    fake_pool = mock.MagicMock()
    fake_pool.get_worker_id.return_value = 3
    monkeypatch.setattr('core.geminiweb_pool.get_worker_id', fake_pool.get_worker_id)
    monkeypatch.setattr('core.geminiweb_pool.release_worker_id', fake_pool.release_worker_id)

    run = mock.MagicMock()
    run.return_value = mock.MagicMock(returncode=0, stdout=f"SUCCESS:{out}", stderr="")
    monkeypatch.setattr('subprocess.run', run)
    real_exists = os.path.exists
    monkeypatch.setattr('os.path.exists',
                        lambda p: True if ('worker_' in str(p) or str(p) == out) else real_exists(p))
    monkeypatch.setattr('os.path.getsize', lambda p: 1234)

    from core.flowweb_image_generator import generate_image_flowweb
    result = generate_image_flowweb(
        "a cat", out, aspect_ratio="9:16", project_title="My Proj",
        reference_image_path=["/tmp/a.png", "/tmp/b.png"],
        model="Nano Banana Pro", outputs="x2")

    assert result == out
    cmd = run.call_args.args[0]
    assert "core.flowweb_image_subprocess" in cmd
    assert "a cat" in cmd
    assert cmd[cmd.index("--aspect-ratio") + 1] == "9:16"
    assert cmd[cmd.index("--project-title") + 1] == "My Proj"
    assert cmd.count("--reference-image") == 2
    assert cmd[cmd.index("--model") + 1] == "Nano Banana Pro"
    assert cmd[cmd.index("--outputs") + 1] == "x2"
    assert any("worker_3" in c for c in cmd), "worker profile must be passed"
    fake_pool.release_worker_id.assert_called_once_with(3)
