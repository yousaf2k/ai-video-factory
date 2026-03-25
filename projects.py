"""
Project Viewer - View and manage AI Film Studio projects
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.project_manager import ProjectManager


def list_projects():
    """List all projects"""
    project_mgr = ProjectManager()
    projects = project_mgr.list_all_projects()

    if not projects:
        print("\n[INFO] No projects found.")
        return

    print("\n" + "="*80)
    print("AI FILM STUDIO - SESSIONS")
    print("="*80)

    for project in projects:
        status = "✓ COMPLETE" if project['completed'] else "⏳ IN PROGRESS"
        print(f"\n{status} | {project['project_id']}")
        print(f"  Idea: {project['idea'][:80]}...")
        print(f"  Started: {project['started_at']}")
        print(f"  Progress: {project['stats']['images_generated']}/{project['stats']['total_shots']} images, "
              f"{project['stats']['videos_rendered']} videos")

    print("\n" + "="*80)


def view_project(project_id):
    """View detailed project info"""
    project_mgr = ProjectManager()

    try:
        project_mgr.print_project_summary(project_id)

        # Show file locations
        project_dir = project_mgr.get_project_dir(project_id)
        print(f"\nFiles:")
        print(f"  Project dir: {project_dir}")
        print(f"  Story: {os.path.join(project_dir, 'story.json')}")
        print(f"  Shots: {os.path.join(project_dir, 'shots.json')}")
        print(f"  Images: {os.path.join(project_dir, 'images')}")

    except Exception as e:
        print(f"[ERROR] Could not load project: {e}")


def show_help():
    """Show help"""
    print("""
AI Film Studio - Project Viewer

Commands:
  python projects.py list              List all projects
  python projects.py view <project_id> View detailed project info
  python projects.py help              Show this help

Examples:
  python projects.py list
  python projects.py view project_20250208_002238
""")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_help()
    else:
        command = sys.argv[1].lower()

        if command == "list":
            list_projects()
        elif command == "view":
            if len(sys.argv) < 3:
                print("[ERROR] Please provide a project ID")
                print("Usage: python projects.py view <project_id>")
            else:
                view_project(sys.argv[2])
        elif command == "help":
            show_help()
        else:
            print(f"[ERROR] Unknown command: {command}")
            show_help()
