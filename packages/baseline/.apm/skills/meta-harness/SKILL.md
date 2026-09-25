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
      - "https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/use-hooks"
      - "https://docs.github.com/en/copilot/reference/hooks-reference"
      - "https://learn.chatgpt.com/docs/hooks"
      - "https://microsoft.github.io/apm/producer/author-primitives/hooks-and-commands/"
      # MCP servers — apm.yml dependencies.mcp, per-target mcp.json
      - "https://code.claude.com/docs/en/mcp"
      - "https://code.visualstudio.com/docs/agent-customization/mcp-servers"
      - "https://learn.chatgpt.com/docs/extend/mcp"
      - "https://microsoft.github.io/apm/consumer/install-mcp-servers/"
      - "https://microsoft.github.io/apm/producer/author-primitives/mcp-as-primitive/"
      # Plugins — plugin.json, bundle layout
      - "https://code.claude.com/docs/en/plugins"
      - "https://code.claude.com/docs/en/plugins-reference"
      - "https://code.visualstudio.com/docs/agent-customization/agent-plugins"
      - "https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-plugin-reference"
      - "https://agent-plugins.org/plugin-authors/manifest"
      - "https://learn.chatgpt.com/docs/build-plugins"
      - "https://developers.openai.com/plugins/build/plugins"
      # Packaging and marketplace distribution
      - "https://code.claude.com/docs/en/plugin-marketplaces"
      - "https://microsoft.github.io/apm/producer/pack-a-bundle/"
      - "https://microsoft.github.io/apm/reference/package-types/"
      - "https://microsoft.github.io/apm/reference/targets-matrix/"
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

**Verify enforcement in the runtime.** A hook provides a lifecycle entry point, not a universal blocking guarantee: trust, supported decisions, failures and timeouts differ by harness. Codex skips untrusted non-managed definitions; Copilot hook timeouts fail open. Use deterministic code for hard checks and test the rejection path. Prompt/agent hook decisions still depend on a model. See [hooks.md](./references/hooks.md).

Do not use a hook to steer behaviour, and do not add an MCP server for a capability a built-in tool already covers.

## 2) Route to the detail

| Authoring | Read |
|---|---|
| `*.hook.json`, `hooks:` frontmatter, `.apm/hooks/`, `settings.json` | [hooks.md](./references/hooks.md) |
| `dependencies.mcp` in `apm.yml`, `.mcp.json`, `.vscode/mcp.json`, `.codex/config.toml` | [mcp.md](./references/mcp.md), then [mcp-configuration.md](./references/mcp-configuration.md) for the full per-tool schema matrix |
| `plugin.json`, bundle layout, marketplace entries | [plugins.md](./references/plugins.md) |

## 3) APM-first — one declaration, every target

This repo deploys via APM. **Declare each MCP server once in `apm.yml` under `dependencies.mcp`, and author hooks once in `.apm/hooks/`.** APM translates both into every target's native config on deploy.

Per-target files are machine-generated output, not source. Never hand-maintain `.vscode/mcp.json`, `.mcp.json`, `.github/mcp.json`, `~/.copilot/mcp-config.json`, or `.codex/config.toml` — editing them creates a second source of truth that silently drifts.

