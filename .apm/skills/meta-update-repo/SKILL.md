---
name: "meta-update-repo"
description: "Refreshes this repository's upstream inputs — the pinned APM dependencies and their lockfiles, the files adapted from an upstream via metadata.provenance.adaptedFrom, and the specification URLs under authoritativeSpec — by running the repository's own update and audit commands and reading the diff of everything that moved before any of it is committed. ALWAYS use when asked to update dependencies, bump a pin, sync upstream, refresh a lockfile, or check adapted files for drift. Do not run apm update directly, edit a #sha by hand, or merge an upstream change without this procedure and its safety review. Keywords: apm update, apm outdated, lockfile, pin bump, upstream sync, dependency update, adaptedFrom, authoritativeSpec, drift audit, safety review."
compatibility: "Repo-local: needs `apm`, `uv`, `git` and a GitHub token, and drives this repository's `apm run update`, `check-updates` and `check` commands, which are not bundled with the skill. If they cannot be run, reproduce each step with equivalent repository or MCP tools and report the fallback used."
---

# meta-update-repo

Bring this repository's third-party inputs up to date, deliberately, with a reading of every diff before it lands.

## Scope

Three kinds of upstream, audited separately because they fail differently:

| Input | Declared in | Command |
| --- | --- | --- |
| APM dependencies | `dependencies.apm` in `packages/*/apm.yml`, resolved in `packages/*/apm.lock.yaml` | `apm run update` |
| Adapted content | `metadata.provenance.adaptedFrom` in a primitive's frontmatter | `apm run check-updates` |
| Specifications | `metadata.provenance.authoritativeSpec` in a primitive's frontmatter | the same, with `--specs` |

Out of scope, handled elsewhere: model selections belong to `meta-update-models`, description and structure conventions to `meta-steering` and `meta-harness`.

**Nothing here commits.** Every command writes the working tree at most; what to keep is the judgement this skill exists to support.

## Prerequisites

- A GitHub token in `GITHUB_TOKEN`/`GH_TOKEN`, or `gh auth login`. Without one the diffs cannot be fetched, which is most of the point, and the audits report rate-limit rows that look like broken URLs.
- `git fetch --tags`, and a tree with no uncommitted change under `packages/` — the update measures every move against `HEAD`.

## Phase A — pinned dependencies

```bash
apm run update                                   # every package
uv run llmctl-update --repo . --package core # or one
```

Per package it moves each pin as far as it goes, installs, proves the lockfile followed, scans what was materialised with `apm audit`, and prints the upstream's own diff for everything that moved, filtered to the path this repository consumes.

Two things it deliberately does not do. It never bumps a tagged upstream to HEAD: where `apm update` declines, the pin stays and the run reports it. And it commits nothing.

**Then read every diff**, against [references/safety-review.md](references/safety-review.md), which says what to look for and what each finding means. This is the step the command exists to set up: a pinned dependency is content an agent loads as instructions, some of it ships hooks and scripts that run locally, and `apm approve` gates execution, not content.

Keep a package by committing its two files together:

```bash
git add packages/<dir>/apm.yml packages/<dir>/apm.lock.yaml
git commit -m "build(<dir>): bump <dependency> to <sha7>"
```

Reject one with `git checkout -- packages/<dir>`, and say why.

### When a package cannot be updated

The run exits non-zero and names it. Known cause on APM 0.31: a package pinning several subpaths of one repository at the same commit fails with "Expected exactly one apm.yml entry for `<sha>`, found N" and APM writes nothing. `packages/design` is in that state today. Report it; do not work around it by hand-editing the pins, because a hand-moved pin skips the tag `apm update` would have chosen.

## Phase B — adapted content

```bash
apm run check-updates                                                   # broad
uv run llmctl-check-updates --repo . --include "<glob>" --change-details
```

Scope directly with `--include` when the target is known — never run a broad scan first in that case. This applies even when the request is indirect: if a specific file is contextually identifiable, treat it as an identified target.

| Case | Status | Action |
| --- | --- | --- |
| APM-eligible upstream | `update_available` | recommend converting to an APM dependency instead of merging |
| Single source | `update_available` | merge review |
| Multi-source | one or more `update_available` | synthesised merge review across all changed upstreams |
| `took` present | `update_available` | scope the review to `took` first — if the upstream change touches nothing on its list, close as no action and say so |
| Upstream path gone | `source_missing` | re-point the URL, or drop the provenance entry if nothing of it remains |
| any | `up_to_date`, `not_trackable` | no action |

For a stub or empty local file, fetch the full upstream content: commit summaries alone are not reviewable when there is nothing local to diff against. Prefer a GitHub API tool or `gh api` over a generic web fetch for GitHub sources.

**Multi-source files** are checked per upstream, one row each. When more than one flags `update_available`: run the detailed check for each, compare the changes against the local file to separate overlapping from independent sections, recommend a **single merged update**, and flag any conflict where two upstreams changed the same idea differently.

**After any merge, re-check `fidelity` and `license` in the same edit.** Taking more across than last time raises the fidelity, and a raised fidelity can attach terms the local file's licence cannot carry. Never leave it to a follow-up.

## Phase C — specifications

```bash
uv run llmctl-check-updates --repo . --specs
```

A GitHub source is dated from its commits; anything else is probed over HTTP. `update_available` means the page changed since the local file last did — read it and check the claims the local file makes about it, a field name, a limit, a schema. Record the outcome either way. Edit only when asked.

## Phase D — verify

```bash
apm run check
```

Then report, per package: which pins moved and to what, the verdict of each safety review, which adaptations and specifications were flagged, and what was deliberately left alone and why.

## Guidelines

- Propose, do not apply: commit nothing without confirmation.
- One package per commit, `apm.yml` and `apm.lock.yaml` together. Either without the other fails the `lockfiles` gate.
- Never hand-edit `apm.lock.yaml`. It is generated.
- An entry whose object form loses its `url` drops out of the audit silently — no error, no row. After editing any provenance block, confirm the file still appears in the output.
- Treat `adaptedFrom` entries as merge-review candidates, never blind replacements.
- When an upstream change alters workflow, process, or opinionated behaviour rather than correcting a fact, ask before replicating it.
- Report unknown or unreachable sources explicitly rather than omitting them.
- A licence that moved upstream is reported by phase A. Update `dependency-licenses.yml`, then re-run `apm run check`.

## Notes

- `authoritativeSpec` declares which specification a file conforms to, not where content came from, so it is not in the phase B scan. It is not inert: `llmctl-check-licenses` reads it too, treating a bare URL as a citation that reproduces nothing.
- Provenance forms — a URL string, an array of URLs, or an array of objects carrying `url` plus `license` / `fidelity` / `took` — are described in [references/source-url-reference.md](references/source-url-reference.md).
- Another workspace runs these commands from this repository's git, the same way it runs the rest: `uvx --from git+https://github.com/siegenthalerroger/.llmctl@main llmctl-update --repo .`.
