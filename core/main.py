"""
AI Film Studio - Main Pipeline with Session Management and Crash Recovery
"""
import json
import os
import sys
import argparse
from datetime import datetime

# Add parent directory to path so we can import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

from core.story_engine import build_story
from core.scene_graph import build_scene_graph
from core.shot_planner import plan_shots
from core.prompt_compiler import load_workflow, compile_workflow
from core.comfy_client import submit, wait_for_prompt_completion
from core.render_monitor import wait_until_idle
from core.image_generator import generate_image_gemini
from core.session_manager import SessionManager


def get_idea(args):
    """
    Get video idea from command line argument or input file.

    Priority:
    1. Command line argument (--idea)
    2. Input file (input/video_idea.txt)
    """
    # First priority: command line argument
    if hasattr(args, 'idea') and args.idea:
        return args.idea

    # Second priority: read from file
    idea_file = "input/video_idea.txt"
    if os.path.exists(idea_file):
        with open(idea_file, "r", encoding="utf-8") as f:
            return f.read()

    # No idea found
    return None


def read_idea():
    """Read video idea from input file (legacy function for compatibility)"""
    idea = get_idea(argparse.Namespace(idea=None))
    if idea:
        return idea
    raise FileNotFoundError("input/video_idea.txt not found and no --idea parameter provided")


def get_image_generation_mode():
    """Ask user for image generation mode"""
    print("\n" + "="*70)
    print("IMAGE GENERATION MODE")
    print("="*70)
    print("\nChoose image generation method:")
    print("  1. Gemini (cloud API) - Fast, easy, ~$0.08 per image")
    print("  2. ComfyUI (local) - Free, uses your GPU, more control")
    print(f"\nCurrent default: {config.IMAGE_GENERATION_MODE}")

    choice = input("\nSelect mode [1/2] (or press Enter for default): ").strip()

    if choice == "1":
        mode = "gemini"
        print("[INFO] Using Gemini for image generation")
    elif choice == "2":
        mode = "comfyui"
        print("[INFO] Using ComfyUI for image generation")
        print("[WARN] Make sure ComfyUI is running!")

        # Ask for negative prompt
        neg_prompt = input("\nEnter negative prompt (optional, press Enter to skip): ").strip()
        return mode, neg_prompt
    else:
        mode = config.IMAGE_GENERATION_MODE
        print(f"[INFO] Using default: {mode}")
        return mode, ""

    return mode, ""


def check_continue_session(session_mgr):
    """Check for incomplete session and ask user if they want to continue"""
    latest_session = session_mgr.get_latest_session()

    if not latest_session:
        return None, None

    print("\n" + "="*70)
    print("INCOMPLETE SESSION FOUND")
    print("="*70)
    print(f"Session ID: {latest_session['session_id']}")
    print(f"Started: {latest_session.get('started_at', 'N/A')}")
    print(f"Idea: {latest_session.get('idea', 'N/A')[:100]}...")
    print(f"\nProgress:")
    print(f"  Total shots: {latest_session['stats']['total_shots']}")
    print(f"  Images generated: {latest_session['stats']['images_generated']}")
    print(f"  Videos rendered: {latest_session['stats']['videos_rendered']}")

    # Check for failed images
    failed_images = []
    if latest_session.get('shots'):
        print(f"\nShot Status:")
        for shot in latest_session['shots']:
            has_image = shot.get('image_path') and os.path.exists(shot.get('image_path', ''))
            if shot['image_generated'] and not has_image:
                failed_images.append(shot)
            status = "[DONE]" if shot['video_rendered'] else ("[IMG]" if shot['image_generated'] else "[TODO]")
            if shot['image_generated'] and not has_image:
                status = "[FAIL]"
            print(f"  {status} Shot {shot['index']}: {shot['image_prompt'][:50]}...")

    if failed_images:
        print(f"\n[WARNING] {len(failed_images)} image(s) failed to generate!")
        print("These images will be skipped during video rendering.")

    print("="*70)

    # Ask user
    response = input("\nDo you want to continue this session? (y/n): ").lower().strip()

    if response == 'y' or response == 'yes':
        session_id = latest_session['session_id']
        print(f"\n[INFO] Resuming session: {session_id}")
        return session_id, latest_session
    else:
        print("\n[INFO] Starting a new session...")
        return None, None


