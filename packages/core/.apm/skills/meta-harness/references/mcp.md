# MCP Server Configuration Guidelines

**Contents:** [When to Use MCP](#when-to-use-mcp) · [APM-First Rule](#apm-first-rule) · [Transports](#transports) · [Cross-Tool Config Surface](#cross-tool-config-surface) · [Secrets and Environment Variables](#secrets-and-environment-variables) · [Quality Checklist](#quality-checklist) · [Anti-Patterns](#anti-patterns)

Guidance for configuring Model Context Protocol (MCP) servers across Claude Code, VS Code Copilot, OpenAI Codex CLI, and APM-managed packages.

> [!IMPORTANT]
> MCP servers add **external capabilities** (tools, resources, prompts) to an agent.
> Use instructions and skills for behavior steering, and use hooks for deterministic lifecycle automation.

For exhaustive per-tool schemas and the full config matrix, see [mcp-configuration.md](./mcp-configuration.md). For authoritative format details, consult:
- VS Code Copilot: [MCP servers](https://code.visualstudio.com/docs/agent-customization/mcp-servers)
- Claude Code: [MCP](https://code.claude.com/docs/en/mcp)
- OpenAI Codex CLI: [MCP](https://learn.chatgpt.com/docs/extend/mcp)
- APM: [MCP servers guide](https://microsoft.github.io/apm/consumer/install-mcp-servers/), [MCP as a primitive](https://microsoft.github.io/apm/producer/author-primitives/mcp-as-primitive/)

## When to Use MCP

Use an MCP server when an agent needs a capability that is not built in — querying an API, searching docs, driving a browser, reading a registry — and that capability is reusable across tasks.

### Decision Criteria

MCP servers add external capability; hooks add determinism; instructions and skills add steering; plugins add packaging. The complete seven-way table is in [the `meta-steering` router, section 1](../../meta-steering/SKILL.md#1-pick-the-customization-type-first). Do not add an MCP server for a capability a built-in tool already covers, or to steer behaviour.

### Curating Servers and Tools

Exposed tool count is not free: irrelevant tools degrade selection even when they fit in context. In [Paramanayakam et al., *Less is More* (arXiv:2411.15399), §I](https://arxiv.org/abs/2411.15399), Llama3.1-8b-q4_K_M picks the wrong tool for a GeoEngine query when given all 46 tools and completes it when given 19. That is one small-model example, not a threshold. Curate deliberately:

- Add servers sparingly; disable unused tools where the harness allows it; prefer deferred/on-demand tool loading over always-on exposure when the harness supports it.
- Tool **names** carry heavy routing weight — prefer servers whose tools are purpose-revealing and namespaced (`service_resource_verb`) over generic or cryptic names.
- Split description density by layer: keep the server/namespace-level description terse (it only decides load-or-not); per-tool detail belongs in the tool's own schema, not in steering prose.
- Prefer servers that set MCP tool annotations (`readOnlyHint`, `destructiveHint`, `openWorldHint`) — these are structured safety signals. Never restate a tool's schema/usage in instructions or skills; duplicated prose interferes with the model's autonomous tool selection.

## APM-First Rule

This repo deploys via APM. **Declare each MCP server once in the owning package's `apm.yml` (universal servers: [`packages/core/apm.yml`](https://github.com/siegenthalerroger/.llmctl/blob/main/packages/core/apm.yml)) under `dependencies.mcp` and let APM translate it into every target's native config on deploy.** Do not hand-maintain per-target files (`.vscode/mcp.json`, `.mcp.json`, `.codex/config.toml`) — those are machine-generated output, not source.

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

APM resolves the target chain from `--target` → `targets:` in `apm.yml` → filesystem auto-detection, then writes each harness's file with the correct root key and format (see [Cross-Tool Config Surface](#cross-tool-config-surface)).

> [!WARNING]
> APM MCP support is still maturing, and behavior varies by version, target and scope. Treat MCP wiring as **authored-pending-verification** — install at the scope the package is meant for (`apm install -g` for global packages such as core, project scope otherwise) and inspect the generated per-target files before relying on it (same posture this repo takes for hooks).

## Transports

Pick the transport from how the server runs, not from the tool:

| Transport | Use for | Required fields |
|---|---|---|
| `stdio` | A local process the harness launches (npx/uvx/jbang/binary) | `command`, `args` (+ optional `env`) |
| `http` / `streamable-http` | A remote HTTP MCP endpoint | `url` (+ optional `headers`) |
| `sse` | Legacy Server-Sent-Events endpoint only (URL typically ends `/sse`) | `url` (+ optional `headers`) |

`sse` is deprecated: Claude Code documents it as deprecated in favour of HTTP, Codex does not support it, and APM 0.31 skips an SSE server for the Codex target with a warning. Use `http` whenever the server offers it.

In native VS Code / Claude `mcp.json` the equivalent discriminator is the `type` field. In `apm.yml`, `transport` is required on a self-defined (`registry: false`) server — APM rejects the entry without it (`type` is accepted as a legacy alias); APM infers it only for the `apm install --mcp` CLI flags.

## Cross-Tool Config Surface

One concept, several destinations. APM normalizes the key and format differences — they matter only when reading generated output or configuring a tool by hand. The file-by-file matrix and native examples are in [mcp-configuration.md](./mcp-configuration.md#config-matrix).

The load-bearing trap: **the root key follows the file, not the harness.** `.vscode/mcp.json` uses `servers`; `.mcp.json` (which VS Code also reads), `~/.claude.json` and the Copilot files use `mcpServers`; Codex uses TOML tables.

## Secrets and Environment Variables

> [!IMPORTANT]
> Never commit a plaintext API key, token, or password. The only acceptable form in a tracked file is a placeholder.

- **Author** secrets in `apm.yml` as the `${VAR}` placeholder in `headers`/`env` (APM's grammar). Never put a real value in a tracked file.
- **APM does not resolve uniformly, and does not always bridge the gap.** Depending on the target it keeps the placeholder, bakes in the literal value, or (Codex remote headers) writes a placeholder the harness never expands. Inspect every generated file; the per-target behaviour is in [mcp-configuration.md](./mcp-configuration.md#secrets).
- If a key was ever committed or pasted in plaintext, treat it as compromised: rotate it and revoke the old one.

```yaml
- name: context7
  registry: false
  transport: http
  url: https://mcp.context7.com/mcp
  headers:
    CONTEXT7_API_KEY: "${CONTEXT7_API_KEY}"   # placeholder only; never hard-code the value
```

## Quality Checklist

- Capability isn't already covered by a built-in tool or another server.
- Adding this server doesn't push total exposed tool count past what the model can discriminate; unused tools are disabled where the harness allows it.
- Declared once in `apm.yml`; no hand-edited per-target files committed.
- Transport matches how the server runs (`command` → stdio, `url` → http/sse).
- Every secret is a `${VAR}` placeholder; no real value in a tracked file, and the generated file for each target checked for what APM actually wrote.
- Self-defined server declares `transport`; `http` rather than `sse` when the server offers both.
- Remote `url` and stdio `command`/`args` verified to start and respond.
- `name` is stable and matches how agent prose refers to the server (agents here declare no `tools:` arrays).
- Deploy verified at the intended scope; generated files use the right root key per file.

## Anti-Patterns

- Committing plaintext secrets, or baking a token into a `url`.
- Hand-maintaining `.vscode/mcp.json` / `.mcp.json` instead of `apm.yml` (drift and double source of truth).
- Adding a server "just in case" with no agent or task that uses it.
- Adding a server that pushes total exposed tool count past what the model can discriminate, or restating its tool schemas in steering prose instead of letting the schema/annotations speak.
- Using the wrong root key for the file — `mcpServers` in `.vscode/mcp.json`, or `servers` in `.mcp.json` (silently ignored).
- Pinning `@latest` for a server whose behavior you depend on, then being surprised by a breaking change.
- Relying on `${input:...}` for servers that must work in Claude Code or Codex (not portable).
