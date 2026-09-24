# Tool Configuration Reference

**Contents:** [Overview](#overview) · [Tool Configuration Strategies](#tool-configuration-strategies) · [Understanding Available Tools](#understanding-available-tools) · [Tool Selection Patterns](#tool-selection-patterns) · [Best Practices](#best-practices) · [Tool Limitations and Errors](#tool-limitations-and-errors) · [Security Considerations](#security-considerations) · [Further Reading](#further-reading)

How to scope an agent's tools on each runtime. Available tools vary by environment and installed MCP servers; consult the platform's documentation for current names.

## Overview

Tool scoping serves security (limits the damage of a wrong action), clarity (the capability set documents the role) and selection accuracy (fewer tools, fewer wrong picks).

> **Dual-deployed agents (the default here):** the `tools:` rule and its one exception are in [agent-guide.md, "Tools field"](./agent-guide.md#tools-field). Restrict Claude Code with `disallowedTools:` and restate the restriction in the body. The Copilot-vocabulary `tools:` arrays below apply only to a Copilot-only file.

## Tool Configuration Strategies

| Strategy | Dual-deployed file | Copilot-only file | Claude-only file |
|---|---|---|---|
| All tools | Omit `tools:` | Omit, or `tools: ['*']` | Omit |
| Read-only | `disallowedTools: Edit, Write, NotebookEdit` + body rule | `tools: ['read', 'search']` | `tools: Read, Grep, Glob` or the denylist |
| No tools | Not possible on Claude ("would be spawned with zero tools — refusing") | `tools: []` | Not possible |
| MCP server tools | Omit `tools:`; scope servers with `mcpServers` (Claude) / `mcp-servers` (Copilot) | `tools: ['read', 'github/*']` | `tools: Read, mcp__github__<tool>` names |

A `*` anywhere in a Copilot CLI list grants every tool: "`["view", "*"]` grants every tool, not just `view`".

## Understanding Available Tools

### Tool Categories

- **Workspace:** read, create, edit, delete files; directory listing; search (glob, grep, semantic)
- **Execution:** terminal commands, build systems, test runners
- **External:** web fetch and search; MCP-provided services
- **Orchestration:** sub-agent invocation

### Discovering Available Tools

1. Consult the platform's built-in tool reference
2. List installed MCP servers and their exposed tools
3. Start from the smallest set and add tools as the role proves it needs them

### Copilot Tool Aliases

Copilot's primary aliases are `read`, `edit`, `search`, `execute`, `agent`, `web` and `todo`; it also accepts Claude-style compatible aliases and "All unrecognized tool names are ignored" ([configuration reference](https://docs.github.com/en/copilot/reference/custom-agents-configuration#tool-aliases)). MCP tools are `server/tool` or `server/*`.

### Claude Code Tool Names

Claude Code's built-in tools use PascalCase names: `Read`, `Glob`, `Grep`, `Edit`, `Write`, `NotebookEdit`, `Bash`, `WebFetch`, `WebSearch`, `TodoWrite`, `Skill`, `Agent`. MCP tools are `mcp__server__tool`. Subagents never receive `AskUserQuestion`, `EnterPlanMode` or `ExitPlanMode` (unless `permissionMode: plan`), whatever `tools` says ([sub-agents docs](https://code.claude.com/docs/en/sub-agents)).

```yaml
# Dual-deployed read-only agent: no `tools:`; Claude scoped by the denylist.
disallowedTools: Edit, Write, NotebookEdit
```

## Tool Selection Patterns

Pick the posture by role. The Copilot column is for Copilot-only files; a dual-deployed file uses the Claude denylist column and states the rule in its body.

| Role | Needs | Copilot-only `tools:` | Dual-deployed `disallowedTools:` |
|---|---|---|---|
| Reviewer, auditor, explorer | Read, search | `['read', 'search']` | `Edit, Write, NotebookEdit` |
| Researcher | Read, search, web | `['read', 'search', 'web']` | `Edit, Write, NotebookEdit` |
| Refactorer, implementer | Read, search, edit | `['read', 'search', 'edit']` | `Bash` if execution is not needed |
| Test runner, build agent | Plus execution | `['read', 'search', 'edit', 'execute']` | none |
| Orchestrator | Plus sub-agent invocation | add `'agent'` | none; the spawn tool is on by default |
| Integration agent | Plus an MCP server | add `'server/*'` | scope with `mcpServers` / `mcp-servers` |

## Best Practices

- **Cut tool count aggressively.** Large tool surfaces degrade tool-selection accuracy even when the extra tools are irrelevant; the evidence and curation rules are in [meta-harness, Curating Servers and Tools](../../meta-harness/references/mcp.md#curating-servers-and-tools). Prefer deferred/on-demand tool loading where the harness supports it.
- **Least privilege.** A reviewer does not edit; a refactorer does not execute unless it must run tests.
- **Justify unusual combinations** in a YAML comment next to the field, not in the `description` (which is routing text).
- **Grant progressively.** Start at read-only; add edit, then execution, only when the role proves it needs them.
- **Execution tools:** name the commands the agent is expected to run.
- **Orchestration:** the orchestrator's pool is the ceiling for what it delegates (see [agent-subagent.md](./agent-subagent.md#tool-availability-requirement)).

## Tool Limitations and Errors

| Symptom | Likely cause |
|---|---|
| Claude refuses to spawn: "would be spawned with zero tools" | A `tools:` list with no resolvable Claude name (Copilot vocabulary) |
| Claude agent silently lacks a tool | A `tools:` list where only some entries resolved |
| "Tool not available" | Not in `tools`, removed by `disallowedTools`, MCP server not running, or a subagent-filtered tool |
| "Permission denied" | Workspace policy, `permissionMode`, or the parent's pool lacks the tool |

Debug by checking the frontmatter, the running MCP servers, and the runtime's agent log.

## Security Considerations

High-risk categories: execution (arbitrary commands), edit (modification and deletion), MCP integrations (external permissions).

- [ ] Tools limited to the agent's actual needs
- [ ] Execution and destructive operations only where the role requires them, with confirmation for destructive steps
- [ ] MCP integrations use credentials with limited permissions
- [ ] Every restriction a case 2 key carries is restated in the body
- [ ] Agent tested with malicious and edge-case inputs

## Further Reading

- [agent-guide.md](./agent-guide.md#tools-field) - the dual-deploy `tools:` rule
- [agent-frontmatter.md](./agent-frontmatter.md) - field reference
- [agent-subagent.md](./agent-subagent.md) - orchestration
- [agent-patterns.md](./agent-patterns.md) - personas and their tool posture
