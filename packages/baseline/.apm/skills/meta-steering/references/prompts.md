# Prompt Files Guidelines

**Contents:** [Scope and Principles](#scope-and-principles) · [Prompt Engineering Techniques](#prompt-engineering-techniques) · [Structuring Larger Prompts](#structuring-larger-prompts) · [Bounding Open-Ended Behavior](#bounding-open-ended-behavior) · [Authority and Trust Boundaries](#authority-and-trust-boundaries) · [Frontmatter Fields](#frontmatter-fields) · [Cross-Tool Compatibility (Copilot + Claude Code)](#cross-tool-compatibility-copilot--claude-code) · [File Naming and Placement](#file-naming-and-placement) · [Input and Context Handling](#input-and-context-handling) · [Output and Failure Contracts](#output-and-failure-contracts) · [Instruction Tone and Style](#instruction-tone-and-style) · [Model-Generation Effects](#model-generation-effects) · [Anti-Patterns to Avoid](#anti-patterns-to-avoid) · [Quality Assurance Checklist](#quality-assurance-checklist) · [Additional Resources](#additional-resources)

Instructions for creating effective and maintainable prompt files that guide an AI assistant in delivering consistent, high-quality outcomes across any repository.

> [!IMPORTANT]
> **Relation to other customization files**
>
> Use the minimum text that still makes the task unambiguous.
>
> Put durable policy in instructions or agent skills. Keep prompts focused on inputs, output shape, and execution expectations.

## Scope and Principles

- **Target audience**: Maintainers and contributors authoring reusable prompts
- **Goals**: Predictable behavior, clear expectations, minimal permissions, portability across repositories
- **Core principle**: Spend the **minimum text necessary** to define inputs, output shape, tool/model needs, and failure behavior — nothing more

## Prompt Engineering Techniques

Effective prompts use these techniques (ranked by effectiveness):

1. **Be Clear and Direct**: Use imperative mood ("Generate", "Analyze", "List"); avoid vague language
2. **Define the Output Contract**: Specify required sections, ordering, format, or stop conditions explicitly — include an explicit completion criterion ("Done when...") the assistant can self-check, not just a shape
3. **State Tool and Agent Requirements**: Name required tools, preferred agent, and confirmation thresholds when side effects are possible
4. **Handle Missing Context**: Say what to do if required inputs, selection, or file context are absent
5. **Use Examples Selectively**: Add examples only when they remove ambiguity or show an edge case
6. **Use Structured Delimiters**: Use markdown headers or XML tags to separate instructions from reference content
7. **Ask for Visible Checks, Not Hidden Reasoning**: Request concise rationale, evidence, or verification when needed

## Structuring Larger Prompts

Use fixed slots with an explicit completion criterion instead of freeform prose:

- **Goal** – the outcome, one sentence
- **Context** – inputs and relevant environment facts
- **Constraints** – hard requirements and boundaries
- **Done-when** – the completion criterion the assistant can self-check before responding

For longer prompts, order sections by priority so truncation or skimming loses the least-important content first: **Objective → Hard requirements → Constraints → Guidance → Output format → Examples**.

## Bounding Open-Ended Behavior

- **Bound clarification**: on ambiguity, ask up to 1-3 precise questions or present 2-3 concrete interpretations — never an open-ended "ask if unclear"
- **Bound agentic loops**: give a numeric ceiling, an escape hatch, and an explicit stop criterion (e.g. "max 2 tool calls; stop once results converge") instead of "be thorough"
- **Tie output length to task-size tiers**: state concrete counts per tier (e.g. "≤10-line change → 2-5 sentences or ≤3 bullets") instead of a flat "be concise"

## Authority and Trust Boundaries

- Treat the prompt body as the governing instruction for the requested task
- Treat `${selection}`, pasted text, retrieved docs, tool output, and attachments as task input or reference context unless the prompt explicitly says otherwise
- Keep durable project policy out of prompt files when a higher-authority instruction or skill can own it instead

## Frontmatter Fields

**Copilot authoring baseline: CLI.** New Copilot workflows use skills. The CLI reads prompts only through the `claude` target's `.claude/commands/` output; VS Code-only fields below are compatibility documentation, not fields to add for new CLI behavior. Keep existing fields valid on another deployed target. Per-target validity and survival: [runtime matrix](./frontmatter-deploy.md#the-matrix).

Every prompt file carries YAML frontmatter with the following fields:

### Required/Recommended Fields

| Field           | Required    | Valid on | Description |
| --------------- | ----------- | -------- | ----------- |
| `description`   | Recommended | VS Code, Claude | Populates the slash-command menu entry: naming-first, action-oriented, single sentence starting with a verb. Same discovery craft as skill descriptions (see [the router, section 3](../SKILL.md#3-description-craft--all-four-types)), even though prompts compete with fewer siblings |
| `name`          | Optional    | VS Code | The name shown after typing `/` in chat. A discriminating name is the cheapest routing lever. Defaults to the filename. Claude commands take their name from the filename and do not accept this key |
| `agent`         | Optional (VS Code Local compatibility) | VS Code | The agent to use: `ask`, `agent`, `plan`, or a custom agent name. Defaults to the current agent. Claude also has an `agent` key, but it names the subagent type for `context: fork`, a different meaning |
| `model`         | Optional    | VS Code, Claude | The language model to use. Defaults to the currently selected model |
| `tools`         | Optional    | VS Code | List of tool/tool set names available for this prompt; restricts availability. Claude's `allowed-tools` only pre-approves listed tools and restricts nothing; Claude's restriction is `disallowed-tools`, which APM drops |
| `argument-hint` | Optional    | VS Code, Claude, Copilot CLI | Hint text shown in chat input to guide user interaction |
| `input`         | Optional    | APM only (deployer input) | Names for Claude `arguments`. APM rewrites `${input:name}` to `$name` only for names listed here; see [Input and Context Handling](#input-and-context-handling) |
| `metadata.provenance` | Optional | repo convention | Provenance; convention owned by [the router, section 4](../SKILL.md#4-frontmatter-shared-by-all-four-types) |

Claude Code commands accept the skill frontmatter schema except `name` and `paths`; which keys survive APM is in the matrix.

**No harness has a `skills:` key on a prompt.** Bind a skill by linking it by relative path in the body and telling the reader to load it first.

### Guidelines

- Use consistent quoting (single quotes recommended) and keep one field per line for readability and version control clarity
- If `tools` are specified, the default agent becomes `agent` (VS Code)
- Be explicit about `agent` when tool requirements or side effects matter; do not rely on implicit escalation
- Preserve any additional metadata (`language`, `tags`, `visibility`, etc.) required by your organization

## Cross-Tool Compatibility (Copilot + Claude Code)

Prompt files serve GitHub Copilot in VS Code (as "Prompts") and Claude Code (as "Commands"). Both expose them as user-invocable slash commands. Codex still supports [deprecated custom prompts](https://learn.chatgpt.com/docs/custom-prompts) in its local `~/.codex/prompts/` directory, with `description` and `argument-hint` frontmatter. APM does not deploy prompts to Codex. Keep the native valid fields distinct from that deployment gap; use a skill for workflows this repository must distribute to Codex through APM.

Whether a key works is decided by harness spec, deployer and author intent; [frontmatter-deploy.md](./frontmatter-deploy.md) owns the model, the matrix and APM's command allowlist. For prompts:

- **Author every key valid on a deployed target, even where APM drops it.** `name`, `agent` and `tools` are dropped for Claude commands but valid for VS Code: keep them.
- **Restate each stripped key's behavioral intent in the body**: the tools the task needs, when to confirm, and the skill to load first. Prose does not enforce tool permissions or invocation controls; see [graceful degradation](./frontmatter-deploy.md#degrade-gracefully).

> [!NOTE]
> Commands are superseded by Skills in Claude Code, however we retain the separation of concerns with prompts being for reusable quick-use inputs.

## File Naming and Placement

- Use kebab-case filenames ending with `.prompt.md`. In this repository the source lives in `packages/<package>/.apm/prompts/`; APM deploys it to `.github/prompts/` and `.claude/commands/`. Outside APM, VS Code's workspace default is `.github/prompts/`.
- Provide a short filename that communicates the action (for example, `generate-readme.prompt.md` rather than `prompt1.prompt.md`).

## Input and Context Handling

### Variable Substitution

VS Code accepts `${input:name}` and `${input:name:placeholder}`. Claude commands receive only what APM rewrites (see [the deployer caveats](./frontmatter-deploy.md#deployer-caveats)):

| Body form | VS Code | Claude command after APM |
|---|---|---|
| `${input:name}` with `input: [name]` in frontmatter | Prompts for `name` | `$name`, bound to **one** positional token |
| `${input:name:placeholder}` | Prompts, with placeholder | Literal text, never rewritten |
| `${input:name}` without `input:` | Prompts for `name` | Literal text |

- **Several short values** (an id, a framework name): declare `input: [a, b]`, write `${input:a}`, and set `argument-hint` for the placeholder text.
- **One free-text value** (a brief, pasted config): do not declare `input`, because `$name` would capture only the first word. Write the body so it still reads correctly when the variable arrives literally, e.g. "Plan a trip from the brief supplied with this command: `${input:brief}`", and put the hint in `argument-hint`.

### Contextual Variables

`${selection}`, `${file}`, `${workspaceFolder}` and similar variables are VS Code-only and reach Claude as literal text. State a fallback in the body ("the selected text, or the file the user names") rather than relying on the variable.

**Best practices**:
- Explain when users must supply values
- Provide defaults or alternatives where possible
- Document how to proceed when mandatory context is missing
- State whether the assistant should ask for missing context, infer from the workspace, or stop with a clear explanation
- Link to other customization files using markdown links to load their content

## Output and Failure Contracts

- Specify the expected output shape explicitly, especially for review, transformation, or generation prompts
- State what counts as completion and whether the assistant must verify anything before responding
- Define failure behavior for missing context, unavailable tools, or ambiguous requests
- If the prompt can cause edits or side effects, say whether the assistant should act immediately or confirm first

## Instruction Tone and Style

- Write in direct, imperative sentences addressed to the agent (for example, “Analyze”, “Generate”, “Summarize”).
- Keep sentences short and unambiguous.
- Avoid idioms, humor, or culturally specific references; favor neutral, inclusive language.

## Model-Generation Effects

Literal scoping, the consistency pass, explicit hard requirements, and positive-example preference apply to every steering file type. Label defaults separately and give decision criteria for adapting them. See [the router, section 5](../SKILL.md#5-anti-patterns-across-all-four-types).

## Anti-Patterns to Avoid

❌ **Don't:**
- Write vague descriptions like "helpful prompt" or "generates code"
- Use walls of text without structure (headers, bullets, sections)
- Add examples by default when the task is already unambiguous
- Assume context variables are always available
- Grant more tools than necessary (principle of least privilege)
- Write in second person ("you should") - use imperative mood
- Over-complicate simple tasks with excessive structure
- Make prompts do what agents or instructions should handle
- Ask for hidden chain-of-thought or internal reasoning traces
- Include time-sensitive information without clear expiration
- Use Windows-style paths or system-specific references
- Leave clarification or agentic loops open-ended ("ask if unclear", "be thorough") — bound them with concrete counts, ceilings, and stop criteria
- Blur a hard requirement with an undefined exception such as "unless easier"

✅ **Do:**
- Write action-oriented descriptions (starts with verb)
- Structure with markdown headers and XML tags for clarity
- Handle missing context gracefully with fallbacks
- Specify only necessary tools in frontmatter
- Use imperative mood: "Analyze", "Generate", "Create"
- Use the minimum text that still defines inputs, output format, and failure handling
- Link to instruction files or agent skills for complex guidance
- Test with one representative case and one missing-context or conflicting-context case
- Use portable, cross-platform references
- Bound clarification, loops, and output length with concrete numbers and explicit stop criteria
- State hard requirements unambiguously; label preferences as defaults and state when they may change

## Quality Assurance Checklist

**Frontmatter**:
- [ ] Description is naming-first, action-oriented, and specific (populates the slash-command menu)
- [ ] If `agent` is set (VS Code), it matches task complexity (`ask`, `agent`, `plan`, or custom)
- [ ] Every key stripped on some target (see [frontmatter-deploy.md](./frontmatter-deploy.md)) is kept, and its intent is restated in the body
- [ ] No `skills:` key; any skill the prompt depends on is linked by relative path in the body
- [ ] argument-hint provides clear guidance for user input
- [ ] If `name` is omitted, the filename is descriptive and kebab-case; if `name` is present, it is descriptive in the slash-command UI

**Content**:
- [ ] Instructions distinguish hard requirements from defaults and give decision criteria for permitted adaptations
- [ ] Structure uses markdown headers and/or XML tags
- [ ] Output format is explicitly defined, including a fixed-slot structure (Goal/Context/Constraints/Done-when) for larger prompts
- [ ] Completion criterion ("Done when...") and failure behavior are explicit, not just output shape
- [ ] Clarification, agentic loops, and output length are bounded with concrete numbers and stop criteria
- [ ] Prompt text is internally consistent — no contradictory instructions

**Variables and Context**:
- [ ] Every `${input:*}` variable follows the Variable Substitution table: names used as Claude arguments are declared in `input:` and placeholder-free; free text is not declared
- [ ] Context variables (`${selection}`, etc.) have fallback behavior
- [ ] Mandatory context missing scenarios are documented
- [ ] Variable names are descriptive and clear

**Execution**:
- [ ] Tool and agent requirements are intentional and explicit
- [ ] Side effects require confirmation when appropriate
- [ ] Verification expectations are documented when correctness matters

**Portability**:
- [ ] Uses forward slashes for paths
- [ ] Avoids system-specific references
- [ ] No hardcoded credentials or secrets

## Additional Resources

- [Prompt File Format (VS Code)](https://code.visualstudio.com/docs/agent-customization/prompt-files#_prompt-file-format)
- [Slash Commands (Claude Code)](https://code.claude.com/docs/en/slash-commands)
- [APM Prompts](https://microsoft.github.io/apm/producer/author-primitives/prompts/): the frontmatter keys APM preserves, and the per-target command output
- [frontmatter-deploy.md](./frontmatter-deploy.md): per-target validity and APM survival for every type
- [Prompt Engineering](https://developers.openai.com/api/docs/guides/prompt-engineering)
- [Reasoning Best Practices](https://developers.openai.com/api/docs/guides/reasoning-best-practices)
- [Awesome Copilot prompt-file authoring guide](https://github.com/github/awesome-copilot/blob/main/instructions/prompt.instructions.md)
- [GPT-5 Prompting Guide](https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_prompting_guide)
- [Prompt Optimization Cookbook](https://developers.openai.com/cookbook/examples/gpt-5/prompt-optimization-cookbook)
