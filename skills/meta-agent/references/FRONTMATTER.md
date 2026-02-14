# Agent Frontmatter Reference

This document provides guidance on common frontmatter properties for custom agent files. Available properties may vary by platform and version - consult your platform's official documentation for the complete, up-to-date reference.

## Required Fields

### `description`

**Type:** String
**Required:** Yes (conditionally - see `infer` field)
**Length:** 50-150 characters recommended

A clear, concise description of the agent's purpose and capabilities. This should:
- Be keyword-rich to enable discovery
- Explain what the agent does and when to use it
- Include relevant keywords for searchability
- Avoid XML tags or reserved words (`anthropic`, `claude`, `openai`, `copilot`)

**Example:**
```yaml
description: "Security auditor that scans code for vulnerabilities using OWASP guidelines. Use when reviewing authentication, authorization, input validation, or before deployments. Keywords: security, vulnerability, OWASP, SQL injection, XSS."
```

### `name`

**Type:** String
**Required:** Yes

The display name for the agent shown in the UI. Should be:
- Clear and descriptive
- Title case (e.g., "Test Automation Specialist")
- Distinct from other agents

**Example:**
```yaml
name: "Security Audit Agent"
```

## Optional Fields

### `tools`

**Type:** Array of strings
**Required:** No (defaults to all tools)

Specifies which tools the agent can access. Available tools vary by platform and installed extensions/MCP servers.

**Common patterns:**
- Specific tools: Array of tool names (e.g., `['read', 'edit', 'search']`)
- All tools: `'*'` or omit the field entirely
- No tools: `[]`
- MCP server tools: Use wildcards (e.g., `'github/*'`) or specific tool names

**Best Practice:** Follow the principle of least privilege - only enable tools necessary for the agent's purpose. See [TOOLS.md](./TOOLS.md) for detailed guidance.

**Example:**
```yaml
# Read-only code reviewer
tools: ['read', 'search']

# Full implementation agent
tools: ['read', 'search', 'edit', 'execute', 'agent']

# MCP server tools
tools: ['read', 'edit', 'github/*']
```

### `model`

**Type:** String or Array of strings  
**Required:** No

Specifies the preferred AI model(s) for this agent. Use this when:
- Agent requires specific model capabilities (e.g., extended context, reasoning)
- Agent prompts are optimized for a specific model family
- Performance characteristics matter (speed vs. quality trade-offs)

**Value Format:**
Model identifiers vary by platform and provider. Can be a single string or an array of strings for fallback options.

**Example patterns:**
- Provider-specific identifiers (e.g., `"gpt-4"`, `"claude-sonnet-4.5"`)
- Capability-based identifiers (e.g., `"reasoning-model"`, `"fast-model"`)
- Version-specific identifiers (e.g., `"model-v2.1"`)

**Examples:**
```yaml
# Single model
model: "your-preferred-model"

# Multiple models with fallback
model: ["primary-model", "fallback-model", "backup-model"]
### `target`

**Type:** String
**Required:** No

Specifies the environment where this agent is available. Used to control agent visibility across different contexts.

**Common Values:**
- `"vscode"` - Only available in VS Code
- `"cli"` - Only available in command-line interfaces
- `"web"` - Only available in web interfaces

**Example:**
```yaml
target: "vscode"
```

### `infer`

**Type:** Boolean
**Required:** No (defaults to `true`)

Controls whether the agent can be automatically suggested/inferred based on context, or if it must be manually selected by the user.

- `true` (default): Agent can be auto-suggested based on workspace context and task
- `false`: Agent must be explicitly selected by user (useful for specialized workflows)

**Example:**
```yaml
infer: false  # Must be manually invoked
```

### `handoffs`

**Type:** Array of objects
**Required:** No

Defines multi-step workflows where the agent hands off control to other specialized agents. Each handoff object contains configuration for transitioning to another agent.

See [HANDOFF.md](./HANDOFF.md) for complete documentation.

**Example:**
```yaml
handoffs:
  - name: "implementer"
    description: "Hand off to implementation agent"
    agent: "code-implementer"
```

### `license`

**Type:** String
**Required:** No

Specifies the license under which the agent definition is distributed (e.g., MIT, Apache-2.0, GPL-3.0).

**Example:**
```yaml
license: "MIT"
```

### `metadata`

**Type:** Object
**Required:** No

Additional metadata about the agent. Can contain any custom key-value pairs. Common uses:
- `author`: Agent creator
- `version`: Agent version number
- `adaptedFrom`: Source URL if adapted from another agent
- `tags`: Additional categorization tags

**Example:**
```yaml
metadata:
  author: "Engineering Team"
  version: "1.2.0"
  adaptedFrom: "https://github.com/example/agents"
  tags: ["security", "compliance"]
```

## Minimal Frontmatter Example

The absolute minimum required frontmatter:

```yaml
---
description: "Security auditor for OWASP vulnerability scanning"
name: "Security Auditor"
---
```

## Complete Frontmatter Example

A comprehensive example with all fields:

```yaml
---
description: "Security auditor that scans code for vulnerabilities using OWASP guidelines. Use when reviewing authentication, authorization, input validation, or before deployments. Keywords: security, vulnerability, OWASP."
name: "Security Audit Agent"
tools: ['read', 'search', 'web']
model: ["your-preferred-model", "an-alternative-model", "an-acceptable-backup-model"]  # Example: platform-specific model identifiers
target: "vscode"
infer: true
license: "MIT"
metadata:
  author: "Security Team"
  version: "2.1.0"
  tags: ["security", "owasp", "vulnerability-scanning"]
handoffs:
  - name: "remediation"
    description: "Hand off to fix identified vulnerabilities"
    agent: "security-fixer"
---
```

## Validation Rules

1. **description**: Must be present (unless `infer: false`), 50-150 chars recommended
2. **name**: Must be present and unique within agent collection
3. **tools**: If specified, must be valid tool names or patterns
4. **model**: If specified, must be a supported model identifier
5. **target**: If specified, must be a valid target environment
6. **infer**: If specified, must be boolean
7. **handoffs**: If specified, must follow handoff schema (see HANDOFF.md)

## Common Mistakes

❌ **Don't:**
- Use XML tags in description (`<anthropic>`, `<claude>`)
- Make description too vague ("A helpful agent")
- Grant all tools without justification
- Forget to specify required `description` and `name`

✅ **Do:**
- Write keyword-rich descriptions
- Match tools to agent responsibilities
- Use `infer: false` for specialized workflow agents
- Add metadata for maintainability

## Further Reading

- Check your platform's official documentation for the complete, up-to-date list of available frontmatter properties
- [TOOLS.md](./TOOLS.md) - Tool configuration patterns and best practices
- [HANDOFF.md](./HANDOFF.md) - Handoff configuration for multi-agent workflows
- [SUBAGENT.md](./SUBAGENT.md) - Sub-agent orchestration patterns
