# Hooks

Lifecycle hooks for this collection. Authoring guidance lives in the
[`meta-hook` skill](../skills/meta-hook/SKILL.md).

## `validate-customization-frontmatter`

A deterministic guardrail that validates the frontmatter of customization
files (`*.agent.md`, `SKILL.md`, `*.prompt.md`, `*.instructions.md`) after an
`Edit`/`Write`. It dogfoods the conventions in the `meta-*` skills rather than
relying on the model to remember them.

**Checks**

- Frontmatter block is present.
- `name` and `description` are present and non-empty.
- For skills: `name` matches the parent directory, is kebab-case, ≤64 chars.
- `name` and `description` contain no reserved words (`anthropic`, `claude`,
  `copilot`, `openai`) — each meta-* file is the single canonical entry for its
  topic, so discovery runs off domain keywords, not harness names.
- For agents/prompts/instructions: the filename stem is kebab-case (warning).

**Behavior**

- Hard errors → exit `2`; stderr is fed back to the agent so it self-corrects.
- Warnings → exit `0`; surfaced to the transcript, non-blocking.
- Any non-customization file → exits `0` immediately (cheap no-op).

### Files

- `validate-customization-frontmatter.py` — the validator (Python 3,
  dependency-free).
- `validate-customization-frontmatter.json` — VS Code / APM-style hook config
  (`${workspaceFolder}` path token).
- `../.claude/settings.json` — project-scoped Claude Code wiring
  (`$CLAUDE_PROJECT_DIR` path token), active when working in this repo.

### Notes & caveats

- **Runtime:** invoked via `python3`. On Windows hosts where only `python` is
  on `PATH`, adjust the command accordingly (chosen over PowerShell to keep the
  hook cross-platform, per the `meta-skill` script guidance).
- **Path tokens:** the path differs by host — `$CLAUDE_PROJECT_DIR` (Claude
  project hooks) vs `${workspaceFolder}` (VS Code). APM rewrites hook paths to
  each target's native location on deploy; verify the resolved command after
  `apm install -g`.
- **Test manually** without a live session:

  ```bash
  echo '{"tool_input":{"file_path":"skills/meta-skill/SKILL.md"}}' \
    | python3 hooks/validate-customization-frontmatter.py; echo "exit=$?"
  ```
