---
name: "Self-Improvement Instructions"
description: "Instructions for how to improve yourself and learn from past conversations"
applyTo: ""
source: ""
license: ""
---

# Self-Improvement Guidelines

## Capabilities

You have multiple different mechanisms to improve and learn. Currently we support agents, skills, instructions and prompts as the types of files that can convey rules and guidelines in future conversations.

### Types of Files

- **Agents**: Autonomous systems that execute tasks independently. Use when you need a complete workflow that makes decisions and takes actions without user intervention.
- **Skills**: Reusable, composable capabilities that perform specific tasks. Use for discrete, well-defined functionalities that can be combined together.
- **Instructions**: Guidelines and rules that shape behavior and decision-making. Use for behavioral patterns, best practices, and procedural guidelines.
- **Prompts**: Structured inputs that guide specific model interactions. Use for templated requests, few-shot examples, and conversation starters.

Utilise the provided skills to assist you in the design and implementation of these files. You can also update existing files with new rules and guidelines.

## Writing Effective Guidelines

When adding new files or adapting pre-existing files with new rules, follow these principles:

**Core Principles (Always Apply):**

1. Be explicit about what files to update or add. Consider what type of input would have been most helpful.
2. Use absolute directives. Don't use words like "should" or "would".
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