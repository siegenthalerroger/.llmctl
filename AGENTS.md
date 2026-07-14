# Working with this Repository

This file defines conventions for AI agents editing files in `.llmctl`.

## What this repo is

`.llmctl` is a personal collection of agent steering files (agents, skills, instructions, prompts, hooks, plugins) deployed to agent harnesses via [APM](https://github.com/microsoft/apm).

It is an **APM monorepo of context-scoped sub-packages**, so each context loads only what it needs.

Each `packages/<name>/` is a standalone APM package (`apm.yml` + `.apm/` layout). Adding a primitive means placing it in the correct sub-package by scope — do not add it to the root `.apm/` unless it operates on this repository itself. See the [packaging model in CONTRIBUTING.md](CONTRIBUTING.md#packaging-model).

## Upstream dependencies

Upstream-sourced content is declared in the relevant package's `apm.yml` (`packages/*/apm.yml`) and installed via `apm install`. MCP servers are scoped per package: universal dev servers in `packages/core/apm.yml`, cloud/IaC doc servers in `packages/ops/apm.yml`.

## Authoring rules

This is a quick reference, see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed descriptions.

- **Descriptions (all types):** single-line, front-loaded, name-first. Shape as a directive with an explicit negative constraint ("ALWAYS invoke when … Do not … without this skill") — keyword density is not the activation lever. Stay within budgets (skill `description` ≤ 1024 chars). See the [meta-skill description rules](packages/meta/.apm/skills/meta-skill/SKILL.md#description-best-practices); the frontmatter hook enforces the mechanical limits.
- **Skills:** portable frontmatter is `name` + `description`. Additional fields are defined as a repo convention.
- **Agents:** prefer structural tool constraints (`tools`, `disallowedTools`) over prose-based role restrictions. Add `disable-model-invocation: true` to side-effectful agents that should not be auto-selected.
- **Instructions:** keep narrow — their main job is forcing skill loading via `applyTo` patterns.
- **Prompts:** one slash-command per file. Keep the body concise.
- **Hooks:** deterministic, event-driven guardrails/side-effects only — not behavioral steering. Prefer cross-platform (Python/Node) scripts. Name definition files `*.hook.json`.
- **Plugins:** bundled distribution of multiple components. Add only when shipping a curated subset for marketplace/external use.
- **Provenance:** track upstream sources via `metadata.provenance.{mirror,adaptedFrom,authoritativeSpec}` — prefer APM dependencies over vendored copies.

## Do not do

- Don't ignore the conventions defined in this repository, see [CONTRIBUTING.md](CONTRIBUTING.md)
