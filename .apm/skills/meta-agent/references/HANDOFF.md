# Agent Handoff Configuration Guide

## Overview

Handoffs enable you to create guided sequential workflows that transition seamlessly between custom agents. This is a VS Code-specific mechanism: a handoff is a suggested, user-approved transition with a pre-filled prompt — the user clicks a button, reviews (and can edit) the prompt, and decides whether to send it. It is not silent auto-delegation to another agent. This is useful for orchestrating multi-step development workflows where users can review and approve each step before moving to the next one.

**Handoff vs. agent-as-tool:** use a handoff when a specialist should take over the conversation and own the final response. When an orchestrator must synthesize results from specialists instead, use sub-agent orchestration (agent-as-tool) — see [SUBAGENT.md](./SUBAGENT.md).

## Common Handoff Patterns

- **Planning → Implementation**: Generate a plan in a planning agent, then hand off to an implementation agent to start coding
- **Implementation → Review**: Complete implementation, then switch to a code review agent to check for quality and security issues
- **Write Failing Tests → Write Passing Tests**: Generate failing tests, then hand off to implement the code that makes those tests pass
- **Research → Documentation**: Research a topic, then transition to a documentation agent to write guides
- **Design → Prototype → Production**: Multi-stage development with quality gates at each transition

## Frontmatter Structure

Define handoffs in the agent file's YAML frontmatter using the `handoffs` field:

```yaml
---
description: 'Brief description of the agent'
name: 'Agent Name'
tools: ['search', 'read']
handoffs:
  - label: Start Implementation
    agent: implementation
    prompt: 'Now implement the plan outlined above.'
    send: false
  - label: Code Review
    agent: code-review
    prompt: 'Please review the implementation for quality and security issues.'
    send: false
---
```

## Handoff Properties

Each handoff in the list must include the following properties:

| Property | Type    | Required | Description                                                                        |
| -------- | ------- | -------- | ---------------------------------------------------------------------------------- |
| `label`  | string  | Yes      | The display text shown on the handoff button in the chat interface                 |
| `agent`  | string  | Yes      | The target agent identifier to switch to (name or filename without `.agent.md`)    |
| `prompt` | string  | No       | The prompt text to pre-fill in the target agent's chat input                       |
| `send`   | boolean | No       | If `true`, automatically submits the prompt to the target agent (default: `false`) |

## Handoff Behavior

- **Button Display**: Handoff buttons appear as interactive suggestions after a chat response completes
- **Context Preservation**: When users select a handoff button, they switch to the target agent with conversation context maintained
- **Pre-filled Prompt**: If a `prompt` is specified, it appears pre-filled in the target agent's chat input
- **Manual vs Auto**: When `send: false`, users must review and manually send the pre-filled prompt; when `send: true`, the prompt is automatically submitted

## When to Use Handoffs

- **Multi-step workflows**: Breaking down complex tasks across specialized agents
- **Quality gates**: Ensuring review steps between implementation phases
- **Guided processes**: Directing users through a structured development process
- **Skill transitions**: Moving from planning/design to implementation/testing specialists
- **Approval workflows**: Requiring user review before proceeding to next stage

## Best Practices

### Clear Labels

Use action-oriented labels that clearly indicate the next step.

✅ **GOOD**:

- "Start Implementation"
- "Review for Security"
- "Write Tests"
- "Document Changes"

❌ **BAD**:

- "Next"
- "Go to agent"
- "Do something"
- "Continue"

### Relevant Prompts

Provide context-aware prompts that reference the completed work.

✅ **GOOD**:

```yaml
prompt: 'Now implement the plan outlined above.'
prompt: 'Review this implementation for security vulnerabilities and code quality issues.'
prompt: 'Write unit tests for the components created in this session.'
```

❌ **BAD**:

```yaml
prompt: 'Do your thing.'
prompt: 'Start working.'
prompt: 'Review code.'
```

### Selective Use

Don't create handoffs to every possible agent; focus on logical workflow transitions.

**Guidelines**:

- Limit to 2-3 most relevant next steps per agent
- Only add handoffs for agents that naturally follow in the workflow
- Avoid circular handoffs without clear exit conditions
- Don't handoff to agents unrelated to current work

### Agent Dependencies

Ensure target agents exist before creating handoffs.

**Checklist**:

- [ ] Target agent file exists and is properly configured
- [ ] Target agent has appropriate tools for its role
- [ ] Target agent can access necessary context
- [ ] Handoff chain has logical termination points

**Note**: Handoffs to non-existent agents will be silently ignored.

### Prompt Content

Keep prompts concise and actionable.

**Guidelines**:

- Refer to work from the current agent without duplicating content
- Provide any necessary context the target agent might need
- Use specific terminology consistent with target agent's domain
- Keep prompts under 200 characters when possible

