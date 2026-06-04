# LLM Agent Control (`.llmctl`)

`.llmctl` is a collection of agent modes, prompts and skills intended to be directly configured in your agent orchestrator (be that your IDE or CLI tool).

It is _not_ designed to be a library where only selected items are copied or used, though this is of course possible (copy-pasta).

## Quickstart

This repository is an [APM](https://github.com/microsoft/apm) package. APM deploys all content (agents, skills, prompts, instructions, hooks, plugins) to both Copilot and Claude Code user-scope directories — no manual symlinks needed.

```bash
# Install APM (macOS/Linux)
brew install microsoft/apm/apm

# Install APM (Windows)
winget install Microsoft.APM

# Clone and deploy to user-scope
git clone git@github.com:siegenthalerroger/.llmctl.git ~/.llmctl
apm install -g ~/.llmctl --target copilot,claude
```

This adds the local .llmctl repository to the `~/.apm/apm.yml` file and deploys:

- Agents → `~/.copilot/agents/` + `~/.claude/agents/`
- Skills → `~/.agents/skills/` (shared cross-tool)
- Prompts → `~/.copilot/prompts/` + `~/.claude/commands/` (auto-converted)
- Instructions → `~/.copilot/copilot-instructions.md` + `~/.claude/rules/`
- Hooks → `~/.copilot/hooks/` + `~/.claude/settings.json`
- Plugins → `~/.copilot/plugins/` + Claude plugin registry

Upstream dependencies (declared in `apm.yml`) are also installed into `apm_modules/` (git-ignored).

```bash
apm update              # pull latest upstream versions
apm outdated            # check for available updates
```

## Concept & Contributing

See the [VS Code agent customization docs](https://code.visualstudio.com/docs/agent-customization/overview) for details on what each type of file can achieve. There is an attempt to be tool-neutral, however the supported use-case is initiation of agents from VS Code, as such the naming follows their patterns.

| Steering File Type                     | VS Code Copilot | Claude Code                             |
| -------------------------------------- | --------------- | --------------------------------------- |
| **Agents** (`*.agent.md`)              | Supported       | Supported (APM deploys)                 |
| **Skills** (`*/SKILL.md`)              | Supported       | Supported (APM deploys)                 |
| **Instructions** (`*.instructions.md`) | Supported       | Deployed as **rules** (APM converts)    |
| **Prompts** (`*.prompt.md`)            | Supported       | Deployed as **commands** (APM converts) |
| **Hooks**                              | Preview         | Supported (30+ lifecycle events)        |
| **Plugins**                            | Experimental    | Supported (marketplace + git install)   |

See [CONTRIBUTING.md](CONTRIBUTING.md) for adaptations required for cross-tool compatibility and repository conventions.

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
> Instructions are really useful in VSCode, as the `applyTo` frontmatter, allows us to force the loading of specific files depending on the referenced file-types/-paths. The non-vscode alternatives don't support this, depending on Skills for progressive loading of context.
>
> We can utilise this, by having instructions strongly suggest the loading of a skill when a certain `applyTo` pattern applies. This reinforces the models own decision making and ensures the correct skills are chosen at the correct time.

Any instruction files must end in `*.instructions.md`.

### Prompts

Prevent repeating yourself by making a slash-command available to you. Anything that seems to produce better output can be put here tbh.

Any prompt files must end in `*.prompt.md`.

### Hooks

Lifecycle hooks run deterministic pre/post actions around agent events (file writes, command execution, session start). VS Code Copilot hooks are in preview; Claude Code supports 30+ hook events. Definitions use the `*.hook.json` convention and are deployed by APM into each target's native location. See the [meta-hook skill](skills/meta-hook/SKILL.md) and the [`*.hook.json` convention](CONTRIBUTING.md#hooks-hookjson).

### Plugins

Plugins extend agent capabilities beyond what skills and tools provide. VS Code Copilot plugins are experimental (v1.110+); Claude Code has a production plugin marketplace. See the [meta-plugin skill](skills/meta-plugin/SKILL.md) for when plugins are appropriate.

## Tool Guides

### Validated Steering Content

Curated steering content tested for quality. Some may be installed by default globally (included in this repo's `apm.yml`).

| Package                                             | Provides               | Use case                                                          | Is APM compatible | Is installed globally |
| --------------------------------------------------- | ---------------------- | ----------------------------------------------------------------- | ----------------- | --------------------- |
| `github/awesome-copilot/skills/review-and-refactor` | Code review skill      | Systematic code review and refactoring                            | ✅                | ⭕️                   |
| `analogjs/angular-skills`                           | 10 Angular v20+ skills | Angular development (signals, forms, routing, SSR, testing, etc.) | ✅                | ⭕️                   |
| `pbakaus/impeccable`                                | 17 iterative prompts   | Frontend polish, critique, distillation, optimization             | ✅                | ⭕️                   |

To add a recommended package to a project:

```bash
cd your-project
apm install github/awesome-copilot/skills/review-and-refactor
```

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
  "chat.instructionsFilesLocations": {
    ".agents/instructions": true,
    ".claude/rules": true,
    ".copilot/instructions": true,
    ".github/instructions": true,
    "~/.llmctl/instructions": true,
    "~/.agents/instructions": false,
    "~/.claude/rules": false,
    "~/.copilot/instructions": false,
    "~/.github/instructions": false
  },
  "chat.promptFilesLocations": {
    ".agents/prompts": true,
    ".claude/commands": true,
    ".copilot/prompts": true,
    ".github/prompts": true,
    "~/.llmctl/prompts": true,
    "~/.agents/prompts": false,
    "~/.claude/commands": false,
    "~/.copilot/prompts": false,
    "~/.github/prompts": false
  },
  "chat.agentSkillsLocations": {
    ".agents/skills": true,
    ".claude/skills": true,
    ".copilot/skills": true,
    ".github/skills": true,
    "~/.llmctl/skills": true,
    "~/.agents/skills": false,
    "~/.claude/skills": false,
    "~/.copilot/skills": false,
    "~/.github/skills": false
  },
  "chat.agentFilesLocations": {
    ".agents/agents": true,
    ".claude/agents": true,
    ".copilot/agents": true,
    ".github/agents": true,
    "~/.llmctl/agents": true,
    "~/.agents/agents": false,
    "~/.claude/agents": false,
    "~/.copilot/agents": false,
    "~/.github/agents": false
  },
  "chat.hookFilesLocations": {
    ".agents/hooks": true,
    ".claude/hooks": true,
    ".claude/settings.json": true,
    ".claude/settings.local.json": true,
    ".copilot/hooks": true,
    ".github/hooks": true,
    "~/.llmctl/hooks": true,
    "~/.agents/hooks": false,
    "~/.claude/hooks": false,
    "~/.claude/settings.json": false,
    "~/.copilot/hooks": false,
    "~/.github/hooks": false
  },
  "chat.pluginLocations": {
    "~/.llmctl/plugins": true
  },
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

> **Note:** VS Code Copilot (v1.106+) natively discovers `.claude/` directories, so content deployed for Claude is also available to Copilot without duplication.