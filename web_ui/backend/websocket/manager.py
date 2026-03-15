from typing import List, Dict, Set
from fastapi import WebSocket
import json
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Manages WebSocket connections for real-time progress updates.
    Organizes connections by project_id.
    """
    def __init__(self):
        # project_id -> List[WebSocket]
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # project_id -> Dict[shot_index, dict(message)]
        self.generation_state: Dict[str, Dict[int, dict]] = {}
        self.loop = None

    def set_loop(self, loop):
        """Set the event loop reference (call from startup)"""
        self.loop = loop
        logger.info("ConnectionManager event loop captured")

    async def connect(self, websocket: WebSocket, project_id: str):
        import asyncio
        if self.loop is None:
             self.loop = asyncio.get_running_loop()
             
        await websocket.accept()
        if project_id not in self.active_connections:
            self.active_connections[project_id] = []
        self.active_connections[project_id].append(websocket)
        logger.info(f"WebSocket connected for project {project_id}. Total connections: {len(self.active_connections[project_id])}")

        # Send any currently cached generating states immediately on connect
        if project_id in self.generation_state:
            for shot_index, message in self.generation_state[project_id].items():
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send cached WebSocket message: {e}")

    def disconnect(self, websocket: WebSocket, project_id: str):
        if project_id in self.active_connections:
            if websocket in self.active_connections[project_id]:
                self.active_connections[project_id].remove(websocket)
                if not self.active_connections[project_id]:
                    del self.active_connections[project_id]
        logger.info(f"WebSocket disconnected from project {project_id}")

    def _update_cache(self, project_id: str, message: dict):
        """Update the generation state cache with the latest message"""
        msg_type = message.get("type")
        shot_index = message.get("shot_index")
        
        if shot_index is None:
            return

        if msg_type == "progress":
            if project_id not in self.generation_state:
                self.generation_state[project_id] = {}
            self.generation_state[project_id][shot_index] = message
        elif msg_type in ["completed", "cancelled"]:
            if project_id in self.generation_state and shot_index in self.generation_state[project_id]:
                del self.generation_state[project_id][shot_index]
                if not self.generation_state[project_id]:
                    del self.generation_state[project_id]

    async def broadcast_to_project(self, project_id: str, message: dict):
        """Send a message to all connected clients for a specific project"""
        self._update_cache(project_id, message)
        
        if project_id not in self.active_connections:
            return
        disconnected = []
        connections = list(self.active_connections[project_id])
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send WebSocket message: {e}")
                disconnected.append(connection)
        
        # Clean up dead connections
        for conn in disconnected:
            self.disconnect(conn, project_id)

    def broadcast_sync(self, project_id: str, message: dict):
        """Synchronous version of broadcast_to_project for use in threads"""
        import asyncio

        self._update_cache(project_id, message)

        # Special handling for 'global' project (queue updates)
        if project_id == 'global':
            if self.loop and self.loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    self._broadcast_to_all_clients(message), self.loop
                )
                future.add_done_callback(
                    lambda f: logger.warning(f"Broadcast error: {f.exception()}") if f.exception() else None
                )
            return

        if project_id not in self.active_connections:
            return
        if self.loop and self.loop.is_running():
            future = asyncio.run_coroutine_threadsafe(
                self.broadcast_to_project(project_id, message), self.loop
            )
            # Don't block, but log errors
            future.add_done_callback(
                lambda f: logger.warning(f"Broadcast error: {f.exception()}") if f.exception() else None
            )
        else:
            logger.warning(f"Cannot broadcast: no event loop available (loop={self.loop})")

    async def _broadcast_to_all_clients(self, message: dict):
        """Send a message to all connected clients regardless of project"""
        all_connections = []
        for project_conns in self.active_connections.values():
            all_connections.extend(project_conns)

        disconnected = []
        for connection in all_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send global WebSocket message: {e}")
                disconnected.append(connection)

        # Clean up dead connections across all projects
        for conn in disconnected:
            for project_id, conns in list(self.active_connections.items()):
                if conn in conns:
                    self.disconnect(conn, project_id)
                    break

    # Queue-specific broadcast methods (convenience wrappers)
    def broadcast_queue_update(self, event_type: str, data: dict):
        """Broadcast queue state change to all clients"""
        self.broadcast_sync('global', {
            'type': event_type,
            'data': data
        })

    def broadcast_queue_item_progress(self, item_id: str, progress: int):
        """Update progress percentage for active item"""
        self.broadcast_queue_update('queue.item_progress', {
            'item_id': item_id,
            'progress': progress
        })

    def broadcast_queue_item_status(self, item_id: str, status: str):
        """Update item status (queued -> active -> completed)"""
        self.broadcast_queue_update(f'queue.item_{status}', {
            'item_id': item_id,
            'status': status
        })

    def broadcast_queue_statistics(self):
        """Broadcast updated statistics (called automatically by QueueService)"""
        # This is handled by QueueService._broadcast_statistics()
        # Kept here for API consistency
        pass

# Global instance
manager = ConnectionManager()
