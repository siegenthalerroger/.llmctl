---
name: "meta-agent"
description: "Guidelines for creating high-quality custom agents (aka modes or subagents). Use when asked to create, review, or improve AI agent personas, design agent workflows, configure handoffs between agents, or apply prompt engineering best practices to agent definitions. Keywords: agent, mode, subagent, persona, handoff, workflow, prompt engineering."
license: "MIT"
metadata:
  adaptedFrom: "https://github.com/github/awesome-copilot/blob/main/instructions/agents.instructions.md"
---

# Custom Agent File Guidelines

Instructions for creating effective and maintainable custom agent files that provide specialized expertise for specific development tasks in GitHub Copilot.

## What is a Custom Agent?

Custom agents are specialized AI personas with defined expertise, tools, and behavioral patterns. They enable:

- **Task specialization**: Focus on specific domains (testing, security, refactoring)
- **Workflow orchestration**: Chain agents with handoffs for multi-step processes
- **Scoped permissions**: Limit tools and actions to match responsibilities
- **Consistent behavior**: Define reliable patterns for recurring tasks

Agents work best when they have clear boundaries, explicit responsibilities, and targeted tool access.

See [common examples](./references/COMMON_PATTERNS.md) for typical agent patterns.

## *.agent.md File Structure

### Required Frontmatter
Every agent file must include YAML frontmatter with the following fields:

```yaml
---
description: "Brief description of the agent purpose and capabilities"
name: "Agent Display Name"
tools: ['read', 'edit', 'search']
---
```

#### Frontmatter Properties

> [!NOTE]
>
> TODO: define minimal fields here and add a reference FRONTMATTER.md file with a description of all of the available fields.

## Agent Behavior Definition

### Agent Prompt Structure

The markdown content below the frontmatter defines the agent's behavior, expertise, and instructions. Well-structured prompts typically include:

1. **Agent Identity and Role**: Who the agent is and its primary role
2. **Core Responsibilities**: What specific tasks the agent performs
3. **Approach and Methodology**: How the agent works to accomplish tasks
4. **Guidelines and Constraints**: What to do/avoid and quality standards
5. **Output Expectations**: Expected output format and quality

#### Prompt Writing Best Practices

**Core Techniques** (ranked by effectiveness):

1. **Be Clear and Direct**: Use imperative mood ("Analyze", "Generate", "List"); avoid vague terms like "should" or "try"
2. **Use Examples (Few-Shot)**: Include 3-5 diverse examples showing both typical and edge cases
3. **Chain of Thought**: Add "Think step by step" or "Explain your reasoning" for complex tasks
4. **Use Structured Delimiters**: Markdown headers for sections, XML tags for boundaries (`<context>...</context>`)
5. **Define Role via Identity**: Specify expertise, communication style, and persona
6. **Include Relevant Context**: Reference frameworks, APIs, or documentation when needed

**Authority Hierarchy** (OpenAI Model Spec):
- Developer messages (system/agent definition) = highest authority
- User messages (task inputs) = lower authority
- Assistant messages = model responses

Define agent behavior as "developer" rules that take precedence over user requests.

**Structure Your Prompts**:
- **Identity**: Who the agent is and their expertise
- **Instructions**: What to do and how to do it
- **Examples**: Concrete demonstrations (optional but highly effective)
- **Constraints**: What to avoid and quality standards
- **Output Format**: Expected structure and style

**Writing Style**:
- Use imperative mood consistently
- One instruction = one clear statement
- Bullets over paragraphs
- Show code examples when applicable
- Third person for descriptions ("Analyzes code", not "I analyze code")

## Model-Specific Guidance

Different AI models respond better to different prompting styles:

**GPT-5 Models** (OpenAI):
- Need **explicit, detailed instructions**
- Think of as "junior coworker" - spell everything out
- Best with step-by-step workflows
- Provide concrete examples of expected behavior

**Reasoning Models** (o1, o4):
- Need **high-level goals only**
- Think of as "senior coworker" - trust them with details
- Avoid over-specifying steps (they reason internally)
- Focus on objectives and constraints, not procedure

