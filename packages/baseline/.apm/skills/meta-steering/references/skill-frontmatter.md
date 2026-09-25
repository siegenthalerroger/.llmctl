# SKILL.md Frontmatter Examples

**Contents:** [Description](#description) · [Third-Person Voice](#third-person-voice) · [Harness-Specific Fields](#harness-specific-fields) · [Provenance Metadata (Recommended)](#provenance-metadata-recommended)

## Description

Shape beats keyword density — directive phrasing with an explicit negative constraint is the dominant activation lever. See [the router, section 3](../SKILL.md#3-description-craft--all-four-types) for the empirical basis and full rule set.

**Good description (directive + negative constraint):**

```yaml
description: Toolkit for testing local web applications using Playwright (Chrome, Firefox, WebKit). ALWAYS invoke when asked to verify frontend functionality, debug UI behavior, capture browser screenshots, check for visual regressions, or read browser console logs. Do not hand-write Playwright scripts or guess at UI state from source alone — use this skill first.
```

**Poor description (vague):**

```yaml
description: Web testing helpers
```

Fails because it has no specific triggers, no keywords a user would actually say, and no stated capability.

**Poor description (keyword-stuffed but passive):**

```yaml
description: Playwright, testing, browser, UI, frontend, e2e, screenshots, visual regression, Chrome, Firefox, WebKit, console logs, automation, QA. Use when working with web testing.
```

Fails despite dense keyword coverage — it is passive capability-list phrasing with no directive verb and no negative constraint, the shape [section 3](../SKILL.md#3-description-craft--all-four-types) shows activating least reliably. Keywords belong inside the trigger clause of a directive sentence, not as a standalone list.

## Third-Person Voice

**Good (third person):**

```yaml
description: Processes Excel spreadsheets and generates summary reports. ALWAYS invoke when working with .xlsx files, pivot tables, or data aggregation tasks.
```

**Poor (first/second person):**

```yaml
description: I can help you process Excel files and create reports for you.
```

Use third person ("Processes", "Generates") — not first person ("I can") or second person ("You can use this to").

## Harness-Specific Fields

Not part of the portable spec — verify against current target docs before relying on them.

**`when_to_use` (Claude Code)** — overflow trigger phrases, appended to `description` in discovery (combined text truncates at 1536 chars):

```yaml
description: Toolkit for testing local web applications using Playwright.
when_to_use: When the user mentions flaky e2e tests, visual diffs, headless browser automation, or asks to reproduce a bug in Chrome/Firefox/WebKit.
```

**`paths` (Claude Code)** — restricts automatic activation to work on matching files; it narrows when the skill loads and does not force loading:

```yaml
paths:
  - "**/*.spec.ts"
  - "playwright.config.*"
```

**`context: fork` (Claude Code; VS Code, experimental)** — run the skill body as an isolated subagent instead of loading it inline:

```yaml
context: fork
```

**`user-invocable: false`** — background knowledge with no `/` menu entry (independent of `disable-model-invocation`, which blocks autonomous invocation):

```yaml
user-invocable: false
```

**`argument-hint`** — shown during `/` autocomplete, so it belongs only on a user-invocable skill:

```yaml
argument-hint: "[test-file]"
```

## Provenance Metadata (Recommended)

When documenting where content came from, add provenance under `metadata.provenance` in frontmatter:

```yaml
metadata:
  provenance:
    adaptedFrom: "https://github.com/example-upstream/skills/tree/main/excel-processing"
```

A plain string (or array of strings) means the **whole file** derives from that upstream. Prefer the object form, which scopes the adaptation and records the terms it arrives under:

```yaml
metadata:
  provenance:
    adaptedFrom:
      - url: "https://github.com/example-upstream/skills/tree/main/excel-processing"
        license: MIT              # SPDX id of the upstream, or NONE
        fidelity: partly-derived  # how much of it landed here
        took: "The column-mapping rules."
```

**`fidelity`** is the obligation level. Absent means whole-file derivation, treated as `largely-derived`.

| Value | Meaning | Upstream terms attach? |
| --- | --- | --- |
| `inspiration-only` | A concept or framing was reused; effectively no text | no |
| `structural-echo` | Section skeleton or headings, not content | no |
| `partly-derived` | Some sections genuinely derive from upstream | **yes** |
| `largely-derived` | Most of the local file derives from upstream, up to near-verbatim | **yes** |

**`license`** is the SPDX id of the **upstream**, not of this file. It is required whenever `fidelity` implies an obligation, because it decides what this file may be licensed under: this repository's `licences` gate (`llmctl-check-licenses`, `src/llmctl/check_licenses.py`) rejects a file whose own licence cannot satisfy it. Record `NONE` for an upstream with no LICENSE file — that grants no rights at all, and is only safe at a fidelity that attaches no terms: `inspiration-only` or `structural-echo`.

**`took`** is single-line and records *what was taken*, nothing else. It lets the `meta-update-repo` audit (source repository only) close an upstream change without a merge review when the change touches nothing on the list. Test: could this list ever let a reviewer close a merge review unread? If not, use the plain string form.

- **Never record what was not taken**, or what is original locally. That is an open set: upstream can add sections indefinitely, so it is wrong the moment upstream grows, and no local change ever triggers a refresh.
- **Never record measurements** (line-overlap percentages, sizes, counts). Both sides move; `fidelity` carries the same signal durably. Put a measurement in the commit message that motivated it.
- **Omit `took` on a wholly derived file.** `fidelity: largely-derived` already says the whole file derives from that upstream; a list there misreads a copy as a selective adaptation.
- **Do not overload it.** The licence goes in `license`, the obligation level in `fidelity`, follow-up work in the tracker. The one exception: a short note on why the URL is *not* a line-for-line comparison base (upstream moved or restructured the path) belongs, because it changes how the next reviewer reads the diff.

What the parser accepts, and how an entry can silently drop out of the audit, is in the `meta-update-repo` skill (source repository only), `references/source-url-reference.md`.

A file whose upstream obligation cannot be met by the repository default licence declares its own with a top-level `license:` field; see [LICENSE](https://github.com/siegenthalerroger/.llmctl/blob/main/LICENSE).

> **APM-first rule:** Before creating an `adaptedFrom` entry, verify the upstream content isn't available as an APM package. APM dependencies (declared in `apm.yml`) don't need provenance tracking — they're managed externally. Copy locally only where APM cannot manage the content.

- `metadata.provenance.adaptedFrom`: source URL (string), list of URLs (array), or the object form above, for anything taken from an upstream — from a borrowed idea up to a near-verbatim carry-over, with `fidelity` saying which
- `metadata.provenance.authoritativeSpec`: authoritative specifications defining the format. A bare URL string means **cited only, nothing reproduced**, which carries no obligation. If a reference file reproduces a spec's tables or wording, switch that entry to the object form and give it a `license`/`fidelity` — a vendor documentation site usually grants no reuse rights at all, and the fix is rewriting rather than attribution

**Non-repository sources** (books, papers, vendor pages) are legitimate entries:

- Cite a book by a resolver URL, not a bookshop or publisher page: `https://openlibrary.org/isbn/{isbn}`, or `https://doi.org/{doi}` where a DOI exists.
- Cite the specific edition; page-level claims do not survive an edition change.
- Never "resolve" a `not_trackable` entry by deleting it. The update check cannot track it, but the attribution is what the entry exists to carry.

Use this same convention for prompt, instruction, skill, and agent files.
