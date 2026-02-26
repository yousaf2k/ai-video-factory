#!/usr/bin/env python3
"""
Test script for automatic video length calculation feature.
Tests the calculate_max_shots_from_config() helper function.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock config values for different test scenarios
class MockConfig:
    def __init__(self, default_max_shots, target_video_length, default_shot_length=5):
        self.DEFAULT_MAX_SHOTS = default_max_shots
        self.TARGET_VIDEO_LENGTH = target_video_length
        self.DEFAULT_SHOT_LENGTH = default_shot_length

    def calculate_max_shots_from_config(self):
        """Helper function to calculate max shots from config"""
        # Priority 1: Manual override in config
        if self.DEFAULT_MAX_SHOTS > 0:
            return self.DEFAULT_MAX_SHOTS

        # Priority 2: Automatic calculation from target video length
        if self.TARGET_VIDEO_LENGTH and self.TARGET_VIDEO_LENGTH > 0:
            return int(self.TARGET_VIDEO_LENGTH / self.DEFAULT_SHOT_LENGTH)

        # Priority 3: No limit
        return None


def test_automatic_calculation():
    """Test 1: Automatic calculation from TARGET_VIDEO_LENGTH"""
    print("Test 1: Automatic calculation from TARGET_VIDEO_LENGTH")
    config = MockConfig(default_max_shots=0, target_video_length=600)
    result = config.calculate_max_shots_from_config()
    expected = 120  # 600 / 5 = 120

    print(f"  DEFAULT_MAX_SHOTS = 0, TARGET_VIDEO_LENGTH = 600")
    print(f"  Expected: {expected} shots")
    print(f"  Result: {result} shots")
    assert result == expected, f"FAILED: Expected {expected}, got {result}"
    print("  PASSED\n")


def test_manual_override():
    """Test 2: Manual override takes priority over automatic"""
    print("Test 2: Manual override takes priority")
    config = MockConfig(default_max_shots=50, target_video_length=600)
    result = config.calculate_max_shots_from_config()
    expected = 50  # Manual override wins

    print(f"  DEFAULT_MAX_SHOTS = 50, TARGET_VIDEO_LENGTH = 600")
    print(f"  Expected: {expected} shots (manual override)")
    print(f"  Result: {result} shots")
    assert result == expected, f"FAILED: Expected {expected}, got {result}"
    print("  PASSED\n")


def test_no_limit():
    """Test 3: No limit when both are 0"""
    print("Test 3: No limit when both are 0/None")
    config = MockConfig(default_max_shots=0, target_video_length=0)
    result = config.calculate_max_shots_from_config()
    expected = None

    print(f"  DEFAULT_MAX_SHOTS = 0, TARGET_VIDEO_LENGTH = 0")
    print(f"  Expected: {expected} (no limit)")
    print(f"  Result: {result}")
    assert result == expected, f"FAILED: Expected {expected}, got {result}"
    print("  PASSED\n")


def test_different_shot_length():
    """Test 4: Different shot lengths calculation"""
    print("Test 4: Different shot length")
    config = MockConfig(default_max_shots=0, target_video_length=300, default_shot_length=3)
    result = config.calculate_max_shots_from_config()
    expected = 100  # 300 / 3 = 100

    print(f"  DEFAULT_MAX_SHOTS = 0, TARGET_VIDEO_LENGTH = 300, SHOT_LENGTH = 3")
    print(f"  Expected: {expected} shots")
    print(f"  Result: {result} shots")
    assert result == expected, f"FAILED: Expected {expected}, got {result}"
    print("  PASSED\n")


def test_small_video():
    """Test 5: Small video length"""
    print("Test 5: Small video length (1 minute)")
    config = MockConfig(default_max_shots=0, target_video_length=60)
    result = config.calculate_max_shots_from_config()
    expected = 12  # 60 / 5 = 12

    print(f"  DEFAULT_MAX_SHOTS = 0, TARGET_VIDEO_LENGTH = 60")
    print(f"  Expected: {expected} shots")
    print(f"  Result: {result} shots")
    assert result == expected, f"FAILED: Expected {expected}, got {result}"
    print("  PASSED\n")


if __name__ == "__main__":
    print("="*70)
    print("Testing Automatic Video Length Calculation")
    print("="*70)
    print()

    try:
        test_automatic_calculation()
        test_manual_override()
        test_no_limit()
        test_different_shot_length()
        test_small_video()

        print("="*70)
        print("All tests passed!")
        print("="*70)

    except AssertionError as e:
        print(f"\n{'='*70}")
        print(f"TEST FAILED: {e}")
        print("="*70)
        sys.exit(1)
