# LLM Agent Control (`.llmctl`)

`.llmctl` is a collection of agent modes, prompts and skills intended to be directly configured in your agent orchestrator (be that your IDE or CLI tool).

It is _not_ designed to be a library where only selected items are copied or used, though this is of course possible (copy-pasta).

See the [vscode/github copilot documentation](https://code.visualstudio.com/docs/copilot/customization/overview) for details on what each type of file can achieve.

Read on for details of what to expect from this repo and when to add/adapt the files here.

## How to use

### VS Code

Recommended configuration properties:

```js
{
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

### Agents (Modes)

At a top-level these modes are normally provided by your tool of choice. However it can be useful to have specific personas as sub-agents, especially when parallel execution should be possible.

### Skills

Skills are a generalised form of Instructions that are dynamically loaded based on the name and description.

### Instructions

Instructions are kept intentionally light, as their main purpose is code-base specific rules and not generic guidelines.

Any instruction files must end in `*.instructions.md`.

### Prompts

Prevent repeating yourself by making a slash-command available to you. Anything that seems to produce better output can be put here tbh.

Any prompt files must end in `*.prompt.md`.