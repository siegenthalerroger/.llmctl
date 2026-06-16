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

# Multiple models with ordered fallback
model: ["free-model", "preferred-paid-model", "backup-model"]
```

For Copilot model arrays, order matters: the harness chooses the first available entry. For `FREE` profiles, put genuinely suitable free options first. For non-`FREE` profiles, prefer the best-fitting models within the requested cost band and do **not** put free options first by default. Use the exact accepted display strings, preserving casing and provider-specific suffixes.

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

### `user-invocable`

**Type:** Boolean
**Required:** No

Controls whether users can manually invoke the agent from the client UI or command surface where supported.

**Example:**
```yaml
user-invocable: true
```

### `infer`

**Type:** Boolean
**Required:** No (defaults to `true`)

Controls whether the agent can be automatically suggested/inferred based on context, or if it must be manually selected by the user.

- `true` (default): Agent can be auto-suggested based on workspace context and task
- `false`: Agent must be explicitly selected by user (useful for specialized workflows)

**Note:** This field is legacy or deprecated in some clients. Avoid adding it to new files unless the target platform still documents it.

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
- `provenance`: Provenance tracking (see below)
- `tags`: Additional categorization tags

**Provenance** is grouped under `metadata.provenance`:
- `provenance.mirror` (string): Canonical upstream URL for exact copies
- `provenance.adaptedFrom` (string or array): URL or list of URLs when adapted/synthesised from upstream sources
- `provenance.authoritativeSpec` (array): URLs of authoritative specifications defining the file format (informational only)

#### `metadata.modelProfile`

Declarative capability profile used by the `meta-update-models` skill to resolve the ordered `model:` array at run-time by consulting authoritative provider documentation. Use it only in customization files that support the top-level `model` frontmatter field.

**Schema:**

| Field | Allowed values | Semantics |
|---|---|---|
| `specialisation` | `NONE` \| `CODE` \| `REASONING` \| `LONG-CONTEXT` | `CODE` prefers Codex-family/code-optimised models; `REASONING` prefers models with extended thinking/chain-of-thought capabilities; `LONG-CONTEXT` prefers models with the largest context windows (≥200K tokens); `NONE` accepts general-purpose models |
| `cost` | `FREE` \| `LOW` \| `MEDIUM` \| `HIGH` | Abstract cost tier mapped to each provider's pricing metric by the skill. `FREE`=truly zero incremental usage, `LOW`=light usage burn, `MEDIUM`=standard included usage, `HIGH`=premium or high-burn usage. |
| `latency` | `LOW` \| `MEDIUM` \| `HIGH` | `LOW` selects fastest/smallest models; used as tie-breaker |
| `minDate` | ISO 8601 date string | Exclude models retired before this date |

The `meta-update-models` skill fetches **all supported providers in parallel** and combines the results into one ordered `model:` array. The harness chooses the first available entry, so qualifying free models are placed first; after that free-first prefix, the skill reserves Claude Code, OpenAI-backed models available through Codex, and GitHub Copilot coverage in that order. Subscription-included Claude Code and OpenAI Codex models are not automatically `FREE`. No `provider` field is needed in the profile.

**Example:**

```yaml
metadata:
  modelProfile:
    specialisation: CODE
    cost: FREE
    latency: LOW
    minDate: "2025-01-01"
```

**Example (mirror):**
```yaml
metadata:
  provenance:
    mirror: "https://github.com/example/agents/blob/main/security.agent.md"
```

**Example (synthesised from multiple sources):**
```yaml
metadata:
  provenance:
    adaptedFrom:
      - "https://github.com/org-a/skills/blob/main/skills/security/SKILL.md"
      - "https://github.com/org-b/copilot-rules/blob/main/instructions/owasp.instructions.md"
  tags: ["security", "compliance"]
```

**Example (authoritative spec for dual-tool compatibility):**
```yaml
metadata:
  provenance:
    authoritativeSpec:
      - "https://code.claude.com/docs/en/sub-agents"
      - "https://code.visualstudio.com/docs/copilot/customization/custom-agents"
```

For consistency across customization types, use the same provenance keys in prompt, instruction, skill, and agent files.

## Claude Code-Specific Fields

These fields are recognized by Claude Code only. Copilot safely ignores them. Include them alongside Copilot fields for dual-tool compatibility.

### `disallowedTools`

**Type:** Comma-separated string
**Required:** No

Tools to deny from the inherited set. Use when Claude Code inherits all tools (because Copilot's `tools` array is not parseable by Claude) and you want to restrict specific Claude tools.

**Example:**
```yaml
disallowedTools: Edit, Write  # read-only agent
```

### `permissionMode`

**Type:** String
**Required:** No

Controls how the subagent handles permission prompts. Values: `default`, `acceptEdits`, `dontAsk`, `bypassPermissions`, `plan`.

### `skills`

**Type:** Array of strings
**Required:** No

Claude Code skills to preload into the subagent's context at startup.

### `memory`

**Type:** String
**Required:** No

Persistent memory scope: `user`, `project`, or `local`. Enables cross-session learning.

### `hooks`

**Type:** Object
**Required:** No

Lifecycle hooks scoped to the subagent (e.g., `PreToolUse`, `PostToolUse`, `Stop`).

### `mcpServers`

**Type:** Object
**Required:** No

MCP servers available to the subagent. Each entry is a server name or inline definition.

### Other Claude Code fields

- `maxTurns` (number): Maximum agentic turns before stopping
- `background` (boolean): Always run as a background task
- `isolation` (`worktree`): Run in a temporary git worktree

## Minimal Frontmatter Example

The absolute minimum required frontmatter:

```yaml
---
description: "Security auditor for OWASP vulnerability scanning"
name: "Security Auditor"
---
```

## Complete Frontmatter Example

A comprehensive dual-compatible example with Copilot and Claude Code fields:

```yaml
---
description: "Security auditor that scans code for vulnerabilities using OWASP guidelines. Use when reviewing authentication, authorization, input validation, or before deployments. Keywords: security, vulnerability, OWASP."
name: "Security Audit Agent"
# Copilot fields
tools: ['read', 'search', 'web']
model: ["Claude Sonnet 4.6 (copilot)", "GPT-5.2 (copilot)"]
target: "vscode"
infer: true
handoffs:
  - name: "remediation"
    description: "Hand off to fix identified vulnerabilities"
    agent: "security-fixer"
# Claude Code fields
disallowedTools: Edit, Write
permissionMode: plan
license: "MIT"
metadata:
  author: "Security Team"
  version: "2.1.0"
  provenance:
    mirror: "https://github.com/example/security-agents"
    authoritativeSpec:
      - "https://code.claude.com/docs/en/sub-agents"
      - "https://code.visualstudio.com/docs/copilot/customization/custom-agents"
  tags: ["security", "owasp", "vulnerability-scanning"]
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