**APM translates steering frontmatter too, and lossily.** Agents and skills reach Claude and Copilot verbatim; prompts deployed as Claude commands keep five keys; Claude rules get `paths` rebuilt from `applyTo`; Codex gets TOML agents and no prompts. A dropped-keys warning describes the deployer, not the authoring standard: author against the harness spec and see [meta-steering's deploy matrix](../meta-steering/references/frontmatter-deploy.md).

The load-bearing trap when reading generated output: **`.vscode/mcp.json` uses the `servers` root key; `.mcp.json` and the other JSON targets use `mcpServers`.** VS Code also reads a workspace-root `.mcp.json` with `mcpServers`, so the key follows the file, not the harness. Wrong key means the config is silently ignored. The per-file matrix is in [mcp-configuration.md](./references/mcp-configuration.md#config-matrix).

> **Verify the deploy.** APM's MCP support is still maturing and behavior varies by target and scope. Inspect generated files for the intended deployment scope, then verify native discovery, hook trust and rejection behavior before relying on enforcement. A successful install alone does not establish runtime behavior.

## 4) Secrets

> Never commit a plaintext API key, token or password. The only acceptable form in a tracked file is a placeholder.

- Author secrets as `${VAR}` placeholders in `headers` / `env` in `apm.yml` — that is APM's grammar. No `.env` file is maintained here.
- What reaches each generated file differs by target: kept as a placeholder, baked in as the literal value at install, or — for Codex remote headers in APM 0.31 — written where Codex never expands it. Inspect the generated files; the per-target table is in [mcp-configuration.md](./references/mcp-configuration.md#secrets).
- A key that was ever committed or pasted in plaintext is compromised: rotate it and revoke the old one.

## 5) Tool-surface and discovery budgets

Both MCP servers and plugin bundles spend a budget belonging to the consumer, not the author.

- **Exposed tool count degrades tool selection.** Add servers sparingly and disable unused tools; the evidence and curation rules are in [mcp.md](./references/mcp.md#curating-servers-and-tools).
- **Every bundled skill competes in the consumer's discovery budget.** Design the whole installed listing to about **8,000 chars** (names, descriptions and, for Codex, paths) — a conservative house target, not a portable ceiling; overflow behaviour differs per harness ([meta-steering's budget table](../meta-steering/SKILL.md#context-budget--four-distinct-surfaces)).

## 6) This repository's conventions

**Hook filenames.** This repo names APM source files `*.hook.json` for parity with the other primitives; APM and Copilot folder discovery accept `*.json`. Native paths remain harness-specific: Claude reads settings, Codex reads fixed `hooks.json` files at config layers or inline hooks, and plugin formats have their own locations. The source naming convention does not override those contracts.

**Hook scripts are cross-platform.** Prefer Python or Node over shell or PowerShell; document the runtime where a shell is genuinely required.

**Scope packaging caveats to the format.** The default APM Claude bundle is reduced-fidelity (no instructions, no `apm.yml` MCP), and `--format agent-plugin` carries only skills and MCP; `apm install` remains the full deploy. Consuming an Agent Plugins v1 package through `apm install` registers it only for the `copilot` target — under `targets: [claude, codex]` it is skipped, and since APM 0.31 the install exits 1 if nothing else deploys. Per-format detail is in [plugins.md](./references/plugins.md#consumer-reach-and-fidelity).

**Copilot authoring baseline.** In this repo the APM canonical hook form in `.apm/hooks/` is the source for every target, Copilot included. The Copilot CLI hook and plugin contracts are the baseline only when hand-authoring Copilot config outside APM; keep VS Code Local and cloud differences as compatibility notes.

**Plugin installation is code execution.** Hooks and MCP servers in a bundle run arbitrary commands — review them as a trust boundary, not as metadata import.

## References

- [hooks.md](./references/hooks.md) · [mcp.md](./references/mcp.md) · [plugins.md](./references/plugins.md) — the per-type guides
- [mcp-configuration.md](./references/mcp-configuration.md) — full per-tool MCP schema matrix
- [`meta-steering`](../meta-steering/SKILL.md) — skills, agents, instructions, prompts, and the full type-selection table
- **Hooks** — [Claude Code](https://code.claude.com/docs/en/hooks) · [Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/use-hooks) · [VS Code](https://code.visualstudio.com/docs/agent-customization/hooks) · [Codex](https://learn.chatgpt.com/docs/hooks) · [APM hooks and commands](https://microsoft.github.io/apm/producer/author-primitives/hooks-and-commands/)
- **MCP servers** — [Claude Code](https://code.claude.com/docs/en/mcp) · [VS Code](https://code.visualstudio.com/docs/agent-customization/mcp-servers) · [Codex](https://learn.chatgpt.com/docs/extend/mcp) · [APM MCP guide](https://microsoft.github.io/apm/consumer/install-mcp-servers/)
- **Plugins and packaging** — [Claude plugins reference](https://code.claude.com/docs/en/plugins-reference) · [Claude marketplaces](https://code.claude.com/docs/en/plugin-marketplaces) · [VS Code agent plugins](https://code.visualstudio.com/docs/agent-customization/agent-plugins) · [APM pack a bundle](https://microsoft.github.io/apm/producer/pack-a-bundle/)
