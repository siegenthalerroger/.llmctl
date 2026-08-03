---
name: "meta-skill"
description: "Guidelines and specifications for authoring high-quality Agent Skills (SKILL.md, frontmatter, references, scripts). ALWAYS invoke when creating, reviewing, or improving an AI agent skill, designing skill structure, writing a skill description, or auditing skill discovery and activation behavior. Do not write or edit a SKILL.md file, its frontmatter, or its references/ folder without first loading this skill. Keywords: skill, SKILL.md, agent skill, frontmatter, description, references, progressive disclosure."
metadata:
  provenance:
    adaptedFrom:
      - url: "https://github.com/github/awesome-copilot/blob/main/instructions/agent-skills.instructions.md"
        license: MIT
        fidelity: structural-echo
        took: "The section skeleton for a skill-authoring guide."
    authoritativeSpec:
      - "https://agentskills.io/"
      - "https://code.claude.com/docs/en/skills"
      - "https://code.visualstudio.com/docs/agent-customization/agent-skills"
---

# Agent Skills File Guidelines

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
| `.agents/skills/<skill-name>/`   | Client-agnostic project folder |
| `~/.llmctl/skills/<skill-name>/` | Personal skill library         |

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
| `license` | Conditional | SPDX id of **this** file. Omit to take the repo default for its path (`*.md` is CC-BY-SA-4.0); declare it only where an upstream obligation the default cannot satisfy forces another licence. See [LICENSE](../../../../../LICENSE) |
| `compatibility` | No | Optional note about environment requirements when truly needed, max 500 characters |
| `allowed-tools` | No | Experimental spec field for pre-approved tools where supported |
| `metadata.provenance.adaptedFrom` | No | Where local content was adapted from: a URL string, an array of URLs, or an array of objects carrying `url` plus `license` / `fidelity` / `took`. String and array forms mean the **whole file** derives from that upstream |
| `metadata.provenance.authoritativeSpec` | No | Array of URLs for authoritative format specifications. A bare URL means cited only, nothing reproduced; use the object form for a spec whose wording or tables were reproduced locally |

