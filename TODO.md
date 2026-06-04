# TODO

## 1 — APM Adoption & Content Externalization

**Goal:** Move upstream-sourced content to APM dependencies so it is no longer vendored in this repo.

### Background

[APM](https://github.com/microsoft/apm) (v0.17.0+) manages agent customization dependencies. Upstream content currently committed here (`skills/angular-*`, `skills/frontend-design`, `prompts/i-*.prompt.md`) should be consumed as APM dependencies from their canonical sources.

### Tasks

- [x] **1a — Create `apm.yml`** with targets `[copilot, claude]`. _Note: `dependencies.apm` is currently empty; populating it is tracked under Section 5._
- [x] **1b — Delete vendored upstream skills** (`skills/angular-*`, `skills/frontend-design/`).
- [x] **1c — Delete vendored upstream prompts** (`prompts/i-*.prompt.md`).
- [x] **1d — Add `apm_modules/` to `.gitignore`.**

---

## 2 — MCP Server Configuration Support

**Goal:** Document and provide cross-tool compatible MCP server configuration guidance within `.llmctl`.

### Background

MCP config format differs across tools in both file location and format:

| Tool | File | Format | Key/Section |
|---|---|---|---|
| VS Code Copilot | `.vscode/mcp.json` | JSON | `"servers"` |
| Claude Code | `./.mcp.json` or `~/.claude.json` | JSON | `"mcpServers"` |
| OpenAI Codex CLI | `~/.codex/config.toml` or `.codex/config.toml` | TOML | `[mcp_servers.<name>]` |

**Sources:**
- VS Code MCP: https://code.visualstudio.com/docs/copilot/chat/mcp-servers
- Claude Code MCP: https://code.claude.com/docs/en/mcp
- Codex CLI MCP: https://developers.openai.com/codex/mcp

### Tasks

- [ ] **2a — Create MCP configuration reference doc** (`references/mcp-configuration.md`)
  Document the config schema for each supported tool, file locations, key differences (`servers` vs `mcpServers`), and recommended project layout.

- [ ] **2b — Create a cross-tool MCP setup prompt** (`prompts/setup-mcp.prompt.md`)
  A slash-command that takes a list of MCP server definitions and outputs the correctly formatted config blocks for each supported tool.

- [ ] **2c — Update `README.md` compatibility matrix**
  Add a "MCP Server Config" row to the compatibility matrix. Reference `references/mcp-configuration.md`.

---

## 3 — Run `meta-update-models` Skill as Part of the `meta-updater` Agent

- [x] **Done.** Implemented as **Phase 2 — Model Refresh** in `agents/meta-updater.agent.md`, which loads the `meta-update-models` skill and refreshes `model:` arrays for every file declaring a `metadata.modelProfile`.

---

## 4 — Hooks & Plugins (When Needed)

**Goal:** Add lifecycle hooks and plugins only when a concrete use case arises.

### Background

Both VS Code Copilot (preview) and Claude Code (production) support hooks and plugins. Rather than adding speculative configuration, add content when there's a demonstrated need.

Authoring guidance lives in the [meta-agent skill](skills/meta-agent/SKILL.md).

### Tasks

- [x] **4a — Create `meta-hook` skill:** Standalone skill for lifecycle hook authoring across Claude Code, VS Code, and APM. Sources: `code.claude.com/docs/en/hooks`, `code.visualstudio.com/docs/agent-customization/hooks`, `microsoft.github.io/apm/producer/author-primitives/hooks-and-commands/`.
- [x] **4b — Create `meta-plugin` skill:** Standalone skill for plugin packaging across Claude Code, VS Code, and APM. Sources: `code.claude.com/docs/en/plugins-reference`, `code.visualstudio.com/docs/agent-customization/agent-plugins`, `microsoft.github.io/apm/producer/pack-a-bundle/`.
- [x] **4c — First hook:** Added `hooks/validate-customization-frontmatter.hook.json` — a `PostToolUse` (`Edit|Write`) hook authored in the canonical Claude-style envelope with a `${CLAUDE_PLUGIN_ROOT}` script path, for APM to transform per target on deploy.
- [ ] **4d — First plugin:** Add when tool/MCP capabilities are insufficient for a task.
- [ ] **4e — Verify APM hook deployment once APM's hook support matures:** APM's hook support is still WIP (microsoft/apm [#96](https://github.com/microsoft/apm/issues/96) "Support Hooks as an Agent Primitive", [#541](https://github.com/microsoft/apm/issues/541) "target-aware hook event diagnostics"). Once it lands, run `apm install -g` and verify the canonical hook in `hooks/*.hook.json` transforms correctly into each target's native location/format (Claude → `settings.json`; VS Code → `.github/hooks/*.json` / `chat.hookFilesLocations`), including event-name and matcher reconciliation. Until then, treat the canonical hook as authored-but-unverified end-to-end.

---

## 5 — Populate APM Dependencies

**Goal:** Add confirmed upstream packages to `apm.yml` as APM dependencies become available.

### Background

`apm.yml` exists but has empty dependency arrays. As upstream skill/agent packages are confirmed available via APM, they should be added here and any corresponding local vendored copies removed.

### Tasks

- [ ] **5a — Survey available APM packages** for skills currently tracked via `metadata.provenance.mirror`.
- [ ] **5b — Add confirmed packages to `apm.yml`** and verify installation with `apm install -g`.
- [ ] **5c — Remove vendored local copies** of content now consumed via APM.