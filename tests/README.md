# Tests Documentation

This directory contains all tests for the AI Video Factory project.

## Directory Structure

```
tests/
├── __init__.py                 # Tests package
├── conftest.py                 # pytest fixtures and configuration
├── README.md                   # This file
├── unit/                       # Unit tests (to be added later)
│   └── __init__.py
└── integration/                # Integration tests
    ├── __init__.py
    ├── test_gemini.py          # Gemini API tests
    ├── test_zhipu.py           # Zhipu API tests
    ├── test_lmstudio.py        # LMStudio tests
    └── ...
```

## Running Tests

### Run all tests:
```bash
python -m pytest tests/ -v
```

### Run specific test file:
```bash
python -m pytest tests/integration/test_gemini.py -v
```

### Run using the test runner script:
```bash
python run_tests.py
```

### Run only integration tests:
```bash
python -m pytest tests/integration/ -v
```

### Run with coverage:
```bash
python -m pytest tests/ --cov=core --cov-report=html
```

## Adding New Tests

### Integration Tests
Place integration tests in `tests/integration/`. Integration tests should:
- Test multiple components working together
- Test external API integrations
- Be named `test_*.py`

### Unit Tests
Place unit tests in `tests/unit/`. Unit tests should:
- Test individual functions/classes in isolation
- Use mocks to avoid external dependencies
- Be named `test_*.py`

## Test Naming Conventions

- Test files: `test_<module_name>.py`
- Test classes: `Test<ClassName>`
- Test functions: `test_<function_name>`

## pytest Configuration

The `tests/conftest.py` file contains:
- Python path configuration (adds project root to sys.path)
- Shared fixtures for all tests

You can add shared fixtures here that will be available to all tests.

## Notes

- Existing tests are simple scripts and don't use pytest features yet
- Tests can be gradually refactored to use pytest features like fixtures, parametrize, etc.
- The `unit/` folder is prepared for future unit tests
