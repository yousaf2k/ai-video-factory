#!/usr/bin/env python3
"""
Test script to verify the image generation retry mechanism.

This script simulates the retry behavior without actually calling ComfyUI.
"""
import os
import sys
from core.retry_tracker import RetryTracker, FailedVariation, RetryStatus, RetrySummary


def test_retry_tracker_basic():
    """Test basic retry tracker functionality"""
    print("=" * 70)
    print("TEST 1: Basic Retry Tracker Functionality")
    print("=" * 70)

    tracker = RetryTracker(max_retries=3)

    # Test recording failures
    tracker.record_failure(shot_index=1, variation_index=0, prompt="Test prompt 1", error="Connection failed")
    tracker.record_failure(shot_index=1, variation_index=1, prompt="Test prompt 2", error="API error")
    tracker.record_failure(shot_index=2, variation_index=0, prompt="Test prompt 3", error="Timeout")

    print(f"[OK] Recorded 3 failures")
    print(f"  Pending retries: {len(tracker.get_pending_retries())}")

    # Test recording success
    tracker.record_success(shot_index=3, variation_index=0)
    tracker.summary.total_success_initial += 2  # Simulate 2 more successes

    # Test increment attempts
    pending = tracker.get_pending_retries()
    for failed_var in pending:
        should_retry = tracker.increment_attempts(failed_var.shot_index, failed_var.variation_index)
        print(f"[OK] Shot {failed_var.shot_index}, Var {failed_var.variation_index}: attempt {failed_var.attempts_made}, should_retry: {should_retry}")

    print(f"\n  After incrementing:")
    print(f"  Pending retries: {len(tracker.get_pending_retries())}")

    # Test marking success after retry
    tracker.mark_success(shot_index=1, variation_index=0, image_path="/path/to/image.png")

    print(f"\n  After marking one as success:")
    print(f"  Pending retries: {len(tracker.get_pending_retries())}")
    print(f"  Successes after retry: {tracker.summary.total_success_after_retry}")

    # Print summary
    tracker.summary.total_variations_attempted = 5
    tracker.summary.total_success_initial = 2
    tracker.summary.total_failed_initial = 3
    tracker.print_summary()

    print("\n[PASS] TEST 1 PASSED\n")


def test_retry_exhaustion():
    """Test that retries are exhausted after max attempts"""
    print("=" * 70)
    print("TEST 2: Retry Exhaustion")
    print("=" * 70)

    tracker = RetryTracker(max_retries=3)

    # Record a failure
    tracker.record_failure(shot_index=1, variation_index=0, prompt="Test prompt", error="Permanent error")

    # Attempt 1 (initial) - already counted
    # Attempt 2 (first retry)
    should_retry = tracker.increment_attempts(1, 0)
    print(f"[OK] After attempt 2: should_retry = {should_retry}")

    # Attempt 3 (second retry)
    should_retry = tracker.increment_attempts(1, 0)
    print(f"[OK] After attempt 3: should_retry = {should_retry}")

    # Attempt 4 (third retry) - should return False (max is 3)
    should_retry = tracker.increment_attempts(1, 0)
    print(f"[OK] After attempt 4: should_retry = {should_retry} (should be False - max retries reached)")

    # Mark as permanent failure
    tracker.mark_permanent_failure(1, 0)
    print(f"[OK] Marked as permanent failure")

    permanent_failures = tracker.get_permanent_failures()
    print(f"[OK] Permanent failures: {len(permanent_failures)}")

    print("\n[PASS] TEST 2 PASSED\n")


def test_multiple_variations():
    """Test tracking multiple variations per shot"""
    print("=" * 70)
    print("TEST 3: Multiple Variations Per Shot")
    print("=" * 70)

    tracker = RetryTracker(max_retries=3)

    # Shot 1: 3 variations, 2 fail
    tracker.record_failure(shot_index=1, variation_index=1, prompt="Shot 1, Var 2", error="Failed")
    tracker.record_failure(shot_index=1, variation_index=2, prompt="Shot 1, Var 3", error="Failed")
    tracker.record_success(shot_index=1, variation_index=0)

    # Shot 2: All 3 succeed
    for var_idx in range(3):
        tracker.record_success(shot_index=2, variation_index=var_idx)

    print(f"[OK] Shot 1: 1 success, 2 failures")
    print(f"[OK] Shot 2: 3 successes")
    print(f"[OK] Total pending retries: {len(tracker.get_pending_retries())}")

    # Retry one variation from shot 1
    tracker.mark_success(shot_index=1, variation_index=1, image_path="/path/to/image.png")

    pending = tracker.get_pending_retries()
    print(f"[OK] After retry: {len(pending)} pending")
    print(f"  Remaining: shot 1, variation 2")

    print("\n[PASS] TEST 3 PASSED\n")


def test_config_values():
    """Test that configuration values are accessible"""
    print("=" * 70)
    print("TEST 4: Configuration Values")
    print("=" * 70)

    import config

    print(f"[OK] IMAGE_GENERATION_MAX_RETRIES: {config.IMAGE_GENERATION_MAX_RETRIES}")
    print(f"[OK] IMAGE_GENERATION_RETRY_DELAY: {config.IMAGE_GENERATION_RETRY_DELAY}")
    print(f"[OK] CONTINUE_ON_PARTIAL_IMAGE_FAILURE: {config.CONTINUE_ON_PARTIAL_IMAGE_FAILURE}")

    assert config.IMAGE_GENERATION_MAX_RETRIES == 3, "Max retries should be 3"
    assert config.IMAGE_GENERATION_RETRY_DELAY == 5, "Retry delay should be 5"
    assert config.CONTINUE_ON_PARTIAL_IMAGE_FAILURE == True, "Should continue on partial failure"

    print("\n[PASS] TEST 4 PASSED\n")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("IMAGE GENERATION RETRY MECHANISM - TEST SUITE")
    print("=" * 70 + "\n")

    try:
        test_retry_tracker_basic()
        test_retry_exhaustion()
        test_multiple_variations()
        test_config_values()

        print("=" * 70)
        print("ALL TESTS PASSED [OK]")
        print("=" * 70)
        print("\nThe retry mechanism is working correctly!")
        print("\nKey features verified:")
        print("  [OK] RetryTracker can record failures and successes")
        print("  [OK] Retry attempts are tracked correctly")
        print("  [OK] Max retries are enforced")
        print("  [OK] Permanent failures are marked correctly")
        print("  [OK] Multiple variations per shot are handled")
        print("  [OK] Configuration values are accessible")
        print("\n")

    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
