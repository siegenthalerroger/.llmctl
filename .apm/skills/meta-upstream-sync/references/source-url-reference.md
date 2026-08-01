# Source URL Reference

`check-updates.ps1` auto-discovers tracked files from frontmatter and reads these keys:

- `metadata.provenance.mirror` => tracked as `mirror` (single URL)
- `metadata.provenance.adaptedFrom` => tracked as `adapted` (URL string, array of URLs, or array of `url`/`took` objects)

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

### Partial adaptation (`url` + `took`)

Use the object form when only part of the upstream landed locally. The string and array forms above mean **the whole file** derives from that upstream; the object form narrows it.

```yaml
metadata:
  provenance:
    adaptedFrom:
      - url: "https://github.com/owner/repo/blob/main/path/to/file.md"
        took: "Inspiration only. The X contract and the Y ordering rule."
```

Shape: **a fidelity label, then what was taken.** Nothing else.

| Label | Meaning |
| --- | --- |
| `Inspiration only.` | A concept or framing was reused; effectively no text |
| `Structural echo only.` | Section skeleton or headings, not content |
| `Partly derived.` | Some sections genuinely derive from upstream |
| `Largely derived.` | Most of the local file derives from upstream, some near-verbatim |

`took` is emitted verbatim on the result row (including `-OutputJson`), so a merge review can be dismissed without opening the upstream diff: if the upstream change touches nothing on the list, there is nothing to merge.

**State only what was taken — never what was not.** "Not taken" is an open set: upstream can add sections indefinitely, so that half is wrong the moment upstream grows and no local change ever triggers a refresh. What *was* taken is a closed set bounded by the local file, so it only goes stale when the local file changes — which is exactly when someone is already editing it.

Rules:

- `took` is **single-line** — block scalars (`|`, `>`) are not parsed and their content is lost
- `took` is optional; its absence means the whole file derives from that upstream
- Forms may be mixed within one array (a plain URL string alongside `url`/`took` objects)
- An object entry **must** carry `url`. An entry with only `took` is skipped, and if no other entry supplies a URL the file drops out of the audit entirely — silently, with no error and no row in the output. Check that a provenance block still yields at least one URL after editing it; a file that stops being tracked looks identical to one that has nothing to track

### Keeping `took` minimal

**Test: could this list ever let you close a merge review unread?** If no, use the plain string form.

- **Wholly derived or near-verbatim files** — if almost any upstream change would matter, there is nothing to dismiss. The string form already says "this whole file derives from that upstream", which is shorter and more accurate. Adding `took` there misreads a copy as a selective adaptation
- **Never write a "Not taken" or "Original locally" half** — see above; both are open sets that rot silently
- **Never record point-in-time measurements** (line-overlap percentages, file sizes, line counts). Both sides move, so the number is wrong by the next release and no process refreshes it. The label carries the same signal durably; put any measurement in the commit message that motivated the change
- **Do not overload the field.** `took` records *what was taken*. Licensing concerns, follow-up work, and open questions go wherever the project tracks work — putting them here turns the one place a reader looks for scope into something they have to skim
- A short note on **why the URL is not a line-for-line comparison base** (upstream moved or restructured the adapted path) does belong — it changes how the next reviewer reads the diff

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
