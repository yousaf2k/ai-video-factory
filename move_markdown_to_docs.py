#!/usr/bin/env python3
"""
Move all markdown files to docs/ folder
"""
import os
import shutil
from pathlib import Path

def move_markdown_files():
    """Move all .md files from root to docs/ directory"""

    # Define paths
    project_root = Path(r'C:\AI\ai_video_factory')
    docs_dir = project_root / 'docs'

    # Create docs directory if it doesn't exist
    docs_dir.mkdir(parents=True, exist_ok=True)

    # Find all markdown files in root directory
    md_files = list(project_root.glob('*.md'))

    # Find all markdown files in subdirectories
    for subdir in ['agents', 'input']:
        subdir_path = project_root / subdir
        if subdir_path.is_dir():
            md_files.extend(subdir_path.glob('*.md'))

    print(f"Found {len(md_files)} markdown files to move")

    # Move each file
    moved_count = 0
    skipped_count = 0

    for md_file in md_files:
        # Skip if already in docs/
        if 'docs/' in str(md_file):
            print(f"  ✓ Skipping: {md_file.name} (already in docs/)")
            skipped_count += 1
            continue

        # Determine destination path
        dst = docs_dir / md_file.name

        # Move file
        try:
            shutil.move(str(md_file), str(dst))
            print(f"  OK Moved: {md_file.name}")  # ASCII-safe
            moved_count += 1
        except Exception as e:
            print(f"  X Error moving {md_file.name}: {e}")  # ASCII-safe

    print(f"\n{'='*60}")
    print(f"Results: {moved_count} moved, {skipped_count} skipped")
    print(f"{'='*60}")

if __name__ == '__main__':
    move_markdown_files()
