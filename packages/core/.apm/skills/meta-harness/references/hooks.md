# Lifecycle Hook Guidelines

**Contents:** [When to Use Hooks](#when-to-use-hooks) · [Cross-Tool Compatibility](#cross-tool-compatibility) · [Lifecycle Events](#lifecycle-events) · [Hook Configuration](#hook-configuration) · [File Layout](#file-layout) · [Common Patterns](#common-patterns) · [Quality Checklist](#quality-checklist) · [Anti-Patterns](#anti-patterns)

Guidance for creating reliable lifecycle hooks across Claude Code, Codex, Copilot CLI, VS Code Copilot, and APM-managed packages. In this repo the APM canonical form in `.apm/hooks/` is the source for every target; the native schemas below matter when reading generated output or hand-authoring outside APM.

> [!IMPORTANT]
> Hooks attach automation to lifecycle events. Use deterministic handlers for hard checks; model-based handlers do not provide deterministic decisions.
> Use instructions and skills for behavior steering, and use MCP/plugins for adding external capabilities.

For full event schemas and platform-specific JSON contracts, consult the authoritative docs:
- Claude Code: [Hooks reference](https://code.claude.com/docs/en/hooks), [Hooks guide](https://code.claude.com/docs/en/hooks-guide)
- Codex: [Hooks reference](https://learn.chatgpt.com/docs/hooks)
- Copilot CLI: [Use hooks](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/use-hooks)
- Copilot decisions and failures: [Hooks reference](https://docs.github.com/en/copilot/reference/hooks-reference)
- VS Code Copilot: [Agent hooks](https://code.visualstudio.com/docs/agent-customization/hooks)
- APM: [Hooks and commands](https://microsoft.github.io/apm/producer/author-primitives/hooks-and-commands/)

## When to Use Hooks

Use hooks when you need code to run automatically at lifecycle boundaries, independent of model judgment.

Typical fit:
- Blocking unsafe tool calls before execution
- Running validation or formatting after edits
- Injecting deterministic context at session start
- Emitting notifications or audit entries on completion

Do not use hooks for prompt steering or broad policy text.

### Decision Criteria

Hooks vs instructions vs skills vs MCP/plugins: the complete seven-way table is in [the `meta-steering` router, section 1](../../meta-steering/SKILL.md#1-pick-the-customization-type-first), and the harness-side half is in [the `meta-harness` router, section 1](../SKILL.md#1-is-it-actually-harness-config). For a required check, use a supported hook event with a deterministic handler and verify trust, rejection and timeout behavior — stronger description prose cannot supply those runtime controls.

## Cross-Tool Compatibility

### Configuration Surface

| Platform | Configuration | Location | Format |
|---|---|---|---|
| Claude Code | `hooks` in settings, plugin `hooks/hooks.json`, `hooks:` in skill or agent frontmatter | `~/.claude/settings.json`, `.claude/settings.json`, `.claude/settings.local.json`, managed policy, plugins, per-skill/agent | JSON/YAML |
| Codex | `hooks.json`, inline `[hooks]` config, or plugin hooks | `~/.codex/` and `<repo>/.codex/` (`hooks.json`, `config.toml`), installed plugins; non-managed definitions require trust | JSON/TOML |
| Copilot CLI | `version: 1`; camelCase events with camelCase fields, or PascalCase events with snake_case fields | `.github/hooks/*.json`, `~/.copilot/hooks/*.json`, `.github/copilot/settings.json`, **`.claude/settings.json`** (+ `.local.json` variants), `~/.copilot/settings.json`, policy dirs; loaded at startup | JSON |
| VS Code Copilot | `hooks/*.json` files | Workspace or user-level (commonly `.github/hooks/*.json`; `chat.hookFilesLocations`); `.claude/settings.json` only with `chat.useClaudeHooks` | JSON |
| VS Code Copilot (Preview) | `hooks:` in agent frontmatter | Travels with the agent file; Local harness only | YAML/JSON |
| APM | `.apm/hooks/*.json` | Package-level | JSON |

### Compatibility Notes

- APM does not define a new runtime; it packages/transforms hooks into each target's native locations and naming conventions.
- Event names, decisions, handler types and trust semantics are target contracts, not universal ones. Codex supports `command` and `mcp_tool` handlers; Claude adds `http`, `prompt` and `agent`.
- **Copilot CLI accepts Claude-style input.** PascalCase events "apply Claude's matcher semantics"; `command` is a cross-platform fallback to `bash`/`powershell`; `timeout` is accepted, with `timeoutSec` taking precedence ([hooks reference](https://docs.github.com/en/copilot/reference/hooks-reference)). Whether it accepts the nested `matcher` + `hooks` array shape is not documented — verify.
- **Double-run risk.** Copilot CLI also loads `.claude/settings.json`. A hook APM deploys to both the `claude` target (settings) and the `copilot` target (`.github/hooks/<pkg>-*.json`) can run twice in Copilot CLI; check before deploying to both.

> [!WARNING]
> Treat event names and fields as target contracts, not universal contracts. Always verify against current docs for your target version.

## Lifecycle Events

Do not memorize every event schema; confirm exact names and fields in the platform docs. The core shared by Claude and VS Code Local is `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact`, `SubagentStart`, `SubagentStop`, `Stop`. Copilot CLI's camelCase equivalents include `preToolUse`, `postToolUse` and `agentStop`; Codex adds `PermissionRequest`, `PostCompact` and `Interrupt`. Claude exposes the broadest set (for example `PostToolUseFailure`, `Notification`, `FileChanged`, `PostCompact`).

**File mutation has no portable event.** Use `PostToolUse` filtered to edit/write tools. Claude's `FileChanged` covers watched files; Kiro has `PostFileSave` / `PostFileCreate`. No harness defines a `PostFileWrite` event.

## Hook Configuration

### Matchers

Use matchers to scope hook execution narrowly:
- Tool-name matching for tool lifecycle events (`PreToolUse`, `PostToolUse`); Codex maps `Edit`/`Write` onto `apply_patch`
- Source/trigger matching for session or compaction events

Prefer specific matchers over wildcard `*`.

> [!WARNING]
> **VS Code's Local harness ignores matcher values** and runs every command registered for the event. A hook deployed to VS Code must filter inside its own script (read the tool name from the payload and exit early) rather than rely on the matcher. VS Code's Agent Host harnesses follow each provider's own hook rules ([VS Code hooks](https://code.visualstudio.com/docs/agent-customization/hooks)).

### Command Specification

Claude-style command fields, also used by APM's canonical source format:
- `type: "command"`
- `command`: shell command; with an `args` array Claude runs it in exec form (no shell interpretation) — use that unless pipes/globs are needed
- Optional: `timeout` (seconds), `async` / `asyncRewake`
- VS Code adds per-OS overrides (`windows`, `linux`, `osx`); Copilot CLI uses `bash` / `powershell` + `timeoutSec` natively

When hand-authoring Copilot config outside APM, use the [CLI schema](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/use-hooks). Through APM, author the canonical form: APM 0.31 renames events to camelCase and adds `version: 1` for the `copilot` target, and keeps the nested shape and `command`/`timeout` fields — inspect the generated `.github/hooks/<pkg>-*.json`.

### Input and Output Contract

- Input: JSON payload on stdin. No harness passes tool input as environment variables.
- Output: JSON on stdout (optional): `continue` / `stopReason` for session flow, event-specific `decision` / `reason` / `hookSpecificOutput` (permission decisions, `additionalContext`). Every harness parses stdout only on exit 0.
- **A portable hook reads every payload shape it is deployed to and answers in the dialect it was asked in.** A hook that reads one shape silently no-ops on the others.

`PostToolUse` on an edit, per harness:

| Harness | Edited path in the payload | Feedback to the model | Exit 2 |
|---|---|---|---|
| Claude Code | `tool_input.file_path` | `{"decision": "block", "reason": "…"}`, or `hookSpecificOutput.additionalContext` for non-blocking notes | Ambiguous (below) |
| Codex | `apply_patch`: none; `tool_input.command` holds the patch, with paths on its `*** Add File:` / `*** Update File:` / `*** Move to:` lines, relative to `cwd` | Same fields as Claude; `block` replaces the tool result with the feedback | stderr becomes blocking feedback |
| VS Code Local | Tool-specific and undocumented; inspect the agent debug log (`filePath` is a common field name) | Same fields as Claude | stderr becomes a blocking error |
| Copilot CLI (camelCase `postToolUse`) | `toolArgs`, a JSON **string** (`path` on edit tools) | Top-level `additionalContext` (or `modifiedResult`); `decision`/`reason` apply only to `preToolUse` and `agentStop` | Ignored: non-zero exits are logged and skipped |

Sources: [Claude hooks](https://code.claude.com/docs/en/hooks), [Codex hooks](https://learn.chatgpt.com/docs/hooks), [VS Code hooks reference](https://code.visualstudio.com/docs/agents/reference/hooks-reference), [Copilot hooks reference](https://docs.github.com/en/copilot/reference/hooks-reference). Which shape the Copilot CLI sends to a hook it picks up from `.claude/settings.json` (PascalCase) is not established; detect the shape from the payload (`toolArgs` present) rather than assuming it from the event name. This repository's [frontmatter hook](https://github.com/siegenthalerroger/.llmctl/blob/main/src/llmctl/check_frontmatter.py) implements the table.

### Exit Code Semantics

- `0`: success; stdout JSON is parsed if present.
- `2` blocks only where the event supports blocking. On Claude it blocks `PreToolUse` and prevents `Stop`; for `PostToolUse` the tool has already run.
- **`PostToolUse` + exit 2 is ambiguous in Claude's own docs.** The exit-code table says "Exit code 2 isn't honored for this event", while the command-hook section says to "exit 2 instead so Claude sees the stderr". For `PostToolUse` feedback, emit JSON instead: `{"decision": "block", "reason": "…"}` (reason shown to Claude) or `hookSpecificOutput.additionalContext`, and test that Claude sees it.
- Other non-zero codes are platform-specific: Copilot command `preToolUse` errors deny the call; Codex marks the run failed and continues; VS Code shows a non-blocking warning.
- **For feedback after an edit, exit 0 and emit JSON.** It is the only form every harness reads; exit 2 is ambiguous on Claude and ignored by the Copilot CLI.

### Codex Trust and Decisions

[Codex hooks](https://learn.chatgpt.com/docs/hooks) require trust of the **exact non-managed hook definitions** before execution (manage it with `/hooks`). Trusting a workspace or having a plugin installed is not evidence that its hooks will run; changed definitions need their trust state checked again.

**Do not port Claude's `PreToolUse` approval decisions unchanged.** In Codex, `permissionDecision: "ask"` is parsed but unsupported: Codex "marks the hook run as failed, reports the error, and continues the tool call". Only `allow` and `deny` work; a warning or failed handler is not proof that the tool was blocked.

### Timeout and Async

- Set explicit per-hook timeouts; do not rely on defaults (Claude's command default is 600 s).
- Keep synchronous hooks short and deterministic; use async modes only for non-critical side effects.
- Copilot timeouts fail open for every event. Its command `preToolUse` errors deny, while HTTP handler errors fail open; cloud treats an `ask` decision as deny. These are distinct failure paths, not a portable all-errors-block contract ([Copilot hooks reference](https://docs.github.com/en/copilot/reference/hooks-reference)).

> [!IMPORTANT]
> Hook handlers must be non-interactive. Any command waiting on user input can deadlock agent progress.

## File Layout

### Copilot CLI

- Hooks load at startup; start a new CLI session after changing definitions before validating behavior.
- Portable plugin hook additions use `com.github.copilot/hooks/hooks.json`; see [plugins.md](./plugins.md).

### Codex

- Verify the effective definitions and their trust state, not just the existence of a generated file. Higher-precedence layers do not replace lower-precedence hooks.
- APM 0.31 merges hooks into `.codex/hooks.json` only when a `.codex/` directory already exists.

### APM

- Author package hooks in `.apm/hooks/*.json`; `hooks/*.json` at the package root is also discovered.
- **Author one canonical hook and let APM transform it.** Write APM's canonical (Claude-Code-style) schema — a top-level `hooks` object keyed by lifecycle event, each entry carrying a `matcher` and a `hooks` array of `{ "type": "command", ... }`. Do not hand-maintain per-target variants.
- **Reference bundled scripts as `${CLAUDE_PLUGIN_ROOT}/…` or `./…`.** APM recognises `CLAUDE_PLUGIN_ROOT`, `PLUGIN_ROOT`, `CURSOR_PLUGIN_ROOT` and `KIRO_PLUGIN_ROOT`, copies the referenced script into each target, and rewrites the path (on Claude at project scope, to `"${CLAUDE_PROJECT_DIR}/.claude/hooks/<pkg>/…"`). Any other `${VAR}` — including `${CLAUDE_PROJECT_DIR}` — passes through unchanged and is expanded only by a harness that defines it.
- APM hook support is still maturing: inspect the deployed result after `apm install` before relying on it.

Source filenames (`*.hook.json`) follow [the repo convention](../SKILL.md#6-this-repositorys-conventions).

## Common Patterns

Adapt these; the handler script, not the matcher, carries portability (see [Input and Output Contract](#input-and-output-contract)).

### Protected File Blocking

Block writes to sensitive paths in `PreToolUse` (exit 2 or a `deny` decision).

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/scripts/block-protected-files.py", "timeout": 10 }
        ]
      }
    ]
  }
}
```

### Validate or Format After Edit

`PostToolUse` filtered to edit tools; the script reads the edited paths from stdin in every shape of the [contract table](#input-and-output-contract), exits 0, and reports problems as JSON in the matching dialect.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/scripts/format-edited.py", "timeout": 20 }
        ]
      }
    ]
  }
}
```

Other common attachments: `PostCompact` (Claude, Codex) to re-inject critical context from a deterministic source; `Stop` / `agentStop` or Claude's `Notification` to notify a human.

## Quality Checklist

- Hook command is idempotent and non-interactive.
- Hook has an explicit, reasonable timeout.
- Matchers are specific, and the script also filters (VS Code Local ignores matchers).
- The script handles every target's payload shape it is deployed to, or the hook is scoped to one target.
- Exit code / JSON output behavior is intentional and tested per event; failure path is explicit (block vs warn vs continue).
- Hook logging is sufficient for debugging.
- Native discovery, trust, and rejection behavior are verified on each target; an APM deploy alone does not establish enforcement.

## Anti-Patterns

- Using hooks to steer behavior that belongs in instructions or skills.
- Long-running synchronous hooks that stall the agent loop.
- Hidden side effects without logs, making failures hard to diagnose.
- Depending on undocumented fields, invented event names, or environment variables a harness does not set.
- Fetching an unpinned remote ref (`@main`, `@latest`) inside a hook command — it runs new code on every event.

> [!WARNING]
> Avoid self-triggering file mutation loops: if a post-write hook edits the same file, add guards (path filter, checksum check, or reentry marker) so it only runs once per change.
