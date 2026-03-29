"""
FastAPI Web UI for AI Video Factory
"""
import os
import sys
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging

# Add parent directory to path to import core modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import config

# Set WindowsProactorEventLoopPolicy for Windows to avoid NotImplementedError with Playwright subprocesses
if sys.platform == 'win32':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
from web_ui.backend.api import projects, stories, shots, config as config_api, queue
from web_ui.backend.websocket.manager import manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events for the FastAPI application"""
    # Startup logic
    import config
    import asyncio
    debug_file = config.resolve_path("startup_debug.txt")
    with open(debug_file, "w") as f: f.write("[DEBUG] Startup: lifespan triggered\n")
    print("[DEBUG] Startup: Lifespan triggered")
    print("[DEBUG] Startup: Initializing ConnectionManager")
    from web_ui.backend.websocket.manager import manager
    # Note: get_running_loop() is only valid within an active loop
    manager.set_loop(asyncio.get_running_loop())

    print("[DEBUG] Startup: Ensuring output directories exist")
    projects_dir = config.ABS_PROJECTS_DIR
    os.makedirs(projects_dir, exist_ok=True)
    
    print("[DEBUG] Startup: Importing get_generation_service")
    from web_ui.backend.services.generation_service import get_generation_service
    print("[DEBUG] Startup: Getting generation service instance")
    gen_service = get_generation_service()
    print("[DEBUG] Startup: Ensuring queue processor started")

    async def deferred_start():
        await asyncio.sleep(5)
        print("[DEBUG] Startup: 5s Deferral complete, starting processor task")
        gen_service._ensure_queue_processor_started()

    asyncio.create_task(deferred_start())
    print("[DEBUG] Startup: Scheduled deferred queue processor start")
    logger.info("Generation Queue Processor started via lifespan")
    
    with open(debug_file, "a") as f: f.write("[DEBUG] Startup: Completed lifespan startup\n")
    
    yield
    
    # Shutdown logic (optional)
    with open(debug_file, "a") as f: f.write("[DEBUG] Shutdown: lifespan completed\n")
    print("[DEBUG] Shutdown: Lifespan completed")

# Create FastAPI app
app = FastAPI(
    title="AI Video Factory API",
    description="Web API for AI Video Factory - Generate cinematic videos from text ideas",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
# Step 1: Add the standard CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.WEB_UI_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Step 2: Add the Private Network Access middleware (OUTERMOST)
# In Starlette/FastAPI, the last added middleware is the first to receive the request 
# and the last to receive the response. We need this to be outermost 
# to catch OPTIONS responses from CORSMiddleware.
@app.middleware("http")
async def add_private_network_access_header(request: Request, call_next):
    """
    Handle Chrome's Private Network Access (PNA) by adding the 
    Access-Control-Allow-Private-Network header to preflight and regular requests.
    """
    if request.method == "OPTIONS":
        response = await call_next(request)
        if "Access-Control-Request-Private-Network" in request.headers:
            response.headers["Access-Control-Allow-Private-Network"] = "true"
        return response
    
    response = await call_next(request)
    if "Access-Control-Request-Private-Network" in request.headers:
        response.headers["Access-Control-Allow-Private-Network"] = "true"
    return response

# Include routers
app.include_router(projects.router)
app.include_router(stories.router)
app.include_router(shots.router)
app.include_router(config_api.router)
app.include_router(queue.router)

@app.get("/")
async def root():
    """Root endpoint - API info"""
    print("[DEBUG] Root endpoint accessed")
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


@app.websocket("/api/ws/progress/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    """WebSocket endpoint for real-time progress updates"""
    await manager.connect(websocket, project_id)
    try:
        while True:
            # We don't expect messages from client, but handle ping/pong if needed
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, project_id)
    except Exception as e:
        logger.error(f"WebSocket error for project {project_id}: {e}")
        manager.disconnect(websocket, project_id)





def run_server(host: str = None, port: int = None):
    """Run the FastAPI server"""
    import uvicorn

    host = host or os.getenv("BACKEND_BIND_HOST") or config.BACKEND_BIND_HOST or config.WEB_UI_HOST
    port = port or config.BACKEND_PORT or config.WEB_UI_PORT

    logger.info(f"Starting server at http://{host}:{port}")
    logger.info(f"API documentation available at http://{host}:{port}/docs")

    print(f"[DEBUG] Uvicorn running with host={host}, port={port}")
    uvicorn.run(
        "web_ui.backend.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    run_server()
