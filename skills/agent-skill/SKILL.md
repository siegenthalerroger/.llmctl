---
name: "agent-skill"
description: "Guidelines for creating high-quality Agent Skills. Use when asked to create, review, or improve AI agent skills, design skill structures, write skill documentation, or understand agent skill best practices and specifications."
license: "MIT"
adaptedFrom: "https://github.com/github/awesome-copilot/blob/main/instructions/agent-skills.instructions.md"
---

# Agent Skills File Guidelines

Instructions for creating effective and portable Agent Skills that enhance AI Agents with specialized capabilities, workflows, and bundled resources.

## What Are Agent Skills?

Agent Skills are self-contained folders with instructions and bundled resources that teach AI agents specialized capabilities. Unlike custom instructions (which define coding standards), skills enable task-specific workflows that can include scripts, examples, templates, and reference data.

Key characteristics:

- **Portable**: Works across VS Code, Copilot and Claude Code among other platforms
- **Progressive loading**: Only loaded when relevant to the user's request
- **Resource-bundled**: Can include scripts, templates, examples alongside instructions
- **On-demand**: Activated automatically based on prompt relevance

### Progressive Loading Architecture

Skills use three-level loading for efficiency:

| Level           | What Loads                    | When                                   |
| --------------- | ----------------------------- | -------------------------------------- |
| 1. Discovery    | `name` and `description` only | Always (lightweight metadata)          |
| 2. Instructions | Full `SKILL.md` body          | When request matches description       |
| 3. Resources    | Scripts, examples, docs       | Only when the AI agent references them |

### Where to find skills

Skills are stored in specific locations. Do NOT use other directories!

| Location                         | Scope                | Recommendation                  |
| -------------------------------- | -------------------- | ------------------------------- |
| `.agent/skills/<skill-name>/`    | Project/repository   | Recommended for project skills  |
| `~/.llmctl/skills/<skill-name>/` | Personal (user-wide) | Recommended for personal skills |

Each skill **must** have its own subdirectory containing at minimum a `SKILL.md` file.

## Required SKILL.md Format

### Frontmatter (Required)

```yaml
---
name: "example-skill"
description: "Toolkit and guidelines for an example usecase. Use when asked to do an example task given that a prerequisite is met."
---
```

| Field         | Required | Constraints                                                               |
| ------------- | -------- | ------------------------------------------------------------------------- |
| `name`        | Yes      | Lowercase, hyphens for spaces, max 64 characters (e.g., `webapp-testing`) |
| `description` | Yes      | Clear description of capabilities AND use cases, max 1024 characters      |

#### Description Best Practices

**CRITICAL**: The `description` field is the PRIMARY mechanism for automatic skill discovery. The AI Agent reads ONLY the `name` and `description` to decide whether to load a skill. If your description is vague, the skill will never be activated.

**What to include in description:**

1. **WHAT** the skill does (capabilities)
2. **WHEN** to use it (specific triggers, scenarios, file types, or user requests)
3. **Keywords** that users might mention in their prompts

See examples in the [reference file](./references/FRONTMATTER.md) for clarification.

### Body Content

The body contains detailed instructions that AI loads AFTER the skill is activated. See [examples](./references/BODY.md) for clarification.

## Bundling Resources

Skills can include additional files that Copilot accesses on-demand:

### Supported Resource Types

| Folder        | Purpose                                                               | Loaded into Context? | Example Files                                             |
| ------------- | --------------------------------------------------------------------- | -------------------- | --------------------------------------------------------- |
| `scripts/`    | Executable automation that performs specific operations               | When executed        | `helper.py`, `validate.sh`, `build.ts`                    |
| `references/` | Documentation the AI agent reads to inform decisions                  | Yes, when referenced | `api_reference.md`, `schema.md`, `workflow_guide.md`      |
| `assets/`     | **Static files used AS-IS** in output (not modified by the AI agent)  | No                   | `logo.png`, `brand-template.pptx`, `custom-font.ttf`      |
| `templates/`  | **Starter code/scaffolds that the AI agent MODIFIES** and builds upon | Yes, when referenced | `viewer.html` (insert algorithm), `hello-world/` (extend) |

Check out the [structure reference](./references/STRUCTURE.md) for details.

### Referencing Resources in SKILL.md

Use relative paths from the skill root to reference files:

```markdown
## Available Scripts

Run the [helper script](./scripts/helper.py) to automate common tasks.

See [API reference](./references/api_reference.md) for detailed documentation.

Use the [scaffold](./templates/scaffold.py) as a starting point.
```

## Content Guidelines

### Writing Style

- Use imperative mood: "Run", "Create", "Configure" (not "You should run")
- Be specific and actionable
- Include exact commands with parameters
- Show expected outputs where helpful
- Keep sections focused and scannable

### Workflow Requirements

Define multi-step workflows as numbered steps with TODO lists. Format each step to reference relevant resources:

```markdown
1. [ ] **Example simple step** - Optional inline details here
1. [ ] **Example complex step** - See [additional docs](./references/complex_step.md) and run [example script](./scripts/complex_helper.py)
```

This structure enables interruption and resumption of workflows.

### Script Requirements

When including scripts, prefer cross-platform languages, i.e. python or shell scripts.

## Validation Checklist

Before publishing a skill, ensure:

**Frontmatter**

- [ ] `name` is lowercase with hyphens, 1-64 characters, matches directory
- [ ] `description` is 1-1024 characters and non-empty
- [ ] `description` clearly states **WHAT** it does, **WHEN** to use it, and **KEYWORDS**
- [ ] Optional fields (`license`, `compatibility`, `metadata`) are correctly formatted if included

**File Structure**

- [ ] Minimum required: `SKILL.md` with valid frontmatter
- [ ] SKILL.md body kept under 500 lines (split large content to `references/`)
- [ ] Large workflows (>5 steps) in `references/` folder with clear links from SKILL.md
- [ ] Resource directories follow naming: `scripts/`, `references/`, `templates/`, `assets/`

**References & Paths**

- [ ] All relative paths use forward slashes (`./paths/like/this`)
- [ ] No absolute file paths or system-dependent separators
- [ ] Internal links use markdown format: `[text](./path/to/file.md)`

**Scripts**

- [ ] Scripts are self-contained or dependencies clearly documented
- [ ] Cross-platform languages used (Python, Shell-script with checks)
- [ ] Error handling with clear messages included
- [ ] Shebang line present for shell scripts: `#!/bin/bash`

**Security**

- [ ] No hardcoded credentials, API keys, or secrets
- [ ] No system-wide side effects without user consent documented
- [ ] Sensitive operations clearly flagged in descriptions

## Resources

Learn more about agent skills and see working examples:

- **Local Specification** - [Complete Agent Skills Spec](./references/SPEC.md)
- **Structure Guide** - [Directory organization & resource types](./references/STRUCTURE.md)
- **Frontmatter Examples** - [Good vs. poor descriptions](./references/FRONTMATTER.md)
- **Body Structure** - [Recommended sections and format](./references/BODY.md)
- **Official Spec** - [Full specification at agentskills.io](https://agentskills.io/)
- **VS Code Docs** - [Agent Skills in VS Code](https://code.visualstudio.com/docs/copilot/customization/agent-skills)
- **Reference Library** - [Example skills from Anthropic](https://github.com/anthropics/skills)
- **Community Skills** - [Awesome Copilot skills collection](https://github.com/github/awesome-copilot/blob/main/docs/README.skills.md)