# LLM Agent Control (`.llmctl`)

[![checks](https://github.com/siegenthalerroger/.llmctl/actions/workflows/checks.yml/badge.svg)](https://github.com/siegenthalerroger/.llmctl/actions/workflows/checks.yml)

`.llmctl` is my collection of agents, prompts, skills and other guidance for AI assistants in an IDE, a desktop app or the terminal.

It is structured as an **APM monorepo of context-scoped packages** so each environment loads only what it needs — a global baseline everywhere, domain packages only where they apply.

## Quickstart

Start with [Deploy](#deploy) to install the published plugins. If you want to explore or change the source, each `packages/<name>/` is an independent [APM](https://github.com/microsoft/apm) package. The table below shows where the guidance lives.

### Available packages

| Package | Scope | Provides |
| --- | --- | --- |
| `packages/core` | **Global baseline** | Domain-neutral planning / exploration / execution agents, research, troubleshooting, diagramming, the `meta-steering` + `meta-harness` authoring skills, `reflect` + `setup-mcp` prompts + universal MCP servers |
| `packages/workflow` | Coding | Code delivery — the code-reviewer agent + TDD, git worktrees, merge conflicts, code-review reception, lint pipelines |
| `packages/ops` | IT Operations | Helm / Kubernetes / OpenTofu skills + instructions + cloud/IaC doc MCP servers |
| `packages/product` | Product development | PRD skills + product-manager / UX agents |
| `packages/design` | Design work | Direction-setting, colour, typography, presentation + upstream layout / identity / data-visualisation practice |
| `packages/python` | Python work | Source-authoring standards + single-file script discipline (PEP 723) + upstream uv / ruff / ty project tooling |
| _root `.apm/`_ | _**Repo-local only**_ | _`meta-updater` dispatcher + the `meta-update-repo` / `meta-update-models` / `meta-refresh-steering` / `meta-review-steering` procedures, frontmatter-validation hook_ |

See [CONTRIBUTING.md](CONTRIBUTING.md#packaging-model) for the packaging rules.

### Prerequisites

For plugin installation, follow the [marketplace setup guide](https://github.com/siegenthalerroger/.llmctl-marketplace#before-you-start). The tools below are for direct APM deployment and the MCP servers you enable:

| Tool        | Required for                                                                                         |
| ----------- | ---------------------------------------------------------------------------------------------------- |
| `git`       | APM fetches packages over Git. This repository is public; HTTPS access does not require a GitHub login |
| `gh`        | The `github` MCP server uses the [`shuymn/gh-mcp`](https://github.com/shuymn/gh-mcp) extension, which reuses your `gh` login instead of a Personal Access Token |
| `npx`/`uvx` | Stdio MCP servers shell out to a companion CLI, so install the CLI for any server you enable.        |

If you use the GitHub MCP server, sign in and install its extension:

```bash
gh auth login
gh extension install shuymn/gh-mcp
```

### Deploy

**Install from [`.llmctl-marketplace`](https://github.com/siegenthalerroger/.llmctl-marketplace)**. Its README covers desktop apps, CLI tools and APM. Add the marketplace once, then choose the plugins that fit your work. You do not need to clone this source repository.

Direct APM deployment is also available when you need the source package's agents, instructions or MCP configuration. What a plugin host loads varies; see the [packaging rules](CONTRIBUTING.md#rules).

<details>
<summary>Direct APM deployment from source</summary>

APM resolves each package from GitHub without a checkout. Choose only the targets you use:

```bash
# Install APM (macOS/Linux)
brew install apm
# Install APM (Windows)
winget install Microsoft.APM

# Global baseline — deploy core + workflow to user scope everywhere
apm install -g \
  siegenthalerroger/.llmctl/packages/core \
  siegenthalerroger/.llmctl/packages/workflow \
  --target claude,copilot,codex,agent-skills
```

`packages/core` is deliberately domain-neutral: its executor agents run any well-specified task — code, configuration, IaC, docs, specs — tiered by how much context the work spans. Everything code-specific lives in `packages/workflow`, which is mostly upstream skills pulled in as pinned APM dependencies. Drop `workflow` from the command above (or install it per project) if a context does no code work, or if you do not want third-party steering in the global baseline.

Add domain packages **per project**, only where they apply:

```bash
cd your-ops-repo
apm install siegenthalerroger/.llmctl/packages/ops --target claude

cd your-product-repo
apm install siegenthalerroger/.llmctl/packages/product --target claude

cd your-design-repo
apm install siegenthalerroger/.llmctl/packages/design --target claude

cd your-python-repo
apm install siegenthalerroger/.llmctl/packages/python --target claude
```

By default this tracks the default branch, so APM will warn that the dependency is unpinned. Append a git reference as `#<sha>` or a `#llmctl-core@<version>` release tag (substitute the package name) to pin a context to a known-good state. Refresh unpinned installs with `apm update -g --yes` (user scope) or `apm update --yes` (project).

</details>

## Developing and publishing

Work on the packages from a checkout. Read [AGENTS.md](AGENTS.md) and [CONTRIBUTING.md](CONTRIBUTING.md) before editing; they cover package scope, file conventions and licensing. A focused correction or a rough draft PR is a useful place to start.

```bash
git clone https://github.com/siegenthalerroger/.llmctl.git ~/.llmctl
cd ~/.llmctl
apm install --target claude

# Try a local package before releasing it
apm install ~/.llmctl/packages/core --target claude

# Every gate: the tooling's own lint, conventions, licensing, lockfiles, and a full pack
uv run llmctl-check --repo . --since origin/main
```

The tooling is a small Python project — [pyproject.toml](pyproject.toml), one module per command under `src/llmctl/`, one `llmctl-<command>` console script each — and [uv](https://docs.astral.sh/uv/) runs it from this checkout with nothing installed first: `uv run` syncs the locked environment on the way. The `scripts:` block in [apm.yml](apm.yml) lists the commands in the order you would run them: `check`, `update`, `check-updates`, `check-steering`, `versions`, `release`, `pack-marketplace`. Each entry is a whole command — `apm run` passes nothing through — so a flag that is not written into the entry means calling the command directly.

### Updating what this repo consumes

```bash
apm run update          # move the pinned upstreams and print every diff that moved
apm run check-updates   # the files adapted from an upstream, and the specs they cite
```

`apm run update` commits nothing: it moves each package's pins as far as they go, proves the lockfile followed, scans what it materialised, and prints the upstream's own diff for each moved pin so it can be read before anything is kept. The `meta-update-repo` skill is the procedure around it, and its safety-review reference says what to look for.

Use another `--target` if you work with a different assistant. Edit files under `packages/<name>/.apm/`; installed copies and marketplace bundles are replaced by later installs or releases.

### Regenerating the marketplace

The [marketplace repository](https://github.com/siegenthalerroger/.llmctl-marketplace) holds ready-to-install bundles. Plugin hosts read the committed bundle directly, so packing includes the upstream skills declared as APM dependencies. The generated output lives separately to keep it out of this source tree.

With both repositories checked out as siblings, run this from `.llmctl`:

```bash
# Clone the marketplace beside ~/.llmctl if you do not have it yet
git clone https://github.com/siegenthalerroger/.llmctl-marketplace.git ~/.llmctl-marketplace
cd ~/.llmctl
apm run pack-marketplace
```

The command in [apm.yml](apm.yml) supplies both required paths. For a different checkout location, call the command directly:

```bash
uv run llmctl-pack-marketplace --repo . --marketplace /path/to/.llmctl-marketplace --all
```

Add `--dry-run` to preview what would be packed. Both `--repo` and `--marketplace` are required; the command does not infer paths from the environment.

**Nothing in the marketplace repository is authored there.** Its `README.md`, `LICENSE`, `.gitignore` and `apm.yml` are written from `README.marketplace.md`, `LICENSE.marketplace`, `.gitignore.marketplace` and `apm.marketplace.yml` in this repository, and anything else found in that tree is deleted. Edit the sources here.

Packing writes each package to `plugins/<name>-<version>/` from its committed lockfile, copies the required licence texts, and regenerates `THIRD-PARTY-NOTICES.md` and both catalogues:

| Generated file | Consumer |
| --- | --- |
| `.claude-plugin/marketplace.json` | Claude Code, Claude Desktop and Cowork |
| `.agents/plugins/marketplace.json` | Codex |

Do not hand-edit the bundles, either catalogue or `THIRD-PARTY-NOTICES.md`. Make content changes here and regenerate them.

<details>
<summary>What a bundle contains</summary>

| Path | Purpose |
| --- | --- |
| `.claude-plugin/plugin.json` | Plugin manifest |
| `LICENSE` + `LICENSES/` | The split licence and the licence texts the bundle needs |
| `apm.yml` | Package name, version and SPDX licence expression |
| `apm.lock.yaml` | Upstream sources, resolved commits and file checksums |
| `skills/`, `agents/`, `commands/`, `instructions/` | Packed guidance; host support determines what loads |

</details>

### Releasing

Releases are automatic: a push to `main` runs the gates and then publishes every package whose paths changed. Versions are calendar-derived — `YYYY.M.N`, counting that package's releases within the month — and recorded as annotated `<name>@<version>` tags with a GitHub release beside each one. Nothing is committed to this repository by a release.

Packages version independently: a change to `ops` releases `ops` alone.

`apm run versions` shows what each package's next version would be; `apm run release` shows what a release would publish, including its notes, and writes nothing. See [Releasing](CONTRIBUTING.md#releasing).

## Concept & Contributing

See the [VS Code agent customization docs](https://code.visualstudio.com/docs/agent-customization/overview) for details on what each type of file can achieve.

| Steering File Type                     | VS Code Copilot | Claude Code                             |
| -------------------------------------- | --------------- | --------------------------------------- |
| **Agents** (`*.agent.md`)              | Supported       | Supported                               |
| **Skills** (`*/SKILL.md`)              | Supported       | Supported                               |
| **Instructions** (`*.instructions.md`) | Supported       | Deployed as **rules** (APM converts)    |
| **Prompts** (`*.prompt.md`)            | Supported       | Deployed as **commands** (APM converts) |
| **Hooks** (`*.hook.json`)              | Preview         | Supported (30+ lifecycle events)        |
| **MCP Servers** (`apm.yml`)            | Supported       | Supported                               |

See [CONTRIBUTING.md](CONTRIBUTING.md) for adaptations required for cross-tool compatibility and repository conventions, and [Continuous Integration](CONTRIBUTING.md#continuous-integration) for what runs on a pull request.

### Agents (Custom Agents)

At a top-level these agents are normally provided by your tool of choice. However it can be useful to have specific personas as sub-agents, especially when parallel execution should be possible.

Any custom agent files must end in `*.agent.md`.

### Skills

Skills are a generalised form of Instructions that are dynamically loaded based on the name and description. Prefer skills to instructions whenever possible, as they are an open standard and support improved progressive loading capabilities.

Skills follow the [Agent Skills](https://agentskills.io/) standard. A skill is encapsulated in a folder and at a minimum will have a `SKILL.md` file.

### Instructions

Instructions are kept intentionally light, as their main purpose is code-base specific rules and not generic guidelines. Instructions should always be explicitly loaded, either by a relevant `applyTo` pattern or being referenced from a prompt. Instructions cover what Claude would want in a `CLAUDE.md` or `AGENTS.md`, while enabling optionality in their inclusion based on file patterns (or nested referential inclusion).

> [!TIP]
> **Instructions & Skills combined**
>
> Instructions are really useful in VSCode, as the `applyTo` frontmatter, allows us to force the loading of specific files depending on the referenced file-types/-paths. Other harnesses may support similar functionality either as part of the instructions or as a frontmatter field of skills themselves.
>
> We can utilise this, by having instructions strongly suggest the loading of a skill when a certain `applyTo` pattern applies. This reinforces the models own decision making and ensures the correct skills are chosen at the correct time.

Any instruction files must end in `*.instructions.md`.

### Prompts

Prevent repeating yourself by making a slash-command available to you. Anything that seems to produce better output can be put here tbh.

Any prompt files must end in `*.prompt.md`.

### Hooks

Lifecycle hooks run deterministic pre/post actions around agent events (file writes, command execution, session start). VS Code Copilot hooks are in preview; Claude Code supports 30+ hook events. Definitions use the `*.hook.json` convention and are deployed by APM into each target's native location. See the [meta-harness skill](packages/core/.apm/skills/meta-harness/SKILL.md) and the [`*.hook.json` convention](CONTRIBUTING.md#hooks-hookjson).


### MCP Servers

MCP (Model Context Protocol) servers add external capabilities — API access, doc/registry search, browser automation — to an agent. Declare each server once in the `apm.yml` of the package whose work needs it — universal dev servers in [`packages/core/apm.yml`](packages/core/apm.yml), domain servers in their domain package (cloud/IaC doc servers in [`packages/ops/apm.yml`](packages/ops/apm.yml)) — under `dependencies.mcp`; APM translates it to each tool's native config (`.vscode/mcp.json` → `servers`, `.mcp.json`/`~/.claude.json` → `mcpServers`, Codex TOML). Authoring guidance lives in the [meta-harness skill](packages/core/.apm/skills/meta-harness/SKILL.md); use the [`/setup-mcp` prompt](packages/core/.apm/prompts/setup-mcp.prompt.md) to generate an `apm.yml` block from existing definitions.

## Tool Guides

### Validated Steering Content

Curated steering content tested for quality. Some may be installed by default globally (included in this repo's `apm.yml`).

| Package                                             | Provides               | Use case                                                          | Is APM compatible | Is installed globally |
| --------------------------------------------------- | ---------------------- | ----------------------------------------------------------------- | ----------------- | --------------------- |
| `analogjs/angular-skills`                           | 10 Angular v20+ skills | Angular development (signals, forms, routing, SSR, testing, etc.) | ✅                | ⭕️                   |
| `pbakaus/impeccable`                                | 17 iterative prompts   | Frontend polish, critique, distillation, optimization             | ✅                | ⭕️                   |

To add a recommended package to a project:

```bash
cd your-project
apm install github/awesome-copilot/skills/review-and-refactor
```

### Recommended MCP Servers

These are recommended additions to the ones already wired into the packages ([`packages/core/apm.yml`](packages/core/apm.yml) and [`packages/ops/apm.yml`](packages/ops/apm.yml)) — add them to a project scoped `apm.yml` (or generate the block with [`/setup-mcp`](packages/core/.apm/prompts/setup-mcp.prompt.md)) when a task needs them.

| Server                    | Transport | Provides                                                                             | Secret             |
| ------------------------- | --------- | ------------------------------------------------------------------------------------ | ------------------ |
| `brave-search-mcp-server` | stdio     | Brave web search                                                                     | `BRAVE_API_KEY`    |
| `ddg-search`              | stdio     | DuckDuckGo web search                                                                | —                  |
| `git`                     | stdio     | Local git repository operations                                                      | —                  |
| `kubernetes-mcp-server`   | stdio     | Kubernetes cluster operations                                                        | —                  |
| `gradle`                  | stdio     | Gradle build introspection                                                           | —                  |
| `playwright`              | stdio     | Browser automation                                                                   | —                  |
| `atlassian`               | http      | Jira / Confluence                                                                    | OAuth              |

### VS Code

Recommended configuration properties:

<details>
<summary>Base VSCode</summary>

#### Base VSCode

```json
{
  "$schema": "vscode://schemas/settings/user",
  "editor.aiStats.enabled": true,
  "inlineChat.enableV2": true,
  "chat.checkpoints.showFileChanges": true,
  "chat.agent.enabled": true,
  "chat.customAgentInSubagent.enabled": true,
  "chat.includeReferencedInstructions": true,
  "chat.tools.terminal.autoApprove": {
    "Test-Path": true,
    "podman ps": true,
    "podman compose ps": true,
    "kubectl get": true,
    "kubectl describe": true,
    "kubectl logs": true,
    "/^pnpm (--filter .+)? typecheck/": true,
  },
  "chat.tools.urls.autoApprove": {
    "https://github.com/kilo-org/kilocode": {
      "approveRequest": true,
      "approveResponse": true
    },
    "https://code.visualstudio.com": {
      "approveRequest": true,
      "approveResponse": true
    },
    "https://*.openai.com": {
      "approveRequest": true,
      "approveResponse": true
    },
    "https://github.com/openai/codex": {
      "approveRequest": true,
      "approveResponse": true
    },
    "https://docs.github.com": {
      "approveRequest": false,
      "approveResponse": true
    },
    "https://api.kilo.ai": {
      "approveRequest": true,
      "approveResponse": true
    },
    "https://trivy.dev": {
      "approveRequest": true,
      "approveResponse": true
    }
  },
  "simpleBrowser.useIntegratedBrowser": true,
  "workbench.browser.enableChatTools": true,
}
```

</details>
<details>
<summary>Provider Configs</summary>

#### Provider Configs

```json
{
  "$schema": "vscode://schemas/settings/user",
  "github.copilot.nextEditSuggestions.enabled": true,
  "github.copilot.chat.scopeSelection": true,
  "github.copilot.chat.codesearch.enabled": true,
  "github.copilot.chat.searchSubagent.enabled": true,
  "gitlab.duoCodeSuggestions.enabled": false,
  "gitlab.duoChat.enabled": false,
  "gitlab.duo.enabledWithoutGitlabProject": false,
  "kilo-code.debug": false,
  "kilo-code.enableCodeActions": false,
  "kilo-code.newTaskRequireTodos": true,
  "kilo-code.preventCompletionWithOpenTodos": true,
  "kilo-code.useAgentRules": false,
  "kilo-code.deniedCommands": [],
  "kilo-code.allowedCommands": [
    "git log",
    "git diff",
    "git show",
    "npm test",
    "npm install",
    "tsc"
  ],
  "claudeCode.preferredLocation": "panel",
  "claudeCode.selectedModel": "claude-sonnet-4-6",
  "unifyChatProvider.endpoints": [...]
}
```

</details>

### Claude Code

For direct APM deployment, use the [Deploy](#deploy) instructions above. Check installed agents with `claude agents`. For plugin installation, follow the [marketplace guide](https://github.com/siegenthalerroger/.llmctl-marketplace#claude-code).
