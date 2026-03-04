import os
import json
import sys

# Ensure local modules can be imported
sys.path.insert(0, os.getcwd())

import config
from core.session_manager import SessionManager

def migrate_sessions():
    print("Starting session migration with path healing...")
    sm = SessionManager()
    
    sessions_dir = config.SESSIONS_DIR
    print(f"Scanning sessions in: {sessions_dir}")
    
    if not os.path.exists(sessions_dir):
        print(f"Error: Sessions directory not found: {sessions_dir}")
        return

    migrated_count = 0
    
    for root, dirs, files in os.walk(sessions_dir):
        if "shots.json" in files:
            shots_path = os.path.join(root, "shots.json")
            print(f"Processing: {shots_path}")
            
            try:
                with open(shots_path, 'r', encoding='utf-8') as f:
                    shots = json.load(f)
                
                modified = False
                for shot in shots:
                    # HEALING LOGIC:
                    # If the path is broken, try to find the file in the current session's images/videos folder
                    
                    # 1. Handle image_path healing/discovery
                    if 'image_path' in shot and shot['image_path']:
                        abs_path = config.resolve_path(shot['image_path'])
                        if not os.path.exists(abs_path):
                            filename = os.path.basename(abs_path)
                            healed_path = os.path.join(root, "images", filename)
                            if os.path.exists(healed_path):
                                print(f"  Healed image: {filename}")
                                abs_path = healed_path
                                modified = True
                        
                        new_rel = sm._relativize_path(abs_path)
                        if new_rel != shot['image_path']:
                            shot['image_path'] = new_rel
                            modified = True
                    elif shot.get('index'):
                        # DISCOVERY: If path is empty, find the first available image
                        idx = shot['index']
                        images_dir = os.path.join(root, "images")
                        if os.path.exists(images_dir):
                            shot_prefix = f"shot_{idx:03d}"
                            potential_files = [f for f in os.listdir(images_dir) if f.startswith(shot_prefix) and f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
                            if potential_files:
                                primary_filename = sorted(potential_files)[0]
                                primary_rel = sm._relativize_path(os.path.join(images_dir, primary_filename))
                                print(f"  Discovered primary image for index {idx}: {primary_filename}")
                                shot['image_path'] = primary_rel
                                shot['image_generated'] = True
                                modified = True

                    # 2. Always sync image_paths array with filesystem for every shot
                    if shot.get('index'):
                        idx = shot['index']
                        images_dir = os.path.join(root, "images")
                        if os.path.exists(images_dir):
                            shot_prefix = f"shot_{idx:03d}"
                            potential_files = [f for f in os.listdir(images_dir) if f.startswith(shot_prefix) and f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
                            
                            if potential_files:
                                if 'image_paths' not in shot or not isinstance(shot['image_paths'], list):
                                    shot['image_paths'] = []
                                
                                discovered_rels = [sm._relativize_path(os.path.join(images_dir, f)) for f in sorted(potential_files)]
                                
                                # Check if we need to add anything new
                                for rel_p in discovered_rels:
                                    if rel_p not in shot['image_paths']:
                                        shot['image_paths'].append(rel_p)
                                        modified = True
                                        print(f"  Added to image_paths for index {idx}: {os.path.basename(rel_p)}")

                    # 3. Handle image_paths healing (for existing ones)
                    if 'image_paths' in shot and shot['image_paths']:
                        new_paths = []
                        path_changed = False
                        for p in shot['image_paths']:
                            abs_p = config.resolve_path(p)
                            if not os.path.exists(abs_p):
                                filename = os.path.basename(abs_p)
                                healed_p = os.path.join(root, "images", filename)
                                if os.path.exists(healed_p):
                                    print(f"  Healed image in array: {filename}")
                                    abs_p = healed_p
                                    path_changed = True
                            
                            new_p_rel = sm._relativize_path(abs_p)
                            if new_p_rel != p:
                                path_changed = True
                            new_paths.append(new_p_rel)
                        if path_changed:
                            shot['image_paths'] = new_paths
                            modified = True
                            
                    # 3. Handle video_path
                    if 'video_path' in shot and shot['video_path']:
                        abs_v = config.resolve_path(shot['video_path'])
                        if not os.path.exists(abs_v):
                            filename = os.path.basename(abs_v)
                            healed_v = os.path.join(root, "videos", filename)
                            if os.path.exists(healed_v):
                                print(f"  Healed video: {filename}")
                                abs_v = healed_v
                                modified = True
                                
                        new_v_rel = sm._relativize_path(abs_v)
                        if new_v_rel != shot['video_path']:
                            shot['video_path'] = new_v_rel
                            modified = True
                
                if modified:
                    with open(shots_path, 'w', encoding='utf-8') as f:
                        json.dump(shots, f, indent=2, ensure_ascii=False)
                    print(f"  Successfully updated: {shots_path}")
                    migrated_count += 1
                else:
                    print(f"  No changes needed for: {shots_path}")
                    
            except Exception as e:
                print(f"  Error processing {shots_path}: {e}")

    print(f"\nMigration complete. Total files updated: {migrated_count}")

if __name__ == "__main__":
    migrate_sessions()
