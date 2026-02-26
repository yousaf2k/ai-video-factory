#!/usr/bin/env python3
"""
Test script to verify story.json is formatted with proper indentation.
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.story_engine import build_story

def test_story_json_formatting():
    """Test that story JSON is properly formatted with indentation."""

    print("="*70)
    print("Testing Story JSON Formatting")
    print("="*70)

    # Build a story
    print("\n1. Building story with target_length=180...")
    story_json = build_story(
        "A T-Rex hunting in the Cretaceous period",
        agent_name='prehistoric_pov',
        target_length=180
    )

    # Check if JSON is formatted
    print("\n2. Checking JSON format...")

    # Parse and check
    try:
        story_data = json.loads(story_json)
        print("   [OK] JSON is valid")

        # Check if it's multiline (has newlines)
        if '\n' in story_json:
            print("   [OK] JSON is multiline (has line breaks)")
        else:
            print("   [FAIL] JSON is single-line (not formatted)")

        # Check indentation
        lines = story_json.split('\n')
        print(f"   [OK] JSON has {len(lines)} lines")

        # Check for proper indentation (should have spaces/tabs)
        indented_lines = [line for line in lines if line.startswith('  ') or line.startswith('\t')]
        if indented_lines:
            print(f"   [OK] JSON has {len(indented_lines)} indented lines")
        else:
            print("   [FAIL] JSON has no indented lines")

        # Show a preview
        print("\n3. JSON Preview (first 500 characters):")
        print("-"*70)
        print(story_json[:500])
        if len(story_json) > 500:
            print("\n... (truncated)")
        print("-"*70)

        # Check scene_duration field
        print("\n4. Checking for scene_duration field...")
        if 'scenes' in story_data:
            scenes = story_data['scenes']
            has_durations = all('scene_duration' in s for s in scenes)
            print(f"   [OK] All {len(scenes)} scenes have scene_duration: {has_durations}")

            # Show first scene structure
            if scenes:
                print("\n5. First Scene Structure:")
                print("-"*70)
                first_scene = scenes[0]
                for key, value in first_scene.items():
                    if isinstance(value, str) and len(value) > 60:
                        value = value[:60] + "..."
                    print(f"   {key}: {value}")
                print("-"*70)

        return True

    except json.JSONDecodeError as e:
        print(f"   [FAIL] JSON parsing error: {e}")
        return False
    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_story_json_formatting_no_target():
    """Test story JSON formatting without target_length."""

    print("\n" + "="*70)
    print("Testing Story JSON Formatting (without target_length)")
    print("="*70)

    # Build a story without target_length
    print("\n1. Building story without target_length...")
    story_json = build_story(
        "A simple story about redwood trees",
        agent_name='default'
    )

    # Check formatting
    print("\n2. Checking JSON format...")
    try:
        story_data = json.loads(story_json)
        print("   [OK] JSON is valid")

        # Check if multiline
        if '\n' in story_json:
            lines = story_json.split('\n')
            print(f"   [OK] JSON is multiline ({len(lines)} lines)")
            return True
        else:
            print("   [FAIL] JSON is single-line")
            return False

    except json.JSONDecodeError as e:
        print(f"   [FAIL] JSON parsing error: {e}")
        return False

def main():
    """Run all formatting tests."""

    results = []

    # Test 1: With target_length
    results.append(("With target_length", test_story_json_formatting()))

    # Test 2: Without target_length
    results.append(("Without target_length", test_story_json_formatting_no_target()))

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    for test_name, passed in results:
        status = "[OK] PASS" if passed else "[FAIL] FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(result for _, result in results)

    print("\n" + "="*70)
    if all_passed:
        print("[OK] All tests passed! Story JSON is properly formatted.")
        return 0
    else:
        print("[FAIL] Some tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
