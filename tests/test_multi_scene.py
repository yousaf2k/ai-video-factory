"""
Test script for multi-scene ThenVsNow implementation
Tests shot generation and departure video transitions
"""

import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from core.story_engine import generate_shots_from_then_vs_now_story

# Sample story with 2 scenes
SAMPLE_STORY = {
    "project_type": 2,
    "title": "The Godfather: The Reunion",
    "description": "A cinematic Then vs Now reunion",
    "style": "cinematic ensemble reunion",
    "movie_metadata": {
        "year": 1972,
        "cast": ["Marlon Brando as Don Vito Corleone", "Al Pacino as Michael Corleone", "James Caan as Sonny Corleone"],
        "director": "Francis Ford Coppola",
        "genre": "Crime Drama"
    },
    "scenes": [
        {
            "scene_id": 0,
            "scene_name": "Main Cast",
            "location": "Don Corleone's Office",
            "set_prompt": "Dark office with vintage desk",
            "characters": ["Marlon Brando as Don Vito Corleone", "Al Pacino as Michael Corleone"],
            "action": "Meeting scene",
            "emotion": "Nostalgic",
            "narration": "The family reunites",
            "scene_duration": 30
        },
        {
            "scene_id": 1,
            "scene_name": "Supporting Cast",
            "location": "The Corleone Compound",
            "set_prompt": "Outdoor compound with gardens",
            "characters": ["James Caan as Sonny Corleone"],
            "action": "Departure scene",
            "emotion": "Bittersweet",
            "narration": "Remembering the past",
            "scene_duration": 20
        }
    ],
    "characters": [
        {
            "name": "Marlon Brando as Don Vito Corleone",
            "scene_id": 0,
            "then_prompt": "Young Marlon Brando in tuxedo",
            "now_prompt": "Older Marlon Brando with iPhone selfie",
            "meeting_prompt": "THEN MEETS NOW: Young Don Vito hugs older version",
            "departure_prompt": "Both characters walk to right, talking"
        },
        {
            "name": "Al Pacino as Michael Corleone",
            "scene_id": 0,
            "then_prompt": "Young Al Pacino in suit",
            "now_prompt": "Older Al Pacino with iPhone selfie",
            "meeting_prompt": "THEN MEETS NOW: Young Michael hugs older version",
            "departure_prompt": "Both characters walk to right, talking"
        },
        {
            "name": "James Caan as Sonny Corleone",
            "scene_id": 1,
            "then_prompt": "Young James Caan in vest",
            "now_prompt": "Older James Caan with iPhone selfie",
            "meeting_prompt": "THEN MEETS NOW: Young Sonny hugs older version",
            "departure_prompt": "Both characters walk to right, talking"
        }
    ]
}


def test_shot_generation():
    """Test shot generation from multi-scene story"""
    print("=" * 80)
    print("TEST 1: Shot Generation")
    print("=" * 80)

    shots = generate_shots_from_then_vs_now_story(SAMPLE_STORY)

    print(f"\n[PASS] Generated {len(shots)} shots from {len(SAMPLE_STORY['characters'])} characters")

    # Verify each shot has required fields
    required_fields = [
        'id', 'index', 'is_flfi2v', 'character_id',
        'character_name', 'scene_id', 'scene_name', 'order_in_scene',
        'then_image_prompt', 'now_image_prompt',
        'meeting_video_prompt', 'departure_video_prompt'
    ]

    for i, shot in enumerate(shots):
        print(f"\n--- Shot {shot['index']} ---")
        print(f"  Character: {shot.get('character_name')}")
        print(f"  Scene: {shot.get('scene_name')} (ID: {shot.get('scene_id')})")
        print(f"  Order in Scene: {shot.get('order_in_scene')}")
        print(f"  Character ID: {shot.get('character_id')}")

        # Check all required fields
        for field in required_fields:
            if field not in shot:
                print(f"  [FAIL] MISSING FIELD: {field}")
                return False

        print(f"  [PASS] All fields present")

    # Verify scene grouping
    scene_0_shots = [s for s in shots if s['scene_id'] == 0]
    scene_1_shots = [s for s in shots if s['scene_id'] == 1]

    print(f"\n[PASS] Scene 0 (Main Cast): {len(scene_0_shots)} shots")
    print(f"[PASS] Scene 1 (Supporting Cast): {len(scene_1_shots)} shots")

    # Verify order_in_scene
    for shot in scene_0_shots:
        if shot['order_in_scene'] not in [0, 1]:
            print(f"  [FAIL] Invalid order_in_scene for {shot['character_name']}")
            return False
    print("[PASS] order_in_scene values correct for Scene 0")

    if scene_1_shots[0]['order_in_scene'] != 0:
        print(f"  [FAIL] Invalid order_in_scene for {scene_1_shots[0]['character_name']}")
        return False
    print("[PASS] order_in_scene values correct for Scene 1")

    return shots


