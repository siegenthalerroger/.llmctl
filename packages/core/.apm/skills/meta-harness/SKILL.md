---
name: "meta-harness"
description: "Authoring guide for the config an agent harness executes or installs: lifecycle hooks (*.hook.json, PreToolUse/PostToolUse/SessionStart matchers), MCP servers (apm.yml dependencies.mcp, stdio/http/sse transports, ${VAR} secrets) and plugin bundles (plugin.json, marketplace, apm pack). ALWAYS load before adding or editing one of those, and when deciding whether a rule must be made deterministic rather than left as prose. Do not hand-maintain per-target MCP config files, invent a hook event name from recall, or bundle skills without checking the consumer's discovery budget. Does not cover authoring skills, agents, instructions or prompts — see meta-steering. Keywords: hook, lifecycle, PreToolUse, PostToolUse, matcher, MCP, mcpServers, dependencies.mcp, transport, stdio, http, sse, secret, plugin, plugin.json, marketplace, bundle, APM."
metadata:
  provenance:
    authoritativeSpec:
      # Hooks — *.hook.json, hooks: frontmatter
      - "https://code.claude.com/docs/en/hooks"
      - "https://code.claude.com/docs/en/hooks-guide"
      - "https://code.visualstudio.com/docs/agent-customization/hooks"
      - "https://microsoft.github.io/apm/producer/author-primitives/hooks-and-commands/"
      # MCP servers — apm.yml dependencies.mcp, per-target mcp.json
      - "https://code.claude.com/docs/en/mcp"
      - "https://code.visualstudio.com/docs/agent-customization/mcp-servers"
      - "https://learn.chatgpt.com/docs/extend/mcp"
      - "https://microsoft.github.io/apm/guides/mcp-servers/"
      - "https://microsoft.github.io/apm/producer/author-primitives/mcp-as-primitive/"
      # Plugins — plugin.json, bundle layout
      - "https://code.claude.com/docs/en/plugins"
      - "https://code.claude.com/docs/en/plugins-reference"
      - "https://code.visualstudio.com/docs/agent-customization/agent-plugins"
      # Packaging and marketplace distribution
      - "https://code.claude.com/docs/en/plugin-marketplaces"
      - "https://microsoft.github.io/apm/producer/pack-a-bundle/"
      - "https://microsoft.github.io/apm/reference/package-types/"
---

# Authoring Harness Config

Covers the three artifacts a harness **executes or installs**: lifecycle hooks, MCP servers, plugin bundles. None of them is a steering mechanism.

## 1) Is it actually harness config?

