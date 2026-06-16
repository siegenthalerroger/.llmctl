---
name: "meta-mcp"
description: "Guidelines for configuring MCP (Model Context Protocol) servers for AI agent customization. Covers server config across agent harnesses and APM packaging — `dependencies.mcp` in apm.yml, the `servers` vs `mcpServers` key split, stdio/http/sse transports, and secret handling. Use when adding, reviewing, or debugging MCP servers, or generating MCP config for VS Code, Claude Code, Codex, or APM. Keywords: mcp, server, Model Context Protocol, mcpServers, servers, apm.yml, dependencies.mcp, stdio, http, sse, transport, secret, .mcp.json, mcp.json."
license: ""
metadata:
  provenance:
    authoritativeSpec:
      - "https://code.visualstudio.com/docs/copilot/chat/mcp-servers"
      - "https://code.claude.com/docs/en/mcp"
      - "https://developers.openai.com/codex/mcp"
      - "https://microsoft.github.io/apm/guides/mcp-servers/"
---

# MCP Server Configuration Guidelines

Guidance for configuring Model Context Protocol (MCP) servers across Claude Code, VS Code Copilot, OpenAI Codex CLI, and APM-managed packages.

> [!IMPORTANT]
> MCP servers add **external capabilities** (tools, resources, prompts) to an agent.
> Use instructions and skills for behavior steering, and use hooks for deterministic lifecycle automation.

