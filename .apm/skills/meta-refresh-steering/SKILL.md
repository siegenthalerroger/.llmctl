---
name: "meta-refresh-steering"
description: "Brings this repository's own authoring guidance — the meta-steering and meta-harness skills — back in line with what the harness vendors currently document, by re-reading every page cited under authoritativeSpec and looking for pages that should be cited and are not. ALWAYS invoke when asked to refresh the steering guidance, check whether the authoring rules still match the harnesses, fold new vendor documentation into meta-steering or meta-harness, or find out what changed in how skills and agents should be written. Do not rewrite an authoring rule from recall, and do not adopt a vendor's house style as a rule here without reading the page and recording it under authoritativeSpec. Keywords: steering refresh, authoring guidance, meta-steering, meta-harness, authoritativeSpec, spec drift, harness documentation, skill spec, agent spec, hook spec, new source, discovery budget."
compatibility: "Repo-local: needs `uv`, `git`, network access and a GitHub token, and drives this repository's `check-updates` command. Without network access the declared half cannot run and the discovery half is the whole job."
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

So dispatch one subagent per harness, each with the `authoritativeSpec` URLs this repository already cites for that harness and the local claims those URLs back. Ask each one back for a report, never the pages:

- for each cited page: what it now says about the specific claims the local file encodes, quoting only the lines that moved
- for the index: pages that are not cited and look like they should be — URL plus one line of why
- anything it could not open, said plainly, and nothing it is inferring from a page it did not read

Phase 3 stays here. A subagent reports what a page says; deciding whether that is a fact to copy or a technique to weigh needs the local rules and the reasons behind them in context, which is exactly what not reading the pages here preserves.

## Phase 1 — the sources already cited

```bash
uv run scripts/check_updates.py --repo . --specs --include "meta-steering"
uv run scripts/check_updates.py --repo . --specs --include "meta-harness"
```

Each row is one `authoritativeSpec` URL. `update_available` means the page changed since the local file last did.

**Treat a quiet run as no evidence, not as good news.** The check compares a `Last-Modified` header against the file's last commit, and several of the pages that matter most send no such header — they come back `not_trackable`. So read the ones that matter whether or not they were flagged, and let the flags decide the order rather than the scope.

## Phase 2 — the sources that should be cited and are not

The list is hand-maintained, so the thing most likely to matter is the thing it cannot see: a page that did not exist when the list was last written. Nothing detects this. Go and look.

For each harness the two skills already cite, open its documentation index and compare it against the URLs in the frontmatter:

- a customization type the guidance does not cover at all
- a page that replaced one already cited — the old URL may still resolve
- a capability the guidance says does not exist, or predates

Add what you find to `authoritativeSpec`, under the comment heading for its type, in the same order as the harnesses already listed there. A URL there is a citation and reproduces nothing — see [the provenance reference](../meta-update-repo/references/source-url-reference.md).

## Phase 3 — decide what a change means

Separate two things before editing, because they carry different burdens of proof:

| | What it is | What to do |
| --- | --- | --- |
| **Fact** | a field name, a character limit, an event name, a schema, a file location | update it directly; it is verifiable and being wrong is a defect |
| **Technique** | how a description should be shaped, when to split a skill, what makes discovery work | judgement — a vendor describes their own product's behaviour, which is evidence, not a rule |

A vendor's house style is not automatically this repository's convention. Where the two disagree and the local rule was deliberate, keep the local rule and say why, in the file, where the next reader will meet it.

## Phase 4 — record and verify

- A page whose wording was reproduced needs an `adaptedFrom` entry with its `license` and `fidelity`, not just a citation. The `licences` gate fails a file that copies expression without recording the upstream licence.
- `apm run check` after any frontmatter edit.
- Editing the guidance is what makes every file it governs due for review. Say so at the end, and hand off:

```bash
uv run scripts/check_steering.py --repo .   # what is now behind
```

Then `meta-review-steering` decides which of those actually need a change.

## Report

Per skill: which cited pages moved and what in them moved, which sources were added and why, which changes were facts and which were techniques, what was deliberately not adopted and the reason, and what is now due for review.
