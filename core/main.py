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

# Workflow steps definition
# Note: Idea is step 1, but we start tracking from story (step 2)
# Narration text is generated during story creation (step 2)
# Step 7 only handles TTS conversion (text-to-speech)
WORKFLOW_STEPS = {
    'story': 2,
    'scene_graph': 3,
    'shots': 4,
    'images': 5,
    'videos': 6,
    'narration': 7  # Narration TTS (text already in shots from story)
}

STEP_NAMES = {
    1: 'idea',          # Not tracked in session steps
    2: 'story',         # Includes narration text per scene
    3: 'scene_graph',
    4: 'shots',         # Includes narration from story scenes
    5: 'images',
    6: 'videos',
    7: 'narration_tts'  # TTS conversion only
}

from core.story_engine import build_story
from core.scene_graph import build_scene_graph
from core.shot_planner import plan_shots
from core.prompt_compiler import load_workflow, compile_workflow
from core.comfy_client import submit, wait_for_prompt_completion
from core.render_monitor import wait_until_idle
from core.image_generator import generate_image_gemini
from core.session_manager import SessionManager


def enhance_motion_prompts_with_triggers(shots):
    """
    Append trigger keywords to motion prompts for each shot based on camera type.
    This helps activate the correct LoRA during video generation.

    Args:
        shots: List of shot dictionaries with 'camera' and 'motion_prompt' fields

    Returns:
        Updated shots list with enhanced motion prompts
    """
    for shot in shots:
        camera_type = shot.get('camera', 'default')
        motion_prompt = shot.get('motion_prompt', '')

        if not motion_prompt:
            continue

        # Get trigger keyword for this camera type
        lora_mapping = config.CAMERA_LORA_MAPPING
        trigger_keyword = ""

        camera_type_lower = camera_type.lower() if camera_type else "default"

        # Check if mapping is dict (new-style) or string (old-style)
        if camera_type_lower in lora_mapping:
            mapping = lora_mapping[camera_type_lower]
            if isinstance(mapping, dict):
                trigger_keyword = mapping.get("trigger_keyword", "")
        else:
            # Try partial match
            for key, value in lora_mapping.items():
                if key != "default" and key in camera_type_lower:
                    if isinstance(value, dict):
                        trigger_keyword = value.get("trigger_keyword", "")
                    break

        # Append trigger keyword to motion prompt
        if trigger_keyword:
            enhanced_prompt = f"{motion_prompt}, {trigger_keyword}"
            shot['motion_prompt'] = enhanced_prompt
            print(f"[TRIGGER] Shot {shot.get('index', '?')}: '{camera_type}' -> '{trigger_keyword}'")

    return shots


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


def prompt_step_action(current_step, session_id, session_mgr):
    """
    Prompt user for action after completing a step in manual mode.

    Args:
        current_step: The step that just completed (2-7)
        session_id: Current session ID
        session_mgr: SessionManager instance

    Returns:
        str: User's choice - 'continue', 'retry', or 'quit'
    """
    step_name = STEP_NAMES.get(current_step, 'unknown')
    step_map = {
        'idea': 'Idea Input',
        'story': 'Story Generation',
        'scene_graph': 'Scene Graph',
        'shots': 'Shot Planning',
        'images': 'Image Generation',
        'videos': 'Video Rendering',
        'narration': 'Narration TTS'
    }
    step_title = step_map.get(step_name, step_name.title())

    # Get current progress
    meta = session_mgr.get_session(session_id)
    steps = meta.get('steps', {})

    print("\n" + "="*70)
    print(f"STEP {current_step} COMPLETED: {step_title}")
    print("="*70)
    print(f"\nCurrent Progress:")
    for step_num, step_key in STEP_NAMES.items():
        if step_num == 1:  # Skip idea for display
            continue
        status = "[DONE]" if steps.get(step_key, False) else "[TODO]"
        marker = " <-" if step_key == step_name else ""
        print(f"  Step {step_num}: {step_key.replace('_', ' ').title():20s} {status}{marker}")

    print("\n" + "="*70)
    print("OPTIONS:")
    print("  1. Continue to next step")
    print("  2. Re-execute current step")
    print("  3. Re-execute from a specific step")
    print("  4. Quit (save progress)")
    print("="*70)

    while True:
        choice = input("\nSelect option [1/2/3/4]: ").strip().lower()

        if choice in ('1', 'continue', 'c', 'next'):
            return 'continue'
        elif choice in ('2', 'retry', 'r', 're-execute'):
            return 'retry'
        elif choice in ('3', 'from', 'f', 'restart'):
            # Ask which step to start from
            print("\nSelect step to restart from:")
            for step_num, step_key in STEP_NAMES.items():
                if step_num == 1:  # Skip idea
                    continue
                is_done = steps.get(step_key, False)
                status = ""
                if is_done:
                    status = " (already done - will re-execute)"
                print(f"  {step_num}. {step_key.replace('_', ' ').title()}{status}")

            while True:
                step_choice = input(f"\nEnter step number [2-{len(STEP_NAMES)}]: ").strip()
                try:
                    step_num = int(step_choice)
                    if 2 <= step_num <= len(STEP_NAMES):
                        return f'restart:{step_num}'
                    else:
                        print(f"[WARN] Please enter a number between 2 and {len(STEP_NAMES)}")
                except ValueError:
                    print("[WARN] Please enter a valid number")

        elif choice in ('4', 'quit', 'q', 'exit'):
            return 'quit'
        else:
            print("[WARN] Invalid choice. Please enter 1, 2, 3, or 4")