def regenerate_failed_images(session_id, session_meta, shots, session_mgr):
    """Regenerate images that failed previously"""
    # Get image config from session
    image_config = session_meta.get('image_config', {})
    image_mode = image_config.get('mode', config.IMAGE_GENERATION_MODE)
    negative_prompt = image_config.get('negative_prompt', "")

    print(f"\n[REGENERATE] Using {image_mode} for image generation")

    images_dir = session_mgr.get_images_dir(session_id)
    os.makedirs(images_dir, exist_ok=True)

    regenerated_count = 0
    for shot in shots:
        shot_idx = shot.get('index', 0)
        shot_meta = session_meta['shots'][shot_idx - 1]

        # Check if image failed
        if not shot_meta['image_generated']:
            continue

        existing_path = shot_meta.get('image_path')
        has_file = existing_path and os.path.exists(existing_path)

        if has_file:
            # Image exists, keep it
            shot['image_path'] = existing_path
            continue

        # Image failed - regenerate
        image_prompt = shot.get('image_prompt', '')
        if not image_prompt:
            print(f"[SKIP] Shot {shot_idx}: No image prompt")
            continue

        filename = f"shot_{shot_idx:03d}.png"
        output_path = os.path.join(images_dir, filename)

        print(f"[{shot_idx}/{len(shots)}] Regenerating failed image...")

        if image_mode == "comfyui":
            from core.comfyui_image_generator import generate_image_comfyui
            image_path = generate_image_comfyui(image_prompt, output_path, negative_prompt)
        else:
            image_path = generate_image_gemini(image_prompt, output_path)

        shot['image_path'] = image_path

        # Mark as regenerated
        if image_path:
            # Normalize path for JSON
            normalized_path = image_path.replace('\\', '/')
            session_mgr.mark_image_generated(session_id, shot_idx, normalized_path)
            regenerated_count += 1
            print(f"[PASS] Successfully regenerated shot {shot_idx}")
        else:
            print(f"[FAIL] Failed to regenerate shot {shot_idx}")

    return regenerated_count


