# TODO

## 1 — MCP Server Configuration Support

**Goal:** Document and provide cross-tool compatible MCP server configuration guidance within `.llmctl`.

### Background
MCP config format differs across tools in both file location and format:

| Tool | File | Format | Key/Section |
|---|---|---|---|
| VS Code Copilot | `.vscode/mcp.json` | JSON | `"servers"` |
| Claude Code | `./.mcp.json` or `~/.claude.json` | JSON | `"mcpServers"` |
| KiloCode | VS Code environment (inherits Copilot) | JSON | `"servers"` |
| OpenAI Codex CLI | `~/.codex/config.toml` or `.codex/config.toml` | TOML | `[mcp_servers.<name>]` |

No single file is read by all tools automatically; they must be maintained separately or synchronised.

**Sources:**
- VS Code MCP: https://code.visualstudio.com/docs/copilot/chat/mcp-servers
- Claude Code MCP: https://docs.anthropic.com/en/docs/claude-code/mcp
- Codex CLI MCP: https://developers.openai.com/codex/mcp

### Tasks

- [ ] **1a — Create MCP configuration reference doc** (`references/mcp-configuration.md`)
  Document the config schema for each supported tool (VS Code, Claude Code, KiloCode), the file locations, the key differences (`servers` vs `mcpServers`), and recommended project layout.
  _Coder (Simple): create one new file._

- [ ] **1b — Create a cross-tool MCP setup prompt** (`prompts/setup-mcp.prompt.md`)
  A slash-command that takes a list of MCP server definitions and outputs the correctly formatted config blocks for each supported tool (VS Code `mcp.json` and Claude `.mcp.json`).
  _Coder (Simple): create one new file._

- [ ] **1c — Update `README.md` compatibility matrix**
  Add a "MCP Server Config" row to the compatibility matrix table. Reference the new `references/mcp-configuration.md` doc.
  _Coder (Simple): edit one section of `README.md`._

---

## 2 — OpenAI Codex CLI Support

**Goal:** Document compatibility and add symlink/config guidance for the official OpenAI Codex CLI.

### Background
The official OpenAI Codex CLI ([`openai/codex`](https://github.com/openai/codex), installed via `npm i -g @openai/codex`) has **significantly better** compatibility than initially assumed. It natively implements the [Agent Skills standard](https://agentskills.io/) and reads `AGENTS.md` for instructions.

**Steering file compatibility:**

| File Type | Codex CLI | Notes |
|---|---|---|
| Agents (`*.agent.md`) | ❌ Not supported | No custom mode system |
| Skills (`*/SKILL.md`) | ✅ Full support | Reads from `~/.agents/skills/` — symlink `.llmctl/skills` |
| Instructions (`*.instructions.md`) | ⚠️ Partial | Body can be placed in `~/.codex/AGENTS.md`; `applyTo`/`paths` ignored |
| Prompts (`*.prompt.md`) | ❌ Not supported | No slash-command equivalent |

**Skill discovery paths (Codex):**
- `$HOME/.agents/skills` — user-level (symlink target)
- `$REPO_ROOT/.agents/skills` — project-level
- `$CWD/.agents/skills` — working directory

**Instructions discovery (Codex):**
- `~/.codex/AGENTS.md` — global (or `AGENTS.override.md` for temporary override)
- `AGENTS.md` in each directory from repo root → CWD (layered, later wins)
- Fallback filenames configurable in `~/.codex/config.toml` via `project_doc_fallback_filenames`

**MCP config** (see Epic 2): `~/.codex/config.toml` using TOML `[mcp_servers.<name>]` — separate from VS Code/Claude config.

**Sources:**
- Skills: https://developers.openai.com/codex/skills
- AGENTS.md: https://developers.openai.com/codex/guides/agents-md
- MCP: https://developers.openai.com/codex/mcp

### Tasks

- [ ] **2a — Update `README.md` compatibility matrix**
  Fill in the "Codex" column with the findings above. Skills = ✅, Instructions = ⚠️, Agents = ❌, Prompts = ❌.
  _Coder (Simple): edit one section of `README.md`._

- [ ] **2b — Add Codex CLI setup instructions to `README.md`**
  Add a "OpenAI Codex CLI" subsection under "How to use" with symlink instructions for `~/.agents/skills` and guidance on using `AGENTS.md` for instructions.
---

## 3 — KiloCode Support

**Goal:** Document compatibility and add cross-tool agent/instruction support for KiloCode.

### Background
KiloCode (GitHub: `Kilo-Org/kilocode`, fork of `anomalyco/opencode`) supports custom modes defined in `.kilocodemodes` YAML at the project root or globally as `custom_modes.yaml`. The mode schema uses `slug`, `name`, `description`, `roleDefinition`, `customInstructions`, `whenToUse`, and `groups` (tool permissions).

KiloCode instruction rules live in `.kilo/rules-{slug}/` directories.

Steering file compatibility:

| File Type | KiloCode |
|---|---|
| Agents (`*.agent.md`) | ⚠️ Partial — `name`/`description`/body map to `slug`/`name`/`roleDefinition`; requires conversion |
| Skills (`*/SKILL.md`) | ⚠️ Partial — can be referenced from `customInstructions` or placed in `.kilo/rules-{slug}/` |
| Instructions (`*.instructions.md`) | ⚠️ Partial — body maps to `.kilo/rules-{slug}/*.md` files |
| Prompts (`*.prompt.md`) | ❌ Not natively supported |

### Tasks

- [ ] **3a — Update `README.md` compatibility matrix**
  Add a "KiloCode" column with the compatibility findings above.
  _Coder (Simple): edit one section of `README.md`._

- [ ] **3b — Document KiloCode mode schema in `CONTRIBUTING.md`**
  Add a "KiloCode" section under "Cross-Tool Compatibility" explaining the `.kilocodemodes` schema, how `*.agent.md` fields map to it, and where to place instruction rules.
  _Coder (Simple): edit one section of `CONTRIBUTING.md`._

- [ ] **3c — Create a conversion prompt** (`prompts/export-kilocode.prompt.md`)
  A slash-command prompt that reads an `*.agent.md` file and outputs a `.kilocodemodes` YAML block for it, mapping frontmatter fields to the KiloCode schema.
  _Coder (Simple): create one new file._

- [ ] **3d — Add KiloCode symlink instructions to `README.md`**
  Add a "KiloCode" subsection under "How to use" explaining how to place or symlink `.llmctl` content for KiloCode (`.kilocodemodes` generation, `.kilo/rules-*/` placement).
  _Coder (Simple): edit one section of `README.md`._

---
## 4 - Consider Running `meta-update-models` skill as part of the `meta-updater` Agent

_tbd_