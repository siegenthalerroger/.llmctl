# LLM Agent Control (`.llmctl`)

`.llmctl` is a collection of agent modes, prompts and skills intended to be directly configured in your agent orchestrator (be that your IDE or CLI tool).

It is _not_ designed to be a library where only selected items are copied or used, though this is of course possible (copy-pasta).

## How to use

### VS Code

Recommended configuration properties:

```js
{
  "$schema": "vscode://schemas/settings/user"
  "chat.edits2.enabled": true,
  "chat.customAgentInSubagent.enabled": true,
  "chat.includeReferencedInstructions": true,
  "chat.instructionsFilesLocations": {
    "~/.llmctl/instructions": true,
    ".agents/instructions": true,
    "~/.agents/instructions": false,
    ".github/instructions": false
  },
  "chat.promptFilesLocations": {
    "~/.llmctl/prompts": true,
    ".agents/prompts": true,
    "~/.agents/prompts": false,
    ".github/prompts": false
  },
  "chat.agentSkillsLocations": {
    "~/.llmctl/skills": true,
    ".agents/skills": true,
    "~/.agents/skills": false,
    ".claude/skills": false,
    ".github/skills": false,
    "~/.copilot/skills": false,
    "~/.claude/skills": false
  },
  "chat.agentFilesLocations": {
    "~/.llmctl/agents": true,
    ".agents/agents": true,
    "~/.agents/agents": false,
    ".github/agents": false,
    "~/.github/agents": false
  },
  "github.copilot.chat.codesearch.enabled": true,
  "github.copilot.chat.searchSubagent.enabled": true
}
```

## Concept & Contributing

See the [vscode/github copilot documentation](https://code.visualstudio.com/docs/copilot/customization/overview) for details on what each type of file can achieve. There is an attempt to be tool-neutral, however the supported use-case is initiation of agents from VSCode, as such the naming follows their patterns.

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