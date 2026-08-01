# SKILL.md Frontmatter Examples

## Description

Shape beats keyword density — directive phrasing with an explicit negative constraint is the dominant activation lever. See [SKILL.md § Description Best Practices](../SKILL.md#description-best-practices) for the empirical basis and full rule set.

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

Fails despite dense keyword coverage — it is passive capability-list phrasing with no directive verb and no negative constraint, so it caps at the ~77–87% activation rate of "Use when…" phrasing (and lower still under competing skills). Keywords belong inside the trigger clause of a directive sentence, not as a standalone list.

## Third-Person Voice

**Good (third person):**

```yaml
description: Processes Excel spreadsheets and generates summary reports. Use when working with .xlsx files, pivot tables, or data aggregation tasks.
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

**`paths` (Claude Code)** — glob-gated auto-loading, a structural trigger alongside description text:

```yaml
paths:
  - "**/*.spec.ts"
  - "playwright.config.*"
```

**`context: fork` (VS Code)** — run the skill body as an isolated subagent instead of loading it inline:

```yaml
context: fork
```

**`user-invocable: false` + `argument-hint`** — background knowledge with no `/` menu entry (independent of `disable-model-invocation`, which blocks autonomous invocation):

```yaml
user-invocable: false
argument-hint: "[test-file]"
```

## Provenance Metadata (Recommended)

When documenting where content came from, add provenance under `metadata.provenance` in frontmatter:

```yaml
metadata:
  provenance:
    mirror: "https://github.com/example-org/skills/tree/main/excel-processing"
```

```yaml
metadata:
  provenance:
    adaptedFrom: "https://github.com/example-upstream/skills/tree/main/excel-processing"
```

A plain string (or array of strings) means the **whole file** derives from that upstream. When only part of it landed locally, use the `url`/`took` object form — a fidelity label, then what was taken:

```yaml
metadata:
  provenance:
    adaptedFrom:
      - url: "https://github.com/example-upstream/skills/tree/main/excel-processing"
        took: "Partly derived. The column-mapping rules."
```

`took` is single-line. Labels: `Inspiration only.` / `Structural echo only.` / `Partly derived.` / `Largely derived.` It lets the `meta-upstream-sync` audit close an upstream change without a merge review when the change touches nothing on the list. Never record what was *not* taken, or a line-overlap measurement — both rot without any local change to trigger a refresh.

> **APM-first rule:** Before creating a `mirror` entry, verify the upstream content isn't available as an APM package. APM dependencies (declared in `apm.yml`) don't need provenance tracking — they're managed externally. Use `mirror` only for exceptional cases where APM cannot manage the content.

- `metadata.provenance.mirror`: canonical upstream URL for exact copies
- `metadata.provenance.adaptedFrom`: source URL (string) or list of URLs (array) when locally adapted/synthesised
- `metadata.provenance.authoritativeSpec`: array of URLs for authoritative format specifications (informational only)

Use this same convention for prompt, instruction, skill, and agent files.
