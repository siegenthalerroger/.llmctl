---
name: "meta-review-steering"
description: "Reviews this repository's steering files — skills, agents, instructions, prompts and hooks — against the meta-steering and meta-harness guidance that governs them, starting from the files git says were last touched before that guidance moved. ALWAYS invoke when asked whether the existing skills still follow the authoring conventions, to sweep the repository for steering that has fallen behind, or after the guidance itself has been refreshed. Do not judge a file compliant from its frontmatter alone, and do not rewrite one because a report called it behind — read the guidance commits in the gap first and close the ones that changed no rule it has to follow. Keywords: steering review, alignment sweep, authoring conventions, meta-steering, meta-harness, compliance audit, description shape, drift, stale skill, check-steering."
compatibility: "Repo-local: needs `uv` and `git`, and drives this repository's `check-steering` and `check` commands. Runs offline."
---

# meta-review-steering

Check what the guidance governs against what the guidance says. The other half of [meta-refresh-steering](../meta-refresh-steering/SKILL.md), which moves the guidance itself.

## Where to start

```bash
uv run llmctl-check-steering --repo .                    # everything
uv run llmctl-check-steering --repo . --include python   # one area
```

`--include` and `--exclude` take the same patterns in every `llmctl-*` command: a bare word matches anywhere in the path, a pattern with `*`, `?` or `[` is a whole-path glob.

Every authored `SKILL.md`, `*.agent.md`, `*.instructions.md`, `*.prompt.md` and `*.hook.json`, each against the guidance pages for its own kind, with the guidance commits that landed after the file was last touched.

**`behind` is a starting order, not a finding.** The signal is git, so it is wrong in both directions and knowing how is the difference between a review and a rewrite:

- A cosmetic commit to the guidance — a typo, a renamed link — marks every file it governs `behind`. Most of a run is usually this.
- An edit to a file for an unrelated reason clears its flag with nobody having re-read it. `current` therefore means *not measurable*, never *verified*.

So: read the gap commits first. If none of them changed a rule that file has to follow, close it as no action and say so. That is the common case and it is a real result — record it rather than reaching for a diff.

- **`uncommitted`** means the file has never been committed, so nothing can be measured. Review it in full against the guidance for its kind.
- **The guidance itself is measured only once committed.** `meta-refresh-steering` hands over a working-tree diff when its edits are not committed yet. Then that diff *is* the gap for every file of the kinds it touches: read which rules it changed and review against those, ignoring the `behind` column for them.

## One subagent per package

A sweep is a wide read — every governed file, plus the guidance pages behind it — and doing it in one context degrades the files that come last: by then the guidance is being recalled from a summary of itself rather than read.

So split the run and give each split its own subagent. One per package (`--include packages/baseline/`, `--include packages/ops/`, …) plus one for the root `.apm/` (`--include '.apm/*'` — a bare `.apm/` matches every package too), or finer where a package holds unrelated blocks: a set of skills that cite each other is worth keeping in one context, a set that does not is worth separating. Each subagent gets the paths it owns and the `llmctl-check-steering --json` rows for them, opens the guidance itself, and returns the three groups below for its own files only. Merge the reports here.

## What to review, once a file is worth reviewing

The `frontmatter` gate already covers the mechanical half on every run, and it is not worth repeating by eye: missing `name`/`description`, skill name against its directory, kebab-case, reserved words, the 1024-character limit, block scalars, the line ceiling. Run it rather than reading for it:

```bash
uv run llmctl-check --repo . --only frontmatter
```

What no gate can check, and what this review is for:

| | Against |
| --- | --- |
| Is the description a directive with an explicit negative constraint, front-loaded, name-first? | [meta-steering §3](../../../packages/baseline/.apm/skills/meta-steering/SKILL.md#3-description-craft--all-four-types) |
| Is this the right customization type at all, or a rule wearing the wrong one? | [meta-steering §1](../../../packages/baseline/.apm/skills/meta-steering/SKILL.md#1-pick-the-customization-type-first) |
| Does the description fit the discovery budget its harnesses share? | [meta-steering §3, context budget](../../../packages/baseline/.apm/skills/meta-steering/SKILL.md#context-budget--four-distinct-surfaces) |
| Is every frontmatter key honoured, stripped or destructive on each deployed target, and does a stripped key's intent survive in the body? | [meta-steering §4](../../../packages/baseline/.apm/skills/meta-steering/SKILL.md#4-frontmatter-shared-by-all-four-types) and [the deploy matrix](../../../packages/baseline/.apm/skills/meta-steering/references/frontmatter-deploy.md#the-matrix) |
| Does the body earn its place, or restate what the harness or a tool schema already says? Does it fall into a named anti-pattern? | [meta-steering §5](../../../packages/baseline/.apm/skills/meta-steering/SKILL.md#5-anti-patterns-across-all-four-types) |
| For a hook or an MCP entry: is it deterministic, and is the event name real? | [meta-harness](../../../packages/baseline/.apm/skills/meta-harness/SKILL.md) |

## Constraints

- **Propose, do not apply.** One file at a time, minimal diff, and nothing committed without confirmation. A commit's scope is the package the file lives in, or `meta` for the root `.apm/`.
- A file governed by a rule that changed gets re-read against the rule, not against your memory of it. Open the guidance page.
- Where a file deliberately diverges and says so, that is a decision, not a finding. Leave it and report it as kept.
- Reviewing a file does not make it compliant forever. There is no stamp and nothing records that a review happened — the next run will flag it again the next time the guidance moves.

## Report

Three groups, and the middle one is the point:

1. **Changed** — file, which rule moved, the diff.
2. **Closed** — file, which guidance commits were in its gap, why none of them applied to it.
3. **Kept** — file, the divergence, why it stands.
