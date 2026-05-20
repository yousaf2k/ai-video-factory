import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

files_to_delete = [
    os.path.join(project_root, "web_ui", "backend", "api", "projects.py"),
    os.path.join(project_root, "web_ui", "backend", "services", "project_service.py"),
    os.path.join(project_root, "web_ui", "backend", "models", "project.py"),
    os.path.join(project_root, "core", "project_manager.py")
]

for path in files_to_delete:
    if os.path.exists(path):
        os.remove(path)
        print(f"Deleted {path}")
    else:
        print(f"Skipping {path} - not found")

# Also delete helper scripts I created if they still exist
helpers = [
    os.path.join(project_root, "core", "create_project_manager.py"),
    os.path.join(project_root, "core", "create_project_service.py"),
    os.path.join(project_root, "core", "create_project_models_api.py"),
    os.path.join(project_root, "core", "update_shots_api.py"),
    os.path.join(project_root, "core", "update_backend_files.py"),
    os.path.join(project_root, "core", "update_manager.py"),
    os.path.join(project_root, "core", "update_remaining_backend.py"),
    os.path.join(project_root, "core", "fix_api_services.py")
]

for h in helpers:
    if os.path.exists(h):
        os.remove(h)
        print(f"Deleted helper {h}")

print("Cleanup complete")
