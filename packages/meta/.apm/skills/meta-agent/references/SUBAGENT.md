# Sub-Agent Orchestration Reference

This document provides guidance on using the `agent` tool to orchestrate multi-step workflows with specialized sub-agents.

## Overview

**Sub-agent orchestration** enables an orchestrator agent to delegate work to specialized agents, creating powerful multi-step workflows. This pattern is useful for:

- **Complex workflows**: Breaking large tasks into manageable phases
- **Specialized expertise**: Leveraging domain-specific agents for each phase
- **Quality gates**: Reviewing output before proceeding to the next step
- **Separation of concerns**: Planning vs. implementation vs. review

Availability, inheritance rules, and recursion limits vary by client. Do not assume every platform exposes this capability or allows sub-agents to invoke further sub-agents.

**Context isolation:** a sub-agent receives only its own system prompt plus basic environment info — never the parent conversation's history, memory, or instructions. Every fact the sub-agent needs (paths, IDs, prior decisions, constraints) must be passed explicitly in the invocation prompt or restated in the sub-agent's own `.agent.md` file.

### Agent-as-Tool vs. Handoff

Choose sub-agent orchestration (agent-as-tool) when the orchestrator must synthesize results from one or more specialists into its own final response. Choose a handoff (see [HANDOFF.md](./HANDOFF.md)) when a specialist should take over the conversation and own the final response instead. Mixing both patterns for the same transition usually signals an unclear contract — pick one.

## Prerequisites

### Enabling Agent Orchestration

To invoke sub-agents, include `'agent'` in the orchestrator's tools list:

```yaml
---
description: "Orchestrates multi-phase project setup workflows"
name: "Project Orchestrator"
tools: ['read', 'edit', 'search', 'agent']  # Tool names are platform-specific examples
---
```

**Note:** Tool names used in examples may vary by platform. Consult your platform's documentation for available tool identifiers.

### Tool Availability Requirement ⚠️

**Critical:** If sub-agents need specific tools (e.g., `edit`, `execute`, `search`), the orchestrator **must** include those tools in its own `tools` list. Sub-agents cannot access tools that aren't available to their parent orchestrator.

**Example:**
```yaml
# If sub-agents need to edit files and run tests
tools: ['read', 'edit', 'search', 'execute', 'agent']
```

The orchestrator's tool permissions act as a **ceiling** for all invoked sub-agents.

**Claude Code:** restrict which named sub-agents an orchestrator may spawn structurally, via `Agent(worker, researcher)` syntax inside `tools`, rather than describing the allowed set in prose.

## How It Works

### Basic Invocation Pattern

1. **Orchestrator** defines a step-by-step workflow
2. For each step, the orchestrator invokes a **specialized sub-agent**
3. Sub-agent reads its `.agent.md` spec, applies tools and constraints, and performs work
4. Sub-agent returns a summary to the orchestrator
5. Orchestrator validates results and proceeds to the next step

### Sub-Agent Invocation Syntax

Use the `agent` tool (or `runSubagent` function) to invoke a sub-agent:

```yaml
Agent: name-of-subagent
Spec: path/to/subagent.agent.md
Context: key=value, key2=value2
Input: /path/to/input
Output: /path/to/output
Expected: description of expected outputs
```

## Recommended Pattern: Prompt-Based Orchestration

The **prompt-based orchestration pattern** provides consistency, maintainability, and tool-agnostic coordination.

### Wrapper Prompt Template

Use this consistent structure for every sub-agent invocation:

```text
This phase must be performed as the agent "<AGENT_NAME>" defined in "<AGENT_SPEC_PATH>".

IMPORTANT:
- Read and apply the entire .agent.md spec (tools, constraints, quality standards).
- Work on "<WORK_UNIT_NAME>" with base path: "<BASE_PATH>".
- Perform the necessary reads/writes under this base path.
- Return a clear summary (actions taken + files produced/modified + issues).
```

### Optional: Structured Context Block

For traceability and debugging, embed a small JSON block in the prompt:

```text
{
  "step": "<STEP_ID>",
  "agent": "<AGENT_NAME>",
  "spec": "<AGENT_SPEC_PATH>",
  "basePath": "<BASE_PATH>",
  "inputs": ["<INPUT_FILE_1>", "<INPUT_FILE_2>"],
  "outputs": ["<OUTPUT_FILE_1>", "<OUTPUT_FILE_2>"]
}
```

This provides structured context while remaining human-readable and tool-agnostic.

## Orchestrator Structure

### Essential Elements

Well-designed orchestrators document these structural elements:

1. **Dynamic parameters**: Values extracted from user input (e.g., `projectName`, `basePath`)
2. **Sub-agent registry**: Mapping of steps to agent names and spec paths
3. **Step ordering**: Explicit sequence (Step 1 → Step 2 → ... → Step N)
4. **Trigger conditions** (optional): When a step runs vs. is skipped
5. **Logging strategy** (optional): Tracking progress and results

