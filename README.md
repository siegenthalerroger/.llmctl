# LLM Agent Control (`.llmctl`)

[![checks](https://github.com/siegenthalerroger/.llmctl/actions/workflows/checks.yml/badge.svg)](https://github.com/siegenthalerroger/.llmctl/actions/workflows/checks.yml)

`.llmctl` is a collection of agent modes, prompts and skills intended to be directly configured in your agent orchestrator (be that your IDE or CLI tool).

It is structured as an **APM monorepo of context-scoped packages** so each environment loads only what it needs — a global baseline everywhere, domain packages only where they apply.

## Quickstart

This repository is an [APM](https://github.com/microsoft/apm) monorepo. Each `packages/<name>/` is an independently installable APM package; APM deploys a package's content to both Copilot and Claude Code — no manual symlinks needed.

### Available packages

| Package | Scope | Provides |
| --- | --- | --- |
| `packages/core` | **Global baseline** | Domain-neutral planning / exploration / execution agents, research, troubleshooting, diagramming, the `meta-steering` + `meta-harness` authoring skills, `reflect` + `setup-mcp` prompts + universal MCP servers |
| `packages/workflow` | Coding | Code delivery — the code-reviewer agent + TDD, git worktrees, merge conflicts, code-review reception, lint pipelines |
| `packages/ops` | IT Operations | Helm / Kubernetes / OpenTofu skills + instructions + cloud/IaC doc MCP servers |
| `packages/product` | Product development | PRD skills + product-manager / UX agents |
| `packages/design` | Design work | Direction-setting, colour, typography, presentation + upstream layout / identity / data-visualisation practice |
| _root `.apm/`_ | _**Repo-local only**_ | _`meta-updater` agent + `meta-update-models` / `meta-upstream-sync` audit skills, frontmatter-validation hook_ |

See [CONTRIBUTING.md](CONTRIBUTING.md#packaging-model) for the packaging rules.

### Prerequisites

Install the CLI tools the deploy step and wired-in servers depend on:

| Tool        | Required for                                                                                         |
| ----------- | ---------------------------------------------------------------------------------------------------- |
| `git`       | APM fetches packages over git. This repository is private, so git must be able to authenticate against it — `gh auth setup-git` or an SSH key |
| `gh`        | The wired-in `github` MCP server. The `github` mcp server uses the [`shuymn/gh-mcp`](https://github.com/shuymn/gh-mcp) extension, which reuses your `gh` login instead of a Personal Access Token |
| `npx`/`uvx` | Stdio MCP servers shell out to a companion CLI, so install the CLI for any server you enable.        |

Execute

```bash
gh auth login
gh extension install shuymn/gh-mcp
```

### Deploy

No checkout needed — APM resolves each package straight from this repository.

```bash
# Install APM (macOS/Linux)
brew install microsoft/apm/apm
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
apm install siegenthalerroger/.llmctl/packages/ops

cd your-product-repo
apm install siegenthalerroger/.llmctl/packages/product

cd your-design-repo
apm install siegenthalerroger/.llmctl/packages/design
```

By default this tracks the default branch, so APM will warn that the dependency is unpinned. Append a git reference as `#<sha>` or a `#<package>@<version>` release tag to pin a context to a known-good state. Refresh unpinned installs with `apm update -g --yes` (user scope) or `apm update --yes` (project).

#### Developing this repository

Work on the packages themselves from a checkout, and deploy from local paths so edits take effect without a push:

```bash
git clone git@github.com:siegenthalerroger/.llmctl.git ~/.llmctl
cd ~/.llmctl
apm install

# Try a package before releasing it
apm install ~/.llmctl/packages/core --target claude
```

### Plugin marketplace

For hosts that only accept marketplace content — claude.ai **Cowork**, Claude Desktop, Claude Code — the packages are also published as plugin bundles from a separate repository, [`.llmctl-marketplace`](https://github.com/siegenthalerroger/.llmctl-marketplace). A plugin host clones that repo and reads each bundle as committed, so upstream APM dependencies are vendored into the bundles at pack time.

```bash
apm run pack-marketplace   # supplies --repo and --marketplace; both are required
```

This is a **reduced-fidelity** path — rely on skills and commands travelling, and use `apm install` where agents, instructions, or MCP servers matter. See the [packaging rules](CONTRIBUTING.md#rules).

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

> [!TIP] Instructions & Skills combined
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

APM handles deployment to `~/.claude/` automatically (see Setup above). Verify with `claude agents`.
