# AI Video Factory - Web UI

A modern web-based interface for the AI Video Factory system. This provides a visual way to create, edit, and manage video generation projects.

## Features Implemented (Phase 1-3)

### ✅ Backend (FastAPI)
- **Project Management API**: Full CRUD operations for projects
- **Story Editing API**: Update and regenerate stories with validation
- **Pydantic Models**: Type-safe data models for projects, stories, and shots
- **CORS Support**: Properly configured for frontend communication
- **Static File Serving**: Automatic mounting of images/videos for preview

### ✅ Frontend (Next.js 14 + TypeScript)
- **Project List**: View all projects with progress indicators
- **Project Detail**: Full project view with story and shots
- **Story Editor**: Drag-and-drop scene reordering
- **Inline Editing**: Edit scene fields (location, characters, action, emotion, narration, duration)
- **Add/Delete Scenes**: Full scene management
- **Auto-refresh**: Real-time updates when projects are active

### ✅ Developer Experience
- **TypeScript**: Full type safety across frontend and backend
- **React Query**: Server state management with caching
- **TailwindCSS**: Modern, responsive styling
- **Hot Reload**: Fast development with instant feedback

## Installation & Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- Existing AI Video Factory installation

### Backend Setup

1. Install Python dependencies:
```bash
cd C:\AI\ai_video_factory_v1
pip install -r requirements.txt
```

2. The following dependencies have been added to requirements.txt:
- fastapi>=0.104.0
- uvicorn[standard]>=0.24.0
- websockets>=12.0
- python-multipart>=0.0.6
- aiofiles>=23.2.0
- pydantic>=2.5.0

3. Start the backend server:
```bash
cd web_ui/backend
python main.py
```

The API will be available at `http://127.0.0.1:8000`
API documentation: `http://127.0.0.1:8000/docs`

### Frontend Setup

1. Install Node dependencies:
```bash
cd web_ui/frontend
npm install
```

2. Start the development server:
```bash
npm run dev
```

The web UI will be available at `http://localhost:3000`

## Usage

### Creating a Project

1. Navigate to `http://localhost:3000`
2. Click "New Project"
3. Enter your video idea
4. Click "Create"

### Editing Story

1. Open a project
2. Click "Edit Project"
3. Modify scenes:
   - **Drag** scenes to reorder
   - **Click edit icon** to modify scene details
   - **Click delete icon** to remove a scene
   - **Click "Add Scene"** to create new scenes
4. Click "Save Changes" to persist

### Viewing Progress

- Project list shows completion status
- Detail page has progress bars for:
  - Story generation
  - Shot planning
  - Image generation
  - Video rendering
  - Narration

## API Endpoints

### Projects
- `GET /api/projects` - List all projects
- `POST /api/projects` - Create new project
- `GET /api/projects/{id}` - Get project details
- `PUT /api/projects/{id}` - Update project
- `DELETE /api/projects/{id}` - Delete project
- `POST /api/projects/{id}/duplicate` - Duplicate project

### Story
- `GET /api/projects/{id}/story` - Get story
- `PUT /api/projects/{id}/story` - Update story
- `POST /api/projects/{id}/story/regenerate` - Regenerate story

### Assets
- `GET /api/projects/{id}/images/{filename}` - Get image
- `GET /api/projects/{id}/videos/{filename}` - Get video

## Project Structure

```
web_ui/
├── backend/
│   ├── main.py                 # FastAPI app entry point
│   ├── api/                    # API endpoints
│   │   ├── projects.py         # Project CRUD
│   │   └── stories.py          # Story editing
│   ├── services/               # Business logic
│   │   └── project_service.py  # Project wrapper
│   └── models/                 # Pydantic models
│       ├── project.py          # Project models
│       ├── story.py            # Story models
│       └── shot.py             # Shot models
└── frontend/
    ├── src/
    │   ├── app/                # Next.js pages
    │   │   ├── projects/
    │   │   │   ├── page.tsx    # Project list
    │   │   │   └── [id]/
    │   │   │       ├── page.tsx # Project detail
    │   │   │       └── edit/    # Story editor
    │   │   └── globals.css
    │   ├── components/
    │   │   └── scenes/         # Scene editor components
    │   │       ├── SceneCard.tsx
    │   │       └── SceneList.tsx
    │   ├── hooks/              # React hooks
    │   │   ├── useProjects.ts
    │   │   └── useStory.ts
    │   ├── services/           # API client
    │   │   └── api.ts
    │   └── types/              # TypeScript types
    │       └── index.ts
    └── package.json
```

## Configuration

The following settings have been added to `config.py`:

```python
# Web UI Configuration
WEB_UI_ENABLED = True                    # Enable/disable web UI
WEB_UI_HOST = "127.0.0.1"               # Backend server host
WEB_UI_PORT = 8000                       # Backend server port
WEB_UI_CORS_ORIGINS = [                 # Allowed frontend origins
    "http://localhost:3000",
    "http://127.0.0.1:3000"
]
```

## Next Steps (Planned Features)

### Phase 4: Shot Management
- Edit shot prompts (image, motion, camera)
- Regenerate individual shots
- View generated images/videos inline
- Camera type selector

### Phase 5: Real-time Progress
- WebSocket progress updates
- Start/stop generation from UI
- Live progress bars
- ETA display

### Phase 6: Configuration
- Config panel UI
- Agent selector
- Export/download projects

## Development Notes

### CLI Remains Functional
The web UI is fully complementary to the existing CLI. All CLI commands work exactly as before.

### Wrapper Pattern
The backend uses a wrapper pattern around existing core modules:
- `ProjectManager` - All project operations
- `build_story()` - Story generation
- `plan_shots()` - Shot planning
- No changes to core modules required

### Type Safety
- Backend: Pydantic models for validation
- Frontend: TypeScript types matching backend models
- Shared types in `/types/index.ts`

## Troubleshooting

### Backend won't start
- Check if port 8000 is available
- Verify all dependencies are installed
- Check Python version (3.10+ required)

### Frontend can't connect to backend
- Ensure backend is running on port 8000
- Check CORS origins in config.py
- Verify API_BASE_URL in frontend

### Images/videos not loading
- Check that static files are mounted correctly
- Verify file paths in project data
- Check browser console for errors

## License

Same as AI Video Factory main project.
