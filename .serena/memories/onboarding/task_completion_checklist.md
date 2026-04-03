# Task Completion Checklist for AI Video Factory

Before finishing a task or submitting a change, ensure you've completed the following steps:

## 🧪 Automated Testing
1. **Verification Script**: Run the main test suite:
   ```powershell
   python run_tests.py
   ```
2. **Pytest Integration**: Run all unit and integration tests:
   ```powershell
   pytest
   ```
3. **Specific Tests**: If your changes are focused on a single module, run the corresponding test file in the `tests/` directory (e.g., `pytest tests/test_queue.py`).

## 🌐 Frontend Verification (UI Changes)
1. **Linting**: Run the Next.js linter to check for potential issues:
   ```powershell
   cd web_ui/frontend && npm run lint
   ```
2. **Build Test**: If significant changes were made, verify the frontend builds successfully:
   ```powershell
   npm run build
   ```
3. **Manual UI Check**: Manually verify all UI elements in the browser (default: `http://localhost:3000`).

## 📄 Documentation
1. **Update Agent Prompts**: If you've modified LLM agent prompts, ensure the documentation in `agents/` is updated.
2. **Docstrings**: Verify that any new functions or classes have descriptive docstrings.
3. **GEMINI.md**: Check if any project-wide architectural changes need to be reflected in `GEMINI.md`.

## 📦 Project Clean-up
1. **Logs**: Check the `logs/` directory for any unexpected errors or warnings generated during testing.
2. **Output**: Ensure test projects generated in `output/` are cleaned up (if not automatically handled).
