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

- [x] **2a — Create MCP configuration reference** — implemented as the **`meta-mcp` skill** (`skills/meta-mcp/SKILL.md` + `skills/meta-mcp/references/mcp-configuration.md`) rather than a top-level `references/` doc, matching the repo's meta-* skill family (so it deploys and progressively loads). Documents the per-tool config matrix incl. an **APM** row, `servers` vs `mcpServers` vs Codex TOML, transports, inline-vs-registry forms, and the `${VAR}` secret strategy.

- [x] **2b — Create a cross-tool MCP setup prompt** (`prompts/setup-mcp.prompt.md`)
  Scoped to emit an **`apm.yml` `dependencies.mcp` block only** (APM produces the per-tool files on deploy); delegates schema knowledge to the `meta-mcp` skill.

- [x] **2c — Update `README.md`** — added an **MCP Servers** row to the steering matrix, an MCP Servers subsection + Quickstart deploy line, and a **Recommended MCP Servers** table. References the `meta-mcp` skill.

> **Integration done alongside Task 2:** the 7 MCP servers referenced by `agents/researcher-advanced.agent.md` `tools:` are now wired into `apm.yml` `dependencies.mcp` (advances Section 5), with secrets externalized to `${VAR}` (`.env.example` added). Remaining servers from the personal `mcp.json` (`git`, `kubernetes`, `gradle`, `playwright`, `reddit`, `atlassian`) are listed as recommendations in the README, not wired.
>
> **Pending verification (like hooks 4e/4f):** APM MCP deployment at user/global scope (`apm install -g`) is authored-but-unverified end-to-end here. Confirm the generated per-target files (`.vscode/mcp.json` `servers`, `.mcp.json`/`~/.claude.json` `mcpServers`) and that the inline-stdio `env:` key and `sse` transport translate correctly. **Action: rotate the context7 API key** — it was committed in plaintext in the personal `mcp.json` and is now replaced by `${CONTEXT7_API_KEY}`.

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
- [ ] **4f — Track upstream APM evolution (esp. deployed-file gitignore / local-settings targeting):** APM currently deploys Claude hook wiring only to `settings.json` (project) or `~/.claude/settings.json` (user) — it cannot target the git-ignored `settings.local.json` variant ([hook_integrator.py](https://github.com/microsoft/apm/blob/main/src/apm_cli/integration/hook_integrator.py) hardcodes `config_filename="settings.json"`). Watch microsoft/apm [#1342](https://github.com/microsoft/apm/issues/1342) "Extend .gitignore coverage from apm_modules/ to deployed files" (commented with a heads-up about the `settings.local.json` angle; related: [#990](https://github.com/microsoft/apm/issues/990), [#290](https://github.com/microsoft/apm/issues/290)). When a `.local`-target option or deployed-file gitignore mode ships, revisit the `.gitignore` comment ([.gitignore:7-10](.gitignore#L7-L10)) and the deploy guidance in [CONTRIBUTING.md:127](CONTRIBUTING.md#L127). More broadly, periodically review APM releases for changes affecting this repo's deploy assumptions.

---

## 5 — Populate APM Dependencies

**Goal:** Add confirmed upstream packages to `apm.yml` as APM dependencies become available.

### Background

`apm.yml` exists but has empty dependency arrays. As upstream skill/agent packages are confirmed available via APM, they should be added here and any corresponding local vendored copies removed.

### Tasks

- [ ] **5a — Survey available APM packages** for skills currently tracked via `metadata.provenance.mirror`.
- [ ] **5b — Add confirmed packages to `apm.yml`** and verify installation with `apm install -g`.
- [ ] **5c — Remove vendored local copies** of content now consumed via APM.

---

## 6 — Default Permissions / Auto-Approved Commands

**Goal:** Provide a curated set of default permissions — safe, read-only commands (e.g. `git diff`, `diff`, `git status`, `git log`, `ls`) auto-approved without prompting — that deploy to all supported harnesses (`claude`, `copilot`).

### Background

Each harness expresses its command allow-list differently, and it's unconfirmed whether APM can deploy permission/settings blocks per target (it currently handles skills, agents, prompts, instructions, hooks, and MCP).

| Tool | File | Setting (to verify) |
|---|---|---|
| Claude Code | `settings.json` | `permissions.allow` — e.g. `Bash(git diff:*)`, `Bash(diff:*)` |
| VS Code Copilot | `settings.json` | terminal auto-approve allow-list (confirm exact key) |
| APM | `apm.yml` | confirm whether permission/settings deployment is supported |

Related: the `fewer-permission-prompts` skill derives allow-lists from transcripts — useful as a source for the default set.

### Tasks

- [ ] **6a — Investigate APM support** for deploying permission/settings configuration across targets; if unsupported, track upstream (file/find an issue) or deploy out-of-band.
- [ ] **6b — Define the default allow-list** of safe read-only commands.
- [ ] **6c — Map the allow-list to each target's native format** and verify the deployed result with `apm install -g`.

---

## 7 — LSP Server Configuration Support

**Goal:** Document and provide cross-tool compatible LSP (Language Server Protocol) server configuration guidance within `.llmctl`, analogous to the MCP support in Section 2 — so agent harnesses can be configured with language servers (diagnostics, hover, go-to-definition, etc.) as a deployable unit via APM.

### Background

Agent harnesses increasingly support configuring LSP servers to give agents richer code intelligence. As with MCP, the config format likely differs across tools in file location and structure, and APM's ability to deploy per-target LSP config is unconfirmed. The specifics below need to be investigated and confirmed against current docs before authoring.

| Tool | File | Format | Key/Section |
|---|---|---|---|
| VS Code Copilot | _(to verify)_ | _(to verify)_ | _(to verify)_ |
| Claude Code | _(to verify)_ | _(to verify)_ | _(to verify)_ |
| OpenAI Codex CLI | _(to verify)_ | _(to verify)_ | _(to verify)_ |
| APM | `apm.yml` | YAML | confirm whether `dependencies.lsp` (or equivalent) is supported |

### Tasks

- [ ] **7a — Investigate per-tool LSP config support and format** across `claude` and `copilot` (and Codex if relevant); fill in the matrix above from authoritative docs.
- [ ] **7b — Investigate APM support** for deploying LSP config per target; if unsupported, track upstream (file/find an issue) or deploy out-of-band — mirror the MCP/hooks verification approach.
- [ ] **7c — Create an LSP configuration reference** as a `meta-lsp` skill (matching the `meta-mcp` pattern: `skills/meta-lsp/SKILL.md` + references), documenting the per-tool config matrix and any APM block.
- [ ] **7d — Create a cross-tool LSP setup prompt** (e.g. `prompts/setup-lsp.prompt.md`), scoped to emit the APM dependency block and delegating schema knowledge to the `meta-lsp` skill.
- [ ] **7e — Update `README.md`** — add an LSP Servers row to the steering matrix and a subsection referencing the `meta-lsp` skill.
