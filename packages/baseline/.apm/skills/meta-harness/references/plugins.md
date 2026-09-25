# Plugin Authoring and Packaging Guidelines

**Contents:** [When to Use Plugins](#when-to-use-plugins) · [Cross-Tool Compatibility](#cross-tool-compatibility) · [Plugin Manifest Schema (`plugin.json`)](#plugin-manifest-schema-pluginjson) · [Component Types](#component-types) · [Distribution Models](#distribution-models) · [Local Development Workflow](#local-development-workflow) · [Quality Checklist](#quality-checklist) · [Anti-Patterns](#anti-patterns) · [Reference Links](#reference-links)

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

Every bundled skill spends the consumer's shared discovery budget — design the installed listing to about 8,000 chars and front-load descriptions ([meta-steering's budget table](../../meta-steering/SKILL.md#context-budget--four-distinct-surfaces)).

## Cross-Tool Compatibility

| Platform | Manifest | Components supported | Installation |
| --- | --- | --- | --- |
| Claude Code | `plugin.json` (typically `.claude-plugin/plugin.json`) | skills, commands, agents, hooks, MCP servers, LSP, monitors (output styles, themes experimental) | `--plugin-dir` / `--plugin-url` for local testing, or marketplace install |
| Codex / ChatGPT | Portable root `plugin.json` with `extensions.com.openai`; `.codex-plugin/plugin.json` remains compatible | skills, MCP, hooks, with runtime-specific support | Native plugin discovery/install surfaces; shared ChatGPT/Codex directory |
| Copilot CLI | Agent Plugins 1.0 root `plugin.json` | portable skills/MCP; Copilot agents, commands, rules, hooks and LSP via vendor extensions | Native CLI plugin install/discovery |
| VS Code Copilot | Agent Plugins 1.0 root `plugin.json`; Claude and legacy formats remain supported | portable skills/MCP; Copilot agents/hooks and other additions under `com.github.copilot/` and `extensions.com.github.copilot` | Agent Plugins UI / source install |
| APM | `apm.yml` source; `apm pack` defaults to `claude-plugin`, or `--format agent-plugin` | Claude bundle has Claude component layout; Agent Plugins 1.0 output carries only skills and MCP | `apm pack` produces a distributable. Consuming an Agent Plugins v1 package via `apm install` registers it only for the `copilot` target; since APM 0.31 the install exits 1 when that exclusion leaves nothing deployed |

The portable Agent Plugins 1.0 contract and each vendor's extensions are distinct from Claude-format compatibility. Keep runtime-specific components explicit. Supporting a format does not establish that every runtime executes every bundled component.

## Plugin Manifest Schema (`plugin.json`)

Treat this section as a structural map. Do not hardcode full schema copies in local docs; field definitions are in the [Reference Links](#reference-links).

### Portable Agent Plugins 1.0 and Vendor Extensions

Use the [canonical manifest schema](https://agent-plugins.org/plugin-authors/manifest) for root `plugin.json`, with `$schema: "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"`. Portable component discovery uses fixed `skills/` and `mcp.json` locations; do not copy Claude's component path fields into the portable manifest and assume equivalent behavior.

When hand-authoring Copilot content, use the [Copilot CLI plugin contract](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-plugin-reference) as the baseline. Its additions live under `com.github.copilot/` (`agents/`, `commands/`, `rules/`, `hooks/hooks.json`, `lsp.json`), with manifest metadata in `extensions.com.github.copilot`. VS Code supports this format alongside Claude and legacy compatibility formats; verify [VS Code's runtime support](https://code.visualstudio.com/docs/agent-customization/agent-plugins) independently. OpenAI's portable manifest additions live under `extensions.com.openai`; Codex also accepts the compatibility `.codex-plugin/plugin.json` format ([OpenAI's plugin guide](https://developers.openai.com/plugins/build/plugins)). This is current authoring guidance, not a request to migrate existing repository bundles.

### Claude-Compatible Manifests

- Identity: `name` (required, the namespace anchor), `version`, `description`; optional `author`, `license`, `homepage`, `repository`, `keywords`. Marketplace-facing metadata can live in the marketplace entry instead.
- Component fields: `skills`, `agents`, `hooks`, `mcpServers` — paths, or (for `hooks`) an inline object or an array of paths. A custom `agents` list **replaces** the default `agents/` scan; list `./agents/` explicitly to keep it.

### Root tokens and runtime variables

| Token | Format | Resolves to |
|---|---|---|
| `${CLAUDE_PLUGIN_ROOT}` | Claude (also expanded by VS Code for Claude/Copilot formats) | Plugin install directory |
| `${CLAUDE_PLUGIN_DATA}` | Claude | Persistent per-plugin data directory that survives updates |
| `${CLAUDE_PROJECT_DIR}` | Claude | Project root |
| `${PLUGIN_ROOT}` / `${PLUGIN_DATA}` | Agent Plugins 1.0 (VS Code also accepts `${PLUGIN_ROOT}` in Claude/Copilot formats) | Plugin root / data directory |

Claude exports its three as environment variables to hook, MCP and LSP processes. Prefer root tokens over absolute paths; install locations differ by platform, scope, and marketplace source.

## Component Types

- **Skills:** `skills/<skill-name>/SKILL.md`, with scripts/resources beside the skill.
- **Agents:** `agents/` in Claude-compatible bundles; the vendor extension layout in portable bundles. Claude ignores `hooks`, `mcpServers`, `permissionMode` and `initialPrompt` on a plugin agent.
- **Hooks:** hook configuration plus the scripts it references; respect each runtime's event set.
- **MCP servers:** portable Agent Plugins use `mcp.json`; Claude-compatible bundles use `.mcp.json` or manifest `mcpServers`. Choose the declaration for the actual format.
- **LSP and monitors:** Claude Code plugin features; treat them as Claude-specific in cross-tool plugins.

## Distribution Models

### Local development

- Claude Code: load via `--plugin-dir` for fast iteration.
- VS Code: install plugin from source or marketplace while developing.
- Use local installs to validate hooks, MCP startup, and component discovery.

### Marketplace distribution

- Publish via marketplace indexes (`marketplace.json`) and versioned entries.
- Claude source types: a relative path (same repo, resolved from the marketplace root), `github`, `url`, `git-subdir`, `npm`, and in recent versions `archive` and `command` ([plugin sources](https://code.claude.com/docs/en/plugin-marketplaces)).
- Use pinned versions/refs (`ref`, `sha`) and dependency constraints for reproducibility.

### APM packaging

- `apm pack` defaults to a Claude-format bundle (`--format claude-plugin`). `apm pack --format agent-plugin` emits Agent Plugins 1.0 — root `plugin.json`, `skills/` and `mcp.json` only — and rejects primitives it cannot represent. This is an APM packaging limit, not a limit on native vendor extensions; inspect the [current pack contract](https://microsoft.github.io/apm/producer/pack-a-bundle/) before choosing the format.
- `apm pack` ALSO generates the marketplace index from a `marketplace:` block in `apm.yml` — emitting `.claude-plugin/marketplace.json` (Claude) and, when `outputs` includes `codex`, `.agents/plugins/marketplace.json`. The marketplace is NOT authored/hosted out-of-band; APM builds it. `apm marketplace init` scaffolds the block, `apm marketplace check` validates entries resolve, and `claude plugin validate .` checks the emitted manifest.
- Use APM over direct `plugin.json` authoring when you need repeatable builds, dependency handling and integrity metadata; direct authoring suits quick local iteration.

### Consumer reach and fidelity

Claude Code plugin facts last checked against 2.1.273; the Cowork behavior below was verified against 2.1.205 and not re-checked since. A Claude plugin marketplace reaches **Claude Code CLI, the Claude Desktop app, and claude.ai's Cowork surface** — *"Plugins are available in Cowork and Code. They aren't used in Chat."* It does not reach claude.ai **Chat** (use uploaded/org-provisioned Custom Skills there). OpenAI now has a native plugin ecosystem with a shared ChatGPT/Codex directory; a Claude marketplace alone does not establish publication there. Follow [OpenAI's build and distribution contract](https://developers.openai.com/plugins/build/plugins), and verify each component's availability in the consuming surface.

- **Cowork "Add marketplace"** takes a **Git repository** (`owner/repo` or an `https://…` git URL; GitLab/Bitbucket public too) — NOT a GitHub Pages / static `marketplace.json` URL (that is Claude Code CLI-only), and its UI exposes **no branch field** (tracks the default branch; pin versions at the plugin-source level instead).
- **A marketplace added by direct `marketplace.json` URL cannot use relative-path sources** — Claude Code downloads only that file, so relative paths do not resolve. Use `github`, `url`, `npm` or `archive` sources for URL-based distribution.
- **The default APM Claude bundle has reduced fidelity vs. `apm install`.** It carries **skills** (`skills` field accepts a directory) and **commands** (`commands` field; APM writes each `*.prompt.md` to `commands/` as `*.md`). It does NOT carry **instructions** (no plugin component — `apm pack` copies them in but Claude ignores them). **MCP servers** from `apm.yml` `dependencies.mcp` are not packed in this format; only a project-root `.mcp.json` is, with credentials stripped. **Agents** load from the plugin's `agents/` directory or the `agents` field, subject to the ignored fields listed under [Component Types](#component-types). Use `apm install` where native deployment is needed, and verify that the installed APM version preserves the required behavior. These caveats do not describe every native plugin format.

### Private/managed marketplaces

- Limit approved sources with managed settings (Claude: `strictKnownMarketplaces` allowlist, `blockedMarketplaces`).
- Validate manifests and enforce provenance before rollout.
- Prefer internal review gates for plugins with hooks/MCP executables.

> Plugins can execute code through hooks and MCP servers. Treat plugin installation as code execution trust, not just metadata import.

## Local Development Workflow

### Minimal Claude-Compatible Plugin Structure

```text
my-plugin/
  .claude-plugin/
    plugin.json
  skills/
    my-skill/
      SKILL.md
  agents/
    helper.md
  hooks/
    hooks.json
  .mcp.json
  scripts/
    run-check.py
```

### Suggested workflow

1. Start with the smallest vertical slice (manifest + one skill).
2. Load locally (`--plugin-dir` or equivalent install-from-source flow).
3. Verify component discovery (skills, agents, hooks, MCP servers).
4. After edits, run `/reload-plugins` for hooks, MCP and LSP; **restart the session** after skill, agent or monitor changes, which it does not reload.
5. Validate behavior with representative tasks and failure cases.
6. Package only after local validation passes.

### Debugging plugin load issues

- Validate manifest path and required fields first (`claude plugin validate .`).
- Confirm every configured component path exists and is relative.
- Check for format mismatches (`.claude-plugin/plugin.json` vs root `plugin.json`).
- Verify hook/MCP scripts have executable permissions where required.

## Quality Checklist

- Manifest contains required identity fields and valid naming.
- Component paths are valid, relative, and exist; root tokens used instead of absolute or user-home paths.
- Plugin is tested locally before any distribution step.
- Versioning follows semver and is bumped for publishable changes.
- Hooks/MCP components were reviewed as executable trust boundaries.
- Bundle does not flood the consumer's skill-discovery budget.

## Anti-Patterns

- Bundling unrelated domains in one plugin instead of focused packages.
- Shipping content changes without a version bump.
- Duplicating components that should be shared via APM dependencies.
- Overloading plugin docs with copied full schemas that quickly drift from upstream.

## Reference Links

- [Copilot CLI plugin reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-plugin-reference)
- [Claude plugins guide](https://code.claude.com/docs/en/plugins)
- [Claude plugins reference](https://code.claude.com/docs/en/plugins-reference)
- [Claude plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)
- [VS Code agent plugins](https://code.visualstudio.com/docs/agent-customization/agent-plugins)
- [Agent Plugins manifest](https://agent-plugins.org/plugin-authors/manifest)
- [Codex plugins](https://learn.chatgpt.com/docs/build-plugins)
- [OpenAI plugins](https://developers.openai.com/plugins/build/plugins)
- [APM pack a bundle](https://microsoft.github.io/apm/producer/pack-a-bundle/)
- [APM package types](https://microsoft.github.io/apm/reference/package-types/)
