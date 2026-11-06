"""
Agent Skills loader.

Skills are folders under config.AGENT_SKILLS_DIR (default: agent_skills/) that
each contain a SKILL.md file with an optional YAML frontmatter block:

    ---
    name: fix-shot-prompt
    description: How to diagnose and rewrite a shot's video prompt when the
      character action is wrong, then queue regeneration.
    ---

    ... instructions the agent should follow ...

The name/description pairs are injected into the agent system prompt; the full
content is fetched on demand through the read_skill tool. Extra files next to
SKILL.md are listed and readable too (e.g. cheat-sheets, examples).
"""
import os
import re
import shutil
import threading
from typing import Dict, List, Optional

import config

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _parse_frontmatter(content: str) -> Dict[str, str]:
    """Very small YAML subset parser: flat `key: value` lines (no nesting)."""
    meta: Dict[str, str] = {}
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return meta
    for line in match.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip().strip("'\"")
        if not key:
            continue
        if key in meta:  # multi-line folded values: append continuation lines
            meta[key] += " " + value
        else:
            meta[key] = value
    return meta


def _strip_frontmatter(content: str) -> str:
    return _FRONTMATTER_RE.sub("", content, count=1).strip()


class SkillStore:
    """Discovers and manages agent skills under the skills directory."""

    def __init__(self, root: Optional[str] = None):
        self.root = root or config.AGENT_SKILLS_DIR
        self._lock = threading.RLock()

    # ------------------------------------------------------------------ list
    def list_skills(self) -> List[Dict[str, object]]:
        with self._lock:
            skills: List[Dict[str, object]] = []
            if not os.path.isdir(self.root):
                return skills
            for entry in sorted(os.listdir(self.root)):
                skill_file = os.path.join(self.root, entry, "SKILL.md")
                if not os.path.isfile(skill_file):
                    continue
                try:
                    with open(skill_file, "r", encoding="utf-8") as f:
                        content = f.read()
                except OSError:
                    continue
                meta = _parse_frontmatter(content)
                skills.append({
                    "name": meta.get("name") or entry,
                    "description": meta.get("description", ""),
                    "dir": entry,
                })
            return skills

    # ------------------------------------------------------------------ read
    def read_skill(self, name_or_dir: str) -> Dict[str, object]:
        with self._lock:
            path = self._skill_file(name_or_dir)
            if path is None:
                raise ValueError(
                    f"Skill '{name_or_dir}' not found. Use list_skills to see available skills."
                )
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            meta = _parse_frontmatter(content)
            skill_dir = os.path.dirname(path)
            extra_files = []
            for root, _dirs, files in os.walk(skill_dir):
                for fname in files:
                    if fname == "SKILL.md":
                        continue
                    rel = os.path.relpath(os.path.join(root, fname), skill_dir).replace("\\", "/")
                    extra_files.append(rel)
            return {
                "name": meta.get("name") or os.path.basename(skill_dir),
                "description": meta.get("description", ""),
                "content": _strip_frontmatter(content),
                "files": sorted(extra_files),
            }

    def _skill_file(self, name_or_dir: str) -> Optional[str]:
        candidate = os.path.join(self.root, name_or_dir, "SKILL.md")
        if os.path.isfile(candidate):
            return candidate
        # Fall back to directory-name match when frontmatter name differs.
        if not os.path.isdir(self.root):
            return None
        for entry in os.listdir(self.root):
            skill_file = os.path.join(self.root, entry, "SKILL.md")
            if not os.path.isfile(skill_file):
                continue
            try:
                with open(skill_file, "r", encoding="utf-8") as f:
                    meta = _parse_frontmatter(f.read(2048))
            except OSError:
                continue
            if meta.get("name") == name_or_dir:
                return skill_file
        return None

    # ----------------------------------------------------------- read extras
    def read_skill_file(self, name_or_dir: str, relative_path: str) -> str:
        """Read an auxiliary file that ships inside a skill folder."""
        skill_dir = os.path.realpath(os.path.join(self.root, name_or_dir))
        target = os.path.realpath(os.path.join(skill_dir, relative_path))
        if not target.startswith(skill_dir + os.sep) or not os.path.isfile(target):
            raise ValueError(f"File '{relative_path}' not found in skill '{name_or_dir}'")
        if os.path.getsize(target) > 256 * 1024:
            raise ValueError("Skill file too large (max 256 KB)")
        with open(target, "r", encoding="utf-8") as f:
            return f.read()

    # ------------------------------------------------------------ write ops
    def create_skill(self, name: str, description: str, content: str) -> Dict[str, object]:
        if not _SAFE_NAME_RE.match(name or ""):
            raise ValueError(
                "Skill name must be letters/digits/dots/dashes/underscores "
                "(e.g. 'fix-shot-prompt')"
            )
        with self._lock:
            skill_dir = os.path.join(self.root, name)
            if os.path.exists(skill_dir):
                raise ValueError(f"Skill '{name}' already exists")
            os.makedirs(skill_dir, exist_ok=True)
            front = "---\n"
            front += f"name: {name}\n"
            front += f"description: {(description or '').replace(chr(10), ' ').strip()}\n"
            front += "---\n\n"
            with open(os.path.join(skill_dir, "SKILL.md"), "w", encoding="utf-8") as f:
                f.write(front + (content or "").strip() + "\n")
            return {"name": name, "dir": name, "created": True}

    def delete_skill(self, name_or_dir: str) -> bool:
        with self._lock:
            skill_dir = os.path.realpath(os.path.join(self.root, name_or_dir))
            skills_root = os.path.realpath(self.root)
            if not skill_dir.startswith(skills_root + os.sep) or not os.path.isdir(skill_dir):
                return False
            shutil.rmtree(skill_dir)
            return True


_store: Optional[SkillStore] = None


def get_skill_store() -> SkillStore:
    global _store
    if _store is None:
        _store = SkillStore()
    return _store