For exhaustive per-tool schemas and the full config matrix, see [references/mcp-configuration.md](references/mcp-configuration.md). For authoritative format details, consult:
- VS Code Copilot: [MCP servers](https://code.visualstudio.com/docs/copilot/chat/mcp-servers)
- Claude Code: [MCP](https://code.claude.com/docs/en/mcp)
- OpenAI Codex CLI: [MCP](https://developers.openai.com/codex/mcp)
- APM: [MCP servers guide](https://microsoft.github.io/apm/guides/mcp-servers/)

## 1) When to use MCP

Use an MCP server when an agent needs a capability that is not built in — querying an API, searching docs, driving a browser, reading a registry — and that capability is reusable across tasks.

### Decision criteria

| Need | Use | Why |
|---|---|---|
| Add a new external tool/API/resource to the agent | MCP server | New runtime capability, discovered as tools |
| Run code automatically at a lifecycle boundary | Hooks | Event-triggered and deterministic |
| Teach preferred behavior, style, or process | Instructions | Durable steering, no side effects |
| Bundle reusable workflow knowledge | Skills | Composable task guidance |
| Ship a curated bundle of the above for distribution | Plugin | Packaged, marketplace-installable |

Do not add an MCP server for a capability a built-in tool already covers, or to steer behavior.

## 2) APM-first rule

This repo deploys via APM. **Declare each MCP server once in [`apm.yml`](../../../apm.yml) under `dependencies.mcp` and let APM translate it into every target's native config on deploy.** Do not hand-maintain per-target files (`.vscode/mcp.json`, `.mcp.json`, `.codex/config.toml`) — those are machine-generated output, not source.

```yaml
# apm.yml
dependencies:
  mcp:
    - name: microsoft.docs.mcp        # self-defined remote server
      registry: false
      transport: http
      url: https://learn.microsoft.com/api/mcp
    - name: ddg-search                # self-defined stdio server
      registry: false
      transport: stdio
      command: uvx
      args: ["duckduckgo-mcp-server"]
    - io.github.github/github-mcp-server   # registry string reference
```

APM resolves the target chain from `--target` → `targets:` in `apm.yml` → filesystem auto-detection, then writes each harness's file with the correct root key and format (see §4).

> [!WARNING]
> APM MCP support is still maturing, and user/global-scope (`apm install -g`) behavior varies by version. Treat MCP wiring as **authored-pending-verification** — run `apm install -g` and inspect the generated per-target files before relying on it (same posture this repo takes for hooks).

## 3) Transports

Pick the transport from how the server runs, not from the tool:

| Transport | Use for | Required fields |
|---|---|---|
| `stdio` | A local process the harness launches (npx/uvx/jbang/binary) | `command`, `args` (+ optional `env`) |
| `http` / `streamable-http` | A remote HTTP MCP endpoint | `url` (+ optional `headers`) |
| `sse` | A remote Server-Sent-Events endpoint (URL typically ends `/sse`) | `url` (+ optional `headers`) |

In native VS Code / Claude `mcp.json` the equivalent discriminator is the `type` field (`stdio` | `http` | `sse`). APM infers transport from `command` (→ stdio) or `url` (→ http) unless `transport`/`type` is set explicitly.

## 4) Cross-tool config surface

One concept, four destinations. APM normalizes the key and format differences below — they matter only when reading generated output or configuring a tool by hand.

| Tool | File | Format | Root key |
|---|---|---|---|
| APM (source) | `apm.yml` | YAML | `dependencies.mcp` |
| VS Code Copilot | `.vscode/mcp.json` | JSON | `servers` |
| Claude Code | `.mcp.json` (project) / `~/.claude.json` (user) | JSON | `mcpServers` |
| Copilot CLI | `~/.copilot/mcp-config.json` | JSON | `mcpServers` |
| OpenAI Codex CLI | `.codex/config.toml` / `~/.codex/config.toml` | TOML | `[mcp_servers.<name>]` |

The load-bearing trap: **VS Code uses `servers`; everyone else uses `mcpServers`.** See [references/mcp-configuration.md](references/mcp-configuration.md) for full per-tool examples.

## 5) Secrets and environment variables

> [!IMPORTANT]
> Never commit a plaintext API key, token, or password. The only acceptable form in a tracked file is a placeholder.

- **Author** secrets in `apm.yml` as the `${VAR}` placeholder in `headers`/`env` (APM's grammar). Keep real values in the git-ignored `.env` (see [.gitignore](../../../.gitignore)) and list the names in [`.env.example`](../../../.env.example).
- **A `.env` file is not auto-loaded.** The variable must exist in the environment of whatever resolves the placeholder — export it first (`set -a; source .env; set +a`, a shell profile, or direnv) before deploying or launching the tool.
- **Resolution differs per tool — APM bridges it on deploy, so verify the generated files** (it either bakes the value in at `apm install` time, or passes the placeholder through):
  - *Claude Code* expands `${VAR}` and `${VAR:-default}` in `command`/`args`/`env`/`url`/`headers`, read from Claude's own process environment at launch. A required var that is unset with no default makes Claude **fail to parse** the config.
  - *VS Code* uses `${input:ID}` (with an `inputs` array, `password: true`) or `${env:VAR}`, and can load a file via the `envFile` property (e.g. `"${workspaceFolder}/.env"`). Bare `${VAR}` is **not** VS Code's native secret form.
- If a key was ever committed or pasted in plaintext, treat it as compromised: rotate it and revoke the old one.

```yaml
- name: context7
  registry: false
  transport: http
  url: https://mcp.context7.com/mcp
  headers:
    CONTEXT7_API_KEY: "${CONTEXT7_API_KEY}"   # value lives in .env, never here
```

## 6) Quality checklist

- Capability isn't already covered by a built-in tool or another server.
- Declared once in `apm.yml`; no hand-edited per-target files committed.
- Transport matches how the server runs (`command` → stdio, `url` → http/sse).
- Every secret is a `${VAR}` placeholder; required vars are listed in `.env.example`.
- Remote `url` and stdio `command`/`args` verified to start and respond.
- `name` is stable and matches any `tools:` references in agents (e.g. `context7/*`).
- Deploy verified with `apm install -g`; generated files use the right root key per tool.

## 7) Anti-patterns

- Committing plaintext secrets, or baking a token into a `url`.
- Hand-maintaining `.vscode/mcp.json` / `.mcp.json` instead of `apm.yml` (drift and double source of truth).
- Adding a server "just in case" with no agent or task that uses it.
- Using `servers` for Claude/Codex or `mcpServers` for VS Code (wrong root key → silently ignored).
- Pinning `@latest` for a server whose behavior you depend on, then being surprised by a breaking change.
- Relying on `${input:...}` for servers that must work in Claude Code or Codex (not portable).
