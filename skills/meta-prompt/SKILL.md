---
name: "meta-prompt"
description: "Guidelines for creating high-quality prompts. Use when asked to create, review, or improve stored prompts, design reusable prompt templates, configure prompt variables, or apply prompt engineering techniques. Keywords: prompt, template, variable, input, substitution, few-shot, chain-of-thought."
license: "MIT"
metadata:
  provenance:
    adaptedFrom: "https://github.com/github/awesome-copilot/blob/main/instructions/prompt.instructions.md"
---

# Prompt Files Guidelines

Instructions for creating effective and maintainable prompt files that guide an AI assistant in delivering consistent, high-quality outcomes across any repository.

> [!IMPORTANT] Relation to other customization files
>
> Prompts should be kept short and sweet.
>
> Prefer putting detailed instructions in an instruction file or an agent skill.

## Scope and Principles

- **Target audience**: Maintainers and contributors authoring reusable prompts
- **Goals**: Predictable behavior, clear expectations, minimal permissions, portability across repositories
- **Core principle**: Prompts should be **short and focused**. Use instruction files for detailed rules and agent skills for complex workflows

## Prompt Engineering Techniques

Effective prompts use these techniques (ranked by effectiveness):

1. **Be Clear and Direct**: Use imperative mood ("Generate", "Analyze", "List"); avoid vague language
2. **Use Examples (Few-Shot Learning)**: Include 3-5 diverse examples covering typical and edge cases
3. **Chain of Thought**: Add "Think step by step" for complex reasoning tasks
4. **Structured Delimiters**: Use markdown headers and XML tags for clear boundaries
5. **Provide Context**: Include relevant documentation, frameworks, or domain knowledge
6. **Define Output Format**: Specify expected structure explicitly

## Frontmatter Fields

Every prompt file should include YAML frontmatter with the following fields:

### Required/Recommended Fields

| Field           | Required    | Description                                                                                 |
| --------------- | ----------- | ------------------------------------------------------------------------------------------- |
| `description`   | Recommended | A short description of the prompt (single sentence, actionable outcome)                     |
| `name`          | Optional    | The name shown after typing `/` in chat. Defaults to filename if not specified              |
| `agent`         | Recommended | The agent to use: `ask`, `edit`, `agent`, or a custom agent name. Defaults to current agent |
| `model`         | Optional    | The language model to use. Defaults to the currently selected model                         |
| `tools`         | Optional    | List of tool/tool set names available for this prompt                                       |
| `argument-hint` | Optional    | Hint text shown in chat input to guide user interaction                                     |
| `metadata.provenance.mirror` | Optional | Canonical upstream URL for exact copies |
| `metadata.provenance.adaptedFrom` | Optional | URL (string) or list of URLs (array) when adapted/synthesised from upstream sources |

### Guidelines

- Use consistent quoting (single quotes recommended) and keep one field per line for readability and version control clarity
- If `tools` are specified and the current agent is `ask` or `edit`, the default agent becomes `agent`
- Preserve any additional metadata (`language`, `tags`, `visibility`, etc.) required by your organization
- For provenance tracking, use `metadata.provenance` fields (`mirror`, `adaptedFrom`, `authoritativeSpec`); use the same convention for prompts, instructions, skills, and agents

## Cross-Tool Compatibility (Copilot + Claude Code)

Prompt files can serve both GitHub Copilot (as "Prompts") and Claude Code (as "Commands"). Both create user-invokable slash commands. Each tool ignores frontmatter fields it does not recognize, so a single file works for both.

> [!NOTE] Commands are superseded by Skills in Claude Code, however we retain the separation of concerns with prompts being for reusable quick-use inputs.

## File Naming and Placement

- Use kebab-case filenames ending with `.prompt.md` and store them under `.github/prompts/` unless your workspace standard specifies another directory.
- Provide a short filename that communicates the action (for example, `generate-readme.prompt.md` rather than `prompt1.prompt.md`).

## Input and Context Handling

### Variable Substitution

Use `${input:variableName[:placeholder]}` for required values:

```markdown
${input:componentName:Button}
${input:framework:React}
```

### Contextual Variables

Available context variables:
- `${selection}` - Currently selected text in the editor
- `${file}` - Current file path
- `${workspaceFolder}` - Root workspace directory
- `${fileBasename}` - Current file name without path
- `${fileBasenameNoExtension}` - File name without extension

**Best practices**:
- Explain when users must supply values
- Provide defaults or alternatives where possible
- Document how to proceed when mandatory context is missing
- Link to other customization files using markdown links to load their content

## Instruction Tone and Style

- Write in direct, imperative sentences targeted at Copilot (for example, “Analyze”, “Generate”, “Summarize”).
- Keep sentences short and unambiguous.
- Avoid idioms, humor, or culturally specific references; favor neutral, inclusive language.

## Anti-Patterns to Avoid

❌ **Don't:**
- Write vague descriptions like "helpful prompt" or "generates code"
- Use walls of text without structure (headers, bullets, sections)
- Provide single examples without showing edge cases
- Assume context variables are always available
- Grant more tools than necessary (principle of least privilege)
- Write in second person ("you should") - use imperative mood
- Over-complicate simple tasks with excessive structure
- Make prompts do what agents or instructions should handle
- Include time-sensitive information without clear expiration
- Use Windows-style paths or system-specific references

✅ **Do:**
- Write action-oriented descriptions (starts with verb)
- Structure with markdown headers and XML tags for clarity
- Include 3-5 diverse examples (typical + edge cases)
- Handle missing context gracefully with fallbacks
- Specify only necessary tools in frontmatter
- Use imperative mood: "Analyze", "Generate", "Create"
- Keep prompts focused and brief (under 500 words)
- Link to instruction files or agent skills for complex guidance
- Test across different model families (GPT vs Claude vs reasoning)
- Use portable, cross-platform references

## Quality Assurance Checklist

**Frontmatter**:
- [ ] Description is action-oriented and specific
- [ ] Agent selection matches task complexity (`ask`, `edit`, `agent`, or custom)
- [ ] argument-hint provides clear guidance for user input
- [ ] Name is descriptive and follows kebab-case convention

**Content**:
- [ ] Instructions use imperative mood consistently
- [ ] Structure uses markdown headers and/or XML tags
- [ ] Output format is explicitly defined
- [ ] Content is under 500 words (brief and focused)

**Variables and Context**:
- [ ] All `${input:*}` variables have placeholders or defaults
- [ ] Context variables (`${selection}`, etc.) have fallback behavior
- [ ] Mandatory context missing scenarios are documented
- [ ] Variable names are descriptive and clear

**Portability**:
- [ ] Uses forward slashes for paths
- [ ] Avoids system-specific references
- [ ] No hardcoded credentials or secrets

## Additional Resources

- [Prompt Files Documentation](https://code.visualstudio.com/docs/copilot/customization/prompt-files#_prompt-file-format)
- [Awesome Copilot Prompt Files](https://github.com/github/awesome-copilot/tree/main/prompts)