## Complete Workflow Example

Here's an example of three agents with handoffs creating a complete workflow:

### Planning Agent (`planner.agent.md`)

```yaml
---
description: 'Generate an implementation plan for new features or refactoring'
name: 'Planner'
tools: ['search', 'read']
handoffs:
  - label: Implement Plan
    agent: implementer
    prompt: 'Implement the plan outlined above.'
    send: false
---
# Planner Agent

You are a planning specialist. Your task is to:
1. Analyze the requirements
2. Break down the work into logical steps
3. Generate a detailed implementation plan
4. Identify testing requirements

Do not write any code - focus only on planning.
```

### Implementation Agent (`implementer.agent.md`)

```yaml
---
description: 'Implement code based on a plan or specification'
name: 'Implementer'
tools: ['read', 'edit', 'search', 'execute']
handoffs:
  - label: Review Implementation
    agent: reviewer
    prompt: 'Please review this implementation for code quality, security, and adherence to best practices.'
    send: false
---
# Implementer Agent

You are an implementation specialist. Your task is to:
1. Follow the provided plan or specification
2. Write clean, maintainable code
3. Include appropriate comments and documentation
4. Follow project coding standards

Implement the solution completely and thoroughly.
```

### Review Agent (`reviewer.agent.md`)

```yaml
---
description: 'Review code for quality, security, and best practices'
name: 'Reviewer'
tools: ['read', 'search']
handoffs:
  - label: Back to Planning
    agent: planner
    prompt: 'Review the feedback above and determine if a new plan is needed.'
    send: false
  - label: Iterate on Implementation
    agent: implementer
    prompt: 'Address the review feedback outlined above.'
    send: false
---
# Code Review Agent

You are a code review specialist. Your task is to:
1. Check code quality and maintainability
2. Identify security issues and vulnerabilities
3. Verify adherence to project standards
4. Suggest improvements

Provide constructive feedback on the implementation.
```

### Workflow Execution

This workflow enables:

1. **Planning Phase**: Start with the Planner agent to create a detailed plan
2. **Implementation Phase**: Hand off to the Implementer agent to write code based on the plan
3. **Review Phase**: Hand off to the Reviewer agent to check the implementation
4. **Iteration Options**:

   - Return to planning if significant architectural changes are needed
   - Return to implementation to address specific feedback
   - Complete workflow if review passes

## Advanced Patterns

### Conditional Handoffs

You can create multiple handoff options that users select based on the outcome:

```yaml
handoffs:
  - label: If Approved - Deploy
    agent: deployer
    prompt: 'Deploy the approved implementation.'
  - label: If Issues Found - Revise
    agent: implementer
    prompt: 'Address the issues found in review: ${reviewFeedback}'
  - label: Major Issues - Replan
    agent: planner
    prompt: 'Significant issues require replanning: ${reviewFeedback}'
```

### Parallel Workflows

Create handoffs that enable users to branch into different workflows:

```yaml
handoffs:
  - label: Write Unit Tests
    agent: test-writer
    prompt: 'Create unit tests for the implemented features.'
  - label: Write Documentation
    agent: documenter
    prompt: 'Document the API and usage examples.'
  - label: Create Integration Tests
    agent: integration-tester
    prompt: 'Design integration test scenarios.'
```

### Auto-send for Linear Workflows

Use `send: true` for strict linear workflows where no user review is needed:

```yaml
handoffs:
  - label: Auto-format Code
    agent: formatter
    prompt: 'Format the code according to project standards.'
    send: true
```

**Use sparingly**: Auto-send removes user control and should only be used for non-destructive, deterministic operations.

## Troubleshooting

### Handoff Button Not Appearing

**Possible causes**:

- Target agent doesn't exist
- YAML syntax error in handoffs configuration
- Agent name doesn't match the target agent's name or filename

**Solution**: Verify target agent exists and handoff configuration is valid YAML.

### Context Not Preserved

**Possible causes**:

- Chat history cleared between handoffs
- Session expired

**Solution**: Handoffs preserve context automatically; if lost, it's a platform issue, not configuration.

### Prompt Not Pre-filled

**Possible causes**:

- `prompt` field is empty or missing
- Special characters not properly escaped

**Solution**: Ensure `prompt` field contains valid YAML string, use quotes for special characters.

### Wrong Agent Activated

**Possible causes**:

- `agent` field contains incorrect value
- Multiple agents with similar names

**Solution**: Use exact agent name or filename (without `.agent.md` extension).

## References

- [Creating Custom Agents](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/create-custom-agents)
- [Custom Agents Configuration](https://docs.github.com/en/copilot/reference/custom-agents-configuration)
