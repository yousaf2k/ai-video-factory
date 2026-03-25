import os
import json

base_dir = r"E:\output\projects"

def update_json_content(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 1. Update paths and keys
        new_content = content.replace("projects/", "projects/")
        new_content = new_content.replace("project_", "project_")
        
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Updated content in {filepath}")
    except Exception as e:
        print(f"Error updating content in {filepath}: {e}")

def main():
    count_content = 0
    count_rename = 0
    
    for root, dirs, files in os.walk(base_dir):
        folder_name = os.path.basename(root)
        
        for filename in files:
            if filename.endswith('.json'):
                filepath = os.path.join(root, filename)
                
                # Check for meta.json with wrong name
                if filename.endswith('_meta.json'):
                    desired_name = f"{folder_name}_meta.json"
                    
                    if filename != desired_name:
                        new_filepath = os.path.join(root, desired_name)
                        try:
                            if not os.path.exists(new_filepath):
                                os.rename(filepath, new_filepath)
                                print(f"Renamed {filename} -> {desired_name}")
                                count_rename += 1
                                filepath = new_filepath # Update for content processing
                        except Exception as e:
                            print(f"Error renaming {filename} to {desired_name}: {e}")

                # Update content
                update_json_content(filepath)
                count_content += 1

    print(f"Completed. Renamed {count_rename} meta files. Checked content in {count_content} files.")

if __name__ == "__main__":
    main()