def get_start_step(args, session_meta=None):
    """
    Determine which step to start from.

    Args:
        args: Command line arguments
        session_meta: Session metadata (for resume)

    Returns:
        int: Starting step number (1-6)
    """
    # If --step argument provided, use that
    if hasattr(args, 'step') and args.step:
        step_name = args.step.lower()
        if step_name in WORKFLOW_STEPS:
            return WORKFLOW_STEPS[step_name]
        elif step_name.isdigit():
            step_num = int(step_name)
            if 1 <= step_num <= 6:
                return step_num
        print(f"[WARN] Invalid step '{args.step}', using default")

    # For existing sessions, find first incomplete step
    if session_meta:
        steps = session_meta.get('steps', {})
        for step_num, step_key in STEP_NAMES.items():
            if step_num == 1:  # Skip 'idea' step
                continue
            if not steps.get(step_key, False):
                return step_num
        return 6  # All complete, return last step

    # Default: start from step 2 (story)
    return 2


def get_step_mode(args):
    """
    Determine step progression mode (auto or manual).

    Args:
        args: Command line arguments

    Returns:
        bool: True for auto mode, False for manual
    """
    # Check command line override
    if hasattr(args, 'auto') and args.auto:
        return True
    if hasattr(args, 'manual') and args.manual:
        return False

    # Use config setting
    return config.AUTO_STEP_MODE


def get_image_generation_mode():
    """Get image generation mode from config (no longer prompts user)"""
    # Use config defaults - no interactive prompt
    mode = config.IMAGE_GENERATION_MODE
    negative_prompt = config.DEFAULT_NEGATIVE_PROMPT
    return mode, negative_prompt


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


def submit_and_verify_video(template, shot, shot_length, session_id, shot_idx, session_mgr,
                             image_path=None, variation_idx=1):
    """
    Submit a video to ComfyUI and wait for verification before marking as rendered.

    Args:
        template: ComfyUI workflow template
        shot: Shot data dictionary
        shot_length: Length of each shot in seconds
        session_id: Current session ID
        shot_idx: Shot index (1-based)
        session_mgr: SessionManager instance
        image_path: Specific image path to use (overrides shot['image_path'])
        variation_idx: Variation index for naming (1 = first, 2 = second, etc.)

    Returns:
        tuple: (success: bool, error_message: str or None, video_path: str or None)
    """
    import shutil
    from core.comfy_client import get_output_file_path

    # Create session videos directory
    videos_dir = session_mgr.get_videos_dir(session_id)
    os.makedirs(videos_dir, exist_ok=True)

    # Expected video filename
    # If variation_idx > 1, use shot_001_002.mp4 format
    if variation_idx > 1:
        video_filename = f"shot_{shot_idx:03d}_{variation_idx:03d}.mp4"
    else:
        video_filename = f"shot_{shot_idx:03d}.mp4"
    video_save_path = os.path.join(videos_dir, video_filename)

    try:
        # If a specific image path is provided, temporarily override shot's image_path
        original_image_path = None
        if image_path:
            original_image_path = shot.get('image_path')
            shot['image_path'] = image_path

        # Compile and submit workflow
        wf = compile_workflow(template, shot, video_length_seconds=shot_length)
        result = submit(wf)

        # Restore original image_path if we overrode it
        if original_image_path is not None:
            shot['image_path'] = original_image_path

        prompt_id = result.get('prompt_id')
        if not prompt_id:
            return False, "No prompt_id returned from ComfyUI", None

        variation_label = f" (variation {variation_idx})" if variation_idx > 1 else ""
        print(f"[QUEUE] Shot {shot_idx}{variation_label}: Prompt {prompt_id[:8]}... submitted")

        # Wait for completion and verify
        print(f"[WAIT] Shot {shot_idx}{variation_label}: Waiting for render...")
        wait_result = wait_for_prompt_completion(prompt_id, timeout=config.VIDEO_RENDER_TIMEOUT)

        if not wait_result['success']:
            error_msg = wait_result.get('error', 'Unknown error')
            print(f"[FAIL] Shot {shot_idx}{variation_label}: {error_msg}")
            return False, error_msg, None

        # Check if we got any outputs
        outputs = wait_result.get('outputs', [])
        if not outputs:
            print(f"[FAIL] Shot {shot_idx}{variation_label}: No output files generated")
            return False, "No output files generated", None

        # Find video outputs
        video_outputs = [o for o in outputs if o['type'] == 'video']
        image_outputs = [o for o in outputs if o['type'] == 'image']

        if video_outputs:
            print(f"[PASS] Shot {shot_idx}{variation_label}: Generated {len(video_outputs)} video(s)")

            # Copy first video to session folder
            video_info = video_outputs[0]
            source_path = get_output_file_path(video_info)

            if os.path.exists(source_path):
                shutil.copy2(source_path, video_save_path)
                print(f"[COPY] Shot {shot_idx}{variation_label}: {video_filename} -> session/videos/")
                print(f"       Source: {source_path}")
                print(f"       Target: {video_save_path}")

                # Verify copy
                if os.path.exists(video_save_path):
                    file_size = os.path.getsize(video_save_path)
                    print(f"[INFO] Video saved: {video_filename} ({file_size:,} bytes)")

                    # Mark as rendered with video path
                    # Only mark primary variation (1) in session metadata
                    if variation_idx == 1:
                        session_mgr.mark_video_rendered(session_id, shot_idx, video_save_path)
                    return True, None, video_save_path
                else:
                    print(f"[WARN] Copy verification failed")
                    return False, "Video copy failed", None
            else:
                print(f"[FAIL] Source video not found: {source_path}")
                # DON'T mark as rendered - the video file doesn't exist
                return False, "Source video not found", None

        elif image_outputs:
            print(f"[WARN] Shot {shot_idx}{variation_label}: Generated {len(image_outputs)} frame(s) instead of video")
            for i in image_outputs[:3]:
                print(f"       - {i['filename']}")
            if len(image_outputs) > 3:
                print(f"       ... and {len(image_outputs) - 3} more")

            # No video file, just frames - this is a failure for video generation
            # DON'T mark as rendered - we wanted a video, not frames
            return False, "Generated frames instead of video", None

        else:
            print(f"[FAIL] Shot {shot_idx}{variation_label}: Unknown output type")
            return False, "Unknown output type", None

    except Exception as e:
        error_msg = f"Exception during render: {str(e)}"
        print(f"[FAIL] Shot {shot_idx}{variation_label}: {error_msg}")
        import traceback
        traceback.print_exc()
        return False, error_msg, None


