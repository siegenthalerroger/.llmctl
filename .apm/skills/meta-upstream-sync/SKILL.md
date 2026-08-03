---
name: "meta-upstream-sync"
description: "Audits local customization files for third-party source drift using the metadata.provenance.adaptedFrom pattern, then classifies each as up-to-date, update-available, or missing. ALWAYS use when checking whether an adapted file should be refreshed from upstream. Do not assume an adaptedFrom file is current without running this audit first. Keywords: source drift, adaptedFrom, provenance, sync, update audit."
compatibility: "Primary automation requires PowerShell 7+ to run ./scripts/check-updates.ps1. If PowerShell is unavailable, reproduce the workflow with equivalent repository or MCP tools and report the fallback used."
---

# meta-upstream-sync

Deterministically audit local files by discovering `metadata.provenance.adaptedFrom` in frontmatter, then comparing upstream and local commit dates.

## Scope

This skill audits **locally-committed files** that declare `metadata.provenance.adaptedFrom` in their frontmatter. It does NOT manage APM dependencies — content available from APM-compatible upstream sources should be consumed via `apm.yml` and updated with `apm install -g`.

### Decision: APM Dependency or Local Tracking?

| Question | Yes → | No → |
|---|---|---|
| Is the upstream content available as an APM package? | Use APM dependency (remove local file, add to `apm.yml`) | Continue below |
| Did any of the local file come from upstream? | Use `adaptedFrom` + this skill for drift detection; set `fidelity` to how much was taken, and `license` to the upstream's SPDX id wherever that fidelity copies expression | No tracking needed |

## Compatibility

- Primary automation is [Update Checker](./scripts/check-updates.ps1), which requires PowerShell 7+
- GitHub API calls authenticate via the `gh` CLI by default (`gh auth login`); recommended to avoid rate limits, but the script falls back to unauthenticated (or a supplied token) if `gh` is absent
- The workflow itself is portable: if PowerShell is unavailable, reproduce the same audit steps with equivalent git, GitHub, and web-fetch tools and report which fallback path was used
- The command examples below are PowerShell-specific because they target the bundled script directly

## Inputs

- Script: [Update Checker](./scripts/check-updates.ps1)
- URL rules: [Source URL Reference](./references/source-url-reference.md)

## Workflow

1. [ ] Ensure target files include frontmatter with `metadata.provenance.adaptedFrom`.
1. [ ] Run [Update Checker](./scripts/check-updates.ps1). When a specific target is already identified, use `-IncludePath` to scope the run — do not run a broad discovery scan first. The script compares each upstream's latest commit date with the local file's last git commit date.
1. [ ] Classify each upstream check as `up_to_date`, `update_available`, `missing_local_commit`, or `fetch_failed`.
1. [ ] For new/uncommitted local files that should be bootstrapped from upstream, add `-AllowNoLocalCommit` (guarded mode) so they can be treated as actionable `update_available` entries. Combine with `-IncludePath` in a single invocation when the target is already known.
1. [ ] For items with `update_available`, run targeted follow-up checks per item using `-IncludePath` with `-IncludeChangeDetails` to gather commit-level upstream change summaries.
1. [ ] For bootstrap scenarios (local file is a stub or empty), fetch the full upstream file content. Commit summaries alone are insufficient when there is no local content to diff against. Use the most specific available tool: prefer GitHub API tools (e.g. `mcp_github_get_file_contents`) or `gh api` for GitHub-hosted sources; fall back to a web-fetch tool for other URLs. Do not use unauthenticated terminal commands (`curl`, `Invoke-WebRequest`).
1. [ ] Recommend next action per the recommendation matrix below. For multi-source files, follow the multi-source synthesis procedure below.
1. [ ] After merging anything from upstream, re-check the entry's `fidelity` and `license` before finishing. Taking more than last time raises the fidelity, and a raised fidelity can attach terms that the local file's licence cannot carry. Run `apm run check-licenses` from the repository root; it fails the release gate for exactly this.

### Recommendation Matrix

| Case | Status | Action |
|---|---|---|
| APM-eligible upstream | `update_available` | Recommend converting to an APM dependency |
| Single source | `update_available` | Merge review |
| Multi-source | one or more `update_available` | Synthesised merge review across all changed upstreams |
| `took` present | `update_available` | Scope the merge review to `took` first — if the upstream change touches nothing on its list, close as no action and say so |
| Upstream changed its LICENSE | any | Update the entry's `license`, re-run `apm run check-licenses`, and record the new terms in `scripts/dependency-licenses.yml` |
| any | `up_to_date` | No action |

### Multi-source Synthesis

When a local file lists multiple URLs under `metadata.provenance.adaptedFrom`, each upstream is checked independently. If more than one upstream flags `update_available`:

1. Run targeted detailed checks for each changed source (`-IncludePath` + `-IncludeChangeDetails`).
2. Compare changes against the local file to identify overlapping vs. independent sections.
3. Recommend a **single merged update** that incorporates relevant upstream changes while preserving local customizations.
4. Flag conflicts where two upstreams changed the same concept differently.

## Guidelines

