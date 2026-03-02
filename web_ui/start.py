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


def check_port_available(port):
    """Check if a port is available"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            return True
        except:
            return False


def start_backend():
    """Start the FastAPI backend server"""
    print(f"Starting backend server at http://{config.WEB_UI_HOST}:{config.WEB_UI_PORT}")
    print(f"API docs: http://{config.WEB_UI_HOST}:{config.WEB_UI_PORT}/docs")

    backend_dir = Path(__file__).parent / "backend"
    subprocess.run(
        [sys.executable, "main.py"],
        cwd=backend_dir,
        env=os.environ.copy()
    )


def start_frontend():
    """Start the Next.js frontend development server"""
    print("Starting frontend server at http://localhost:3000")

    frontend_dir = Path(__file__).parent / "frontend"

    # Check if node_modules exists
    if not (frontend_dir / "node_modules").exists():
        print("Installing frontend dependencies...")
        subprocess.run(
            ["npm", "install"],
            cwd=frontend_dir,
            env=os.environ.copy()
        )

    subprocess.run(
        ["npm", "run", "dev"],
        cwd=frontend_dir,
        env=os.environ.copy(),
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

    # Check if both options are provided
    if args.backend_only and args.frontend_only:
        print("Error: Cannot specify both --backend-only and --frontend-only")
        sys.exit(1)

    # Check ports
    if not args.frontend_only and not check_port_available(config.WEB_UI_PORT):
        print(f"Error: Port {config.WEB_UI_PORT} is already in use")
        print("Please stop the other process or use a different port in config.py")
        sys.exit(1)

    if not args.backend_only and not check_port_available(3000):
        print("Error: Port 3000 is already in use")
        print("Please stop the other process (likely the frontend dev server)")
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
