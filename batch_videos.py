"""
Batch Video Generation from Images
Load images from a folder and generate videos using ComfyUI
- Filename (without extension) is used as motion prompt
- Camera type is detected from filename if present
- Falls back to default camera if not specified
"""
import os
import sys
import argparse
import re
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.session_manager import SessionManager
from core.prompt_compiler import load_workflow, compile_workflow
from core.comfy_client import submit, wait_for_prompt_completion, get_output_file_path
from core.video_regenerator import generate_unique_video_filename
import config


# Camera type patterns
CAMERA_PATTERNS = {
    'static': r'\bstatic\s*camera\b',
    'zoom': r'\bzoom\s*camera\b|\bzoom\s*(in|out)\b',
    'pan': r'\bpan\s*camera\b|\bpan\s*(left|right|up|down)\b',
    'tilt': r'\btilt\s*camera\b|\btilt\s*(up|down)\b',
    'dolly': r'\bdolly\s*camera\b|\bdolly\s*(in|out|left|right)\b',
    'truck': r'\btruck\s*camera\b|\btruck\s*(left|right)\b',
    'pedestal': r'\bpedestal\s*camera\b|\bpedestal\s*(up|down)\b',
    'orbit': r'\borbit\s*camera\b|\borbit\s*(left|right)\b',
    'crane': r'\bcrane\s*(up|down|in|out)\b',
    'handheld': r'\bhandheld\s*camera\b',
    'tracking': r'\btracking\s*shot\b',
    'push': r'\bpush\s*(in|on)\b',
    'pull': r'\bpull\s*(back|out)\b',
}


def detect_camera_type(filename):
    """
    Detect camera type from filename.

    Args:
        filename: Image filename (can include path)

    Returns:
        tuple: (camera_type, motion_prompt_without_camera)
              If no camera detected, returns (default_camera, original_prompt)
    """
    # Remove extension and path
    name = Path(filename).stem
    name_lower = name.lower().replace('_', ' ').replace('-', ' ')

    # Check for each camera pattern
    for camera_type, pattern in CAMERA_PATTERNS.items():
        match = re.search(pattern, name_lower, re.IGNORECASE)
        if match:
            # Remove the camera reference from the prompt
            prompt_without_camera = re.sub(pattern, '', name_lower, flags=re.IGNORECASE)
            prompt_without_camera = re.sub(r'\s+', ' ', prompt_without_camera).strip()
            return camera_type, prompt_without_camera

    # No camera detected, return default
    default_camera = 'static'
    return default_camera, name.replace('_', ' ').replace('-', ' ')


def load_images_from_folder(folder_path, image_extensions=None):
    """
    Load all images from a folder and create shot data.

    Args:
        folder_path: Path to folder containing images
        image_extensions: List of image extensions to include (default: common formats)

    Returns:
        list: Shot dictionaries with image_path, motion_prompt, camera
    """
    if image_extensions is None:
        image_extensions = ['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff', '.gif']

    folder_path = Path(folder_path)
    if not folder_path.exists():
        raise FileNotFoundError(f"Folder not found: {folder_path}")

    shots = []
    image_files = []

    # Collect all image files
    for ext in image_extensions:
        image_files.extend(folder_path.glob(f"*{ext}"))
        image_files.extend(folder_path.glob(f"*{ext.upper()}"))

    # Sort files by name for consistent ordering
    image_files.sort(key=lambda x: x.name.lower())

    if not image_files:
        raise ValueError(f"No image files found in {folder_path}")

    print(f"[INFO] Found {len(image_files)} image(s) in {folder_path}")

    for idx, image_path in enumerate(image_files, start=1):
        # Detect camera type and get motion prompt
        camera, motion_prompt = detect_camera_type(image_path.name)

        shot = {
            'index': idx,
            'image_path': str(image_path.absolute()),
            'motion_prompt': motion_prompt,
            'camera': camera,
            'original_filename': image_path.name
        }
        shots.append(shot)

        print(f"[{idx}/{len(image_files)}] {image_path.name}")
        print(f"       Motion: {motion_prompt}")
        print(f"       Camera: {camera}")

    return shots