def continue_session(session_id, session_meta, session_mgr, args=None):
    """Continue from an existing session"""
    if args is None:
        args = argparse.Namespace()

    # Get step mode
    auto_mode = get_step_mode(args)
    mode_str = "AUTO" if auto_mode else "MANUAL"
    print(f"[INFO] Execution mode: {mode_str}")

    # Check if user specified a step to start from
    start_step = get_start_step(args, session_meta)
    if hasattr(args, 'step') and args.step:
        print(f"[INFO] Starting from step {start_step} (--step override)")

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

        # Prompt for next action in manual mode
        if not auto_mode:
            action = prompt_step_action(5, session_id, session_mgr)
            if action == 'quit':
                print("\n[INFO] Session saved. You can continue later with:")
                print(f"       python core/main.py --step videos")
                return None
            elif action.startswith('restart:'):
                print("[INFO] Restart requested. Please run with --step parameter.")
                return None
            # If 'continue' or 'retry', just proceed

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
    total_renders = 0
    errors = []

    for shot in valid_shots:
        shot_idx = shot.get('index', 0)
        shot_meta = session_meta['shots'][shot_idx - 1]

        # Skip if already rendered (only checks primary video)
        if shot_meta['video_rendered']:
            # Verify the video actually exists
            # For now, trust the metadata - user can regenerate if needed
            print(f"[SKIP] Shot {shot_idx}: Video already marked as rendered")
            successful_renders += 1
            continue

        # Get all image paths for this shot
        image_paths = shot.get('image_paths', [])
        if not image_paths:
            # Fall back to single image_path
            image_path = shot.get('image_path')
            if image_path:
                image_paths = [image_path]

        if not image_paths:
            print(f"\n[SKIP] Shot {shot_idx}: No images found")
            errors.append(f"Shot {shot_idx}: No images found")
            failed_renders += 1
            continue

        # Render video for each image variation
        print(f"\n[SUBMIT] Shot {shot_idx} ({shot_length}s each, {len(image_paths)} variation(s))")

        for variation_idx, img_path in enumerate(image_paths, 1):
            total_renders += 1
            variation_label = f" (variation {variation_idx}/{len(image_paths)})" if len(image_paths) > 1 else ""

            success, error, video_path = submit_and_verify_video(
                template, shot, shot_length, session_id, shot_idx, session_mgr,
                image_path=img_path, variation_idx=variation_idx
            )

            if success:
                successful_renders += 1
            else:
                failed_renders += 1
                errors.append(f"Shot {shot_idx}{variation_label}: {error}")

    # Summary
    print("\n" + "="*70)
    print("RENDER SUMMARY")
    print("="*70)
    print(f"Successful: {successful_renders}/{total_renders}")
    print(f"Failed: {failed_renders}/{total_renders}")

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

    # Get image generation mode and negative prompt from config or args
    if hasattr(args, 'image_mode') and args.image_mode:
        image_mode = args.image_mode
        print(f"[INFO] Image generation mode: {image_mode} (from command line)")
    else:
        image_mode = config.IMAGE_GENERATION_MODE
        print(f"[INFO] Image generation mode: {image_mode} (from config)")

    # Get negative prompt from args or config
    if hasattr(args, 'negative_prompt') and args.negative_prompt:
        negative_prompt = args.negative_prompt
    else:
        negative_prompt = config.DEFAULT_NEGATIVE_PROMPT
    if negative_prompt:
        print(f"[INFO] Negative prompt: {negative_prompt}")

    # Get video configuration
    print("\n" + "="*70)
    print("VIDEO CONFIGURATION")
    print("="*70)

    # Determine total video length
    if hasattr(args, 'total_length') and args.total_length:
        total_length = args.total_length
        print(f"[INFO] Total video length: {total_length}s (from command line)")
    else:
        total_length = config.TARGET_VIDEO_LENGTH
        if total_length:
            print(f"[INFO] Total video length: {total_length}s (from config)")

    # Determine shot length
    if hasattr(args, 'shot_length') and args.shot_length:
        shot_length = args.shot_length
        print(f"[INFO] Shot length: {shot_length}s (from command line)")
    else:
        shot_length = config.DEFAULT_SHOT_LENGTH
        print(f"[INFO] Shot length: {shot_length}s (from config)")

    # Calculate number of shots needed
    if total_length:
        max_shots = int(total_length / shot_length)
        print(f"\n[INFO] Target: {total_length}s video, {shot_length}s per shot = {max_shots} shots")
    elif hasattr(args, 'max_shots') and args.max_shots is not None:
        max_shots = args.max_shots
        if max_shots > 0:
            print(f"\n[INFO] Maximum shots limited to: {max_shots} (from command line)")
        else:
            max_shots = None
            print(f"\n[INFO] Shot length: {shot_length}s (no shot limit)")
    elif config.DEFAULT_MAX_SHOTS > 0:
        max_shots = config.DEFAULT_MAX_SHOTS
        print(f"\n[INFO] Maximum shots limited to: {max_shots} (set by DEFAULT_MAX_SHOTS)")
        print(f"[INFO] Shot length: {shot_length}s")
    else:
        max_shots = None
        print(f"\n[INFO] Shot length: {shot_length}s (number of shots based on story)")
        if config.DEFAULT_MAX_SHOTS == 0:
            print(f"[INFO] No shot limit - all story scenes will be generated")

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
    images_per_shot = getattr(args, 'images_per_shot', None) or config.IMAGES_PER_SHOT
    session_meta['image_config'] = {
        'mode': image_mode,
        'negative_prompt': negative_prompt,
        'images_per_shot': images_per_shot
    }

    # Get agent selection from args or config
    story_agent = getattr(args, 'story_agent', None) or config.STORY_AGENT
    image_agent = getattr(args, 'image_agent', None) or config.IMAGE_AGENT
    video_agent = getattr(args, 'video_agent', None) or config.VIDEO_AGENT
    narration_agent = getattr(args, 'narration_agent', None) or config.NARRATION_AGENT

    # Get narration settings
    generate_narration = not getattr(args, 'no_narration', False) and config.GENERATE_NARRATION
    tts_method = getattr(args, 'tts_method', None) or config.TTS_METHOD
    tts_workflow = getattr(args, 'tts_workflow', None) or config.TTS_WORKFLOW_PATH
    tts_voice = getattr(args, 'tts_voice', None) or config.TTS_VOICE

    # Store agent config in session
    session_meta['agent_config'] = {
        'story': story_agent,
        'image': image_agent,
        'video': video_agent,
        'narration': narration_agent
    }

    # Store narration config in session
    session_meta['narration_config'] = {
        'enabled': generate_narration,
        'tts_method': tts_method,
        'tts_workflow': tts_workflow,
        'tts_voice': tts_voice
    }

    session_mgr._save_meta(session_id, session_meta)

    print(f"[INFO] Created session: {session_id}")
    print(f"[INFO] Using agents - Story: {story_agent}, Image: {image_agent}, Video: {video_agent}, Narration: {narration_agent}")
    print(f"[INFO] Image generation: {images_per_shot} image(s) per shot")
    if generate_narration:
        print(f"[INFO] Narration enabled - TTS: {tts_method}, Voice: {tts_voice}")
    else:
        print(f"[INFO] Narration disabled")

    # Get execution mode
    auto_mode = get_step_mode(args)
    start_step = get_start_step(args)
    mode_str = "AUTO" if auto_mode else "MANUAL"
    print(f"[INFO] Execution mode: {mode_str} (starting from step {start_step})")

    # Execute workflow based on mode
    if auto_mode:
        # Original auto mode - execute all remaining steps
        _run_auto_mode(session_id, session_meta, session_mgr, idea, image_mode, negative_prompt, max_shots, shot_length,
                      story_agent=story_agent, image_agent=image_agent, video_agent=video_agent,
                      narration_agent=narration_agent, generate_narration=generate_narration,
                      tts_method=tts_method, tts_workflow=tts_workflow, tts_voice=tts_voice,
                      images_per_shot=images_per_shot)
    else:
        # New manual mode - step by step with prompts
        _run_manual_mode(session_id, session_meta, session_mgr, idea, image_mode, negative_prompt, max_shots, shot_length, start_step,
                        story_agent=story_agent, image_agent=image_agent, video_agent=video_agent,
                        narration_agent=narration_agent, generate_narration=generate_narration,
                        tts_method=tts_method, tts_workflow=tts_workflow, tts_voice=tts_voice,
                        images_per_shot=images_per_shot)


