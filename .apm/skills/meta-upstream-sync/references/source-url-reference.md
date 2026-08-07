# Source URL Reference

`check-updates.ps1` auto-discovers tracked files from frontmatter and reads one key:

- `metadata.provenance.adaptedFrom` — URL string, array of URLs, or array of objects

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

### Scoped adaptation (`url` + `license` + `fidelity` + `took`)

Use the object form when only part of the upstream landed locally, or when the upstream's licence has to be recorded. The string and array forms above mean **the whole file** derives from that upstream; the object form narrows it and states the terms it arrives under.

```yaml
metadata:
  provenance:
    adaptedFrom:
      - url: "https://github.com/owner/repo/blob/main/path/to/file.md"
        license: MIT
        fidelity: inspiration-only
        took: "The X contract and the Y ordering rule."
```

`fidelity` is the obligation level. The first two values mean no upstream terms attach, because ideas and structure are not protected expression; the last two mean they do.

| Value | Meaning | Terms attach? |
| --- | --- | --- |
| `inspiration-only` | A concept or framing was reused; effectively no text | no |
| `structural-echo` | Section skeleton or headings, not content | no |
| `partly-derived` | Some sections genuinely derive from upstream | **yes** |
| `largely-derived` | Most of the local file derives from upstream, some near-verbatim | **yes** |

`license` is the SPDX id of the **upstream**, not of the local file — `NONE` where the upstream has no LICENSE file. It is required wherever `fidelity` implies an obligation; `scripts/check-licenses.py` in the repo root reads it to decide what the local file may be licensed under, and fails the build when the two cannot be reconciled.

All three are emitted on the result row (including `-OutputJson`), so a merge review can be dismissed without opening the upstream diff: if the upstream change touches nothing on the `took` list, there is nothing to merge.

**State only what was taken — never what was not.** "Not taken" is an open set: upstream can add sections indefinitely, so that half is wrong the moment upstream grows and no local change ever triggers a refresh. What *was* taken is a closed set bounded by the local file, so it only goes stale when the local file changes — which is exactly when someone is already editing it.

Rules:

- `took` is **single-line** — block scalars (`|`, `>`) are not parsed and their content is lost. The same applies to `license` and `fidelity`
- `took` is optional; its absence, and an absent `fidelity`, both mean the whole file derives from that upstream (`largely-derived`)
- Forms may be mixed within one array (a plain URL string alongside object entries)
- An object entry **must** carry `url`. An entry with only `took` is skipped, and if no other entry supplies a URL the file drops out of the audit entirely — silently, with no error and no row in the output. Check that a provenance block still yields at least one URL after editing it; a file that stops being tracked looks identical to one that has nothing to track

### Keeping `took` minimal

**Test: could this list ever let you close a merge review unread?** If no, use the plain string form.

- **Wholly derived or near-verbatim files** — if almost any upstream change would matter, there is nothing to dismiss. Give the entry `fidelity: largely-derived` and omit `took`; that already says "this whole file derives from that upstream", which is shorter and more accurate. Listing what was taken there misreads a copy as a selective adaptation
- **Never write a "Not taken" or "Original locally" half** — see above; both are open sets that rot silently
- **Never record point-in-time measurements** (line-overlap percentages, file sizes, line counts). Both sides move, so the number is wrong by the next release and no process refreshes it. `fidelity` carries the same signal durably; put any measurement in the commit message that motivated the change
- **Do not overload the field.** `took` records *what was taken*. The upstream's licence goes in `license`, the obligation level in `fidelity`, and follow-up work wherever the project tracks work — putting any of it here turns the one place a reader looks for scope into something they have to skim
- A short note on **why the URL is not a line-for-line comparison base** (upstream moved or restructured the adapted path) does belong — it changes how the next reviewer reads the diff

## Supported URL Formats

Currently supported host: `github.com`

- Repository root:
  - `https://github.com/{owner}/{repo}`
- File URL:
  - `https://github.com/{owner}/{repo}/blob/{ref}/{path}`
- Directory URL:
  - `https://github.com/{owner}/{repo}/tree/{ref}/{path}`

### Sources with no revision history

A provenance source is not always a repository. A book, a paper or a vendor documentation page is a legitimate `adaptedFrom` entry — it is where the material came from — but there is no commit date to compare against, so drift detection cannot say anything about it.

Those entries are reported as **`not_trackable`**, counted separately in the summary, and excluded from `failedCount`. They are not a problem to fix; the status records that the audit deliberately has no opinion. Do not "resolve" one by deleting the entry — that drops the attribution the entry exists to carry.

Give a book a resolver URL rather than a bookshop or publisher link, so it stays valid: `https://openlibrary.org/isbn/{isbn}` for an ISBN, `https://doi.org/{doi}` where a DOI exists. Cite the specific edition — an ISBN identifies one, and page-level claims do not survive an edition change.

## Comparison Rule

For each tracked local file and each upstream URL:

1. If the host has no revision history, record `not_trackable` and stop.
2. Read local file last git commit date.
3. Query upstream latest commit date for the referenced ref/path.
4. Recommend update only when `upstreamDate > localDate`.

For multi-source files, every upstream is compared against the same local commit date. A file may show `update_available` for some upstreams and `up_to_date` for others.

This removes the need for a local tracking manifest.
