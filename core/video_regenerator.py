"""
Video Regenerator - Re-render videos from existing sessions
Allows changing video length or re-rendering with different settings
"""
import sys
import os
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.session_manager import SessionManager
from core.prompt_compiler import load_workflow, compile_workflow
from core.comfy_client import submit, wait_for_prompt_completion, get_output_file_path
from core.render_monitor import wait_until_idle
import config


def generate_unique_video_filename(videos_dir, shot_idx):
    """
    Generate a unique video filename based on shot index.
    If the base filename exists, appends letter suffixes (a, b, c, etc.)

    Examples:
        - shot_001.mp4 (if doesn't exist)
        - shot_001a.mp4 (if shot_001.mp4 exists)
        - shot_001b.mp4 (if shot_001a.mp4 exists)
        - shot_001c.mp4 (if shot_001b.mp4 exists)

    Args:
        videos_dir: Directory where videos are stored
        shot_idx: Shot index (1-based)

    Returns:
        tuple: (video_filename, video_save_path)
    """
    # Suffix letters to try: empty (no suffix), 'a', 'b', 'c', ..., 'z'
    suffixes = [''] + [chr(ord('a') + i) for i in range(26)]

    for suffix in suffixes:
        if suffix:
            video_filename = f"shot_{shot_idx:03d}{suffix}.mp4"
        else:
            video_filename = f"shot_{shot_idx:03d}.mp4"

        video_save_path = os.path.join(videos_dir, video_filename)

        # Check if file exists
        if not os.path.exists(video_save_path):
            return video_filename, video_save_path

    # Fallback (should never reach here with 26+ suffixes)
    # Use timestamp as last resort
    import time
    timestamp = int(time.time())
    video_filename = f"shot_{shot_idx:03d}_{timestamp}.mp4"
    video_save_path = os.path.join(videos_dir, video_filename)
    return video_filename, video_save_path