def _run_auto_mode(session_id, session_meta, session_mgr, idea, image_mode, negative_prompt, max_shots, shot_length,
                   story_agent=None, image_agent=None, video_agent=None,
                   narration_agent=None, generate_narration=False, tts_method=None, tts_workflow=None, tts_voice=None,
                   images_per_shot=1):
    """Execute all remaining steps automatically"""
    # Get current progress
    steps = session_meta.get('steps', {})

    # Get agent names from session metadata or args
    agent_config = session_meta.get('agent_config', {})
    story_agent = story_agent or agent_config.get('story', config.STORY_AGENT)
    image_agent = image_agent or agent_config.get('image', config.IMAGE_AGENT)
    video_agent = video_agent or agent_config.get('video', config.VIDEO_AGENT)
    narration_agent = narration_agent or agent_config.get('narration', config.NARRATION_AGENT)

    # Get narration config
    narration_config = session_meta.get('narration_config', {})
    generate_narration = generate_narration or narration_config.get('enabled', False)
    tts_method = tts_method or narration_config.get('tts_method', config.TTS_METHOD)
    tts_workflow = tts_workflow or narration_config.get('tts_workflow', config.TTS_WORKFLOW_PATH)
    tts_voice = tts_voice or narration_config.get('tts_voice', config.TTS_VOICE)

    # Get image config
    image_config = session_meta.get('image_config', {})
    images_per_shot = images_per_shot or image_config.get('images_per_shot', config.IMAGES_PER_SHOT)

    print(f"[INFO] Using agents - Story: {story_agent}, Image: {image_agent}, Video: {video_agent}, Narration: {narration_agent}")
    print(f"[INFO] Generating {images_per_shot} image(s) per shot")

    # STEP 2: Story
    if not steps.get('story', False):
        print("\nSTEP 2: Story Generation")
        story_json = build_story(idea, agent_name=story_agent)
        session_mgr.save_story(session_id, story_json)

    # STEP 3: Scene Graph
    if not steps.get('scene_graph', False):
        print("\nSTEP 3: Scene Graph")
        session_mgr.mark_step_complete(session_id, 'scene_graph')
        graph = build_scene_graph(story_json)

    # STEP 4: Shot Planning (with max_shots if specified)
    if not steps.get('shots', False):
        print("\nSTEP 4: Shot Planning")
        shots = plan_shots(graph, max_shots=max_shots, image_agent=image_agent, video_agent=video_agent)
        # Enhance motion prompts with trigger keywords for LoRA activation
        shots = enhance_motion_prompts_with_triggers(shots)
        session_mgr.save_shots(session_id, shots)
    else:
        # Reload shots if already done
        shots_dir = session_mgr.get_session_dir(session_id)
        shots_path = os.path.join(shots_dir, "shots.json")
        with open(shots_path, 'r', encoding='utf-8') as f:
            shots = json.load(f)

    # STEP 4.5: Image Generation
    if not steps.get('images', False):
        print("\nSTEP 4.5: Image Generation")
        _generate_images(session_id, session_mgr, shots, image_mode, negative_prompt, images_per_shot)
        # Reload shots with updated paths
        shots_dir = session_mgr.get_session_dir(session_id)
        shots_path = os.path.join(shots_dir, "shots.json")
        with open(shots_path, 'r', encoding='utf-8') as f:
            shots = json.load(f)

    # STEP 5: Rendering with verification
    if not steps.get('videos', False):
        # Filter to only shots with successfully generated images
        valid_shots = [s for s in shots if s.get('image_path')]

        if not valid_shots:
            print("[ERROR] No images were successfully generated. Cannot proceed.")
            return

        print(f"\nSTEP 5: Rendering {len(valid_shots)} shots")
        _render_videos(session_id, session_mgr, valid_shots, shot_length, shots)

    # STEP 6: Narration TTS
    if generate_narration and not steps.get('narration', False):
        print("\nSTEP 6: Narration TTS")

        # Load story for narration
        story_dir = session_mgr.get_session_dir(session_id)
        story_path = os.path.join(story_dir, "story.json")
        with open(story_path, 'r', encoding='utf-8') as f:
            story_json = f.read()

        # Calculate total duration
        video_config = session_meta.get('video_config', {})
        total_duration = video_config.get('total_length') or (len(shots) * shot_length)

        # Generate narration
        from core.narration_generator import generate_narration_for_session

        script_path, audio_path = generate_narration_for_session(
            session_id=session_id,
            story_json=story_json,
            shots=shots,
            total_duration=total_duration,
            agent_name=narration_agent,
            tts_method=tts_method,
            tts_workflow_path=tts_workflow,
            voice=tts_voice
        )

        if script_path and audio_path:
            print(f"[PASS] Narration complete")
            print(f"       Script: {script_path}")
            print(f"       Audio: {audio_path}")
        elif script_path:
            print(f"[WARN] Narration script generated but audio failed")
            print(f"       Script: {script_path}")
        else:
            print(f"[FAIL] Narration generation failed")

    if not generate_narration or steps.get('videos', False):
        print("\n[INFO] All steps completed!")
        session_mgr.print_session_summary(session_id)


