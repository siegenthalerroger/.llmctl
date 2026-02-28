---
name: "upstream-sync"
description: "Deterministic workflow and scripts to audit third-party source updates for local customization files using metadata.source or metadata.adaptedFrom patterns. Use when checking whether copied (mirror) or adapted files should be refreshed. Keywords: source drift, adaptedFrom, mirror, sync, update audit."
license: "MIT"
metadata:
  source: ""
---

# Upstream Sync

Deterministically audit local files by discovering `metadata.source` and `metadata.adaptedFrom` in frontmatter, then comparing upstream and local commit dates.

## Inputs

- Script: [Update Checker](./scripts/check-updates.ps1)
- URL rules: [Source URL Reference](./references/source-url-reference.md)

## Workflow

1. [ ] Ensure target files include frontmatter with `metadata.source` (mirror) or `metadata.adaptedFrom` (adapted).
1. [ ] Run [Update Checker](./scripts/check-updates.ps1) to discover tracked files automatically.
1. [ ] For each tracked file (and each upstream URL), compare upstream latest commit date with local file last commit date.
1. [ ] Classify each upstream check as `up_to_date`, `update_available`, `missing_local_commit`, or `fetch_failed`.
1. [ ] Recommend next action:
  - `mirror` + `update_available` => recommend replace from upstream.
  - `adapted` (single source) + `update_available` => recommend merge review.
  - `adapted` (multi-source) + one or more `update_available` => recommend synthesised merge review across all changed upstreams.
  - `up_to_date` => no action.

## Command

```powershell
./skills/upstream-sync/scripts/check-updates.ps1
```

Machine-readable output:

```powershell
./skills/upstream-sync/scripts/check-updates.ps1 -OutputJson
```

Filter by workspace-relative wildcard path:

```powershell
./skills/upstream-sync/scripts/check-updates.ps1 -IncludePath "skills/meta-*/SKILL.md"
```

Combine filter with JSON output:

```powershell
./skills/upstream-sync/scripts/check-updates.ps1 -IncludePath "agents/*.agent.md" -OutputJson
```

## Notes

- No local manifest is required.
- Comparison uses commit date only: upstream latest commit date for source path vs local file last git commit date.
- Supported source format is currently GitHub repository/tree/blob URLs.
- `metadata.adaptedFrom` may be a single URL string or a YAML array of URLs for files synthesised from multiple upstream sources.
- When a file has multiple upstreams, each is checked independently and output shows one row per upstream. The agent groups these rows when recommending a synthesised update.