**Claude 4.x Models** (Anthropic):
- Excel at **extended thinking and creative tasks**
- Use `<thinking>` tags for complex reasoning
- Prefer markdown structure over XML for long-form content
- Strong at following nuanced instructions with less hand-holding

Tailor agent complexity to the target model family.

## Good vs Bad Examples

### Agent Descriptions (Frontmatter)

✅ **GOOD** - Specific, keyword-rich, clear use cases:
```yaml
description: "Security auditor that scans code for vulnerabilities using OWASP guidelines. Use when reviewing authentication, authorization, input validation, or before deployments. Keywords: security, vulnerability, OWASP, SQL injection, XSS."
```

❌ **BAD** - Vague, no keywords:
```yaml
description: "A helpful agent that reviews code."
```

### Agent Identity and Instructions

✅ **GOOD** - Clear role, specific responsibilities:
```markdown
# Test Automation Specialist

You are a test automation expert focusing on comprehensive test coverage and quality assurance.

## Core Responsibilities
- Analyze codebases to identify untested paths
- Generate unit, integration, and E2E tests
- Follow project testing conventions (Jest, Pytest, etc.)
- Ensure tests are maintainable and well-documented

## Approach
1. Review existing test coverage
2. Identify critical paths and edge cases
3. Write tests that validate behavior, not implementation
4. Avoid modifying production code unless necessary

## Constraints
- Never skip test setup or teardown
- Always mock external dependencies
- Write self-documenting test names
```

❌ **BAD** - Generic, no structure:
```markdown
You are a helpful agent that writes tests when asked. Try to write good tests that cover the code.
```

### Tool Configuration

✅ **GOOD** - Tools match responsibilities:
```yaml
# Code reviewer - read-only
tools: ['read', 'search']

# Refactoring specialist - code modification
tools: ['read', 'search', 'edit']

# Full implementation agent - all tools
tools: ['read', 'search', 'edit', 'execute', 'web']
```

❌ **BAD** - All tools for every agent:
```yaml
# Every agent gets everything
tools: ['read', 'search', 'edit', 'execute', 'web', 'debug']
```

## Testing and Iteration

**Essential Practices**:
- **Build evaluations first**: Define success criteria before optimizing prompts
- **Iterate systematically**: Change one variable at a time
- **Test edge cases**: Go beyond happy paths in examples
- **Pin model versions**: Avoid surprise breakage from model updates in production
- **Monitor performance**: Track effectiveness across model updates

**Common Issues**:
- Too many options without clear defaults → Add recommended path with escape hatch
- Vague instructions → Add concrete examples and explicit steps
- Overly complex workflows → Split into multiple agents with handoffs
- Inconsistent behavior → Review authority hierarchy and clarify constraints

### Handoffs Configuration

Handoffs enable guided multi-step workflows between specialized agents.

**Common Handoff Patterns:**
- **Planning -> Implementation**: Plan in one agent, implement in another
- **Implementation -> Review**: Build first, then validate quality and security
- **Write Failing Tests -> Write Passing Tests**: Tests first, implementation second
- **Research -> Documentation**: Research, then produce docs

See the complete configuration guide in [references/HANDOFF.md](./references/HANDOFF.md). It contains:
- Frontmatter structure and required properties
- Behavior details and best practices
- Full workflow examples and advanced patterns
- Troubleshooting guidance

### Tool Configuration

> [!NOTE]
>
> TODO: write an explanation and move details to a TOOLS.md reference file

#### Tool Specification Strategies

**Enable all tools** (default):

```yaml
# Omit tools property entirely, or use:
tools: ['*']
```

**Enable specific tools**:

```yaml
tools: ['read', 'edit', 'search', 'execute']
```

**Enable MCP server tools**:

```yaml
tools: ['read', 'edit', 'github/*', 'playwright/navigate']
```

**Disable all tools**:

```yaml
tools: []
```

#### Tool Selection Best Practices

