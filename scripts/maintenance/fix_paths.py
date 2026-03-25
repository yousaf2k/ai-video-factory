import json
import os
from core.project_manager import ProjectManager

project_id = 'project_20260208_015314'
project_mgr = ProjectManager()
images_dir = project_mgr.get_images_dir(project_id)

# Load shots
shots_path = os.path.join(project_mgr.get_project_dir(project_id), 'shots.json')
with open(shots_path, 'r', encoding='utf-8') as f:
    shots = json.load(f)

# Update shots with image paths
shots_with_paths = []
for idx, shot in enumerate(shots):
    shot_idx = idx + 1
    expected_filename = f'shot_{shot_idx:03d}.png'
    expected_path = os.path.join(images_dir, expected_filename)

    # Copy and add image_path with forward slashes
    shot_with_path = shot.copy()
    if os.path.exists(expected_path):
        # Normalize path to use forward slashes
        normalized_path = expected_path.replace(os.sep, '/')
        shot_with_path['image_path'] = normalized_path
        print(f'Shot {shot_idx}: {normalized_path}')

    shots_with_paths.append(shot_with_path)

# Save updated shots
with open(shots_path, 'w', encoding='utf-8') as f:
    json.dump(shots_with_paths, f, indent=2, ensure_ascii=False)

print('\n[SUCCESS] Updated shots.json with image paths')
