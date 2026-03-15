from typing import List, Dict, Set
from fastapi import WebSocket
import json
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Manages WebSocket connections for real-time progress updates.
    Organizes connections by session_id.
    """
    def __init__(self):
        # session_id -> List[WebSocket]
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # session_id -> Dict[shot_index, dict(message)]
        self.generation_state: Dict[str, Dict[int, dict]] = {}
        self.loop = None

    def set_loop(self, loop):
        """Set the event loop reference (call from startup)"""
        self.loop = loop
        logger.info("ConnectionManager event loop captured")

    async def connect(self, websocket: WebSocket, session_id: str):
        import asyncio
        if self.loop is None:
             self.loop = asyncio.get_running_loop()
             
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
        logger.info(f"WebSocket connected for session {session_id}. Total connections: {len(self.active_connections[session_id])}")

        # Send any currently cached generating states immediately on connect
        if session_id in self.generation_state:
            for shot_index, message in self.generation_state[session_id].items():
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send cached WebSocket message: {e}")

    def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_connections:
            if websocket in self.active_connections[session_id]:
                self.active_connections[session_id].remove(websocket)
                if not self.active_connections[session_id]:
                    del self.active_connections[session_id]
        logger.info(f"WebSocket disconnected from session {session_id}")

    def _update_cache(self, session_id: str, message: dict):
        """Update the generation state cache with the latest message"""
        msg_type = message.get("type")
        shot_index = message.get("shot_index")
        
        if shot_index is None:
            return

        if msg_type == "progress":
            if session_id not in self.generation_state:
                self.generation_state[session_id] = {}
            self.generation_state[session_id][shot_index] = message
        elif msg_type in ["completed", "cancelled"]:
            if session_id in self.generation_state and shot_index in self.generation_state[session_id]:
                del self.generation_state[session_id][shot_index]
                if not self.generation_state[session_id]:
                    del self.generation_state[session_id]

    async def broadcast_to_session(self, session_id: str, message: dict):
        """Send a message to all connected clients for a specific session"""
        self._update_cache(session_id, message)
        
        if session_id not in self.active_connections:
            return
        disconnected = []
        connections = list(self.active_connections[session_id])
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send WebSocket message: {e}")
                disconnected.append(connection)
        
        # Clean up dead connections
        for conn in disconnected:
            self.disconnect(conn, session_id)

    def broadcast_sync(self, session_id: str, message: dict):
        """Synchronous version of broadcast_to_session for use in threads"""
        import asyncio

        self._update_cache(session_id, message)

        # Special handling for 'global' session (queue updates)
        if session_id == 'global':
            if self.loop and self.loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    self._broadcast_to_all_clients(message), self.loop
                )
                future.add_done_callback(
                    lambda f: logger.warning(f"Broadcast error: {f.exception()}") if f.exception() else None
                )
            return

        if session_id not in self.active_connections:
            return
        if self.loop and self.loop.is_running():
            future = asyncio.run_coroutine_threadsafe(
                self.broadcast_to_session(session_id, message), self.loop
            )
            # Don't block, but log errors
            future.add_done_callback(
                lambda f: logger.warning(f"Broadcast error: {f.exception()}") if f.exception() else None
            )
        else:
            logger.warning(f"Cannot broadcast: no event loop available (loop={self.loop})")

    async def _broadcast_to_all_clients(self, message: dict):
        """Send a message to all connected clients regardless of session"""
        all_connections = []
        for session_conns in self.active_connections.values():
            all_connections.extend(session_conns)

        disconnected = []
        for connection in all_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send global WebSocket message: {e}")
                disconnected.append(connection)

        # Clean up dead connections across all sessions
        for conn in disconnected:
            for session_id, conns in list(self.active_connections.items()):
                if conn in conns:
                    self.disconnect(conn, session_id)
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
