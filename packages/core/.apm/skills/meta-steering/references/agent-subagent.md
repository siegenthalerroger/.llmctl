# Sub-Agent Orchestration Reference

**Contents:** [Overview](#overview) · [Prerequisites](#prerequisites) · [How It Works](#how-it-works) · [Recommended Pattern: Prompt-Based Orchestration](#recommended-pattern-prompt-based-orchestration) · [Orchestrator Structure](#orchestrator-structure) · [Common Orchestration Patterns](#common-orchestration-patterns) · [Best Practices](#best-practices) · [Limitations and Warnings](#limitations-and-warnings) · [Debugging Orchestration](#debugging-orchestration) · [Example: Complete Orchestrator](#example-complete-orchestrator) · [Further Reading](#further-reading)

How an orchestrator agent delegates steps to specialised sub-agents and synthesises their results.

## Overview

Use sub-agent orchestration for complex workflows split into phases, for domain specialists per phase, for quality gates between steps, and to keep search and read noise out of the main context.

**What a sub-agent starts with differs per runtime:**

- **Claude Code:** its own body plus environment details, the delegation message, every CLAUDE.md/AGENTS.md level the main conversation loads (unless `omitClaudeMd: true`), a git status snapshot, and skills named in `skills:`. It never sees the parent's conversation history or auto memory.
- **Copilot CLI:** a custom agent spawned as a subagent gets no repository instruction files unless it sets `include-custom-instructions: true`.
- **VS Code:** subagents run in their own context; verify what a given agent inherits in the current release.
- **Codex:** inherits the parent session's configuration unless the agent file or spawn call overrides it.

On every runtime, pass the facts the sub-agent needs (paths, IDs, prior decisions, constraints) in the delegation prompt, or restate them in its `.agent.md`.

### Agent-as-Tool vs. Handoff

Choose sub-agent orchestration (agent-as-tool) when the orchestrator must synthesize results into its own final response. Choose a handoff ([agent-handoff.md](./agent-handoff.md)) when a specialist should take over the conversation. Mixing both for the same transition signals an unclear contract — pick one.

## Prerequisites

### Enabling Agent Orchestration

| Runtime | Spawn tool | Restricting which agents may be called |
|---|---|---|
| Claude Code | `Agent` (on by default) | `Agent(a, b)` in `tools`, **only** for an agent run with `claude --agent`; ignored in subagent definitions |
| VS Code | `agent` / `runSubagent` | `agents: ['A', 'B']`, `*` or `[]` |
| Copilot CLI | `task` | Target agent's `infer: false` keeps it out of auto-delegation |
| Copilot cloud | `agent` alias (`custom-agent`, `Task`) | Target's `disable-model-invocation: true` |

In a dual-deployed file, do not add the spawn tool through `tools:` ([agent-guide.md, Tools field](./agent-guide.md#tools-field)); omitting `tools:` already grants it.

### Tool Availability Requirement

A sub-agent cannot use a tool its caller's pool lacks. Claude Code: subagents "inherit the built-in tools and MCP tools available in the main conversation", narrowed by filters that always remove `AskUserQuestion`, `EnterPlanMode` and (outside `permissionMode: plan`) `ExitPlanMode`. Nothing a sub-agent lists in `tools` can exceed that pool.

## How It Works

1. The orchestrator defines a step-by-step workflow
2. For each step, it invokes a named sub-agent with a self-contained prompt
3. The harness loads that agent's body as its system prompt and applies its tool policy; the sub-agent does the work
4. The sub-agent returns a summary as its final message
5. The orchestrator validates the result and proceeds

## Recommended Pattern: Prompt-Based Orchestration

### Wrapper Prompt Template

Invoke the agent **by name** through the spawn tool, so the harness applies its definition. Then give it the task:

```text
Work unit: "<WORK_UNIT_NAME>", base path "<BASE_PATH>".
Inputs: <INPUT_FILES>. Outputs: <OUTPUT_FILES>.
Constraints: <facts and decisions this agent cannot know>.
Return: actions taken, files produced or modified, issues found.
```

Do not tell a sub-agent to "read and apply its .agent.md tools": tool policy is enforced by the harness from frontmatter, not by the model re-reading its own file.

### Optional: Structured Context Block

For traceability, embed a small JSON block in the prompt:

```text
{
  "step": "<STEP_ID>",
  "agent": "<AGENT_NAME>",
  "basePath": "<BASE_PATH>",
  "inputs": ["<INPUT_FILE_1>"],
  "outputs": ["<OUTPUT_FILE_1>"]
}
```

## Orchestrator Structure

### Essential Elements

1. **Dynamic parameters**: values extracted from user input (`projectName`, `basePath`)
2. **Sub-agent registry**: which step uses which agent name
3. **Step ordering**: explicit sequence and dependencies
4. **Trigger conditions** (optional): when a step runs or is skipped
5. **Failure handling**: what stops the workflow and what is reported
6. **Fallback**: what the orchestrator does itself when the spawn tool is absent

### Keep It Generic

Write the workflow as natural-language steps, not embedded code:

```text
Step 1: Extract user requirements
Step 2: Generate project structure based on requirements (depends on Step 1)
Step 3: Validate generated structure; if validation fails, report and stop
```

## Common Orchestration Patterns

Each pattern is the same step block with a different registry; conditional and failure rules go in the step text.

| Pattern | Steps | Gate between steps |
|---|---|---|
| Planning → Implementation | planner, implementer | plan file exists and is approved |
| Implementation → Review | implementer, reviewer | tests pass before review |
| Test-Driven Development | test writer, implementer, test runner | new tests fail first, then pass |
| Research → Documentation | researcher, documenter | every claim has a source |
| Multi-Agent Review | security, performance, accessibility reviewers (parallel), consolidator | all reviews written before consolidation |
| Conditional step | checker, generator | run generator only if checker reports coverage < target |

## Best Practices

### ✅ Do

- **Name steps clearly**: "Step 1: Validate requirements", not "Step 1"
- **Pass minimal but sufficient context**: the facts the sub-agent cannot infer
- **Require summaries**: every sub-agent reports what it did and what it could not do
- **Validate results** before dependent steps
- **Use explicit paths**: `${basePath}/output/file.md`, not "the output file"
- **Keep chains shallow**: 5-10 steps maximum per orchestrator; nest only where a step genuinely needs its own delegation

### ❌ Don't

- **Over-orchestrate**: do simple tasks in-thread
- **Create circular handoffs** without exit conditions
- **Skip error handling**
- **Overlap responsibilities** between sub-agents
- **Process bulk data** through sub-agents

## Limitations and Warnings

### Not Suitable for Large-Scale Processing

Not appropriate for hundreds of files, large datasets, bulk transformations, more than ~10 sequential steps, or high-frequency event processing: each invocation adds latency and context overhead. Implement that logic in a single agent.

### Complexity Overhead

More agents mean more to maintain, more failure points, harder debugging and longer runs. Orchestrate only when specialisation, quality gates or reuse outweigh that.

### Nesting Depth

Claude Code lets a subagent spawn its own "up to three layers below the main conversation", then withholds `Agent`. Nested delegation in this repository (Executor (Broad) → Executor (Focused), Plan → Explore) fits inside that. Every agent that delegates must also say what it does when the spawn tool is absent.

## Debugging Orchestration

| Symptom | Check |
|---|---|
| Sub-agent not invoked | Spawn tool present; agent `name` exact; VS Code `agents:` list includes it; target not `disable-model-invocation: true` |
| Sub-agent lacks tools | Caller's pool; subagent filters; `disallowedTools` |
| Sub-agent ignores repository conventions | Copilot CLI: `include-custom-instructions: true`; Claude: `omitClaudeMd` not set |
| Step failures | Previous output exists; paths substituted; sub-agent report |

Test each sub-agent on its own before wiring it into an orchestrator.

## Example: Complete Orchestrator

```yaml
---
name: "Project Setup Orchestrator"
description: "Orchestrates new project setup: planning, scaffolding and validation via sub-agents. ALWAYS invoke to create a new project from a brief. Does not modify existing projects — use Executor (Broad)."
include-custom-instructions: true
---

# Project Setup Orchestrator

Coordinate specialised agents to create a project. Extract `projectName`, `projectType` and `basePath` (default `./${projectName}`) from the request.

## Workflow

1. Delegate to **project-planner**: write `${basePath}/PROJECT_PLAN.md`; return features, structure, open questions.
2. Delegate to **project-scaffolder** (after 1): create the structure the plan describes; return files and directories created.
3. Delegate to **project-validator** (after 2): run available build and test commands; write `${basePath}/VALIDATION.md`; return status and issues.

If a step fails, report its output and stop. If the spawn tool is unavailable, perform the steps yourself in order.

## Final Report

Summarize what was created, list validation issues, and give next steps.
```

## Further Reading

- [agent-guide.md](./agent-guide.md#sub-agent-orchestration) - summary rules
- [agent-tools.md](./agent-tools.md) - tool vocabulary
- [agent-frontmatter.md](./agent-frontmatter.md) - orchestrator frontmatter
- [agent-handoff.md](./agent-handoff.md) - the alternative to orchestration
