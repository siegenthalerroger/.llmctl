---
name: "meta-instruction"
description: "Guidelines for creating high-quality instruction files that define coding standards, project conventions, and behavioral rules. Use when asked to create, review, or improve instruction files, define project rules, set coding standards, or configure AI assistant behavior patterns. Keywords: instructions, rules, conventions, standards, guidelines, applyTo, patterns."
license: ""
---

# Instruction Files Guidelines

Instructions for creating effective and maintainable instruction files that define coding standards, conventions, and behavioral rules for AI assistants.

> [!IMPORTANT] Relation to other customization files
>
> **Skills are always preferable to instructions.**
>
> Instructions should normally only be used to **force VS Code to load certain skills** (via `applyTo` rules) or for broad behavioral conventions.
>
> For templated tasks with inputs, use **prompts**. For complex workflows with specialized expertise, use **agents**.

## What Are Instruction Files?

Instruction files contain rules and guidelines that shape AI assistant behavior across your codebase. They capture:

- **Coding standards**: Style guides, naming conventions, patterns
- **Project conventions**: Architecture decisions, file organization, best practices
- **Behavioral rules**: How to approach tasks, what to avoid, quality standards
- **Domain knowledge**: Framework-specific patterns, library usage, business logic

Key characteristics:
- **Conditional application**: Use `applyTo` glob patterns to target specific files
- **Hierarchical specificity**: Personal > Repository > Organization
- **Non-obvious rules**: Focus on conventions linters don't catch
- **Include reasoning**: Explain WHY rules exist for better edge case handling

## When to Use Instructions vs Prompts vs Agents

| Type | Best For | Application Scope |
|------|----------|-------------------|
| **Skills** | Discrete capabilities, knowledge, tasks (ALWAYS PREFER OVER INSTRUCTIONS) | On-demand or forced via instructions |
| **Instructions** | Forcing VS Code to load skills, broad behavioral rules | Conditional (via `applyTo`) or always-on |
| **Prompts** | Quick templated tasks with variable inputs | One-time invocation |
| **Agents** | Complex workflows with specialized expertise | Session-based with specific role |

**Decision tree**:
- Need a reusable capability or knowledge? → **Skill**
- Need to automatically load a skill for certain files? → **Instruction** (with `applyTo`)
- One-off task with inputs? → **Prompt**
- Multi-step workflow with expertise? → **Agent**

## Loading Skills via Instructions

As per the core principle "Skills are always preferable to instructions", the most common pattern for instruction files should be to conditionally load skills based on file types.

**Why?**
Skills are modular, testable, and reusable. Instructions are broad and "always on" for the matched files. By using instructions primarily to load skills, you get the best of both worlds: automatic context loading (from instructions) with modular capability definitions (from skills).

**Example Pattern:**

\`\`\`markdown
---
name: "Load React Skills"
description: "Forces loading of React-specific skills for .tsx files"
applyTo: "**/*.tsx"
---

# React Development

When working with these files, ALWAYS use the following skills as your primary reference:
- [React Component Generator](../skills/react-gen/SKILL.md)
- [React Testing Library](../skills/react-test/SKILL.md)
\`\`\`

## File Structure and Naming

**Directory locations**:
```
.github/
  copilot-instructions.md     # Always-on repository instructions
  instructions/                # Conditional instruction files
    *.instructions.md

~/.llmctl/
  instructions/                # Personal instructions
    *.instructions.md
```

**Naming convention**:
- Use kebab-case with `.instructions.md` extension
- Descriptive names that indicate scope: `python-style.instructions.md`, `api-testing.instructions.md`
- Avoid generic names like `rules.instructions.md` or `guidelines.instructions.md`

## Frontmatter Requirements

Every instruction file must include YAML frontmatter with the following fields:

### Required Fields

```yaml
---
name: "Python Style Guide"
description: "Coding standards and style conventions for Python files"
applyTo: "**/*.py"
source: ""
license: ""
---
```

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Display name for the instruction set |
| `description` | Yes | Brief explanation of what rules are covered |
| `applyTo` | Yes | Glob pattern(s) determining when instructions apply |
| `source` | Optional | URL or reference to source material |
| `license` | Optional | License information for the instructions |

### applyTo Patterns

The `applyTo` field uses glob patterns to conditionally activate instructions:

**Examples**:
```yaml
# All Python files
applyTo: "**/*.py"