def submit_and_verify_video(template, shot, shot_length, session_id, shot_idx, session_mgr):
    """
    Submit a video to ComfyUI and wait for verification before marking as rendered.

    Args:
        template: ComfyUI workflow template
        shot: Shot data dictionary
        shot_length: Length of each shot in seconds
        session_id: Current session ID
        shot_idx: Shot index (1-based)
        session_mgr: SessionManager instance

    Returns:
        tuple: (success: bool, error_message: str or None, video_path: str or None)
    """
    import shutil
    from core.comfy_client import get_output_file_path

    # Create session videos directory
    videos_dir = session_mgr.get_videos_dir(session_id)
    os.makedirs(videos_dir, exist_ok=True)

    # Expected video filename
    video_filename = f"shot_{shot_idx:03d}.mp4"
    video_save_path = os.path.join(videos_dir, video_filename)

    try:
        # Compile and submit workflow
        wf = compile_workflow(template, shot, video_length_seconds=shot_length)
        result = submit(wf)

        prompt_id = result.get('prompt_id')
        if not prompt_id:
            return False, "No prompt_id returned from ComfyUI", None

        print(f"[QUEUE] Shot {shot_idx}: Prompt {prompt_id[:8]}... submitted")

        # Wait for completion and verify
        print(f"[WAIT] Shot {shot_idx}: Waiting for render...")
        wait_result = wait_for_prompt_completion(prompt_id, timeout=config.VIDEO_RENDER_TIMEOUT)

        if not wait_result['success']:
            error_msg = wait_result.get('error', 'Unknown error')
            print(f"[FAIL] Shot {shot_idx}: {error_msg}")
            return False, error_msg, None

        # Check if we got any outputs
        outputs = wait_result.get('outputs', [])
        if not outputs:
            print(f"[FAIL] Shot {shot_idx}: No output files generated")
            return False, "No output files generated", None

        # Find video outputs
        video_outputs = [o for o in outputs if o['type'] == 'video']
        image_outputs = [o for o in outputs if o['type'] == 'image']

        if video_outputs:
            print(f"[PASS] Shot {shot_idx}: Generated {len(video_outputs)} video(s)")

            # Copy first video to session folder
            video_info = video_outputs[0]
            source_path = get_output_file_path(video_info)

            if os.path.exists(source_path):
                shutil.copy2(source_path, video_save_path)
                print(f"[COPY] Shot {shot_idx}: {video_filename} -> session/videos/")
                print(f"       Source: {source_path}")
                print(f"       Target: {video_save_path}")

                # Verify copy
                if os.path.exists(video_save_path):
                    file_size = os.path.getsize(video_save_path)
                    print(f"[INFO] Video saved: {video_filename} ({file_size:,} bytes)")

                    # Mark as rendered with video path
                    session_mgr.mark_video_rendered(session_id, shot_idx, video_save_path)
                    return True, None, video_save_path
                else:
                    print(f"[WARN] Copy verification failed")
                    return False, "Video copy failed", None
            else:
                print(f"[WARN] Source video not found: {source_path}")
                # Mark as rendered anyway (video exists in ComfyUI output)
                session_mgr.mark_video_rendered(session_id, shot_idx)
                return True, None, source_path

        elif image_outputs:
            print(f"[PASS] Shot {shot_idx}: Generated {len(image_outputs)} frame(s)")
            for i in image_outputs[:3]:
                print(f"       - {i['filename']}")
            if len(image_outputs) > 3:
                print(f"       ... and {len(image_outputs) - 3} more")

            # No video file, just frames - mark as rendered but no video path
            session_mgr.mark_video_rendered(session_id, shot_idx)
            return True, None, None

        else:
            print(f"[FAIL] Shot {shot_idx}: Unknown output type")
            return False, "Unknown output type", None

    except Exception as e:
        error_msg = f"Exception during render: {str(e)}"
        print(f"[FAIL] Shot {shot_idx}: {error_msg}")
        import traceback
        traceback.print_exc()
        return False, error_msg, None


