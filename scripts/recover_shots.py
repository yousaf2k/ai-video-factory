import os
import sys
import json
import glob
import uuid
from datetime import datetime

# Add project root to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import config
from core.project_manager import ProjectManager
from core.shot_planner import plan_shots
from core.story_engine import generate_shots_from_then_vs_now_story

def recover_project_shots(project_id):
    print(f"--- Starting recovery for project: {project_id} ---")
    pm = ProjectManager()
    
    # 1. Load Story
    story = pm.get_story(project_id)
    if not story:
        print(f"[ERROR] Could not load story.json for {project_id}. Recovery impossible.")
        return False
        
    print(f"[INFO] Loaded story: {story.get('title', 'Untitled')}")
    
    # 2. Generate Shots (Generate fresh metadata based on project type)
    project_type = story.get('project_type', 1)
    
    try:
        if project_type == 2: # ProjectType.THEN_VS_NOW
            print("[INFO] Project is ThenVsNow (FLFI2V). Using specialized shot generation.")
            shots = generate_shots_from_then_vs_now_story(story)
        else:
            print("[INFO] Project is Documentary. Using LLM shot planner.")
            shots = plan_shots(story)
        print(f"[SUCCESS] Generated {len(shots)} shots.")
    except Exception as e:
        print(f"[ERROR] Failed to generate shots: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 3. Process Shots (Ensure all status fields are initialized)
    shots_with_status = []
    for idx, shot in enumerate(shots, start=1):
        # Update/Ensure index and stable ID
        if 'id' not in shot:
            shot['id'] = str(uuid.uuid4())[:8]
        shot['index'] = idx
        
        # Initialize standard status fields if missing
        status_defaults = {
            'image_generated': False,
            'image_path': None,
            'image_paths': [],
            'video_rendered': False,
            'video_path': None,
            'video_paths': [],
            # FLFI2V fields
            'then_image_generated': False,
            'then_image_path': None,
            'now_image_generated': False,
            'now_image_path': None,
            'meeting_video_rendered': False,
            'meeting_video_path': None,
            'departure_video_rendered': False,
            'departure_video_path': None,
        }
        
        for key, val in status_defaults.items():
            if key not in shot:
                shot[key] = val
        
        shots_with_status.append(shot)

    # 4. Scan for existing images and videos
    print("[INFO] Scanning for existing media files...")
    images_dir = pm.get_images_dir(project_id)
    videos_dir = pm.get_videos_dir(project_id)
    
    if os.path.exists(images_dir):
        image_files = os.listdir(images_dir)
        for shot in shots_with_status:
            idx_str = f"{shot['index']:03d}"
            
            # Standard image
            pattern = f"shot_{idx_str}*.png"
            matches = glob.glob(os.path.join(images_dir, f"shot_{idx_str}_*.png"))
            matches += glob.glob(os.path.join(images_dir, f"shot_{idx_str}.png"))
            
            if matches:
                # Use the first one as primary
                primary = matches[0]
                shot['image_path'] = pm.relativize_path(primary)
                shot['image_generated'] = True
                shot['image_paths'] = [pm.relativize_path(m) for m in matches]
                print(f"  - Linked {len(matches)} images for shot {shot['index']}")

            # FLFI2V variants
            if shot['is_flfi2v']:
                # THEN
                then_matches = glob.glob(os.path.join(images_dir, f"shot_{idx_str}_then_*.png"))
                if then_matches:
                    shot['then_image_path'] = pm.relativize_path(then_matches[0])
                    shot['then_image_generated'] = True
                    print(f"  - Linked THEN image for shot {shot['index']}")
                
                # NOW
                now_matches = glob.glob(os.path.join(images_dir, f"shot_{idx_str}_now_*.png"))
                if now_matches:
                    shot['now_image_path'] = pm.relativize_path(now_matches[0])
                    shot['now_image_generated'] = True
                    print(f"  - Linked NOW image for shot {shot['index']}")

    if os.path.exists(videos_dir):
        video_files = os.listdir(videos_dir)
        for shot in shots_with_status:
            idx_str = f"{shot['index']:03d}"
            matches = glob.glob(os.path.join(videos_dir, f"shot_{idx_str}*.mp4"))
            if matches:
                shot['video_path'] = pm.relativize_path(matches[0])
                shot['video_rendered'] = True
                shot['video_paths'] = [pm.relativize_path(m) for m in matches]
                print(f"  - Linked {len(matches)} videos for shot {shot['index']}")

    # 5. Save recovered shots.json
    print(f"[INFO] Saving recovered shots.json...")
    pm.save_shots(project_id, shots_with_status)
    
    # 6. Update Meta Stats
    meta = pm.load_project(project_id)
    if meta:
        meta['stats']['total_shots'] = len(shots_with_status)
        meta['stats']['images_generated'] = sum(1 for s in shots_with_status if s['image_generated'] or s['then_image_generated'] or s['now_image_generated'])
        meta['stats']['videos_rendered'] = sum(1 for s in shots_with_status if s['video_rendered'])
        meta['steps']['shots'] = True
        pm._save_meta(project_id, meta)
        print("[SUCCESS] Project metadata updated.")

    print(f"--- Recovery complete for {project_id} ---")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/recover_shots.py <project_id>")
        sys.exit(1)
    
    pid = sys.argv[1]
    recover_project_shots(pid)
