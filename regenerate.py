"""
Video Regeneration CLI Tool
Re-render videos from existing sessions with optional length changes
Also supports regenerating failed images
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.video_regenerator import regenerate_videos, interactive_regenerate


def regenerate_images(session_id):
    """Regenerate failed images for a session"""
    from core.session_manager import SessionManager

    session_mgr = SessionManager()
    session = session_mgr.load_session(session_id)

    if not session:
        print(f"[ERROR] Session {session_id} not found")
        return False

    print(f"\n[REGENERATE] Session: {session_id}")
    print(f"Idea: {session['idea'][:80]}...")

    # Load shots
    shots_dir = session_mgr.get_session_dir(session_id)
    shots_path = os.path.join(shots_dir, "shots.json")

    if not os.path.exists(shots_path):
        print(f"[ERROR] Shots file not found: {shots_path}")
        return False

    import json
    with open(shots_path, 'r', encoding='utf-8') as f:
        shots = json.load(f)

    # Get image config
    image_config = session.get('image_config', {})
    image_mode = image_config.get('mode', 'gemini')
    negative_prompt = image_config.get('negative_prompt', "")

    print(f"[INFO] Using {image_mode} for image generation")

    # Find failed images (both not generated and generated but missing file)
    failed_images = []
    images_dir = session_mgr.get_images_dir(session_id)

    # Check for failed images
    for idx, shot_meta in enumerate(session['shots']):
        shot_idx = idx + 1  # 1-based index
        expected_filename = f"shot_{shot_idx:03d}.png"
        expected_path = os.path.join(images_dir, expected_filename)

        # Check if actual file exists
        file_exists = os.path.exists(expected_path)

        if not file_exists:
            # Image file doesn't exist - needs regeneration
            failed_images.append({
                'index': shot_idx,
                'shot_data': shot_meta,
                'shot_index': idx  # for accessing shots array
            })
        elif not shot_meta['image_generated']:
            # File exists but metadata not updated - fix it
            print(f"[INFO] Fixing metadata for shot {shot_idx} (image exists but not marked)")
            session_mgr.mark_image_generated(session_id, shot_idx, expected_path)

    if not failed_images:
        print("[INFO] No failed images found. All images are intact.")
        # Create a new shots array with image_path included for video regeneration
        shots_with_paths = []
        for idx, shot in enumerate(shots):
            shot_idx = idx + 1
            expected_filename = f"shot_{shot_idx:03d}.png"
            expected_path = os.path.join(images_dir, expected_filename)
            if os.path.exists(expected_path):
                # Normalize path to use forward slashes (JSON-safe)
                normalized_path = expected_path.replace('\\', '/')
                shot['image_path'] = normalized_path
            shots_with_paths.append(shot)

        # Save the updated shots array with proper paths
        shots_path = os.path.join(session_mgr.get_session_dir(session_id), "shots.json")
        with open(shots_path, 'w', encoding='utf-8') as f:
            json.dump(shots_with_paths, f, indent=2, ensure_ascii=False)
        return True

    print(f"[INFO] Found {len(failed_images)} failed image(s)")

    # Regenerate
    images_dir = session_mgr.get_images_dir(session_id)
    os.makedirs(images_dir, exist_ok=True)

    regenerated_count = 0
    for failed_item in failed_images:
        shot_idx = failed_item['index']
        shot_array_idx = failed_item['shot_index']
        shot = shots[shot_array_idx]

        image_prompt = shot.get('image_prompt', '')
        if not image_prompt:
            print(f"[SKIP] Shot {shot_idx}: No image prompt")
            continue

        filename = f"shot_{shot_idx:03d}.png"
        output_path = os.path.join(images_dir, filename)

        print(f"[{shot_idx}/{len(failed_images)}] Regenerating: {image_prompt[:50]}...")

        if image_mode == "comfyui":
            from core.comfyui_image_generator import generate_image_comfyui
            image_path = generate_image_comfyui(image_prompt, output_path, negative_prompt)
        else:
            from core.image_generator import generate_image_gemini
            image_path = generate_image_gemini(image_prompt, output_path)

        if image_path:
            # Update local shots array
            shot['image_path'] = image_path

            # Update session metadata
            session_mgr.mark_image_generated(session_id, shot_idx, image_path)
            regenerated_count += 1
            print(f"[PASS] Regenerated shot {shot_idx}")
        else:
            print(f"[FAIL] Failed to regenerate shot {shot_idx}")

    print(f"\n[SUCCESS] Regenerated {regenerated_count}/{len(failed_images)} images")

    # Final sync: create shots array with image_path for all shots
    shots_with_paths = []
    for idx, shot in enumerate(shots):
        shot_idx = idx + 1
        expected_filename = f"shot_{shot_idx:03d}.png"
        expected_path = os.path.join(images_dir, expected_filename)

        # Copy the shot data
        shot_with_path = shot.copy()

        # Add image_path if file exists
        if os.path.exists(expected_path):
            # Normalize path to use forward slashes (JSON-safe)
            normalized_path = expected_path.replace('\\', '/')
            shot_with_path['image_path'] = normalized_path

        shots_with_paths.append(shot_with_path)

    # Save updated shots to file
    shots_path = os.path.join(session_mgr.get_session_dir(session_id), "shots.json")
    with open(shots_path, 'w', encoding='utf-8') as f:
        json.dump(shots_with_paths, f, indent=2, ensure_ascii=False)

    print(f"[INFO] Updated shots.json and session metadata")
    print(f"[INFO] Shots now have image_path field for video regeneration")
    return True


def show_help():
    """Show help message"""
    print("""