def _run_manual_mode(session_id, session_meta, session_mgr, idea, image_mode, negative_prompt, max_shots, shot_length, start_step,
                     story_agent=None, image_agent=None, video_agent=None,
                     narration_agent=None, generate_narration=False, tts_method=None, tts_workflow=None, tts_voice=None,
                     images_per_shot=1):
    """Execute workflow step by step with user prompts"""
    shots = None
    story_json = None
    graph = None

    # Get agent names from session metadata or args
    agent_config = session_meta.get('agent_config', {})
    story_agent = story_agent or agent_config.get('story', config.STORY_AGENT)
    image_agent = image_agent or agent_config.get('image', config.IMAGE_AGENT)
    video_agent = video_agent or agent_config.get('video', config.VIDEO_AGENT)
    narration_agent = narration_agent or agent_config.get('narration', config.NARRATION_AGENT)

    # Get narration config
    narration_config = session_meta.get('narration_config', {})
    generate_narration = generate_narration or narration_config.get('enabled', False)
    tts_method = tts_method or narration_config.get('tts_method', config.TTS_METHOD)
    tts_workflow = tts_workflow or narration_config.get('tts_workflow', config.TTS_WORKFLOW_PATH)
    tts_voice = tts_voice or narration_config.get('tts_voice', config.TTS_VOICE)

    # Get image config
    image_config = session_meta.get('image_config', {})
    images_per_shot = images_per_shot or image_config.get('images_per_shot', config.IMAGES_PER_SHOT)

    print(f"[INFO] Using agents - Story: {story_agent}, Image: {image_agent}, Video: {video_agent}, Narration: {narration_agent}")
    print(f"[INFO] Generating {images_per_shot} image(s) per shot")

    current_step = start_step

    while current_step <= 7:
        step_key = STEP_NAMES[current_step]

        # Execute the current step
        if current_step == 2:  # Story
            if not session_meta.get('steps', {}).get('story', False):
                print("\nSTEP 2: Story Generation")
                story_json = build_story(idea, agent_name=story_agent)
                session_mgr.save_story(session_id, story_json)
            else:
                print("\n[SKIP] STEP 2: Story already generated")
                # Load existing story
                story_dir = session_mgr.get_session_dir(session_id)
                story_path = os.path.join(story_dir, "story.json")
                with open(story_path, 'r', encoding='utf-8') as f:
                    story_json = f.read()

        elif current_step == 3:  # Scene Graph
            if not session_meta.get('steps', {}).get('scene_graph', False):
                print("\nSTEP 3: Scene Graph")
                session_mgr.mark_step_complete(session_id, 'scene_graph')
                graph = build_scene_graph(story_json)
            else:
                print("\n[SKIP] STEP 3: Scene Graph already created")

        elif current_step == 4:  # Shot Planning
            if not session_meta.get('steps', {}).get('shots', False):
                print("\nSTEP 4: Shot Planning")
                shots = plan_shots(graph, max_shots=max_shots, image_agent=image_agent, video_agent=video_agent)
                # Enhance motion prompts with trigger keywords for LoRA activation
                shots = enhance_motion_prompts_with_triggers(shots)
                session_mgr.save_shots(session_id, shots)
            else:
                print("\n[SKIP] STEP 4: Shots already planned")
                # Load existing shots
                shots_dir = session_mgr.get_session_dir(session_id)
                shots_path = os.path.join(shots_dir, "shots.json")
                with open(shots_path, 'r', encoding='utf-8') as f:
                    shots = json.load(f)

        elif current_step == 5:  # Image Generation
            if not session_meta.get('steps', {}).get('images', False):
                print("\nSTEP 5: Image Generation")
                _generate_images(session_id, session_mgr, shots, image_mode, negative_prompt, images_per_shot)
                # Reload shots with updated paths
                shots_dir = session_mgr.get_session_dir(session_id)
                shots_path = os.path.join(shots_dir, "shots.json")
                with open(shots_path, 'r', encoding='utf-8') as f:
                    shots = json.load(f)
            else:
                print("\n[SKIP] STEP 5: Images already generated")

        elif current_step == 6:  # Video Rendering
            if not session_meta.get('steps', {}).get('videos', False):
                # Filter to only shots with successfully generated images
                valid_shots = [s for s in shots if s.get('image_path')]

                if not valid_shots:
                    print("[ERROR] No images were successfully generated. Cannot proceed.")
                    return

                print(f"\nSTEP 6: Rendering {len(valid_shots)} shots")
                _render_videos(session_id, session_mgr, valid_shots, shot_length, shots)
            else:
                print("\n[SKIP] STEP 6: Videos already rendered")

        elif current_step == 7:  # Narration TTS
            if generate_narration and not session_meta.get('steps', {}).get('narration', False):
                print("\nSTEP 7: Narration TTS")

                # Calculate total duration
                video_config = session_meta.get('video_config', {})
                total_duration = video_config.get('total_length') or (len(shots) * shot_length)

                # Generate narration
                from core.narration_generator import generate_narration_for_session

                script_path, audio_path = generate_narration_for_session(
                    session_id=session_id,
                    story_json=story_json,
                    shots=shots,
                    total_duration=total_duration,
                    agent_name=narration_agent,
                    use_comfyui=(tts_method == 'comfyui'),
                    tts_workflow_path=tts_workflow,
                    voice=tts_voice
                )

                if script_path and audio_path:
                    print(f"[PASS] Narration complete")
                    print(f"       Script: {script_path}")
                    print(f"       Audio: {audio_path}")
                elif script_path:
                    print(f"[WARN] Narration script generated but audio failed")
                else:
                    print(f"[FAIL] Narration generation failed")
            else:
                if generate_narration:
                    print("\n[SKIP] STEP 7: Narration already generated")
                else:
                    print("\n[SKIP] STEP 7: Narration disabled")
                # All steps complete
                print("\n[INFO] All steps completed!")
                session_mgr.print_session_summary(session_id)
                return

        # Reload session metadata after step
        session_meta = session_mgr.get_session(session_id)

        # Prompt for next action
        if current_step < 7:  # Don't prompt after final step
            action = prompt_step_action(current_step, session_id, session_mgr)

            if action == 'continue':
                current_step += 1
            elif action == 'retry':
                # Re-execute current step
                continue
            elif action.startswith('restart:'):
                # Restart from specific step
                _, step_num = action.split(':')
                current_step = int(step_num)
                print(f"\n[INFO] Restarting from step {current_step}")
            elif action == 'quit':
                print("\n[INFO] Session saved. You can continue later with:")
                print(f"       python core/main.py --step {current_step + 1}")
                return


