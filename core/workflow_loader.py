"""
Workflow Loader - Load and manage ComfyUI workflow JSON files.

Workflow folder structure:
workflow/
├── image/
│   ├── flux.json
│   └── flux2.json
├── video/
│   ├── wan2.json
│   └── lt_long.json
└── voice/
    └── default.json
"""
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import config

class WorkflowLoader:
    """Load and manage workflow JSON files from the workflow folder."""

    def __init__(self, workflow_dir: str = None):
        """
        Initialize the workflow loader.

        Args:
            workflow_dir: Path to the workflow directory (default: "workflow" in project root)
        """
        if workflow_dir is None:
            self.workflow_dir = Path(config.PROJECT_ROOT) / "workflow"
        else:
            self.workflow_dir = Path(workflow_dir)

    def list_categories(self) -> List[str]:
        """List all workflow categories (subdirectories)."""
        if not self.workflow_dir.exists():
            return []
        
        categories = []
        for item in self.workflow_dir.iterdir():
            if item.is_dir():
                categories.append(item.name)
        return sorted(categories)

    def list_workflows(self, category: str) -> List[str]:
        """List all available workflows for a given category."""
        category_dir = self.workflow_dir / category
        if not category_dir.exists():
            return []

        workflows = []
        for file in category_dir.glob("*.json"):
            workflows.append(file.name)
        return sorted(workflows)

    def load_workflow(self, category: str, filename: str) -> str:
        """Load a workflow JSON file as a string."""
        workflow_file = self.workflow_dir / category / filename

        if not workflow_file.exists():
            raise FileNotFoundError(f"Workflow not found: {workflow_file}")

        with open(workflow_file, 'r', encoding='utf-8') as f:
            return f.read()

    def save_workflow(self, category: str, filename: str, content: str):
        """Save/update a workflow JSON file."""
        # Validate JSON content
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON content: {str(e)}")

        category_dir = self.workflow_dir / category
        os.makedirs(category_dir, exist_ok=True)
        
        workflow_file = category_dir / filename
        
        with open(workflow_file, 'w', encoding='utf-8') as f:
            f.write(content)

    def get_all_workflows(self) -> List[Dict[str, str]]:
        """Get all workflows grouped by category."""
        all_workflows = []
        for category in self.list_categories():
            workflows = self.list_workflows(category)
            for filename in workflows:
                all_workflows.append({
                    "id": filename,
                    "name": filename.replace('.json', '').replace('_', ' ').title(),
                    "category": category,
                    "filename": filename
                })
        return all_workflows

# Global workflow loader instance
_workflow_loader = None

def get_workflow_loader() -> WorkflowLoader:
    """Get the global workflow loader instance."""
    global _workflow_loader
    if _workflow_loader is None:
        _workflow_loader = WorkflowLoader()
    return _workflow_loader
