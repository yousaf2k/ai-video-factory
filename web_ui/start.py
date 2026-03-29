"""
Start script for AI Video Factory Web UI
Launches both backend and frontend servers
"""
import os
import sys
import subprocess
import time
import threading
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import config


def ensure_base_directories():
    """Ensure all required base directories exist"""
    base_dirs = [
        getattr(config, 'ABS_OUTPUT_DIR', 'output'),
        getattr(config, 'LOG_DIR', 'logs'),
        os.path.join(getattr(config, 'ABS_OUTPUT_DIR', 'output'), "images"),
        os.path.join(getattr(config, 'ABS_OUTPUT_DIR', 'output'), "videos")
    ]
    
    for directory in base_dirs:
        if not os.path.exists(directory):
            print(f"Creating directory: {directory}")
            os.makedirs(directory, exist_ok=True)


def check_port_available(port):
    """Check if a port is available"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            # Bind to 0.0.0.0 (all interfaces) for common network accessibility 
            # while checking if the port is available
            s.bind(('0.0.0.0', port))
            return True
        except:
            return False


def start_backend():
    """Start the FastAPI backend server"""
    host = getattr(config, 'BACKEND_HOST', '127.0.0.1')
    bind_host = getattr(config, 'BACKEND_BIND_HOST', '0.0.0.0')
    port = getattr(config, 'BACKEND_PORT', 8000)
    print(f"Starting backend server at http://{host}:{port}")
    print(f"Listening on: {bind_host}:{port}")
    print(f"API docs: http://{host}:{port}/docs")

    backend_dir = Path(__file__).parent / "backend"
    # Pass bind host through env for uvicorn in main.py
    env = os.environ.copy()
    env["BACKEND_BIND_HOST"] = bind_host
    subprocess.run(
        [sys.executable, "main.py"],
        cwd=backend_dir,
        env=env
    )


def start_frontend():
    """Start the Next.js frontend development server"""
    # Use configuration for frontend host/port and backend URL
    frontend_host = getattr(config, 'FRONTEND_HOST', '127.0.0.1')
    frontend_bind_host = getattr(config, 'FRONTEND_BIND_HOST', '0.0.0.0')
    frontend_port = getattr(config, 'FRONTEND_PORT', 3000)
    backend_url = getattr(config, 'BACKEND_URL', 'http://127.0.0.1:8000')

    print(f"Starting frontend server at http://{frontend_host}:{frontend_port}")
    print(f"Listening on: {frontend_bind_host}:{frontend_port}")
    print(f"Connecting to backend at {backend_url}")

    frontend_dir = Path(__file__).parent / "frontend"

    # Check if node_modules exists
    if not (frontend_dir / "node_modules").exists():
        print("Installing frontend dependencies...")
        subprocess.run(
            ["npm", "install"],
            cwd=frontend_dir,
            env=os.environ.copy()
        )

    # Set environment variables for the frontend
    env = os.environ.copy()
    env["PORT"] = str(frontend_port)
    env["HOSTNAME"] = frontend_bind_host # Next.js binds to this
    env["NEXT_PUBLIC_API_URL"] = backend_url

    subprocess.run(
        ["npm", "run", "dev"],
        cwd=frontend_dir,
        env=env,
        shell=True
    )


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Start AI Video Factory Web UI")
    parser.add_argument(
        "--backend-only",
        action="store_true",
        help="Start only the backend server"
    )
    parser.add_argument(
        "--frontend-only",
        action="store_true",
        help="Start only the frontend server"
    )

    args = parser.parse_args()

    # Ensure all base directories exist
    ensure_base_directories()

    # Check if both options are provided
    if args.backend_only and args.frontend_only:
        print("Error: Cannot specify both --backend-only and --frontend-only")
        sys.exit(1)

    # Check ports
    backend_port = getattr(config, 'BACKEND_PORT', 8000)
    frontend_port = getattr(config, 'FRONTEND_PORT', 3000)

    if not args.frontend_only and not check_port_available(backend_port):
        print(f"Error: Port {backend_port} (Backend) is already in use")
        print("Please stop the other process or use a different port in config.py")
        sys.exit(1)

    if not args.backend_only and not check_port_available(frontend_port):
        print(f"Error: Port {frontend_port} (Frontend) is already in use")
        print("Please stop the other process (likely a previous frontend dev server)")
        sys.exit(1)

    print("="*60)
    print("AI Video Factory Web UI")
    print("="*60)

    if args.backend_only:
        print("Mode: Backend Only")
        start_backend()
    elif args.frontend_only:
        print("Mode: Frontend Only")
        start_frontend()
    else:
        print("Mode: Full Stack (Backend + Frontend)")
        print("\nStarting both servers in separate threads...")
        print("Press Ctrl+C to stop both servers\n")

        # Start backend in thread
        backend_thread = threading.Thread(target=start_backend, daemon=True)
        backend_thread.start()

        # Give backend time to start
        time.sleep(2)

        # Start frontend (blocks in main thread)
        try:
            start_frontend()
        except KeyboardInterrupt:
            print("\nShutting down...")


if __name__ == "__main__":
    main()
