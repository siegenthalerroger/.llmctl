# TODO

## 1 — Add New Upstream Content as APM Dependencies

**Goal:** Consume beneficial upstream content via `apm.yml` `dependencies.apm` rather than authoring it locally.

**Priority: medium.** `dependencies.apm` is still `[]`. The vendored upstream *packages* (`angular-*`, `frontend-design`, `i-*`) are already deleted — what remains locally is either original or intentionally *adapted* (`metadata.provenance.adaptedFrom`, 18 files) content, plus 5 `mirror:` reference docs. So this is about pulling in **new** upstream packages where they'd add value, not removing duplicates.

### Tasks

- [ ] **1a — Survey upstream APM packages** worth consuming — including anything currently tracked only via `metadata.provenance.mirror` (5 reference docs) that a maintained package could replace.
- [ ] **1b — Add confirmed packages to `apm.yml`** and verify installation with `apm install -g`.

---

## 2 — Default Permissions / Auto-Approved Commands

**Goal:** Provide a curated set of default permissions — safe, read-only commands (e.g. `git diff`, `diff`, `git status`, `git log`, `ls`) auto-approved without prompting — that deploy to all supported harnesses (`claude`, `copilot`).

**Priority: medium (concrete user value).**

### Background

Each harness expresses its command allow-list differently, and it's unconfirmed whether APM can deploy permission/settings blocks per target (it currently handles skills, agents, prompts, instructions, hooks, and MCP).

| Tool            | File            | Setting (to verify)                                           |
| --------------- | --------------- | ------------------------------------------------------------- |
| Claude Code     | `settings.json` | `permissions.allow` — e.g. `Bash(git diff:*)`, `Bash(diff:*)` |
| VS Code Copilot | `settings.json` | terminal auto-approve allow-list (confirm exact key)          |
| APM             | `apm.yml`       | confirm whether permission/settings deployment is supported   |

Related: the `fewer-permission-prompts` skill derives allow-lists from transcripts — useful as a source for the default set.

### Tasks

- [ ] **2a — Investigate APM support** for deploying permission/settings configuration across targets; if unsupported, track upstream (file/find an issue) or deploy out-of-band.
- [ ] **2b — Define the default allow-list** of safe read-only commands.
- [ ] **2c — Map the allow-list to each target's native format** and verify the deployed result with `apm install -g`.

---

## 3 — LSP Server Configuration Support

**Goal:** Document and provide cross-tool compatible LSP (Language Server Protocol) server configuration guidance within `.llmctl`, analogous to the MCP support — so agent harnesses can be configured with language servers (diagnostics, hover, go-to-definition, etc.) as a deployable unit via APM.

**Priority: medium-low (investigative, mirrors the MCP pattern).**

### Background

Agent harnesses increasingly support configuring LSP servers to give agents richer code intelligence. As with MCP, the config format likely differs across tools in file location and structure, and APM's ability to deploy per-target LSP config is unconfirmed. The specifics below need to be investigated and confirmed against current docs before authoring.

| Tool             | File          | Format        | Key/Section                                                     |
| ---------------- | ------------- | ------------- | --------------------------------------------------------------- |
| VS Code Copilot  | _(to verify)_ | _(to verify)_ | _(to verify)_                                                   |
| Claude Code      | _(to verify)_ | _(to verify)_ | _(to verify)_                                                   |
| OpenAI Codex CLI | _(to verify)_ | _(to verify)_ | _(to verify)_                                                   |
| APM              | `apm.yml`     | YAML          | confirm whether `dependencies.lsp` (or equivalent) is supported |

### Tasks

- [ ] **3a — Investigate per-tool LSP config support and format** across `claude` and `copilot` (and Codex if relevant); fill in the matrix above from authoritative docs.
- [ ] **3b — Investigate APM support** for deploying LSP config per target; if unsupported, track upstream (file/find an issue) or deploy out-of-band — mirror the MCP/hooks verification approach.
- [ ] **3c — Create an LSP configuration reference** as a `meta-lsp` skill (matching the `meta-mcp` pattern: `packages/meta/.apm/skills/meta-lsp/SKILL.md` + references), documenting the per-tool config matrix and any APM block.
- [ ] **4d — Create a cross-tool LSP setup prompt** (e.g. `packages/meta/.apm/prompts/setup-lsp.prompt.md`), scoped to emit the APM dependency block and delegating schema knowledge to the `meta-lsp` skill.
- [ ] **4e — Update `README.md`** — add an LSP Servers row to the steering matrix and a subsection referencing the `meta-lsp` skill.

---

## 4 — Upstream APM Tracking / Add When Needed

**Priority: waiting.** Ongoing tracking and items gated on a demonstrated need.

