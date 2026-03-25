import os
import re

def update_file_content(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Skipping {file_path} due to read error: {e}")
        return False

    original_content = content

    # 1. Update paths
    content = content.replace("output/projects/", "output/projects/")
    content = content.replace("projects/", "projects/")
    
    # 2. Update method calls and variables
    content = content.replace("load_project(", "load_project(")
    content = content.replace("save_project(", "save_project(")
    content = content.replace("load_project_full(", "load_project_full(")
    content = content.replace("project_dir", "project_dir")
    content = content.replace("project_path", "project_path")
    
    # 3. Update log/message text that strictly means Project as in Project
    # But do NOT touch requests.Project()
    content = re.sub(r'Project ({project_id}|{project_id}|[a-zA-Z0-9_\-]+)', r'Project \1', content)
    content = re.sub(r'project ({project_id}|{project_id})', r'project \1', content)
    
    # 4. Miscellaneous renames
    content = content.replace("project_title", "project_title")
    content = content.replace("total_projects", "total_projects")
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    root_dir = r"c:\AI\ai_video_factory_v1"
    updated_files = []

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip node_modules and .next and .git
        if 'node_modules' in dirpath or '.next' in dirpath or '.git' in dirpath:
            continue
            
        for filename in filenames:
            if filename.endswith(".py"):
                file_path = os.path.join(dirpath, filename)
                # Skip this script itself
                if filename == "update_py_files.py":
                    continue
                    
                if update_file_content(file_path):
                    updated_files.append(file_path)

    print(f"Updated {len(updated_files)} python files:")
    for f in updated_files:
        print(f"- {f}")

if __name__ == "__main__":
    main()