### Keep It Generic

Avoid embedding orchestration "code" (JavaScript, Python, etc.) inside the orchestrator prompt. Prefer deterministic, tool-driven coordination with natural language instructions.

**✅ Good (Natural Language):**
```text
Step 1: Extract user requirements
Step 2: Generate project structure based on requirements
Step 3: Validate generated structure
```

**❌ Bad (Embedded Code):**
```python
# Don't embed code in orchestrator prompts
for step in steps:
    agent.invoke(step.name, step.spec)
```

## Basic Orchestration Pattern

### Single-Step Invocation

Structure each sub-agent invocation with:

1. **Step description**: Clear one-line purpose
2. **Agent identity**: `agentName` + `agentSpecPath`
3. **Context**: Explicit variables (paths, IDs, environment)
4. **Expected outputs**: Files to create/update
5. **Return summary**: Request structured feedback

**Example:**
```text
Step 1: Analyze project requirements

Agent: requirements-analyzer
Spec: .github/agents/requirements-analyzer.agent.md
Context: projectName=${projectName}, basePath=${basePath}
Input: ${basePath}/requirements.md
Output: ${basePath}/analysis/requirements-analysis.md
Expected: Write structured analysis with sections for features, constraints, and risks

Return: Summary of key features and any ambiguities found
```

### Multi-Step Sequential Workflow

For workflows with dependencies, run steps sequentially:

```text
Step 1: Transform raw input data
Agent: data-processor
Spec: .github/agents/data-processor.agent.md
Context: projectName=${projectName}, basePath=${basePath}
Input: ${basePath}/raw/
Output: ${basePath}/processed/
Expected: Write ${basePath}/processed/summary.md

Step 2: Analyze processed data (depends on Step 1 output)
Agent: data-analyst
Spec: .github/agents/data-analyst.agent.md
Context: projectName=${projectName}, basePath=${basePath}
Input: ${basePath}/processed/
Output: ${basePath}/analysis/
Expected: Write ${basePath}/analysis/report.md

Step 3: Generate visualizations (depends on Step 2 output)
Agent: data-visualizer
Spec: .github/agents/data-visualizer.agent.md
Context: projectName=${projectName}, basePath=${basePath}
Input: ${basePath}/analysis/report.md
Output: ${basePath}/visualizations/
Expected: Create charts and graphs in ${basePath}/visualizations/
```

## Common Orchestration Patterns

### Planning → Implementation

**Use case:** Separate planning from execution

```text
Step 1: Planning Phase
Agent: project-planner
Spec: .github/agents/planner.agent.md
Context: projectName=${projectName}, basePath=${basePath}
Expected: Create ${basePath}/plan.md with architecture and task breakdown

Step 2: Implementation Phase
Agent: project-implementer
Spec: .github/agents/implementer.agent.md
Context: projectName=${projectName}, basePath=${basePath}, planFile=${basePath}/plan.md
Expected: Implement project according to plan.md
```

### Implementation → Review

**Use case:** Build first, then validate quality

```text
Step 1: Implementation
Agent: feature-implementer
Spec: .github/agents/implementer.agent.md
Context: feature=${featureName}, basePath=${basePath}
Expected: Implement feature in ${basePath}/src/

Step 2: Code Review
Agent: code-reviewer
Spec: .github/agents/reviewer.agent.md
Context: feature=${featureName}, basePath=${basePath}
Expected: Review implementation and create ${basePath}/review-report.md
```

### Test-Driven Development (TDD)

**Use case:** Write failing tests, then implement passing code

```text
Step 1: Generate Failing Tests
Agent: test-generator
Spec: .github/agents/test-generator.agent.md
Context: feature=${featureName}, basePath=${basePath}
Expected: Create tests in ${basePath}/tests/ that fail initially

Step 2: Implement Feature
Agent: feature-implementer
Spec: .github/agents/implementer.agent.md
Context: feature=${featureName}, basePath=${basePath}, testDir=${basePath}/tests/
Expected: Implement code in ${basePath}/src/ to make tests pass

Step 3: Verify Tests Pass
Agent: test-runner
Spec: .github/agents/test-runner.agent.md
Context: basePath=${basePath}
Expected: Run tests and confirm all pass
```

### Research → Documentation

**Use case:** Research a topic, then produce documentation

```text
Step 1: Research
Agent: research-agent
Spec: .github/agents/researcher.agent.md
Context: topic=${topic}, basePath=${basePath}
Expected: Create ${basePath}/research-notes.md with findings

Step 2: Documentation
Agent: documentation-agent
Spec: .github/agents/documenter.agent.md
Context: topic=${topic}, basePath=${basePath}, researchFile=${basePath}/research-notes.md
Expected: Create ${basePath}/docs/${topic}.md with polished documentation
```

