# TODO

## 1 — Context-Scoped Packaging / Plugin Decomposition

**Goal:** Re-work the repository so it can ship smaller, context-specific APM packages or generalized agent plugins, reducing the amount of customization loaded globally in every context.

**Priority: high — do first.** The current setup is broad and loads more items than are needed in every environment. Deciding the packaging model up front shapes how new dependencies (Section 2) and per-context assets are organized.

### Background

Some assets should only be available in specific repositories or workflows (for example, the `meta-updater` agent only needs to be present in this repository, not globally in all contexts).

### Tasks

- [ ] **1a — Evaluate whether to split the repo into multiple APM packages or plugin bundles by concern/context.**
- [ ] **1b — Identify customization items that should be scoped to this repository versus globally shared assets.**
- [ ] **1c — Define a packaging model** (for example repo-local package, reusable plugin, or context-specific bundle) and update the repo structure/docs accordingly.
- [ ] **1d — Prototype one scoped package/plugin** and verify that deployment behavior matches the intended context boundaries.

---

## 2 — Add New Upstream Content as APM Dependencies

**Goal:** Consume beneficial upstream content via `apm.yml` `dependencies.apm` rather than authoring it locally.

**Priority: medium.** `dependencies.apm` is still `[]`. The vendored upstream *packages* (`angular-*`, `frontend-design`, `i-*`) are already deleted — what remains locally is either original or intentionally *adapted* (`metadata.provenance.adaptedFrom`, 18 files) content, plus 5 `mirror:` reference docs. So this is about pulling in **new** upstream packages where they'd add value, not removing duplicates.

### Tasks

- [ ] **2a — Survey upstream APM packages** worth consuming — including anything currently tracked only via `metadata.provenance.mirror` (5 reference docs) that a maintained package could replace.
- [ ] **2b — Add confirmed packages to `apm.yml`** and verify installation with `apm install -g`.

---

## 3 — Default Permissions / Auto-Approved Commands

**Goal:** Provide a curated set of default permissions — safe, read-only commands (e.g. `git diff`, `diff`, `git status`, `git log`, `ls`) auto-approved without prompting — that deploy to all supported harnesses (`claude`, `copilot`).

**Priority: medium (concrete user value).**

### Background

Each harness expresses its command allow-list differently, and it's unconfirmed whether APM can deploy permission/settings blocks per target (it currently handles skills, agents, prompts, instructions, hooks, and MCP).

| Tool | File | Setting (to verify) |
|---|---|---|
| Claude Code | `settings.json` | `permissions.allow` — e.g. `Bash(git diff:*)`, `Bash(diff:*)` |
| VS Code Copilot | `settings.json` | terminal auto-approve allow-list (confirm exact key) |
| APM | `apm.yml` | confirm whether permission/settings deployment is supported |

Related: the `fewer-permission-prompts` skill derives allow-lists from transcripts — useful as a source for the default set.

### Tasks

- [ ] **3a — Investigate APM support** for deploying permission/settings configuration across targets; if unsupported, track upstream (file/find an issue) or deploy out-of-band.
- [ ] **3b — Define the default allow-list** of safe read-only commands.
- [ ] **3c — Map the allow-list to each target's native format** and verify the deployed result with `apm install -g`.

---

## 4 — LSP Server Configuration Support

**Goal:** Document and provide cross-tool compatible LSP (Language Server Protocol) server configuration guidance within `.llmctl`, analogous to the MCP support — so agent harnesses can be configured with language servers (diagnostics, hover, go-to-definition, etc.) as a deployable unit via APM.

**Priority: medium-low (investigative, mirrors the MCP pattern).**

### Background

Agent harnesses increasingly support configuring LSP servers to give agents richer code intelligence. As with MCP, the config format likely differs across tools in file location and structure, and APM's ability to deploy per-target LSP config is unconfirmed. The specifics below need to be investigated and confirmed against current docs before authoring.

| Tool | File | Format | Key/Section |
|---|---|---|---|
| VS Code Copilot | _(to verify)_ | _(to verify)_ | _(to verify)_ |
| Claude Code | _(to verify)_ | _(to verify)_ | _(to verify)_ |
| OpenAI Codex CLI | _(to verify)_ | _(to verify)_ | _(to verify)_ |
| APM | `apm.yml` | YAML | confirm whether `dependencies.lsp` (or equivalent) is supported |

### Tasks

- [ ] **4a — Investigate per-tool LSP config support and format** across `claude` and `copilot` (and Codex if relevant); fill in the matrix above from authoritative docs.
- [ ] **4b — Investigate APM support** for deploying LSP config per target; if unsupported, track upstream (file/find an issue) or deploy out-of-band — mirror the MCP/hooks verification approach.
- [ ] **4c — Create an LSP configuration reference** as a `meta-lsp` skill (matching the `meta-mcp` pattern: `.apm/skills/meta-lsp/SKILL.md` + references), documenting the per-tool config matrix and any APM block.
- [ ] **4d — Create a cross-tool LSP setup prompt** (e.g. `.apm/prompts/setup-lsp.prompt.md`), scoped to emit the APM dependency block and delegating schema knowledge to the `meta-lsp` skill.
- [ ] **4e — Update `README.md`** — add an LSP Servers row to the steering matrix and a subsection referencing the `meta-lsp` skill.

---

## 5 — Upstream APM Tracking / Add When Needed

**Priority: waiting.** Ongoing tracking and items gated on a demonstrated need.

- [ ] **5a — Track upstream APM evolution (esp. deployed-file gitignore / local-settings targeting).** APM deploys Claude hook wiring only to `settings.json` (project) or `~/.claude/settings.json` (user) — it cannot target the git-ignored `settings.local.json` variant ([hook_integrator.py](https://github.com/microsoft/apm/blob/main/src/apm_cli/integration/hook_integrator.py) hardcodes `config_filename="settings.json"`). Watch microsoft/apm [#1342](https://github.com/microsoft/apm/issues/1342) (related: [#990](https://github.com/microsoft/apm/issues/990), [#290](https://github.com/microsoft/apm/issues/290)). When a `.local`-target option or deployed-file gitignore mode ships, revisit the `.gitignore` comment ([.gitignore:7-10](.gitignore#L7-L10)) and the deploy guidance in [CONTRIBUTING.md:127](CONTRIBUTING.md#L127). More broadly, periodically review APM releases for changes affecting this repo's deploy assumptions.
- [ ] **5b — First plugin:** Add a plugin bundle when tool/MCP capabilities are insufficient for a task. Authoring guidance lives in the [meta-plugin skill](.apm/skills/meta-plugin/SKILL.md).
