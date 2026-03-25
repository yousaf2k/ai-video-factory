import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
files_to_update = [
    os.path.join(project_root, "web_ui", "backend", "models", "queue.py"),
    os.path.join(project_root, "web_ui", "backend", "services", "queue_service.py")
]

def update_file(filepath):
    if not os.path.exists(filepath):
        print(f"Skipping {filepath} - not found")
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Standard replacement
    new_content = content.replace("/api/projects", "/api/projects")
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {filepath}")
    else:
        print(f"No changes needed for {filepath}")

if __name__ == "__main__":
    for f in files_to_update:
        update_file(f)