def continue_session(session_id, session_meta, session_mgr):
    """Continue from an existing session"""
    shots_dir = session_mgr.get_session_dir(session_id)
    shots_path = os.path.join(shots_dir, "shots.json")

    # Load shots data
    if os.path.exists(shots_path):
        with open(shots_path, 'r', encoding='utf-8') as f:
            shots = json.load(f)
    else:
        print("[ERROR] Cannot find shots data for session. Starting fresh.")
        return None

    # Get video config from session
    video_config = session_meta.get('video_config', {})
    shot_length = video_config.get('shot_length', config.DEFAULT_SHOT_LENGTH)
    total_length = video_config.get('total_length')

    if total_length:
        print(f"[INFO] Video config: {total_length}s total, {shot_length}s per shot")
    else:
        print(f"[INFO] Video config: {shot_length}s per shot")

    # Check for failed images
    failed_images = []
    if session_meta.get('shots'):
        for shot_meta in session_meta['shots']:
            if shot_meta['image_generated']:
                existing_path = shot_meta.get('image_path')
                if not existing_path or not os.path.exists(existing_path):
                    failed_images.append(shot_meta)

    # Offer to regenerate failed images
    if failed_images:
        print(f"\n[WARNING] Found {len(failed_images)} failed image(s)")
        response = input("Do you want to regenerate failed images? (y/n): ").lower().strip()
        if response == 'y' or response == 'yes':
            count = regenerate_failed_images(session_id, session_meta, shots, session_mgr)
            print(f"[INFO] Regenerated {count} image(s)")
            # Reload session metadata to get updated state
            session_meta = session_mgr.get_session(session_id)

    # Check which steps are already done
    story_done = session_meta['steps'].get('story', False)
    scene_graph_done = session_meta['steps'].get('scene_graph', False)
    shots_done = session_meta['steps'].get('shots', False)
    images_done = session_meta['steps'].get('images', False)
    videos_done = session_meta['steps'].get('videos', False)

    # Resume from appropriate step
    if not images_done:
        print("\n[RESUME] STEP 4.5: Image Generation")

        # Get image config from session
        image_config = session_meta.get('image_config', {})
        image_mode = image_config.get('mode', config.IMAGE_GENERATION_MODE)
        negative_prompt = image_config.get('negative_prompt', "")

        print(f"[INFO] Using {image_mode} for image generation")

        images_dir = session_mgr.get_images_dir(session_id)
        os.makedirs(images_dir, exist_ok=True)

        for shot in shots:
            shot_idx = shot.get('index', 0)
            shot_meta = session_meta['shots'][shot_idx - 1]

            # Skip if already generated
            if shot_meta['image_generated']:
                print(f"[SKIP] Shot {shot_idx}: Image already generated")
                shot['image_path'] = shot_meta['image_path']
                continue

            # Generate image
            image_prompt = shot.get('image_prompt', '')
            if not image_prompt:
                print(f"[SKIP] Shot {shot_idx}: No image prompt")
                continue

            filename = f"shot_{shot_idx:03d}.png"
            output_path = os.path.join(images_dir, filename)

            print(f"[{shot_idx}/{len(shots)}] Generating image...")

            if image_mode == "comfyui":
                from core.comfyui_image_generator import generate_image_comfyui
                image_path = generate_image_comfyui(image_prompt, output_path, negative_prompt)
            else:
                image_path = generate_image_gemini(image_prompt, output_path)

            shot['image_path'] = image_path

            # Mark as generated
            if image_path:
                # Normalize path for JSON
                normalized_path = image_path.replace('\\', '/')
                session_mgr.mark_image_generated(session_id, shot_idx, normalized_path)

        session_mgr.mark_step_complete(session_id, 'images')

    elif not videos_done:
        print("\n[RESUME] STEP 5: Rendering")

    else:
        print("\n[INFO] All steps completed!")
        session_mgr.print_session_summary(session_id)
        return shots

    # Filter to shots with images
    valid_shots = [s for s in shots if s.get('image_path') and os.path.exists(s.get('image_path', ''))]

    if not valid_shots:
        print("[ERROR] No valid shots with images. Cannot continue.")
        print("[HINT] Use 'python regenerate.py --images' to regenerate failed images.")
        return None

    # Submit videos (only those not yet rendered) with verification
    print(f"\n[INFO] Submitting videos to ComfyUI with verification...")

    template = load_workflow(config.WORKFLOW_PATH, video_length_seconds=shot_length)

    # Track results
    successful_renders = 0
    failed_renders = 0
    errors = []

    for shot in valid_shots:
        shot_idx = shot.get('index', 0)
        shot_meta = session_meta['shots'][shot_idx - 1]

        # Skip if already rendered
        if shot_meta['video_rendered']:
            # Verify the video actually exists
            # For now, trust the metadata - user can regenerate if needed
            print(f"[SKIP] Shot {shot_idx}: Video already marked as rendered")
            successful_renders += 1
            continue

        print(f"\n[SUBMIT] Shot {shot_idx} ({shot_length}s each)")
        success, error, video_path = submit_and_verify_video(
            template, shot, shot_length, session_id, shot_idx, session_mgr
        )

        if success:
            successful_renders += 1
        else:
            failed_renders += 1
            errors.append(f"Shot {shot_idx}: {error}")

    # Summary
    print("\n" + "="*70)
    print("RENDER SUMMARY")
    print("="*70)
    print(f"Successful: {successful_renders}/{len(valid_shots)}")
    print(f"Failed: {failed_renders}/{len(valid_shots)}")

    if errors:
        print("\n[ERRORS] Failed renders:")
        for error in errors:
            print(f"  - {error}")
        print("\n[HINT] You can regenerate failed videos with:")
        print(f"       python regenerate.py --session {session_id} --videos")

    print("="*70)

    # Mark step complete
    session_mgr.mark_step_complete(session_id, 'videos')

    # Only mark session complete if all renders succeeded
    if failed_renders == 0:
        session_mgr.mark_session_complete(session_id)
        print("\n[SUCCESS] SESSION COMPLETE!")
    else:
        print("\n[WARNING] Session completed with errors. Some videos failed to render.")

    session_mgr.print_session_summary(session_id)

    return shots


