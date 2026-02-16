---
name: "Self-Improvement Instructions"
description: "Instructions for how to improve yourself and learn from past conversations"
applyTo: "**/*.agent.md, **/*.SKILL.md, **/*.prompt.md, **/*.instructions.md"
source: ""
license: ""
---

# Self-Improvement Guidelines

## Capabilities

You have multiple mechanisms to improve and learn. We support agents, skills, instructions and prompts as the types of files that can store rules and guidelines and steer future conversations. Collectively we call them "customization" files.

**Customization Types:**

- **Agents**: Autonomous systems that execute tasks independently. Use when you need a complete workflow that makes decisions and takes actions without user intervention.
- **Skills**: Reusable, composable capabilities that perform specific tasks. Always prefer creating a skill over an instruction if the capability involves specific knowledge or tasks.
- **Instructions**: Guidelines and rules that shape behavior and decision-making. **Only use instructions to force VS Code to load specific skills** or for strictly behavioral patterns that cannot be encapsulated in a skill.
- **Prompts**: Structured inputs that guide specific model interactions. Use for templated requests, few-shot examples, and conversation starters.

## Workflow

- Utilise `#tool:runSubagent` to add or update any customization files, loading the provided skills to assist you in the design and implementation of these files.
- Run multiple subagents in parallel if the learnings can be clearly separated from eachother.

## Writing Effective Guidelines

When adding new or adapting pre-existing agent customization files, follow these principles:

**Core Principles (Always Apply):**

1. **Prefer Skills over Instructions**: Skills are modular and more powerful. Only use instructions for setting context or loading skills via `applyTo`.
2. Be explicit about what files to update or add. Consider what type of input would have been most helpful.
3. Use absolute directives. Don't use words like "should" or "would".
3. Bullets over paragraphs. Keep explanations concise.
4. Do NOT just suggest what could have been done differently this time! Generalise and adapt any pre-existing provided inputs.

**Optional Enhancements (Use Strategically):**

- ❌/✅ examples: Only when the antipattern is subtle
- "Warning Signs" section: Only for gradual mistakes
- "General Principle": Only when abstraction is non-obvious
- Add code examples where it make sense

**Anti-Bloat Rules:**

- ❌ Don't add "Warning Signs" to obvious rules
- ❌ Don't show bad examples for trivial mistakes
- ❌ Don't write paragraphs explaining what bullets can convey