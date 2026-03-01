# Contributing

## Repository Frontmatter Provenance Convention

This repository defines a local provenance convention for customization files (`*.agent.md`, `*.prompt.md`, `*.instructions.md`, `*/SKILL.md`).

Use the following metadata keys in YAML frontmatter:

Single-source:

```yaml
metadata:
  source: "https://example.com/canonical/upstream"
  adaptedFrom: "https://example.com/original/that-was-adapted"
```

Multi-source (synthesised from multiple upstreams):

```yaml
metadata:
  adaptedFrom:
    - "https://github.com/org-a/repo/blob/main/skill.md"
    - "https://github.com/org-b/repo/blob/main/skill.md"
```

- `metadata.source`: Canonical upstream/original source URL or reference
- `metadata.adaptedFrom`: URL (string) or list of URLs (array) when local content is adapted/synthesised from upstream sources

This is a **repository convention**, not a universal standard.

For instruction files, a top-level `source` field may still be used for tooling compatibility; it can coexist with `metadata.source`.

## Upstream Update Tooling

Use the `meta-updater` agent together with the `meta-upstream-sync` skill to audit and synthesize upstream updates.

For GitHub API authentication, use a **Fine-grained Personal Access Token** whenever possible:

- Repository access: only the repositories you need to audit
- Repository permissions: `Contents` = **Read-only**
- No write permissions are required for update checks

Provide the token via `GITHUB_TOKEN`/`GH_TOKEN`, or pass `-GitHubToken` to `./skills/meta-upstream-sync/scripts/check-updates.ps1`.