If the artifact is not something the harness runs or installs, it belongs in [`meta-steering`](../meta-steering/SKILL.md) — that skill also carries the [full seven-way type-selection table](../meta-steering/SKILL.md#1-pick-the-customization-type-first).

| It is harness config when | It is steering when |
|---|---|
| Code must run at a lifecycle boundary, independent of model judgment → **hook** | The model should be *taught* a preference, style or process → instruction or skill |
| The agent needs a capability it does not have — an API, registry, browser, docs lookup → **MCP server** | The capability exists and only the approach needs shaping → skill |
| Several components need one versioned install surface → **plugin** | A single capability stands alone → skill or agent |

**The escalation gate, from the other side.** Autonomous skill and instruction triggering is probabilistic. When something must happen *every* time, that is a hook — not stronger description prose. Arriving here from [`meta-steering`](../meta-steering/SKILL.md#1-pick-the-customization-type-first) for that reason is the expected path.

Do not use a hook to steer behaviour, and do not add an MCP server for a capability a built-in tool already covers.

## 2) Route to the detail

| Authoring | Read |
|---|---|
| `*.hook.json`, `hooks:` frontmatter, `.apm/hooks/`, `settings.json` | [hooks.md](./references/hooks.md) |
| `dependencies.mcp` in `apm.yml`, `.mcp.json`, `.vscode/mcp.json`, `.codex/config.toml` | [mcp.md](./references/mcp.md), then [mcp-configuration.md](./references/mcp-configuration.md) for the full per-tool schema matrix |
| `plugin.json`, bundle layout, marketplace entries | [plugins.md](./references/plugins.md) |

## 3) APM-first — one declaration, every target

This repo deploys via APM. **Declare each MCP server once in `apm.yml` under `dependencies.mcp`, and author hooks once in `.apm/hooks/`.** APM translates both into every target's native config on deploy.

Per-target files are machine-generated output, not source. Never hand-maintain `.vscode/mcp.json`, `.mcp.json`, `~/.copilot/mcp-config.json`, or `.codex/config.toml` — editing them creates a second source of truth that silently drifts.

The load-bearing trap when reading generated output: **VS Code uses the `servers` root key; every other target uses `mcpServers`.** Wrong key means the config is silently ignored.

> **Verify the deploy.** APM's MCP support is still maturing and user-scope (`apm install -g`) behaviour varies by version. Treat MCP and hook wiring as authored-pending-verification — run `apm install -g` and inspect the generated per-target files before relying on either.

## 4) Secrets

> Never commit a plaintext API key, token or password. The only acceptable form in a tracked file is a placeholder.

- Author secrets as `${VAR}` placeholders in `headers` / `env` in `apm.yml` — that is APM's grammar.
- APM resolves the value at `apm install` time, prompting for anything it cannot read from the environment, and writes the resolved value into each generated config. No `.env` file is maintained here.
- Resolution differs per target, which is why the generated files need checking: Claude Code expands `${VAR}` and `${VAR:-default}` from its own process environment and **fails to parse** the config when a required var is unset with no default. VS Code's native form is `${input:ID}` or `${env:VAR}` — bare `${VAR}` is not.
- A key that was ever committed or pasted in plaintext is compromised: rotate it and revoke the old one.

## 5) Tool-surface and discovery budgets

Both MCP servers and plugin bundles spend a budget belonging to the consumer, not the author.

- **Exposed tool count degrades selection accuracy** — a mid-size model that fails at 46 available tools passes at 19. Add servers sparingly, disable unused tools where the harness allows it, and prefer purpose-revealing namespaced tool names (`service_resource_verb`). Never restate a tool's schema in prose; it interferes with autonomous selection.
- **Every bundled skill's `description` competes in the consumer's skill-discovery budget** — Claude Code totals ~15,000 chars across all loaded skills and skills past that cutoff become *invisible*, not down-ranked. Keep bundles cohesive and descriptions short. `SLASH_COMMAND_TOOL_CHAR_BUDGET` is consumer-side relief an author cannot assume.

## 6) This repository's conventions

**Hook filenames.** Standalone hook files are matched by glob (`*.json`), not by a fixed name, so this repo names them `*.hook.json` for parity with `*.agent.md` / `*.prompt.md` / `*.instructions.md`. It is a strict subset of `*.json`, so VS Code folder discovery and APM still find them, and Claude Code is unaffected because it reads hooks from `settings.json` rather than scanning the directory. The fixed names `hooks.json` / `hooks/hooks.json` apply only *inside plugin bundles*.

**Hook scripts are cross-platform.** Prefer Python or Node over shell or PowerShell; document the runtime where a shell is genuinely required.

**The plugin path is reduced-fidelity; `apm install` is the full deploy.** Treat **skills** and **commands** (prompts) as the only primitives that reliably reach a marketplace consumer. Instructions are copied but ignored; MCP servers are dropped; agents load only from a default `agents/` directory at the bundle root. Use `apm install` wherever those matter.

**Plugin installation is code execution.** Hooks and MCP servers in a bundle run arbitrary commands — review them as a trust boundary, not as metadata import.

## References

- [hooks.md](./references/hooks.md) · [mcp.md](./references/mcp.md) · [plugins.md](./references/plugins.md) — the per-type guides
- [mcp-configuration.md](./references/mcp-configuration.md) — full per-tool MCP schema matrix
- [`meta-steering`](../meta-steering/SKILL.md) — skills, agents, instructions, prompts, and the full type-selection table
- **Hooks** — [Claude Code](https://code.claude.com/docs/en/hooks) · [VS Code](https://code.visualstudio.com/docs/agent-customization/hooks) · [APM hooks and commands](https://microsoft.github.io/apm/producer/author-primitives/hooks-and-commands/)
- **MCP servers** — [Claude Code](https://code.claude.com/docs/en/mcp) · [VS Code](https://code.visualstudio.com/docs/agent-customization/mcp-servers) · [Codex](https://learn.chatgpt.com/docs/extend/mcp) · [APM MCP guide](https://microsoft.github.io/apm/guides/mcp-servers/)
- **Plugins and packaging** — [Claude plugins reference](https://code.claude.com/docs/en/plugins-reference) · [Claude marketplaces](https://code.claude.com/docs/en/plugin-marketplaces) · [VS Code agent plugins](https://code.visualstudio.com/docs/agent-customization/agent-plugins) · [APM pack a bundle](https://microsoft.github.io/apm/producer/pack-a-bundle/)
