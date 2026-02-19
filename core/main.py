"""
AI Film Studio - Main Pipeline with Session Management and Crash Recovery
"""
import json
import os
import sys
import argparse
import time
from datetime import datetime

# Add parent directory to path so we can import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from core.logger_config import get_logger


# Get logger for pipeline orchestration
logger = get_logger(__name__)

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


def print_configuration_summary():
    """Print all configuration settings at startup"""
    print("\n" + "="*70)
    print("CONFIGURATION SUMMARY")
    print("="*70)

    # LLM Provider Configuration
    print("\n[LLM Provider]")
    print(f"  Provider: {config.LLM_PROVIDER}")
    print(f"  Gemini Model: {config.GEMINI_TEXT_MODEL}")
    print(f"  OpenAI Model: {config.OPENAI_MODEL}")

    # API Key Status (masked)
    def mask_key(key):
        return f"{key[:8]}...{key[-4:]}" if len(key) > 12 else "***" if key else "NOT SET"

    print("\n[API Keys Status]")
    print(f"  Gemini: {mask_key(config.GEMINI_API_KEY)}")
    print(f"  OpenAI: {mask_key(config.OPENAI_API_KEY)}")
    print(f"  Zhipu: {mask_key(config.ZHIPU_API_KEY)}")
    print(f"  Qwen: {mask_key(config.QWEN_API_KEY)}")
    print(f"  Kimi: {mask_key(config.KIMI_API_KEY)}")
    print(f"  ElevenLabs: {mask_key(config.ELEVENLABS_API_KEY)}")

    # Image Generation Configuration
    print("\n[Image Generation]")
    print(f"  Mode: {config.IMAGE_GENERATION_MODE}")
    print(f"  Workflow: {config.IMAGE_WORKFLOW}")
    print(f"  Images per Shot: {config.IMAGES_PER_SHOT}")
    print(f"  Aspect Ratio: {config.IMAGE_ASPECT_RATIO}")
    print(f"  Resolution: {config.IMAGE_RESOLUTION}")
    print(f"  Dimensions: {config.IMAGE_WIDTH}x{config.IMAGE_HEIGHT}")

    # Video Generation Configuration
    print("\n[Video Generation]")
    print(f"  Shot Length: {config.DEFAULT_SHOT_LENGTH}s")
    print(f"  Max Shots: {config.DEFAULT_MAX_SHOTS} (0 = no limit)")
    print(f"  FPS: {config.VIDEO_FPS}")
    if config.TARGET_VIDEO_LENGTH:
        print(f"  Target Length: {config.TARGET_VIDEO_LENGTH}s")

    # Workflow Mode
    print("\n[Workflow]")
    print(f"  Auto Step Mode: {config.AUTO_STEP_MODE}")
    print(f"  Generate Narration: {config.GENERATE_NARRATION}")
    print(f"  TTS Method: {config.TTS_METHOD}")
    print(f"  TTS Voice: {config.TTS_VOICE}")

    # Agents
    print("\n[Agents]")
    print(f"  Story Agent: {config.STORY_AGENT}")
    print(f"  Image Agent: {config.IMAGE_AGENT}")
    print(f"  Video Agent: {config.VIDEO_AGENT}")
    print(f"  Narration Agent: {config.NARRATION_AGENT}")

    print("\n" + "="*70)


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
    2. Custom input file (--idea-file)
    3. Default input file (input/video_idea.txt)

    Returns:
        Video idea as string, or None if not found
    """
    # First priority: command line argument
    if hasattr(args, 'idea') and args.idea:
        logger.debug(f"Using idea from command line argument")
        return args.idea

    # Second priority: custom input file from --idea-file
    if hasattr(args, 'idea_file') and args.idea_file:
        idea_file = args.idea_file
        logger.info(f"Reading idea from custom file: {idea_file}")
        if os.path.exists(idea_file):
            try:
                with open(idea_file, "r", encoding="utf-8") as f:
                    idea = f.read()
                    logger.debug(f"  Loaded {len(idea)} characters from {idea_file}")
                    return idea
            except Exception as e:
                logger.error(f"Failed to read idea file {idea_file}: {e}")
                print(f"[ERROR] Failed to read {idea_file}: {e}")
                return None
        else:
            logger.error(f"Idea file not found: {idea_file}")
            print(f"[ERROR] Idea file not found: {idea_file}")
            print(f"[HINT] Create the file or use --idea 'your idea here'")
            return None

    # Third priority: default input file
    idea_file = "input/video_idea.txt"
    if os.path.exists(idea_file):
        logger.info(f"Reading idea from default file: {idea_file}")
        try:
            with open(idea_file, "r", encoding="utf-8") as f:
                idea = f.read()
                logger.debug(f"  Loaded {len(idea)} characters from {idea_file}")
                return idea
        except Exception as e:
            logger.error(f"Failed to read idea file {idea_file}: {e}")
            print(f"[ERROR] Failed to read {idea_file}: {e}")
            return None

    # No idea found
    logger.warning("No video idea provided")
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

    # Initialize variation_label before try block for exception handler
    variation_label = f" (variation {variation_idx})" if variation_idx > 1 else ""

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

            # Wait for file to be written to disk with retry mechanism
            # Video files can be large and take several seconds to finalize
            max_retries = 10
            retry_delay = 2  # seconds
            file_found = False

            for attempt in range(max_retries):
                if os.path.exists(source_path):
                    # File exists, but check if it's still being written
                    # by checking if the file size is stable
                    try:
                        initial_size = os.path.getsize(source_path)
                        time.sleep(1)  # Wait 1 second
                        final_size = os.path.getsize(source_path)

                        if initial_size == final_size and final_size > 0:
                            # File size is stable and non-zero, file is complete
                            file_found = True
                            break
                        else:
                            if attempt < max_retries - 1:
                                print(f"[WAIT] Shot {shot_idx}{variation_label}: File still writing... (retry {attempt + 1}/{max_retries})")
                                time.sleep(retry_delay)
                            else:
                                print(f"[WARN] Shot {shot_idx}{variation_label}: File size unstable after {max_retries} retries")
                    except OSError as e:
                        if attempt < max_retries - 1:
                            print(f"[WAIT] Shot {shot_idx}{variation_label}: Cannot access file yet... (retry {attempt + 1}/{max_retries})")
                            time.sleep(retry_delay)
                        else:
                            print(f"[ERROR] Shot {shot_idx}{variation_label}: Cannot access file: {e}")
                else:
                    if attempt < max_retries - 1:
                        print(f"[WAIT] Shot {shot_idx}{variation_label}: File not on disk yet... (retry {attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
                    else:
                        print(f"[FAIL] Shot {shot_idx}{variation_label}: File not found after {max_retries} retries")

            if file_found:
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
                print(f"[FAIL] Source video not found after retries: {source_path}")
                print(f"[HINT] ComfyUI may have saved it to a different location")
                print(f"[HINT] Check ComfyUI's output directory")
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


def _continue_existing_session(session_id, session_meta, session_mgr, args=None):
    """
    Continue an existing session from where it left off.

    Args:
        session_id: Existing session ID
        session_meta: Session metadata
        session_mgr: SessionManager instance
        args: Optional argparse namespace with command line arguments
    """
    logger.info(f"Resuming session: {session_id}")
    if args is None:
        args = argparse.Namespace()

    # Get idea from session metadata
    idea = session_meta.get('idea', '')
    logger.debug(f"  Resuming with idea: {idea[:200]}...")

    # Get execution mode
    auto_mode = get_step_mode(args)
    start_step = get_start_step(args, session_meta)
    mode_str = "AUTO" if auto_mode else "MANUAL"

    print(f"\n[RESUME] Session: {session_id}")
    print(f"[RESUME] Execution mode: {mode_str}")
    print(f"[RESUME] Starting from step {start_step}")

    # Get config from session metadata
    image_config = session_meta.get('image_config', {})
    image_mode = image_config.get('mode', config.IMAGE_GENERATION_MODE)
    negative_prompt = image_config.get('negative_prompt', config.DEFAULT_NEGATIVE_PROMPT)
    images_per_shot = image_config.get('images_per_shot', config.IMAGES_PER_SHOT)

    video_config = session_meta.get('video_config', {})
    shot_length = video_config.get('shot_length', config.DEFAULT_SHOT_LENGTH)
    total_length = video_config.get('total_length')
    shots_per_scene = video_config.get('shots_per_scene', config.DEFAULT_SHOTS_PER_SCENE)

    # Calculate max_shots from total_length if specified
    if total_length and shot_length:
        max_shots = int(total_length / shot_length)
    else:
        max_shots = None

    # Get agent config from session
    agent_config = session_meta.get('agent_config', {})
    story_agent = agent_config.get('story', config.STORY_AGENT)
    image_agent = agent_config.get('image', config.IMAGE_AGENT)
    video_agent = agent_config.get('video', config.VIDEO_AGENT)
    narration_agent = agent_config.get('narration', config.NARRATION_AGENT)

    # Get narration config
    narration_config = session_meta.get('narration_config', {})
    generate_narration = narration_config.get('enabled', False)
    tts_method = narration_config.get('tts_method', config.TTS_METHOD)
    tts_workflow = narration_config.get('tts_workflow', config.TTS_WORKFLOW_PATH)
    tts_voice = narration_config.get('tts_voice', config.TTS_VOICE)

    # Update config with session values for display
    config.IMAGE_GENERATION_MODE = image_mode
    config.IMAGES_PER_SHOT = images_per_shot
    config.STORY_AGENT = story_agent
    config.IMAGE_AGENT = image_agent
    config.VIDEO_AGENT = video_agent
    config.NARRATION_AGENT = narration_agent
    config.GENERATE_NARRATION = generate_narration
    config.TTS_METHOD = tts_method
    config.TTS_VOICE = tts_voice

    # Print configuration summary for resumed session
    print_configuration_summary()

    print(f"[INFO] Image generation: {image_mode}")
    print(f"[INFO] Using agents - Story: {story_agent}, Image: {image_agent}, Video: {video_agent}, Narration: {narration_agent}")

    # Execute workflow based on mode
    if auto_mode:
        _run_auto_mode(session_id, session_meta, session_mgr, idea, image_mode, negative_prompt, max_shots, shot_length,
                      story_agent=story_agent, image_agent=image_agent, video_agent=video_agent,
                      narration_agent=narration_agent, generate_narration=generate_narration,
                      tts_method=tts_method, tts_workflow=tts_workflow, tts_voice=tts_voice,
                      images_per_shot=images_per_shot, shots_per_scene=shots_per_scene)
    else:
        _run_manual_mode(session_id, session_meta, session_mgr, idea, image_mode, negative_prompt, max_shots, shot_length, start_step,
                        story_agent=story_agent, image_agent=image_agent, video_agent=video_agent,
                        narration_agent=narration_agent, generate_narration=generate_narration,
                        tts_method=tts_method, tts_workflow=tts_workflow, tts_voice=tts_voice,
                        images_per_shot=images_per_shot, shots_per_scene=shots_per_scene)


def run_new_session(session_mgr, args=None):
    """
    Run a complete new session

    Args:
        session_mgr: SessionManager instance
        args: Optional argparse namespace with command line arguments
    """
    logger.info("Starting new session workflow")
    if args is None:
        args = argparse.Namespace()

    # Check if using prompts file workflow
    if hasattr(args, 'prompts_file') and args.prompts_file:
        return _run_with_prompts_file(session_mgr, args)

    logger.debug("Starting STEP 1: Idea Input")
    print("\nSTEP 1: Idea")
    idea = get_idea(args)
    logger.debug(f"  Idea: {idea[:200]}...")
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

    # Check for shots-per-scene parameter
    shots_per_scene = getattr(args, 'shots_per_scene', None) or config.DEFAULT_SHOTS_PER_SCENE
    if shots_per_scene and not max_shots:
        # Will be calculated after story generation when we know scene count
        print(f"[INFO] Shots per scene target: {shots_per_scene}")
        print(f"[INFO] Total shots will be calculated after story generation")

    print("="*70)

    # Create new session
    session_id, session_meta = session_mgr.create_session(idea)

    logger.info(f"Session created: {session_id}")
    # Store video config in session
    session_meta['video_config'] = {
        'total_length': total_length,
        'shot_length': shot_length,
        'fps': config.VIDEO_FPS,
        'shots_per_scene': shots_per_scene
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
                      images_per_shot=images_per_shot, shots_per_scene=shots_per_scene)
    else:
        # New manual mode - step by step with prompts
        _run_manual_mode(session_id, session_meta, session_mgr, idea, image_mode, negative_prompt, max_shots, shot_length, start_step,
                        story_agent=story_agent, image_agent=image_agent, video_agent=video_agent,
                        narration_agent=narration_agent, generate_narration=generate_narration,
                        tts_method=tts_method, tts_workflow=tts_workflow, tts_voice=tts_voice,
                        images_per_shot=images_per_shot, shots_per_scene=shots_per_scene)


def _run_auto_mode(session_id, session_meta, session_mgr, idea, image_mode, negative_prompt, max_shots, shot_length,
                   story_agent=None, image_agent=None, video_agent=None,
                   narration_agent=None, generate_narration=False, tts_method=None, tts_workflow=None, tts_voice=None,
                   images_per_shot=1, shots_per_scene=None):
    """Execute all remaining steps automatically"""
    logger.info(f"Running auto mode for session: {session_id}")
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

    story_json = None
    shots = None
    graph = None

    # STEP 2: Story
    if not steps.get('story', False):
        logger.info("STEP 2: Story Generation")
        print("\nSTEP 2: Story Generation")
        story_json = build_story(idea, agent_name=story_agent)
        session_mgr.save_story(session_id, story_json)
    else:
        # Check if this is a prompts file session (no story.json)
        if session_meta.get('prompts_file'):
            print("\n[SKIP] STEP 2: Story skipped (prompts file mode)")
            story_json = None
        else:
            # Load existing story
            print("\n[SKIP] STEP 2: Story already generated")
            story_dir = session_mgr.get_session_dir(session_id)
            story_path = os.path.join(story_dir, "story.json")
            with open(story_path, 'r', encoding='utf-8') as f:
                story_json = f.read()

    # STEP 3: Scene Graph
    if not steps.get('scene_graph', False):
        logger.info("STEP 3: Scene Graph")
        print("\nSTEP 3: Scene Graph")
        session_mgr.mark_step_complete(session_id, 'scene_graph')
        graph = build_scene_graph(story_json)
    else:
        print("\n[SKIP] STEP 3: Scene Graph already created")

    # STEP 4: Shot Planning (with max_shots if specified)
    if not steps.get('shots', False):
        logger.info("STEP 4: Shot Planning")
        print("\nSTEP 4: Shot Planning")
        shots = plan_shots(graph, max_shots=max_shots, image_agent=image_agent, video_agent=video_agent, shots_per_scene=shots_per_scene)
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
        logger.info("STEP 4.5: Image Generation")
        print("\nSTEP 4.5: Image Generation")
        _generate_images(session_id, session_mgr, shots, image_mode, negative_prompt, images_per_shot)
        # Reload shots with updated paths
        shots_dir = session_mgr.get_session_dir(session_id)
        shots_path = os.path.join(shots_dir, "shots.json")
        with open(shots_path, 'r', encoding='utf-8') as f:
            shots = json.load(f)
    else:
        # Images step marked complete, but verify images actually exist
        print("\n[VERIFY] Checking if images exist...")
        images_dir = session_mgr.get_images_dir(session_id)

        # Check if shots have image_path and files exist
        missing_images = False
        for shot in shots:
            img_path = shot.get('image_path')
            if not img_path or not os.path.exists(os.path.join(images_dir, os.path.basename(img_path))):
                missing_images = True
                break

        if missing_images:
            print("[WARN] Some images are missing. Regenerating...")
            _generate_images(session_id, session_mgr, shots, image_mode, negative_prompt, images_per_shot)
            # Reload shots with updated paths
            shots_dir = session_mgr.get_session_dir(session_id)
            shots_path = os.path.join(shots_dir, "shots.json")
            with open(shots_path, 'r', encoding='utf-8') as f:
                shots = json.load(f)
        else:
            print("[SKIP] Images verified and already exist")
            # Update shots with image paths from disk
            for shot_idx, shot in enumerate(shots, start=1):
                image_paths = []
                for var_idx in range(images_per_shot):
                    img_path = os.path.join(images_dir, f"shot_{shot_idx:03d}_{var_idx + 1:03d}.png")
                    if os.path.exists(img_path):
                        normalized_path = img_path.replace('\\', '/')
                        image_paths.append(normalized_path)
                shot['image_paths'] = image_paths
                shot['image_path'] = image_paths[0] if image_paths else None
            print(f"[INFO] Loaded {len([s for s in shots if s.get('image_path')])} shots with images")

    # STEP 5: Rendering with verification
    print(f"\n[DEBUG] Checking video step: steps.get('videos') = {steps.get('videos', False)}")
    print(f"[DEBUG] Shots with images: {len([s for s in shots if s.get('image_path')])}/{len(shots)}")

    if not steps.get('videos', False):
        # Filter to only shots with successfully generated images
        valid_shots = [s for s in shots if s.get('image_path')]

        if not valid_shots:
            logger.error("No images were successfully generated. Cannot proceed.")
            print("[ERROR] No images were successfully generated. Cannot proceed.")
            return

        logger.info(f"STEP 5: Rendering {len(valid_shots)} shots")
        print(f"\nSTEP 5: Rendering {len(valid_shots)} shots")
        _render_videos(session_id, session_mgr, valid_shots, shot_length, shots)
    else:
        # Videos step is marked complete, but verify videos actually exist
        print(f"[VERIFY] Checking if videos actually exist...")
        videos_dir = session_mgr.get_videos_dir(session_id)

        # Check if video files actually exist on disk
        missing_videos = False
        for shot in shots:
            shot_idx = shot.get('index', shots.index(shot) + 1)
            video_path = os.path.join(videos_dir, f"shot_{shot_idx:03d}.mp4")
            if not os.path.exists(video_path):
                missing_videos = True
                break

        if missing_videos:
            print(f"[WARN] Videos step marked complete but video files are missing!")
            print(f"[INFO] Unmarking videos step and proceeding with video generation...")
            # Unmark the videos step so we can regenerate
            session_meta['steps']['videos'] = False
            session_mgr._save_meta(session_id, session_meta)

            # Now render videos
            valid_shots = [s for s in shots if s.get('image_path')]
            logger.info(f"STEP 5: Rendering {len(valid_shots)} shots")
            print(f"\nSTEP 5: Rendering {len(valid_shots)} shots")
            _render_videos(session_id, session_mgr, valid_shots, shot_length, shots)
        else:
            print(f"[SKIP] Videos verified and already exist")

    # STEP 6: Narration TTS
    if generate_narration and not steps.get('narration', False):
        # Skip narration for prompts file sessions (no story.json)
        if session_meta.get('prompts_file'):
            print("\n[SKIP] STEP 6: Narration skipped (prompts file mode)")
            print("[INFO] Shots already have narration text from prompts file")
            # Mark narration as complete so session can finish
            session_mgr.mark_step_complete(session_id, 'narration')
        else:
            logger.info("STEP 6: Narration TTS")
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
        logger.info("All steps completed successfully")
        print("\n[INFO] All steps completed!")
        session_mgr.print_session_summary(session_id)


def _run_manual_mode(session_id, session_meta, session_mgr, idea, image_mode, negative_prompt, max_shots, shot_length, start_step,
                     story_agent=None, image_agent=None, video_agent=None,
                     narration_agent=None, generate_narration=False, tts_method=None, tts_workflow=None, tts_voice=None,
                     images_per_shot=1, shots_per_scene=None):
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
                # Check if this is a prompts file session (no story.json)
                if session_meta.get('prompts_file'):
                    print("\n[SKIP] STEP 2: Story skipped (prompts file mode)")
                    story_json = None
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
                shots = plan_shots(graph, max_shots=max_shots, image_agent=image_agent, video_agent=video_agent, shots_per_scene=shots_per_scene)
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
                # Skip narration for prompts file sessions (no story.json)
                if session_meta.get('prompts_file'):
                    print("\n[SKIP] STEP 7: Narration skipped (prompts file mode)")
                    print("[INFO] Shots already have narration text from prompts file")
                    # Mark narration as complete so session can finish
                    session_mgr.mark_step_complete(session_id, 'narration')
                else:
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
        first_image_path = os.path.join(images_dir, f"shot_001_001.png")

        if os.path.exists(first_image_path):
            print(f"[SKIP] Images already generated, loading from disk")
            # Load existing images
            for shot_idx, shot in enumerate(shots, start=1):
                # Use sequential index to match filenames
                image_paths = []
                for var_idx in range(images_per_shot):
                    img_path = os.path.join(images_dir, f"shot_{shot_idx:03d}_{var_idx + 1:03d}.png")
                    if os.path.exists(img_path):
                        normalized_path = img_path.replace('\\', '/')
                        image_paths.append(normalized_path)
                        stored_index = shot.get('index', shot_idx)
                        session_mgr.mark_image_generated(session_id, stored_index, normalized_path)

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

    # Only mark step complete if at least one video was successfully rendered
    if successful_renders > 0:
        session_mgr.mark_step_complete(session_id, 'videos')

    # Only mark session complete if all renders succeeded
    if failed_renders == 0:
        session_mgr.mark_session_complete(session_id)
        print("\n[SUCCESS] ALL RENDERS COMPLETE!")
    else:
        print("\n[WARNING] Session completed with errors. Some videos failed to render.")

    session_mgr.print_session_summary(session_id)


def _run_with_prompts_file(session_mgr, args):
    """
    Run workflow using custom prompts file (skip story generation).

    Args:
        session_mgr: SessionManager instance
        args: argparse namespace with command line arguments

    Returns:
        List of shots, or None if failed
    """
    from core.prompts_parser import parse_prompts_file, prompts_to_shots, validate_and_fix_prompts

    prompts_file = args.prompts_file

    # Validate file exists
    if not os.path.exists(prompts_file):
        print(f"[ERROR] Prompts file not found: {prompts_file}")
        return None

    logger.info(f"Using custom prompts file: {prompts_file}")
    print(f"\n[INFO] Loading prompts from: {prompts_file}")

    # Parse prompts file
    try:
        prompts_data, overall_title = parse_prompts_file(prompts_file)
        print(f"[INFO] Parsed {len(prompts_data)} prompts from file")
        prompts_data = validate_and_fix_prompts(prompts_data)
    except Exception as e:
        print(f"[ERROR] Failed to parse prompts file: {e}")
        import traceback
        traceback.print_exc()
        return None

    # Convert to shots format
    shots = prompts_to_shots(prompts_data)

    # Apply defaults from args or config
    default_camera = getattr(args, 'default_camera', None) or config.DEFAULT_CAMERA_FOR_PROMPTS
    default_motion = getattr(args, 'default_motion', None) or config.DEFAULT_MOTION_FOR_PROMPTS

    for shot in shots:
        # Set camera to default (skip auto-detection)
        shot['camera'] = default_camera
        # Set motion_prompt to be the same as image_prompt
        shot['motion_prompt'] = shot['image_prompt']

    print(f"[INFO] Created {len(shots)} shots from prompts")
    print(f"[INFO] Using default camera: {default_camera}")
    print(f"[INFO] motion_prompt set to image_prompt for all shots")

    # Use overall_title or filename as session idea
    idea = overall_title or f"Custom prompts: {os.path.basename(prompts_file)}"

    # Get config from args or config
    image_mode = getattr(args, 'image_mode', None) or config.IMAGE_GENERATION_MODE
    negative_prompt = getattr(args, 'negative_prompt', None) or config.DEFAULT_NEGATIVE_PROMPT
    shot_length = getattr(args, 'shot_length', None) or config.DEFAULT_SHOT_LENGTH
    images_per_shot = getattr(args, 'images_per_shot', None) or config.IMAGES_PER_SHOT

    # Create session
    session_id, session_meta = session_mgr.create_session(idea)

    # Store config in session
    session_meta['video_config'] = {
        'shot_length': shot_length,
        'fps': config.VIDEO_FPS
    }
    session_meta['image_config'] = {
        'mode': image_mode,
        'negative_prompt': negative_prompt,
        'images_per_shot': images_per_shot
    }
    session_meta['prompts_file'] = prompts_file

    # Mark story and scene_graph as complete (skipped)
    session_meta['steps']['story'] = True
    session_meta['steps']['scene_graph'] = True

    session_mgr._save_meta(session_id, session_meta)

    print(f"[INFO] Created session: {session_id}")
    print(f"[INFO] Skipping story generation (using custom prompts)")
    print(f"[INFO] Image generation: {image_mode}")

    # Enhance motion prompts with trigger keywords for LoRA activation
    shots = enhance_motion_prompts_with_triggers(shots)

    # Save shots
    session_mgr.save_shots(session_id, shots)

    # STEP 4.5: Image Generation
    print("\nSTEP 4.5: Image Generation")
    _generate_images(session_id, session_mgr, shots, image_mode, negative_prompt, images_per_shot)

    # Reload shots with image paths
    shots_dir = session_mgr.get_session_dir(session_id)
    shots_path = os.path.join(shots_dir, "shots.json")
    with open(shots_path, 'r', encoding='utf-8') as f:
        shots = json.load(f)

    # Count how many images were actually generated
    shots_with_images = [s for s in shots if s.get('image_path')]
    shots_without_images = [s for s in shots if not s.get('image_path')]

    print(f"\n[INFO] Image generation summary:")
    print(f"  - Total shots: {len(shots)}")
    print(f"  - Shots with images: {len(shots_with_images)}")
    print(f"  - Shots without images: {len(shots_without_images)}")

    if shots_without_images:
        print(f"\n[WARN] The following shots did not generate images:")
        for shot in shots_without_images[:5]:  # Show first 5
            idx = shot.get('index', '?')
            title = shot.get('title', 'No title')[:50]
            print(f"  - Shot {idx}: {title}...")
        if len(shots_without_images) > 5:
            print(f"  ... and {len(shots_without_images) - 5} more")

    # Check if images-only mode
    if getattr(args, 'images_only', False):
        print("\n[INFO] Images-only mode: Skipping video generation")
        session_mgr.mark_session_complete(session_id)
        session_mgr.print_session_summary(session_id)
        return shots

    # STEP 5: Video Rendering
    valid_shots = [s for s in shots if s.get('image_path')]

    if not valid_shots:
        print("\n[ERROR] No images were successfully generated. Cannot proceed to video generation.")
        print(f"[ERROR] Total shots: {len(shots)}, Shots with images: 0")
        print("[INFO] Please check the ComfyUI server and image generation logs")
        return None

    print(f"\n[INFO] ✓ Proceeding to video generation with {len(valid_shots)}/{len(shots)} shots")
    print(f"\nSTEP 5: Rendering {len(valid_shots)} shots")
    _render_videos(session_id, session_mgr, valid_shots, shot_length, shots)

    return shots


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

  # Load idea from default file (input/video_idea.txt)
  python core/main.py

  # Load idea from custom file
  python core/main.py --idea-file ideas/nature_documentary.txt

  # Quick test with limited shots (for testing workflow)
  python core/main.py --idea "Test video" --max-shots 3

  # Generate short video for testing
  python core/main.py --idea "Quick test" --max-shots 2 --no-narration

  # Generate video with specific shots per scene (4 shots x 5 scenes = 20 shots)
  python core/main.py --idea "Nature documentary" --shots-per-scene 4

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

  # Use custom prompts file (skip story generation)
  python core/main.py --prompts-file input/my_prompts.txt

  # Use prompts file with custom default camera
  python core/main.py --prompts-file input/my_prompts.txt --default-camera drone

  # Generate only images from prompts file (no videos)
  python core/main.py --prompts-file input/my_prompts.txt --images-only

  # Use prompts file with multiple image variations
  python core/main.py --prompts-file input/my_prompts.txt --images-per-shot 4 --shot-length 3

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
  --shots-per-scene N    : Generate N shots per scene (default: from config)
  --images-per-shot N    : Generate N image variations per shot (default: 1)
  --no-narration        : Skip narration generation
  --no-resume           : Skip resume prompt, start new session

  Use --list-voices to see ElevenLabs voices
  Use --list-agents to see all available agents
        """
    )

    parser.add_argument(
        '--idea', '-i',
        type=str,
        help='Video idea (inline). If not provided, checks --idea-file, then input/video_idea.txt'
    )

    parser.add_argument(
        '--idea-file', '-f',
        type=str,
        metavar='PATH',
        help='Path to text file containing video idea (default: input/video_idea.txt)'
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
        '--shots-per-scene',
        type=int,
        help=f'Number of shots to generate per scene (default: {config.DEFAULT_SHOTS_PER_SCENE})'
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

    parser.add_argument(
        '--prompts-file',
        '-p',
        type=str,
        metavar='PATH',
        help='Path to custom prompts file to skip story generation. Format: "Prompt N: Title" followed by prompt text'
    )

    parser.add_argument(
        '--default-camera',
        type=str,
        choices=['slow pan', 'pan', 'static', 'orbit', 'zoom', 'tracking', 'drone', 'arc', 'walk', 'fpv', 'dronedive', 'bullettime', 'dolly'],
        default=None,
        help='Default camera type for prompts (default: from config.py)'
    )

    parser.add_argument(
        '--default-motion',
        type=str,
        default=None,
        help='Default motion prompt (default: from config.py)'
    )

    parser.add_argument(
        '--images-only',
        action='store_true',
        help='When using --prompts-file, only generate images without videos'
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
        print("\n" + "="*70)
        print("[ERROR] No video idea provided!")
        print("="*70)
        print("\nPlease provide your video idea using one of these methods:")
        print("\n  1. Use --idea parameter:")
        print("        python core/main.py --idea 'A cat dancing in the rain'")
        print("\n  2. Use --idea-file parameter:")
        print("        python core/main.py --idea-file path/to/your/idea.txt")
        print("\n  3. Create default input file:")
        print("        input/video_idea.txt")
        print("\n" + "="*70)
        print("Examples:")
        print("  python core/main.py --idea 'A cat dancing in the rain'")
        print("  python core/main.py -f my_ideas/nature_documentary.txt")
        print("  python core/main.py --idea-file ideas/sci_fi_video.txt")
        print("\nRun: python core/main.py --help for more options")
        print("="*70)
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

    # Print configuration summary after command-line overrides
    print_configuration_summary()

    # Initialize session manager
    session_mgr = SessionManager()

    # Check for incomplete session (unless --no-resume)
    if args.no_resume:
        session_id, session_meta = None, None
    else:
        session_id, session_meta = check_continue_session(session_mgr)

    if session_id and session_meta:
        # Continue existing session - use the same workflow as new session
        # but with existing session_id and metadata
        try:
            _continue_existing_session(session_id, session_meta, session_mgr, args=args)
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