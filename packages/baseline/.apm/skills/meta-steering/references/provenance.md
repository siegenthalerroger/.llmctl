# Provenance Metadata

**Contents:** [Keys](#keys) · [Forms](#forms) · [`fidelity` and `license`](#fidelity-and-license) · [`took`](#took) · [Declaring and reading](#declaring-and-reading) · [Other rules](#other-rules)

One convention for every file type this guide covers: skills, agents, instructions, prompts, and the reference pages a skill ships. Provenance lives under `metadata.provenance` in the file's frontmatter. What a skill adds for its bundled files (reference pages, scripts, assets) is in [skill-structure.md](./skill-structure.md#provenance-on-bundled-files).

## Keys

Two keys with different jobs:

| Key | Holds | Why it is listed |
| --- | --- | --- |
| `authoritativeSpec` | **Binding normative sources** governing the file's declared subject: format specifications, technical contracts (APIs, protocols, schemas, algorithms), operational requirements and organizational standards | The file has to conform to it, whether or not any text was copied |
| `adaptedFrom` | **Ordinary adaptations and borrowed material**: sources the work learned from, restructured or reproduced, that do not bind it | The file was shaped by it, and nothing obliges the file to follow it |

**Authority and copying are separate questions.** The key answers the first. The object-form fields `license`, `fidelity` and `took` answer the second, under either key. A binding source whose material was reproduced stays in `authoritativeSpec` as an object entry; do not also list it under `adaptedFrom` because it was copied. Within one file, a source appears under one key.

## Forms

```yaml
metadata:
  provenance:
    authoritativeSpec:
      - "https://example.com/format-spec"                   # binding; nothing reproduced
      - url: "https://github.com/example-upstream/spec/blob/main/format.md"
        license: Apache-2.0        # SPDX id of the upstream, or NONE
        fidelity: partly-derived   # how much of it landed here
        took: "The field table and the ordering rule."
    adaptedFrom:
      - url: "https://github.com/example-upstream/skills/tree/main/excel-processing"
        license: MIT
        fidelity: partly-derived
        took: "The column-mapping rules."
```

Both keys accept the same three forms, which may be mixed in one array: a URL string, an array of URL strings, or an array of objects carrying `url` plus any of `license`, `fidelity` and `took`. A bare `adaptedFrom` URL means the **whole file** derives from that upstream. A bare `authoritativeSpec` URL means **cited and conformed to, nothing reproduced**, which carries no obligation. Prefer the object form wherever anything was reproduced or adapted.

## `fidelity` and `license`

**`fidelity`** is the obligation level. Absent means `largely-derived` under `adaptedFrom` (whole-file derivation) and `inspiration-only` under `authoritativeSpec` (cited, nothing reproduced).

| Value | Meaning | Upstream terms attach? |
| --- | --- | --- |
| `inspiration-only` | A concept or framing was reused; effectively no text | no |
| `structural-echo` | Section skeleton or headings, not content | no |
| `partly-derived` | Some sections genuinely derive from upstream | **yes** |
| `largely-derived` | Most of the local file derives from upstream, up to near-verbatim | **yes** |

**`license`** is the SPDX id of the **upstream**, not of this file. It is required whenever `fidelity` implies an obligation, because it decides what this file may be licensed under: this repository's `licences` gate (`llmctl-check-licenses`, `src/llmctl/check_licenses.py`) rejects a file whose own licence cannot satisfy it. Three values grant no rights at all, and the gate treats them alike: such an upstream is only safe at a fidelity that attaches no terms (`inspiration-only` or `structural-echo`), and the fix for anything more is rewriting rather than attribution.

| Value | For |
| --- | --- |
| `NONE` | A source that states no licence: a repository with no LICENSE file, a book, a blog post |
| `Proprietary` | A vendor documentation site whose terms reserve all rights |
| `NOASSERTION` | An upstream whose licence has not been established yet |

Where terms attach, the upstream also needs a row in `dependency-licenses.yml` with its copyright `holder`: the generated notices take the copyright line from there, and the `pack` gate fails without it.

A file whose upstream obligation cannot be met by the repository default licence declares its own with a top-level `license:` field, whatever its type; see [LICENSE](https://github.com/siegenthalerroger/.llmctl/blob/main/LICENSE).

## `took`

`took` is optional, and it records **borrowing**: what was actually taken from this upstream, nothing else.

- **Single line.**
- **Specific enough to identify the reused material.** Name the rules, tables, sections, procedures or concepts: "The severity tiers and the location / why-it-matters / how-to-fix evidence standard." A vague label such as "the general approach", "the framing" or "the structure" names nothing a reader could find in both files, so it cannot close a drift review.
- **Never an exclusion list** ("not taken", "original locally"). That is an open set: upstream can add sections indefinitely, so it is wrong the moment upstream grows, and no local change ever triggers a refresh.
- **Never a measurement** (line-overlap percentages, sizes, counts). Both sides move; `fidelity` carries the same signal durably. Put a measurement in the commit message that motivated it.
- **Omit it when the whole upstream file was carried over into the declaring file.** A list there misreads a copy as a selective adaptation. A script or asset attributed in its owning `SKILL.md` is the exception: its `took` always names the companion's path, even for a whole-file copy ([skill-structure.md](./skill-structure.md#provenance-on-bundled-files)).
- **Do not overload it.** The licence goes in `license`, the obligation level in `fidelity`, follow-up work in the tracker. The one exception: a short note on why the URL is *not* a line-for-line comparison base (upstream moved or restructured the path), because it changes how the next reviewer reads the diff.
- **Test:** could a reader find each named item in the local file and in the upstream? If not, it is too vague to record.

**`took` is not an update allowlist.** Whether a change needs integrating is decided by what the source is:

| Source | Role of `took` in a drift review |
| --- | --- |
| **Binding** (`authoritativeSpec`) | None. Every changed or newly introduced normative content relevant to the declared subject is assessed, whether or not `took` mentions it. `took` never excludes a new binding requirement |
| **Nonbinding selective adaptation** (`adaptedFrom` with a specific `took`) | The reviewer reads the upstream change and may decide that a change outside the declared borrowing needs no integration. That is a judgement, recorded in the review; it is not an automatic closure |
| **`took` missing or vague** | None. Review the whole change. A missing or vague `took` never justifies dismissing a change |

**Normative content** is what states what the subject must, must not or may do: requirements, constraints, limits, schemas, defaults, deprecations, new mandatory behaviour. Explanation, examples and rationale are not. **The declared subject** is what the declaring file says it governs: a primitive's `description`, or a reference page's title and scope. A change that is irrelevant to the declared subject needs no integration; that conclusion comes from the subject, never from `took`.

## Declaring and reading

- **Copying is declared per file, by the file that contains the copy.** A file's provenance never covers another file's: a skill's `SKILL.md` does not stand in for its reference pages. The licence check, the generated notices and the packed bundle each read a file's own declaration only, and a file with no frontmatter is taken to carry no upstream obligation. A prompt, an instruction or an agent that adapts upstream material declares it in its own frontmatter, with a top-level `license:` where the upstream's terms need one.
- **Keep the entry current.** An edit that adds, removes or rewrites borrowed material updates the entry in the same commit: `took`, `fidelity` (and with it whether `license` is required), or the entry itself once nothing borrowed is left. An upstream relicensing affects this file only if it takes content published under the new licence; what was already taken stays under the terms it was taken under.
- **Provenance is read from the source file and from the packed bundle, never from an installed copy.** `apm pack` keeps `license` and `metadata.provenance` on all four types, so the generated notices see them. `apm install` does not: on APM 0.31.0, the CLI the gates pin, it drops both from a Claude command with a dropped-keys warning, and Claude rules keep only `paths`. That warning on a prompt that carries provenance is expected. Keep the keys (case 2 in [frontmatter-deploy.md](./frontmatter-deploy.md)) and do not read attribution off a deployed copy.
- **Shared binding authority** for a skill, and where reference pages, scripts and assets declare theirs, are in [skill-structure.md](./skill-structure.md#provenance-on-bundled-files).

## Other rules

> **APM-first rule:** Before creating an `adaptedFrom` entry, verify the upstream content isn't available as an APM package. APM dependencies (declared in `apm.yml`) don't need provenance tracking: they're managed externally. Copy locally only where APM cannot manage the content.

**Non-repository sources** (books, papers, vendor pages) are legitimate entries:

- Cite a book by a resolver URL, not a bookshop or publisher page: `https://openlibrary.org/isbn/{isbn}`, or `https://doi.org/{doi}` where a DOI exists.
- Cite the specific edition; page-level claims do not survive an edition change.
- Never "resolve" a `not_trackable` entry by deleting it. The update check cannot track it, but the attribution is what the entry exists to carry.

What the parser accepts, which files the drift audit reads, and how an entry can silently drop out of the audit is in the `meta-update-repo` skill (source repository only), `references/source-url-reference.md`.
