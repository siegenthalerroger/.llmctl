---
name: "meta-update-repo"
description: "Refreshes this repository's upstream inputs — the pinned APM dependencies and their lockfiles, the files adapted from an upstream via metadata.provenance.adaptedFrom, and the specification URLs under authoritativeSpec — one package at a time, reading the diff of everything that moved before any of it is committed. ALWAYS use when asked to update dependencies, bump a pin, sync upstream, refresh a lockfile, or check adapted files for drift. Do not run apm update, edit a #sha by hand, or merge an upstream change without this procedure and its safety review. Keywords: apm update, apm outdated, lockfile, pin bump, upstream sync, dependency update, adaptedFrom, authoritativeSpec, drift audit, safety review."
compatibility: "Repo-local: needs `apm`, `uv`, `git` and a GitHub token, and drives this repository's scripts/check_updates.py and scripts/check.py, which are not bundled with the skill. If they cannot be run, reproduce each step with equivalent repository or MCP tools and report the fallback used."
---

# meta-update-repo

Bring this repository's third-party inputs up to date, deliberately, with a
reading of every diff before it lands.

## Scope

Three kinds of upstream, audited separately because they fail differently:

| Input | Declared in | Moves when |
| --- | --- | --- |
| APM dependencies | `dependencies.apm` in `packages/*/apm.yml`, resolved in `packages/*/apm.lock.yaml` | a pin is bumped |
| Adapted content | `metadata.provenance.adaptedFrom` in a primitive's frontmatter | the upstream file changes and we merge it |
| Specifications | `metadata.provenance.authoritativeSpec` in a primitive's frontmatter | the spec changes and our claims about it stop being true |

Out of scope, handled elsewhere: model selections belong to `meta-update-models`,
description and structure conventions to `meta-steering` and `meta-harness`.

## Prerequisites

- A clean tree, or at least no uncommitted change in `packages/`: phase A commits
  per package, and phase B reads what moved against `HEAD`.
- `git fetch --tags` — the audit dates each local file from its last commit.
- A GitHub token in `GITHUB_TOKEN`/`GH_TOKEN`, or `gh auth login`. Unauthenticated
  runs hit a 60-request hourly limit and report `fetch_failed` rows that look
  like broken URLs.

## Phase A — APM dependencies

Per package, never across packages: a bump and its lockfile refresh are one
commit, and one commit is one thing to review.

```bash
cd packages/<dir>
apm outdated
apm update --dry-run
```

Read the plan before running it. Then, for each dependency it can move:

```bash
apm update -y --target claude
```

**Rows reported `unknown` need the manual path.** `apm update` moves a full-SHA
pin only to the newest *annotated* semver tag upstream; a repository that
publishes no annotated tags — `blader/humanizer` and `rshade/agent-skills`
today — can never be refreshed by it. For those:

```bash
git ls-remote https://github.com/<owner>/<repo> HEAD     # the commit to move to
# edit the `#<sha>` in packages/<dir>/apm.yml
apm install --target claude                              # re-resolve and rewrite the lockfile
```

Never `apm install --frozen` here. A frozen install checks that each dependency
*appears* in the lockfile, never at which commit, so it would not notice the pin
you just moved.

Then go to phase B. Only after it passes, commit `apm.yml` and `apm.lock.yaml`
together:

```text
build(<dir>): bump <dependency> to <sha7>
```

## Phase B — Safety review, before anything is committed

A pinned dependency is content an agent will read as instructions, and some of
it ships scripts and hooks that run locally. The pin fixes *which* content
arrives, not what it does. A bump is the one moment where looking is cheap: the
change is bounded and someone is already reviewing it.

```bash
apm audit --file apm_modules/<owner>/<repo>/<changed file>   # hidden Unicode, per file
uv run scripts/check_updates.py --repo . --compare --package <dir>
```

`--compare` prints the upstream's own diff between the committed pin and the one
now in the working tree, filtered to the path this repository consumes. Read it
against [references/safety-review.md](references/safety-review.md), which lists
what to look for and what each finding means.

A blocking finding stops the bump. Report it to the person you are working with,
quoting the hunk, and leave the pin where it was.

Where `apm experimental enable external-scanners` has been run locally,
`apm audit --external skillspector` adds a second opinion. It is experimental and
makes outbound calls; it supplements the reading, it does not replace it.

## Phase C — Adapted content

```bash
uv run scripts/check_updates.py --repo .                               # broad
uv run scripts/check_updates.py --repo . --include "<glob>" --change-details --json
```

Scope directly with `--include` when the target is known — never run a broad scan
first in that case. This applies even when the request is indirect: if a specific
file is contextually identifiable, treat it as an identified target.

| Case | Status | Action |
| --- | --- | --- |
| APM-eligible upstream | `update_available` | recommend converting to an APM dependency instead of merging |
| Single source | `update_available` | merge review |
| Multi-source | one or more `update_available` | synthesised merge review across all changed upstreams |
| `took` present | `update_available` | scope the review to `took` first — if the upstream change touches nothing on its list, close as no action and say so |
| Upstream path gone | `source_missing` | re-point the URL, or drop the provenance entry if nothing of it remains |
| Upstream relicensed | any | update the entry's `license`, record it in `dependency-licenses.yml`, re-run the licences gate |
| any | `up_to_date` | no action |

For a stub or empty local file, fetch the full upstream content: commit summaries
alone are not reviewable when there is nothing local to diff against. Prefer a
GitHub API tool or `gh api` over a generic web fetch for GitHub sources.

**Multi-source files** are checked per upstream, one row each. When more than one
flags `update_available`: run the detailed check for each, compare the changes
against the local file to separate overlapping from independent sections,
recommend a **single merged update**, and flag any conflict where two upstreams
changed the same idea differently.

**After any merge, re-check `fidelity` and `license` in the same edit.** Taking
more across than last time raises the fidelity, and a raised fidelity can attach
terms the local file's licence cannot carry. Never leave it to a follow-up.

## Phase D — Specifications

```bash
uv run scripts/check_updates.py --repo . --specs
```

A GitHub source is dated from its commits. Anything else — vendor documentation,
mostly — is probed over HTTP: a dead link reports `source_missing`, a page whose
`Last-Modified` is newer than the local file's last commit reports
`update_available`, and a site that sends no date reports `not_trackable`, which
is the honest answer rather than a stored hash that would churn on every site
rebuild.

For `update_available`, read the page and check the claims the local file makes
about it — a field name, a limit, a schema. Record the outcome either way. Edit
only when asked.

## Phase E — Verify

```bash
uv run scripts/check.py --repo . --since origin/main
```

Then report, per package: which pins moved and to what, the verdict of each
safety review, which adaptations were flagged and what was done, and which specs
changed. Say explicitly what was left alone and why.

## Guidelines

- Commit nothing without confirmation; propose, do not apply.
- One package per commit, `apm.yml` and `apm.lock.yaml` together. A lockfile that
  moves without its manifest, or the reverse, fails the `lockfiles` gate.
- Never hand-edit `apm.lock.yaml`. It is generated; `apm install` writes it.
- An entry whose object form loses its `url` drops out of the audit silently — no
  error, no row. After editing any provenance block, confirm the file still
  appears in the output.
- Treat `adaptedFrom` entries as merge-review candidates, never blind replacements.
- When an upstream change alters workflow, process, or opinionated behaviour
  rather than correcting a fact, ask before replicating it.
- Report unknown or unreachable sources explicitly rather than omitting them.

## Notes

- `authoritativeSpec` is not checked by the default mode — it declares which
  specification a file conforms to, not where content came from. It is not inert:
  `scripts/check_licenses.py` reads it too, treating a bare URL as a citation
  that reproduces nothing.
- Provenance forms — a URL string, an array of URLs, or an array of objects
  carrying `url` plus `license` / `fidelity` / `took` — are described in
  [references/source-url-reference.md](references/source-url-reference.md).
- Another workspace borrows this repository's scripts the same way it borrows
  the rest: `uv run ../.llmctl/scripts/check_updates.py --repo .`.