AI Film Studio - Video & Image Regeneration Tool

Regenerate videos or images from existing sessions. Change video length,
re-render with different settings, or regenerate failed images.

Usage:
  python regenerate.py                    # Interactive mode
  python regenerate.py --interactive       # Interactive mode
  python regenerate.py --list             # List all sessions
  python regenerate.py --session <id>      # Regenerate specific session
  python regenerate.py --session <id> --length 10    # Change to 10s shots
  python regenerate.py --session <id> --force       # Re-render all videos
  python regenerate.py --session <id> --images      # Regenerate failed images

Options:
  --interactive     Interactive mode with menus
  --session <id>    Session ID to regenerate
  --length <secs>   New shot length in seconds
  --force           Regenerate all videos (including already rendered)
  --list            List all sessions
  --images          Regenerate failed images only

Examples:
  # Interactive mode - easiest way
  python regenerate.py

  # List all sessions first
  python regenerate.py --list

  # Regenerate session with new shot length
  python regenerate.py --session session_20250208_002238 --length 10

  # Force re-render all videos in a session
  python regenerate.py --session session_20250208_002238 --force

  # Regenerate only failed images
  python regenerate.py --session session_20250208_002238 --images

  # Change length and re-render all
  python regenerate.py --session session_20250208_002238 --length 8 --force

Use Cases:
  - Want longer/shorter shots: Use --length
  - ComfyUI had errors: Use --force
  - Images failed to generate: Use --images
  - Try different video length: Use --length
  - Re-render with better quality: Use --force

For more details, see VIDEO_REGENERATION_GUIDE.md
""")


def list_sessions():
    """List all sessions"""
    from core.session_manager import SessionManager

    session_mgr = SessionManager()
    sessions = session_mgr.list_all_sessions()

    if not sessions:
        print("\n[INFO] No sessions found.")
        return

    print("\n" + "="*80)
    print("AI FILM STUDIO - SESSIONS")
    print("="*80)

    for session in sessions:
        status = "[COMPLETE]" if session['completed'] else "[IN PROGRESS]"
        video_config = session.get('video_config', {})
        shot_length = video_config.get('shot_length', 5.0)

        print(f"\n{status} | {session['session_id']}")
        print(f"  Idea: {session['idea'][:80]}...")
        print(f"  Started: {session['started_at']}")
        print(f"  Shot length: {shot_length}s")
        print(f"  Progress: {session['stats']['images_generated']}/{session['stats']['total_shots']} images, "
              f"{session['stats']['videos_rendered']} videos")

    print("\n" + "="*80)
    print("\nTo regenerate, use:")
    print("  python regenerate.py --session <session_id>")
    print("  python regenerate.py --session <session_id> --length <seconds>")
    print("  python regenerate.py --session <session_id> --force")
    print("  python regenerate.py --session <session_id> --images")


if __name__ == "__main__":
    import argparse

    if len(sys.argv) == 1 or '--help' in sys.argv or '-h' in sys.argv:
        show_help()
        sys.exit(0)

    parser = argparse.ArgumentParser(
        description="Regenerate videos/images from AI Film Studio sessions",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--interactive', '-i', action='store_true',
                        help='Interactive mode with menus')
    parser.add_argument('--session', '-s', type=str, metavar='ID',
                        help='Session ID to regenerate')
    parser.add_argument('--length', '-l', type=float, metavar='SECONDS',
                        help='New shot length in seconds (for videos)')
    parser.add_argument('--force', '-f', action='store_true',
                        help='Regenerate all videos (including already rendered)')
    parser.add_argument('--images', action='store_true',
                        help='Regenerate failed images only')
    parser.add_argument('--list', action='store_true',
                        help='List all sessions')

    args = parser.parse_args()

    if args.list:
        list_sessions()
    elif args.images:
        if not args.session:
            print("[ERROR] --images requires --session <id>")
            print("\nExample: python regenerate.py --session session_XXX --images")
            sys.exit(1)
        regenerate_images(args.session)
    elif args.interactive or not args.session:
        interactive_regenerate()
    else:
        regenerate_videos(args.session, new_shot_length=args.length, force_regenerate_all=args.force)
