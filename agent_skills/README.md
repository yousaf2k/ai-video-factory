# Agent Skills

Skills are reusable instruction playbooks for the AI Agent Assistant. Each skill
is a folder with a `SKILL.md` file. The agent sees every skill's name and
description in its system prompt and reads the full instructions on demand via
its `read_skill` tool.

## Creating a skill

```
agent_skills/
└── my-skill/
    ├── SKILL.md          # required
    └── notes.md          # optional extra files (read via read_skill_file)
```

`SKILL.md` format — an optional YAML frontmatter block, then markdown:

```markdown
---
name: my-skill
description: One line telling the agent WHEN to use this skill.
---

Step-by-step instructions the agent should follow...
```

- `name` defaults to the folder name.
- `description` is what the agent uses to decide when the skill applies —
  write it as a trigger condition ("Use when the user asks ...").
- Extra files next to `SKILL.md` can hold checklists, prompt templates or
  examples; reference them in the skill body.

Skills can also be created from the Web UI: **Agent → Settings → Skills → New Skill**.

## Built-in examples

| Skill | Use when |
|---|---|
| `fix-shot-prompt` | A generated shot shows the wrong action/character and the prompt needs a surgical fix + regeneration |
| `new-project-wizard` | The user wants a brand-new project set up end to end |
| `project-health-check` | The user wants a full audit of a project (missing media, failed steps, queue state) |
