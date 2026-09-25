# Working with this Repository

This file defines conventions for AI agents editing files in `.llmctl`.

## What this repo is

`.llmctl` is a personal collection of agent steering files (agents, skills, instructions, prompts, hooks, plugins) deployed to agent harnesses via [APM](https://github.com/microsoft/apm).

It is an **APM monorepo of context-scoped sub-packages**, so each context loads only what it needs.

Each `packages/<name>/` is a standalone APM package (`apm.yml` + `.apm/` layout). Adding a primitive means placing it in the correct sub-package by scope — do not add it to the root `.apm/` unless it operates on this repository itself. See the [packaging model in CONTRIBUTING.md](CONTRIBUTING.md#packaging-model).

Content that cannot be published lives in a **separate private workspace**, not in `packages/` here — this repo and its marketplace are public. That workspace has the same layout minus the tooling, and runs this repo's commands from git with its own `--repo`/`--marketplace`.

## Upstream dependencies

Upstream-sourced content is declared in the relevant package's `apm.yml` (`packages/*/apm.yml`), pinned to a full commit SHA, and resolved in that package's committed `apm.lock.yaml`. MCP servers are scoped per package: universal dev servers in `packages/baseline/apm.yml`, domain servers in their domain package (`ops`, `travel`).

A pin and its lockfile move only through the `meta-update-repo` skill — `apm run update` for a bump, its new-dependency phase for an addition — in one commit, after its safety review has read the upstream content. Nothing about that is `apm install --frozen`'s job — see [Lockfiles](CONTRIBUTING.md#lockfiles) for why.

## Authoring rules

Load the owning skill before creating or editing any customization file. The rules live there and are not repeated here:

- [`meta-steering`](packages/baseline/.apm/skills/meta-steering/SKILL.md): skills, agents, instructions, prompts, including frontmatter per harness, descriptions and provenance fields.
- [`meta-harness`](packages/baseline/.apm/skills/meta-harness/SKILL.md): hooks, MCP servers, plugin bundles.

Repository-only rules:

- **Licensing:** `*.md` is CC-BY-SA-4.0, everything else MIT — see [LICENSE](LICENSE) and [Licensing](CONTRIBUTING.md#licensing). Run `apm run check` after touching provenance or adding a dependency.
- **Tooling:** a uv project — [pyproject.toml](pyproject.toml), one module per command under `src/llmctl/`, one `llmctl-<command>` console script each — run with `uv run`, which syncs the locked environment first. `uv.lock` moves only through `uv lock`. Run `uv run ruff format src/ && uv run ruff check src/ && uv run ty check src/` before committing; the `tooling` gate runs exactly those three plus `uv lock --check`. The `scripts:` block in [apm.yml](apm.yml) is the index of commands.

## Commits

Conventional, and enforced by a gate rather than trusted:

```text
<type>(<scope>): <description>
```

`type` ∈ `feat` `fix` `docs` `refactor` `chore` `test` `build` `ci`; `!` before the colon marks a breaking change. `scope` is optional, and when present must name a package the commit touched (`baseline`, `workflow`, …) or an area outside `packages/` (`tooling`, `ci`, `meta`, `docs`, `repo`).

The type no longer sizes anything — versions are calendar-derived — it decides which heading the commit lands under in the release notes. Which package a commit releases comes from the paths it touched. Prose for the notes goes in the pull request body under a `## Release notes` heading. See [CONTRIBUTING.md](CONTRIBUTING.md#commit-convention).

## Do not do

- Don't ignore the conventions defined in this repository, see [CONTRIBUTING.md](CONTRIBUTING.md)
- **Don't edit anything in the marketplace repositories.** Every file there is generated, and a release deletes whatever it did not produce. The sources are here: `README.marketplace.md`, `LICENSE.marketplace`, `.gitignore.marketplace`, `apm.marketplace.yml`, and the packages themselves.
- **Don't hand-edit `packages/*/apm.lock.yaml`,** and don't refresh one on its own. It moves with its `apm.yml` pin, in one commit, through the `meta-update-repo` skill.
- **Don't edit `version:` in a package manifest.** It is a placeholder; the release stamps the real calendar version into a scratch copy and records it as a tag.