### Multi-Agent Review Process

**Use case:** Multiple specialized reviewers

```text
Step 1: Security Review
Agent: security-reviewer
Spec: .github/agents/security-reviewer.agent.md
Context: basePath=${basePath}
Expected: Create ${basePath}/reviews/security-review.md

Step 2: Performance Review
Agent: performance-reviewer
Spec: .github/agents/performance-reviewer.agent.md
Context: basePath=${basePath}
Expected: Create ${basePath}/reviews/performance-review.md

Step 3: Accessibility Review
Agent: accessibility-reviewer
Spec: .github/agents/accessibility-reviewer.agent.md
Context: basePath=${basePath}
Expected: Create ${basePath}/reviews/accessibility-review.md

Step 4: Consolidate Reviews
Agent: review-consolidator
Spec: .github/agents/consolidator.agent.md
Context: basePath=${basePath}
Expected: Create ${basePath}/reviews/final-report.md
```

## Advanced Patterns

### Conditional Steps

Include trigger conditions to skip steps when not needed:

```text
Step 1: Check for existing tests
Agent: test-checker
Spec: .github/agents/test-checker.agent.md
Context: basePath=${basePath}
Expected: Return test coverage percentage

Step 2: Generate tests (ONLY if coverage < 80%)
Agent: test-generator
Spec: .github/agents/test-generator.agent.md
Context: basePath=${basePath}
Expected: Create tests to reach 80% coverage
Trigger: Run only if Step 1 reports coverage < 80%
```

### Error Handling and Retries

Check results before proceeding to dependent steps:

```text
Step 1: Validate input data
Agent: data-validator
Spec: .github/agents/validator.agent.md
Context: basePath=${basePath}
Expected: Return validation status (pass/fail)

If Step 1 fails:
  - Report validation errors to user
  - Do not proceed to Step 2

Step 2: Process validated data (depends on Step 1 success)
Agent: data-processor
Spec: .github/agents/processor.agent.md
Context: basePath=${basePath}
Expected: Process data from ${basePath}/input/
```

### Logging and Progress Tracking

Maintain a single log file updated after each step:

```text
Log File: ${basePath}/orchestration-log.md

Step 1: Initialize project
Agent: project-initializer
Spec: .github/agents/initializer.agent.md
Context: projectName=${projectName}, basePath=${basePath}, logFile=${basePath}/orchestration-log.md
Expected: Create project structure and append to log

Step 2: Generate boilerplate
Agent: boilerplate-generator
Spec: .github/agents/boilerplate.agent.md
Context: projectName=${projectName}, basePath=${basePath}, logFile=${basePath}/orchestration-log.md
Expected: Generate files and append to log

Step 3: Finalize setup
Agent: setup-finalizer
Spec: .github/agents/finalizer.agent.md
Context: projectName=${projectName}, basePath=${basePath}, logFile=${basePath}/orchestration-log.md
Expected: Complete setup and append final status to log
```

## Best Practices

### ✅ Do

- **Use clear step names**: "Step 1: Validate requirements" not "Step 1"
- **Pass minimal context**: Only what the sub-agent needs
- **Require summaries**: Each sub-agent should report what it accomplished
- **Validate results**: Check outputs before proceeding to dependent steps
- **Use explicit paths**: `${basePath}/output/file.md` not "output file"
- **Document dependencies**: Make it clear when Step N depends on Step M
- **Keep orchestrators generic**: Extract dynamic values from user input
- **Limit scope**: 5-10 steps maximum for maintainability

### ❌ Don't

- **Over-orchestrate**: Don't use sub-agents for simple tasks
- **Create circular handoffs**: Ensure workflows have clear exit conditions
- **Skip error handling**: Always validate step results
- **Hard-code values**: Use variables like `${projectName}` instead
- **Duplicate work**: Sub-agents should have clear, non-overlapping responsibilities
- **Process large datasets**: Sub-agent orchestration is not for bulk operations
- **Nest too deeply**: Avoid sub-agents invoking sub-agents (1 level max)

## Limitations and Warnings

### ⚠️ Not Suitable for Large-Scale Processing

**Sub-agent orchestration is NOT appropriate for:**
- Processing hundreds or thousands of files
- Handling large datasets (> 100MB)
- Bulk transformations on big codebases
- Orchestrating more than 10 sequential steps
- High-frequency operations (e.g., processing events)

**Why:** Each sub-agent invocation adds latency and context overhead. For high-volume processing, implement logic directly in a single agent.

### ⚠️ Complexity Overhead

Orchestration adds complexity:
- More agents to maintain
- More places for errors to occur
- More difficult to debug
- Longer execution time