def test_departure_transitions(shots):
    """Test departure video transition algorithm"""
    print("\n" + "=" * 80)
    print("TEST 2: Departure Video Transitions")
    print("=" * 80)

    # Import the generation service class
    from web_ui.backend.services.generation_service import GenerationService

    # Create a mock instance (we only need the method)
    class MockGenerationService:
        pass

    # Add the method to our mock
    MockGenerationService._find_next_shot_for_departure = \
        GenerationService._find_next_shot_for_departure

    service = MockGenerationService()

    print("\n--- Testing Transitions ---\n")

    for i, shot in enumerate(shots):
        result = service._find_next_shot_for_departure(shot, shots, SAMPLE_STORY)

        current_name = shot.get('character_name', f"Shot {shot['index']}")
        next_name = result['next_shot'].get('character_name', f"Shot {result['next_shot']['index']}")

        print(f"Shot {shot['index']} ({current_name})")
        print(f"  -> Transition Type: {result['transition_type']}")
        print(f"  -> Next Shot: {result['next_shot']['index']} ({next_name})")
        print(f"  -> Description: {result['description']}")
        print(f"  -> Last Frame Image: {result['last_frame_image'] or 'None'}")
        print()

    # Verify expected transitions
    expected_transitions = [
        (0, 1, "within_scene", "Marlon Brando -> Al Pacino (both in Main Cast)"),
        (1, 2, "cross_scene", "Al Pacino -> James Caan (Main Cast -> Supporting Cast)"),
        (2, 0, "circular", "James Caan -> Marlon Brando (loop back to start)")
    ]

    print("\n--- Verifying Expected Transitions ---\n")

    for from_idx, to_idx, trans_type, description in expected_transitions:
        from_shot = shots[from_idx]
        result = service._find_next_shot_for_departure(from_shot, shots, SAMPLE_STORY)

        if result['transition_type'] != trans_type:
            print(f"[FAIL] Shot {from_idx + 1}: Expected {trans_type}, got {result['transition_type']}")
            return False

        if result['next_shot']['index'] != to_idx + 1:
            print(f"[FAIL] Shot {from_idx + 1}: Expected next shot {to_idx + 1}, got {result['next_shot']['index']}")
            return False

        print(f"[PASS] Shot {from_idx + 1} -> {to_idx + 1}: {trans_type} ({description})")

    return True


def test_backward_compatibility():
    """Test backward compatibility with all characters in scene 0"""
    print("\n" + "=" * 80)
    print("TEST 3: Backward Compatibility (All in Scene 0)")
    print("=" * 80)

    # Old-style story with no scene grouping
    old_story = {
        "project_type": 2,
        "title": "Old Story",
        "scenes": [
            {
                "scene_id": 0,
                "location": "Same location",
                "characters": "Actor 1, Actor 2",
                "action": "Action",
                "emotion": "Emotion",
                "narration": "Narration",
                "scene_duration": 30
            }
        ],
        "characters": [
            {
                "name": "Actor 1",
                "scene_id": 0,  # All in scene 0
                "then_prompt": "Young actor 1",
                "now_prompt": "Old actor 1",
                "meeting_prompt": "Meeting 1",
                "departure_prompt": "Departure 1"
            },
            {
                "name": "Actor 2",
                "scene_id": 0,  # All in scene 0
                "then_prompt": "Young actor 2",
                "now_prompt": "Old actor 2",
                "meeting_prompt": "Meeting 2",
                "departure_prompt": "Departure 2"
            }
        ]
    }

    shots = generate_shots_from_then_vs_now_story(old_story)

    print(f"\n[PASS] Generated {len(shots)} shots")

    # Verify all are in scene 0
    for shot in shots:
        if shot['scene_id'] != 0:
            print(f"[FAIL] Shot {shot['index']} has scene_id {shot['scene_id']}, expected 0")
            return False

    print("[PASS] All shots in scene 0")

    # Verify transitions are all within_scene
    from web_ui.backend.services.generation_service import GenerationService

    class MockGenerationService:
        pass

    MockGenerationService._find_next_shot_for_departure = \
        GenerationService._find_next_shot_for_departure

    service = MockGenerationService()

    # For a single-scene story, the last shot should do a circular transition
    for i, shot in enumerate(shots):
        result = service._find_next_shot_for_departure(shot, shots, old_story)

        # First shot: within_scene (to next shot)
        # Last shot: circular (back to first shot)
        if i == 0:
            expected = 'within_scene'
        else:  # Last shot
            expected = 'circular'

        if result['transition_type'] != expected:
            print(f"[FAIL] Shot {shot['index']}: Expected {expected}, got {result['transition_type']}")
            return False

    print("[PASS] Transitions correct for single-scene story (first: within_scene, last: circular)")

    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("MULTI-SCENE THENVSNOW IMPLEMENTATION TEST")
    print("=" * 80)

    try:
        # Test 1: Shot generation
        shots = test_shot_generation()
        if not shots:
            print("\n[FAIL] Shot generation FAILED")
            return False

        print("\n[PASS] Shot generation PASSED")

        # Test 2: Departure transitions
        if not test_departure_transitions(shots):
            print("\n[FAIL] Departure transitions FAILED")
            return False

        print("\n[PASS] Departure transitions PASSED")

        # Test 3: Backward compatibility
        if not test_backward_compatibility():
            print("\n[FAIL] Backward compatibility FAILED")
            return False

        print("\n[PASS] Backward compatibility PASSED")

        # Final summary
        print("\n" + "=" * 80)
        print("ALL TESTS PASSED [SUCCESS]")
        print("=" * 80)
        print("\nSummary:")
        print("  - Shot generation with multi-scene structure: [PASS]")
        print("  - Departure video transitions (within/cross/circular): [PASS]")
        print("  - Backward compatibility with single-scene stories: [PASS]")
        print("\nImplementation is working correctly!")

        return True

    except Exception as e:
        print(f"\n[FAIL] TEST FAILED WITH ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