def regenerate_videos(session_id, new_shot_length=None, force_regenerate_all=False):
    """
    Regenerate videos for a session

    Args:
        session_id: Session to regenerate
        new_shot_length: New shot length in seconds (None to use existing)
        force_regenerate_all: If True, re-render all shots. If False, skip already rendered
    """
    session_mgr = SessionManager()

    print("\n" + "="*70)
    print(f"VIDEO REGENERATION: {session_id}")
    print("="*70)

    # Load session
    try:
        session_meta = session_mgr.load_session(session_id)
    except Exception as e:
        print(f"[ERROR] Could not load session: {e}")
        return False

    # Load shots data
    shots_dir = session_mgr.get_session_dir(session_id)
    shots_path = os.path.join(shots_dir, "shots.json")

    if not os.path.exists(shots_path):
        print(f"[ERROR] Shots file not found: {shots_path}")
        return False

    import json
    with open(shots_path, 'r', encoding='utf-8') as f:
        shots = json.load(f)

    # Get current video config
    video_config = session_meta.get('video_config', {})
    current_shot_length = video_config.get('shot_length', config.DEFAULT_SHOT_LENGTH)

    # Determine shot length to use
    if new_shot_length:
        shot_length = new_shot_length
        print(f"[INFO] New shot length: {shot_length}s (was {current_shot_length}s)")
    else:
        shot_length = current_shot_length
        print(f"[INFO] Using existing shot length: {shot_length}s")

    # Calculate total video length
    total_length = shot_length * len(shots)
    print(f"[INFO] Total video length: {total_length}s ({len(shots)} shots × {shot_length}s)")
    print(f"[INFO] Framerate: {config.VIDEO_FPS} fps")
    print(f"[INFO] Frames per shot: {int(shot_length * config.VIDEO_FPS)}")

    # Check which shots have images
    valid_shots = []
    for shot in shots:
        image_path = shot.get('image_path')
        if image_path:
            # Convert to absolute path if relative
            if not os.path.isabs(image_path):
                # Get absolute path relative to current directory
                abs_path = os.path.abspath(image_path)
                shot['image_path'] = abs_path

            if os.path.exists(shot['image_path']):
                valid_shots.append(shot)
            else:
                print(f"[WARN] Shot {shot.get('index', '?')}: Image file not found, skipping")
        else:
            print(f"[WARN] Shot {shot.get('index', '?')}: No image path, skipping")

    if not valid_shots:
        print("[ERROR] No shots with images found. Cannot regenerate videos.")
        return False

    print(f"\n[INFO] Found {len(valid_shots)} shots with images")

    # Load shots status from shots.json
    shots_status = session_mgr.get_shots(session_id)
    shots_status_dict = {s['index']: s for s in shots_status}

    # Determine which shots to render
    shots_to_render = []
    for shot in valid_shots:
        shot_idx = shot.get('index', 0)
        shot_meta = shots_status_dict.get(shot_idx, {})

        if force_regenerate_all:
            shots_to_render.append(shot)
        elif not shot_meta.get('video_rendered', False):
            shots_to_render.append(shot)
        else:
            # Check if we're changing video length - if so, regenerate
            if new_shot_length and new_shot_length != current_shot_length:
                shots_to_render.append(shot)
            else:
                print(f"[SKIP] Shot {shot_idx}: Already rendered (use --force to re-render)")

    if not shots_to_render:
        print("[INFO] All videos already rendered. Use --force to regenerate all.")
        return True

    print(f"\n[INFO] Will render {len(shots_to_render)} videos")

    # Confirm
    response = input("\nProceed with rendering? (y/n): ").lower().strip()
    if response != 'y' and response != 'yes':
        print("[INFO] Cancelled")
        return False

    # Load workflow with new video length
    print(f"\n[INFO] Loading workflow...")
    try:
        template = load_workflow(config.WORKFLOW_PATH, video_length_seconds=shot_length)
    except Exception as e:
        print(f"[ERROR] Failed to load workflow: {e}")
        return False

    # Submit videos with verification
    print(f"\n[INFO] Submitting to ComfyUI with verification...")

    # Track results
    successful_renders = 0
    failed_renders = 0
    errors = []

    for shot in shots_to_render:
        shot_idx = shot.get('index', 0)

        # Print image name before video generation
        image_path = shot.get('image_path', '')
        print(f"\n[PROCESS] Shot {shot_idx}: Using image '{os.path.basename(image_path)}'")

        print(f"[SUBMIT] Shot {shot_idx} ({shot_length}s)")

        try:
            wf = compile_workflow(template, shot, video_length_seconds=shot_length)
            result = submit(wf)

            prompt_id = result.get('prompt_id')
            if not prompt_id:
                print(f"[ERROR] Shot {shot_idx}: No prompt_id returned")
                failed_renders += 1
                errors.append(f"Shot {shot_idx}: No prompt_id returned")
                continue

            print(f"[QUEUE] Shot {shot_idx}: Prompt {prompt_id[:8]}... submitted")

            # Wait for completion and verify
            print(f"[WAIT] Shot {shot_idx}: Waiting for render...")
            wait_result = wait_for_prompt_completion(prompt_id, timeout=config.VIDEO_RENDER_TIMEOUT)

            if not wait_result['success']:
                error_msg = wait_result.get('error', 'Unknown error')
                print(f"[FAIL] Shot {shot_idx}: {error_msg}")
                failed_renders += 1
                errors.append(f"Shot {shot_idx}: {error_msg}")
                continue

            # Check outputs
            outputs = wait_result.get('outputs', [])
            if not outputs:
                print(f"[FAIL] Shot {shot_idx}: No output files generated")
                failed_renders += 1
                errors.append(f"Shot {shot_idx}: No output files generated")
                continue

            # Log outputs and copy to session folder
            video_outputs = [o for o in outputs if o['type'] == 'video']
            image_outputs = [o for o in outputs if o['type'] == 'image']

            if video_outputs:
                print(f"[PASS] Shot {shot_idx}: Generated {len(video_outputs)} video(s)")

                # Create session videos directory
                videos_dir = session_mgr.get_videos_dir(session_id)
                os.makedirs(videos_dir, exist_ok=True)

                # Generate unique filename to avoid overwriting existing videos
                video_info = video_outputs[0]
                video_filename, video_save_path = generate_unique_video_filename(videos_dir, shot_idx)

                source_path = get_output_file_path(video_info)
                if os.path.exists(source_path):
                    shutil.copy2(source_path, video_save_path)
                    file_size = os.path.getsize(video_save_path)
                    print(f"[COPY] Shot {shot_idx}: {video_filename} -> session/videos/")
                    print(f"       Size: {file_size:,} bytes")

                    # Mark as rendered with video path
                    session_mgr.mark_video_rendered(session_id, shot_idx, video_save_path)
                else:
                    print(f"[WARN] Source video not found: {source_path}")
                    # Mark as rendered anyway
                    session_mgr.mark_video_rendered(session_id, shot_idx)

                successful_renders += 1

            elif image_outputs:
                print(f"[PASS] Shot {shot_idx}: Generated {len(image_outputs)} frame(s)")
                for i in image_outputs[:3]:
                    print(f"       - {i['filename']}")
                if len(image_outputs) > 3:
                    print(f"       ... and {len(image_outputs) - 3} more")

                # Mark as rendered (no video file, just frames)
                session_mgr.mark_video_rendered(session_id, shot_idx)
                successful_renders += 1

        except Exception as e:
            error_msg = f"Exception: {str(e)}"
            print(f"[ERROR] Failed to submit/render shot {shot_idx}: {error_msg}")
            failed_renders += 1
            errors.append(f"Shot {shot_idx}: {error_msg}")
            import traceback
            traceback.print_exc()
            continue

    # Summary
    print("\n" + "="*70)
    print("RENDER SUMMARY")
    print("="*70)
    print(f"Successful: {successful_renders}/{len(shots_to_render)}")
    print(f"Failed: {failed_renders}/{len(shots_to_render)}")

    if errors:
        print("\n[ERRORS] Failed renders:")
        for error in errors:
            print(f"  - {error}")

    print("="*70)

    # If changing video length, update config
    if new_shot_length:
        session_meta['video_config']['shot_length'] = new_shot_length
        session_mgr._save_meta(session_id, session_meta)

    if successful_renders > 0:
        print(f"\n[SUCCESS] {successful_renders} video(s) regenerated successfully!")
        if failed_renders > 0:
            print(f"[WARNING] {failed_renders} video(s) failed. See errors above.")
        return True
    else:
        print("\n[ERROR] All renders failed!")
        return False


