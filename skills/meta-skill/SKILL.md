---
name: "meta-skill"
description: "Guidelines for creating high-quality Agent Skills. Use when asked to create, review, or improve AI agent skills, design skill structures, write skill documentation, or understand agent skill best practices and specifications."
license: "MIT"
metadata:
  provenance:
    adaptedFrom: "https://github.com/github/awesome-copilot/blob/main/instructions/agent-skills.instructions.md"
    authoritativeSpec:
      - "https://agentskills.io/"
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
| `name`        | Yes      | Lowercase letters, numbers, and hyphens only. Max 64 chars. Must not start/end with hyphen or contain `--`. Must match parent directory name. No XML tags or reserved words (`anthropic`, `claude`, `copilot`, `openai`). |
| `description` | Yes      | Clear description of capabilities AND use cases, max 1024 characters      |
| `metadata.provenance.mirror` | No | Canonical upstream URL for exact copies |
| `metadata.provenance.adaptedFrom` | No | URL (string) or list of URLs (array) when adapted/synthesised from upstream sources |
| `metadata.provenance.authoritativeSpec` | No | Array of URLs for authoritative format specifications (informational only) |

For consistent provenance tracking, use `metadata.provenance` fields across prompt, instruction, skill, and agent frontmatter.

**Naming conventions:**
- Preferred: gerund form (`processing-pdfs`, `analyzing-data`)
- Acceptable: noun phrases (`pdf-processing`) or action-oriented (`process-pdfs`)
- Avoid: vague names (`helper`, `utils`, `tools`, `documents`)

#### Description Best Practices

**CRITICAL**: The `description` field is the PRIMARY mechanism for automatic skill discovery. The AI Agent reads ONLY the `name` and `description` to decide whether to load a skill. If your description is vague, the skill will never be activated.

**What to include in description:**

1. **WHAT** the skill does (capabilities)
2. **WHEN** to use it (specific triggers, scenarios, file types, or user requests)
3. **Keywords** that users might mention in their prompts

**Additional constraints:**
- Write in third person ("Processes Excel files", not "I can help you process Excel files")
- No XML tags allowed in description
- No reserved words (`anthropic`, `claude`, `copilot`, `openai`)

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

> [!NOTE]
> `templates/` is a **non-standard extension** not in the [official spec](https://agentskills.io/). The spec places template files under `assets/`. Use `templates/` when portability across implementations is not a concern.

For reference files longer than 100 lines, include a table of contents at the top so agents can see the full scope when previewing with partial reads.

Check out the [structure reference](./references/STRUCTURE.md) for details.


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

### Degrees of Freedom

Match the level of prescriptiveness to the task's fragility and variability:

| Freedom    | When to Use                                        | Approach                            |
| ---------- | -------------------------------------------------- | ----------------------------------- |
| **High**   | Multiple valid approaches, context-dependent        | Text-based guidance                 |
| **Medium** | Preferred pattern exists, some variation acceptable | Pseudocode or parameterized scripts |
| **Low**    | Fragile/critical operations, consistency essential  | Exact scripts, no modifications     |

Think of the agent as navigating a path — narrow bridge with cliffs means low freedom (exact instructions); open field means high freedom (general direction).

### Workflow Requirements

Define multi-step workflows as numbered steps with TODO lists. Format each step to reference relevant resources:

```markdown
1. [ ] **Example simple step** - Optional inline details here
1. [ ] **Example complex step** - See [additional docs](./references/complex_step.md) and run [example script](./scripts/complex_helper.py)
```

This structure enables interruption and resumption of workflows.

### Script Requirements

When including scripts, prefer cross-platform languages, i.e. python or shell scripts.

- Handle errors explicitly with clear messages rather than failing and letting the agent figure it out
- Avoid unexplained magic numbers — document why specific values were chosen

## Anti-Patterns

- **"When to Use" sections in the body** — Useless since the body loads only AFTER activation. All trigger info belongs in the `description` field.
- **Too many options** — Provide a default with an escape hatch, not a menu of alternatives.
- **Deeply nested references** — Keep references one level deep from SKILL.md. Agents may partially read nested files.
- **Time-sensitive information** — Avoid "if before date X, use Y". Use a collapsible "old patterns" section instead.
- **Windows-style paths** — Always use forward slashes, even on Windows.
- **Vague file names** — Use descriptive names (`form_validation_rules.md`, not `doc2.md`).

## Validation Checklist

Before publishing a skill, ensure:

**Frontmatter**

- [ ] `name` is lowercase letters, numbers, and hyphens only, 1-64 characters, matches directory
- [ ] `name` does not start/end with hyphen, no consecutive hyphens (`--`)
- [ ] `name` contains no XML tags or reserved words (`anthropic`, `claude`)
- [ ] `description` is 1-1024 characters and non-empty
- [ ] `description` clearly states **WHAT** it does, **WHEN** to use it, and **KEYWORDS**
- [ ] `description` uses third person ("Processes files", not "I process files")
- [ ] `description` contains no XML tags or reserved words (`anthropic`, `claude`)
- [ ] Optional fields (`license`, `compatibility`, `metadata`) are correctly formatted if included

**File Structure**

- [ ] Minimum required: `SKILL.md` with valid frontmatter
- [ ] SKILL.md body kept under 500 lines (split large content to `references/`)
- [ ] Large workflows (>5 steps) in `references/` folder with clear links from SKILL.md
- [ ] Resource directories follow naming: `scripts/`, `references/`, `assets/` (official spec), `templates/` (non-standard extension)

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
- **Authoring Best Practices** - [Official skill authoring guide](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
