# Contributing

## Repository Frontmatter Provenance Convention

This repository defines a local provenance convention for customization files (`*.agent.md`, `*.prompt.md`, `*.instructions.md`, `*/SKILL.md`).

Provenance fields are grouped under `metadata.provenance` in YAML frontmatter:

```yaml
metadata:
  provenance:
    mirror: "https://example.com/canonical/upstream"           # single string — exact copy
    adaptedFrom:                                                # array — synthesised from
      - "https://github.com/org-a/repo/blob/main/skill.md"
      - "https://github.com/org-b/repo/blob/main/skill.md"
    authoritativeSpec:                                          # array — format specifications
      - "https://code.visualstudio.com/docs/copilot/customization/custom-agents"
      - "https://code.claude.com/docs/en/sub-agents"
```

- `metadata.provenance.mirror` (string): Canonical upstream URL for files that are exact copies. Tracked by the update script as `mirror` mode (replace from upstream).
- `metadata.provenance.adaptedFrom` (string or array): URL or list of URLs when local content is adapted/synthesised from upstream sources. Tracked by the update script as `adapted` mode (merge review).
- `metadata.provenance.authoritativeSpec` (array): URLs of authoritative specifications that define the file format, frontmatter schema, or behavioral contract. Informational only — not tracked for content drift.

`adaptedFrom` takes precedence when both `mirror` and `adaptedFrom` exist.

This is a **repository convention**, not a universal standard.

## Model Profile Convention (`metadata.modelProfile`)

Agent and skill files may declare a `metadata.modelProfile` block to describe the model capabilities required, instead of maintaining a hardcoded `model:` array. The `update-models` skill reads this profile, fetches the authoritative model list for the target provider at run-time, and rewrites the `model:` array with the current best-matching models.

```yaml
metadata:
  modelProfile:
    specialisation: NONE   # NONE | CODE | REASONING | LONG-CONTEXT
    cost: MEDIUM           # FREE | LOW | MEDIUM | HIGH
    latency: LOW           # LOW | MEDIUM | HIGH
    minDate: "2025-01-01"  # ISO date — exclude models retired before this date
```

### Field reference

| Field | Type | Allowed values | Semantics |
|---|---|---|---|
| `specialisation` | string | `NONE`, `CODE`, `REASONING`, `LONG-CONTEXT` | `CODE` prefers Codex-family and code-optimised models; `REASONING` prefers models with extended thinking/chain-of-thought capabilities; `LONG-CONTEXT` prefers models with the largest context windows and capability to retrieve from its entirety; `NONE` accepts general-purpose models |
| `cost` | string | `FREE`, `LOW`, `MEDIUM`, `HIGH` | Abstract cost tier: `FREE` = no quota consumed, `LOW` = minimal quota, `MEDIUM` = standard, `HIGH` = premium. Mapped to provider-specific pricing by the `update-models` skill. |
| `latency` | string | `LOW`, `MEDIUM`, `HIGH` | `LOW` prefers the fastest/smallest models; tie-breaks within a cost band |
| `minDate` | string | ISO 8601 date | Ensure models have intrinsic knowledge of everything up to this date; excludes models trained before this date |

### Resolution rules

The `update-models` skill fetches **all supported providers in parallel** and combines the results into one ranked `model:` array. Cost bands are abstract — the skill maps them to each provider's pricing metric at run-time:

| Cost tier | Copilot | KiloCode |
|---|---|---|
| `FREE` | Premium multiplier = 0 | Included without credits |
| `LOW` | Multiplier ≤ 0.33 | Low credit consumption |
| `MEDIUM` | Multiplier ≤ 1 | Standard credit consumption |
| `HIGH` | Any multiplier | Any model |

Authoritative sources are maintained in the `update-models` skill frontmatter (`metadata.provenance.authoritativeSpec`).

> **Note:** The `model:` array is a Copilot-only frontmatter field. Claude Code and other tools ignore it. `metadata.modelProfile` is a local repository convention and is safely ignored by all tools.

## Cross-Tool Compatibility

### Agents (`*.agent.md`)

Both VS Code Copilot and Claude Code use markdown files with YAML frontmatter for agent definitions. Each tool safely ignores frontmatter fields it doesn't recognize, so a single file can work for both.

- **Shared fields:** `name`, `description`, and the markdown body (system prompt) are fully compatible.
- **Tools:** Copilot and Claude Code have different tool ecosystems. The Copilot `tools` array is ignored by Claude Code, which falls back to inheriting all tools. Use the Claude-only `disallowedTools` field to restrict specific tools.
- **Model:** Copilot's `model` array is ignored by Claude Code, which defaults to inheriting the conversation model.
- **Extra fields:** Each tool safely ignores the other's unique fields.

See the [meta-agent skill](skills/meta-agent/SKILL.md) for full cross-tool compatibility documentation.

### Skills (`*/SKILL.md`)

Both tools support skill discovery from user-level directories. The [Agent Skills](https://agentskills.io/) standard (`SKILL.md` + folder structure) is shared — no format changes are needed.

- **Discovery:** Copilot uses `chat.agentSkillsLocations` in VS Code settings. Claude Code discovers skills from `~/.claude/skills/` (symlink `~/.llmctl/skills` there).
- **Frontmatter:** Both tools read `name` and `description` for discovery. Unknown fields are ignored.
- **References:** Relative paths to reference files (e.g., `references/*.md`) work in both tools since the folder structure is preserved via symlink.

### Instructions (`*.instructions.md`)

Copilot calls these "Instructions" and Claude Code calls them "Rules" — both auto-load behavioral guidelines when matching file patterns are referenced. Each tool uses a different frontmatter key for path-scoping, but both safely ignore unknown keys, so a single file works for both.

- **Shared fields:** `name`, `description`, and the markdown body are fully compatible.
- **Path-scoping:** Copilot uses `applyTo` (string or array); Claude Code uses `paths` (array of strings). Include both in the frontmatter with `# Copilot` / `# Claude Code` comments.
- **Discovery:** Copilot uses `chat.instructionsFilesLocations` in VS Code settings. Claude Code discovers rules from `~/.claude/rules/` (symlink `~/.llmctl/instructions` there).

### Prompts (`*.prompt.md`)

VSCode Prompts map to Claude Code Commands (`.claude/commands/`) — both create user-invokable slash commands. Commands are superseded by Skills in Claude Code; this mapping is for basic compatibility only.

## Upstream Update Tooling

Use the `meta-updater` agent together with the `meta-upstream-sync` skill to audit and synthesize upstream updates.

For GitHub API authentication, use a **Fine-grained Personal Access Token** whenever possible:

- Repository access: only the repositories you need to audit
- Repository permissions: `Contents` = **Read-only**
- No write permissions are required for update checks

Provide the token via `GITHUB_TOKEN`/`GH_TOKEN`, or pass `-GitHubToken` to `./skills/meta-upstream-sync/scripts/check-updates.ps1`.