def _generate_images(session_id, session_mgr, shots, image_mode, negative_prompt, images_per_shot=1):
    """Generate images for all shots with optional multiple variations"""
    from core.image_generator import generate_images_for_shots

    images_dir = session_mgr.get_images_dir(session_id)
    os.makedirs(images_dir, exist_ok=True)

    # Check if images are already generated (resume case)
    # For simplicity, check if first variation of first shot exists
    if shots and images_per_shot > 0:
        first_shot_idx = shots[0].get('index', 1)
        first_image_path = os.path.join(images_dir, f"shot_{first_shot_idx:03d}_001.png")

        if os.path.exists(first_image_path):
            print(f"[SKIP] Images already generated, loading from disk")
            # Load existing images
            for shot in shots:
                shot_idx = shot.get('index', shots.index(shot) + 1)
                image_paths = []
                for var_idx in range(images_per_shot):
                    img_path = os.path.join(images_dir, f"shot_{shot_idx:03d}_{var_idx + 1:03d}.png")
                    if os.path.exists(img_path):
                        normalized_path = img_path.replace('\\', '/')
                        image_paths.append(normalized_path)
                        session_mgr.mark_image_generated(session_id, shot_idx, normalized_path)

                shot['image_paths'] = image_paths
                shot['image_path'] = image_paths[0] if image_paths else None

            session_mgr.mark_step_complete(session_id, 'images')
            return

    # Generate images using the updated function
    shots = generate_images_for_shots(
        shots=shots,
        output_dir=images_dir,
        mode=image_mode,
        negative_prompt=negative_prompt,
        images_per_shot=images_per_shot
    )

    # Mark all generated images in session
    for shot in shots:
        shot_idx = shot.get('index', shots.index(shot) + 1)
        image_paths = shot.get('image_paths', [])
        for img_path in image_paths:
            normalized_path = img_path.replace('\\', '/')
            session_mgr.mark_image_generated(session_id, shot_idx, normalized_path)

    session_mgr.mark_step_complete(session_id, 'images')


