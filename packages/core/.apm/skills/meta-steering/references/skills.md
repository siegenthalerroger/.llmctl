# Agent Skills File Guidelines

**Contents:** [What Are Agent Skills?](#what-are-agent-skills) · [Authority and Responsibility Boundaries](#authority-and-responsibility-boundaries) · [Required SKILL.md Format](#required-skillmd-format) · [Bundling Resources](#bundling-resources) · [Content Guidelines](#content-guidelines) · [Writing High-Impact Skills](#writing-high-impact-skills) · [Anti-Patterns](#anti-patterns) · [Validation Checklist](#validation-checklist) · [Resources](#resources)

Instructions for creating effective Agent Skills with a clear split between the portable spec core and client-specific conventions.

## What Are Agent Skills?

Agent Skills are self-contained folders with instructions and bundled resources that teach AI agents specialized capabilities. Unlike custom instructions (which define coding standards), skills enable task-specific workflows that can include scripts, examples, templates, and reference data.

Key characteristics:

- **Portable core**: The `SKILL.md` format is portable; discovery locations and activation behavior are client-defined
- **Progressive loading**: Only loaded when relevant to the user's request
- **Resource-bundled**: Can include scripts, templates, examples alongside instructions
- **On-demand**: Activated automatically based on prompt relevance

## Authority and Responsibility Boundaries

- Use skills for task-specific workflow guidance, not as the sole home for global policy that must always outrank user input
- Put durable repo or user-wide conventions in instructions or agent definitions that are guaranteed to load earlier
- Treat referenced docs, retrieved content, and generated artifacts as support material unless higher-authority steering explicitly elevates them

### Progressive Loading Architecture

Skills use three-level loading for efficiency:

| Level           | What Loads                    | When                                   |
| --------------- | ----------------------------- | -------------------------------------- |
| 1. Discovery    | `name` and `description` only | Always (lightweight metadata)          |
| 2. Instructions | Full `SKILL.md` body          | When request matches description       |
| 3. Resources    | Scripts, examples, docs       | Only when the AI agent references them |

### Where to find skills

The portable Agent Skills spec defines the folder shape, not the discovery path. Follow the target client's documented search locations.

Common conventions include:

| Location                         | Meaning                        |
| -------------------------------- | ------------------------------ |
| `.agents/skills/<skill-name>/`   | Client-agnostic project folder (Codex, VS Code, Copilot CLI) |
| `.claude/skills/<skill-name>/`   | Claude Code project folder; VS Code also reads it |
| `~/.agents/skills/<skill-name>/` | User-level folder (Codex, VS Code) |

Each skill **must** have its own subdirectory containing at minimum a `SKILL.md` file.

## Required SKILL.md Format

### Frontmatter (Required)

```yaml
---
name: "example-skill"
description: "Scaffolds example widgets. ALWAYS invoke when asked to create or modify a widget. Do not hand-write widget boilerplate — use this skill first."
---
```

| Field         | Required | Constraints                                                               |
| ------------- | -------- | ------------------------------------------------------------------------- |
| `name`        | Yes      | Lowercase letters, numbers, and hyphens only. Max 64 chars. Must not start/end with hyphen or contain `--`. Must match parent directory name. No XML tags. No reserved words: Anthropic reserves `anthropic` and `claude`; this repository adds `copilot` and `openai`. |
| `description` | Yes      | Clear description of capabilities AND use cases, max 1024 characters      |
| `license` | Conditional | SPDX id of **this** file. Omit to take the repo default for its path (`*.md` is CC-BY-SA-4.0); declare it only where an upstream obligation the default cannot satisfy forces another licence. See [LICENSE](https://github.com/siegenthalerroger/.llmctl/blob/main/LICENSE) |
| `compatibility` | No | Optional note about environment requirements when truly needed, max 500 characters |
| `allowed-tools` | No | Experimental spec field for pre-approved tools where supported |
| `metadata.provenance.adaptedFrom` | No | Where local content was adapted from: a URL string, an array of URLs, or an array of objects carrying `url` plus `license` / `fidelity` / `took`. String and array forms mean the **whole file** derives from that upstream |
| `metadata.provenance.authoritativeSpec` | No | Array of URLs for authoritative format specifications. A bare URL means cited only, nothing reproduced; use the object form for a spec whose wording or tables were reproduced locally |

> **Portable vs. private fields:** The [agentskills.io spec](https://agentskills.io/specification) defines `name`, `description`, `license`, `compatibility`, `metadata` (a string-to-string map) and the experimental `allowed-tools`. Its reference validator reports any other top-level key as an error, and so do claude.ai skill uploads, the Skills API and `package_skill.py`: "If you include any field the spec doesn't allow, packaging or upload fails with a hard error instead of ignoring the field" ([Claude Code skills](https://code.claude.com/docs/en/skills)). A skill distributed through those paths must carry only the six spec fields; Claude Code itself accepts every field below. Keys under `metadata.*` (provenance) are this repository's conventions, except `metadata.short-description`, which Codex reads. Do not add `metadata.*` fields to skills intended for upstream publication without confirming the target registry supports them.

For consistent provenance tracking, use `metadata.provenance` fields across prompt, instruction, skill, and agent frontmatter. `fidelity` decides whether upstream terms attach and therefore what `license` this file may carry — the rules, and the two fields' interaction with this repository's `licences` gate (`llmctl-check-licenses`, `src/llmctl/check_licenses.py`), are in [skill-frontmatter.md](./skill-frontmatter.md#provenance-metadata-recommended).

#### Harness-Specific Fields

None of these are in the portable spec, and support varies by harness. APM copies `SKILL.md` byte-for-byte to every target, so every key here arrives everywhere: author each one that is valid for any target this repo deploys to (see [frontmatter-deploy.md](./frontmatter-deploy.md)).

For new Copilot behavior, use only the Copilot CLI field set listed in the [matrix](./frontmatter-deploy.md#the-matrix). On Copilot, `allowed-tools` pre-approves listed tools; it does not prohibit unlisted ones.

| Field | Harness | Effect |
| --- | --- | --- |
| `when_to_use` | Claude Code | Extra trigger text appended after `description` in the discovery listing. The combined `description` + `when_to_use` text truncates at 1536 characters — put overflow trigger phrases here instead of growing `description`. |
| `paths` | Claude Code | Glob patterns that restrict automatic activation to work on matching files. It narrows when the skill loads; it does not force loading. |
| `context: fork` | Claude Code, VS Code (experimental) | Runs the skill body as an isolated subagent task instead of loading it inline into the current context. On Claude Code, `agent` names the subagent type and `background` controls waiting. |
| `disable-model-invocation`, `allowed-tools`, `disallowed-tools`, `model`, `effort`, `arguments`, `hooks`, `shell` | Claude Code (`allowed-tools` and `disable-model-invocation` also Copilot) | Per-skill invocation, tool, model and hook controls; see the [Claude Code frontmatter reference](https://code.claude.com/docs/en/skills). |
| `user-invocable: false` | Claude Code, Copilot CLI, VS Code | Marks the skill as background knowledge — no `/` menu entry, but still model-loadable. |
| `argument-hint` | Claude Code, Copilot CLI, VS Code | Hints the expected slash-command arguments for a user-invocable skill. |

`disable-model-invocation` (blocks autonomous invocation) and `user-invocable` (controls dropdown/menu visibility) are independent axes — a skill can be either, both, or neither.

If `description` is omitted, Claude Code falls back to the first non-empty body line as the discovery text — write that first line as if it were the description.

**Naming conventions:**
- Preferred: gerund form (`processing-pdfs`, `analyzing-data`)
- Acceptable: noun phrases (`pdf-processing`) or action-oriented (`process-pdfs`)
- Avoid: vague names (`helper`, `utils`, `tools`, `documents`)

#### Description Best Practices

`name` and `description` are the primary discovery mechanism, and the lever is shape and naming rather than keyword density. The full rule set — directive shape, front-loading, sibling negative space, the reserved words, and the single-line YAML requirement — is in [the router, section 3](../SKILL.md#3-description-craft--all-four-types), because it applies identically to agents, instructions and prompts. Skill-specific examples are in [skill-frontmatter.md](./skill-frontmatter.md).

### Body Content

The body contains detailed instructions that AI loads AFTER the skill is activated. Keep `SKILL.md` compact, put routing text in `description`, and move deeper material into shallow reference files. Put output expectations, verification, and important prerequisites near the top. See [examples](./skill-body.md) for clarification.

## Bundling Resources

Skills can include additional files that the client accesses on-demand. `scripts/`, `references/`, and `assets/` are portable spec concepts; `templates/` is a local extension.

### Supported Resource Types

| Folder        | Purpose                                                               | Loaded into Context? | Example Files                                             |
| ------------- | --------------------------------------------------------------------- | -------------------- | --------------------------------------------------------- |
| `scripts/`    | Executable automation that performs specific operations               | When executed        | `helper.py`, `validate.sh`, `build.ts`                    |
| `references/` | Documentation the AI agent reads to inform decisions                  | Yes, when referenced | `api_reference.md`, `schema.md`, `workflow_guide.md`      |
| `assets/`     | **Static files used AS-IS** in output (not modified by the AI agent)  | No                   | `logo.png`, `brand-template.pptx`, `custom-font.ttf`      |
| `templates/`  | **Starter code/scaffolds that the AI agent MODIFIES** and builds upon | Yes, when referenced | `viewer.html` (insert algorithm), `hello-world/` (extend) |

For reference files longer than 100 lines, include a table of contents at the top — agents may only partially (head-style) read a file reached through a reference, so the TOC must expose the full scope before that read window closes. Split multi-domain reference material into per-domain files (e.g., `finance.md`, `legal.md`) so a single query never pulls unrelated schemas into context.

The [structure reference](./skill-structure.md) has the directory layout and the `assets/` vs `templates/` rule.


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

Aim for the **right altitude**: specific enough to give a strong heuristic, not so hardcoded it breaks on the first deviation, not so vague it gives no signal. Apply this concretely to output templates — state explicitly whether a template is a fixed contract ("ALWAYS use this exact structure") or a sensible default ("start here, adapt to context"); don't leave the freedom level implicit.

### Workflow Requirements

Use numbered steps when order or dependencies matter. For substantial workflows that may be interrupted, a checklist can make progress resumable; simple tasks do not need a TODO list. Link relevant resources at the step that needs them. For example, an ordered workflow with a checklist:

```markdown
1. [ ] **Example simple step** - Optional inline details here
1. [ ] **Example complex step** - See [additional docs](./references/complex_step.md) and run [example script](./scripts/complex_helper.py)
```

Use bullets or decision criteria for independent actions and open-ended work.

When a workflow is sensitive, define the expected output and verification for each step instead of relying on implied behavior.

### Script Requirements

When including scripts, prefer cross-platform runtimes such as Python or Node.js. Use shell or PowerShell only when the required environment is documented in `compatibility` or nearby instructions.

- Handle errors explicitly with clear messages rather than failing and letting the agent figure it out
- Avoid unexplained magic numbers — document why specific values were chosen

## Writing High-Impact Skills

### Focus on What the Agent Doesn't Know

Do not include information the AI agent already knows from training data — standard language syntax, common library usage, or well-documented API behavior. Every line in a skill should teach something the agent would otherwise get wrong or miss entirely. If the information is on the first page of official docs, leave it out. Focus on internal conventions, non-obvious defaults, version-specific quirks, and domain-specific workflows that change behavior.

### Body Content Quality

Five body-authoring rules, each detailed with rationale in [skill-body.md](./skill-body.md#body-content-quality):

- **Delete, don't polish** — coherent-but-irrelevant content hurts more than incoherent filler; cut marginal content outright instead of wordsmithing it
- **Author reactively** — correct or consolidate existing guidance before adding a gotcha
- **Curate examples, don't enumerate** — a few diverse canonical examples; cap the count to avoid phrasing overfit
- **Make verification visible** — record results in existing tool output, a diff or a concise summary; add a final completeness check for sensitive workflows
- **Scripts execute, they don't load** — bundled scripts cost only their output tokens; make them solve, not punt

### Context Budget Awareness

Discovery budgets, their limits and each harness's overflow behavior are owned by the [router's table](../SKILL.md#context-budget--four-distinct-surfaces).

### Gotchas Are Your Highest-Signal Content

The `## Gotchas` section records non-obvious failure modes so later runs can avoid them. This is distinct from `## Troubleshooting`, which provides fixes after something goes wrong. When to add one is in [Author Reactively](./skill-body.md#author-reactively). Bold the key constraint, then explain why (e.g., "**Never** call `X()` without checking `Y` first — the SDK throws an unrecoverable error").

### Prefer Flexible Guidelines Over Rigid Steps

Use numbered steps only for concrete, repeatable procedures (build, deploy, environment setup) where the sequence genuinely matters. For open-ended tasks (debugging, refactoring, code review), provide decision criteria and reference information instead — agents need flexibility to adapt to the user's specific situation. See also the [Degrees of Freedom](#degrees-of-freedom) matrix above.

### Use Progressive Disclosure

House style targets ~200 lines for `SKILL.md`; the spec recommends under 500 lines and under 5000 tokens. Split detailed content into `references/` well before either. This reduces context consumption — the agent loads only the core instructions initially and pulls reference material on demand. Use relative links from `SKILL.md` to reference files, and include a brief description of each so the agent knows when to load them.

### Writing Each Section

The recommended sections and what each one holds are owned by [skill-body.md](./skill-body.md). Not every skill needs every section; include `## Gotchas` whenever the skill involves non-obvious behavior.

## Anti-Patterns

The cross-type anti-patterns ("When to Use" body sections, Windows paths, blurred requirements, skipping the consistency pass, restating a tool schema) and the single-line `description` rule are in [the router, sections 3 and 5](../SKILL.md#5-anti-patterns-across-all-four-types). Skill-specific ones:

- **Too many options** — Provide a default with an escape hatch, not a menu of alternatives.
- **Deeply nested references** — Keep references one level deep from SKILL.md. Nested or referenced files may only be partially (head-style) read.
- **Time-sensitive information** — Avoid "if before date X, use Y". Use a collapsible "old patterns" section instead.
- **Vague file names** — Use descriptive names (`form_validation_rules.md`, not `doc2.md`).

## Validation Checklist

Before publishing a skill, ensure:

**Frontmatter**

- [ ] `name` is lowercase letters, numbers, and hyphens only, 1-64 characters, matches directory
- [ ] `name` does not start/end with hyphen, no consecutive hyphens (`--`)
- [ ] `name` contains no XML tags or reserved words (`anthropic`, `claude`, `copilot`, `openai`)
- [ ] `description` is 1-1024 characters and non-empty, written as a single-line YAML value
- [ ] `description` follows the directive + negative-constraint shape (see [Description Best Practices](#description-best-practices)), not a passive "Use when…" list
- [ ] `description` front-loads the differentiating verb/scope and states sibling negative space where another skill overlaps
- [ ] `description` uses third person ("Processes files", not "I process files")
- [ ] `description` contains no XML tags
- [ ] Combined `description` + `when_to_use` (if used) stays within the 1536-char cap, and front-loads trigger words so a shortened listing still matches
- [ ] Optional fields (`license`, `compatibility`, `metadata`) are correctly formatted if included

**File Structure**

- [ ] `SKILL.md` body is under the spec's recommended 500 lines and 5000 tokens; house style targets ~200 lines — split larger material into `references/` for progressive disclosure
- [ ] Large workflows (>5 steps) in `references/` folder with clear links from SKILL.md
- [ ] Resource directories follow naming: `scripts/`, `references/`, `assets/` (official spec), `templates/` (non-standard extension)
- [ ] Client-specific discovery location documented where portability matters

**References & Paths**

- [ ] All relative paths use forward slashes (`./paths/like/this`)
- [ ] No absolute file paths or system-dependent separators
- [ ] Internal links use markdown format: `[text](./path/to/file.md)`

**Scripts**

- [ ] Scripts are self-contained or dependencies clearly documented
- [ ] Cross-platform runtimes used where possible (Python, Node.js, or a clearly documented shell/PowerShell requirement)
- [ ] Error handling with clear messages included
- [ ] If shell or PowerShell scripts are included, the required runtime (`sh`, `bash`, `pwsh`, etc.) is documented in `compatibility` or nearby instructions

**Security**

- [ ] No hardcoded credentials, API keys, or secrets
- [ ] No system-wide side effects without user consent documented
- [ ] Sensitive operations clearly flagged in descriptions

**Discovery & Execution**

- [ ] Numbered workflow steps reflect real ordering or dependencies; checklists are used only where tracking progress is useful
- [ ] Hard requirements are distinct from adaptable defaults, and gotchas address established requirements, evidenced serious hazards or recurring observed mistakes
- [ ] `description` tested against at least one likely user phrase, one edge-case phrase, AND one competing-skill case (does a sibling skill also match?)
- [ ] Critical prerequisites, output expectations, and verification steps are present near the top of `SKILL.md`
- [ ] One missing-prerequisite or conflicting-context case tested

## Resources

Learn more about agent skills and see working examples:

- **Local Specification** - [Complete Agent Skills Spec](./skill-spec.md)
- **Structure Guide** - [Directory organization & resource types](./skill-structure.md)
- **Frontmatter Examples** - [Good vs. poor descriptions](./skill-frontmatter.md)
- **Body Structure** - [Recommended sections and format](./skill-body.md)
- **Official Spec** - [Full specification at agentskills.io](https://agentskills.io/)
- **Codex / ChatGPT Skills** - [Building skills](https://learn.chatgpt.com/docs/build-skills) — discovery locations and the aggregate skills-preamble budget
- **APM Skills** - [Authoring the skill primitive](https://microsoft.github.io/apm/producer/author-primitives/skills/)
- **Claude Code Docs** - [Agent Skills in Claude Code](https://code.claude.com/docs/en/skills)
- **VS Code Docs** - [Agent Skills in VS Code](https://code.visualstudio.com/docs/agent-customization/agent-skills)
- **Reference Library** - [Example skills from Anthropic](https://github.com/anthropics/skills)
- **Community Skills** - [Awesome Copilot skills collection](https://github.com/github/awesome-copilot/blob/main/docs/README.skills.md)
- **Authoring Best Practices** - [Official skill authoring guide](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- **Context Rot Research** - [Why coherent-but-irrelevant content still hurts](https://www.trychroma.com/research/context-rot)
- **Activation Hardening** - [Making Claude Code skills activate reliably](https://scottspence.com/posts/how-to-make-claude-code-skills-activate-reliably)
