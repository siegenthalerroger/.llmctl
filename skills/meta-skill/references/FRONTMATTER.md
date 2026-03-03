# SKILL.md Frontmatter Examples

## Description

**Good description:**

```yaml
description: Toolkit for testing local web applications using Playwright. Use when asked to verify frontend functionality, debug UI behavior, capture browser screenshots, check for visual regressions, or view browser console logs. Supports Chrome, Firefox, and WebKit browsers.
```

**Poor description:**

```yaml
description: Web testing helpers
```

The poor description fails because:

- No specific triggers (when should Copilot load this?)
- No keywords (what user prompts would match?)
- No capabilities (what can it actually do?)

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

- `metadata.provenance.mirror`: canonical upstream URL for exact copies
- `metadata.provenance.adaptedFrom`: source URL (string) or list of URLs (array) when locally adapted/synthesised
- `metadata.provenance.authoritativeSpec`: array of URLs for authoritative format specifications (informational only)

Use this same convention for prompt, instruction, skill, and agent files.