- When the user identifies a specific target, scope directly with `-IncludePath`. Never run a broad discovery scan when the target is already known. This applies even when the user's phrasing is indirect (e.g. "check out the new stub") — if a specific file is contextually identifiable, treat it as an identified target.
- For bootstrap/stub local files (empty or placeholder content), fetch the full upstream file(s) so the actual content can be reviewed. Commit-level metadata alone is not actionable without source content. Use the most specific available tool for fetching: prefer GitHub API tools (e.g. `mcp_github_get_file_contents`) or `gh api` over generic web-fetch tools when the source is a GitHub URL.
- Treat `adapted` entries as merge-review candidates, not blind replacements.
- A merge that pulls across more text than before raises `fidelity`, which can attach upstream terms the local file's licence cannot carry. Update `fidelity` and `license` in the same edit, never in a follow-up.
- An entry whose object form loses its `url` drops out of this audit silently — no error, no row. After editing any provenance block, confirm the file still appears in the output.
- For multi-source files, never apply one upstream's changes without considering all upstreams flagged as changed.
- When upstream changes alter workflow, process, or opinionated behavior (not just factual corrections), flag for human review before replication.
- Report unknown or unreachable sources explicitly.
- The script authenticates to the GitHub API via the `gh` CLI (`gh auth token`) by default — ensure `gh auth login` has been run. `-GitHubToken` or `$env:GITHUB_TOKEN`/`$env:GH_TOKEN` override this only for CI or non-`gh` environments.

## Command

```powershell
./.apm/skills/meta-upstream-sync/scripts/check-updates.ps1
```

Machine-readable output:

```powershell
./.apm/skills/meta-upstream-sync/scripts/check-updates.ps1 -OutputJson
```

Filter by workspace-relative wildcard path. Paths are matched with `-like`, where
`*` also spans `/`, so a trailing fragment is usually the shortest correct filter:

```powershell
./.apm/skills/meta-upstream-sync/scripts/check-updates.ps1 -IncludePath "packages/*/.apm/skills/meta-*/SKILL.md"
```

Combine filter with JSON output:

```powershell
./.apm/skills/meta-upstream-sync/scripts/check-updates.ps1 -IncludePath "packages/*/.apm/agents/*.agent.md" -OutputJson
```

Authentication is automatic via the `gh` CLI (`gh auth login`) — no token flag needed. For CI or non-`gh` environments, override with an env var or the `-GitHubToken` parameter:

```powershell
$env:GITHUB_TOKEN = "<your-token>"   # or: -GitHubToken "<your-token>"
./.apm/skills/meta-upstream-sync/scripts/check-updates.ps1 -OutputJson
```

Targeted detailed check for one updated item:

```powershell
./.apm/skills/meta-upstream-sync/scripts/check-updates.ps1 -IncludePath "*/meta-prompt/SKILL.md" -IncludeChangeDetails -MaxChangeCommits 5 -OutputJson
```

Bootstrap check for an uncommitted local file (explicitly guarded):

```powershell
./.apm/skills/meta-upstream-sync/scripts/check-updates.ps1 -IncludePath "*/k8s-standards/SKILL.md" -AllowNoLocalCommit -IncludeChangeDetails -MaxChangeCommits 5 -OutputJson
```

## Notes

- The `metadata.provenance.authoritativeSpec` field is not checked by the update script — it declares which specifications the file format conforms to, not where content was sourced from. It is **not** inert, though: `scripts/check-licenses.py` reads it too, treating a bare URL as a citation that reproduces nothing.
- No local manifest is required.
- Comparison uses commit date only: upstream latest commit date for source path vs local file last git commit date.
- Supported source format is currently GitHub repository/tree/blob URLs.
- `metadata.provenance.adaptedFrom` may be a single URL string, a YAML array of URLs, or an array of objects carrying `url` plus any of `license` / `fidelity` / `took`. String and array forms mean the whole file derives from those upstreams; the object form narrows it and records the terms it arrives under. All three fields are echoed on the result row. See [Source URL Reference](./references/source-url-reference.md).
- When recording a new adaptation, keep the three fields separate: `fidelity` carries the obligation level (`inspiration-only` / `structural-echo` / `partly-derived` / `largely-derived`), `license` the upstream's SPDX id, and `took` **only what was taken** — no fidelity label, no "Not taken" half, no "Original locally" half, no measurement. Omit `took` entirely at `largely-derived`; "the whole file" is what the fidelity already says.
- When a file has multiple upstreams, each is checked independently and output shows one row per upstream. See the Multi-source Synthesis section above for the recommended grouping procedure.
- `upstreamChanges` commit summaries are opt-in via `-IncludeChangeDetails` to keep the default output concise.
- Use `-MaxChangeCommits` to cap detailed commit payload size for targeted checks (default: `5`).
- Uncommitted local files stay blocked by default (`missing_local_commit`); enable `-AllowNoLocalCommit` only for intentional bootstrap/synthesis from upstream.
- GitHub API auth defaults to the `gh` CLI login (`gh auth token`); `-GitHubToken` and `GITHUB_TOKEN`/`GH_TOKEN` are optional overrides. Authenticated requests greatly reduce 403 rate-limit failures.
