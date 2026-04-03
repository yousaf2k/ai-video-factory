# Style & Conventions for AI Video Factory

## 🐍 Python Coding Standards
- **Standard**: Follow PEP8-like principles for readability.
- **Logging**: Use the built-in `logging` module to track project execution.
- **Type Hints**: Use type hints for function arguments and return values (e.g., `def load_workflow(path: str, video_length_seconds: float = None) -> dict`).
- **Docstrings**: Provide clear, descriptive docstrings for all functions and classes.
- **Data Management**: Use JSON for data storage (stories, shots, project state).

### 🏷️ Naming Conventions
- **Functions/Variables**: `snake_case` (e.g., `generate_video_clip()`).
- **Classes**: `PascalCase` (e.g., `StoryEngine`).
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `IMAGE_GENERATION_MODE`).

## 🌐 Frontend Coding Standards (Next.js)
- **Framework**: Next.js 14 (App Router).
- **Styling**: Tailwind CSS for component styling.
- **Component Design System**: Radix UI for accessible UI primitives.
- **State Management**: TanStack Query (React Query) for data fetching and Zustand for local state management (where needed).
- **Form Handling**: React Hook Form for visual story editing.
- **Linting**: Run `npm run lint` in `web_ui/frontend` before committing UI changes.

## 🤖 Agent-Based Prompt Engineering
AI agents are defined in Markdown files within `agents/`.
- **System Prompts**: Each file contains a system prompt defining the LLM's role.
- **Output Format**: Prompts should clearly specify the expected output format (e.g., JSON, or specific text structure).
- **Placeholders**: Use `{USER_INPUT}` for injection points.
- **Guidelines**: Include a `## Guidelines` section for the agent.

## ⚙️ Configuration
- Use `config.py` as the central configuration hub.
- Override settings using environment variables in a `.env` file (e.g., `GEMINI_API_KEY`, `COMFYUI_SERVER_URL`).
