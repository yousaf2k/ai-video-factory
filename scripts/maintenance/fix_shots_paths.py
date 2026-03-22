#!/usr/bin/env python3
"""
Fix shot media paths in shots.json to use consistent relative paths with 'output/projects/' prefix.
This ensures the frontend's getMediaUrl function can properly convert them to API URLs.
"""

import json
import os
import re
from pathlib import Path

def fix_shot_paths(project_path: str):
    """Fix all media paths in shots.json to use consistent 'output/projects/' prefix."""

    shots_json_path = os.path.join(project_path, "shots.json")

    if not os.path.exists(shots_json_path):
        print(f"X shots.json not found at {project_path}")
        return

    # Read current shots
    with open(shots_json_path, 'r', encoding='utf-8') as f:
        shots = json.load(f)

    # Extract project_id from path (e.g., "project_20260314_020256" from "E:/output/projects/project_20260314_020256")
    project_dir_name = os.path.basename(project_path)
    project_id = project_dir_name

    # Track changes
    changes_count = 0

    # Path fields to fix
    path_fields = [
        'image_path',
        'then_image_path',
        'now_image_path',
        'video_path',
        'meeting_video_path',
        'departure_video_path',
    ]

    list_path_fields = [
        'image_paths',
        'video_paths',
    ]

    for shot in shots:
        # Fix single path fields
        for field in path_fields:
            current_path = shot.get(field)
            if current_path:
                new_path = normalize_path(current_path, project_id)
                if new_path != current_path:
                    shot[field] = new_path
                    changes_count += 1
                    print(f"  Fixed {field} for shot {shot.get('index', '?')}: {current_path[:60]}... -> {new_path[:60]}...")

        # Fix list path fields
        for field in list_path_fields:
            current_paths = shot.get(field, [])
            if current_paths:
                new_paths = []
                for i, current_path in enumerate(current_paths):
                    new_path = normalize_path(current_path, project_id)
                    new_paths.append(new_path)
                    if new_path != current_path:
                        changes_count += 1
                        print(f"  Fixed {field}[{i}] for shot {shot.get('index', '?')}: {current_path[:60]}... -> {new_path[:60]}...")

                shot[field] = new_paths

    if changes_count > 0:
        # Backup original file
        backup_path = shots_json_path + ".backup"
        shutil.copy2(shots_json_path, backup_path)
        print(f"\nOK Backup created at {backup_path}")

        # Write updated shots
        with open(shots_json_path, 'w', encoding='utf-8') as f:
            json.dump(shots, f, indent=2, ensure_ascii=False)

        print(f"OK Fixed {changes_count} paths in {shots_json_path}")
    else:
        print("OK All paths are already in correct format")

def normalize_path(path: str, project_id: str) -> str:
    """Normalize a path to use 'output/projects/{project_id}/' prefix"""

    if not path:
        return path

    # If already starts with 'output/projects/', return as-is
    if path.startswith('output/projects/'):
        return path.replace('\\', '/')

    # Extract filename from path
    # Handles: "E:/output/projects/project_20260314_020256/images/shot_001_001.png"
    # And: "project_20260314_020256/images/shot_001_001.png"

    # Normalize slashes
    path = path.replace('\\', '/')

    # Find project_id in path
    project_idx = path.find(project_id)
    if project_idx != -1:
        # Extract everything after project_id (including project_id itself)
        relative_part = path[project_idx:]
        # Construct normalized path
        return f"output/projects/{relative_part}"

    # If project_id not found, try to extract filename and construct new path
    # Look for patterns like "shot_XXX_XXX.png" or "shot_XXX_meeting_XXX.mp4"
    filename = os.path.basename(path)

    # Try to determine if it's an image or video
    if 'video' in path.lower() or filename.endswith('.mp4'):
        subdir = 'videos'
    else:
        subdir = 'images'

    # Construct normalized path
    return f"output/projects/{project_id}/{subdir}/{filename}"

if __name__ == "__main__":
    import shutil
    import sys

    if len(sys.argv) > 1:
        project_path = sys.argv[1]
    else:
        # Default to the project mentioned in the error
        project_path = r"E:\output\projects\project_20260314_020256"

    print(f"Fixing paths in: {project_path}")
    fix_shot_paths(project_path)
    print("\nOK Done! Please refresh the browser to see changes.")