def _render_videos(session_id, session_mgr, valid_shots, shot_length, shots):
    """Render videos for all shots and all image variations"""
    template = load_workflow(config.WORKFLOW_PATH, video_length_seconds=shot_length)

    # Track results
    successful_renders = 0
    failed_renders = 0
    total_renders = 0
    errors = []

    for shot in valid_shots:
        shot_idx = shot.get('index', shots.index(shot) + 1)

        # Get all image paths for this shot
        image_paths = shot.get('image_paths', [])
        if not image_paths:
            # Fall back to single image_path
            image_path = shot.get('image_path')
            if image_path:
                image_paths = [image_path]

        if not image_paths:
            print(f"\n[SKIP] Shot {shot_idx}: No images found")
            errors.append(f"Shot {shot_idx}: No images found")
            failed_renders += 1
            continue

        # Render video for each image variation
        print(f"\n[SUBMIT] Shot {shot_idx} ({shot_length}s each, {len(image_paths)} variation(s))")

        for variation_idx, img_path in enumerate(image_paths, 1):
            total_renders += 1
            variation_label = f" (variation {variation_idx}/{len(image_paths)})" if len(image_paths) > 1 else ""

            success, error, video_path = submit_and_verify_video(
                template, shot, shot_length, session_id, shot_idx, session_mgr,
                image_path=img_path, variation_idx=variation_idx
            )

            if success:
                successful_renders += 1
            else:
                failed_renders += 1
                errors.append(f"Shot {shot_idx}{variation_label}: {error}")

    # Summary
    print("\n" + "="*70)
    print("RENDER SUMMARY")
    print("="*70)
    print(f"Successful: {successful_renders}/{total_renders}")
    print(f"Failed: {failed_renders}/{total_renders}")

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

  # Quick test with limited shots (for testing workflow)
  python core/main.py --idea "Test video" --max-shots 3

  # Generate short video for testing
  python core/main.py --idea "Quick test" --max-shots 2 --no-narration

  # Generate multiple image variations per shot
  python core/main.py --idea "Artistic video" --images-per-shot 4

  # Generate 4 variations for quick testing
  python core/main.py --idea "Test" --max-shots 2 --images-per-shot 4 --no-narration

  # Use specific agents for different steps
  python core/main.py --idea "Dramatic space epic" --story-agent dramatic --image-agent artistic --video-agent cinematic

  # Generate video with narration using ElevenLabs
  python core/main.py --idea "Nature documentary" --story-agent documentary --narration-agent professional --tts-method elevenlabs --tts-voice "Rachel"

  # List available ElevenLabs voices
  python core/main.py --list-voices

  # Generate narration with edge-tts (free)
  python core/main.py --idea "Tutorial video" --narration-agent default --tts-method local --tts-voice "en-US-AriaNeural"

  # Use ComfyUI TTS workflow for narration
  python core/main.py --idea "Explainer video" --narration-agent professional --tts-method comfyui --tts-workflow workflow/tts_workflow.json

  # List all available agents
  python core/main.py --list-agents

  # Use idea from file (default)
  python core/main.py

  # Specify image generation mode
  python core/main.py --idea "Sunset beach" --image-mode comfyui

  # Set video length and shot duration
  python core/main.py --idea "City timelapse" --total-length 30 --shot-length 3

  # Set image dimensions
  python core/main.py --idea "Portrait video" --aspect-ratio 9:16 --resolution 1024

  # Run in manual step-by-step mode
  python core/main.py --idea "Space epic" --manual

  # Start from a specific step (2=story, 3=scene_graph, 4=shots, 5=images, 6=videos, 7=narration)
  python core/main.py --step narration --manual

  # Skip narration generation
  python core/main.py --idea "Music video" --no-narration

  # Skip resume prompt (always start new session)
  python core/main.py --idea "Quick test" --no-resume

  # For camera-specific LoRA strengths, edit config.py CAMERA_LORA_MAPPING

