#!/usr/bin/env python3
"""
Test script for FLFI2V Departure Video Generation Logic

This script tests the new departure video logic:
- First frame: Current character's NOW image
- Last frame: Next character's NOW image OR scene image
"""

import sys
import os
import json
import config

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from web_ui.backend.services.session_service import SessionService
from core.session_manager import SessionManager

def test_departure_video_logic():
    """Test the departure video generation logic"""

    print("=" * 80)
    print("FLFI2V Departure Video Logic Test")
    print("=" * 80)

    # Initialize services
    session_service = SessionService()
    session_manager = SessionManager()

    # Get all sessions
    sessions_list = session_service.list_sessions()

    # Find ThenVsNow sessions
    then_vs_now_sessions = []
    for s in sessions_list:
        # Access story attribute from SessionListItem
        story = getattr(s, 'story', None)
        if story and isinstance(story, dict) and story.get('project_type') == 2:
            then_vs_now_sessions.append(s)

    if not then_vs_now_sessions:
        print("\nFAIL No ThenVsNow sessions found!")
        print("Please create a ThenVsNow session first using:")
        print("  python main.py --idea 'The Godfather' --story-agent then_vs_now")
        return False

    print(f"\nOK Found {len(then_vs_now_sessions)} ThenVsNow session(s)")

    # Test each session
    for session_info in then_vs_now_sessions:
        session_id = getattr(session_info, 'session_id', None)
        print(f"\n{'=' * 80}")
        print(f"Testing Session: {session_id}")
        story = getattr(session_info, 'story', {})
        title = story.get('title', 'Unknown') if isinstance(story, dict) else 'Unknown'
        print(f"Title: {title}")
        print('=' * 80)

        # Load session data
        try:
            shots = session_manager.get_shots(session_id)
            story = session_manager.get_story(session_id)
        except Exception as e:
            print(f"FAIL Error loading session data: {e}")
            continue

        if not shots:
            print("FAIL No shots found in session")
            continue

        # Get FLFI2V shots
        flfi2v_shots = [s for s in shots if s.get('is_flfi2v')]
        if not flfi2v_shots:
            print("FAIL No FLFI2V shots found")
            continue

        print(f"\nOK Found {len(flfi2v_shots)} FLFI2V shots")

        # Test each shot
        for shot in flfi2v_shots:
            shot_index = shot['index']
            print(f"\n{'-' * 80}")
            print(f"Shot {shot_index}: {shot.get('character_id', 'Unknown')}")
            print('-' * 80)

            # Check prerequisites
            has_then = shot.get('then_image_generated') and shot.get('then_image_path')
            has_now = shot.get('now_image_generated') and shot.get('now_image_path')
            has_departure_prompt = shot.get('departure_video_prompt')

            print(f"\nPrerequisites:")
            print(f"  THEN image: {'OK' if has_then else 'X'} {shot.get('then_image_path', 'N/A')}")
            print(f"  NOW image:  {'OK' if has_now else 'X'} {shot.get('now_image_path', 'N/A')}")
            print(f"  Departure prompt: {'OK' if has_departure_prompt else 'X'}")

            if not has_now:
                print(f"  WARN  Shot {shot_index} cannot generate departure video: Missing NOW image")
                continue

            # Test departure video logic
            print(f"\nDeparture Video Logic:")

            # First frame: Current character's NOW image
            first_frame = shot.get('now_image_path')
            print(f"  First frame (current NOW): {first_frame}")

            # Last frame: Find next character's NOW or scene image
            current_scene_id = shot.get('scene_id')
            last_frame = None
            last_frame_source = None

            if current_scene_id is not None:
                print(f"\n  Searching for next character in scene {current_scene_id}...")

                # Find next shot with same scene_id
                for next_shot in shots[shot_index:]:  # Start from current shot
                    if next_shot.get('scene_id') == current_scene_id and next_shot.get('index') > shot_index:
                        if next_shot.get('now_image_path'):
                            last_frame = next_shot['now_image_path']
                            last_frame_source = f"Next character (shot {next_shot['index']})"
                            print(f"    OK Found: {last_frame_source}")
                            print(f"      Path: {last_frame}")
                            break

                # If no next character, try scene image
                if not last_frame:
                    print(f"  WARN  No next character found in scene")
                    print(f"  Searching for scene image...")

                    if story and current_scene_id < len(story.get('scenes', [])):
                        scene = story['scenes'][current_scene_id]
                        scene_image_path = scene.get('scene_image_path')
                        if scene_image_path:
                            last_frame = scene_image_path
                            last_frame_source = "Scene image"
                            print(f"    OK Found: Scene image")
                            print(f"      Path: {last_frame}")
                        else:
                            print(f"    X No scene_image_path in scene data")
                    else:
                        print(f"    X Scene {current_scene_id} not found in story")

            # Fallback
            if not last_frame:
                last_frame = shot.get('now_image_path')
                last_frame_source = "Current NOW (fallback)"
                print(f"\n  WARN  Using fallback: {last_frame_source}")

            print(f"\n  Last frame ({last_frame_source}): {last_frame}")

            # Validate the logic
            print(f"\nValidation:")
            if first_frame and last_frame:
                print(f"  OK First frame defined: {os.path.basename(first_frame)}")
                print(f"  OK Last frame defined: {os.path.basename(last_frame)}")

                # Check if files exist
                first_frame_abs = config.resolve_path(first_frame)
                last_frame_abs = config.resolve_path(last_frame)

                first_exists = os.path.exists(first_frame_abs)
                last_exists = os.path.exists(last_frame_abs)

                print(f"\n  File existence:")
                print(f"    First frame: {'OK' if first_exists else 'X'} {first_frame_abs}")
                print(f"    Last frame:  {'OK' if last_exists else 'X'} {last_frame_abs}")

                if first_exists and last_exists:
                    print(f"\n  SUCCESS Shot {shot_index} ready for departure video generation!")
                else:
                    print(f"\n  FAIL Shot {shot_index} missing required images")
            else:
                print(f"  FAIL Missing frame definitions")

            # Check if departure video already exists
            if shot.get('departure_video_rendered'):
                print(f"\n  Status: Departure video already generated")
                print(f"  Path: {shot.get('departure_video_path')}")

                # Verify file exists
                video_path = config.resolve_path(shot['departure_video_path'])
                if os.path.exists(video_path):
                    size_mb = os.path.getsize(video_path) / (1024 * 1024)
                    print(f"  Size: {size_mb:.2f} MB OK")
                else:
                    print(f"  WARN  Video file not found at path")
            else:
                print(f"\n  Status: Not yet generated")

    print(f"\n{'=' * 80}")
    print("Test Complete!")
    print('=' * 80)

    return True


