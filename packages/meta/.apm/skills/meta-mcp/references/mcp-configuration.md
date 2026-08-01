# MCP Server Configuration Reference

Detailed per-tool schemas for Model Context Protocol (MCP) servers. For the decision criteria, APM-first rule, and authoring checklist, see the [SKILL.md](../SKILL.md).

The same MCP server can be described once in `apm.yml` and deployed to every tool below. This reference documents both the **APM source form** and each tool's **native form**, so you can author for APM, read generated output, or configure a tool by hand.

## Config matrix

| Tool | File | Scope | Format | Root key |
|---|---|---|---|---|
| **APM** (source of truth) | `apm.yml` | package | YAML | `dependencies.mcp` (list) |
| **VS Code Copilot** | `.vscode/mcp.json` (project) · profile `mcp.json` (user) | project / user | JSON | `servers` |
| **Claude Code** | `.mcp.json` (project) · `~/.claude.json` (user) | project / user | JSON | `mcpServers` |
| **Copilot CLI** | `~/.copilot/mcp-config.json` | user | JSON | `mcpServers` |
| **OpenAI Codex CLI** | `.codex/config.toml` (project) · `~/.codex/config.toml` (user) | project / user | TOML | `[mcp_servers.<name>]` |

Sources: [VS Code MCP](https://code.visualstudio.com/docs/copilot/chat/mcp-servers), [Claude Code MCP](https://code.claude.com/docs/en/mcp), [Codex CLI MCP](https://developers.openai.com/codex/mcp), [APM MCP guide](https://microsoft.github.io/apm/guides/mcp-servers/).

> **The load-bearing difference:** VS Code uses the root key `servers`; Claude Code, Copilot CLI, and Cursor use `mcpServers`; Codex uses TOML tables `[mcp_servers.<name>]`. A correct config under the wrong key is silently ignored.

## APM source form (`apm.yml`)

`dependencies.mcp` is a list. Each entry is one of three forms:

**(A) Registry string reference** — resolves from the MCP server registry:

```yaml
dependencies:
  mcp:
    - io.github.github/github-mcp-server
```

**(B) Self-defined stdio server** — a local process APM/the harness launches:

```yaml
    - name: ddg-search
      registry: false
      transport: stdio
      command: uvx
      args: ["duckduckgo-mcp-server"]
      env:
        SOME_TOKEN: "${SOME_TOKEN}"   # optional; verify inline-stdio env: support on deploy
```

**(C) Self-defined remote server** — an HTTP/SSE endpoint:

```yaml
    - name: microsoft.docs.mcp
      registry: false
      transport: http        # http | sse | streamable-http
      url: https://learn.microsoft.com/api/mcp
      headers:
        Authorization: "Bearer ${SOME_TOKEN}"   # optional
```

Field notes:
- `registry: false` marks a self-defined (inline) server; omit it for registry references.
- `transport` is `stdio` | `http` | `sse` | `streamable-http`. If omitted, APM infers `stdio` from `command` and `http` from `url`.
- Env placeholders use `${VAR}` grammar and are resolved from the environment at deploy — never written to disk in plaintext.

## Native form: VS Code Copilot (`.vscode/mcp.json`)

Root key `servers`. Each server carries a `type` (`stdio` | `http` | `sse`). Supports an `inputs` array for `${input:...}` prompts (VS-Code-specific).

```jsonc
{
  "servers": {
    "ddg-search": {
      "type": "stdio",
      "command": "uvx",
      "args": ["duckduckgo-mcp-server"]
    },
    "microsoft.docs.mcp": {
      "type": "http",
      "url": "https://learn.microsoft.com/api/mcp"
    },
    "brave-search-mcp-server": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@brave/brave-search-mcp-server", "--transport", "stdio"],
      "env": { "BRAVE_API_KEY": "${input:brave-api-key}" }
    }
  },
  "inputs": [
    { "id": "brave-api-key", "type": "promptString", "description": "Brave Search API Key", "password": true }
  ]
}
```

## Native form: Claude Code (`.mcp.json` / `~/.claude.json`)

Root key `mcpServers`. Same `type`/`command`/`args`/`url`/`headers`/`env` shape, but **no `inputs` mechanism** — use `${VAR}` env references for secrets.

```jsonc
{
  "mcpServers": {
    "ddg-search": {
      "type": "stdio",
      "command": "uvx",
      "args": ["duckduckgo-mcp-server"]
    },
    "context7": {
      "type": "http",
      "url": "https://mcp.context7.com/mcp",
      "headers": { "CONTEXT7_API_KEY": "${CONTEXT7_API_KEY}" }
    }
  }
}
```

## Native form: OpenAI Codex CLI (`.codex/config.toml`)

TOML table per server: `[mcp_servers.<name>]`. stdio uses `command`/`args`/`env`; remote uses `url`.

```toml
[mcp_servers.ddg-search]
command = "uvx"
args = ["duckduckgo-mcp-server"]

[mcp_servers.context7]
url = "https://mcp.context7.com/mcp"
[mcp_servers.context7.env]
CONTEXT7_API_KEY = "${CONTEXT7_API_KEY}"
```

## Secrets

The only acceptable secret form in a tracked file is a placeholder. But the placeholder syntax and *who resolves it* differ per tool, so the value must reach the right environment.

| Layer | Syntax | Resolved by / when |
|---|---|---|
| `apm.yml` (source) | `${VAR}` | APM on `apm install` — either bakes the value into each generated file, or passes the placeholder through (version-dependent; **inspect the output**). |
| Claude Code `.mcp.json` | `${VAR}`, `${VAR:-default}` | Claude Code, from its own process env at launch. Expandable in `command`/`args`/`env`/`url`/`headers`. **Unset + no default → Claude fails to parse the config.** |
| VS Code `mcp.json` | `${input:ID}` (+ `inputs`/`password`) or `${env:VAR}` | VS Code, at server start. Bare `${VAR}` is not native here. |
| Codex `config.toml` | `${VAR}` env reference | Codex, from its process env. |

Key points:
- **APM prompts for secrets at `apm install` time** — it resolves each `${VAR}` it can't read from the environment and writes the value into the generated per-target config. No `.env` file is maintained in this repo.
- For non-interactive runs (CI), export the vars first (`set -a; source <file>; set +a`, a shell profile, or direnv) so APM finds them without prompting.
- A key committed or pasted in plaintext is compromised — rotate and revoke it.

## Recommended layout for this repo

1. Author every server in [`packages/core/apm.yml`](../../../../../../packages/core/apm.yml) under `dependencies.mcp`.
2. Externalize all secrets to `${VAR}`; APM prompts for each value on install.
3. Run `apm install -g` to deploy; do not commit the generated `.vscode/mcp.json` / `.mcp.json` / `config.toml`.
4. Keep server `name`s aligned with how agents refer to them. No agent in this repo declares a `tools:` array (a Copilot-style array makes Claude Code refuse to spawn the agent — see the [meta-agent skill](../../meta-agent/SKILL.md)), so the alignment that matters is prose: an agent body naming a server (`context7`, `opentofu-registry`) must use the name declared here.
