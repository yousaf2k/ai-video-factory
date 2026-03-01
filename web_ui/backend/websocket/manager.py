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

    def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_connections:
            if websocket in self.active_connections[session_id]:
                self.active_connections[session_id].remove(websocket)
                if not self.active_connections[session_id]:
                    del self.active_connections[session_id]
        logger.info(f"WebSocket disconnected from session {session_id}")

    async def broadcast_to_session(self, session_id: str, message: dict):
        """Send a message to all connected clients for a specific session"""
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

# Global instance
manager = ConnectionManager()
