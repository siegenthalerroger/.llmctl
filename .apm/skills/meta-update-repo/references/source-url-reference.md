# Source URL Reference

How `llmctl-check-updates` ([check_updates.py](../../../../src/llmctl/check_updates.py)) finds, parses and judges provenance URLs. What to *write* in a provenance block — which key a source belongs under, the forms to choose, what `fidelity`, `license` and `took` mean, where a reference page or a script declares its upstream, how to cite a book — is authoring guidance owned by [meta-steering's provenance reference](../../../../packages/baseline/.apm/skills/meta-steering/references/provenance.md). This file covers only what the tooling does with it.

## Two modes, one parse

| Mode | Key read | Command |
| --- | --- | --- |
| adapted content (default) | `metadata.provenance.adaptedFrom`: ordinary adaptations and borrowed material | `uv run llmctl-check-updates --repo .` |
| binding sources | `metadata.provenance.authoritativeSpec`: format specifications, technical contracts, operational requirements, organizational standards | the same, with `--specs` |

Both modes parse through [provenance.py](../../../../src/llmctl/provenance.py), the same parse the `licences` gate uses.

- **Files read:** every `*.md` file under `packages/` and `.apm/` that declares provenance, so primitives (`SKILL.md`, `*.agent.md`, `*.instructions.md`, `*.prompt.md`) and `references/*.md` pages alike. A reference page declares its own upstream and `SKILL.md` never stands in for it, so each is a row on its own file. Non-Markdown files (scripts, assets, templates) carry no frontmatter and are never read: a source-derived one is attributed in its owning Markdown file's entry, and the row is that file's. `apm_modules/`, the deploy mirrors (`.claude/`, `.agents/`, `.codex/`, `.github/`), `build/` and `LICENSES/` are skipped.
- **Scoping:** `--include PATTERN` keeps matching paths and `--exclude PATTERN` (repeatable) drops them. A pattern with no `*`, `?` or `[` is a substring match; one with a wildcard is a whole-path, case-sensitive glob where `*` spans `/`. Every `llmctl-*` command that filters paths uses this matcher.
- **Output:** the text report prints status, file, source, reason and recommendation. `kind` (the provenance key), `took`, `license` and `fidelity` are **only in `--json`**, so a review needs `--json` to see them.
- **Ownership:** the filters partition the files, so each is audited once. `meta-refresh-steering` includes the `meta-steering/` and `meta-harness/` directories, and `meta-update-repo` phase D excludes those same two and `meta-update-models/`; a reference page under any of them goes with its skill.
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
- `license`, `fidelity` and `took` are read as YAML strings. Block scalars (`|`, `>`) parse; a multi-line `took` arrives with its newlines intact.
- An absent `fidelity` defaults to `largely-derived` under `adaptedFrom`, and to `inspiration-only` under `authoritativeSpec` for a bare URL and for an object entry with no `took`. That default decides whether the `licences` gate requires a `license`. An `authoritativeSpec` object entry that records `took` with no `fidelity` is a `licences` error: the gate never infers a fidelity from `took`.
- `took` is carried into the row and nothing else: the audit does not read it, so it cannot narrow what a row recommends. What a row calls for depends on the key: `update_available` under `adaptedFrom` recommends `review_and_merge_from_upstream` (`bootstrap_review_and_merge_from_upstream` for a bootstrap), and under `authoritativeSpec` it recommends `assess_all_normative_content` (`bootstrap_assess_all_normative_content`), whichever host the source is on.
- The row is dated from the last commit of the file that declares the entry. A script re-synced from upstream keeps flagging until the Markdown file that names it is committed with it.

**What the parser reports instead of reading.** Provenance is read only from `metadata.provenance`, a non-empty mapping that holds `adaptedFrom`, `authoritativeSpec` or both. An entry read from there is *tracked*: the `licences` gate checks its licence, the generated notices carry it, and the drift audit dates it. Each shape below is reported as malformed, as a `licences` error whose message ends with the consequence shown, and the parser does not read it:

| Reported | The message ends |
| --- | --- |
| A provenance block outside `metadata.provenance`, anywhere in the frontmatter: a `provenance` block at the top level, `adaptedFrom` or `authoritativeSpec` at the top level or directly under `metadata`, or any of them nested deeper (`metadata.metadata.provenance`). Case, separator, dotted and near-miss spellings count (`Provenance`, `metadata_provenance`, `provenace`, `Metadata`, a single dotted key such as `metadata.provenance.adaptedFrom:`). It is reported even beside a valid `metadata.provenance`, which is still read | nothing in it is tracked |
| A `metadata` holding a value that is not a mapping (an empty `metadata:` is not reported), or a `metadata.provenance` that is a string, a list, a number, null or `{}` | nothing in it is tracked |
| A key under `metadata.provenance` other than `adaptedFrom` and `authoritativeSpec`, such as `adapted_from` or `license`. The keys beside it are still read | nothing in it is tracked |
| A key whose value is neither a URL nor a list, or is an empty list | nothing in it is tracked |
| An entry with no `url`, or whose `url` is not a string | this entry is not tracked |
| A field on an object entry other than `url`, `license`, `fidelity` and `took`, such as `licence`, `fidelty` or `Took`. The message names the allowed fields, and the nearest when one is close | the field is ignored, so the entry is judged without it (this entry is not tracked, when it also has no `url`) |
| A `license`, `fidelity` or `took` that is not a string: a list, a mapping, a boolean, a number or a date. YAML 1.1 reads an unquoted `took: no` as `false` | the field is ignored, so the entry is judged without it |
| The file's own licence anywhere but the top-level `license` field: `metadata.license`, `metadata.licence`, or a top-level `licence`, `License` or `licenses` | it stays `<licence>`, the declared top-level `license` or else the repo default |
| Frontmatter that does not parse as YAML | none of this frontmatter is read, so the file declares no provenance and no licence |

The drift audit and the notices never read these messages: whatever is not tracked is absent from both, **without a row**. Run `uv run llmctl-check --repo . --only licences` after editing a provenance block. It is the only place these show.

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