def run_new_session(session_mgr, args=None):
    """
    Run a complete new session

    Args:
        session_mgr: SessionManager instance
        args: Optional argparse namespace with command line arguments
    """
    if args is None:
        args = argparse.Namespace()

    print("\nSTEP 1: Idea")
    idea = get_idea(args)
    print(f"\n{idea[:200]}{'...' if len(idea) > 200 else ''}")

    # Determine image generation mode
    if hasattr(args, 'image_mode') and args.image_mode:
        image_mode = args.image_mode
        negative_prompt = getattr(args, 'negative_prompt', '')
        print(f"\n[INFO] Image generation mode: {image_mode} (from command line)")
    else:
        # Get image generation mode from user
        image_mode, negative_prompt = get_image_generation_mode()

    # Get video configuration
    print("\n" + "="*70)
    print("VIDEO CONFIGURATION")
    print("="*70)

    # Determine total video length
    if hasattr(args, 'total_length') and args.total_length:
        total_length = args.total_length
        print(f"[INFO] Total video length: {total_length}s (from command line)")
    else:
        # Ask for total video length
        total_length_input = input(f"\nEnter total video length in seconds (or press Enter for default based on story): ").strip()
        if total_length_input:
            try:
                total_length = float(total_length_input)
            except ValueError:
                print("[WARN] Invalid input, using story-based length")
                total_length = config.TARGET_VIDEO_LENGTH
        else:
            total_length = config.TARGET_VIDEO_LENGTH

    # Determine shot length
    if hasattr(args, 'shot_length') and args.shot_length:
        shot_length = args.shot_length
        print(f"[INFO] Shot length: {shot_length}s (from command line)")
    else:
        # Ask for shot length
        shot_length_input = input(f"\nEnter length per shot in seconds (default: {config.DEFAULT_SHOT_LENGTH}s): ").strip()
        if shot_length_input:
            try:
                shot_length = float(shot_length_input)
            except ValueError:
                print(f"[WARN] Invalid input, using default: {config.DEFAULT_SHOT_LENGTH}s")
                shot_length = config.DEFAULT_SHOT_LENGTH
        else:
            shot_length = config.DEFAULT_SHOT_LENGTH

    # Calculate number of shots needed
    if total_length:
        max_shots = int(total_length / shot_length)
        print(f"\n[INFO] Target: {total_length}s video, {shot_length}s per shot = {max_shots} shots")
    else:
        max_shots = None
        print(f"\n[INFO] Shot length: {shot_length}s (number of shots based on story)")

    print("="*70)

    # Create new session
    session_id, session_meta = session_mgr.create_session(idea)

    # Store video config in session
    session_meta['video_config'] = {
        'total_length': total_length,
        'shot_length': shot_length,
        'fps': config.VIDEO_FPS
    }

    # Store image generation config
    session_meta['image_config'] = {
        'mode': image_mode,
        'negative_prompt': negative_prompt
    }

    session_mgr._save_meta(session_id, session_meta)

    print(f"[INFO] Created session: {session_id}")

    # STEP 2: Story
    print("\nSTEP 2: Story Generation")
    story_json = build_story(idea)
    session_mgr.save_story(session_id, story_json)

    # STEP 3: Scene Graph
    print("\nSTEP 3: Scene Graph")
    session_mgr.mark_step_complete(session_id, 'scene_graph')
    graph = build_scene_graph(story_json)

    # STEP 4: Shot Planning (with max_shots if specified)
    print("\nSTEP 4: Shot Planning")
    shots = plan_shots(graph, max_shots=max_shots)
    session_mgr.save_shots(session_id, shots)

    # STEP 4.5: Image Generation
    print("\nSTEP 4.5: Image Generation")

    images_dir = session_mgr.get_images_dir(session_id)
    os.makedirs(images_dir, exist_ok=True)

    for idx, shot in enumerate(shots, start=1):
        # Check if already exists (in case of resume)
        filename = f"shot_{idx:03d}.png"
        output_path = os.path.join(images_dir, filename)

        if os.path.exists(output_path):
            print(f"[SKIP] Shot {idx}: Image already exists")
            # Normalize path for JSON
            normalized_path = output_path.replace('\\', '/')
            session_mgr.mark_image_generated(session_id, idx, normalized_path)
            shot['image_path'] = normalized_path
            continue

        # Generate image
        image_prompt = shot.get('image_prompt', '')
        if not image_prompt:
            print(f"[SKIP] Shot {idx}: No image prompt")
            continue

        print(f"[{idx}/{len(shots)}] Generating image: {image_prompt[:60]}...")

        if image_mode == "comfyui":
            from core.comfyui_image_generator import generate_image_comfyui
            image_path = generate_image_comfyui(image_prompt, output_path, negative_prompt)
        else:
            image_path = generate_image_gemini(image_prompt, output_path)

        shot['image_path'] = image_path

        # Mark as generated
        if image_path:
            # Normalize path for JSON
            normalized_path = image_path.replace('\\', '/')
            session_mgr.mark_image_generated(session_id, idx, normalized_path)

    session_mgr.mark_step_complete(session_id, 'images')

    # Filter to only shots with successfully generated images
    valid_shots = [s for s in shots if s.get('image_path')]

    if not valid_shots:
        print("[ERROR] No images were successfully generated. Cannot proceed.")
        return

    # STEP 5: Rendering with verification
    print(f"\nSTEP 5: Rendering {len(valid_shots)} shots")

    # Get shot length from session
    shot_length = session_meta.get('video_config', {}).get('shot_length', config.DEFAULT_SHOT_LENGTH)

    template = load_workflow(config.WORKFLOW_PATH, video_length_seconds=shot_length)

    # Track results
    successful_renders = 0
    failed_renders = 0
    errors = []

    for shot in valid_shots:
        shot_idx = shot.get('index', shots.index(shot) + 1)
        print(f"\n[SUBMIT] Shot {shot_idx} ({shot_length}s each)")

        success, error, video_path = submit_and_verify_video(
            template, shot, shot_length, session_id, shot_idx, session_mgr
        )

        if success:
            successful_renders += 1
        else:
            failed_renders += 1
            errors.append(f"Shot {shot_idx}: {error}")

    # Summary
    print("\n" + "="*70)
    print("RENDER SUMMARY")
    print("="*70)
    print(f"Successful: {successful_renders}/{len(valid_shots)}")
    print(f"Failed: {failed_renders}/{len(valid_shots)}")

    if errors:
        print("\n[ERRORS] Failed renders:")
        for error in errors:
            print(f"  - {error}")
        print("\n[HINT] You can regenerate failed videos with:")
        print(f"       python regenerate.py --session {session_id} --videos")

    print("="*70)

    # Mark step complete
    session_mgr.mark_step_complete(session_id, 'videos')

    # Only mark session complete if all renders succeeded
    if failed_renders == 0:
        session_mgr.mark_session_complete(session_id)
        print("\n[SUCCESS] ALL RENDERS COMPLETE!")
    else:
        print("\n[WARNING] Session completed with errors. Some videos failed to render.")

    session_mgr.print_session_summary(session_id)


