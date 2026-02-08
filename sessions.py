"""
Session Viewer - View and manage AI Film Studio sessions
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.session_manager import SessionManager


def list_sessions():
    """List all sessions"""
    session_mgr = SessionManager()
    sessions = session_mgr.list_all_sessions()

    if not sessions:
        print("\n[INFO] No sessions found.")
        return

    print("\n" + "="*80)
    print("AI FILM STUDIO - SESSIONS")
    print("="*80)

    for session in sessions:
        status = "✓ COMPLETE" if session['completed'] else "⏳ IN PROGRESS"
        print(f"\n{status} | {session['session_id']}")
        print(f"  Idea: {session['idea'][:80]}...")
        print(f"  Started: {session['started_at']}")
        print(f"  Progress: {session['stats']['images_generated']}/{session['stats']['total_shots']} images, "
              f"{session['stats']['videos_rendered']} videos")

    print("\n" + "="*80)


def view_session(session_id):
    """View detailed session info"""
    session_mgr = SessionManager()

    try:
        session_mgr.print_session_summary(session_id)

        # Show file locations
        session_dir = session_mgr.get_session_dir(session_id)
        print(f"\nFiles:")
        print(f"  Session dir: {session_dir}")
        print(f"  Story: {os.path.join(session_dir, 'story.json')}")
        print(f"  Shots: {os.path.join(session_dir, 'shots.json')}")
        print(f"  Images: {os.path.join(session_dir, 'images')}")

    except Exception as e:
        print(f"[ERROR] Could not load session: {e}")


def show_help():
    """Show help"""
    print("""
AI Film Studio - Session Viewer

Commands:
  python sessions.py list              List all sessions
  python sessions.py view <session_id> View detailed session info
  python sessions.py help              Show this help

Examples:
  python sessions.py list
  python sessions.py view session_20250208_002238
""")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_help()
    else:
        command = sys.argv[1].lower()

        if command == "list":
            list_sessions()
        elif command == "view":
            if len(sys.argv) < 3:
                print("[ERROR] Please provide a session ID")
                print("Usage: python sessions.py view <session_id>")
            else:
                view_session(sys.argv[2])
        elif command == "help":
            show_help()
        else:
            print(f"[ERROR] Unknown command: {command}")
            show_help()
