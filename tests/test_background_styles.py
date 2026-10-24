"""Offline unit tests for the named background-style feature.

styles.json holds name/style pairs; the web UI dropdown binds to them via
GET /api/config/styles and the selected style text is appended to the end
of the background prompt at generation time.
"""
import config
from core.sheet_generator import apply_background_style, background_sheet_prompt


def test_styles_json_loads():
    styles = config.load_background_styles()
    assert styles, "styles.json should define at least one style"
    names = [s["name"] for s in styles]
    assert "Studio Ghibli" in names
    for s in styles:
        assert s.get("name") and s.get("style")


def test_styles_loader_missing_file(monkeypatch):
    monkeypatch.setattr(config, "BACKGROUND_STYLES_FILE", "Z:/nonexistent/styles.json")
    assert config.load_background_styles() == []


def test_apply_background_style_appends_at_end():
    prompt = background_sheet_prompt("a mountain village", "cinematic doc")
    styled = apply_background_style(prompt, "Studio Ghibli Style, hand-painted")
    assert styled.startswith(prompt)
    assert styled.endswith("Studio Ghibli Style, hand-painted")


def test_apply_background_style_empty_is_noop():
    prompt = background_sheet_prompt("a mountain village")
    assert apply_background_style(prompt, "") == prompt
    assert apply_background_style(prompt, None) == prompt
    assert apply_background_style(prompt, "   ") == prompt


def test_queue_item_and_requests_accept_background_style():
    from web_ui.backend.models.queue import QueueItem
    from web_ui.backend.models.queue import GenerationType
    from web_ui.backend.models.story import BackgroundGenerationRequest
    from web_ui.backend.models.shot import BatchRegenerateRequest

    item = QueueItem(
        item_id="x", project_id="p", generation_type=GenerationType.BACKGROUND,
        background_style="Studio Ghibli Style")
    assert item.background_style == "Studio Ghibli Style"

    req = BackgroundGenerationRequest(background_style="Studio Ghibli Style")
    assert req.background_style == "Studio Ghibli Style"

    batch = BatchRegenerateRequest(background_style="Studio Ghibli Style")
    assert batch.background_style == "Studio Ghibli Style"



def test_background_base_text_prefers_set_prompt():
    from core.sheet_generator import background_base_text
    scene = {
        "set_prompt": "A sunlit Lahore tea stall outside a school gate, steam rising",
        "location": "tea stall",
    }
    assert background_base_text(scene) == scene["set_prompt"]


def test_background_base_text_falls_back_to_location():
    from core.sheet_generator import background_base_text
    assert background_base_text({"location": "tea stall"}) == "tea stall"
    assert background_base_text({}) == ""


def test_story_schema_instructs_set_prompt():
    import os
    path = os.path.join("agents", "story", "_base", "base_story_format.md")
    with open(path, encoding="utf-8") as f:
        schema = f.read()
    assert '"set_prompt"' in schema
    assert "Detailed background image prompt" in schema
    # location stays a short setting name
    assert '"location": "Short name of the setting"' in schema
