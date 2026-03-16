"""
Queue Service - Centralized queue management for all generation tasks
"""
import asyncio
import json
import os
import threading
from datetime import datetime
from typing import List, Optional, Dict, Set
from pathlib import Path
import uuid
import logging

from web_ui.backend.models.queue import (
    QueueItem,
    QueueStatistics,
    QueueItemStatus,
    GenerationType,
    ReorderRequest,
    PriorityUpdateRequest
)
from web_ui.backend.websocket.manager import manager

logger = logging.getLogger(__name__)


class QueueService:
    """
    Centralized queue management service.

    Replaces GenerationService's in-memory queue with a persistent,
    cross-project queue system with real-time updates.
    """

    def __init__(self, persistence_path: str = None):
        """
        Initialize QueueService.

        Args:
            persistence_path: Path to JSON file for queue persistence
        """
        # Core queue state
        self._queue: List[QueueItem] = []
        self._queue_lock = threading.RLock()
        self._is_paused = False
        self._pause_lock = threading.Lock()

        # Persistence
        if persistence_path is None:
            # Default to queue_state.json in output directory
            import config
            output_dir = getattr(config, 'ABS_OUTPUT_DIR', None)
            if output_dir:
                persistence_path = os.path.join(output_dir, 'queue_state.json')
            else:
                persistence_path = 'queue_state.json'

        self._persistence_path = persistence_path
        self._persistence_lock = threading.Lock()

        # Load persisted state on startup
        self._load_queue()

        # Start persistence task (save every 30 seconds)
        self._start_persistence_task()

        logger.info(f"QueueService initialized with {len(self._queue)} items")

    def _load_queue(self):
        """Load queue state from persistence file"""
        print(f"[DEBUG] QueueService loading from: {self._persistence_path}")
        try:
            if os.path.exists(self._persistence_path):
                with open(self._persistence_path, 'r') as f:
                    data = json.load(f)

                # Restore queue items
                queue_data = data.get('queue', [])
                self._queue = [QueueItem(**item) for item in queue_data]

                # Restore pause state
                self._is_paused = data.get('is_paused', False)

                # Clean up completed/cancelled/failed items on startup
                # (keep them for statistics but don't reprocess)
                logger.info(f"Loaded {len(self._queue)} items from {self._persistence_path}")
            else:
                logger.info("No existing queue state found, starting fresh")
        except Exception as e:
            logger.error(f"Error loading queue state: {e}")
            self._queue = []

    def _save_queue(self):
        """Save queue state to persistence file"""
        try:
            with self._persistence_lock:
                # Convert QueueItems to dicts for JSON serialization
                queue_data = [item.model_dump(mode='json') for item in self._queue]

                data = {
                    'queue': queue_data,
                    'is_paused': self._is_paused,
                    'saved_at': datetime.utcnow().isoformat()
                }

                # Write to temp file first, then rename (atomic write)
                temp_path = self._persistence_path + '.tmp'
                with open(temp_path, 'w') as f:
                    json.dump(data, f, indent=2, default=str)

                # Rename temp to actual file
                if os.path.exists(temp_path):
                    if os.path.exists(self._persistence_path):
                        os.remove(self._persistence_path)
                    os.rename(temp_path, self._persistence_path)

                logger.debug(f"Saved {len(self._queue)} items to {self._persistence_path}")
        except Exception as e:
            logger.error(f"Error saving queue state: {e}")

    def _start_persistence_task(self):
        """Start background task to persist queue periodically"""
        def persistence_loop():
            import time
            while True:
                try:
                    time.sleep(30)  # Save every 30 seconds
                    self._save_queue()
                except Exception as e:
                    logger.error(f"Error in persistence loop: {e}")

        thread = threading.Thread(target=persistence_loop, daemon=True)
        thread.start()
        logger.info("Started queue persistence task")

    def add_items(self, items: List[QueueItem]) -> List[QueueItem]:
        """
        Add items to queue, auto-sort by priority.

        Args:
            items: List of QueueItems to add

        Returns:
            List of added items with assigned item_ids
        """
        with self._queue_lock:
            # Find current max priority to place new items at the bottom
            max_priority = 0
            if self._queue:
                max_priority = max(item.priority for item in self._queue)

            # Generate item_ids if not provided and set priorities
            for i, item in enumerate(items):
                if not item.item_id:
                    item.item_id = f"queue_{uuid.uuid4().hex[:8]}"
                
                # Assign priority sequentially from max_priority
                item.priority = max_priority + (i + 1) * 10

            # Add to queue and sort by priority
            self._queue.extend(items)
            self._sort_queue()

            # Broadcast additions
            for item in items:
                manager.broadcast_sync('global', {
                    'type': 'queue.item_added',
                    'data': item.model_dump(mode='json')
                })

            # Broadcast statistics update
            self._broadcast_statistics()
            # self._save_queue()

            logger.info(f"Added {len(items)} items to queue")
            return items

    def remove_item(self, item_id: str) -> bool:
        """
        Remove specific item from queue.

        Args:
            item_id: Item identifier

        Returns:
            True if item was found and removed
        """
        with self._queue_lock:
            for i, item in enumerate(self._queue):
                if item.item_id == item_id:
                    removed = self._queue.pop(i)
                    manager.broadcast_sync('global', {
                        'type': 'queue.item_removed',
                        'data': {'item_id': item_id}
                    })
                    self._broadcast_statistics()
                    # self._save_queue()
                    logger.info(f"Removed item {item_id} from queue")
                    return True
            return False

    def update_priority(self, item_id: str, request: PriorityUpdateRequest) -> bool:
        """
        Update item priority and re-sort queue.

        Args:
            item_id: Item identifier
            request: Priority update request

        Returns:
            True if item was found and updated
        """
        with self._queue_lock:
            for item in self._queue:
                if item.item_id == item_id:
                    item.priority = request.priority
                    self._sort_queue()

                    manager.broadcast_sync('global', {
                        'type': 'queue.item_updated',
                        'data': {
                            'item_id': item_id,
                            'priority': request.priority
                        }
                    })
                    # self._save_queue()
                    logger.info(f"Updated priority for item {item_id} to {request.priority}")
                    return True
            return False

    def reorder_items(self, request: ReorderRequest) -> bool:
        """
        Reorder queue based on item_id sequence (drag-and-drop).

        Args:
            request: Reorder request with ordered item_ids

        Returns:
            True if reorder was successful
        """
        with self._queue_lock:
            # Create mapping of item_id to item
            item_map = {item.item_id: item for item in self._queue}

            # Rebuild queue in requested order
            new_queue = []
            for item_id in request.item_ids:
                if item_id in item_map:
                    new_queue.append(item_map[item_id])
                    del item_map[item_id]

            # Add any remaining items (that weren't in the reorder list)
            new_queue.extend(list(item_map.values()))

            # Update priority based on new position
            for i, item in enumerate(new_queue):
                item.priority = i * 10

            self._queue = new_queue

            manager.broadcast_sync('global', {
                'type': 'queue.reordered',
                'data': {'item_ids': request.item_ids}
            })
            # self._save_queue()
            logger.info(f"Reordered queue with {len(request.item_ids)} items")
            return True

    def get_queue(self, project_id: str = None, status: QueueItemStatus = None) -> List[QueueItem]:
        """
        Retrieve queue items, optionally filtered.

        Args:
            project_id: Optional project filter
            status: Optional status filter

        Returns:
            List of queue items
        """
        with self._queue_lock:
            items = self._queue.copy()

            if project_id:
                items = [item for item in items if item.project_id == project_id]

            if status:
                items = [item for item in items if item.status == status]

            return items

    def get_item(self, item_id: str) -> Optional[QueueItem]:
        """
        Get specific item by ID.

        Args:
            item_id: Item identifier

        Returns:
            QueueItem or None
        """
        with self._queue_lock:
            for item in self._queue:
                if item.item_id == item_id:
                    return item
            return None

    def mark_active(self, item_id: str) -> bool:
        """
        Mark item as active (started processing).

        Args:
            item_id: Item identifier

        Returns:
            True if item was found and updated
        """
        with self._queue_lock:
            for item in self._queue:
                if item.item_id == item_id and item.status == QueueItemStatus.QUEUED:
                    item.status = QueueItemStatus.ACTIVE
                    item.started_at = datetime.utcnow()
                    # self._save_queue()

                    manager.broadcast_sync('global', {
                        'type': 'queue.item_started',
                        'data': item.model_dump(mode='json')
                    })
                    self._broadcast_statistics()
                    logger.info(f"Marked item {item_id} as active")
                    return True
            return False

    def mark_completed(self, item_id: str, progress: int = 100) -> bool:
        """
        Mark item as completed.

        Args:
            item_id: Item identifier
            progress: Final progress value (default 100)

        Returns:
            True if item was found and updated
        """
        with self._queue_lock:
            for item in self._queue:
                if item.item_id == item_id:
                    item.status = QueueItemStatus.COMPLETED
                    item.completed_at = datetime.utcnow()
                    item.progress = progress
                    # self._save_queue()

                    manager.broadcast_sync('global', {
                        'type': 'queue.item_completed',
                        'data': item.model_dump(mode='json')
                    })
                    self._broadcast_statistics()
                    logger.info(f"Marked item {item_id} as completed")
                    return True
            return False

    def mark_cancelled(self, item_id: str) -> bool:
        """
        Mark item as cancelled.

        Args:
            item_id: Item identifier

        Returns:
            True if item was found and updated
        """
        with self._queue_lock:
            for item in self._queue:
                if item.item_id == item_id:
                    item.status = QueueItemStatus.CANCELLED
                    item.completed_at = datetime.utcnow()

                    manager.broadcast_sync('global', {
                        'type': 'queue.item_cancelled',
                        'data': item.model_dump(mode='json')
                    })
                    self._broadcast_statistics()
                    logger.info(f"Marked item {item_id} as cancelled")
                    return True
            return False

    def mark_paused(self, item_id: str) -> bool:
        """
        Mark item as paused.

        Args:
            item_id: Item identifier

        Returns:
            True if item was found and updated
        """
        with self._queue_lock:
            for item in self._queue:
                if item.item_id == item_id:
                    item.status = QueueItemStatus.PAUSED

                    manager.broadcast_sync('global', {
                        'type': 'queue.item_paused',
                        'data': item.model_dump(mode='json')
                    })
                    self._broadcast_statistics()
                    logger.info(f"Marked item {item_id} as paused")
                    return True
            return False

    def mark_failed(self, item_id: str, error_message: str) -> bool:
        """
        Mark item as failed.

        Args:
            item_id: Item identifier
            error_message: Error description

        Returns:
            True if item was found and updated
        """
        with self._queue_lock:
            for item in self._queue:
                if item.item_id == item_id:
                    item.status = QueueItemStatus.FAILED
                    item.completed_at = datetime.utcnow()
                    item.error_message = error_message

                    manager.broadcast_sync('global', {
                        'type': 'queue.item_failed',
                        'data': item.model_dump(mode='json')
                    })
                    self._broadcast_statistics()
                    logger.warning(f"Marked item {item_id} as failed: {error_message}")
                    return True
            return False

    def update_progress(self, item_id: str, progress: int) -> bool:
        """
        Update progress for active item.

        Args:
            item_id: Item identifier
            progress: Progress percentage (0-100)

        Returns:
            True if item was found and updated
        """
        with self._queue_lock:
            for item in self._queue:
                if item.item_id == item_id and item.status == QueueItemStatus.ACTIVE:
                    item.progress = progress

                    manager.broadcast_sync('global', {
                        'type': 'queue.item_progress',
                        'data': {
                            'item_id': item_id,
                            'progress': progress
                        }
                    })
                    return True
            return False

    def requeue_item(self, item_id: str) -> bool:
        """
        Requeue a failed or cancelled item.

        Args:
            item_id: Item identifier

        Returns:
            True if item was found and requeued
        """
        with self._queue_lock:
            for item in self._queue:
                if item.item_id == item_id and item.status in [QueueItemStatus.FAILED, QueueItemStatus.CANCELLED]:
                    item.status = QueueItemStatus.QUEUED
                    item.progress = 0
                    item.error_message = None
                    item.started_at = None
                    item.completed_at = None

                    manager.broadcast_sync('global', {
                        'type': 'queue.item_requeued',
                        'data': item.model_dump(mode='json')
                    })
                    self._broadcast_statistics()
                    logger.info(f"Requeued item {item_id}")
                    return True
            return False

    def resume_item(self, item_id: str) -> bool:
        """
        Resume a paused item.

        Args:
            item_id: Item identifier

        Returns:
            True if item was found and resumed
        """
        with self._queue_lock:
            for item in self._queue:
                if item.item_id == item_id and item.status == QueueItemStatus.PAUSED:
                    item.status = QueueItemStatus.QUEUED

                    manager.broadcast_sync('global', {
                        'type': 'queue.item_resumed',
                        'data': item.model_dump(mode='json')
                    })
                    self._broadcast_statistics()
                    logger.info(f"Resumed item {item_id}")
                    return True
            return False

    def pause_queue(self) -> bool:
        """
        Pause queue processing (no new items will start).

        Returns:
            True if pause state was changed
        """
        with self._pause_lock:
            if not self._is_paused:
                self._is_paused = True
                manager.broadcast_sync('global', {
                    'type': 'queue.paused',
                    'data': {'is_paused': True}
                })
                logger.info("Queue paused")
                return True
            return False

    def resume_queue(self) -> bool:
        """
        Resume queue processing.

        Returns:
            True if pause state was changed
        """
        with self._pause_lock:
            if self._is_paused:
                self._is_paused = False
                manager.broadcast_sync('global', {
                    'type': 'queue.resumed',
                    'data': {'is_paused': False}
                })
                logger.info("Queue resumed")
                return True
            return False

    def is_paused(self) -> bool:
        """Check if queue is paused"""
        with self._pause_lock:
            return self._is_paused

    def clear_completed(self) -> int:
        """
        Remove all completed items from queue.

        Returns:
            Number of items removed
        """
        with self._queue_lock:
            original_count = len(self._queue)
            self._queue = [
                item for item in self._queue
                if item.status != QueueItemStatus.COMPLETED
            ]
            removed_count = original_count - len(self._queue)

            if removed_count > 0:
                manager.broadcast_sync('global', {
                    'type': 'queue.cleared_completed',
                    'data': {'count': removed_count}
                })
                self._broadcast_statistics()
                logger.info(f"Cleared {removed_count} completed items from queue")

            return removed_count

    def clear_failed(self) -> int:
        """
        Remove all failed items from queue.

        Returns:
            Number of items removed
        """
        with self._queue_lock:
            original_count = len(self._queue)
            self._queue = [
                item for item in self._queue
                if item.status != QueueItemStatus.FAILED
            ]
            removed_count = original_count - len(self._queue)

            if removed_count > 0:
                manager.broadcast_sync('global', {
                    'type': 'queue.cleared_failed',
                    'data': {'count': removed_count}
                })
                self._broadcast_statistics()
                logger.info(f"Cleared {removed_count} failed items from queue")

            return removed_count

    def clear_cancelled(self) -> int:
        """
        Remove all cancelled items from queue.

        Returns:
            Number of items removed
        """
        with self._queue_lock:
            original_count = len(self._queue)
            self._queue = [
                item for item in self._queue
                if item.status != QueueItemStatus.CANCELLED
            ]
            removed_count = original_count - len(self._queue)

            if removed_count > 0:
                manager.broadcast_sync('global', {
                    'type': 'queue.cleared_cancelled',
                    'data': {'count': removed_count}
                })
                self._broadcast_statistics()
                logger.info(f"Cleared {removed_count} cancelled items from queue")

            return removed_count

    def get_statistics(self) -> QueueStatistics:
        """
        Get aggregated queue statistics.

        Returns:
            QueueStatistics object
        """
        with self._queue_lock:
            # Count by status
            stats = {
                'total': len(self._queue),
                'queued': 0,
                'active': 0,
                'completed': 0,
                'cancelled': 0,
                'failed': 0,
                'paused': 0
            }

            # Count by type
            type_counts = {
                'images': 0,
                'videos': 0,
                'flfi2v': 0,
                'narrations': 0,
                'backgrounds': 0
            }

            # Track unique projects
            projects: Set[str] = set()

            for item in self._queue:
                # Status counts
                stats[item.status.value] += 1

                # Type counts
                if item.generation_type in [GenerationType.IMAGE, GenerationType.THEN_IMAGE, GenerationType.NOW_IMAGE]:
                    type_counts['images'] += 1
                elif item.generation_type in [GenerationType.VIDEO, GenerationType.MEETING_VIDEO, GenerationType.DEPARTURE_VIDEO]:
                    type_counts['videos'] += 1
                elif item.generation_type == GenerationType.NARRATION:
                    type_counts['narrations'] += 1
                elif item.generation_type == GenerationType.BACKGROUND:
                    type_counts['backgrounds'] += 1

                # FLFI2V count
                if item.is_flfi2v:
                    type_counts['flfi2v'] += 1

                # Unique projects
                projects.add(item.project_id)

            stats.update(type_counts)
            stats['total_projects'] = len(projects)

            return QueueStatistics(**stats)

    def _sort_queue(self):
        """Sort queue by priority (lower first), then by creation time"""
        self._queue.sort(key=lambda item: (item.priority, item.created_at))

    def _broadcast_statistics(self):
        """Broadcast updated statistics via WebSocket"""
        stats = self.get_statistics()
        manager.broadcast_sync('global', {
            'type': 'queue.statistics_updated',
            'data': stats.model_dump(mode='json')
        })


# Global singleton instance
_queue_service: Optional[QueueService] = None
_queue_service_lock = threading.Lock()


def get_queue_service() -> QueueService:
    """Get global QueueService instance"""
    global _queue_service
    with _queue_service_lock:
        if _queue_service is None:
            _queue_service = QueueService()
        return _queue_service
