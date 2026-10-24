"""
Tests for the DirectorLoader and the shipped directors/ content.

Content tests load every runnable director from the real directors/ directory and
guard against the failure modes that degrade LLM prompts silently:
unresolved or circular {{include:...}} directives, missing {USER_INPUT}
placeholders, and stray content appended after the placeholder (a past bulk
edit corrupted several shots directors this way).
"""
from pathlib import Path

import pytest

from core.director_loader import DirectorLoader, DIRECTOR_TYPES, BASE_DIR_NAMES


@pytest.fixture(scope="module")
def loader():
    return DirectorLoader()


def _all_director_ids(loader):
    for director_type in DIRECTOR_TYPES:
        for director_id in loader.list_directors(director_type):
            yield director_type, director_id


def test_both_director_types_have_directors(loader):
    for director_type in DIRECTOR_TYPES:
        directors = loader.list_directors(director_type)
        assert directors, f"No directors discovered for type '{director_type}'"


def test_all_directors_resolve_includes(loader):
    """Every runnable director must expand without unresolved or circular includes."""
    for director_type, director_id in _all_director_ids(loader):
        prompt = loader.load_prompt(director_type, director_id)
        assert "<!-- Include not found" not in prompt, (
            f"{director_type}/{director_id} has an unresolved {{include:...}} directive"
        )
        assert "<!-- Circular dependency detected" not in prompt, (
            f"{director_type}/{director_id} has a circular include"
        )


def test_every_director_has_user_input_placeholder(loader):
    for director_type, director_id in _all_director_ids(loader):
        raw = loader.load_prompt_raw(director_type, director_id)
        assert "{USER_INPUT}" in raw, (
            f"{director_type}/{director_id} is missing the {{USER_INPUT}} placeholder; "
            "user input would never be injected"
        )


def test_no_content_after_last_user_input(loader):
    """Regression: corrupted directors had truncated fragments after {USER_INPUT}."""
    for director_type, director_id in _all_director_ids(loader):
        raw = loader.load_prompt_raw(director_type, director_id)
        tail = raw[raw.rfind("{USER_INPUT}") + len("{USER_INPUT}"):]
        assert tail.strip() == "", (
            f"{director_type}/{director_id} has content after the last {{USER_INPUT}}: "
            f"{tail.strip()!r}"
        )


def test_no_unresolved_include_markers_in_components(loader):
    """Base/context/style files must resolve even when loaded standalone."""
    tree = loader.list_director_tree()
    for director_type, categories in tree.items():
        for category in categories:
            for item in category["directors"] + category["base_files"]:
                file_path = Path(loader.directors_dir) / director_type / f"{item['id']}.md"
                raw = file_path.read_text(encoding="utf-8")
                # Includes resolve relative to the including file's own
                # directory chain, exactly as load_prompt does for directors.
                prompt = loader._process_includes(director_type, raw, base_dir=file_path.parent)
                assert "<!-- Include not found" not in prompt, (
                    f"{director_type}/{item['id']} references a missing include"
                )


def test_component_files_are_not_runnable_directors(loader):
    """Cameras/contexts/styles/etc. are component libraries, not directors."""
    for director_type in DIRECTOR_TYPES:
        for director_id in loader.list_directors(director_type):
            category = director_id.split("/")[0] if "/" in director_id else None
            assert category not in BASE_DIR_NAMES, (
                f"{director_type}/{director_id} is a component file but is listed as a runnable director"
            )


# --- Loader mechanics (synthetic directors dir) ---


def _make_loader(tmp_path, files: dict) -> DirectorLoader:
    directors_dir = tmp_path / "directors"
    for rel_path, content in files.items():
        path = directors_dir / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return DirectorLoader(directors_dir=str(directors_dir))


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


def test_composite_director_name_joins_prompts(tmp_path):
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
    assert data["content"].startswith("# Director:")
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
    assert "_output_format" in child_names

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
