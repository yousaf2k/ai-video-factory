<!--
  Sync Impact Report:
  - Version change: Initial (0.0.0) → 1.0.0
  - This is the initial ratification of the AI Video Factory constitution
  - All principles are newly established
  - Templates reviewed: plan-template.md ✅, spec-template.md ✅, tasks-template.md ✅
  - No deferred placeholders - all values populated from project context
-->

# AI Video Factory Constitution

## Core Principles

### I. Pipeline-First Architecture

Every feature MUST align with the 7-step video generation pipeline:

1. **Idea** → User input/idea file
2. **Story** → Narrative generation with scene breakdown
3. **Scene Graph** → Visual structure and flow planning
4. **Shots** → Detailed shot planning with camera movements
5. **Images** → Visual content generation (Gemini/ComfyUI)
6. **Videos** → Motion generation (Wan 2.2/ComfyUI)
7. **Narration** → Text-to-speech overlay

**Rationale**: The pipeline is the core abstraction. All features must either:
- Enhance a specific pipeline step (e.g., new image generation method)
- Improve pipeline orchestration (e.g., crash recovery, session management)
- Add cross-cutting capabilities (e.g., new LLM providers, batch processing)

Violations: Features that bypass or ignore the pipeline structure without clear justification.

### II. Agent-Based Content Generation

Content creation MUST use specialized agents defined in `agents/` directory structure:

- **Story Agents** (`agents/story/`) - Narrative generation with specific styles (documentary, dramatic, time traveler, etc.)
- **Image Agents** (`agents/image/`) - Visual prompt engineering (artistic, photorealistic, DSLR photography, etc.)
- **Video Agents** (`agents/video/`) - Motion and camera direction (cinematic, standard, etc.)
- **Narration Agents** (`agents/narration/`) - Voice-over script generation (professional, storytelling, etc.)

**Agent Requirements**:
- Each agent MUST be a standalone `.md` file with clear system prompt
- Agents MUST include `{USER_INPUT}` placeholder for dynamic content insertion
- Agents MUST specify output format clearly (JSON, text, etc.)
- New agents MUST follow existing template structure in `.specify/templates/agent-file-template.md`

**Rationale**: Agents provide modularity, testability, and extensibility. Users can create custom agents without modifying core pipeline code.

### III. Multi-Provider Integration

The system MUST support multiple providers for each capability:

**LLM Providers**:
- Gemini API (primary)
- Local providers: Ollama, LM Studio, Zhipu AI
- Extensible provider architecture in `core/llm/`

**Image Generation**:
- Gemini API (simple mode)
- ComfyUI with Flux/SDXL workflows (advanced mode)
- Automatic retry mechanism for failed generations

**Video Generation**:
- ComfyUI with Wan 2.2 model
- Multi-camera LoRA system (drone, orbit, dolly, zoom, etc.)

**TTS Providers**:
- ElevenLabs (premium voices)
- Extensible for additional providers

**Rationale**: Avoids vendor lock-in, provides fallback options, enables local/offline operation, supports different cost/performance trade-offs.

### IV. Session State & Crash Recovery

The pipeline MUST maintain robust session state:

**Requirements**:
- Every session tracked in `sessions/` directory
- State persisted after each pipeline step completion
- Automatic crash recovery allowing continuation from last successful step
- Selective regeneration (regenerate specific steps without starting over)
- Shot-level tracking for video/image regeneration

**Implementation**:
- `sessions.py` module for session management
- JSON-based state persistence
- Atomic step completion marking

**Rationale**: Video generation is resource-intensive and time-consuming. Users must not lose progress due to crashes, API failures, or intentional interruptions.

### V. Configuration Driven

All configurable parameters MUST be externalized:

**Configuration Sources** (priority order):
1. Command-line arguments (highest priority)
2. Environment variables
3. `config.py` defaults (lowest priority)

**Configurable Areas**:
- API keys and endpoints
- Model selection and parameters
- Pipeline step execution (skip steps, start from specific step)
- Output paths and file naming
- Agent selection for each content type
- Retry logic and timeout values
- Batch processing options

