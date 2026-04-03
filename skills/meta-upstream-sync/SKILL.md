---
name: "meta-upstream-sync"
description: "Deterministic workflow and scripts to audit third-party source updates for local customization files using metadata.provenance.mirror or metadata.provenance.adaptedFrom patterns. Use when checking whether copied (mirror) or adapted files should be refreshed. Keywords: source drift, adaptedFrom, mirror, sync, update audit."
license: "MIT"
compatibility: "Primary automation requires PowerShell 7+ to run ./scripts/check-updates.ps1. If PowerShell is unavailable, reproduce the workflow with equivalent repository or MCP tools and report the fallback used."
---

# meta-upstream-sync

Deterministically audit local files by discovering `metadata.provenance.mirror` and `metadata.provenance.adaptedFrom` in frontmatter, then comparing upstream and local commit dates.

## Compatibility

- Primary automation is [Update Checker](./scripts/check-updates.ps1), which requires PowerShell 7+
- The workflow itself is portable: if PowerShell is unavailable, reproduce the same audit steps with equivalent git, GitHub, and web-fetch tools and report which fallback path was used
- The command examples below are PowerShell-specific because they target the bundled script directly

## Inputs

- Script: [Update Checker](./scripts/check-updates.ps1)
- URL rules: [Source URL Reference](./references/source-url-reference.md)

## Workflow

1. [ ] Ensure target files include frontmatter with `metadata.provenance.mirror` (mirror) or `metadata.provenance.adaptedFrom` (adapted).
1. [ ] Run [Update Checker](./scripts/check-updates.ps1). When a specific target is already identified, use `-IncludePath` to scope the run — do not run a broad discovery scan first. The script compares each upstream's latest commit date with the local file's last git commit date.
1. [ ] Classify each upstream check as `up_to_date`, `update_available`, `missing_local_commit`, or `fetch_failed`.
1. [ ] For new/uncommitted local files that should be bootstrapped from upstream, add `-AllowNoLocalCommit` (guarded mode) so they can be treated as actionable `update_available` entries. Combine with `-IncludePath` in a single invocation when the target is already known.
1. [ ] For items with `update_available`, run targeted follow-up checks per item using `-IncludePath` with `-IncludeChangeDetails` to gather commit-level upstream change summaries.
1. [ ] For bootstrap scenarios (local file is a stub or empty), fetch the full upstream file content. Commit summaries alone are insufficient when there is no local content to diff against. Use the most specific available tool: prefer GitHub API tools (e.g. `mcp_github_get_file_contents`) for GitHub-hosted sources; fall back to a web-fetch tool for other URLs. Do not use terminal commands (`curl`, `Invoke-WebRequest`).
1. [ ] Recommend next action per the recommendation matrix below. For multi-source files, follow the multi-source synthesis procedure below.

### Recommendation Matrix

| Mode | Status | Action |
|---|---|---|
| `mirror` | `update_available` | Replace from upstream |
| `adapted` (single source) | `update_available` | Merge review |
| `adapted` (multi-source) | one or more `update_available` | Synthesised merge review across all changed upstreams |
| any | `up_to_date` | No action |

### Multi-source Synthesis

When a local file lists multiple URLs under `metadata.provenance.adaptedFrom`, each upstream is checked independently. If more than one upstream flags `update_available`:

1. Run targeted detailed checks for each changed source (`-IncludePath` + `-IncludeChangeDetails`).
2. Compare changes against the local file to identify overlapping vs. independent sections.
3. Recommend a **single merged update** that incorporates relevant upstream changes while preserving local customizations.
4. Flag conflicts where two upstreams changed the same concept differently.

## Guidelines

- When the user identifies a specific target, scope directly with `-IncludePath`. Never run a broad discovery scan when the target is already known. This applies even when the user's phrasing is indirect (e.g. "check out the new stub") — if a specific file is contextually identifiable, treat it as an identified target.
- For bootstrap/stub local files (empty or placeholder content), fetch the full upstream file(s) so the actual content can be reviewed. Commit-level metadata alone is not actionable without source content. Use the most specific available tool for fetching: prefer GitHub API tools (e.g. `mcp_github_get_file_contents`) over generic web-fetch tools when the source is a GitHub URL.
- Treat `adapted` entries as merge-review candidates, not blind replacements.
- For multi-source files, never apply one upstream's changes without considering all upstreams flagged as changed.
- When upstream changes alter workflow, process, or opinionated behavior (not just factual corrections), flag for human review before replication.
- Report unknown or unreachable sources explicitly.
- When a GitHub token is provided interactively, store it in `$env:GITHUB_TOKEN` (or `$env:GH_TOKEN`) immediately. Do not pass tokens inline to individual script invocations.

## Command

```powershell
./skills/meta-upstream-sync/scripts/check-updates.ps1
```

Machine-readable output:

```powershell
./skills/meta-upstream-sync/scripts/check-updates.ps1 -OutputJson
```

Filter by workspace-relative wildcard path:

```powershell
./skills/meta-upstream-sync/scripts/check-updates.ps1 -IncludePath "skills/meta-*/SKILL.md"
```

Combine filter with JSON output:

```powershell
./skills/meta-upstream-sync/scripts/check-updates.ps1 -IncludePath "agents/*.agent.md" -OutputJson
```

Authenticated run (recommended to avoid GitHub API rate limits):

```powershell
$env:GITHUB_TOKEN = "<your-token>"
./skills/meta-upstream-sync/scripts/check-updates.ps1 -OutputJson
```

Alternative explicit token parameter:

```powershell
./skills/meta-upstream-sync/scripts/check-updates.ps1 -GitHubToken "<your-token>" -OutputJson
```

Targeted detailed check for one updated item:

```powershell
./skills/meta-upstream-sync/scripts/check-updates.ps1 -IncludePath "skills/meta-prompt/SKILL.md" -IncludeChangeDetails -MaxChangeCommits 5 -OutputJson
```

Bootstrap check for an uncommitted local file (explicitly guarded):

```powershell
./skills/meta-upstream-sync/scripts/check-updates.ps1 -IncludePath "skills/k8s-standards/SKILL.md" -AllowNoLocalCommit -IncludeChangeDetails -MaxChangeCommits 5 -OutputJson
```

## Notes

- The `metadata.provenance.authoritativeSpec` field is informational only and is not checked by the update script. It declares which specifications the file format conforms to, not where content was sourced from.
- No local manifest is required.
- Comparison uses commit date only: upstream latest commit date for source path vs local file last git commit date.
- Supported source format is currently GitHub repository/tree/blob URLs.
- `metadata.provenance.adaptedFrom` may be a single URL string or a YAML array of URLs for files synthesised from multiple upstream sources.
- When a file has multiple upstreams, each is checked independently and output shows one row per upstream. See the Multi-source Synthesis section above for the recommended grouping procedure.
- `upstreamChanges` commit summaries are opt-in via `-IncludeChangeDetails` to keep the default output concise.
- Use `-MaxChangeCommits` to cap detailed commit payload size for targeted checks (default: `5`).
- Uncommitted local files stay blocked by default (`missing_local_commit`); enable `-AllowNoLocalCommit` only for intentional bootstrap/synthesis from upstream.
- GitHub API auth supports `-GitHubToken` or environment variables `GITHUB_TOKEN`/`GH_TOKEN`; authenticated requests greatly reduce 403 rate-limit failures.
