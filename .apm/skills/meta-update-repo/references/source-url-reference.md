# Source URL Reference

How `llmctl-check-updates` ([check_updates.py](../../../../src/llmctl/check_updates.py)) finds, parses and judges provenance URLs. What to *write* in a provenance block — the forms to choose, what `fidelity`, `license` and `took` mean, how to cite a book — is authoring guidance owned by [meta-steering's provenance section](../../../../packages/core/.apm/skills/meta-steering/references/skill-frontmatter.md#provenance-metadata-recommended). This file covers only what the tooling does with it.

## Two modes, one parse

| Mode | Key read | Command |
| --- | --- | --- |
| adapted content (default) | `metadata.provenance.adaptedFrom` | `uv run llmctl-check-updates --repo .` |
| specifications | `metadata.provenance.authoritativeSpec` | the same, with `--specs` |

Both modes parse through [provenance.py](../../../../src/llmctl/provenance.py), the same parse the `licences` gate uses.

- **Files read:** only `SKILL.md`, `*.agent.md`, `*.instructions.md` and `*.prompt.md` under `packages/` and `.apm/`. A `references/*.md` page is never audited, even if it has frontmatter. `apm_modules/`, the deploy mirrors (`.claude/`, `.agents/`, `.codex/`, `.github/`), `build/` and `LICENSES/` are skipped.
- **Scoping:** `--include PATTERN` keeps matching paths and `--exclude PATTERN` (repeatable) drops them. A pattern with no `*`, `?` or `[` is a substring match; one with a wildcard is a whole-path, case-sensitive glob where `*` spans `/`. Every `llmctl-*` command that filters paths uses this matcher.
- **Output:** the text report prints status, file, source, reason and recommendation. `took`, `license` and `fidelity` are **only in `--json`**, so a review that scopes by `took` needs `--json`.
- **Exit code:** 1 only when no source matched the filters. Every per-URL failure is a row, never an exit code.

## Accepted forms

Both keys accept the same three forms, and they may be mixed within one array:

```yaml
metadata:
  provenance:
    adaptedFrom: "https://github.com/owner/repo/blob/main/path/to/file.md"   # one URL
    authoritativeSpec:
      - "https://example.com/spec"                                             # array of URLs
      - url: "https://github.com/owner/repo/blob/main/path/to/file.md"         # object form
        license: MIT
        fidelity: partly-derived
        took: "The X contract and the Y ordering rule."
```

Parser facts:

- An array produces one row per URL. Every URL is compared against the same local commit date, so one file can show `update_available` for one upstream and `up_to_date` for another.
- `license`, `fidelity` and `took` are read as YAML scalars. Block scalars (`|`, `>`) parse; a multi-line `took` arrives with its newlines intact.
- An absent `fidelity` defaults to `largely-derived` under `adaptedFrom` and to `inspiration-only` under `authoritativeSpec`. That default decides whether the `licences` gate requires a `license`.
- An object entry with no `url`, or a key that yields no entries, is dropped from the audit **without a row**. The `licences` gate reports both as errors ("parses to nothing"), so run `uv run llmctl-check --repo . --only licences` after editing a provenance block. That is the only place the drop shows.

## GitHub URLs

Either key, any mode, when the host is `github.com`:

| URL | Read as |
| --- | --- |
| `https://github.com/{owner}/{repo}` | the default branch, whole repository |
| `https://github.com/{owner}/{repo}/blob/{ref}/{path}` | one file at `ref` |
| `https://github.com/{owner}/{repo}/tree/{ref}/{path}` | one directory at `ref` |

Anything else on `github.com` is a `fetch_failed` row ("Unsupported GitHub URL structure").

1. The local file's last commit date comes from `git log`. With none, the row is `missing_local_commit` unless `--allow-no-local-commit` is passed. With that flag, it is `update_available` with a bootstrap recommendation.
2. `contents/{path}` is probed at `ref`. A 404 is `source_missing`. Without this probe, a deleted path would still report a date: the date of the commit that deleted it.
3. The newest upstream commit touching `path` at `ref` is compared with the local date. The row is `update_available` only when upstream is newer. `--change-details` adds up to `--max-change-commits` of those commits.

**A `{ref}` that is a commit SHA never moves.** The newest commit at an immutable ref is fixed, so such a row reports `up_to_date` forever. Treat a SHA-pinned permalink as frozen by construction. Re-pin it deliberately when the thing it describes moves on.

## Other hosts

- **`adaptedFrom` mode:** always `not_trackable`. A book, a paper or a vendor page has no revision history to compare.
- **`--specs` mode:** probed over HTTP with `HEAD`, falling back to `GET` on 405/501.
  - Status ≥ 400 is `source_missing`. A site that refuses scripted clients (403, 429) lands here too. Open the URL in a browser before re-pointing it.
  - A network error is `fetch_failed`.
  - No `Last-Modified` header, an unparsable one, or a local file with no commit is `not_trackable`. Many vendor docs sites send no such header, so for them `not_trackable` says nothing about whether the page changed.
  - Otherwise `Last-Modified` is compared with the local commit date.

## Statuses

| Status | Meaning | Counted as |
| --- | --- | --- |
| `up_to_date` | upstream is not newer than the local file's last commit | up to date |
| `update_available` | upstream is newer; or a bootstrap under `--allow-no-local-commit` | update available |
| `source_missing` | the GitHub path is gone, or the page answers ≥ 400 | source missing |
| `not_trackable` | no revision date exists to compare | not trackable, excluded from failures |
| `fetch_failed` | the request failed: bad URL shape, rate limit, network, API error | failed |
| `missing_local_commit` | the local file has never been committed | failed |

An unauthenticated run hits GitHub's rate limit quickly, and the result looks like `fetch_failed` rows on URLs that are fine. The report prints `Auth: unauthenticated` and a tip when that is the case.