**Rationale**: Enables different deployment scenarios (local vs. cloud), supports experimentation without code changes, facilitates debugging and testing.

### VI. Error Resilience & Observability

The system MUST provide comprehensive error handling and logging:

**Requirements**:
- Structured logging via `core/logger_config.py`
- Log levels: DEBUG for development, INFO for normal operation, ERROR for failures
- Automatic retry with exponential backoff for API calls
- Graceful degradation (fall back to alternative providers when primary fails)
- Clear error messages with actionable guidance

**Retry Logic**:
- Automatic retry for transient failures
- Retry tracker module to monitor and limit retry attempts
- Configurable retry counts and timeouts
- Manual retry capability via CLI flags

**Rationale**: External APIs are unreliable. Video generation is expensive. Users need visibility into what's happening and why.

## Development Standards

### Code Organization

```
ai_video_factory_v1/
├── core/                   # Core pipeline orchestration
│   ├── main.py            # Main entry point and pipeline orchestration
│   ├── logger_config.py   # Logging configuration
│   ├── llm/               # LLM provider implementations
│   └── [pipeline modules] # Step-specific implementations
├── agents/                # Agent prompt definitions
│   ├── story/
│   ├── image/
│   ├── video/
│   └── narration/
├── sessions.py            # Session state management
├── config.py              # Configuration defaults
├── workflow/              # ComfyUI workflow definitions
└── tests/                 # Test suite (contract, integration, unit)
```

### Python Standards

- **Language**: Python 3.11+
- **Style**: PEP 8 with 4-space indentation
- **Type Hints**: Required for all public functions
- **Docstrings**: Google style for all modules and public functions
- **Error Handling**: Specific exceptions, never bare `except:` clauses

### Testing Strategy

Tests are OPTIONAL per feature specification but MUST follow this structure when included:

- **Contract Tests**: API/interface contracts between modules
- **Integration Tests**: Pipeline step coordination
- **Unit Tests**: Individual component logic

**Note**: Tests explicitly written only when requested in feature spec (see tasks-template.md).

### Documentation Standards

**Required Documentation**:
- `README.md` - Quick start and basic usage
- `docs/QUICK_START.md` - Detailed getting started guide
- Feature-specific guides in `docs/` for major capabilities
- Agent usage guides for custom agent creation
- API reference for programmatic usage

**Documentation Updates**:
- Update README for any user-facing changes
- Create feature guide for substantial new features
- Update quickstart guides for workflow changes

## Governance

### Amendment Process

1. **Proposal**: Document rationale and proposed changes
2. **Impact Analysis**: Assess effect on existing features and templates
3. **Version Bump**: Follow semantic versioning:
   - **MAJOR**: Removal or redefinition of core principles
   - **MINOR**: New principle added or material expansion
   - **PATCH**: Clarifications, wording improvements, non-semantic changes
4. **Template Sync**: Update all dependent templates:
   - `.specify/templates/plan-template.md` - Constitution Check section
   - `.specify/templates/spec-template.md` - Requirements alignment
   - `.specify/templates/tasks-template.md` - Task categorization
   - `.specify/templates/agent-file-template.md` - Agent standards
5. **Compliance Review**: Verify existing features conform or document violations

### Compliance Review

All feature implementations MUST:
1. Reference applicable constitutional principles
2. Document any violations with justification in plan.md Complexity Tracking
3. Pass Constitution Check gate before implementation begins
4. Update dependent artifacts if principles change

### Complexity Justification

If a feature appears to violate constitutional principles:
1. Document the specific principle(s) impacted
2. Explain why the violation is necessary
3. Describe simpler alternatives considered and why they were insufficient
4. Record in plan.md Complexity Tracking table

### Runtime Development Guidance

For day-to-day development decisions not covered by feature specs, refer to:
- `README.md` - Project overview and usage
- `docs/QUICK_START.md` - Detailed setup and workflow
- `docs/AGENT_GUIDE.md` - Agent creation guidelines (when created)
- `docs/WORKFLOW_GUIDE.md` - Pipeline architecture

**Version**: 1.0.0 | **Ratified**: 2026-02-27 | **Last Amended**: 2026-02-27