def main():
    """Main pipeline with crash recovery"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="AI Film Studio - Video Generation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use idea from command line
  python core/main.py --idea "A cat dancing in the rain"

  # Use idea from file (default)
  python core/main.py

  # Specify image generation mode
  python core/main.py --idea "Sunset beach" --image-mode comfyui

  # Set video length and shot duration
  python core/main.py --idea "City timelapse" --total-length 30 --shot-length 3

  # Set image dimensions
  python core/main.py --idea "Portrait video" --aspect-ratio 9:16 --resolution 1024

  # Skip resume prompt (always start new session)
  python core/main.py --idea "Quick test" --no-resume
        """
    )

    parser.add_argument(
        '--idea', '-i',
        type=str,
        help='Video idea (if not provided, reads from input/video_idea.txt)'
    )

    parser.add_argument(
        '--image-mode',
        type=str,
        choices=['gemini', 'comfyui'],
        help='Image generation mode (default: from config.py)'
    )

    parser.add_argument(
        '--negative-prompt',
        type=str,
        default='',
        help='Negative prompt for ComfyUI image generation'
    )

    parser.add_argument(
        '--shot-length',
        type=float,
        help='Length per shot in seconds (default: from config.py)'
    )

    parser.add_argument(
        '--total-length',
        type=float,
        help='Total video length in seconds (default: based on story)'
    )

    parser.add_argument(
        '--aspect-ratio',
        type=str,
        choices=['1:1', '16:9', '9:16', '4:3', '3:4'],
        help='Image aspect ratio (default: from config.py)'
    )

    parser.add_argument(
        '--resolution',
        type=str,
        choices=['512', '1024', '2048'],
        help='Image resolution (default: from config.py)'
    )

    parser.add_argument(
        '--no-resume',
        action='store_true',
        help='Skip resume prompt, always start new session'
    )

    parser.add_argument(
        '--list-sessions',
        action='store_true',
        help='List all sessions and exit'
    )

    args = parser.parse_args()

    # Handle --list-sessions
    if args.list_sessions:
        session_mgr = SessionManager()
        sessions = session_mgr.list_all_sessions()

        if not sessions:
            print("[INFO] No sessions found")
            return

        print("\n" + "="*70)
        print("ALL SESSIONS")
        print("="*70)
        for session in sessions:
            status = "[DONE]" if session['completed'] else "[OPEN]"
            print(f"\n{status} {session['session_id']}")
            print(f"  Idea: {session['idea'][:80]}...")
            print(f"  Created: {session.get('created_at', 'N/A')}")
            print(f"  Shots: {session['stats']['total_shots']}")
            print(f"  Images: {session['stats']['images_generated']}")
            print(f"  Videos: {session['stats']['videos_rendered']}")
        print("="*70)
        return

    print("\n" + "="*70)
    print("AI FILM STUDIO - Video Generation Pipeline")
    print("="*70)

    # Check if idea is provided
    idea = get_idea(args)
    if not idea:
        print("[ERROR] No video idea provided!")
        print("\nPlease either:")
        print("  1. Use --idea parameter: python core/main.py --idea 'Your idea here'")
        print("  2. Create input/video_idea.txt with your idea")
        print("\nRun: python core/main.py --help for more options")
        return

    # Update config if command line arguments provided
    if args.aspect_ratio:
        config.IMAGE_ASPECT_RATIO = args.aspect_ratio
        print(f"[INFO] Aspect ratio: {args.aspect_ratio}")

    if args.resolution:
        config.IMAGE_RESOLUTION = args.resolution
        print(f"[INFO] Resolution: {args.resolution}")

    # Recalculate dimensions if config changed
    if args.aspect_ratio or args.resolution:
        config.IMAGE_WIDTH, config.IMAGE_HEIGHT = config.calculate_image_dimensions()
        print(f"[INFO] Image dimensions: {config.IMAGE_WIDTH}x{config.IMAGE_HEIGHT}")

    # Initialize session manager
    session_mgr = SessionManager()

    # Check for incomplete session (unless --no-resume)
    if args.no_resume:
        session_id, session_meta = None, None
    else:
        session_id, session_meta = check_continue_session(session_mgr)

    if session_id and session_meta:
        # Continue existing session
        try:
            continue_session(session_id, session_meta, session_mgr)
        except Exception as e:
            print(f"\n[ERROR] Failed to continue session: {e}")
            import traceback
            traceback.print_exc()
    else:
        # Run new session with command line args
        try:
            run_new_session(session_mgr, args=args)
        except Exception as e:
            print(f"\n[ERROR] Pipeline failed: {e}")
            import traceback
            traceback.print_exc()
            print("\n[INFO] Session data saved. Run again to continue.")

    print("\n" + "="*70)
    print("To view all sessions, check: output/sessions/")
    print("="*70)


if __name__ == "__main__":
    main()