> **Portable vs. private fields:** Only `name`, `description`, and `license` are part of the [agentskills.io](https://agentskills.io/) spec. Everything under `metadata.*` (provenance, modelProfile) is a **private convention** of this repository — other tools and consumers safely ignore it. Do not add `metadata.*` fields to skills intended for upstream publication without confirming the target registry supports them.

For consistent provenance tracking, use `metadata.provenance` fields across prompt, instruction, skill, and agent frontmatter. `fidelity` decides whether upstream terms attach and therefore what `license` this file may carry — the rules, and the two fields' interaction with `scripts/check-licenses.py`, are in [references/FRONTMATTER.md](./references/FRONTMATTER.md#provenance-metadata-recommended).

#### Harness-Specific Fields

None of these are in the portable spec — support varies by harness. Verify against current target docs before relying on them.

| Field | Harness | Effect |
| --- | --- | --- |
| `when_to_use` | Claude Code | Extra trigger text appended after `description` in the discovery listing. The combined `description` + `when_to_use` text truncates at 1536 characters — put overflow trigger phrases here instead of growing `description`. |
| `paths` | Claude Code | Glob patterns that auto-load the skill when a matching file is open — a structural trigger that complements description text. |
| `context: fork` | VS Code | Runs the skill body as an isolated subagent task instead of loading it inline into the current context. |
| `user-invocable: false` | Claude Code, VS Code | Marks the skill as background knowledge — no `/` menu entry, but still model-loadable. |
| `argument-hint` | Claude Code, VS Code | Hints the expected slash-command arguments for a user-invocable skill. |

`disable-model-invocation` (blocks autonomous invocation) and `user-invocable` (controls dropdown/menu visibility) are independent axes — a skill can be either, both, or neither.

If `description` is omitted, Claude Code falls back to the first body paragraph as the discovery text — write that paragraph as if it were the description.

**Naming conventions:**
- Preferred: gerund form (`processing-pdfs`, `analyzing-data`)
- Acceptable: noun phrases (`pdf-processing`) or action-oriented (`process-pdfs`)
- Avoid: vague names (`helper`, `utils`, `tools`, `documents`)

#### Description Best Practices

**CRITICAL**: `name` and `description` are the PRIMARY mechanism for automatic skill discovery — the AI Agent reads ONLY these to decide whether to load a skill. But the lever that matters is **shape and naming, not keyword density**: a 650-trial Claude Code activation study found keyword density had "zero measurable effect," while directive phrasing with an explicit negative constraint was ~20x more likely to trigger (OR=20.6, p<0.0001). Passive "Use when…" phrasing caps at ~77–87% activation and collapses to ~37% under competing skills.

1. **Invest in the name first.** A discriminating, purpose-revealing name (`processing-invoices`, not `helper`) is the cheapest routing lever — treat `description` as the secondary disambiguator.
2. **Shape the description as a directive with a negative constraint**, not a passive capability list:

   ```
   <What it does/domain>. ALWAYS invoke when <concrete triggers>. Do not <the default action the model would otherwise take> — use this skill first.
   ```

3. **Front-load** the differentiating verb and scope — the discovery entry may be truncated, so it must still work as a match when only the first part is read.
4. **Keywords are coverage, not density.** List the concrete words a user would say inside the trigger clause; don't pad the text with synonyms hoping for a match.
5. **Sibling negative space.** When two skills overlap, state what each does NOT cover — overlapping descriptions make the model invoke every match or hesitate to invoke any.
6. Write in third person, active voice, present tense; spell out acronyms — the description is injected verbatim into the system prompt.
7. No XML tags, no reserved words (`anthropic`, `claude`, `copilot`, `openai`).
8. Autonomous triggering is probabilistic. For anything that must fire, pair the description with an explicit-invocation path (slash command, `Skill(name)` mention, path-scoped rule, or hook) rather than adding more descriptive prose.

See examples in the [reference file](./references/FRONTMATTER.md) for clarification.

### Body Content

The body contains detailed instructions that AI loads AFTER the skill is activated. Keep `SKILL.md` compact, put routing text in `description`, and move deeper material into shallow reference files. Put output expectations, verification, and important prerequisites near the top. See [examples](./references/BODY.md) for clarification.

## Bundling Resources

Skills can include additional files that the client accesses on-demand. `scripts/`, `references/`, and `assets/` are portable spec concepts; `templates/` is a local extension.

### Supported Resource Types

| Folder        | Purpose                                                               | Loaded into Context? | Example Files                                             |
| ------------- | --------------------------------------------------------------------- | -------------------- | --------------------------------------------------------- |
| `scripts/`    | Executable automation that performs specific operations               | When executed        | `helper.py`, `validate.sh`, `build.ts`                    |
| `references/` | Documentation the AI agent reads to inform decisions                  | Yes, when referenced | `api_reference.md`, `schema.md`, `workflow_guide.md`      |
| `assets/`     | **Static files used AS-IS** in output (not modified by the AI agent)  | No                   | `logo.png`, `brand-template.pptx`, `custom-font.ttf`      |
| `templates/`  | **Starter code/scaffolds that the AI agent MODIFIES** and builds upon | Yes, when referenced | `viewer.html` (insert algorithm), `hello-world/` (extend) |

> [!NOTE]
> `templates/` is a **non-standard extension** not in the [official spec](https://agentskills.io/). The spec places template files under `assets/`. Use `templates/` when portability across implementations is not a concern.

For reference files longer than 100 lines, include a table of contents at the top — agents may only partially (head-style) read a file reached through a reference, so the TOC must expose the full scope before that read window closes. Split multi-domain reference material into per-domain files (e.g., `finance.md`, `legal.md`) so a single query never pulls unrelated schemas into context.

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

Aim for the **right altitude**: specific enough to give a strong heuristic, not so hardcoded it breaks on the first deviation, not so vague it gives no signal. Apply this concretely to output templates — state explicitly whether a template is a fixed contract ("ALWAYS use this exact structure") or a sensible default ("start here, adapt to context"); don't leave the freedom level implicit.

### Workflow Requirements

Define multi-step workflows as numbered steps with TODO lists. Format each step to reference relevant resources:

```markdown
1. [ ] **Example simple step** - Optional inline details here
1. [ ] **Example complex step** - See [additional docs](./references/complex_step.md) and run [example script](./scripts/complex_helper.py)
```

This structure enables interruption and resumption of workflows.

When a workflow is sensitive, define the expected output and verification for each step instead of relying on implied behavior.

### Script Requirements

When including scripts, prefer cross-platform runtimes such as Python or Node.js. Use shell or PowerShell only when the required environment is documented in `compatibility` or nearby instructions.

- Handle errors explicitly with clear messages rather than failing and letting the agent figure it out
- Avoid unexplained magic numbers — document why specific values were chosen

## Writing High-Impact Skills

### Focus on What the Agent Doesn't Know

Do not include information the AI agent already knows from training data — standard language syntax, common library usage, or well-documented API behavior. Every line in a skill should teach something the agent would otherwise get wrong or miss entirely. If the information is on the first page of official docs, leave it out. Focus on internal conventions, non-obvious defaults, version-specific quirks, and domain-specific workflows that change behavior.

### Body Content Quality

Five body-authoring rules, each detailed with rationale in [references/BODY.md](./references/BODY.md#body-content-quality):

- **Delete, don't polish** — coherent-but-irrelevant content hurts more than incoherent filler; cut marginal content outright instead of wordsmithing it
- **Author reactively** — promote a rule into the skill only after the same mistake recurs
- **Curate examples, don't enumerate** — a few diverse canonical examples; cap the count to avoid phrasing overfit
- **Make verification visible** — checks must emit an output artifact; add a final self-evaluation gate for sensitive workflows
- **Scripts execute, they don't load** — bundled scripts cost only their output tokens; make them solve, not punt

### Context Budget Awareness

Description text is budgeted at four distinct surfaces — know which one applies before trimming:

| Budget | Surface | Failure mode past the limit |
| --- | --- | --- |
| 1024 chars | Per-skill `description` field (agentskills.io spec limit) | Field is invalid |
| 1536 chars | Claude Code: combined `description` + `when_to_use` in the discovery listing | Overflow text is truncated |
| 8000 chars | Codex: aggregate skills-preamble across ALL installed skills | Later skills in the preamble get cut |
| ~15,000 chars (~4000 tokens) | Claude Code: TOTAL name+description budget for the injected skills list | Skills below the cutoff are **invisible**, not down-ranked |

The last row is the one that matters most: past the total budget, excess skills simply never get considered — pruning unused skills helps more than trimming one description. Claude Code exposes `SLASH_COMMAND_TOOL_CHAR_BUDGET` to raise this ceiling when many skills are installed. Regardless of budget, every description still competes with every other installed skill's description for the same space — keep it as short as the directive shape (above) allows.

### Gotchas Are Your Highest-Signal Content

The `## Gotchas` section is consistently the most valuable part of any skill — proactive warnings that prevent mistakes before they happen. This is distinct from `## Troubleshooting`, which provides reactive fixes after something goes wrong. Treat gotchas as a living section: every time the agent produces a wrong result, add a gotcha. Bold the key constraint, then explain why (e.g., "**Never** call `X()` without checking `Y` first — the SDK throws an unrecoverable error").

### Prefer Flexible Guidelines Over Rigid Steps

Use numbered steps only for concrete, repeatable procedures (build, deploy, environment setup) where the sequence genuinely matters. For open-ended tasks (debugging, refactoring, code review), provide decision criteria and reference information instead — agents need flexibility to adapt to the user's specific situation. See also the [Degrees of Freedom](#degrees-of-freedom) matrix above.

### Use Progressive Disclosure

House style targets ~200 lines for `SKILL.md`; the upstream authoritative ceiling is looser but hard — under 500 lines AND under 5000 tokens, both must hold. Split detailed content into `references/` well before hitting either limit. This reduces context consumption — the agent loads only the core instructions initially and pulls reference material on demand. Use relative links from `SKILL.md` to reference files, and include a brief description of each so the agent knows when to load them.

### Writing Each Section

- **`# Title`** — One sentence stating what the skill enables. Be specific about the domain.
- **`## When to Use This Skill`** — Bullet list of concrete scenarios that reinforce the description triggers. Helps the agent confirm it loaded the right skill.
- **`## Prerequisites`** — Only include if the skill requires tools, services, or configuration that cannot be assumed. List exact install commands.
- **`## Step-by-Step Workflows`** — Numbered steps for repeatable procedures where sequence matters. Describe WHAT to accomplish at each stage, not hardcoded file paths — steps should adapt to different project structures. For complex workflows (>5 steps), split into `references/` files.
- **`## Gotchas`** — Proactive warnings. Bold the key constraint, then explain why.
- **`## Troubleshooting`** — Reactive fixes as a symptom → solution table.
- **`## References`** — Links to bundled docs in `references/`, external documentation, or related skills.

Not every skill needs every section. Skip `## Prerequisites` if there are no external dependencies. Skip `## Step-by-Step Workflows` if the skill is purely advisory. Include `## Gotchas` whenever the skill involves non-obvious behavior.

## Anti-Patterns

- **"When to Use" sections in the body** — Useless since the body loads only AFTER activation. All trigger info belongs in the `description` field.
- **Too many options** — Provide a default with an escape hatch, not a menu of alternatives.
- **Deeply nested references** — Keep references one level deep from SKILL.md. Nested or referenced files may only be partially (head-style) read.
- **Time-sensitive information** — Avoid "if before date X, use Y". Use a collapsible "old patterns" section instead.
- **Windows-style paths** — Always use forward slashes, even on Windows.
- **Vague file names** — Use descriptive names (`form_validation_rules.md`, not `doc2.md`).
- **Multi-line YAML `description:`** — Spec-valid but can silently register as invisible to the Claude Code loader. Keep `description` on a single line.
- **Soft-permission phrasing** — "Prefer X, but Y if simpler" erodes hard constraints. Grep for "but … if" and "unless … makes more sense"; replace with binary rules.
- **Skipping the consistency pass** — Newer, more literal-following models are MORE damaged by contradictory instructions, not less. Review the skill for internal contradictions before shipping.
- **Restating the tool schema** — Don't re-describe what a tool's own schema already declares; it interferes with autonomous tool selection.

## Validation Checklist

Before publishing a skill, ensure:

**Frontmatter**

- [ ] `name` is lowercase letters, numbers, and hyphens only, 1-64 characters, matches directory
- [ ] `name` does not start/end with hyphen, no consecutive hyphens (`--`)
- [ ] `name` contains no XML tags or reserved words (`anthropic`, `claude`)
- [ ] `description` is 1-1024 characters and non-empty, written as a single-line YAML value
- [ ] `description` follows the directive + negative-constraint shape (see [Description Best Practices](#description-best-practices)), not a passive "Use when…" list
- [ ] `description` front-loads the differentiating verb/scope and states sibling negative space where another skill overlaps
- [ ] `description` uses third person ("Processes files", not "I process files")
- [ ] `description` contains no XML tags or reserved words (`anthropic`, `claude`)
- [ ] Combined `description` + `when_to_use` (if used) stays within the 1536/15,000-char discovery budgets
- [ ] Optional fields (`license`, `compatibility`, `metadata`) are correctly formatted if included

**File Structure**

- [ ] `SKILL.md` body is under 500 lines AND under 5000 tokens (hard ceiling); house style targets ~200 lines — split larger material into `references/` for progressive disclosure
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

- [ ] `description` tested against at least one likely user phrase, one edge-case phrase, AND one competing-skill case (does a sibling skill also match?)
- [ ] Critical prerequisites, output expectations, and verification steps are present near the top of `SKILL.md`
- [ ] One missing-prerequisite or conflicting-context case tested

## Resources

Learn more about agent skills and see working examples:

- **Local Specification** - [Complete Agent Skills Spec](./references/SPEC.md)
- **Structure Guide** - [Directory organization & resource types](./references/STRUCTURE.md)
- **Frontmatter Examples** - [Good vs. poor descriptions](./references/FRONTMATTER.md)
- **Body Structure** - [Recommended sections and format](./references/BODY.md)
- **Official Spec** - [Full specification at agentskills.io](https://agentskills.io/)
- **Claude Code Docs** - [Agent Skills in Claude Code](https://code.claude.com/docs/en/skills)
- **VS Code Docs** - [Agent Skills in VS Code](https://code.visualstudio.com/docs/agent-customization/agent-skills)
- **Reference Library** - [Example skills from Anthropic](https://github.com/anthropics/skills)
- **Community Skills** - [Awesome Copilot skills collection](https://github.com/github/awesome-copilot/blob/main/docs/README.skills.md)
- **Authoring Best Practices** - [Official skill authoring guide](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- **Context Rot Research** - [Why coherent-but-irrelevant content still hurts](https://www.trychroma.com/research/context-rot)
- **Activation Hardening** - [Making Claude Code skills activate reliably](https://scottspence.com/posts/how-to-make-claude-code-skills-activate-reliably)
