# Tool Configuration Reference

**Contents:** [Overview](#overview) · [Tool Configuration Strategies](#tool-configuration-strategies) · [Understanding Available Tools](#understanding-available-tools) · [Tool Selection Patterns](#tool-selection-patterns) · [Best Practices](#best-practices) · [Tool Limitations and Errors](#tool-limitations-and-errors) · [Security Considerations](#security-considerations) · [Examples by Use Case](#examples-by-use-case) · [Further Reading](#further-reading)

This document provides guidance on configuring agent tool access in custom agent files. Available tools vary by environment and installed MCP servers - consult your platform's documentation for specific tool names and capabilities.

## Overview

The `tools` field in agent frontmatter controls which capabilities an agent can access. Proper tool configuration is essential for:

- **Security**: Limiting potential damage from agent errors
- **Clarity**: Making agent capabilities explicit and discoverable
- **Performance**: Reducing decision overhead by limiting options
- **Maintainability**: Documenting intentional design decisions

> **Dual-deployed agents (default): omit `tools:`; restrict via the Claude-only `disallowedTools:` denylist.** A Copilot `tools:` array makes Claude Code refuse to spawn the agent (see [agents.md, "Tools field"](./agents.md#tools-field)). The `tools:` examples in this document are **Copilot-only-file** usage.

## Tool Configuration Strategies

### Enable All Tools (Default)

Grant the agent access to all available tools. Use when the agent needs maximum flexibility.

```yaml
# Option 1: Omit the tools field entirely
---
description: "Full-featured implementation agent"
name: "Implementation Agent"
---

# Option 2: Use wildcard
---
description: "Full-featured implementation agent"
name: "Implementation Agent"
tools: ['*']
---
```

**When to use:**
- General-purpose implementation agents
- Orchestrator agents that invoke specialized sub-agents
- Prototyping and experimentation

**Risks:**
- Agent may use tools unnecessarily
- Less clear what the agent is designed to do
- Higher security risk if agent makes errors

### Enable Specific Tools

Grant access to only the tools needed for the agent's purpose. **Recommended for most agents.**

```yaml
---
description: "Code reviewer that analyzes code quality"
name: "Code Review Agent"
tools: ['read', 'search']
---
```

**When to use:**
- Specialized agents with well-defined responsibilities
- Read-only agents (reviewers, analyzers, documenters)
- Agents that need controlled edit access

**Copilot-only file.** If this file must also run on Claude Code, drop the `tools:` array — see [Claude Code Tool Names](#claude-code-tool-names) below for why this exact array makes Claude Code refuse to spawn the agent.

**Benefits:**
- Clear capability boundaries
- Follows principle of least privilege
- Reduces error surface area

### Enable MCP Server Tools

Grant access to tools provided by MCP (Model Context Protocol) servers. Use for agents that integrate with external services.

```yaml
---
description: "GitHub PR manager that creates and reviews pull requests"
name: "GitHub Agent"
tools: ['read', 'edit', 'github/*']
---
```

**Wildcards:**
- `'github/*'` - All GitHub MCP tools
- `'playwright/*'` - All Playwright tools
- `'toolname'` - Specific tool (e.g., `'github/createPullRequest'`)

**When to use:**
- Agents that interact with version control (GitHub, GitLab)
- Agents that perform browser automation (Playwright)
- Agents that query external APIs or databases

### Disable All Tools

Create an agent with no tool access. Use for pure reasoning or advice agents.

```yaml
---
description: "Architecture advisor that provides design guidance"
name: "Architecture Advisor"
tools: []
---
```

**When to use:**
- Advisory agents that provide recommendations
- Planning agents that outline approaches
- Educational agents that explain concepts
- Agents that only need conversation capability

## Understanding Available Tools

Available tools vary by environment, installed extensions, and MCP (Model Context Protocol) servers. Rather than maintaining an exhaustive list, this section provides guidance on tool categories and discovery.

### Tool Categories

Tools generally fall into these categories:

**Workspace Operations:**
- File reading and content access
- File creation, editing, and deletion
- Directory listing and structure navigation
- Code search (semantic, grep, file patterns)

**Execution:**
- Terminal command execution
- Script and build system invocation
- Test runners and validators

**External Integration:**
- Web content fetching and documentation access
- Debugging and runtime inspection
- Version control operations (via MCP)
- Third-party service integration (via MCP)

**Orchestration:**
- Sub-agent invocation
- Workflow coordination

### Discovering Available Tools

To identify which tools are available in your environment:

1. **Check documentation:** Consult your AI assistant platform's documentation for built-in tools
2. **Review MCP servers:** List installed MCP servers and their exposed tools
3. **Test incrementally:** Start with common tools (`read`, `search`, `edit`) and add others as needed
4. **Use wildcards:** For MCP tools, use `servername/*` to grant access to all tools from a server

### Common Tool Names

While specific implementations vary, these tool names are commonly available:

- `read`, `edit`, `search` - Workspace file operations
- `execute`, `run`, `terminal` - Command execution
- `web`, `fetch`, `browser` - External content access
- `debug`, `inspect` - Runtime debugging
- `agent`, `subagent` - Orchestration

**Note:** Always verify tool names in your specific environment as they may differ.

### Claude Code Tool Names

Claude Code uses a different tool ecosystem from Copilot. Its built-in tools use PascalCase names:

- `Read`, `Glob`, `Grep` - File reading and search
- `Edit`, `Write` - File modification
- `Bash` - Command execution
- `Agent` - Sub-agent orchestration
- `WebFetch`, `WebSearch` - External content access
- `NotebookEdit` - Jupyter notebook editing

**Dual-deployed default:** omit `tools:`; restrict via the Claude-only `disallowedTools:` denylist (comma-separated, ignored by Copilot). A Copilot `tools:` array makes Claude Code refuse to spawn the agent — see [agents.md, "Tools field"](./agents.md#tools-field) for the full rule and the Copilot trade-off.

```yaml
# No `tools:` — both platforms inherit all tools; Claude is scoped by the denylist.
disallowedTools: Edit, Write, Bash
```

### MCP Server Tools

MCP servers extend the tool ecosystem with integrations for external services. Common patterns:

```yaml
# All tools from a specific server
tools: ['read', 'edit', 'github/*']

# Specific tools from MCP servers
tools: ['read', 'edit', 'github/createPullRequest', 'github/listIssues']

# Multiple MCP servers
tools: ['read', 'edit', 'github/*', 'jira/*', 'database/*']
```

Consult your MCP server documentation for available tool names and capabilities.

## Tool Selection Patterns

### Read-Only Agents
**Purpose:** Analyze, review, or document code without modifications

```yaml
tools: ['read', 'search']
```

**Examples:**
- Code reviewers
- Documentation generators
- Security auditors
- Architecture analyzers

### Standard Implementation Agents
**Purpose:** Read, search, and modify code

```yaml
tools: ['read', 'search', 'edit']
```

**Examples:**
- Feature implementers
- Refactoring specialists
- Bug fixers
- Test generators

### Full-Stack Implementation Agents
**Purpose:** Complete development workflows including execution

```yaml
tools: ['read', 'search', 'edit', 'execute']
```

**Examples:**
- Build agents
- Test runners
- Deployment agents
- Setup automators

### Research Agents
**Purpose:** Gather information from code and external sources

```yaml
tools: ['read', 'search', 'web']
```

**Examples:**
- Documentation researchers
- Best practice advisors
- API reference lookups
- Framework migration guides

### Orchestrator Agents
**Purpose:** Coordinate multiple specialized agents

```yaml
tools: ['read', 'edit', 'search', 'agent']
```

**Examples:**
- Multi-phase project generators
- Complex refactoring pipelines
- Test-driven development workflows
- Multi-agent review processes

### Integration Agents
**Purpose:** Interact with external services via MCP

```yaml
tools: ['read', 'edit', 'github/*']
```

**Examples:**
- GitHub PR agents
- Jira ticket agents
- Database query agents
- API testing agents

## Best Practices

### Cut Tool Count Aggressively

Large tool surfaces degrade model tool-selection accuracy even when the extra tools are irrelevant to the current task — a mid-size model that fails a task at 46 available tools passes the same task at 19.

- Cut exposed tools per agent; don't trust the model to ignore ones it doesn't need
- Where the harness supports it, prefer deferred/on-demand tool loading over always exposing the full set

### Principle of Least Privilege

Grant only the tools needed for the agent's specific purpose.

✅ **Do:**
```yaml
# Security auditor - no modifications needed
tools: ['read', 'search', 'web']

# Refactoring agent - no execution needed
tools: ['read', 'search', 'edit']
```

❌ **Don't:**
```yaml
# Security auditor shouldn't need execution capabilities
tools: ['read', 'search', 'web', 'execute']

# Review agent shouldn't be able to edit
tools: ['read', 'search', 'edit']
```

**Note:** Tool names in examples are illustrative - verify actual names in your environment.

### Document Tool Justification

For agents with unusual tool combinations, add comments or metadata explaining why specific tools are needed.

```yaml
---
description: "Test generator that creates and runs tests to verify behavior"
name: "TDD Agent"
tools: ['read', 'search', 'edit', 'execute']  # 'execute' needed to run tests
metadata:
  toolJustification: "Requires 'execute' to run tests and verify generated code"
---
```

### Progressive Tool Grants

Start with minimal tools and add more as needed, rather than starting with all tools and removing them.

✅ **Recommended progression:**
1. Start: `['read', 'search']`
2. Add editing: `['read', 'search', 'edit']`
3. Add execution if needed: `['read', 'search', 'edit', 'execute']`

### Tool-Specific Guidelines

When using tools that modify the system or invoke sub-agents, follow these patterns:

**Execution tools** (e.g., `execute`, `run`, `terminal`):
- Only for agents that explicitly need to run commands
- Document which commands the agent should run
- Consider security implications (arbitrary code execution)

**Orchestration tools** (e.g., `agent`, `subagent`):
- Only for orchestrator agents
- Must include all tools needed by sub-agents
- Document the sub-agent workflow

**MCP server tools:**
- Use wildcards (`github/*`) for agent families
- Use specific tools (`github/createPullRequest`) for targeted agents
- Ensure MCP servers are installed and configured

## Tool Limitations and Errors

### Common Issues

**"Tool not available"**
- Tool not included in agent's `tools` list
- MCP server not installed or not running
- Tool disabled in workspace settings

**"Permission denied"**
- Workspace security policy restricts tool usage
- File permissions prevent access
- Parent orchestrator doesn't have required tools

**"Tool failed to execute"**
- Invalid command syntax (for execution tools)
- Missing dependencies (for execution tools)
- Network issues (for web/external access tools)

### Debugging Tool Issues

1. **Verify tool list:** Check frontmatter `tools` field
2. **Check MCP servers:** Ensure required servers are running
3. **Test manually:** Try the operation manually to verify it works
4. **Review logs:** Check agent execution logs for detailed errors

## Security Considerations

### High-Risk Tool Categories

These tool categories require extra caution:

1. **Execution tools** - Can run arbitrary commands on the system
2. **Edit tools** - Can modify or delete code and files
3. **MCP integration tools** - Depend on external service permissions and access

### Security Checklist

- [ ] Tools limited to agent's actual needs
- [ ] High-risk tools (execution, destructive operations) only when necessary
- [ ] MCP integrations use service accounts with limited permissions
- [ ] Tool usage documented in agent description
- [ ] Agent tested with malicious or edge-case inputs

### Defense in Depth

Even with limited tools, agents should follow safe practices:
- Validate inputs before processing
- Avoid destructive operations without confirmation
- Log significant actions for audit trails
- Handle errors gracefully

## Examples by Use Case

These examples use common tool names for illustration. Verify actual tool names in your environment, as they may vary by platform and configuration.

### Code Review Agent (Read-Only)
```yaml
---
description: "Reviews code for style, bugs, and best practices"
name: "Code Reviewer"
tools: ['read', 'search']
---
```

### Refactoring Agent (Safe Modifications)
```yaml
---
description: "Refactors code to improve structure and maintainability"
name: "Refactoring Specialist"
tools: ['read', 'search', 'edit']
---
```

### Test Runner (Execution Required)
```yaml
---
description: "Generates, runs, and validates test suites"
name: "Test Automation Agent"
tools: ['read', 'search', 'edit', 'execute']
---
```

### Documentation Researcher (External Access)
```yaml
---
description: "Researches documentation and generates guides"
name: "Documentation Agent"
tools: ['read', 'search', 'web', 'edit']
---
```

### GitHub Integration Agent (MCP)
```yaml
---
description: "Creates PRs, reviews code, and manages issues on GitHub"
name: "GitHub Agent"
tools: ['read', 'edit', 'search', 'github/*']
---
```

### Orchestrator Agent (Sub-Agent Management)
```yaml
---
description: "Coordinates multi-phase project setup and implementation"
name: "Project Orchestrator"
tools: ['read', 'edit', 'search', 'execute', 'agent']
---
```

## Further Reading

- [Agent Frontmatter Reference](./agent-frontmatter.md) - Complete frontmatter documentation
- [Sub-Agent Orchestration](./agent-subagent.md) - Using the `agent` tool for workflows
- [Common Agent Patterns](./agent-patterns.md) - Real-world agent examples
- [Anthropic — Writing Tools for Agents](https://www.anthropic.com/engineering/writing-tools-for-agents) - Tool design and count evidence
