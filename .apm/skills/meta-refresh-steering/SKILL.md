---
name: "meta-refresh-steering"
description: "Brings this repository's own authoring guidance — the meta-steering and meta-harness skills — back in line with what the harness vendors currently document, by re-reading every page cited under authoritativeSpec and looking for pages that should be cited and are not. ALWAYS invoke when asked to refresh the steering guidance, check whether the authoring rules still match the harnesses, fold new vendor documentation into meta-steering or meta-harness, or find out what changed in how skills and agents should be written. Do not rewrite an authoring rule from recall, and do not adopt a vendor's house style as a rule here without reading the page and recording it under authoritativeSpec. Keywords: steering refresh, authoring guidance, meta-steering, meta-harness, authoritativeSpec, spec drift, harness documentation, skill spec, agent spec, hook spec, new source, discovery budget."
compatibility: "Repo-local: needs `uv`, `git`, network access and a GitHub token, and drives this repository's `llmctl-check-updates`, `llmctl-check` and `llmctl-check-steering` commands. Both halves read vendor documentation, so without network access nothing here can run; say so and stop."
---

# meta-refresh-steering

Update the guidance itself. Everything else in this repository is written against `meta-steering` and `meta-harness`; this is the only procedure that moves those two.

Run it when you feel like it. Nothing schedules it, and nothing else depends on it having run — which is exactly why the guidance goes stale without a nudge.

## Scope

| In | Out |
| --- | --- |
| `packages/core/.apm/skills/meta-steering/` and its `references/` | every file those two govern — that is `meta-review-steering` |
| `packages/core/.apm/skills/meta-harness/` and its `references/` | `model:` and `effort:` selections — `meta-update-models` |
| the `authoritativeSpec` lists both carry | pinned dependencies and adapted files — `meta-update-repo` |

**Nothing here commits.** Propose the diff and say what it is based on.

## Read the documentation in subagents

Phases 1 and 2 are the expensive part by a wide margin: a harness's documentation index, plus every page under it that a cited rule depends on, will fill a context window on its own — and most of what gets read turns out to be unchanged. Reading it all here spends the context that Phase 3 needs to decide anything with.

So dispatch one subagent per harness, each with the `authoritativeSpec` URLs this repository already cites for that harness and the local claims those URLs back. Build each brief from the Phase 1 rows:

- **Group the rows by host**, not by skill: `code.claude.com`, `code.visualstudio.com`, `docs.github.com`, `learn.chatgpt.com` with `developers.openai.com`, `agentskills.io`, `agent-plugins.org`, `microsoft.github.io/apm` with `github.com/microsoft/apm`. One host is one subagent.
- **Find the claims each URL backs** with `grep -rn "<url>" packages/core/.apm/skills/meta-steering packages/core/.apm/skills/meta-harness`. A URL cited only in frontmatter backs the section named by its comment heading there. Hand the subagent those file paths and lines, not a summary of them.

Ask each one back for a report, never the pages:

- for each cited page: what it now says about the specific claims the local file encodes, quoting only the lines that moved
- for the index: pages that are not cited and look like they should be — URL plus one line of why
- anything it could not open, said plainly, and nothing it is inferring from a page it did not read

Phase 3 stays here. A subagent reports what a page says; deciding whether that is a fact to copy or a technique to weigh needs the local rules and the reasons behind them in context, which is exactly what not reading the pages here preserves.

## Phase 1 — the sources already cited

```bash
uv run llmctl-check-updates --repo . --specs --include "packages/core/.apm/skills/meta-steering/SKILL.md"
uv run llmctl-check-updates --repo . --specs --include "packages/core/.apm/skills/meta-harness/SKILL.md"
```

