import os

files_to_update = [
    r"c:\AI\ai_video_factory_v1\web_ui\backend\models\queue.py",
    r"c:\AI\ai_video_factory_v1\web_ui\backend\services\queue_service.py"
]

def update_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Generic replacements
    content = content.replace("project_id", "project_id")
    content = content.replace("project_title", "project_title")
    content = content.replace("total_projects", "total_projects")
    content = content.replace("projects.add", "projects.add")
    content = content.replace("projects: Set[str]", "projects: Set[str]")
    content = content.replace("projects = set()", "projects = set()")
    content = content.replace("for item in self._queue:\n                # Status counts", "for item in self._queue:\n                # Status counts") # just to be sure
    content = content.replace("projects.add(item.project_id)", "projects.add(item.project_id)") # since project_id becomes project_id
    content = content.replace("stats['total_projects'] = len(projects)", "stats['total_projects'] = len(projects)")
    
    # Text replacements in docstrings or logs if any
    content = content.replace("Project counts", "Project counts")
    content = content.replace("unique projects", "unique projects")
    content = content.replace("Project filter", "Project filter")
    content = content.replace("Project title", "Project title")
    content = content.replace("cross-project", "cross-project")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Updated {filepath}")

for f in files_to_update:
    if os.path.exists(f):
        update_file(f)
    else:
        print(f"File not found: {f}")