# Specific directory
applyTo: "src/components/**"

# Multiple patterns (JSON array)
applyTo: ["**/*.ts", "**/*.tsx"]

# All files (always active)
applyTo: "**"

# Specific file types in specific folders
applyTo: "tests/**/*.test.{js,ts}"
```

**Best practices**:
- Be as specific as possible to avoid unnecessary context loading
- Use `**` for recursive directory matching
- Use `{ext1,ext2}` for multiple extensions
- Test patterns match intended files

## Writing Effective Instructions

### Core Principles

1. **Be Specific and Actionable**: Write clear, direct rules that can be followed immediately
2. **Focus on Non-Obvious Rules**: Don't duplicate what linters/formatters already enforce
3. **Include Reasoning**: Explain WHY rules exist to help with edge cases
4. **Use Imperative Mood**: "Use", "Avoid", "Always", "Never" - not "should" or "would"
5. **Show, Don't Tell**: Provide concrete code examples over abstract descriptions
6. **Bullets Over Paragraphs**: Keep explanations concise and scannable

### Instruction Structure

Organize instructions into logical sections:

```markdown
# Category Name

## Naming Conventions
- Use PascalCase for class names
- Use camelCase for function names
- Use SCREAMING_SNAKE_CASE for constants

## File Organization
- One component per file
- Co-locate tests with source files
- Group by feature, not by type

## Error Handling
- Always validate user input before database queries (prevents SQL injection)
- Use specific exception types instead of generic Exception
- Log errors with contextual information
```

### Including Code Examples

✅ **GOOD** - Concrete examples with reasoning:
```markdown
## Database Queries

Use parameterized queries to prevent SQL injection:

✅ **GOOD**:
\`\`\`python
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
\`\`\`

❌ **BAD**:
\`\`\`python
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
\`\`\`

**Reasoning**: Parameterized queries prevent SQL injection by separating SQL code from data.
```

❌ **BAD** - Vague guidance without examples:
```markdown
Write secure database queries.
```

## Good vs Bad Examples

### Instruction Content

✅ **GOOD** - Specific, actionable, with reasoning:
```markdown
---
name: "React Component Standards"
description: "Component structure and prop handling conventions"
applyTo: "src/components/**/*.{tsx,jsx}"
---

# React Component Standards

## Component Structure
- Use functional components with hooks (class components are deprecated in our codebase)
- Define prop interfaces before the component declaration
- Export components as default, types as named exports

## Prop Handling
- Always destructure props in function signature for clarity
- Provide default values for optional props using parameter defaults
- Use TypeScript interfaces, not `type` keyword, for props (consistency with codebase)

## Example

\`\`\`tsx
interface UserCardProps {
  name: string;
  email?: string;
  onUpdate?: () => void;
}

export default function UserCard({
  name,
  email = 'no-email@example.com',
  onUpdate
}: UserCardProps) {
  return <div>...</div>;
}

export type { UserCardProps };
\`\`\`
```

❌ **BAD** - Generic, no examples, no reasoning:
```markdown
---
name: "Component Rules"
applyTo: "**"
---

Write good components. Follow best practices. Keep them clean.
```

### Specificity Hierarchy

✅ **GOOD** - Properly scoped with clear hierarchy:
```markdown
# Personal preference (override repository rules)
applyTo: "**/*.py"
# In ~/.llmctl/instructions/python-personal.instructions.md

# Repository standard (override organization rules)
applyTo: "src/**/*.py"
# In .github/instructions/python-style.instructions.md

# Organization baseline
applyTo: "**/*.py"
# In organization-level settings
```

❌ **BAD** - Conflicts without clear precedence:
```markdown
# Multiple conflicting rules at same level
applyTo: "**/*.py"
# Results in unpredictable behavior
```

## Model-Specific Considerations

