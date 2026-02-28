"""
FastAPI Web UI for AI Video Factory
"""
import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging

# Add parent directory to path to import core modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import config
from web_ui.backend.api import sessions, stories

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


# Mount static files for serving assets (images, videos)
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting AI Video Factory API")
    logger.info(f"CORS origins: {config.WEB_UI_CORS_ORIGINS}")

    # Ensure output directories exist
    os.makedirs("output/sessions", exist_ok=True)

    # Mount static files for each existing session
    # This allows accessing images/videos via HTTP
    sessions_dir = "output/sessions"
    if os.path.exists(sessions_dir):
        for session_id in os.listdir(sessions_dir):
            session_path = os.path.join(sessions_dir, session_id)
            if os.path.isdir(session_path):
                # Mount images directory
                images_dir = os.path.join(session_path, "images")
                if os.path.exists(images_dir):
                    mount_path = f"/api/sessions/{session_id}/images"
                    app.mount(mount_path, StaticFiles(directory=images_dir), name=f"{session_id}_images")
                    logger.info(f"Mounted {mount_path} -> {images_dir}")

                # Mount videos directory
                videos_dir = os.path.join(session_path, "videos")
                if os.path.exists(videos_dir):
                    mount_path = f"/api/sessions/{session_id}/videos"
                    app.mount(mount_path, StaticFiles(directory=videos_dir), name=f"{session_id}_videos")
                    logger.info(f"Mounted {mount_path} -> {videos_dir}")


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