def generate_videos_from_images(shots, output_dir, video_length=5, session_id=None):
    """
    Generate videos from a list of shots with images.

    Args:
        shots: List of shot dictionaries with image_path, motion_prompt, camera
        output_dir: Directory to save videos
        video_length: Length of each video in seconds
        session_id: Optional session ID for tracking

    Returns:
        tuple: (success_count, failed_count, errors)
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Load ComfyUI workflow
    print(f"\n[INFO] Loading ComfyUI workflow (video length: {video_length}s)...")
    try:
        template = load_workflow(config.WORKFLOW_PATH, video_length_seconds=video_length)
    except Exception as e:
        print(f"[ERROR] Failed to load workflow: {e}")
        return 0, len(shots), [f"Workflow load failed: {e}"]

    # Initialize session manager if session_id provided
    session_mgr = SessionManager() if session_id else None

    success_count = 0
    failed_count = 0
    errors = []

    print(f"\n[INFO] Generating videos for {len(shots)} shot(s)...")
    print("="*70)

    for shot in shots:
        shot_idx = shot['index']
        image_path = shot['image_path']
        motion_prompt = shot['motion_prompt']
        camera = shot['camera']

        print(f"\n[{shot_idx}/{len(shots)}] Processing: {shot.get('original_filename', image_path)}")
        print(f"       Motion: {motion_prompt}")
        print(f"       Camera: {camera}")

        # Verify image exists
        if not os.path.exists(image_path):
            error = f"Image not found: {image_path}"
            print(f"[ERROR] {error}")
            errors.append(f"Shot {shot_idx}: {error}")
            failed_count += 1
            continue

        # Generate unique video filename
        video_filename, video_save_path = generate_unique_video_filename(output_dir, shot_idx)

        # Prepare shot data for workflow compilation
        shot_data = {
            'index': shot_idx,
            'image_path': image_path,
            'motion_prompt': motion_prompt,
            'camera': camera
        }

        try:
            # Compile and submit workflow
            wf = compile_workflow(template, shot_data, video_length_seconds=video_length)
            result = submit(wf)

            prompt_id = result.get('prompt_id')
            if not prompt_id:
                error = "No prompt_id returned from ComfyUI"
                print(f"[ERROR] {error}")
                errors.append(f"Shot {shot_idx}: {error}")
                failed_count += 1
                continue

            print(f"[QUEUE] Prompt {prompt_id[:8]}... submitted")

            # Wait for completion
            print(f"[WAIT] Waiting for render...")
            wait_result = wait_for_prompt_completion(prompt_id, timeout=config.VIDEO_RENDER_TIMEOUT)

            if not wait_result['success']:
                error = wait_result.get('error', 'Unknown error')
                print(f"[FAIL] {error}")
                errors.append(f"Shot {shot_idx}: {error}")
                failed_count += 1
                continue

            # Check outputs
            outputs = wait_result.get('outputs', [])
            if not outputs:
                error = "No output files generated"
                print(f"[FAIL] {error}")
                errors.append(f"Shot {shot_idx}: {error}")
                failed_count += 1
                continue

            # Find video outputs
            video_outputs = [o for o in outputs if o['type'] == 'video']

            if video_outputs:
                import shutil
                import time

                video_info = video_outputs[0]
                source_path = get_output_file_path(video_info)

                # Wait for file to be written to disk
                max_retries = 10
                retry_delay = 2
                file_found = False

                for attempt in range(max_retries):
                    if os.path.exists(source_path):
                        initial_size = os.path.getsize(source_path)
                        time.sleep(1)
                        final_size = os.path.getsize(source_path)

                        if initial_size == final_size and final_size > 0:
                            file_found = True
                            break
                        else:
                            if attempt < max_retries - 1:
                                print(f"[WAIT] File still writing... (retry {attempt + 1}/{max_retries})")
                                time.sleep(retry_delay)

                if file_found:
                    shutil.copy2(source_path, video_save_path)
                    file_size = os.path.getsize(video_save_path)
                    print(f"[PASS] Video saved: {video_filename} ({file_size:,} bytes)")

                    # Update session if provided
                    if session_mgr and session_id:
                        session_mgr.mark_video_rendered(session_id, shot_idx, video_save_path)

                    success_count += 1
                else:
                    error = "Source video not found after retries"
                    print(f"[FAIL] {error}")
                    errors.append(f"Shot {shot_idx}: {error}")
                    failed_count += 1

            else:
                # Check if image outputs (frames) were generated instead
                image_outputs = [o for o in outputs if o['type'] == 'image']
                if image_outputs:
                    error = "Generated frames instead of video"
                    print(f"[FAIL] {error}")
                    errors.append(f"Shot {shot_idx}: {error}")
                    failed_count += 1
                else:
                    error = "Unknown output type"
                    print(f"[FAIL] {error}")
                    errors.append(f"Shot {shot_idx}: {error}")
                    failed_count += 1

        except Exception as e:
            error = f"Exception: {str(e)}"
            print(f"[ERROR] {error}")
            errors.append(f"Shot {shot_idx}: {error}")
            failed_count += 1
            import traceback
            traceback.print_exc()

    # Summary
    print("\n" + "="*70)
    print("GENERATION SUMMARY")
    print("="*70)
    print(f"Successful: {success_count}/{len(shots)}")
    print(f"Failed: {failed_count}/{len(shots)}")

    if errors:
        print("\n[ERRORS] Failed generations:")
        for error in errors:
            print(f"  - {error}")

    print("="*70)

    return success_count, failed_count, errors


def main():
    parser = argparse.ArgumentParser(
        description='Generate videos from images in a folder',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate videos from all images in a folder
  python batch_videos.py input_images/ output_videos/

  # Specify video length
  python batch_videos.py input_images/ output_videos/ --length 10

  # Create a session for tracking
  python batch_videos.py input_images/ output_videos/ --session my_video_project

Camera Types (detected from filename):
  static, zoom, pan, tilt, dolly, truck, pedestal, orbit, crane, handheld, tracking, push, pull

Filename Examples:
  beautiful_girl_dancing_static_camera.png
  sunset_zoom_camera.jpg
  city_pan_left-camera.gif
        """
    )

    parser.add_argument('input_folder', help='Folder containing input images')
    parser.add_argument('output_folder', help='Folder to save generated videos')
    parser.add_argument('--length', type=int, default=5,
                        help='Video length in seconds (default: 5)')
    parser.add_argument('--session', type=str, default=None,
                        help='Optional session ID for tracking progress')
    parser.add_argument('--list-cameras', action='store_true',
                        help='List supported camera types and exit')

    args = parser.parse_args()

    if args.list_cameras:
        print("Supported Camera Types (detect from filename):")
        for camera in CAMERA_PATTERNS.keys():
            print(f"  - {camera}")
        print("\nDefault camera: static")
        return

    try:
        # Load images from folder
        print("="*70)
        print("BATCH VIDEO GENERATION FROM IMAGES")
        print("="*70)
        print(f"\nInput folder: {args.input_folder}")
        print(f"Output folder: {args.output_folder}")
        print(f"Video length: {args.length}s")
        print(f"Session: {args.session or 'None'}")

        shots = load_images_from_folder(args.input_folder)

        # Create session if specified
        if args.session:
            session_mgr = SessionManager()
            # Create a new session with idea
            idea = f"Batch video generation from images in {args.input_folder}"
            session_id, _ = session_mgr.create_session(idea, session_id=args.session)
            print(f"\n[INFO] Created session: {session_id}")
        else:
            session_id = args.session

        # Generate videos
        success, failed, errors = generate_videos_from_images(
            shots,
            args.output_folder,
            video_length=args.length,
            session_id=session_id
        )

        # Mark session complete if created
        if args.session:
            session_mgr = SessionManager()
            if failed == 0:
                session_mgr.mark_session_complete(session_id)
                print(f"\n[SUCCESS] Session {session_id} complete!")
            else:
                print(f"\n[WARNING] Session {session_id} completed with errors.")

        # Exit with appropriate code
        sys.exit(0 if failed == 0 else 1)

    except FileNotFoundError as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n[INFO] Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
