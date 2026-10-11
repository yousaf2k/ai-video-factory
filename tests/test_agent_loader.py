"""
Tests for the AgentLoader and the shipped agents/ content.

Content tests load every runnable agent from the real agents/ directory and
guard against the failure modes that degrade LLM prompts silently:
unresolved or circular {{include:...}} directives, missing {USER_INPUT}
placeholders, and stray content appended after the placeholder (a past bulk
edit corrupted several shots agents this way).
"""
from pathlib import Path

import pytest

from core.agent_loader import AgentLoader, AGENT_TYPES, BASE_DIR_NAMES


@pytest.fixture(scope="module")
def loader():
    return AgentLoader()


def _all_agent_ids(loader):
    for agent_type in AGENT_TYPES:
        for agent_id in loader.list_agents(agent_type):
            yield agent_type, agent_id


def test_both_agent_types_have_agents(loader):
    for agent_type in AGENT_TYPES:
        agents = loader.list_agents(agent_type)
        assert agents, f"No agents discovered for type '{agent_type}'"


def test_all_agents_resolve_includes(loader):
    """Every runnable agent must expand without unresolved or circular includes."""
    for agent_type, agent_id in _all_agent_ids(loader):
        prompt = loader.load_prompt(agent_type, agent_id)
        assert "<!-- Include not found" not in prompt, (
            f"{agent_type}/{agent_id} has an unresolved {{include:...}} directive"
        )
        assert "<!-- Circular dependency detected" not in prompt, (
            f"{agent_type}/{agent_id} has a circular include"
        )


def test_every_agent_has_user_input_placeholder(loader):
    for agent_type, agent_id in _all_agent_ids(loader):
        raw = loader.load_prompt_raw(agent_type, agent_id)
        assert "{USER_INPUT}" in raw, (
            f"{agent_type}/{agent_id} is missing the {{USER_INPUT}} placeholder; "
            "user input would never be injected"
        )


def test_no_content_after_last_user_input(loader):
    """Regression: corrupted agents had truncated fragments after {USER_INPUT}."""
    for agent_type, agent_id in _all_agent_ids(loader):
        raw = loader.load_prompt_raw(agent_type, agent_id)
        tail = raw[raw.rfind("{USER_INPUT}") + len("{USER_INPUT}"):]
        assert tail.strip() == "", (
            f"{agent_type}/{agent_id} has content after the last {{USER_INPUT}}: "
            f"{tail.strip()!r}"
        )


def test_no_unresolved_include_markers_in_components(loader):
    """Base/context/style files must resolve even when loaded standalone."""
    tree = loader.list_agent_tree()
    for agent_type, categories in tree.items():
        for category in categories:
            for item in category["agents"] + category["base_files"]:
                file_path = Path(loader.agents_dir) / agent_type / f"{item['id']}.md"
                raw = file_path.read_text(encoding="utf-8")
                # Includes resolve relative to the including file's own
                # directory chain, exactly as load_prompt does for agents.
                prompt = loader._process_includes(agent_type, raw, base_dir=file_path.parent)
                assert "<!-- Include not found" not in prompt, (
                    f"{agent_type}/{item['id']} references a missing include"
                )


def test_component_files_are_not_runnable_agents(loader):
    """Cameras/contexts/styles/etc. are component libraries, not agents."""
    for agent_type in AGENT_TYPES:
        for agent_id in loader.list_agents(agent_type):
            category = agent_id.split("/")[0] if "/" in agent_id else None
            assert category not in BASE_DIR_NAMES, (
                f"{agent_type}/{agent_id} is a component file but is listed as a runnable agent"
            )


# --- Loader mechanics (synthetic agents dir) ---


def _make_loader(tmp_path, files: dict) -> AgentLoader:
    agents_dir = tmp_path / "agents"
    for rel_path, content in files.items():
        path = agents_dir / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return AgentLoader(agents_dir=str(agents_dir))


def test_include_resolved_from_subdirectory(tmp_path):
    loader = _make_loader(tmp_path, {
        "story/_parts/shared.md": "SHARED",
        "story/main.md": "A {{include:_parts/shared}} B",
    })
    assert loader.load_prompt("story", "main") == "A SHARED B"


def test_circular_include_detected(tmp_path):
    loader = _make_loader(tmp_path, {
        "story/a.md": "A {{include:b}}",
        "story/b.md": "B {{include:a}}",
    })
    prompt = loader.load_prompt("story", "a")
    assert "A B" in prompt
    assert "<!-- Circular dependency detected: a -->" in prompt


def test_missing_include_emits_marker(tmp_path):
    loader = _make_loader(tmp_path, {
        "story/main.md": "X {{include:does_not_exist}} Y",
    })
    prompt = loader.load_prompt("story", "main")
    assert prompt == "X <!-- Include not found: does_not_exist --> Y"


def test_composite_agent_name_joins_prompts(tmp_path):
    loader = _make_loader(tmp_path, {
        "story/a.md": "PROMPT A",
        "story/b.md": "PROMPT B",
    })
    assert loader.load_prompt("story", "a,b") == "PROMPT A\n\nPROMPT B"


def test_format_prompt_replaces_all_occurrences(tmp_path):
    loader = _make_loader(tmp_path, {
        "story/main.md": "Hello {USER_INPUT} and {USER_INPUT} again",
    })
    result = loader.format_prompt("story", "WORLD", "main")
    assert result == "Hello WORLD and WORLD again"


def test_path_traversal_rejected(tmp_path):
    loader = _make_loader(tmp_path, {
        "story/main.md": "PROMPT",
        "secret.md": "SECRET",
    })
    with pytest.raises(ValueError):
        loader.load_prompt_raw("story", "../secret")
    with pytest.raises(ValueError):
        loader.save_prompt("story", "../../secret", "data")


def test_load_prompt_segments_structure(loader):
    """Preview segments split text/includes and resolve nested children."""
    data = loader.load_prompt_segments("story", "documentary/default")
    assert data["content"].startswith("# Agent:")
    assert "{{include:" not in data["expanded"]  # expanded view has directives resolved
    assert data["segments"][0]["type"] == "text"

    includes = {s["name"]: s for s in data["segments"] if s["type"] == "include"}
    assert "_base/base_standard" in includes
    assert "_styles/style_documentary" in includes

    std = includes["_base/base_standard"]
    assert std["found"] and not std["circular"]
    assert std["path"] == "story/documentary/_base/base_standard"
    # nested include inside the base file resolves as a child section
    child_names = [c["name"] for c in std["children"] if c["type"] == "include"]
    assert "_base/base_story_format" in child_names

    # the trailing text segment carries the user input placeholder
    assert data["segments"][-1]["type"] == "text"
    assert "{USER_INPUT}" in data["segments"][-1]["content"]


def test_load_prompt_segments_reports_missing_and_circular(tmp_path):
    loader = _make_loader(tmp_path, {
        "story/main.md": "A {{include:ghost}} {{include:loop}}",
        "story/loop.md": "L {{include:main}}",
    })
    data = loader.load_prompt_segments("story", "main")
    includes = {s["name"]: s for s in data["segments"] if s["type"] == "include"}

    assert not includes["ghost"]["found"]
    assert includes["ghost"]["path"] is None
    assert includes["ghost"]["children"] == []

    assert includes["loop"]["found"]
    nested = includes["loop"]["children"]
    circular = [c for c in nested if c["type"] == "include"]
    assert circular and circular[0]["name"] == "main"
    assert circular[0]["circular"]
