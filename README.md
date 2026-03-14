# LLM Agent Control (`.llmctl`)

`.llmctl` is a collection of agent modes, prompts and skills intended to be directly configured in your agent orchestrator (be that your IDE or CLI tool).

It is _not_ designed to be a library where only selected items are copied or used, though this is of course possible (copy-pasta).

## Concept & Contributing

See the [vscode/github copilot documentation](https://code.visualstudio.com/docs/copilot/customization/overview) for details on what each type of file can achieve. There is an attempt to be tool-neutral, however the supported use-case is initiation of agents from VSCode, as such the naming follows their patterns.

See [CONTRIBUTING.md](CONTRIBUTING.md) for adaptations required for cross-tool compatibility and repository conventions.

### Agents (Custom Modes)

At a top-level these modes are normally provided by your tool of choice. However it can be useful to have specific personas as sub-agents, especially when parallel execution should be possible.

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

## How to use

### Compatibility Matrix

| Steering File Type                 | VS Code Copilot | Claude Code                                     | Codex   |
| ---------------------------------- | --------------- | ----------------------------------------------- | ------- |
| Agents (`*.agent.md`)              | Supported       | Supported (symlink)                             | Unknown |
| Skills (`*/SKILL.md`)              | Supported       | Supported (symlink)                             | Unknown |
| Instructions (`*.instructions.md`) | Supported       | Supported (symlink - as "rules")                | Unknown |
| Prompts (`*.prompt.md`)            | Supported       | Supported (symlink, deprecated - as "commands") | Unknown |

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

Symlink the agents and skills directories into Claude Code's user-level directories:

```bash
# Unix/macOS
ln -s ~/.llmctl/agents ~/.claude/agents
ln -s ~/.llmctl/skills ~/.claude/skills
ln -s ~/.llmctl/instructions ~/.claude/rules
ln -s ~/.llmctl/prompts ~/.claude/commands
```

```bat
:: Windows (requires admin or developer mode - run in CMD not powershell)
mklink /D "%USERPROFILE%\.claude\agents" "%USERPROFILE%\.llmctl\agents"
mklink /D "%USERPROFILE%\.claude\skills" "%USERPROFILE%\.llmctl\skills"
mklink /D "%USERPROFILE%\.claude\rules" "%USERPROFILE%\.llmctl\instructions"
mklink /D "%USERPROFILE%\.claude\commands" "%USERPROFILE%\.llmctl\prompts"
```

Verify agent discovery with `claude agents`. Skills are discovered automatically from `~/.claude/skills/` (there is no `claude skills` command — ask within a session to confirm).