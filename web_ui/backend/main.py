"""
FastAPI Web UI for AI Video Factory
"""
import os
import sys
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging

# Add parent directory to path to import core modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import config
from web_ui.backend.api import sessions, stories, shots, config as config_api
from web_ui.backend.websocket.manager import manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="AI Video Factory API",
    description="Web API for AI Video Factory - Generate cinematic videos from text ideas",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.WEB_UI_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sessions.router)
app.include_router(stories.router)
app.include_router(shots.router)
app.include_router(config_api.router)


@app.get("/")
async def root():
    """Root endpoint - API info"""
    return {
        "name": "AI Video Factory API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "config": {
            "web_ui_enabled": config.WEB_UI_ENABLED,
            "llm_provider": config.LLM_PROVIDER,
            "image_generation_mode": config.IMAGE_GENERATION_MODE,
            "comfy_url": config.COMFY_URL
        }
    }


@app.websocket("/api/ws/progress/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time progress updates"""
    await manager.connect(websocket, session_id)
    try:
        while True:
            # We don't expect messages from client, but handle ping/pong if needed
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        manager.disconnect(websocket, session_id)



# Mount static files for serving assets (images, videos)
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    import asyncio
    manager.set_loop(asyncio.get_running_loop())
    logger.info("Starting AI Video Factory API")
    logger.info(f"CORS origins: {config.WEB_UI_CORS_ORIGINS}")

    # Ensure output directories exist
    sessions_dir = config.ABS_SESSIONS_DIR
    os.makedirs(sessions_dir, exist_ok=True)
    
    # Note: Sessions assets (images/videos) are now served dynamically 
    # via endpoints in sessions.py to support newly created sessions
    # without requiring a server restart.


def run_server(host: str = None, port: int = None):
    """Run the FastAPI server"""
    import uvicorn

    host = host or config.WEB_UI_HOST
    port = port or config.WEB_UI_PORT

    logger.info(f"Starting server at http://{host}:{port}")
    logger.info(f"API documentation available at http://{host}:{port}/docs")

    uvicorn.run(
        "web_ui.backend.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    run_server()