- **Principle of Least Privilege**: Only enable tools necessary for the agent's purpose
- **Security**: Limit `execute` access unless explicitly required
- **Focus**: Fewer tools = clearer agent purpose and better performance
- **Documentation**: Comment why specific tools are required for complex configurations

### Sub-Agent Invocation (Agent Orchestration)

Agents can invoke other agents using the **agent invocation tool** (the `agent/runSubagent` tool) to orchestrate multi-step workflows.

The recommended approach is **prompt-based orchestration**:

- The orchestrator defines a step-by-step workflow in natural language.
- Each step is delegated to a specialized agent.
- The orchestrator passes only the essential context (e.g., base path, identifiers) and requires each sub-agent to read its own `.agent.md` spec for tools/constraints.

> [!NOTE]
>
> TODO: move details to a SUBAGENT.md reference file

#### How It Works

1) Enable agent invocation by including `agent` in the orchestrator's tools list:

```yaml
tools: ['read', 'edit', 'search', 'agent']
```

2) For each step, invoke a sub-agent by providing:

- **Agent name** (the identifier users select/invoke)
- **Agent spec path** (the `.agent.md` file to read and follow)
- **Minimal shared context** (e.g., `basePath`, `projectName`, `logFile`)

#### Prompt Pattern (Recommended)

Use a consistent “wrapper prompt” for every step so sub-agents behave predictably:

```text
This phase must be performed as the agent "<AGENT_NAME>" defined in "<AGENT_SPEC_PATH>".

IMPORTANT:
- Read and apply the entire .agent.md spec (tools, constraints, quality standards).
- Work on "<WORK_UNIT_NAME>" with base path: "<BASE_PATH>".
- Perform the necessary reads/writes under this base path.
- Return a clear summary (actions taken + files produced/modified + issues).
```

Optional: if you need a lightweight, structured wrapper for traceability, embed a small JSON block in the prompt (still human-readable and tool-agnostic):

```text
{
  "step": "<STEP_ID>",
  "agent": "<AGENT_NAME>",
  "spec": "<AGENT_SPEC_PATH>",
  "basePath": "<BASE_PATH>"
}
```

#### Orchestrator Structure (Keep It Generic)

For maintainable orchestrators, document these structural elements:

- **Dynamic parameters**: what values are extracted from the user (e.g., `projectName`, `fileName`, `basePath`).
- **Sub-agent registry**: a list/table mapping each step to `agentName` + `agentSpecPath`.
- **Step ordering**: explicit sequence (Step 1 → Step N).
- **Trigger conditions** (optional but recommended): define when a step runs vs is skipped.
- **Logging strategy** (optional but recommended): a single log/report file updated after each step.

Avoid embedding orchestration “code” (JavaScript, Python, etc.) inside the orchestrator prompt; prefer deterministic, tool-driven coordination.

#### Basic Pattern

Structure each step invocation with:

1. **Step description**: Clear one-line purpose (used for logs and traceability)
2. **Agent identity**: `agentName` + `agentSpecPath`
3. **Context**: A small, explicit set of variables (paths, IDs, environment name)
4. **Expected outputs**: Files to create/update and where they should be written
5. **Return summary**: Ask the sub-agent to return a short, structured summary

#### Example: Multi-Step Processing

```text
Step 1: Transform raw input data
Agent: data-processor
Spec: .github/agents/data-processor.agent.md
Context: projectName=${projectName}, basePath=${basePath}
Input: ${basePath}/raw/
Output: ${basePath}/processed/
Expected: write ${basePath}/processed/summary.md

Step 2: Analyze processed data (depends on Step 1 output)
Agent: data-analyst
Spec: .github/agents/data-analyst.agent.md
Context: projectName=${projectName}, basePath=${basePath}
Input: ${basePath}/processed/
Output: ${basePath}/analysis/
Expected: write ${basePath}/analysis/report.md
```

#### Key Points