def interactive_regenerate():
    """Interactive menu for regenerating videos"""
    session_mgr = SessionManager()

    print("\n" + "="*70)
    print("VIDEO REGENERATION WIZARD")
    print("="*70)

    # List sessions
    sessions = session_mgr.list_all_sessions()

    if not sessions:
        print("\n[INFO] No sessions found.")
        return

    print("\nAvailable Sessions:")
    for i, session in enumerate(sessions, 1):
        status = "✓" if session['completed'] else "⏳"
        shots_count = session['stats']['total_shots']
        videos_count = session['stats']['videos_rendered']
        print(f"  {i}. {status} {session['session_id']}")
        print(f"     Idea: {session['idea'][:60]}...")
        print(f"     Shots: {shots_count}, Videos: {videos_count}")
        print()

    # Select session
    try:
        choice = input("Select session number (or 'q' to quit): ").strip()
        if choice.lower() == 'q':
            return

        session_idx = int(choice) - 1
        if session_idx < 0 or session_idx >= len(sessions):
            print("[ERROR] Invalid selection")
            return

        session_id = sessions[session_idx]['session_id']

    except ValueError:
        print("[ERROR] Invalid input")
        return

    # Get shot length
    current_session = sessions[session_idx]
    current_length = current_session.get('video_config', {}).get('shot_length', config.DEFAULT_SHOT_LENGTH)

    print(f"\n[INFO] Current shot length: {current_length}s")

    length_choice = input(f"Enter new shot length (or press Enter to keep {current_length}s): ").strip()

    if length_choice:
        try:
            new_length = float(length_choice)
        except ValueError:
            print("[ERROR] Invalid length. Using current length.")
            new_length = None
    else:
        new_length = None

    # Force regenerate all?
    force_choice = input("\nRegenerate all videos (including already rendered)? (y/n): ").lower().strip()
    force_all = force_choice == 'y' or force_choice == 'yes'

    # Show summary
    print("\n" + "="*70)
    print("REGENERATION SUMMARY")
    print("="*70)
    print(f"Session: {session_id}")
    print(f"Shot length: {new_length if new_length else current_length}s")
    print(f"Force regenerate all: {'Yes' if force_all else 'No (only missing)'}")
    print("="*70)

    # Do it
    regenerate_videos(session_id, new_shot_length=new_length, force_regenerate_all=force_all)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Regenerate videos from sessions")
    parser.add_argument('--session', type=str, help='Session ID to regenerate')
    parser.add_argument('--length', type=float, help='New shot length in seconds')
    parser.add_argument('--force', action='store_true', help='Regenerate all videos (including already rendered)')
    parser.add_argument('--interactive', action='store_true', help='Interactive mode')

    args = parser.parse_args()

    if args.interactive or not args.session:
        interactive_regenerate()
    else:
        regenerate_videos(args.session, new_shot_length=args.length, force_regenerate_all=args.force)
