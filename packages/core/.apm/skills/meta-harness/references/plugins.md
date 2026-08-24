# Plugin Authoring and Packaging Guidelines

**Contents:** [When to Use Plugins](#when-to-use-plugins) · [Cross-Tool Compatibility](#cross-tool-compatibility) · [Plugin Manifest Schema (`plugin.json`)](#plugin-manifest-schema-pluginjson) · [Component Types](#component-types) · [Distribution Models](#distribution-models) · [Local Development Workflow](#local-development-workflow) · [APM Integration](#apm-integration) · [Quality Checklist](#quality-checklist) · [Anti-Patterns](#anti-patterns) · [Reference Links](#reference-links)

Read this when packaging and distributing multiple customizations together, not when authoring a single skill, agent, or hook in isolation.

For volatile schema details and CLI flags, verify against the [Reference Links](#reference-links) below and the `authoritativeSpec` list in [SKILL.md](../SKILL.md).

## When to Use Plugins

Plugins are the packaging and distribution mechanism, not the capability mechanism.

A plugin never substitutes for a component — it ships components that already exist. Settle each component's type against [the `meta-steering` router, section 1](../../meta-steering/SKILL.md#1-pick-the-customization-type-first) first, then decide whether they travel together.

Reach for a plugin when at least one of these is true:

- You need one install surface for multiple components.
- You need versioned releases and upgrade semantics.
- You need marketplace distribution or private internal catalogs.
- You need portable packaging across projects, teams, or tools.

> Keep plugin scope cohesive: one clear domain or problem per plugin, never a kitchen-sink bundle.

Bundling many skills also has a discovery cost: every bundled skill's `description` competes in the consumer's shared skill-discovery budget (Claude Code totals ~15,000 chars across all loaded skills; skills past that cutoff become invisible, not down-ranked — see [the `meta-steering` router, section 3](../../meta-steering/SKILL.md#3-description-craft--all-four-types)). Keep bundles cohesive **and** descriptions short. `SLASH_COMMAND_TOOL_CHAR_BUDGET` exists as consumer-side relief, but a plugin author cannot rely on the consumer having raised it.

## Cross-Tool Compatibility

| Platform | Manifest | Components supported | Installation |
| --- | --- | --- | --- |
| Claude Code | `plugin.json` (typically `.claude-plugin/plugin.json`) | skills, agents, hooks, MCP servers, LSP, monitors | `--plugin-dir` / `--plugin-url` for local testing, or marketplace install |
| VS Code Copilot | `plugin.json` | skills, agents, hooks, MCP servers | Workspace or user-level plugin install via Agent Plugins UI / source install |
| APM | `apm.yml` source, `apm pack` emits plugin-format bundle (`plugin.json`) | skills, agents, hooks, MCP servers, prompts (packaging primitive set) | `apm pack` to produce bundle, `apm install` to consume |

Claude-format `plugin.json` content is largely portable to VS Code for overlapping component types. Keep Claude-only components (for example LSP/monitors) isolated or optional when targeting both platforms.

## Plugin Manifest Schema (`plugin.json`)

Treat this section as a structural map. Do not hardcode full schema copies in local docs.

Core identity fields:

- `name` (required): plugin identifier and namespace anchor.
- `version` (recommended): semantic version for release and update control.
- `description` (recommended): concise intent and scope.

Common component path/config fields:

- `skills`: path(s) to skill directories.
- `agents`: path(s) to agent files/directories.
- `hooks`: hook config path or object, depending on format.
- `mcpServers`: MCP config path or object.

Other commonly encountered metadata:

- `author`, `license`, `homepage`, `repository`, `keywords`.
- Marketplace-facing metadata can appear in marketplace descriptors rather than only plugin manifest.

Variable substitution and runtime roots:

- `${CLAUDE_PLUGIN_ROOT}`: Claude-format plugin root token used by Claude and recognized by VS Code in Claude-compatible plugins.
- `${PLUGIN_ROOT}`: OpenPlugin-style root token where supported.
- Runtime env vars may also be injected (for example `CLAUDE_PLUGIN_ROOT`) for hooks/MCP server processes.

> Prefer plugin root tokens over absolute paths. Plugin install locations differ by platform, scope, and marketplace source.

For full field definitions and constraints, see the platform references:

- [Claude plugins reference](https://code.claude.com/docs/en/plugins-reference)
- [VS Code agent plugins](https://code.visualstudio.com/docs/agent-customization/agent-plugins)

## Component Types

### Skills directory plugins

- Package skills under `skills/<skill-name>/SKILL.md`.
- Use plugin namespacing behavior where required by runtime.
- Include scripts/resources next to the skill when needed.

### Agent bundles

- Package one or more `*.agent.md` files under `agents/`.
- Keep agent tool policies explicit in each agent file.

### Hook definitions

- Include hook configuration plus referenced scripts.
- Respect each runtime's supported hook event set and precedence behavior.

### MCP server declarations

- Bundle `.mcp.json` or inline `mcpServers` definitions in manifest.
- Use plugin root variables for command paths, cwd, and config paths.

### LSP and monitor components

- LSP and background monitor plugin components are Claude Code plugin features.
- Treat them as Claude-specific extensions when building cross-tool plugins.

## Distribution Models

### Local development

- Claude Code: load via `--plugin-dir` for fast iteration.
- VS Code: install plugin from source or marketplace while developing.
- Use local installs to validate hooks, MCP startup, and component discovery.

### Marketplace distribution

- Publish via marketplace indexes (`marketplace.json`) and versioned entries.
- Common source types include a relative path (same-repo, resolved from the marketplace root), `github`, `url`, `git-subdir`, and `npm`.
- Use pinned versions/refs and dependency constraints for reproducibility.

### APM packaging

- `apm pack` produces a plugin-format distributable bundle (`plugin.json` + component directories + lock/integrity metadata), consumed with `apm install`.
- `apm pack` ALSO generates the marketplace index from a `marketplace:` block in `apm.yml` — emitting `.claude-plugin/marketplace.json` (Claude) and, when `outputs` includes `codex`, `.agents/plugins/marketplace.json`. The marketplace is NOT authored/hosted out-of-band; APM builds it. `apm marketplace init` scaffolds the block, `apm marketplace check` validates entries resolve, and `claude plugin validate .` checks the emitted manifest.

### Consumer reach and fidelity (verified against Claude Code 2.1.205 / claude.ai Cowork)

A Claude plugin marketplace reaches **Claude Code CLI, the Claude Desktop app, and claude.ai's Cowork surface** — *"Plugins are available in Cowork and Code. They aren't used in Chat."* It does NOT reach claude.ai **Chat** (use uploaded/org-provisioned Custom Skills there) or **hosted ChatGPT** (a separate Custom-GPT/Actions ecosystem).

- **Cowork "Add marketplace"** takes a **Git repository** (`owner/repo` or an `https://…` git URL; GitLab/Bitbucket public too) — NOT a GitHub Pages / static `marketplace.json` URL (that is Claude Code CLI-only), and its UI exposes **no branch field** (tracks the default branch; pin versions at the plugin-source level instead).
- **A plugin install is reduced-fidelity vs. `apm install`.** It carries **skills** (`skills` field accepts a directory) and **commands** (`commands` field; APM renames `*.prompt.md` → `*.prompt`). It does NOT carry **instructions** (no plugin component — `apm pack` copies them in but Claude ignores them) or **MCP servers** (`apm pack` drops them). **Agents** load only from a default `agents/` directory at the plugin root — the `agents` field itself does not load them; point a real `agents/` dir (or symlink) at them, or ship agents via `apm install`. Use `apm install` for full-fidelity deploys (instructions + MCP + agents).

### Private/managed marketplaces

- Use strict/allowlist policies to limit approved marketplace sources.
- Validate manifests and enforce provenance before rollout.
- Prefer internal review gates for plugins with hooks/MCP executables.

> Plugins can execute code through hooks and MCP servers. Treat plugin installation as code execution trust, not just metadata import.

## Local Development Workflow

### Minimal plugin structure

```text
my-plugin/
  .claude-plugin/
    plugin.json
  skills/
    my-skill/
      SKILL.md
  agents/
    helper.agent.md
  hooks/
    hooks.json
  .mcp.json
  scripts/
    run-check.sh
```

### Suggested workflow

1. Start with the smallest vertical slice (manifest + one skill).
2. Load locally (`--plugin-dir` or equivalent install-from-source flow).
3. Verify component discovery (skills, agents, hooks, MCP servers).
4. Run reload cycle after edits (`/reload-plugins` or host equivalent).
5. Validate behavior with representative tasks and failure cases.
6. Package only after local validation passes.

### Debugging plugin load issues

- Validate manifest path and required fields first.
- Confirm every configured component path exists and is relative.
- Check for format mismatches (`.claude-plugin/plugin.json` vs root `plugin.json`).
- Use platform diagnostics/doctor commands for plugin errors.
- Verify hook/MCP scripts have executable permissions where required.

### Runtime environment variables

Commonly relevant runtime variables include:

- `CLAUDE_PLUGIN_ROOT` / `${CLAUDE_PLUGIN_ROOT}` for Claude-format plugin paths.
- `${PLUGIN_ROOT}` for formats that define it.

Always check current platform docs for exact availability and expansion rules.

## APM Integration

APM is a producer/consumer packaging workflow that can emit plugin-format bundles.

How `apm.yml` relates to `plugin.json`:

- `apm.yml` is the authoring manifest used by APM workflows.
- `apm pack` can synthesize or include plugin identity metadata in emitted bundle output.
- Core fields typically map cleanly (`name`, `version`, `description`, plus metadata fields).

Using `apm pack`:

- Build distributable plugin bundle artifacts from source primitives.
- Use dry-run/preview style checks before publishing.
- Ship archives or directories depending on consumer workflow.

Package types and when they matter:

- Skill package: focused single-skill distribution.
- Hook package: hook-only distribution.
- Plugin collection (`plugin.json`): multi-component plugin layout.
- APM package (`.apm/`) and skill collection layouts are useful producer forms but may install differently by target.

When to use APM vs direct `plugin.json` authoring:

- Use direct plugin authoring for quick local plugin iteration.
- Use APM when you need repeatable bundle builds, dependency handling, integrity metadata, and marketplace publishing workflows.

## Quality Checklist

- Manifest contains required identity fields and valid naming.
- Component paths are valid, relative, and exist.
- Plugin is tested locally before any distribution step.
- No absolute paths or user-home hardcoding in configs/scripts.
- Variable substitution is used for portable paths.
- Versioning follows semver and is bumped for publishable changes.
- Description clearly states scope, behavior, and intended usage.
- Hooks/MCP components were reviewed as executable trust boundaries.
- Bundle does not flood the consumer's skill-discovery budget.

## Anti-Patterns

- Bundling unrelated domains in one plugin instead of focused packages.
- Hardcoding absolute paths instead of `${PLUGIN_ROOT}` or `${CLAUDE_PLUGIN_ROOT}`.
- Shipping content changes without a version bump.
- Duplicating components that should be shared via APM dependencies.
- Overloading plugin docs with copied full schemas that quickly drift from upstream.

## Reference Links

- [Claude plugins guide](https://code.claude.com/docs/en/plugins)
- [Claude plugins reference](https://code.claude.com/docs/en/plugins-reference)
- [Claude plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)
- [VS Code agent plugins](https://code.visualstudio.com/docs/agent-customization/agent-plugins)
- [APM pack a bundle](https://microsoft.github.io/apm/producer/pack-a-bundle/)
- [APM package types](https://microsoft.github.io/apm/reference/package-types/)