Workflow Steps:
  1. Idea Input
  2. Story Generation (story)
  3. Scene Graph (scene_graph)
  4. Shot Planning (shots)
  5. Image Generation (images)
  6. Video Rendering (videos)
  7. Narration TTS (narration)

Available Agents:
  Story: default, dramatic, documentary
  Image: default, artistic
  Video: default, cinematic
  Narration: default, documentary, professional, storytelling

TTS Methods:
  - local: edge-tts (free, requires: pip install edge-tts)
  - elevenlabs: ElevenLabs API (requires API key)
  - comfyui: ComfyUI TTS workflow

LoRA System:
  - Wan 2.2 workflow uses TWO LoRA nodes simultaneously
  - LORA_NODE_ID: Low noise model (subtle motion)
  - LORA_NODE_ID_2: High noise model (dynamic motion)
  - Configure camera-specific LoRAs in CAMERA_LORA_MAPPING (config.py)
  - Each camera type has its own strength_low and strength_high (0.0 to 1.0)
  - Edit config.py to adjust LoRA strengths for each camera type

Testing Options:
  --max-shots N         : Limit to N shots (for quick testing)
  --images-per-shot N   : Generate N image variations per shot (default: 1)
  --no-narration        : Skip narration generation
  --no-resume          : Skip resume prompt, start new session

  Use --list-voices to see ElevenLabs voices
  Use --list-agents to see all available agents
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
        '--images-per-shot',
        type=int,
        default=None,
        help='Number of images to generate per shot (default: from config.py)'
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
        '--max-shots',
        type=int,
        help='Maximum number of shots to generate (0=no limit, useful for testing workflow)'
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

    parser.add_argument(
        '--step', '-s',
        type=str,
        help='Start from specific step (2-7, or: story, scene_graph, shots, images, videos, narration)'
    )

    parser.add_argument(
        '--auto',
        action='store_true',
        help='Auto-proceed through steps without pausing'
    )

    parser.add_argument(
        '--manual',
        action='store_true',
        help='Manual step progression - pause after each step'
    )

    parser.add_argument(
        '--story-agent',
        type=str,
        default=None,
        help='Story agent to use (default: dramatic, documentary, etc.)'
    )

    parser.add_argument(
        '--image-agent',
        type=str,
        default=None,
        help='Image prompt agent to use (default: artistic, etc.)'
    )

    parser.add_argument(
        '--video-agent',
        type=str,
        default=None,
        help='Video motion agent to use (default: cinematic, etc.)'
    )

    parser.add_argument(
        '--narration-agent',
        type=str,
        default=None,
        help='Narration agent to use (default: professional, storytelling, documentary, etc.)'
    )

    parser.add_argument(
        '--no-narration',
        action='store_true',
        help='Skip narration generation step'
    )

    parser.add_argument(
        '--tts-method',
        type=str,
        choices=['comfyui', 'local', 'elevenlabs'],
        help='TTS method: comfyui workflow, local (edge-tts), or elevenlabs'
    )

    parser.add_argument(
        '--tts-workflow',
        type=str,
        help='Path to ComfyUI TTS workflow JSON'
    )

    parser.add_argument(
        '--tts-voice',
        type=str,
        help='Voice name for TTS (e.g., "Rachel" for ElevenLabs, "en-US-AriaNeural" for edge-tts)'
    )

    parser.add_argument(
        '--list-voices',
        action='store_true',
        help='List available ElevenLabs voices and exit'
    )

    parser.add_argument(
        '--list-agents',
        action='store_true',
        help='List all available agents and exit'
    )

    args = parser.parse_args()

    # Handle --list-agents
    if args.list_agents:
        from core.agent_loader import AgentLoader
        loader = AgentLoader()
        loader.print_all_agents()
        return

    # Handle --list-voices
    if args.list_voices:
        from core.narration_generator import list_elevenlabs_voices
        print("\n" + "="*70)
        print("ELEVENLABS VOICES")
        print("="*70)

        voices = list_elevenlabs_voices()
        if voices:
            print(f"\nFound {len(voices)} voices:\n")
            for voice in voices:
                name = voice.get('name', 'Unknown')
                voice_id = voice.get('voice_id', 'Unknown')
                labels = voice.get('labels', {})
                accent = labels.get('accent', 'N/A')
                gender = labels.get('gender', 'N/A')
                age = labels.get('age', 'N/A')
                print(f"  {name}")
                print(f"    ID: {voice_id}")
                print(f"    Accent: {accent}, Gender: {gender}, Age: {age}")
                print()
        else:
            print("\n[ERROR] Could not fetch voices.")
            print("[HINT] Make sure ELEVENLABS_API_KEY is set in config.py or environment")
        print("="*70)
        return

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
            continue_session(session_id, session_meta, session_mgr, args=args)
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