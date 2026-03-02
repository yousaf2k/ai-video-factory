"""
Retry Tracker Module - Tracks failed image generations and retry statistics

This module provides classes to track failed image generations at the shot+variation level,
managing retry attempts and providing comprehensive summaries.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
from core.logger_config import get_logger

logger = get_logger(__name__)


class RetryStatus(Enum):
    """Status of a retry attempt"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED_PERMANENTLY = "failed_permanently"


@dataclass
class FailedVariation:
    """Represents a failed image variation that needs retry"""
    shot_index: int
    variation_index: int
    prompt: str
    attempts_made: int = 1
    status: RetryStatus = RetryStatus.PENDING
    last_error: str = ""

    def __hash__(self):
        """Make hashable for set operations"""
        return hash((self.shot_index, self.variation_index))

    def __eq__(self, other):
        """Check equality based on shot and variation index"""
        if not isinstance(other, FailedVariation):
            return False
        return (self.shot_index == other.shot_index and
                self.variation_index == other.variation_index)


@dataclass
class RetrySummary:
    """Summary statistics for retry attempts"""
    total_variations_attempted: int = 0
    total_success_initial: int = 0
    total_failed_initial: int = 0
    total_success_after_retry: int = 0
    total_failed_permanently: int = 0


class RetryTracker:
    """
    Tracks failed image generations and manages retry logic.

    Usage:
        tracker = RetryTracker(max_retries=3)
        tracker.record_failure(shot_idx=1, variation_idx=0, prompt="...")
        # Later...
        pending = tracker.get_pending_retries()
        for failed_var in pending:
            # Retry generation
            if success:
                tracker.mark_success(failed_var.shot_index, failed_var.variation_index)
    """

    def __init__(self, max_retries: int = 3):
        """
        Initialize the retry tracker.

        Args:
            max_retries: Maximum number of total attempts (including initial)
        """
        self.max_retries = max_retries
        self.failed_variations: List[FailedVariation] = []
        self.summary = RetrySummary()

    def record_failure(self, shot_index: int, variation_index: int, prompt: str, error: str = ""):
        """
        Record a failed variation for potential retry.

        Args:
            shot_index: Shot index (1-based)
            variation_index: Variation index (0-based)
            prompt: The image prompt that failed
            error: Optional error message
        """
        # Check if this variation is already tracked
        for existing in self.failed_variations:
            if (existing.shot_index == shot_index and
                existing.variation_index == variation_index):
                # Already tracked, don't duplicate
                return

        failed_var = FailedVariation(
            shot_index=shot_index,
            variation_index=variation_index,
            prompt=prompt,
            attempts_made=1,
            status=RetryStatus.PENDING,
            last_error=error
        )
        self.failed_variations.append(failed_var)
        logger.debug(f"Recorded failure: shot {shot_index}, variation {variation_index}")

    def record_success(self, shot_index: int, variation_index: int):
        """
        Record a successful generation (for summary statistics).

        Args:
            shot_index: Shot index (1-based)
            variation_index: Variation index (0-based)
        """
        self.summary.total_success_initial += 1
        logger.debug(f"Recorded success: shot {shot_index}, variation {variation_index}")

    def increment_attempts(self, shot_index: int, variation_index: int) -> bool:
        """
        Increment the attempt count for a failed variation.

        Args:
            shot_index: Shot index (1-based)
            variation_index: Variation index (0-based)

        Returns:
            True if should retry (attempts < max_retries), False otherwise
        """
        for failed_var in self.failed_variations:
            if (failed_var.shot_index == shot_index and
                failed_var.variation_index == variation_index):
                failed_var.attempts_made += 1
                if failed_var.attempts_made >= self.max_retries:
                    failed_var.status = RetryStatus.FAILED_PERMANENTLY
                    logger.debug(f"Marked as permanent failure: shot {shot_index}, variation {variation_index} after {failed_var.attempts_made} attempts")
                    return False
                return True
        return False

    def mark_success(self, shot_index: int, variation_index: int, image_path: str = ""):
        """
        Mark a previously failed variation as successful after retry.

        Args:
            shot_index: Shot index (1-based)
            variation_index: Variation index (0-based)
            image_path: Path to the successfully generated image
        """
        for i, failed_var in enumerate(self.failed_variations):
            if (failed_var.shot_index == shot_index and
                failed_var.variation_index == variation_index):
                failed_var.status = RetryStatus.SUCCESS
                self.summary.total_success_after_retry += 1
                logger.info(f"Retry succeeded: shot {shot_index}, variation {variation_index} -> {image_path}")
                return

    def mark_permanent_failure(self, shot_index: int, variation_index: int):
        """
        Mark a variation as permanently failed (exhausted all retries).

        Args:
            shot_index: Shot index (1-based)
            variation_index: Variation index (0-based)
        """
        for failed_var in self.failed_variations:
            if (failed_var.shot_index == shot_index and
                failed_var.variation_index == variation_index):
                failed_var.status = RetryStatus.FAILED_PERMANENTLY
                self.summary.total_failed_permanently += 1
                logger.warning(f"Permanent failure: shot {shot_index}, variation {variation_index} after {self.max_retries} attempts")

    def get_pending_retries(self) -> List[FailedVariation]:
        """
        Get list of variations that still need retry.

        Returns:
            List of FailedVariation objects with PENDING status
        """
        return [fv for fv in self.failed_variations if fv.status == RetryStatus.PENDING]

    def get_failed_variations(self) -> List[FailedVariation]:
        """
        Get all failed variations (including pending and permanent failures).

        Returns:
            List of all FailedVariation objects
        """
        return self.failed_variations.copy()

    def get_permanent_failures(self) -> List[FailedVariation]:
        """
        Get variations that permanently failed.

        Returns:
            List of FailedVariation objects with FAILED_PERMANENTLY status
        """
        return [fv for fv in self.failed_variations if fv.status == RetryStatus.FAILED_PERMANENTLY]

    def print_summary(self):
        """Print a comprehensive summary of retry statistics"""
        print("\n" + "=" * 66)
        print("IMAGE GENERATION RETRY SUMMARY")
        print("=" * 66)
        print(f"Total variations attempted: {self.summary.total_variations_attempted}")
        print(f"Initial success: {self.summary.total_success_initial}")
        print(f"Initial failures: {self.summary.total_failed_initial}")
        print(f"Success after retry: {self.summary.total_success_after_retry}")
        print(f"Permanent failures: {self.summary.total_failed_permanently}")
        print("=" * 66)

        # Calculate success rate
        total_success = self.summary.total_success_initial + self.summary.total_success_after_retry
        if self.summary.total_variations_attempted > 0:
            success_rate = (total_success / self.summary.total_variations_attempted) * 100
            print(f"Overall success rate: {success_rate:.1f}%")
            print("=" * 66)

        # Log to file as well
        logger.info(f"Retry Summary: {self.summary.total_success_initial + self.summary.total_success_after_retry}/{self.summary.total_variations_attempted} variations succeeded")
