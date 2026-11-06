"""
Sandboxed file operations for the AI Agent Assistant.

Read access: the whole repo (docs, directors, workflows, skills — read-only)
and everything under the output root (projects, assets, logs, agent data).

Write access: only the output root (projects' folders, assets, editor files).
Directors/workflows are edited through their dedicated tools instead.

The search tool uses the platform's native shell commands — PowerShell
Get-ChildItem + Select-String on Windows, grep -r on Linux/macOS — with a
pure-Python fallback if the shell is unavailable or fails.
"""
import os
import re
import subprocess
import sys
from typing import List, Optional, Tuple

import config

IS_WINDOWS = sys.platform == "win32"

# File globs the agent may never read (secrets).
_FORBIDDEN_NAMES = {".env"}

MAX_READ_CHARS = 60_000
MAX_WRITE_CHARS = 400_000


def _real(path: str) -> str:
    return os.path.realpath(os.path.abspath(path))


def _output_root() -> str:
    return _real(config.ABS_OUTPUT_DIR)


def _repo_root() -> str:
    return _real(config.PROJECT_ROOT)


def _project_dir(project_id: str) -> str:
    from core.project_manager import ProjectManager
    return _real(ProjectManager().get_project_dir(project_id))


def resolve_read_path(path: str, project_id: Optional[str] = None) -> str:
    """Resolve `path` for reading. Raises PermissionError outside allowed roots."""
    abs_path = _resolve(path, project_id)
    if os.path.basename(abs_path) in _FORBIDDEN_NAMES or abs_path.endswith(os.sep + ".env"):
        raise PermissionError("Reading .env is not allowed (contains API keys).")
    allowed = [_repo_root(), _output_root()]
    if _is_inside(abs_path, allowed):
        return abs_path
    raise PermissionError(
        f"Path '{path}' is outside the allowed read roots (repository or output folder)."
    )


# Repo locations the file tools must never write (use dedicated tools instead).
_REPO_WRITE_GUARD = {
    "docs", "directors", "workflow", "core", "web_ui", "tests", "agent_skills",
    "mcp_server", "scripts", "batch_videos.py", "projects.py", "regenerate.py",
    "run_tests.py", "config.py", "requirements.txt", "readme.md", "agents.md",
    "styles.json",
}


def resolve_write_path(path: str, project_id: Optional[str] = None) -> str:
    """Resolve `path` for writing — only inside the output root (or a project)."""
    normalized = path.replace("\\", "/").strip()
    segments = [s for s in normalized.split("/") if s not in ("", ".")]
    if ".." in segments:
        raise PermissionError("Path traversal (..) is not allowed.")
    first = segments[0].lower() if segments else ""
    if first in _REPO_WRITE_GUARD and not re.match(r"^output(/|$)", normalized, re.IGNORECASE):
        raise PermissionError(
            f"'{first}' belongs to the read-only repository area. Use the "
            "write_director / write_workflow tools for those, or prefix the path "
            "with output/ to write inside the output folder."
        )
    abs_path = _resolve(path, project_id)
    if _is_inside(abs_path, [_output_root()]):
        return abs_path
    raise PermissionError(
        f"Path '{path}' is outside the output folder. Writes are limited to the "
        f"output directory; use the director/workflow tools to edit repo files."
    )


def _resolve(path: str, project_id: Optional[str]) -> str:
    if not path or not isinstance(path, str):
        raise ValueError("A non-empty path is required.")
    path = path.replace("\\", "/").strip()
    if re.match(r"^[A-Za-z]:[\\/]", path) or path.startswith("/") or path.startswith("~"):
        expanded = os.path.expanduser(path)
    elif project_id:
        base = _project_dir(project_id)
        # output/projects/<id>/... or project-relative both resolve into the project dir.
        norm = re.sub(r"^output/projects/[^/]+/", "", path, flags=re.IGNORECASE)
        expanded = os.path.join(base, norm)
    elif re.match(r"^output(/|$)", path, flags=re.IGNORECASE):
        expanded = os.path.join(_output_root(), path[len("output"):].lstrip("/"))
    else:
        # Repo-relative (docs/..., directors/..., workflow/...) or output-relative.
        as_repo = os.path.join(_repo_root(), path)
        as_output = os.path.join(_output_root(), path)
        expanded = as_repo if os.path.exists(as_repo) else as_output
    return _real(expanded)


def _is_inside(path: str, roots: List[str]) -> bool:
    return any(path == root or path.startswith(root + os.sep) for root in roots)


