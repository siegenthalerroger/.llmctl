---
name: "setup-mcp"
description: "Converts MCP server definitions into an apm.yml dependencies.mcp block with secrets externalized to ${VAR}. ALWAYS invoke when asked to add or wire an MCP server into this repo from pasted config or an mcp.json path. Do not generate the per-tool files (.vscode/mcp.json, .mcp.json, .codex/config.toml) — emit only the APM block and let deploy produce them."
agent: agent
argument-hint: "paste MCP server definitions or a path to an mcp.json"
# Claude Code fields
skills: ['meta-harness']
---

Convert the MCP server definitions in `${input:servers:paste server config or an mcp.json path}` into an APM `dependencies.mcp` block for [apm.yml](../../../../apm.yml).

Load the [meta-harness skill](../skills/meta-harness/SKILL.md) for the schema, transport rules, and the cross-tool config matrix. **Do not generate per-tool files** (`.vscode/mcp.json`, `.mcp.json`, `.codex/config.toml`) — APM produces those on deploy.

## Steps

1. **Parse the input.** Accept a VS Code `mcp.json` (`servers` key), a Claude `.mcp.json` (`mcpServers` key), a path to either, or a loose list. If empty or unparseable, ask for the definitions and stop.
2. **Map each server** to an `apm.yml` entry per the [mcp-configuration.md](../skills/meta-harness/references/mcp-configuration.md): `name`, `registry: false`, `transport` (infer `stdio` from `command`, `http`/`sse` from `url`), plus `command`/`args`/`env` or `url`/`headers`.
3. **Externalize every secret** to a `${VAR}` placeholder. Convert VS Code `${input:...}` references to `${VAR}` env form. Never emit a plaintext key.

## Output

- A single fenced `yaml` block ready to paste under `dependencies.mcp` in [apm.yml](../../../../apm.yml).
- A short list of the `${VAR}` secrets the block references — APM prompts for each value at `apm install` time (no `.env` file to maintain).
- A one-line flag for any secret that appeared in plaintext in the input (rotate it).

End with the reminder: run `apm install -g` and verify the generated per-target config before relying on it.
