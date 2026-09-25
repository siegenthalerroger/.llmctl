# MCP Server Configuration Reference

**Contents:** [Config Matrix](#config-matrix) · [APM Source Form (`apm.yml`)](#apm-source-form-apmyml) · [Native Form: VS Code Copilot (`.vscode/mcp.json`)](#native-form-vs-code-copilot-vscodemcpjson) · [Native Form: Claude Code (`.mcp.json` / `~/.claude.json`)](#native-form-claude-code-mcpjson--claudejson) · [Native Form: OpenAI Codex CLI (`.codex/config.toml`)](#native-form-openai-codex-cli-codexconfigtoml) · [Secrets](#secrets) · [Recommended Layout for This Repo](#recommended-layout-for-this-repo)

Detailed per-tool schemas for Model Context Protocol (MCP) servers. For the decision criteria, APM-first rule, and authoring checklist, see [mcp.md](./mcp.md).

The same MCP server can be described once in `apm.yml` and deployed to every tool below. This reference documents both the **APM source form** and each tool's **native form**, so you can author for APM, read generated output, or configure a tool by hand.

## Config Matrix

| Tool | File | Scope | Format | Root key |
|---|---|---|---|---|
| **APM** (source of truth) | `apm.yml` | package | YAML | `dependencies.mcp` (list) |
| **VS Code Copilot** | `.vscode/mcp.json` (project) · profile `mcp.json` (user) | project / user | JSON | `servers` |
| **VS Code Copilot** (portable) | workspace-root `.mcp.json` | project | JSON | `mcpServers` |
| **Claude Code** | `.mcp.json` (project) · `~/.claude.json` (user) | project / user | JSON | `mcpServers` |
| **Copilot CLI** | `.github/mcp.json` (project, as APM writes it) · `~/.copilot/mcp-config.json` (user) | project / user | JSON | `mcpServers` |
| **OpenAI Codex CLI** | `.codex/config.toml` (project) · `~/.codex/config.toml` (user) | project / user | TOML | `[mcp_servers.<name>]` |

Sources: [VS Code MCP](https://code.visualstudio.com/docs/agent-customization/mcp-servers), [Claude Code MCP](https://code.claude.com/docs/en/mcp), [Codex CLI MCP](https://learn.chatgpt.com/docs/extend/mcp), [APM MCP guide](https://microsoft.github.io/apm/consumer/install-mcp-servers/), [APM MCP as a primitive](https://microsoft.github.io/apm/producer/author-primitives/mcp-as-primitive/).

> **The load-bearing difference — the key follows the file:** `.vscode/mcp.json` and the VS Code profile file use `servers`; every `.mcp.json`, `~/.claude.json` and the Copilot CLI files use `mcpServers`; Codex uses TOML tables `[mcp_servers.<name>]`. A correct config under the wrong key is silently ignored.

## APM Source Form (`apm.yml`)

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
      transport: http        # http | streamable-http | sse (deprecated)
      url: https://learn.microsoft.com/api/mcp
      headers:
        Authorization: "Bearer ${SOME_TOKEN}"   # optional
```

Field notes:
- `registry: false` marks a self-defined (inline) server; omit it for registry references.
- `transport` is `stdio` | `http` | `sse` | `streamable-http` (`type` is a legacy alias). It is **required** on a self-defined server: APM rejects a `registry: false` entry without it ("requires 'transport'"). Only the `apm install --mcp` CLI flags infer it.
- Env placeholders use `${VAR}` grammar. Whether the generated file keeps the placeholder or receives the literal value depends on the target — see [Secrets](#secrets).

## Native Form: VS Code Copilot (`.vscode/mcp.json`)

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

## Native Form: Claude Code (`.mcp.json` / `~/.claude.json`)

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

## Native Form: OpenAI Codex CLI (`.codex/config.toml`)

TOML table per server: `[mcp_servers.<name>]`, read from `~/.codex/config.toml` or a trusted project's `.codex/config.toml`. Codex documents stdio and streamable HTTP, not SSE. stdio uses `command`/`args`/`env`; remote uses `url`, with auth through `bearer_token_env_var` or `env_http_headers` (header name → environment variable name). `env` applies to stdio servers only.

```toml
[mcp_servers.ddg-search]
command = "uvx"
args = ["duckduckgo-mcp-server"]

[mcp_servers.context7]
url = "https://mcp.context7.com/mcp"
[mcp_servers.context7.env_http_headers]
CONTEXT7_API_KEY = "CONTEXT7_API_KEY"
```

## Secrets

The only acceptable secret form in a tracked file is a placeholder. But the placeholder syntax and *who resolves it* differ per tool, so the value must reach the right environment.

| Layer | Syntax | Resolved by / when |
|---|---|---|
| `apm.yml` (source) | `${VAR}` | APM on `apm install`, per target — see the list below the table. **Inspect the output.** |
| Claude Code `.mcp.json` | `${VAR}`, `${VAR:-default}` | Claude Code, from its own process env at launch. Expandable in `command`/`args`/`env`/`url`/`headers`. **Unset + no default → a warning in `claude mcp list` / `/mcp`, and the server loads with the literal `${VAR}` text.** |
| VS Code `mcp.json` | `${input:ID}` (+ `inputs`/`password`) or `${env:VAR}` | VS Code, at server start. Bare `${VAR}` is not native here. |
| Codex `config.toml` | no placeholder syntax documented; name the variable instead (`bearer_token_env_var`, `env_http_headers`, `env_vars`) | Codex, from its process env at server start. |

What APM 0.31 writes from a `${VAR}` placeholder (it never shell-expands one):
- **VS Code, Copilot CLI, Kiro** — keeps the placeholder for the harness to resolve at runtime.
- **Claude Code `env` and `headers`, Codex stdio `env`** — resolves `${VAR}` from the install environment (prompting when a terminal is attached) and **writes the literal value** into the generated file; left as the placeholder when unset in a non-interactive install. For Claude, leaving the variable unset during `apm install` keeps the placeholder, which Claude then expands itself at launch.
- **Codex remote `headers` — known gap.** APM writes them to `http_headers`, which Codex treats as static values, with `${VAR}` copied verbatim. Codex sends the literal placeholder, so header auth silently fails; it never emits `env_http_headers` or `bearer_token_env_var`. Tracked as [microsoft/apm#2984](https://github.com/microsoft/apm/issues/2984). **Workaround, verified 2026-09-24 on APM 0.31.0 and Codex 0.156.1:** add an `extra: { env_http_headers: { HEADER: VAR } }` passthrough to the entry, alongside `headers:`. APM blocks `http_headers` in `extra`, but not `env_http_headers`. The generated TOML then carries both tables, and Codex sends the header **once**, with the value from the environment. The passthrough also lands in every other target's config, for example `.mcp.json`; `claude mcp get` parses it without error and shows only `headers`. APM also writes an `id = ""` key that Codex warns it ignores; the warning is harmless.

Key points:
- No `.env` file is maintained in this repo.
- For non-interactive runs (CI), export the vars first (`set -a; source <file>; set +a`, a shell profile, or direnv) so APM finds them without prompting.
- A key committed or pasted in plaintext is compromised — rotate and revoke it.

## Recommended Layout for This Repo

1. Author each server under `dependencies.mcp` in the package that owns it.
2. Externalize all secrets to `${VAR}`, then check what each target's generated file received (see [Secrets](#secrets)).
3. Run `apm install -g` to deploy; do not commit the generated `.vscode/mcp.json` / `.mcp.json` / `config.toml`.
4. Keep server `name`s aligned with how agents refer to them. No agent in this repo declares a `tools:` array (a Copilot-style array makes Claude Code refuse to spawn the agent — see [agent-guide.md](../../meta-steering/references/agent-guide.md#tools-field)), so the alignment that matters is prose: an agent body naming a server (`context7`, `opentofu-registry`) must use the name declared here.
