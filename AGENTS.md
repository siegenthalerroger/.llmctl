# Working with this Repository

This file defines conventions for AI agents editing files in `.llmctl`.

## What this repo is

`.llmctl` is a personal collection of agent steering files (agents, skills, instructions, prompts) deployed to agent harnesses via [APM](https://github.com/microsoft/apm). It is not a library — the entire collection is configured as a unit.

## Upstream dependencies

Upstream-sourced content is declared in `apm.yml` and installed via `apm install -g`.

## Authoring rules

This is a quick reference, see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed descriptions.

- **Skills:** portable frontmatter is `name` + `description`. Additional fields are defined as a repo convention.
- **Agents:** prefer structural tool constraints (`tools`, `disallowedTools`) over prose-based role restrictions. Add `disable-model-invocation: true` to side-effectful agents that should not be auto-selected.
- **Instructions:** keep narrow — their main job is forcing skill loading via `applyTo` patterns.
- **Prompts:** one slash-command per file. Keep the body concise.
- **Provenance:** track upstream sources via `metadata.provenance.{mirror,adaptedFrom,authoritativeSpec}` —

## Do not do

- Don't ignore the conventions defined in this repository, see [CONTRIBUTING.md](CONTRIBUTING.md)
