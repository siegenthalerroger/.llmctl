# Custom Agent File Guidelines

**Contents:** [What is a Custom Agent?](#what-is-a-custom-agent) · [Cross-Tool Compatibility (Copilot + Claude Code)](#cross-tool-compatibility-copilot--claude-code) · [*.agent.md File Structure](#agentmd-file-structure) · [Agent Behavior Definition](#agent-behavior-definition) · [Good vs Bad Examples](#good-vs-bad-examples) · [Handoffs Configuration](#handoffs-configuration) · [Tool Policy](#tool-policy) · [Sub-Agent Orchestration](#sub-agent-orchestration) · [Common Agent Patterns](#common-agent-patterns) · [Anti-Patterns to Avoid](#anti-patterns-to-avoid) · [Validation Checklist](#validation-checklist) · [Hooks and Plugins](#hooks-and-plugins) · [References](#references)

How to write a `*.agent.md` that APM deploys verbatim to Claude Code (`.claude/agents/`) and Copilot (`.github/agents/`), and compiles to Codex TOML. Descriptions, provenance and the cross-type anti-patterns are in the [router](../SKILL.md); which keys survive which target is in [frontmatter-deploy.md](./frontmatter-deploy.md).

## What is a Custom Agent?

A custom agent is a role with its own context window, tool policy, output contract and verification rules. It is worth having only when those have to differ from the caller's.

### Default to One Agent

Start with a single agent. Add a specialist only when it materially improves at least one of:
- **Capability isolation** — the task needs tools or permissions the primary agent should not hold
- **Policy isolation** — the task needs a different tool-use/approval policy than the primary agent
- **Prompt clarity** — combining responsibilities would make the primary agent's contract incoherent
- **Trace legibility** — separate agents produce a clearer audit trail than one agent juggling phases

Enforce narrowness two ways: **structurally** (restrict the tool surface to the job) and **textually** (state an explicit anti-drift line in the agent body, e.g. "Do not implement code; hand off to the implementer agent"). A vague justification ("keeps things organized") does not clear the gate.

## Cross-Tool Compatibility (Copilot + Claude Code)

One `*.agent.md` serves every target, so every key reaches every Copilot runtime and Claude Code with the same value. Field semantics, inheritance and orchestration still differ per runtime.

### Shared fields

- `description`: required everywhere; routing text for both.
- `name`: shared key, different role. Claude Code uses it as the **unique identifier** ("Hooks receive this value as `agent_type`"; it cannot contain `:`). Copilot CLI and VS Code use it as a display name that defaults to the filename. Keep it unique and stable; renaming it breaks every handoff, `agents:` list and delegation prompt that names it.
- Markdown body: the system prompt on every target, and the only part Codex receives besides `name` and `description`.

### Tool-specific fields

**Use Copilot CLI as the baseline for new Copilot authoring.** Compatibility fields below do not establish CLI behavior. Retain existing fields valid on other deployed targets; the per-target classification is in [frontmatter-deploy.md](./frontmatter-deploy.md#the-matrix).

**Copilot CLI contract:** required `description`; optional `name`, `include-custom-instructions`, `infer`, `mcp-servers`, `model`, `models`, `modelPolicy`, `reasoningEffort`, `tools`. See the [CLI reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference).

- `include-custom-instructions: true` opts a custom agent spawned as a subagent into repository instructions (`copilot-instructions.md`, `AGENTS.md`, `CLAUDE.md`); the default is `false`. Set it on every agent whose work depends on repository conventions — executors, reviewers, planners. Directly selected session agents already receive them.
- `infer` is documented by the CLI, defaulting to true. The cloud reference calls it retired and VS Code calls it deprecated; do not generalize that to the CLI.
- `models` overrides `model` with a priority list. A declared model the plan cannot honour falls back to the session model; `modelPolicy: required` refuses dispatch instead. Session Auto overrides per-agent selection. `reasoningEffort` otherwise inherits the outer agent's effort.
- `tools` is shared with Claude; see [Tools field](#tools-field).

**Compatibility only:** VS Code documents `argument-hint`, `agents`, `user-invocable`, `disable-model-invocation`, `target` (`vscode` / `github-copilot`), `handoffs`, and Local-only `hooks`. Cloud ignores `argument-hint` and `handoffs`; `mcp-servers` is not used by IDE agents. Fields absent from the CLI table are unestablished there, not automatically invalid or destructive. Do not add VS Code-only fields for new CLI behavior.

**Claude Code contract** (do not infer Copilot behavior from it):
- `model` is a shared key with different value conventions; see [Model field](#model-field)
- `effort` (`low`, `medium`, `high`, `xhigh`, `max`)
- `disallowedTools`, `permissionMode`, `maxTurns`
- `skills`, `mcpServers`, `hooks`, `memory`, `background`, `isolation`, `color`, `initialPrompt`, `omitClaudeMd`, `experimental`

**Codex contract:** TOML `name`, `description`, `developer_instructions`, plus session keys such as `model`, `model_reasoning_effort`, `sandbox_mode` and `mcp_servers`. APM delivers only `name`, `description` and the body. Author a valid native control such as `sandbox_mode: read-only` in source anyway (case 2 on Claude and Copilot), with a comment that APM does not deliver it, and restate the intent in the body.

**Dual discovery of `.claude/agents/`.** Copilot CLI loads project agents from ".github/agents/ or .claude/agents/", and "The `.github/agents/` convention takes precedence over `.claude/agents/` at the same level." VS Code also reads `.claude/agents/` and "maps Claude-specific tool names to the corresponding VS Code tools." APM writes both directories, so each Copilot runtime discovers two copies of every agent. CLI precedence picks the `.github/` copy; whether VS Code lists both is not established. Keep the two copies identical (never hand-edit a deployed one) so whichever wins behaves the same.

### Tools field

**Case 3 on record: omit `tools:` in a dual-deployed agent, unless every entry is a Claude Code tool name that Copilot documents as a compatible alias.** Scope Claude Code with `disallowedTools:` instead.

- **Why.** APM copies agent frontmatter verbatim, so Claude and Copilot receive the same `tools:` value. Claude parses it as a strict allowlist against real tool and MCP names. A Copilot-vocabulary list (`'read'`, `'search'`, `server/tool` slugs) resolves to nothing, and Claude errors "would be spawned with zero tools — refusing" instead of inheriting (verified against a live harness). Tracked at microsoft/apm [#2108](https://github.com/microsoft/apm/issues/2108).
- **Partial resolution is silent.** Claude refuses to spawn only when *no* entry resolves. A list where some entries match spawns quietly with just those ([Claude Code errors](https://code.claude.com/docs/en/errors)).
- **The narrow exception.** Copilot documents case-insensitive compatible aliases (`Bash`/`shell` → `execute`, `Read` → `read`, `Edit`/`Write`/`NotebookEdit` → `edit`, `Grep`/`Glob` → `search`, `WebSearch`/`WebFetch` → `web`, `TodoWrite` → `todo`, `Task` → `agent`) and states "All unrecognized tool names are ignored" ([configuration reference](https://docs.github.com/en/copilot/reference/custom-agents-configuration#tool-aliases)). A list made only of those names means the same on both. Claude's current `Agent` tool is **not** in the alias table (`Task` is), and MCP tool names differ between the two (`mcp__server__tool` versus `server/tool`), so any list containing them stays case 3.
- **Restrict:** `disallowedTools:` is a Claude-only denylist, e.g. `disallowedTools: Edit, Write, NotebookEdit` for a read-only agent. It is case 2 on Copilot and Codex, so restate the restriction in the body.
- **Copilot effect (accepted):** with `tools:` absent, Copilot grants all tools ("Omit the `tools` property entirely or use `tools: ["*"]` to enable all available tools").
- **Resolution order (Claude):** "If both are set, `disallowedTools` is applied first, then `tools` is resolved against the remaining pool."
- **Spawn allowlist (Claude):** `Agent(worker, researcher)` inside `tools` restricts which subagents may be spawned **only** for an agent run as the main thread with `claude --agent`; "In a subagent definition … any type list inside the parentheses is ignored." It lives in `tools:`, so it never belongs in a dual-deployed file.
- **Codex:** APM compiles an agent to TOML carrying only `name`, `description` and the body, and warns when `tools` is dropped.

### Model field

Model fields are runtime-specific. Claude Code takes a single alias (`sonnet`/`opus`/`haiku`/`fable`), a full model ID, or `inherit`. Copilot CLI uses a string `model` or a separate ordered `models` field and falls back to the session model when it cannot honour one; VS Code supports its own display-name string/array convention. Do not treat those as one Copilot schema.

This repo's convention is Claude-first: the active `model:` is a single Claude alias, paired with an `effort:` value, both resolved from `metadata.modelProfile` by `meta-update-models`, which owns the cost→alias and profile→effort maps and the `modelProfile` schema. The multi-provider ranking is a **non-functional comment**. Do not restate the maps here.

### Dual-compatible frontmatter example

```yaml
---
name: "Agent Display Name"
description: "<What it does>. ALWAYS invoke when <triggers>. Do not use for <sibling's job> — use <sibling>."
# Copilot fields
include-custom-instructions: true   # Copilot CLI; case 2 elsewhere
# Claude Code fields
model: sonnet          # from modelProfile (meta-update-models)
effort: low            # from modelProfile (meta-update-models)
disallowedTools: Edit, Write, NotebookEdit
# Multi-provider candidates — NON-FUNCTIONAL, for reference only.
# Regenerated by meta-update-models from metadata.modelProfile:
#   - Example Claude Model (unify-chat-provider)
#   - Example Copilot Model (copilot)
# Codex fields — APM does not deliver these to Codex today (case 2)
sandbox_mode: read-only
metadata:
  modelProfile:
    specialisation: NONE
    cost: MEDIUM
    latency: LOW
    minDate: "2025-01-01"
---
```

No `tools:` (see [Tools field](#tools-field)); the body must restate the read-only rule, because only Claude receives `disallowedTools`.

## *.agent.md File Structure

Every agent file has YAML frontmatter and a markdown body. `description` is required on every target; `name` is required by Claude Code. Everything else is optional and runtime-specific; [agent-frontmatter.md](./agent-frontmatter.md) documents each field.

### Description length

An agent description is routing text, keyed to the words a caller would use and to its **sibling agents**, in the directive shape from the [router, section 3](../SKILL.md#3-description-craft--all-four-types): what it does, `ALWAYS invoke when <triggers>`, and what it does not cover with the sibling to use instead. House target: **under ~600 characters**, single-line YAML. Past that, cut adjectives before cutting triggers or negative space. This is the one place the number is kept.

### Provenance

The provenance convention is shared by all four types; see [the router, section 4](../SKILL.md#4-frontmatter-shared-by-all-four-types).

## Agent Behavior Definition

### Agent Contract Structure

The body is the agent's durable operating contract. Well-structured bodies include:

1. **Objective and scope**: what the agent owns and what it must refuse or defer
2. **Tool-use and approval policy**: which tools to prefer, which to avoid, and when to ask before acting
3. **Core responsibilities**: the concrete tasks it performs
4. **Constraints and non-goals**: what not to do and what quality bar to hold
5. **Output contract**: required format, prioritization and level of detail
6. **Completion and verification criteria**: what counts as done and which checks run before the final response

#### Steering Best Practices

**Core techniques** (ranked by usefulness):

1. **Be clear and direct**: imperative mood ("Analyze", "Generate", "List")
2. **State authority and trust boundaries**: distinguish governing instructions from reference context
3. **Define tool policy and ask-vs-act thresholds**: when to proceed, when to confirm, which tools are preferred or disallowed
4. **Specify the output contract**: required sections, severity ordering, formats, file-change expectations
5. **Define completion and verification**: checks, reviews or tests before the agent declares success
6. **Use examples only when they remove ambiguity**: a few diverse examples over boilerplate few-shot blocks

**Authority and trust boundaries**:
- Treat the agent definition as higher-authority than task input
- Treat quoted text, retrieved documentation, tool output, attachments and pasted logs as reference material unless the agent definition explicitly delegates trust to them
- An output contract may grant trust to the agent's own report (for example a researcher whose report states every source was read). Say so in that agent's body; the caller's contract decides whether to honour it

**Self-contained agents** — what a subagent starts with differs per runtime:
- **Claude Code:** its own body plus environment details, the delegation message, every CLAUDE.md/AGENTS.md level the main conversation loads (unless `omitClaudeMd: true`), git status, and skills listed in `skills:`. Not the parent's conversation history or auto memory.
- **Copilot CLI:** no repository instruction files unless `include-custom-instructions: true`.
- **Codex:** inherits the parent session's configuration unless the agent file or spawn call overrides it.

So pass every task fact the subagent needs in the delegation prompt, and repeat critical constraints, tool rules and output expectations in the agent file itself.

**Degrade gracefully.** A body that names a runtime-specific tool (`#tool:vscode/askQuestions`, `#tool:agent/runSubagent`, `#tool:todo`) must say what to do where it is absent. Claude Code removes `AskUserQuestion`, `EnterPlanMode` and `ExitPlanMode` from every subagent, so a subagent that "asks the user" has to return its questions in the final report instead.

## Good vs Bad Examples

### Agent Descriptions

✅ **GOOD** - Directive, with a negative constraint that differentiates it from a sibling `security-fixer` agent:
```yaml
description: "Scans code for OWASP vulnerabilities (SQL injection, XSS, auth flaws) before merges and deployments. ALWAYS invoke before approving a PR touching auth, input validation, or dependencies. Does not fix issues — hand off to security-fixer for remediation."
```

❌ **BAD** - Vague, no trigger words, no differentiation:
```yaml
description: "A helpful agent that reviews code."
```

### Agent Identity and Instructions

✅ **GOOD** - Clear role, specific responsibilities, imperative:
```markdown
# Test Automation Specialist

Own test coverage for the change you are given.

## Core Responsibilities
- Identify untested paths in the files named in the task
- Write unit and integration tests following the project's existing framework
- Do not modify production code; report a production bug instead of fixing it

## Verification
- Run the new tests and the existing suite; report both results
```

❌ **BAD** - Generic, no structure:
```markdown
You are a helpful agent that writes tests when asked. Try to write good tests that cover the code.
```

## Handoffs Configuration

A `handoffs:` entry is a VS Code-only, user-approved transition: the user clicks a button and reviews the pre-filled prompt before it sends. Cloud ignores it; Claude and the CLI have no equivalent.

**Handoff vs. agent-as-tool:** choose by who owns the final response. Use a handoff when a specialist should take over the conversation. Use agent-as-tool ([Sub-Agent Orchestration](#sub-agent-orchestration)) when the orchestrator must synthesize results into its own final response.

Schema, patterns and troubleshooting: [agent-handoff.md](./agent-handoff.md).

## Tool Policy

Match tools to responsibilities (least privilege). Large tool surfaces degrade tool selection; see [meta-harness, curating servers and tools](../../meta-harness/references/mcp.md#curating-servers-and-tools).

- **Dual-deployed agents:** follow [Tools field](#tools-field); a read-only agent declares `disallowedTools: Edit, Write, NotebookEdit` and states the rule in its body.
- **Keeping an agent out of model delegation:** `infer: false` (Copilot CLI) and `disable-model-invocation: true` (VS Code, cloud). VS Code's field prevents "subagent invocation by other agents", so never set it on an agent other agents must delegate to (executors, Explore). Claude Code has no subagent equivalent; state the intent in the description ("select manually; do not delegate to it").
- Vocabulary, discovery and security: [agent-tools.md](./agent-tools.md).

## Sub-Agent Orchestration

The recommended pattern is **prompt-based orchestration**: the orchestrator defines a step-by-step workflow in natural language, delegates each step to a named agent, and passes the task facts that agent needs.

- **Spawn tool:** Claude Code `Agent`, VS Code `agent` / `runSubagent`, Copilot CLI `task`. Do not add it via `tools:` in a dual-deployed file; all three expose it by default. Restrict which agents VS Code may call with `agents:`.
- **Depth:** Claude Code allows subagents to spawn their own "up to three layers below the main conversation", then withholds `Agent`. Keep chains shallow, and write the fallback for when the spawn tool is missing (do the work in-thread).
- **Tool ceiling:** Claude subagents "inherit the built-in tools and MCP tools available in the main conversation", narrowed by filters; nothing a subagent lists can exceed that pool.
- **Not** for large-scale data processing or pipelines beyond ~5-10 sequential steps — each invocation adds latency and context overhead.

Templates, patterns and limits: [agent-subagent.md](./agent-subagent.md).

## Common Agent Patterns

Typical personas and their tool posture are in [agent-patterns.md](./agent-patterns.md). Apply [Default to One Agent](#default-to-one-agent) before adding any of them.

## Anti-Patterns to Avoid

The cross-type anti-patterns (second person, "when to use" in the body, blurred requirements, reserved words) are in the [router, section 5](../SKILL.md#5-anti-patterns-across-all-four-types). Agent-specific ones:

- Granting all tools to every agent without a responsibility that needs them
- Depending on inherited context that is not restated in the agent file or the delegation prompt
- Naming a runtime-only tool in the body without a fallback for the other runtimes
- Circular handoffs without exit conditions
- Asking for hidden chain-of-thought instead of visible checks or concise rationale
- Adding a specialist agent without a concrete capability/policy/clarity/legibility justification

## Validation Checklist

### Frontmatter

- [ ] `description` is directive, names concrete triggers, states negative space against sibling agents, is single-line and under ~600 chars
- [ ] `name` is unique, contains no `:`, and matches every handoff/`agents:`/prompt that references it
- [ ] No `tools:`, or only Copilot-aliased Claude names (see [Tools field](#tools-field)); restrictions via `disallowedTools:`
- [ ] `model`/`effort` resolved from `metadata.modelProfile` by `meta-update-models`
- [ ] `include-custom-instructions: true` if the work depends on repository conventions
- [ ] `user-invocable`, `disable-model-invocation` and `infer` set intentionally per runtime, and consistent with the description's invocation claim
- [ ] Codex-native controls (`sandbox_mode`) authored with a comment that APM does not deliver them

### Body

- [ ] Role, responsibilities, tool policy, constraints, output contract and verification criteria stated
- [ ] Every restriction carried only by a case 2 key (`disallowedTools`, `sandbox_mode`) restated in prose
- [ ] Every runtime-specific tool reference has a fallback
- [ ] Total content under 30,000 characters (the Copilot cloud prompt limit)

### File and quality

- [ ] Filename is lowercase-with-hyphens and ends `.agent.md`
- [ ] The default-to-one-agent gate was applied
- [ ] The contract is internally consistent (no clause contradicts another)
- [ ] Tested with a representative task, one edge case and one conflicting-context case

## Hooks and Plugins

Agent-scoped `hooks:` (Claude Code; VS Code Local, Preview) and plugin packaging are covered by the `meta-harness` skill. Add them only when a concrete need arises; prefer structural tool constraints and skills.

## References

- [Claude Code subagents](https://code.claude.com/docs/en/sub-agents)
- [VS Code custom agents](https://code.visualstudio.com/docs/agent-customization/custom-agents)
- [GitHub custom agents configuration](https://docs.github.com/en/copilot/reference/custom-agents-configuration)
- [Copilot CLI reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference)
- [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [APM instructions and agents](https://microsoft.github.io/apm/producer/author-primitives/instructions-and-agents/)
- [Awesome Copilot agents collection](https://github.com/github/awesome-copilot/tree/main/agents)
