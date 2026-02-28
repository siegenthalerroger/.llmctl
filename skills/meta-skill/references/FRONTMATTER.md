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

When documenting where content came from, add provenance under `metadata` in frontmatter:

```yaml
metadata:
	source: "https://github.com/example-org/skills/tree/main/excel-processing"
	adaptedFrom: "https://github.com/example-upstream/skills/tree/main/excel-processing"
```

- `metadata.source`: canonical upstream/original source URL or reference
- `metadata.adaptedFrom`: source URL/reference when locally adapted

Use this same convention for prompt, instruction, skill, and agent files.
