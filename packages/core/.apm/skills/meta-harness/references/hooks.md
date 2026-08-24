# Lifecycle Hook Guidelines

**Contents:** [When to Use Hooks](#when-to-use-hooks) · [Cross-Tool Compatibility](#cross-tool-compatibility) · [Lifecycle Events](#lifecycle-events) · [Hook Configuration](#hook-configuration) · [File Layout](#file-layout) · [Common Patterns](#common-patterns) · [Quality Checklist](#quality-checklist) · [Anti-Patterns](#anti-patterns)

Guidance for creating reliable lifecycle hooks across Claude Code, VS Code Copilot, and APM-managed packages.

> [!IMPORTANT]
> Hooks are for deterministic, event-driven automation.
> Use instructions and skills for behavior steering, and use MCP/plugins for adding external capabilities.

For full event schemas and platform-specific JSON contracts, consult the authoritative docs:
- Claude Code: [Hooks reference](https://code.claude.com/docs/en/hooks), [Hooks guide](https://code.claude.com/docs/en/hooks-guide)
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

Hooks are the **deterministic arm of the triggering ladder**: autonomous skill/instruction triggering is inherently probabilistic (see [the `meta-steering` router, section 1](../../meta-steering/SKILL.md#1-pick-the-customization-type-first)). When something must always happen, reach for a hook — or an explicit invocation — not stronger description prose.

### Decision Criteria

Hooks vs instructions vs skills vs MCP/plugins: the complete seven-way table is in [the `meta-steering` router, section 1](../../meta-steering/SKILL.md#1-pick-the-customization-type-first), and the harness-side half is in [the `meta-harness` router, section 1](../SKILL.md#1-is-it-actually-harness-config). The short form: hooks enforce runtime guardrails at specific events because they are deterministic; everything that merely *teaches* a behaviour belongs in an instruction or a skill.

## Cross-Tool Compatibility

### Configuration Surface

| Platform | Configuration | Location | Format |
|---|---|---|---|
| Claude Code | `hooks:` in agent frontmatter or `hooks` in settings | Per-agent or global (`~/.claude/settings.json`, `.claude/settings.json`) | YAML/JSON |
| VS Code Copilot | `hooks/*.json` files | Workspace or user-level (commonly `.github/hooks/*.json`; configurable locations) | JSON |
| VS Code Copilot (Preview) | `hooks:` in agent frontmatter | Travels with the agent file instead of a global/workspace location | YAML/JSON |
| APM | `.apm/hooks/*.json` | Package-level | JSON |

### Compatibility Notes

- Claude and VS Code share a strongly overlapping schema for command hooks (stdin JSON, stdout JSON control).
- APM does not define a new runtime; it packages/transforms hooks into each target's native locations and naming conventions.
- Event names are not perfectly identical across tools and versions.
- VS Code Copilot agent-scoped `hooks:` is a **Preview** feature — verify current availability and field names against the docs before relying on it.

> [!WARNING]
> Treat event names and fields as target contracts, not universal contracts. Always verify against current docs for your target version.

## Lifecycle Events

Do not memorize every event schema. Use category-based design and confirm exact fields in the platform docs.

### Event Categories

| Category | Typical events | When they fire | Common input focus | Common control output |
|---|---|---|---|---|
| Session lifecycle | `SessionStart`, `SessionEnd`, `Stop` | Session begin/end or turn completion | Session source/IDs/cwd/transcript | Continue/block decisions, context injection |
| Tool lifecycle | `PreToolUse`, `PostToolUse` | Before/after tool execution | Tool name, tool input, tool output/result | Allow/deny/ask, rewrite input, add context |
| File lifecycle | `PostFileWrite` (where supported), `FileChanged`, or `PostToolUse` filtered to edit/write tools | After file mutation or watched file change | Changed path(s), write metadata, triggering tool | Run formatter/linter, block on policy failure |
| Permission lifecycle | `PermissionRequest`, `PermissionDenied` (platform-dependent) | Approval and denial boundaries | Requested tool/action and reason | Approve, request confirmation, deny |
| Compaction lifecycle | `PreCompact`, `PostCompact` | Before/after context compaction | Trigger reason and context state | Persist/reload context, reinject critical data |
| Subagent lifecycle | `SubagentStart`, `SubagentStop` | Subagent spawn/finish | Agent ID/type and stop state | Inject context, block stop with reason |

### Shared vs Platform-Specific (High Level)

- Common core across Claude and VS Code: `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop`, `SubagentStart`, `SubagentStop`, `PreCompact`.
- Claude currently exposes broader coverage, including additional async/system events and richer matcher variants.
- APM supports hook authoring as a packaging primitive and maps to each target's supported lifecycle/event model.

## Hook Configuration

### Matchers

Use matchers to scope hook execution narrowly:
- Tool-name matching for tool lifecycle events (`PreToolUse`, `PostToolUse`)
- File-name matching for file watch events (platform-specific semantics)
- Source/trigger matching for session or compaction events

Prefer specific matchers over wildcard `*`.

### Command Specification

Common command fields across platforms:
- `type: "command"`
- `command`: shell command
- Optional: `cwd`, `env`, per-OS command overrides, `timeout`

If supported by the platform, use direct exec/args mode for safer argument handling and shell mode only when pipes/globs are needed.

### Input and Output Contract

Most hooks follow this contract:
- Input: JSON payload on stdin
- Output: JSON payload on stdout (optional)

Typical control fields:
- Session-level flow: `continue`, `stopReason`
- Event-specific control: `hookSpecificOutput` payloads (for example permission decisions, additional context, block reasons)

### Exit Code Semantics

Use exit codes intentionally:
- `0`: success; parse stdout JSON if present
- Non-zero: warning or failure path (platform-specific)
- Blocking convention often uses code `2` for hard block/error in hook processing

Always validate behavior against target docs, especially for stop/block semantics.

### Timeout and Async

- Set explicit per-hook timeouts; do not rely on defaults.
- Keep synchronous hooks short and deterministic.
- Use async/background modes only where supported and only for non-critical side effects.

> [!IMPORTANT]
> Hook handlers must be non-interactive. Any command waiting on user input can deadlock agent progress.

## File Layout

### Claude Code

- Inline agent scope: `hooks:` in `.agent.md` frontmatter
- Global/project settings: `~/.claude/settings.json` or `.claude/settings.json`

### VS Code Copilot

- Hooks directory with JSON files per hook (commonly `.github/hooks/*.json` in workspace layout)
- User-level hooks are supported via configured hook file locations

### APM

- Author package hooks in `.apm/hooks/` with one or more JSON files
- `hooks/*.json` is also discovered for Claude-native hook slices in APM workflows
- APM installs/transforms to target-native hook locations during integration

> [!NOTE]
> **Standalone hook filenames are matched by glob (`*.json`), not by a fixed name** — so this repo names them `*.hook.json` (parity with `*.agent.md` / `*.prompt.md` / `*.instructions.md`; see [CONTRIBUTING](../../../../../../CONTRIBUTING.md#hooks-hookjson)). It is a strict subset of `*.json`, so VS Code folder discovery and APM still pick it up, and Claude Code is unaffected because it reads hooks from `settings.json` rather than scanning the directory. The fixed names `hooks.json` / `hooks/hooks.json` apply only inside **plugin** bundles, not to standalone hook files.

## Common Patterns

Brief patterns you can adapt across tools.

### Format on Write

Use `PostFileWrite` where available, otherwise `PostToolUse` filtered to write/edit tools.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "npm run format -- $TOOL_INPUT_FILE_PATH", "timeout": 20 }
        ]
      }
    ]
  }
}
```

### Protected File Blocking

Block writes to sensitive paths in `PreToolUse`.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "./scripts/block-protected-files.sh", "timeout": 10 }
        ]
      }
    ]
  }
}
```

### Context Re-Injection After Compaction

Use `PostCompact` to re-add critical context from a deterministic source.

```json
{
  "hooks": {
    "PostCompact": [
      {
        "hooks": [
          { "type": "command", "command": "./scripts/reinject-context.sh", "timeout": 10 }
        ]
      }
    ]
  }
}
```

### Notification on Task Completion

Use `Stop` or `TaskCompleted` events (where available) to notify humans.

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          { "type": "command", "command": "./scripts/notify-complete.sh", "timeout": 5 }
        ]
      }
    ]
  }
}
```

## Quality Checklist

- Hook command is idempotent.
- Hook has explicit, reasonable timeout.
- Hook does not require interactive input.
- Exit code behavior is intentional and tested.
- Matchers are specific, not broad wildcards.
- Hook is tested in isolation before lifecycle attachment.
- Hook logging is sufficient for debugging.
- Failure path is explicit (block vs warn vs continue).

## Anti-Patterns

- Using hooks to steer behavior that belongs in instructions or skills.
- Overly broad matchers that trigger on every event.
- Long-running synchronous hooks that stall the agent loop.
- Hooks that rewrite the same file path repeatedly and create loops.
- Hidden side effects without logs, making failures hard to diagnose.
- Depending on undocumented fields or stale event names.

> [!WARNING]
> Avoid self-triggering file mutation loops: if a post-write hook edits the same file, add guards (path filter, checksum check, or reentry marker) so it only runs once per change.