- [ ] **4a — Track upstream APM evolution (esp. deployed-file gitignore / local-settings targeting).** APM deploys Claude hook wiring only to `settings.json` (project) or `~/.claude/settings.json` (user) — it cannot target the git-ignored `settings.local.json` variant ([hook_integrator.py](https://github.com/microsoft/apm/blob/main/src/apm_cli/integration/hook_integrator.py) hardcodes `config_filename="settings.json"`). Watch microsoft/apm [#1342](https://github.com/microsoft/apm/issues/1342) (related: [#990](https://github.com/microsoft/apm/issues/990), [#290](https://github.com/microsoft/apm/issues/290)). When a `.local`-target option or deployed-file gitignore mode ships, revisit the `.gitignore` comment ([.gitignore:7-10](.gitignore#L7-L10)) and the deploy guidance in [CONTRIBUTING.md:127](CONTRIBUTING.md#L127). More broadly, periodically review APM releases for changes affecting this repo's deploy assumptions.
- [ ] **4b — First plugin:** Add a plugin bundle when tool/MCP capabilities are insufficient for a task. Authoring guidance lives in the [meta-plugin skill](packages/meta/.apm/skills/meta-plugin/SKILL.md).
- [ ] **4c — Track two APM 0.25 environment issues found during clean redeploy.**

  1. **Aggregator not `-g`-installable (aggregator removed, reinstate later).** A prototyped `packages/global` aggregator (an `apm.yml` with only `dependencies.apm` → `../core`, `../meta`) resolved its transitive *local-path* deps but deployed **zero** primitives at user scope (worked at project scope). It was **removed** to avoid documenting a broken command; global install names `core` + `meta` directly for now. **To reinstate:** recreate `packages/global/apm.yml` (deps: `./../core`, `./../meta`, + third-party global recs), point `~/.apm/apm.yml` at it, and make it the single-command global profile + home for third-party global recommendations. File/find an upstream APM issue for transitive local-path deploy at `-g`; do this once it's fixed.
  2. **`copilot-cowork` + multiple OneDrive mounts** aborts any global install at lockfile generation (`--exclude copilot-cowork` does not help). Workaround: export `APM_COPILOT_COWORK_SKILLS_DIR` to a single dir. Noted in README prerequisites.
- [ ] **4d — Track APM per-target agent tool-policy mapping.** APM 0.26.0 copies agent frontmatter verbatim to every target (no per-target normalization, unlike hooks), so a Copilot `tools:` array deploys unchanged to `~/.claude/agents/` and makes the agent unspawnable on Claude Code. Repo agents work around this by omitting `tools:` and scoping Claude via `disallowedTools` (see [meta-agent skill](packages/meta/.apm/skills/meta-agent/SKILL.md#tools-field)); the trade-off is that Copilot loses allow-list scoping (inherits all tools). Watch microsoft/apm [#2108](https://github.com/microsoft/apm/issues/2108) (portable agent semantics) under epic [#2112](https://github.com/microsoft/apm/issues/2112); related: [#293](https://github.com/microsoft/apm/issues/293) (consumer tool overrides), [#2261](https://github.com/microsoft/apm/issues/2261) (per-file target declaration — would let us stop deploying `plan`/`explore` to Claude), [#581](https://github.com/microsoft/apm/issues/581) (declined intra-file translation precedent). When per-target agent frontmatter mapping ships, restore precise Copilot allow-lists.

---

## 6 — Distribute via Plugin Marketplace (claude.ai Cowork & Claude Desktop/Code)

**Goal:** Make `.llmctl` content loadable on the one surface APM can't deploy to — **claude.ai's Cowork** (plus Claude Desktop and Claude Code) — by publishing a plugin marketplace. Built and verified locally; the actual publish (commit + push, then add in the live UI) is left to the user.

**Priority: medium (broadens reach beyond local APM deploy).**

### Background & corrected premise (6a findings)

The original framing ("web-based Claude") was imprecise. Verified against first-party docs + Claude Code 2.1.205:

- **A plugin marketplace reaches Claude Code CLI, Claude Desktop, and claude.ai Cowork** — *"Plugins are available in Cowork and Code. They aren't used in Chat."* It does **NOT** reach claude.ai **Chat** (that needs uploaded/org-provisioned **Custom Skills**, 200-char description cap — a separate future track) or **hosted ChatGPT** (separate Custom-GPT/Actions ecosystem — out of scope).
- **Cowork "Add marketplace" takes a Git repository** (`owner/repo` or git URL) — not a GitHub Pages / static `marketplace.json` URL, and no branch selector in its UI (tracks the default branch).
- **APM 0.26 generates the whole marketplace** — a `marketplace:` block in root `apm.yml` + `apm pack` emits `.claude-plugin/marketplace.json` (Claude) and `.agents/plugins/marketplace.json` (Codex). Nothing is authored out-of-band.
- **The plugin path is reduced-fidelity vs `apm install`:** it carries **skills + commands** only. **Instructions, MCP servers, and agents do NOT travel** (no instructions component; `apm pack` drops MCP; the plugin `agents` field does not load in 2.1.205). `apm install` stays the full-fidelity deploy.

### Tasks

- [x] **6a — Investigate marketplace requirements** — done (findings above). APM generates both marketplace manifests; hosting is the repo itself (Cowork clones it via `owner/repo`).
- [x] **6b — Define the plugin bundle(s)** — one plugin per package (`llmctl-core`, `llmctl-meta`, `llmctl-ops`, `llmctl-product`), each a thin `packages/<name>/.claude-plugin/plugin.json` pointing at its `.apm/` dirs. Skills-only (+ meta commands) by decision; agents/instructions/MCP remain `apm install`-only.
- [x] **6c — Build & verify locally** — `marketplace:` block added to `apm.yml`; `apm pack` generates both manifests (committed as the documented exception); `apm marketplace check` + `claude plugin validate .` pass; local `claude plugin install` confirmed skills load (core 4, meta 9 incl. `reflect.prompt`/`setup-mcp.prompt`) and confirmed agents/instructions/MCP drop.
- [x] **6d — Publish (user)** — commit the manifests + thin `plugin.json`s, push to `main`, then in claude.ai/Cowork **Add marketplace → `siegenthalerroger/.llmctl`** and install a plugin end-to-end. Optionally host the marketplace in a dedicated repo (`git-subdir` sources) if URL/non-clone consumers are ever targeted.
- [x] **6e — (follow-up) claude.ai Chat via Custom Skills** — separate track: package skills as claude.ai-uploadable Custom Skills (≤200-char descriptions vs. this repo's long directive ones). Not a marketplace. See [meta-plugin skill](packages/meta/.apm/skills/meta-plugin/SKILL.md).