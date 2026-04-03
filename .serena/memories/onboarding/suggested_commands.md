# Suggested Commands for AI Video Factory

## Essential Commands

### 🎬 Running the Pipeline (CLI)
Generate a video from a text idea:
```powershell
python core/main.py --idea "A futuristic city in the clouds"
```
List available LLM agents:
```powershell
python core/main.py --list-agents
```

### 🌐 Starting the Web UI
Launches both the FastAPI backend and Next.js frontend:
```powershell
python web_ui/start.py
```
Or use the batch file:
```powershell
launch_ui.bat
```

### 🧪 Running Tests
Run the entire test suite:
```powershell
python run_tests.py
# OR
pytest
```

## Utility Scripts

### 📂 Project Management
List and manage projects via CLI:
```powershell
python projects.py --list
```

### 🔄 Selective Regeneration
Regenerate specific shots from an existing project:
```powershell
python regenerate.py --project {project_id} --shots "1,3,5"
```

### 📦 Batch Processing
Generate multiple videos from a list of prompts:
```powershell
python batch_videos.py --input-file prompts.txt
```

## Development Workflow

### 🛠️ Coding Helper
Run the built-in coding helper tool:
```powershell
coding_helper.bat
```

### 🔌 ComfyUI Interaction
Ensure ComfyUI is running locally before starting the pipeline:
- Default URL: `http://127.0.0.1:8188`

## Windows-Specific Utilities
- `dir` / `ls`: List files and directories
- `findstr` / `grep`: Search for text in files
- `type` / `cat`: View file contents
- `git`: Standard version control operations
