"""
Queue API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from web_ui.backend.models.queue import (
    QueueItem,
    QueueStatistics,
    QueueItemStatus,
    ReorderRequest,
    PriorityUpdateRequest
)
from web_ui.backend.services.queue_service import get_queue_service

router = APIRouter(prefix="/api/queue", tags=["queue"])

# Get queue service instance
queue_service = get_queue_service()


@router.get("/items", response_model=List[QueueItem])
async def get_queue_items(
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    status: Optional[QueueItemStatus] = Query(None, description="Filter by status")
):
    """
    Get queue items, optionally filtered by session or status.

    Returns all items across all sessions by default.
    """
    try:
        items = queue_service.get_queue(session_id=session_id, status=status)
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_model=QueueStatistics)
async def get_queue_statistics():
    """
    Get aggregated queue statistics.
    """
    try:
        stats = queue_service.get_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/items", response_model=List[QueueItem])
async def add_queue_items(items: List[QueueItem]):
    """
    Add items to queue.

    Items will be auto-sorted by priority after adding.
    """
    try:
        added_items = queue_service.add_items(items)
        
        # Ensure queue processor is running
        try:
            from web_ui.backend.services.generation_service import get_generation_service
            get_generation_service()._ensure_queue_processor_started()
        except Exception as e:
            # Don't fail the request if it fails to start, but log it
            import logging
            logging.getLogger(__name__).warning(f"Failed to start queue processor: {e}")
            
        return added_items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/items/{item_id}")
async def remove_queue_item(item_id: str):
    """
    Remove specific item from queue.
    """
    try:
        success = queue_service.remove_item(item_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
        return {"message": "Item removed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/items/{item_id}/priority")
async def update_item_priority(item_id: str, request: PriorityUpdateRequest):
    """
    Update priority for a specific item.

    Lower priority value = higher priority (processed first).
    """
    try:
        success = queue_service.update_priority(item_id, request)
        if not success:
            raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
        return {"message": "Priority updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/items/reorder")
async def reorder_queue(request: ReorderRequest):
    """
    Reorder queue based on item_id sequence.

    Used for drag-and-drop reordering in the UI.
    Items will be assigned new priorities based on their position.
    """
    try:
        success = queue_service.reorder_items(request)
        if not success:
            raise HTTPException(status_code=400, detail="Reorder failed")
        return {"message": "Queue reordered successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/items/{item_id}/cancel")
async def cancel_queue_item(item_id: str):
    """
    Cancel a specific queue item.

    If the item is currently active, an interrupt will be sent to ComfyUI.
    """
    try:
        success = queue_service.mark_cancelled(item_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

        # If item is active, interrupt ComfyUI generation
        item = queue_service.get_item(item_id)
        if item and item.status == QueueItemStatus.ACTIVE:
            from core.comfy_client import interrupt_generation
            interrupt_generation()

        return {"message": "Item cancelled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pause")
async def pause_queue():
    """
    Pause queue processing.

    No new items will be started until queue is resumed.
    """
    try:
        changed = queue_service.pause_queue()
        if not changed:
            return {"message": "Queue is already paused", "is_paused": True}
        return {"message": "Queue paused successfully", "is_paused": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resume")
async def resume_queue():
    """
    Resume queue processing.
    """
    try:
        changed = queue_service.resume_queue()
        if not changed:
            return {"message": "Queue is not paused", "is_paused": False}
        return {"message": "Queue resumed successfully", "is_paused": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/completed")
async def clear_completed_items():
    """
    Remove all completed items from queue.
    """
    try:
        count = queue_service.clear_completed()
        return {"message": f"Cleared {count} completed items", "count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/failed")
async def clear_failed_items():
    """
    Remove all failed items from queue.
    """
    try:
        count = queue_service.clear_failed()
        return {"message": f"Cleared {count} failed items", "count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/cancelled")
async def clear_cancelled_items():
    """
    Remove all cancelled items from queue.
    """
    try:
        count = queue_service.clear_cancelled()
        return {"message": f"Cleared {count} cancelled items", "count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/paused")
async def is_queue_paused():
    """
    Check if queue is currently paused.
    """
    try:
        is_paused = queue_service.is_paused()
        return {"is_paused": is_paused}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
