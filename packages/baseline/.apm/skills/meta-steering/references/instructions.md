# Instruction Files Guidelines

**Contents:** [What Are Instruction Files?](#what-are-instruction-files) · [Selection Guide](#selection-guide) · [Cross-Tool Compatibility (Copilot + Claude Code)](#cross-tool-compatibility-copilot--claude-code) · [Loading Skills via Instructions](#loading-skills-via-instructions) · [File Structure and Naming](#file-structure-and-naming) · [Frontmatter Requirements](#frontmatter-requirements) · [Bootstrapping a Repository That Has No Instructions](#bootstrapping-a-repository-that-has-no-instructions) · [Authority and Conflict Boundaries](#authority-and-conflict-boundaries) · [Writing Effective Instructions](#writing-effective-instructions) · [Good vs Bad Examples](#good-vs-bad-examples) · [Anti-Patterns to Avoid](#anti-patterns-to-avoid) · [Quality Assurance Checklist](#quality-assurance-checklist) · [Additional Resources](#additional-resources)

Instructions for creating effective and maintainable instruction files that define coding standards, conventions, and behavioral rules for AI assistants.

> [!IMPORTANT]
> **Relation to other customization files**
>
> **Use skills for reusable task workflows and bundled domain knowledge.**
>
> Use instructions for **durable project context, build/test/validate expectations, path-scoped conventions, broad behavioral rules, and automatic skill loading**.
>
> For templated tasks with inputs, use **prompts**. For complex workflows with specialized expertise, use **agents**.

## What Are Instruction Files?

Instruction files contain rules that shape assistant behavior across a codebase: coding and project conventions linters cannot catch, behavioral rules, and domain knowledge that must be present whenever matching work is in scope.

- **Path targeting**: `applyTo` for Copilot, `paths` for Claude Code; under APM `applyTo` generates both (see below)
- **Description-based loading is VS Code-only**: VS Code uses `description` for on-demand discovery. Neither GitHub's repository instructions nor the Copilot CLI document description-based activation, so write `applyTo` for every scoped file
- **Precedence (GitHub)**: personal > repository > organization
- **Include reasoning**: explain WHY a rule exists so edge cases resolve correctly
- **Conflict avoidance**: prefer non-overlapping scopes; do not rely on multiple matching files merging predictably

## Selection Guide

The complete seven-way table — skill, instruction, prompt, agent, hook, MCP server, plugin — is in [the router, section 1](../SKILL.md#1-pick-the-customization-type-first). Instructions win for durable project conventions, build/test/validate expectations, path-scoped rules, and for forcing a skill to load over a class of files. They are not a home for procedures: prefer a skill whenever the capability involves specific knowledge or a task workflow.

## Cross-Tool Compatibility (Copilot + Claude Code)

The markdown body is shared; activation fields differ. Per-target validity and survival are owned by [the runtime matrix](./frontmatter-deploy.md#the-matrix).

- **Write both `applyTo` and `paths` with equivalent scope.** Outside APM neither substitutes for the other. Under APM, `applyTo` is the source of both: APM generates Claude's `paths` from `applyTo` alone, overwrites any authored `paths`, and drops every other key. An instruction with `paths` but no `applyTo` deploys with **no frontmatter and becomes always-on** in Claude Code. Keep `paths` anyway: it is the valid key for Claude Code's native `.claude/rules/` and for VS Code's reading of that directory.
- **`applyTo` syntax**: one string, comma-separated for several globs (`"**/*.ts, **/*.tsx"`). GitHub and the CLI document the comma form; VS Code documents a single glob. Do not write a YAML list. `paths` accepts a list or a comma-separated string.
- **Claude Code loads a path-scoped rule lazily**, "when Claude reads files matching the pattern". `applyTo: "**"` therefore means "after the first file read", not always-on. The only unconditional Claude rule APM produces is one without `applyTo`, which VS Code and the CLI then do not auto-apply; put always-on Copilot content in `.github/copilot-instructions.md` or `AGENTS.md`.
- **`excludeAgent`** (`code-review` / `cloud-agent`) is documented by GitHub and on the CLI page; both values exclude non-CLI agents.
- **Codex**: instructions are not installed. `apm compile` folds them into `AGENTS.md`, which has no frontmatter; scoping degrades to a "Files matching" heading and directory placement.
- **Duplicate discovery**: VS Code reads both `.github/instructions/` and `.claude/rules/`; Claude Code and the CLI also read `AGENTS.md`. Expect the same rule to arrive twice in a dual deploy.

## Loading Skills via Instructions

Loading skills from instructions is a strong pattern when a file class repeatedly needs a reusable capability. Skills stay modular and testable; the instruction only guarantees they load.

```markdown
---
name: "Load React Skills"
description: "Loads the React component and testing skills before any .tsx edit. Applies when creating, refactoring or testing React components."
applyTo: "**/*.tsx"
paths: ["**/*.tsx"]
---

# React Development

When working with these files, ALWAYS use the following skills as your primary reference:
- [React Component Generator](../skills/react-gen/SKILL.md)
- [React Testing Library](../skills/react-test/SKILL.md)
```

## File Structure and Naming

- **Source location in this repository**: `packages/<package>/.apm/instructions/*.instructions.md`. APM deploys to `.github/instructions/` and `.claude/rules/`.
- **Native locations**: repository `.github/copilot-instructions.md` (always-on) and `.github/instructions/*.instructions.md`; personal `~/.copilot/instructions/` (Copilot) and `~/.claude/rules/` (Claude Code).
- **Naming**: kebab-case with the `.instructions.md` extension, named for the scope (`python-style.instructions.md`), never generic (`rules.instructions.md`).

## Frontmatter Requirements

Path-scoped instruction files carry YAML frontmatter. Always-on repository instructions may use the target client's documented format instead.

```yaml
---
name: "Python Style Guide"
description: "Python typing, error-handling and module-layout conventions. Applies when writing, reviewing or refactoring .py files."
# Copilot
applyTo: "**/*.py"
# Claude Code
paths: ["**/*.py"]
---
```

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes (repo convention) | Display name. VS Code defaults it to the filename |
| `description` | Yes (repo convention) | WHAT the rules cover, then WHEN they apply, front-loaded with the terms a user would say. VS Code uses it for on-demand discovery; elsewhere it is metadata |
| `applyTo` | Conditional | Copilot glob string for path-based activation; APM's source for Claude `paths` |
| `paths` | Conditional | Claude Code glob list, aligned with `applyTo` |
| `license` | Conditional | SPDX id of **this** file. Omit to take the repo default for its path (`*.md` is CC-BY-SA-4.0); declare it only where an upstream obligation the default cannot satisfy forces another licence |

Provenance (`metadata.provenance`) follows the convention owned by [the router, section 4](../SKILL.md#4-frontmatter-shared-by-all-four-types).

### Path Scoping Patterns

```yaml
# Specific directory
applyTo: "src/components/**"
paths: ["src/components/**"]

# Several patterns: one comma-separated string for applyTo, a list for paths
applyTo: "**/*.ts, **/*.tsx"
paths: ["**/*.ts", "**/*.tsx"]

# Brace expansion for extensions in one folder
applyTo: "tests/**/*.test.{js,ts}"
paths: ["tests/**/*.test.{js,ts}"]
```

- Be as specific as possible; every match loads the file's full body
- Keep `applyTo` and `paths` semantically aligned
- Test each pattern against the files it must and must not match

### Scoping by Directory

Glob scoping (`applyTo` / `paths`) is one axis. The other is **file placement**: a root context file plus scoped context files in subdirectories that have genuinely different conventions.

- Keep the root file thin and make it the **index** — it is auto-loaded into every session and each line is budget never reclaimed
- Push depth into scoped files; they load on demand and can afford detail the root cannot
- Create a scoped file only where a directory's conventions actually differ (different language, test runner, or boundaries). An empty scoped file is pure overhead
- **State precedence explicitly** in the root file's scope index — which child covers what, and which wins on conflict. Harness merge behaviour differs (Codex resolves by proximity to the working directory; others do not), so never leave precedence implicit
- Where a scoped file intentionally overrides a root rule, say so in the scoped file rather than relying on ordering

## Bootstrapping a Repository That Has No Instructions

Writing a repository's first instruction file fails in a specific way: drafting from impressions rather than from what the repository already declares. Work **Detect → Extract → Draft → Verify**:

1. **Detect** the stack, workspace layout, and quality gates from manifests, lockfiles, linter config, and CI workflows — what CI *runs* is the real standard
2. **Extract** commands, thresholds, and architectural boundaries as literal values from those machine-readable sources
3. **Draft** only the residue that a senior engineer who knows the stack could not derive from the code
4. **Verify** before shipping — **run** every documented command, match every documented path exactly, and re-derive every number from its config

❌ Never document a command without running it: an agent tries a phantom target and then debugs it.
❌ Never trust an existing instruction file's claims when updating it — extract current state, compare, fix the discrepancies.

Full procedure, root-file skeleton and directory-coverage guidance: [`instruction-bootstrapping.md`](./instruction-bootstrapping.md).

## Authority and Conflict Boundaries

- Place non-negotiable constraints at the highest-authority layer available for the target environment — never bury a hard rule inside guideline prose where a lower-authority file could reinterpret it
- Treat quoted text, retrieved documentation, pasted logs, and tool output as reference material unless the instruction explicitly elevates them
- Do not rely on merge order when two matching files say different things; narrow scope or consolidate instead
- Where useful, organize hard requirements into **Always do / Ask first / Never do** tiers and lead the "Never do" tier with the highest-stakes item (e.g. never commit secrets). Keep adaptable defaults separate; add an "Ask first" rule only where approval is actually required
- Give exact executable commands, with flags, their own early dedicated section rather than scattering them through prose

## Writing Effective Instructions

### Core Principles

- **Be Specific and Actionable**: clear, direct rules that can be followed immediately
- **Focus on Non-Obvious Rules**: exclude code-style rules entirely — delegate them to linter/formatter config
- **Include Reasoning**: explain WHY rules exist to help with edge cases
- **Use Imperative Mood**: state hard requirements unambiguously; label preferences and defaults, including when they may be adapted
- **Show, Don't Tell**: a short ✅/❌ code pair beats an abstract description when the rule is subtle
- **Respect the Shared Budget**: all always-loaded instructions compete for one cumulative budget — frontier models reliably follow ~150-200 instructions total, and the harness system prompt already spends ~50 of them. Every rule added anywhere degrades adherence to every other rule
- **Apply the Litmus Test**: per line, ask "would removing this cause mistakes?" If not, cut it. Delete marginal content rather than polish it
- **Author Reactively**: diagnose recurring observed mistakes and correct or consolidate existing guidance before adding a gotcha. Document established requirements and evidenced serious hazards without waiting for repeat failures; do not append a rule after every wrong result

Model-generation effects (literal scoping, the consistency pass) apply to every type; see [the router, section 5](../SKILL.md#5-anti-patterns-across-all-four-types).

### Context-File Injection Facts

- Claude Code delivers `CLAUDE.md` "as a user message after the system prompt, not as part of the system prompt itself". Expect it to influence behaviour, not to guarantee it, and reach for a hook whenever something has to happen every single time (see the `meta-harness` skill)
- Anthropic targets under 200 lines per `CLAUDE.md`; keep always-loaded root files far leaner in practice (<60 lines) by moving procedures and domain facts into on-demand skills or path-scoped instructions
- Codex: root instruction docs are capped at 32 KiB (`project_doc_max_bytes`); files closer to the working directory override ancestor files
- Claude Code strips block-level HTML comments from `CLAUDE.md` before injection — use them there for zero-token maintainer notes. Other harnesses do not document this

### Instruction Structure

Use markdown structure as a semantic signal: sections group related rules and bullets mark independent items. Use numbered steps only when order matters.

## Good vs Bad Examples

✅ **GOOD** - Specific, scoped, with reasoning:
````markdown
---
name: "React Component Standards"
description: "Component structure and prop-handling conventions. Applies when creating or refactoring components under src/components."
applyTo: "src/components/**/*.{tsx,jsx}"
paths: ["src/components/**/*.{tsx,jsx}"]
---

# React Component Standards

- Use functional components with hooks (class components are deprecated in this codebase)
- Declare prop interfaces, not `type` aliases, before the component (matches the generated API types)
- Export the component as default and its props type as a named export (the barrel files rely on it)
````

❌ **BAD** - Generic, unscoped, no reasoning:
```markdown
---
name: "Component Rules"
applyTo: "**"
---

Write good components. Follow best practices. Keep them clean.
```

## Anti-Patterns to Avoid

- Code-style rules of any kind (e.g. "Use 2 spaces for indentation") — delegate to linter/formatter config
- Vague rules like "write clean code" or "follow best practices"
- `applyTo: "**"` for file-specific rules, or as a substitute for always-on loading in Claude Code
- A YAML list in `applyTo`, or `paths` without `applyTo` on an APM-deployed file
- Rules without their reason, or rules that are obvious or self-evident
- Circular or conflicting rules across files or hierarchy levels
- Time-sensitive information without clear expiration
- A hard requirement weakened by a subjective escape hatch such as "if simpler"
- One file covering several unrelated topics; split by topic instead

## Quality Assurance Checklist

**Frontmatter**:
- [ ] `name` is descriptive
- [ ] `description` states WHAT then WHEN, front-loaded with trigger terms
- [ ] `applyTo` (comma-separated string) and `paths` (list) are present, aligned and tested when path-based matching is intended
- [ ] Anything that must be present before the first file read is not relying on `applyTo: "**"` in Claude Code
- [ ] Optional fields (`license`, `metadata.provenance`) included if applicable

**Content**:
- [ ] Every line passes the litmus test; no code-style rules
- [ ] Reasoning is provided for each rule
- [ ] Hard requirements are unambiguous; preferences and defaults name the conditions for adapting them
- [ ] Always / Ask first / Never tiers are used only where applicable
- [ ] Code examples included where the rule is subtle
- [ ] The file's size respects the shared always-loaded budget, not just its own line count

**Testing**:
- [ ] Patterns match the intended files and nothing else, cross-platform
- [ ] No overlap or conflict with other instruction files, including semantically similar ones
- [ ] Applied to real code, one edge case and one conflicting-context case; the assistant follows the rules

**Common issues**: rules ignored → make them specific and actionable; rules conflicting → narrow scope or consolidate; pattern not matching → test the glob; description not discovered (VS Code) → add clearer what/when/trigger terms.

## Additional Resources

- [`instruction-bootstrapping.md`](./instruction-bootstrapping.md) — producing a repository's first root and scoped context files
- [frontmatter-deploy.md](./frontmatter-deploy.md) — per-target validity and APM survival for every type
- [agents.md convention](https://agents.md/)
- [netresearch/agent-rules-skill](https://github.com/netresearch/agent-rules-skill) — script-driven AGENTS.md generator; source for the bootstrap procedure above
- [Custom Instructions Documentation](https://code.visualstudio.com/docs/agent-customization/custom-instructions)
- [Memory and Root Context Files](https://code.claude.com/docs/en/memory)
- [Awesome Copilot Instructions Collection](https://github.com/github/awesome-copilot/tree/main/instructions)
- [Repository Instructions](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/add-custom-instructions/add-repository-instructions)
- [Copilot CLI custom instructions](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions)
- [Codex AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [APM Instructions and Agents](https://microsoft.github.io/apm/producer/author-primitives/instructions-and-agents/)
- [Prompt Engineering](https://developers.openai.com/api/docs/guides/prompt-engineering)
- [Writing a Good CLAUDE.md (HumanLayer)](https://www.humanlayer.dev/blog/writing-a-good-claude-md)
- [Lessons from 2,500 Repos on Writing AGENTS.md](https://github.blog/ai-and-ml/github-copilot/how-to-write-a-great-agents-md-lessons-from-over-2500-repositories/)