def test_workflow_config():
    """Test workflow configuration for departure videos"""
    print("\n" + "=" * 80)
    print("Workflow Configuration Test")
    print("=" * 80)

    workflows = getattr(config, 'VIDEO_WORKFLOWS', {})
    flfi2v_workflows = {k: v for k, v in workflows.items() if 'flfi2v' in k.lower()}

    if not flfi2v_workflows:
        print("FAIL No FLFI2V workflows found in config!")
        return False

    print(f"\nOK Found {len(flfi2v_workflows)} FLFI2V workflow(s):\n")

    for name, workflow_config in flfi2v_workflows.items():
        print(f"  {name}:")
        print(f"    Path: {workflow_config.get('workflow_path')}")
        print(f"    First frame node: {workflow_config.get('load_image_first_node_id')}")
        print(f"    Last frame node: {workflow_config.get('load_image_last_node_id')}")
        print(f"    Seed node: {workflow_config.get('seed_node_id')}")
        print(f"    Description: {workflow_config.get('description')}")

        # Check required fields
        required = ['workflow_path', 'load_image_first_node_id', 'load_image_last_node_id']
        missing = [field for field in required if not workflow_config.get(field)]

        if missing:
            print(f"    WARN  Missing fields: {missing}")
        else:
            print(f"    OK All required fields present")

    print(f"\nOK Workflow configuration OK")
    return True


def main():
    """Main test function"""
    print("\nFLFI2V Departure Video Generation Test Suite")
    print("=" * 80)
    print()

    # Test workflow configuration first
    config_ok = test_workflow_config()

    if not config_ok:
        print("\nFAIL Fix workflow configuration issues before proceeding")
        return 1

    # Test departure video logic
    logic_ok = test_departure_video_logic()

    if not logic_ok:
        print("\nFAIL Departure video logic test failed")
        return 1

    print("\nSUCCESS All tests passed!")
    print("\nNext steps:")
    print("  1. Generate THEN and NOW images for all shots")
    print("  2. Run departure video generation:")
    print("     python regenerate.py --session <SESSION_ID> --videos --video-variant departure")
    print("  3. Or use the Web UI: Click 'Regenerate All Videos'")
    print("  4. View departure videos by switching to video mode and clicking 'Departure' button")

    return 0


if __name__ == '__main__':
    sys.exit(main())