# --------------------------------------------------------------------- ops
def list_dir(path: str = "", project_id: Optional[str] = None, recursive: bool = False,
             max_entries: int = 300) -> dict:
    base = resolve_read_path(path or ".", project_id)
    if not os.path.isdir(base):
        raise ValueError(f"'{path}' is not a directory.")
    entries: List[dict] = []
    if recursive:
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in {"node_modules", ".git", "__pycache__"}]
            for name in files:
                full = os.path.join(root, name)
                entries.append({
                    "path": os.path.relpath(full, base).replace("\\", "/"),
                    "size": os.path.getsize(full) if os.path.exists(full) else 0,
                })
                if len(entries) >= max_entries:
                    return {"dir": path or ".", "entries": entries, "truncated": True}
    else:
        for name in sorted(os.listdir(base)):
            full = os.path.join(base, name)
            entries.append({
                "path": name,
                "type": "dir" if os.path.isdir(full) else "file",
                "size": os.path.getsize(full) if os.path.isfile(full) else 0,
            })
            if len(entries) >= max_entries:
                break
    return {"dir": path or ".", "entries": entries, "truncated": len(entries) >= max_entries}


def read_file(path: str, project_id: Optional[str] = None, offset: int = 0,
              max_chars: Optional[int] = None) -> dict:
    abs_path = resolve_read_path(path, project_id)
    if not os.path.isfile(abs_path):
        raise ValueError(f"File not found: {path}")
    limit = min(max_chars or MAX_READ_CHARS, MAX_READ_CHARS)
    size = os.path.getsize(abs_path)
    if size > 8 * 1024 * 1024:
        raise ValueError("File too large to read (max 8 MB) — binary media should not be read.")
    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except OSError as exc:
        raise ValueError(f"Cannot read file: {exc}")
    total = len(content)
    chunk = content[offset:offset + limit]
    return {
        "path": path,
        "content": chunk,
        "offset": offset,
        "total_chars": total,
        "truncated": offset + len(chunk) < total,
    }


def write_file(path: str, content: str, project_id: Optional[str] = None) -> dict:
    if len(content or "") > MAX_WRITE_CHARS:
        raise ValueError("Content too large (max 400 KB per write).")
    abs_path = resolve_write_path(path, project_id)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content or "")
    return {"path": path, "bytes": len(content or ""), "written": True}


