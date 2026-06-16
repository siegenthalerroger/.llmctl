# Source URL Reference

`check-updates.ps1` auto-discovers tracked files from frontmatter and reads these keys:

- `metadata.provenance.mirror` => tracked as `mirror` (single URL)
- `metadata.provenance.adaptedFrom` => tracked as `adapted` (single URL string or YAML array of URLs)

`adaptedFrom` takes precedence when both exist.

### Mirror (exact copy)

```yaml
metadata:
  provenance:
    mirror: "https://github.com/owner/repo/blob/main/path/to/file.md"
```

### Single-source adapted

```yaml
metadata:
  provenance:
    adaptedFrom: "https://github.com/owner/repo/blob/main/path/to/file.md"
```

### Multi-source adapted (synthesised)

```yaml
metadata:
  provenance:
    adaptedFrom:
      - "https://github.com/owner-a/repo-a/blob/main/skill.md"
      - "https://github.com/owner-b/repo-b/blob/main/skill.md"
```

Each URL in the array is checked independently. The script emits one result row per upstream URL.

## Supported URL Formats

Currently supported host: `github.com`

- Repository root:
  - `https://github.com/{owner}/{repo}`
- File URL:
  - `https://github.com/{owner}/{repo}/blob/{ref}/{path}`
- Directory URL:
  - `https://github.com/{owner}/{repo}/tree/{ref}/{path}`

## Comparison Rule

For each tracked local file and each upstream URL:

1. Read local file last git commit date.
2. Query upstream latest commit date for the referenced ref/path.
3. Recommend update only when `upstreamDate > localDate`.

For multi-source files, every upstream is compared against the same local commit date. A file may show `update_available` for some upstreams and `up_to_date` for others.

This removes the need for a local tracking manifest.
