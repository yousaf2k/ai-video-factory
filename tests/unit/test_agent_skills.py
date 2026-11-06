"""
Unit tests for the agent Skills store (SKILL.md discovery + CRUD).
"""
import pytest

from web_ui.backend.services.agent.skills import SkillStore


@pytest.fixture
def store(tmp_path):
    root = tmp_path / "skills"
    root.mkdir()
    (root / "alpha").mkdir()
    (root / "alpha" / "SKILL.md").write_text(
        "---\nname: alpha\ndescription: Use for alpha things.\n---\n\nDo alpha.\n",
        encoding="utf-8",
    )
    (root / "beta").mkdir()
    (root / "beta" / "SKILL.md").write_text(
        "# No frontmatter skill\n\nPlain body.\n", encoding="utf-8",
    )
    (root / "not-a-skill").mkdir()  # no SKILL.md -> ignored
    return SkillStore(root=str(root))


def test_list_skills(store):
    skills = {s["name"]: s for s in store.list_skills()}
    assert set(skills) == {"alpha", "beta"}
    assert skills["alpha"]["description"] == "Use for alpha things."
    assert skills["beta"]["description"] == ""


def test_read_skill_strips_frontmatter(store):
    skill = store.read_skill("alpha")
    assert skill["name"] == "alpha"
    assert "Do alpha." in skill["content"]
    assert "frontmatter" not in skill["content"]
    assert "---" not in skill["content"]


def test_read_skill_extra_files(store):
    from pathlib import Path
    extra = Path(store.root) / "alpha" / "notes.md"
    extra.write_text("notes body", encoding="utf-8")
    skill = store.read_skill("alpha")
    assert skill["files"] == ["notes.md"]
    assert store.read_skill_file("alpha", "notes.md") == "notes body"


def test_read_missing_skill_raises(store):
    with pytest.raises(ValueError, match="not found"):
        store.read_skill("nope")


def test_create_and_delete(store):
    store.create_skill("gamma", "Use for gamma.", "1. do gamma")
    names = {s["name"] for s in store.list_skills()}
    assert "gamma" in names
    skill = store.read_skill("gamma")
    assert skill["description"] == "Use for gamma."
    assert "do gamma" in skill["content"]
    assert store.delete_skill("gamma") is True
    assert "gamma" not in {s["name"] for s in store.list_skills()}


def test_create_skill_validates_name(store):
    with pytest.raises(ValueError, match="name"):
        store.create_skill("../escape", "desc", "body")
    with pytest.raises(ValueError, match="already exists"):
        store.create_skill("alpha", "desc", "body")


def test_read_skill_file_blocks_path_escape(store):
    with pytest.raises(ValueError):
        store.read_skill_file("alpha", "../beta/SKILL.md")
