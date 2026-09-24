---
name: "Self-Improvement Instructions"
description: "Workflow and writing rules for changing steering files: edit sources never installed mirrors, load the owning meta skill first, and budget every added rule. Applies when creating, editing or reviewing skills, agents, instructions, prompts, hooks, plugins or root context files."
# Copilot
applyTo: "**/*.agent.md, **/SKILL.md, **/*.prompt.md, **/*.instructions.md, CLAUDE.md, AGENTS.md, **/*.hook.json, **/plugin.json, **/.apm/**"
# Claude Code
paths: ["**/*.agent.md", "**/SKILL.md", "**/*.prompt.md", "**/*.instructions.md", "CLAUDE.md", "AGENTS.md", "**/*.hook.json", "**/plugin.json", "**/.apm/**"]
---

# Self-Improvement Guidelines

## Capabilities

You have multiple mechanisms to improve and learn: agents, skills, instructions, prompts, hooks, MCP servers, and plugins. Collectively we call them "customization" files.

Which one a given rule belongs in is the first decision, and getting it wrong costs more than any amount of polish on the wrong artifact. The complete seven-way selection table lives in the `meta-steering` skill — load it rather than guessing.

## Workflow

- **Edit source files, NEVER installed mirrors.** Global customization sources live under `.llmctl/packages/*/.apm/` (or `.llmctl/.apm/` for repository tooling), project scoped ones in a `.apm` folder of the specific repository. Before editing any customization file, check the path to validate if it is project scoped or global and whether it is a mirror. The path a skill is loaded from at runtime is often a mirror — do not edit it in place.
- **A file inside a plugin bundle or `apm_modules/` is not ours to edit either.** An enclosing `.claude-plugin/plugin.json` or `apm.lock.yaml` marks generated output that the next install overwrites. Trace it to the workspace it was packed from — the `/reflect` prompt carries the full chain — and fix it there or shadow it into `.llmctl` with provenance recorded.
- Delegate to a subagent to **create new** or **substantially rewrite** customization files, and have it load the owning skill for the design and implementation.
- Before creating or substantially editing a customization file, load the skill that owns it:
  - `meta-steering` for what the model reads — `SKILL.md`, `*.agent.md`, `*.instructions.md`, `*.prompt.md`
  - `meta-harness` for what the harness executes or installs — `*.hook.json`, MCP servers in `apm.yml`, `plugin.json` and bundle layouts

  Each routes to a per-type reference; neither is optional before writing frontmatter.
- For targeted edits (inserting a section, appending items, fixing wording), edit the file directly with the available tools. Do not use a subagent when the edit is simple and the insertion point is known.
- Run multiple subagents in parallel if the learnings can be clearly separated from eachother.

## Writing Effective Guidelines

When adding new or adapting pre-existing agent customization files, follow these principles:

**Core Principles (Always Apply):**

1. **Prefer Skills over Instructions**: Skills are modular and load on demand. Reserve instructions for durable project context, build/test/validate expectations, path-scoped conventions, broad behavioral rules, and loading skills via `applyTo`.
2. Be explicit about what files to update or add. Consider what type of input would have been most helpful.
3. State hard requirements as absolute directives, never with "should" or "would". Label genuine defaults as defaults and say when they may change.
4. Bullets over paragraphs. Keep explanations concise.
5. Do NOT just suggest what could have been done differently this time! Generalise and adapt any pre-existing provided inputs.
6. Apply the per-line litmus test: would removing this line cause mistakes? If not, cut it.
7. Write descriptions name-first, directive shape, with an explicit negative constraint; keywords are trigger coverage, not stuffing (see `meta-steering` for detail).
8. Never soften a hard requirement with soft-permission phrasing ("prefer X, but Y if simpler").
9. Budget every addition against the shared always-loaded instruction pool (frontier models reliably follow ~150–200 total, and the harness already spends ~50) — move procedures into an on-demand skill instead of growing an always-loaded file.

**Optional Enhancements (Use Strategically):**

- ❌/✅ examples: Only when the antipattern is subtle
- "Warning Signs" section: Only for gradual mistakes
- "General Principle": Only when abstraction is non-obvious
- Add code examples where it make sense

**Anti-Bloat Rules:**

- ❌ Don't add "Warning Signs" to obvious rules
- ❌ Don't show bad examples for trivial mistakes
- ❌ Don't write paragraphs explaining what bullets can convey
- ❌ Don't polish marginal content — delete it (irrelevant-but-coherent text measurably hurts more than incoherent filler)
- ❌ Don't add a gotcha for a one-off mistake; wait until it recurs, and correct or consolidate existing guidance first. Established requirements and evidenced serious hazards are documented without waiting