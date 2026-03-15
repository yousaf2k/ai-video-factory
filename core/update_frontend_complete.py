import os
import re

base_dir = r"c:\AI\ai_video_factory_v1\web_ui\frontend\src"

def replace_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Generic case-sensitive replacements
    # 1. Title Case: Project -> Project
    content = content.replace("ProjectStep", "ProjectStep")
    content = content.replace("ProjectStats", "ProjectStats")
    content = content.replace("ProjectListItem", "ProjectListItem")
    content = content.replace("ProjectDetail", "ProjectDetail")
    content = content.replace("Project", "Project")

    # 2. Lowercase: project -> project
    # Use re to avoid matching it inside other words if any (though usually fine)
    content = content.replace("project_id", "project_id")
    content = content.replace("projectId", "projectId")
    
    # Avoid replacing /api/projects which is already correct, but just in case
    # Let's target links:
    content = content.replace("/projects", "/projects")
    
    # query keys
    content = content.replace("['projects']", "['projects']")
    content = content.replace('["projects"]', '["projects"]')

    # Hooks and methods
    content = content.replace("useProjects", "useProjects")
    content = content.replace("useProject", "useProject")
    content = content.replace("useUpdateProject", "useUpdateProject")
    
    content = content.replace("listProjects", "listProjects")
    content = content.replace("createProject", "createProject")
    content = content.replace("getProject", "getProject")
    content = content.replace("updateProject", "updateProject")
    content = content.replace("deleteProject", "deleteProject")
    content = content.replace("duplicateProject", "duplicateProject")

    # General lowercase variable names
    # Be careful not to replace it if it's already updated, but safe mostly
    content = content.replace("const { data: projects", "const { data: projects")
    content = content.replace("projects.map", "projects.map")
    content = content.replace("projects?", "projects?")
    content = content.replace("projects ", "projects ")
    content = content.replace("project.", "project.")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

# 1. Rename hooks file
old_hook = os.path.join(base_dir, "hooks", "useProjects.ts")
new_hook = os.path.join(base_dir, "hooks", "useProjects.ts")
if os.path.exists(old_hook):
    os.rename(old_hook, new_hook)
    print(f"Renamed hook file to useProjects.ts")

# 2. Walk and replace in files
count = 0
for dirpath, dirnames, filenames in os.walk(base_dir):
    for filename in filenames:
        if filename.endswith(('.ts', '.tsx', '.js', '.jsx')):
            filepath = os.path.join(dirpath, filename)
            replace_in_file(filepath)
            count += 1

print(f"Processed {count} frontend files for string replacement.")