- **Pass variables in prompts**: Use `${variableName}` for all dynamic values
- **Keep prompts focused**: Clear, specific tasks for each sub-agent
- **Return summaries**: Each sub-agent should report what it accomplished
- **Sequential execution**: Run steps in order when dependencies exist between outputs/inputs
- **Error handling**: Check results before proceeding to dependent steps

#### ⚠️ Tool Availability Requirement

**Critical**: If a sub-agent requires specific tools (e.g., `edit`, `execute`, `search`), the orchestrator must include those tools in its own `tools` list. Sub-agents cannot access tools that aren't available to their parent orchestrator.

**Example**:

```yaml
# If your sub-agents need to edit files, execute commands, or search code
tools: ['read', 'edit', 'search', 'execute', 'agent']
```

The orchestrator's tool permissions act as a ceiling for all invoked sub-agents. Plan your tool list carefully to ensure all sub-agents have the tools they need.

#### ⚠️ Important Limitation

**Sub-agent orchestration is NOT suitable for large-scale data processing.** Avoid using multi-step sub-agent pipelines when:

- Processing hundreds or thousands of files
- Handling large datasets
- Performing bulk transformations on big codebases
- Orchestrating more than 5-10 sequential steps

Each sub-agent invocation adds latency and context overhead. For high-volume processing, implement logic directly in a single agent instead. Use orchestration only for coordinating specialized tasks on focused, manageable datasets.


## Anti-Patterns to Avoid

❌ **Don't:**
- Create agents with vague descriptions like "helpful assistant" or "coding agent"
- Provide too many options without recommending a default path
- Use walls of text instead of structured bullets and headers
- Grant all tools to every agent (principle of least privilege)
- Write "when to use" sections in the agent body (put in description instead)
- Include time-sensitive instructions without escape hatches
- Over-specify steps for reasoning models (o1, o4) - they reason internally
- Under-specify for GPT-5 models - they need explicit guidance
- Create circular handoffs without exit conditions
- Write in second person ("you should") - use imperative mood ("Analyze", "Generate")
- Add XML tags or reserved words in descriptions (`anthropic`, `claude`, `openai`, `copilot`)

✅ **Do:**
- Write keyword-rich descriptions that enable discovery
- Provide concrete examples in the agent definition
- Match tool permissions to agent responsibilities
- Structure prompts with clear sections (Identity, Instructions, Examples, Constraints)
- Test agents with edge cases before deployment
- Use chain of thought for complex reasoning tasks
- Define clear boundaries and scope limits
- Create logical handoff workflows with quality gates

## Validation Checklist

### Frontmatter

- [ ] `description` field present and descriptive (50-150 chars)
- [ ] `name` specified
- [ ] `tools` configured appropriately (or intentionally omitted)
- [ ] `model` specified for optimal performance
- [ ] `target` set if environment-specific
- [ ] `infer` set to `false` if manual selection required

### Prompt Content

- [ ] Clear agent identity and role defined
- [ ] Core responsibilities listed explicitly
- [ ] Approach and methodology explained
- [ ] Guidelines and constraints specified
- [ ] Output expectations documented
- [ ] Examples provided where helpful
- [ ] Instructions are specific and actionable
- [ ] Scope and boundaries clearly defined
- [ ] Total content under 30,000 characters

### File Structure

- [ ] Filename follows lowercase-with-hyphens convention
- [ ] Filename uses only allowed characters
- [ ] File extension is `.agent.md`

### Quality Assurance

- [ ] Agent purpose is unique and not duplicative
- [ ] Tools are minimal and necessary
- [ ] Instructions are clear and unambiguous
- [ ] Agent has been tested with representative tasks
- [ ] Documentation references are current
- [ ] Security considerations addressed (if applicable)

## References

- [Creating Custom Agents](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/create-custom-agents)
- [Custom Agents Configuration](https://docs.github.com/en/copilot/reference/custom-agents-configuration)
- [Custom Agents in VS Code](https://code.visualstudio.com/docs/copilot/customization/custom-agents)
- [Awesome Copilot Agents Collection](https://github.com/github/awesome-copilot/tree/main/agents)
