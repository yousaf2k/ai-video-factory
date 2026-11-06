"""
Unit tests for agent sandboxed file operations + platform search.
"""
import os

import pytest

from web_ui.backend.services.agent import file_ops


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Redirect the output root and repo root into a temp sandbox."""
    output = tmp_path / "output"
    repo = tmp_path / "repo"
    (output / "projects" / "p1").mkdir(parents=True)
    (repo / "docs").mkdir(parents=True)
    (repo / ".env").write_text("SECRET=1", encoding="utf-8")
    (repo / "docs" / "guide.md").write_text("hello alpha world", encoding="utf-8")
    (output / "projects" / "p1" / "notes.txt").write_text("needle alpha here", encoding="utf-8")
    (output / "projects" / "p1" / "story.json").write_text('{"title": "alpha"}', encoding="utf-8")
    monkeypatch.setattr(file_ops.config, "ABS_OUTPUT_DIR", str(output))
    monkeypatch.setattr(file_ops.config, "ABS_PROJECTS_DIR", str(output / "projects"))
    monkeypatch.setattr(file_ops.config, "PROJECT_ROOT", str(repo))
    return {"output": output, "repo": repo}


# ------------------------------------------------------------------- sandbox

def test_write_inside_output_allowed(sandbox):
    result = file_ops.write_file("projects/p1/new.txt", "data")
    assert result["written"] is True
    assert (sandbox["output"] / "projects" / "p1" / "new.txt").read_text(encoding="utf-8") == "data"


def test_write_outside_output_denied(sandbox):
    with pytest.raises(PermissionError):
        file_ops.write_file("../../etc/evil.txt", "nope")
    with pytest.raises(PermissionError):
        file_ops.write_file("docs/steal.md", "nope")  # repo docs are read-only


def test_env_read_denied(sandbox):
    with pytest.raises(PermissionError):
        file_ops.read_file(".env")


def test_read_repo_docs_allowed(sandbox):
    result = file_ops.read_file("docs/guide.md")
    assert "hello alpha world" in result["content"]


def test_project_relative_paths(sandbox, monkeypatch):
    result = file_ops.read_file("notes.txt", project_id="p1")
    assert "needle" in result["content"]
    file_ops.write_file("extra.txt", "x", project_id="p1")
    assert (sandbox["output"] / "projects" / "p1" / "extra.txt").exists()


def test_edit_file_requires_unique_match(sandbox):
    file_ops.write_file("projects/p1/dupe.txt", "a a a")
    with pytest.raises(ValueError, match="occurs 3 times"):
        file_ops.edit_file("projects/p1/dupe.txt", "a", "b")
    result = file_ops.edit_file("projects/p1/dupe.txt", "a", "b", replace_all=True)
    assert result["replacements"] == 3
    with pytest.raises(ValueError, match="does not occur"):
        file_ops.edit_file("projects/p1/dupe.txt", "zzz", "b")


# -------------------------------------------------------------------- search

def test_search_python_fallback(sandbox, monkeypatch):
    monkeypatch.setattr(file_ops.config, "AGENT_FILE_SEARCH_USE_SHELL", False)
    result = file_ops.search_files("alpha", root="projects")
    assert result["engine"] == "python-fallback"
    assert result["count"] >= 2
    files = {m["file"] for m in result["matches"]}
    assert any(f.endswith("notes.txt") for f in files)


def test_search_shell_platform_command(sandbox, monkeypatch):
    """Search uses PowerShell on Windows / grep elsewhere (with python fallback)."""
    monkeypatch.setattr(file_ops.config, "AGENT_FILE_SEARCH_USE_SHELL", True)
    result = file_ops.search_files("needle", root="projects")
    assert result["count"] == 1
    assert result["matches"][0]["file"].endswith("notes.txt")
    assert result["engine"] in ("powershell", "grep", "python-fallback")


def test_search_glob_and_root_validation(sandbox, monkeypatch):
    monkeypatch.setattr(file_ops.config, "AGENT_FILE_SEARCH_USE_SHELL", False)
    result = file_ops.search_files("alpha", root="project", project_id="p1", file_glob="*.json")
    assert result["count"] == 1
    assert result["matches"][0]["file"].endswith("story.json")
    with pytest.raises(ValueError):
        file_ops.search_files("x", root="project")  # missing project_id
    with pytest.raises(ValueError):
        file_ops.search_files("x", root="bogus-root")


def test_delete_file_only_in_output(sandbox):
    file_ops.write_file("projects/p1/tmp.txt", "x")
    assert file_ops.delete_file("projects/p1/tmp.txt")["deleted"] is True
    with pytest.raises(PermissionError):
        file_ops.delete_file("docs/guide.md")
