"""
Director Loader - Load and manage system prompts for LLM directors.

Director folder structure:
directors/
├── story/
│   ├── default.md
│   ├── documentary/         # category with wrapper directors
│   │   ├── _base/           # component files (not selectable directors)
│   │   ├── _contexts/
│   │   └── _styles/
│   ├── movie/
│   ├── asmr/
│   ├── then_vs_now/
│   └── system/
└── shots/
    ├── default.md
    ├── base/                # type-level base dir (component files)
    ├── cameras/
    ├── contexts/
    ├── styles/
    ├── soundfx/
    └── videoprompt/
"""
import os
import re
from pathlib import Path
from typing import Optional, Tuple, Set
from core.logger_config import setup_director_logger
from core.log_decorators import log_director_call
import config


# Get logger for director operations
logger = setup_director_logger(__name__)


# Director types
DIRECTOR_TYPES = {
    'story': 'Story generation director',
    'shots': 'Shots prompt engineering director',
}

# Directories holding shared/base component files (not selectable as run directors)
BASE_DIR_NAMES = {"base", "common", "cameras", "contexts", "styles", "soundfx", "videoprompt"}


class DirectorLoader:
    """Load and manage director system prompts from the directors folder."""

    def __init__(self, directors_dir: str = None):
        """
        Initialize the director loader.

        Args:
            directors_dir: Path to the directors directory (default: "directors" in project root)
        """
        if directors_dir is None:
            self.directors_dir = Path(config.PROJECT_ROOT) / "directors"
        else:
            self.directors_dir = Path(directors_dir)
        
        logger.debug(f"DirectorLoader initialized with directory: {self.directors_dir}")

    def list_directors(self, director_type: str) -> list:
        """
        List all available directors for a given type.

        Args:
            director_type: Type of director ('story', 'shots')

        Returns:
            List of director names (without .md extension)
        """
        if director_type not in DIRECTOR_TYPES:
            raise ValueError(f"Unknown director type: {director_type}. Must be one of: {list(DIRECTOR_TYPES.keys())}")

        director_dir = self.directors_dir / director_type
        if not director_dir.exists():
            return []

        directors = []
        # Support both flat files and directors design nested in subdirectories
        for item in director_dir.iterdir():
            # Skip hidden folders and base/component folders (not runnable directors)
            if item.is_dir():
                if item.name.startswith(".") or self._is_base_dir(item.name):
                    continue
                
                for file in item.glob("*.md"):
                    # Skip internal/partial files starting with underscore
                    if file.name.startswith("_"):
                        continue
                    # Format as category/filename (e.g., documentary/default)
                    directors.append(f"{item.name}/{file.name[:-3]}")
            
            elif item.is_file() and item.suffix == ".md":
                # Skip internal/partial files starting with underscore
                if item.name.startswith(("_", ".")):
                    continue
                directors.append(item.stem)

                    
        return sorted(directors)

    @staticmethod
    def _file_item(director_id: str, is_base: bool, group: Optional[str] = None) -> dict:
        return {
            "id": director_id,
            "name": director_id.split("/")[-1],
            "is_base": is_base,
            "group": group,
        }

    def list_category_files(self, director_type: str, category_dir: Path, category_id: str,
                            include_base_dirs: bool = True, all_base: bool = False,
                            include_dirs: bool = True) -> dict:
        """
        Collect director and base files from a category directory.

        Files directly in the category dir are directors; files inside base dirs
        (_*, base, common) or _-prefixed files are base/component files.

        Args:
            director_type: Director type ('story', 'shots')
            category_dir: Directory to scan
            category_id: Category id used as id prefix ("" for type root)
            include_base_dirs: When False, base subdirs are skipped (they are
                listed as their own categories by list_director_tree).
            all_base: Treat every collected file as a base/component file
                (used when scanning a type-level base dir such as shots/base).
            include_dirs: When False, only files directly in category_dir are
                scanned (used for the type root so nested categories are not
                duplicated).
        """
        directors, base_files = [], []

        if not category_dir.exists():
            return {"directors": directors, "base_files": base_files}

        def add(file: Path, group: Optional[str] = None):
            rel = file.relative_to(category_dir).with_suffix("")
            director_id = "/".join(([category_id] if category_id else []) + list(rel.parts))
            item = self._file_item(director_id, all_base or group is not None)
            if group:
                item["group"] = group
            (base_files if (all_base or group is not None) else directors).append(item)

        for item in sorted(category_dir.iterdir()):
            if item.is_dir():
                if not include_dirs or item.name.startswith("."):
                    continue
                if self._is_base_dir(item.name):
                    if not include_base_dirs:
                        continue
                    for file in sorted(item.glob("*.md")):
                        if not file.name.startswith("."):
                            add(file, item.name)
                else:
                    for file in sorted(item.glob("*.md")):
                        if not file.name.startswith(("_", ".")):
                            add(file)
            elif item.is_file() and item.suffix == ".md":
                if item.name.startswith("."):
                    continue
                if item.name.startswith("_"):
                    add(item, "_root")
                else:
                    add(item)

        return {"directors": directors, "base_files": base_files}

    def list_director_tree(self) -> dict:
        """
        List all director files grouped by type and category, including base/component files.

        Used by the Web UI directors editor:
        - Each type (story/shots) contains a list of categories.
        - A category holds runnable `directors` and editable `base_files`
          (from _base/_contexts/_styles/base/common subdirs).
        - Flat .md files at the type root are grouped under the "_root" category.
        """
        tree = {}

        for director_type in DIRECTOR_TYPES:
            type_dir = self.directors_dir / director_type
            categories = []

            # Flat files at the type root become the "_root" (General) category;
            # subdirs at this level are skipped (they get their own categories)
            root_files = self.list_category_files(director_type, type_dir, "", include_dirs=False)
            if root_files["directors"] or root_files["base_files"]:
                categories.append({
                    "id": "_root",
                    "name": "General",
                    "is_base": False,
                    **root_files,
                })

            if type_dir.exists():
                for item in sorted(type_dir.iterdir()):
                    if not item.is_dir() or item.name.startswith("."):
                        continue

                    if self._is_base_dir(item.name):
                        # Base dir at type level (e.g. shots/base) -> its own category
                        files = self.list_category_files(director_type, item, item.name, all_base=True)
                        if files["directors"] or files["base_files"]:
                            categories.append({
                                "id": item.name,
                                "name": item.name.replace("_", " ").title(),
                                "is_base": True,
                                **files,
                            })
                    else:
                        files = self.list_category_files(director_type, item, item.name)
                        if files["directors"] or files["base_files"]:
                            categories.append({
                                "id": item.name,
                                "name": item.name.replace("_", " ").title(),
                                "is_base": False,
                                **files,
                            })

            tree[director_type] = categories

        return tree

    def load_prompt(self, director_type: str, director_name: str = "default") -> str:
        """
        Load a system prompt for a specific director.

        Args:
            director_type: Type of director ('story', 'shots')
            director_name: Name of the director (default: "default")

        Returns:
            The system prompt as a string

        Raises:
            FileNotFoundError: If the director file doesn't exist
            ValueError: If the director_type is invalid
        """
        if director_type not in DIRECTOR_TYPES:
            raise ValueError(f"Unknown director type: {director_type}. Must be one of: {list(DIRECTOR_TYPES.keys())}")

        # Support composite director names (comma-separated)
        if "," in director_name:
            names = [n.strip() for n in director_name.split(",")]
            contents = []
            for name in names:
                contents.append(self.load_prompt(director_type, name))
            return "\n\n".join(contents)

        director_file = self._resolve_director_file(director_type, director_name)

        if not director_file.exists():
            available = self.list_directors(director_type)
            raise FileNotFoundError(
                f"Director not found: {director_file}\n"
                f"Available {director_type} directors: {available}"
            )

        with open(director_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Process includes recursively
        # Use parent folder of director_file as initial base_dir
        return self._process_includes(director_type, content, {str(director_file.resolve())}, base_dir=director_file.parent)

    def load_prompt_segments(self, director_type: str, director_name: str = "default") -> dict:
        """
        Build a preview structure for an director file.

        Returns the raw content split into text segments and resolved
        {{include:...}} sections (expanded recursively), plus the fully
        expanded prompt. Used by the Web UI preview so every included file
        can be rendered inline as its own collapsible section.
        """
        director_file = self._resolve_director_file(director_type, director_name)

        if not director_file.exists():
            raise FileNotFoundError(f"Director file not found: {director_file}")

        with open(director_file, 'r', encoding='utf-8') as f:
            content = f.read()

        segments = self._build_segments(
            director_type, content, {str(director_file.resolve())}, director_file.parent
        )
        return {
            "content": content,
            "expanded": self.load_prompt(director_type, director_name),
            "segments": segments,
        }

    def _build_segments(self, director_type: str, content: str, seen_paths: Set[str], base_dir: Path) -> list:
        """Split content into text and include segments, expanding includes recursively."""
        segments = []
        include_pattern = re.compile(r'\{\{include:(.+?)\}\}')
        pos = 0

        for match in include_pattern.finditer(content):
            if match.start() > pos:
                segments.append({"type": "text", "content": content[pos:match.start()]})

            include_name = match.group(1).strip()
            include_file = self._resolve_include_path(include_name, base_dir, director_type)

            if include_file is None:
                segments.append({
                    "type": "include", "name": include_name, "path": None,
                    "found": False, "circular": False, "children": [],
                })
            else:
                abs_path = str(include_file.resolve())
                segment_path = self._relative_include_path(include_file)
                if abs_path in seen_paths:
                    segments.append({
                        "type": "include", "name": include_name, "path": segment_path,
                        "found": True, "circular": True, "children": [],
                    })
                else:
                    with open(include_file, 'r', encoding='utf-8') as f:
                        include_content = f.read()
                    children = self._build_segments(
                        director_type, include_content, seen_paths | {abs_path}, include_file.parent
                    )
                    segments.append({
                        "type": "include", "name": include_name, "path": segment_path,
                        "found": True, "circular": False, "children": children,
                    })
            pos = match.end()

        if pos < len(content):
            segments.append({"type": "text", "content": content[pos:]})
        return segments

    def _relative_include_path(self, path: Path) -> str:
        """Path relative to the directors dir without .md extension (for display)."""
        try:
            rel = path.resolve().relative_to(self.directors_dir.resolve())
            return str(rel.with_suffix("")).replace(os.sep, "/")
        except ValueError:
            return str(path)

    def _resolve_include_path(self, include_name: str, base_dir: Path, director_type: str) -> Optional[Path]:
        """
        Resolve an {{include:name}} directive to a file path, or None if not found.

        Search order:
        1. Global path relative to the directors root (when the name contains a slash)
        2. Direct path in the including file's directory
        3. Subdirectories of the including file's directory (e.g. _base, _styles)
        4. Direct path in the director type root
        5. Subdirectories of the director type root
        """
        paths_to_try = []
        if "/" in include_name:
            paths_to_try.append(self.directors_dir / f"{include_name}.md")

        paths_to_try.append(base_dir / f"{include_name}.md")

        if base_dir.exists():
            for item in base_dir.iterdir():
                if item.is_dir() and not item.name.startswith("."):
                    paths_to_try.append(item / f"{include_name}.md")

        director_type_dir = self.directors_dir / director_type
        paths_to_try.append(director_type_dir / f"{include_name}.md")

        if director_type_dir.exists() and director_type_dir != base_dir:
            for item in director_type_dir.iterdir():
                if item.is_dir() and not item.name.startswith("."):
                    paths_to_try.append(item / f"{include_name}.md")

        for p in paths_to_try:
            if p.exists():
                return p
        return None

    def _process_includes(self, director_type: str, content: str, seen_paths: Set[str] = None, base_dir: Path = None) -> str:
        """
        Process {{include:path}} directives in the content.
        
        Args:
            director_type: Type of director
            content: The prompt content to process
            seen_paths: Set of already seen file paths (for circular dependency protection)
            base_dir: Base directory for resolving includes (defaults to directors_dir/director_type)
            
        Returns:
            Content with inclusions resolved
        """
        if seen_paths is None:
            seen_paths = set()
        
        if base_dir is None:
            base_dir = self.directors_dir / director_type

        include_pattern = re.compile(r'\{\{include:(.+?)\}\}')
        
        def replace_include(match):
            include_name = match.group(1).strip()

            include_file = self._resolve_include_path(include_name, base_dir, director_type)

            if include_file is None:
                logger.error(f"Include file not found: {include_name}")
                return f"<!-- Include not found: {include_name} -->"

            abs_path = str(include_file.resolve())

            if abs_path in seen_paths:
                logger.warning(f"Circular dependency detected for: {abs_path}")
                return f"<!-- Circular dependency detected: {include_name} -->"

            with open(include_file, 'r', encoding='utf-8') as f:
                include_content = f.read()

            # Recursive call with new base_dir (parent of current include)
            new_seen_paths = seen_paths | {abs_path}
            return self._process_includes(director_type, include_content, new_seen_paths, base_dir=include_file.parent)

        return include_pattern.sub(replace_include, content)

    @staticmethod
    def _is_base_dir(name: str) -> bool:
        """Check if a directory holds base/component files rather than runnable directors."""
        return name.startswith("_") or name in BASE_DIR_NAMES

    def _resolve_director_file(self, director_type: str, director_name: str) -> Path:
        """Resolve an director id to a file path, ensuring it stays inside the directors dir."""
        if director_type not in DIRECTOR_TYPES:
            raise ValueError(f"Unknown director type: {director_type}. Must be one of: {list(DIRECTOR_TYPES.keys())}")

        if not director_name or director_name.strip() in ("", ".", ".."):
            raise ValueError("Invalid director name")

        director_file = (self.directors_dir / director_type / f"{director_name}.md").resolve()

        # Prevent path traversal (director ids come from the Web UI)
        type_root = (self.directors_dir / director_type).resolve()
        if not str(director_file).startswith(str(type_root) + os.sep):
            raise ValueError(f"Invalid director path: {director_name}")

        return director_file

    def load_prompt_raw(self, director_type: str, director_name: str = "default") -> str:
        """
        Load the raw content of an director file without resolving {{include:...}} directives.

        This is what editors should use - saving include-expanded content back
        to disk would destroy the modular {{include:...}} structure.
        """
        director_file = self._resolve_director_file(director_type, director_name)

        if not director_file.exists():
            raise FileNotFoundError(f"Director file not found: {director_file}")

        with open(director_file, 'r', encoding='utf-8') as f:
            return f.read()

    def save_prompt(self, director_type: str, director_name: str, content: str):
        """
        Save/update a system prompt for a specific director.

        Args:
            director_type: Type of director ('story', 'shots')
            director_name: Name of the director (may be nested, e.g. "documentary/default")
            content: The new system prompt content
        """
        director_file = self._resolve_director_file(director_type, director_name)

        director_file.parent.mkdir(parents=True, exist_ok=True)

        with open(director_file, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Saved director prompt: {director_file}")

    def format_prompt(self, director_type: str, user_input: str, director_name: str = "default") -> str:
        """
        Load and format a system prompt with user input.

        Args:
            director_type: Type of director ('story', 'shots')
            user_input: The user input to insert into the prompt
            director_name: Name of the director (default: "default")

        Returns:
            Formatted prompt with user input inserted
        """
        prompt = self.load_prompt(director_type, director_name)
        return prompt.replace("{USER_INPUT}", user_input)

    def get_director_info(self, director_type: str) -> dict:
        """
        Get information about available directors for a type.

        Args:
            director_type: Type of director

        Returns:
            Dict with 'type', 'description', and 'available_directors'
        """
        return {
            'type': director_type,
            'description': DIRECTOR_TYPES.get(director_type, ''),
            'available_directors': self.list_directors(director_type)
        }

    def print_all_directors(self):
        """Print a summary of all available directors."""
        print("\n" + "="*60)
        print("AVAILABLE DIRECTORS")
        print("="*60)

        for director_type in DIRECTOR_TYPES.keys():
            directors = self.list_directors(director_type)
            print(f"\n{director_type.upper()}: {DIRECTOR_TYPES[director_type]}")
            if directors:
                for director in directors:
                    marker = " [DEFAULT]" if director == "default" else ""
                    print(f"  - {director}{marker}")
            else:
                print(f"  (no directors found)")

        print("\n" + "="*60)


# Global director loader instance
_director_loader = None


def get_director_loader() -> DirectorLoader:
    """Get the global director loader instance."""
    global _director_loader
    if _director_loader is None:
        _director_loader = DirectorLoader()
    return _director_loader


def load_director_prompt(director_type: str, user_input: str, director_name: str = "default") -> str:
    """
    Convenience function to load and format an director prompt.

    Args:
        director_type: Type of director ('story', 'shots')
        user_input: The user input to insert into the prompt
        director_name: Name of the director (default: "default")

    Returns:
        Formatted prompt ready to send to LLM
    """
    loader = get_director_loader()
    return loader.format_prompt(director_type, user_input, director_name)


def list_directors() -> list:
    """
    List all available directors across all types.
    Used by the Web UI API.

    Returns:
        List of dictionaries with director info
    """
    loader = get_director_loader()
    all_directors = []
    
    for director_type in DIRECTOR_TYPES.keys():
        directors = loader.list_directors(director_type)
        for director_id in directors:
            all_directors.append({
                "id": director_id,
                "name": director_id.replace('_', ' ').title(),
                "type": director_type
            })
            
    return all_directors


if __name__ == "__main__":
    # Test: list all available directors
    loader = DirectorLoader()
    loader.print_all_directors()

    # Test: load a prompt
    print("\n" + "="*60)
    print("EXAMPLE: Loading story/default director")
    print("="*60)
    prompt = loader.format_prompt("story", "A cat dancing in the rain")
    print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