Different models respond to instructions differently:

**All Models**:
- Clear, direct language works universally
- Concrete examples improve adherence
- Reasoning helps with edge cases

**GPT-5 Models**:
- Need very explicit rules
- Benefit from step-by-step guidance
- May need redundant examples

**Reasoning Models** (o1, o4):
- Understand nuanced rules better
- Can infer from principles
- Less need for exhaustive examples

**Claude 4.x**:
- Strong at context-aware rule application
- Excellent at understanding reasoning
- Good at balancing conflicting guidelines

## Anti-Patterns to Avoid

❌ **Don't:**
- Duplicate what linters/formatters already enforce (e.g., "Use 2 spaces for indentation")
- Write vague rules like "write clean code" or "follow best practices"
- Use `applyTo: "**"` for file-specific rules (too broad)
- Create walls of text without structure or examples
- Write in second person ("you should") - use imperative mood
- Include rules without explaining WHY they exist
- Make instructions too long (split into multiple files by topic)
- Create circular or conflicting rules
- Use time-sensitive information without clear expiration
- Add rules that are obvious or self-evident

✅ **Do:**
- Focus on non-obvious patterns and conventions
- Provide concrete, actionable guidance
- Use specific `applyTo` patterns for targeted rules
- Structure content with headers and bullets
- Use imperative mood: "Use", "Avoid", "Always"
- Explain reasoning behind each rule
- Keep files focused on single topic/domain
- Test rules don't conflict across hierarchy levels
- Update or mark deprecated rules clearly
- Show both good and bad examples

## Testing and Validation

**Before finalizing instructions**:

1. **Verify Pattern Matching**:
   - Test `applyTo` patterns match intended files
   - Check for unintended file matches
   - Verify patterns work cross-platform

2. **Check for Conflicts**:
   - Review hierarchy: personal > repository > organization
   - Ensure rules don't contradict each other
   - Test with files at hierarchy boundaries

3. **Validate Rules**:
   - Apply to real code and verify AI follows them
   - Test edge cases and ambiguous scenarios
   - Check if reasoning is clear and helpful

4. **Test Across Models**:
   - Verify instructions work with target AI models
   - Check if examples are understood correctly
   - Validate reasoning helps with edge cases

**Common Issues**:
- Rules too vague → Add concrete examples
- Rules conflicting → Check hierarchy and scope
- Rules ignored → Make them more specific and actionable
- Pattern not matching → Test glob pattern syntax
- Over-specification → Trust model intelligence for obvious cases

## Quality Assurance Checklist

**Frontmatter**:
- [ ] `name` is descriptive and clear
- [ ] `description` explains scope accurately
- [ ] `applyTo` pattern is specific and tested
- [ ] Optional fields (`source`, `license`) included if applicable

**Content**:
- [ ] Rules are specific and actionable
- [ ] Focus on non-obvious conventions (not linter rules)
- [ ] Reasoning is provided for each rule
- [ ] Imperative mood used consistently
- [ ] Structured with headers and bullets
- [ ] Code examples included for complex rules

**Examples**:
- [ ] Both good (✅) and bad (❌) examples shown
- [ ] Examples are realistic and practical
- [ ] Edge cases are demonstrated
- [ ] Reasoning connects examples to rules

**Quality**:
- [ ] No conflicts with other instruction files
- [ ] Rules don't duplicate linter/formatter checks
- [ ] File is focused on single topic/domain
- [ ] Length is reasonable (split if >500 lines)
- [ ] Cross-platform compatible (no OS-specific paths)

**Testing**:
- [ ] `applyTo` pattern matches intended files
- [ ] Rules applied to real code successfully
- [ ] AI assistant follows instructions correctly
- [ ] Edge cases handled appropriately
- [ ] No unintended side effects

## Additional Resources

- [Custom Instructions Documentation](https://code.visualstudio.com/docs/copilot/customization/custom-instructions)
- [Awesome Copilot Instructions Collection](https://github.com/github/awesome-copilot/tree/main/instructions)
- [Prompt Engineering Best Practices](https://platform.openai.com/docs/guides/prompt-engineering)