def edit_file(path: str, find: str, replace: str, project_id: Optional[str] = None,
              replace_all: bool = False) -> dict:
    abs_path = resolve_write_path(path, project_id)
    if not os.path.isfile(abs_path):
        raise ValueError(f"File not found: {path}")
    with open(abs_path, "r", encoding="utf-8", errors="strict") as f:
        content = f.read()
    count = content.count(find)
    if count == 0:
        raise ValueError("Text to find does not occur in the file.")
    if not replace_all and count > 1:
        raise ValueError(
            f"Text to find occurs {count} times. Pass replace_all=true or make the "
            "search text more specific."
        )
    new_content = content.replace(find, replace) if replace_all else content.replace(find, replace, 1)
    with open(abs_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(new_content)
    return {"path": path, "replacements": count if replace_all else 1}


def delete_file(path: str, project_id: Optional[str] = None) -> dict:
    """DANGEROUS: delete a file inside the output folder (no recursion)."""
    abs_path = resolve_write_path(path, project_id)
    if os.path.isdir(abs_path):
        raise ValueError("Refusing to delete a directory; delete files individually.")
    if not os.path.isfile(abs_path):
        raise ValueError(f"File not found: {path}")
    os.remove(abs_path)
    return {"path": path, "deleted": True}


# ------------------------------------------------------------------ search
_SEARCH_ROOTS = {
    "output": lambda _pid: _output_root(),
    "projects": lambda _pid: _real(config.ABS_PROJECTS_DIR),
    "project": lambda pid: _project_dir(pid) if pid else _output_root(),
    "repo": lambda _pid: _repo_root(),
    "docs": lambda _pid: os.path.join(_repo_root(), "docs"),
    "skills": lambda _pid: _real(config.AGENT_SKILLS_DIR),
}


def search_files(pattern: str, root: str = "output", project_id: Optional[str] = None,
                 file_glob: Optional[str] = None, regex: bool = False,
                 ignore_case: bool = True, max_results: int = 50) -> dict:
    """Search file CONTENTS. Uses PowerShell on Windows / grep on Linux, with
    a pure-Python fallback so the tool still works when the shell cannot run."""
    if not pattern:
        raise ValueError("Search pattern is required.")
    root_key = (root or "output").lower()
    if root_key not in _SEARCH_ROOTS:
        raise ValueError(f"root must be one of {sorted(_SEARCH_ROOTS)}")
    if root_key == "project" and not project_id:
        raise ValueError("project_id is required when root='project'.")
    base = _SEARCH_ROOTS[root_key](project_id)
    if not os.path.isdir(base):
        raise ValueError(f"Search root '{root}' does not exist on disk ({base}).")

    use_shell = config.AGENT_FILE_SEARCH_USE_SHELL
    matches: Optional[List[dict]] = None
    command_used = None
    if use_shell:
        try:
            if IS_WINDOWS:
                command_used, raw = _search_powershell(base, pattern, file_glob, regex, ignore_case, max_results)
            else:
                command_used, raw = _search_grep(base, pattern, file_glob, regex, ignore_case, max_results)
            matches = _parse_shell_matches(raw, base)
        except Exception:
            matches = None  # fall back to Python
    if matches is None:
        command_used = "python-fallback"
        matches = _search_python(base, pattern, file_glob, regex, ignore_case, max_results)

    return {
        "root": root,
        "pattern": pattern,
        "matches": matches[:max_results],
        "count": len(matches[:max_results]),
        "truncated": len(matches) > max_results,
        "engine": command_used,
    }


def _quote_ps(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _search_powershell(base, pattern, file_glob, regex, ignore_case, max_results) -> Tuple[str, str]:
    parts = [
        "Get-ChildItem -LiteralPath", _quote_ps(base), "-Recurse -File -ErrorAction SilentlyContinue"
    ]
    if file_glob:
        parts.append(f"| Where-Object {{ $_.Name -like {_quote_ps(file_glob)} }}")
    parts.append("| Select-String -Pattern " + _quote_ps(pattern))
    if not regex:
        parts.append(" -SimpleMatch")
    if not ignore_case:
        parts.append(" -CaseSensitive")
    parts.append(f"| Select-Object -First {int(max_results)}")
    parts.append("| ForEach-Object { '{0}:{1}:{2}' -f $_.Path, $_.LineNumber, ($_.Line -replace '\\r|\\n','').Trim() }")
    command = " ".join(parts)
    full = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command]
    proc = subprocess.run(full, capture_output=True, text=True, timeout=90)
    if proc.returncode not in (0, 1):
        raise RuntimeError(f"powershell exited {proc.returncode}: {proc.stderr[:400]}")
    return "powershell", proc.stdout


def _search_grep(base, pattern, file_glob, regex, ignore_case, max_results) -> Tuple[str, str]:
    cmd = ["grep", "-rn"]
    if ignore_case:
        cmd.append("-i")
    if regex:
        cmd.append("-E")
    else:
        cmd.append("-F")
    if file_glob:
        cmd += ["--include", file_glob]
    cmd += ["--", pattern, base]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    if proc.returncode not in (0, 1):
        raise RuntimeError(f"grep exited {proc.returncode}: {proc.stderr[:400]}")
    lines = proc.stdout.splitlines()
    return "grep", "\n".join(lines[:max_results])


_LINE_RE = re.compile(r"^\s*((?:[A-Za-z]:)?[\\\/]?.*?):(\d+):(.*)$")


def _parse_shell_matches(raw: str, base: str) -> List[dict]:
    """Parse `path:line:text` lines from grep / Select-String output.

    The regex keeps Windows drive-letter colons (C:\\...) out of the split.
    """
    matches: List[dict] = []
    base_norm = base.replace("\\", "/").rstrip("/") + "/"
    for line in raw.splitlines():
        if not line.strip():
            continue
        match = _LINE_RE.match(line.strip())
        if not match:
            continue
        path_part, lineno, text = match.group(1), int(match.group(2)), match.group(3)
        if not path_part:
            continue
        rel = path_part.replace("\\", "/")
        if rel.lower().startswith(base_norm.lower()):
            rel = rel[len(base_norm):]
        matches.append({"file": rel, "line": lineno, "text": text.strip()[:300]})
    return matches


def _search_python(base, pattern, file_glob, regex, ignore_case, max_results) -> List[dict]:
    flags = re.IGNORECASE if ignore_case else 0
    if regex:
        matcher = re.compile(pattern, flags)
    else:
        matcher = re.compile(re.escape(pattern), flags)

    import fnmatch
    matches: List[dict] = []
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in {"node_modules", ".git", "__pycache__"}]
        for name in files:
            if file_glob and not fnmatch.fnmatch(name, file_glob):
                continue
            full = os.path.join(root, name)
            try:
                if os.path.getsize(full) > 2 * 1024 * 1024:
                    continue
                with open(full, "r", encoding="utf-8", errors="ignore") as f:
                    for lineno, line in enumerate(f, 1):
                        if matcher.search(line):
                            matches.append({
                                "file": os.path.relpath(full, base).replace("\\", "/"),
                                "line": lineno,
                                "text": line.strip()[:300],
                            })
                            if len(matches) >= max_results:
                                return matches
            except OSError:
                continue
    return matches