`--include` and `--exclude` filter the same way in every `llmctl-*` command: a pattern with a wildcard is a whole-path glob, and a bare word matches anywhere in the path. How each status arises is in [source-url-reference.md](../meta-update-repo/references/source-url-reference.md#statuses).

Each row is one `authoritativeSpec` URL. `update_available` means the page changed since the local file last did.

**Treat a quiet run as no evidence, not as good news.** A non-GitHub page is judged by its `Last-Modified` header against the file's last commit, and most vendor docs sites send no such header — they come back `not_trackable`. A GitHub permalink pinned to a commit SHA (the `microsoft/apm` integrator sources) reports `up_to_date` forever, because an immutable ref never moves; re-pinning those follows an APM CLI bump and is `meta-update-repo`'s phase F. So read the ones that matter whether or not they were flagged, and let the flags decide the order rather than the scope.

A `source_missing` or `fetch_failed` row is a finding in itself: open the URL in a browser before concluding it moved (some sites refuse scripted clients), then find its replacement under Phase 2.

## Phase 2 — the sources that should be cited and are not

The list is hand-maintained, so the thing most likely to matter is the thing it cannot see: a page that did not exist when the list was last written. Nothing detects this. Go and look.

For each harness the two skills already cite, open its documentation index and compare it against the URLs in the frontmatter:

- a customization type the guidance does not cover at all
- a page that replaced one already cited — the old URL may still resolve
- a capability the guidance says does not exist, or predates

Add what you find to `authoritativeSpec`, under the comment heading for its type, in the same order as the harnesses already listed there. A bare URL there is a citation and reproduces nothing — see [meta-steering's provenance section](../../../packages/core/.apm/skills/meta-steering/references/skill-frontmatter.md#provenance-metadata-recommended).

## Phase 3 — decide what a change means

Separate two things before editing, because they carry different burdens of proof:

| | What it is | What to do |
| --- | --- | --- |
| **Fact** | a field name, a character limit, an event name, a schema, a file location | update it directly; it is verifiable and being wrong is a defect |
| **Technique** | how a description should be shaped, when to split a skill, what makes discovery work | judgement — a vendor describes their own product's behaviour, which is evidence, not a rule |

A vendor's house style is not automatically this repository's convention. Where the two disagree and the local rule was deliberate, keep the local rule and say why, in the file, where the next reader will meet it.

## Phase 4 — record and verify

- A spec whose wording or tables were reproduced keeps its `authoritativeSpec` entry and switches it to the object form with `license` and `fidelity`, as [meta-steering's provenance section](../../../packages/core/.apm/skills/meta-steering/references/skill-frontmatter.md#provenance-metadata-recommended) says. Do not add an `adaptedFrom` entry for it. The `licences` gate can only enforce what is declared: a bare URL counts as `inspiration-only`, so reproduced wording under a bare URL passes unnoticed. Rewrite it in local words instead.
- After any frontmatter edit: `uv run llmctl-check --repo . --only frontmatter --only licences`; before proposing the whole diff, `apm run check`.
- Editing the guidance is what makes every file it governs due for review. Say so at the end, and hand off to `meta-review-steering`.

**`llmctl-check-steering` measures committed guidance only.** It reads `git log`, so an edit that is still in the working tree — which is every edit this procedure makes, since nothing here commits — is invisible to it. Hand off in one of two ways:

- **Committed** (after confirmation, one commit per guidance skill, scope `core`): `uv run llmctl-check-steering --repo .` now shows what is behind.
- **Not committed**: give `meta-review-steering` the working-tree diff itself, and say which rules it changed:

  ```bash
  git diff -- packages/core/.apm/skills/meta-steering packages/core/.apm/skills/meta-harness
  git status --short -- packages/core/.apm/skills/meta-steering packages/core/.apm/skills/meta-harness   # new, untracked pages
  ```

Then `meta-review-steering` decides which governed files actually need a change.

## Report

Per skill: which cited pages moved and what in them moved, which sources were added and why, which changes were facts and which were techniques, what was deliberately not adopted and the reason, and what is now due for review.