**Use orchestration only when the benefits (specialization, quality gates, reusability) outweigh the costs.**

### ⚠️ Tool Inheritance

Sub-agents are limited by the orchestrator's tools. If the orchestrator has `tools: ['read', 'search', 'agent']`, sub-agents cannot use `edit` or `execute` even if their specs request them.

## Debugging Orchestration

### Common Issues

**Sub-agent not invoked:**
- `agent` tool not in orchestrator's tools list
- Agent name or spec path incorrect
- Sub-agent spec file not found

**Sub-agent lacks tools:**
- Orchestrator missing required tools
- Sub-agent spec requests tools unavailable to orchestrator

**Step failures:**
- Previous step didn't produce expected output
- File paths incorrect or not properly substituted
- Sub-agent encountered errors (check logs)

### Debugging Checklist

1. **Verify orchestrator tools:** Ensure `'agent'` and all sub-agent tools included
2. **Check agent specs:** Confirm sub-agent `.agent.md` files exist and are valid
3. **Validate paths:** Ensure all file paths use correct variables and exist
4. **Review step order:** Confirm dependencies are satisfied sequentially
5. **Check logs:** Look for sub-agent error messages
6. **Test sub-agents independently:** Invoke each sub-agent manually to verify it works

## Example: Complete Project Setup Orchestrator

```yaml
---
description: "Orchestrates multi-phase new project setup with planning, scaffolding, and validation"
name: "Project Setup Orchestrator"
tools: ['read', 'edit', 'search', 'execute', 'agent']
---

# Project Setup Orchestrator

You are a project setup orchestrator that coordinates specialized agents to create well-structured projects.

## Dynamic Parameters

Extract these values from user input:
- `projectName`: Name of the project to create
- `projectType`: Type of project (e.g., "web-app", "library", "cli-tool")
- `basePath`: Root directory for the project (default: `./${projectName}`)

## Workflow

### Step 1: Planning Phase

This phase must be performed as the agent "project-planner" defined in ".github/agents/project-planner.agent.md".

IMPORTANT:
- Read and apply the entire .agent.md spec (tools, constraints, quality standards).
- Work on "${projectName}" with base path: "${basePath}".
- Create a comprehensive project plan in ${basePath}/PROJECT_PLAN.md
- Return a clear summary (features identified + project structure + next steps).

Context:
{
  "step": "1-planning",
  "agent": "project-planner",
  "spec": ".github/agents/project-planner.agent.md",
  "projectName": "${projectName}",
  "projectType": "${projectType}",
  "basePath": "${basePath}",
  "outputs": ["${basePath}/PROJECT_PLAN.md"]
}

### Step 2: Scaffolding Phase (depends on Step 1)

This phase must be performed as the agent "project-scaffolder" defined in ".github/agents/project-scaffolder.agent.md".

IMPORTANT:
- Read and apply the entire .agent.md spec (tools, constraints, quality standards).
- Read the plan from ${basePath}/PROJECT_PLAN.md
- Create project structure according to the plan
- Return a clear summary (files created + directories created + issues).

Context:
{
  "step": "2-scaffolding",
  "agent": "project-scaffolder",
  "spec": ".github/agents/project-scaffolder.agent.md",
  "projectName": "${projectName}",
  "basePath": "${basePath}",
  "inputs": ["${basePath}/PROJECT_PLAN.md"],
  "outputs": ["${basePath}/src/", "${basePath}/tests/", "${basePath}/README.md"]
}

### Step 3: Validation Phase (depends on Step 2)

This phase must be performed as the agent "project-validator" defined in ".github/agents/project-validator.agent.md".

IMPORTANT:
- Read and apply the entire .agent.md spec (tools, constraints, quality standards).
- Validate all generated files against the plan
- Run any available build/test commands to verify setup
- Create validation report in ${basePath}/VALIDATION.md
- Return a clear summary (validation status + issues found + recommendations).

Context:
{
  "step": "3-validation",
  "agent": "project-validator",
  "spec": ".github/agents/project-validator.agent.md",
  "projectName": "${projectName}",
  "basePath": "${basePath}",
  "inputs": ["${basePath}/PROJECT_PLAN.md", "${basePath}/src/", "${basePath}/tests/"],
  "outputs": ["${basePath}/VALIDATION.md"]
}

## Final Report

After all steps complete:
1. Summarize what was created
2. Report any issues or warnings from validation
3. Provide next steps for the user
```

## Further Reading

- [Tool Configuration Reference](./TOOLS.md) - Details on the `agent` tool and others
- [Agent Frontmatter Reference](./FRONTMATTER.md) - Configuring orchestrator frontmatter
- [Common Agent Patterns](./COMMON_PATTERNS.md) - Real-world agent examples
- [Handoff Configuration](./HANDOFF.md) - Alternative to sub-agent orchestration
