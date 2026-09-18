# Working with this Repository

This file defines conventions for AI agents editing files in `.llmctl`.

## What this repo is

`.llmctl` is a personal collection of agent steering files (agents, skills, instructions, prompts, hooks, plugins) deployed to agent harnesses via [APM](https://github.com/microsoft/apm).

It is an **APM monorepo of context-scoped sub-packages**, so each context loads only what it needs.

Each `packages/<name>/` is a standalone APM package (`apm.yml` + `.apm/` layout). Adding a primitive means placing it in the correct sub-package by scope — do not add it to the root `.apm/` unless it operates on this repository itself. See the [packaging model in CONTRIBUTING.md](CONTRIBUTING.md#packaging-model).

Content that cannot be published lives in a **separate private workspace**, not in `packages/` here — this repo and its marketplace are public. That workspace has the same layout minus `scripts/`, and borrows this repo's release scripts via `--repo`/`--marketplace`.

## Upstream dependencies

Upstream-sourced content is declared in the relevant package's `apm.yml` (`packages/*/apm.yml`), pinned to a full commit SHA, and resolved in that package's committed `apm.lock.yaml`. MCP servers are scoped per package: universal dev servers in `packages/core/apm.yml`, cloud/IaC doc servers in `packages/ops/apm.yml`.

A pin and its lockfile move only through `apm run update`, in one commit, after the `meta-update-repo` skill's safety review has read the upstream diff. Nothing about that is `apm install --frozen`'s job — see [Lockfiles](CONTRIBUTING.md#lockfiles) for why.

## Authoring rules

This is a quick reference, see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed descriptions.

- **Descriptions (all types):** single-line, front-loaded, name-first. Shape as a directive with an explicit negative constraint ("ALWAYS invoke when … Do not … without this skill") — keyword density is not the activation lever. Stay within budgets (skill `description` ≤ 1024 chars). See the [meta-steering description rules](packages/core/.apm/skills/meta-steering/SKILL.md#3-description-craft--all-four-types); the frontmatter hook enforces the mechanical limits.
- **Skills:** portable frontmatter is `name` + `description`. Additional fields are defined as a repo convention.
- **Agents:** prefer structural tool constraints (`tools`, `disallowedTools`) over prose-based role restrictions. Add `disable-model-invocation: true` to side-effectful agents that should not be auto-selected.
- **Instructions:** keep narrow — their main job is forcing skill loading via `applyTo` patterns.
- **Prompts:** one slash-command per file. Keep the body concise.
- **Hooks:** deterministic, event-driven guardrails/side-effects only — not behavioral steering. Prefer cross-platform (Python/Node) scripts. Name definition files `*.hook.json`.
- **Plugins:** bundled distribution of multiple components. Add only when shipping a curated subset for marketplace/external use.
- **Provenance:** track upstream sources via `metadata.provenance.{adaptedFrom,authoritativeSpec}` — prefer APM dependencies over vendored copies. On the object form, `license` (upstream SPDX id) and `fidelity` (`inspiration-only`/`structural-echo`/`partly-derived`/`largely-derived`) are required wherever expression was copied; `took` records only what was taken.
- **Licensing:** `*.md` is CC-BY-SA-4.0, everything else MIT — see [LICENSE](LICENSE). A file adapting an upstream whose terms the default cannot satisfy declares a top-level `license:` in its frontmatter. Run `apm run check` after touching provenance or adding a dependency.
- **Scripts:** one file per command under `scripts/`, run with `uv run` — each entry script declares its own dependencies in a PEP 723 header, so there is no `pyproject.toml` and nothing to install first. The `scripts:` block in [apm.yml](apm.yml) is the index: `check`, `update`, `check-updates`, `versions`, `release`, `pack-marketplace`, in the order you would run them.

## Commits

Conventional, and enforced by a gate rather than trusted:

```text
<type>(<scope>): <description>
```

`type` ∈ `feat` `fix` `docs` `refactor` `chore` `test` `build` `ci`; `!` before the colon marks a breaking change. `scope` is optional, and when present must name a package the commit touched (`core`, `workflow`, …) or an area outside `packages/` (`scripts`, `ci`, `meta`, `docs`, `repo`).

The type no longer sizes anything — versions are calendar-derived — it decides which heading the commit lands under in the release notes. Which package a commit releases comes from the paths it touched. Prose for the notes goes in the pull request body under a `## Release notes` heading. See [CONTRIBUTING.md](CONTRIBUTING.md#commit-convention).

## Do not do

- Don't ignore the conventions defined in this repository, see [CONTRIBUTING.md](CONTRIBUTING.md)
- **Don't edit anything in the marketplace repositories.** Every file there is generated, and a release deletes whatever it did not produce. The sources are here: `README.marketplace.md`, `LICENSE.marketplace`, `.gitignore.marketplace`, `apm.marketplace.yml`, and the packages themselves.
- **Don't hand-edit `packages/*/apm.lock.yaml`,** and don't refresh one on its own. It moves with its `apm.yml` pin, in one commit, through `apm run update`.
- **Don't edit `version:` in a package manifest.** It is a placeholder; the release stamps the real calendar version into a scratch copy and records it as a tag.
