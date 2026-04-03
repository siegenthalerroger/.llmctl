# Contributing

## Repository Frontmatter Provenance Convention

This repository defines a local provenance convention for customization files (`*.agent.md`, `*.prompt.md`, `*.instructions.md`, `*/SKILL.md`).

Provenance fields are grouped under `metadata.provenance` in YAML frontmatter:

```yaml
metadata:
  provenance:
    mirror: "https://example.com/canonical/upstream"           # single string — exact copy
    adaptedFrom:                                               # array — synthesised from
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

Customization files may declare a `metadata.modelProfile` block to describe the model capabilities required, instead of maintaining a hardcoded `model:` array, but only when that file type supports the top-level Copilot `model` frontmatter field. The `meta-update-models` skill reads this profile, fetches the authoritative model catalogues for all supported providers at run-time, and rewrites the ordered `model:` array with the current best-matching models.

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
| `cost` | string | `FREE`, `LOW`, `MEDIUM`, `HIGH` | Abstract cost tier: `FREE` = truly zero incremental usage, `LOW` = light usage burn, `MEDIUM` = standard included usage, `HIGH` = premium or high-burn usage. Mapped to provider-specific pricing by the `meta-update-models` skill. |
| `latency` | string | `LOW`, `MEDIUM`, `HIGH` | `LOW` prefers the fastest/smallest models; tie-breaks within a cost band |
| `minDate` | string | ISO 8601 date | Ensure models have intrinsic knowledge of everything up to this date; excludes models trained before this date |

### Resolution rules

The `meta-update-models` skill fetches **all supported providers in parallel** and combines the results into one ranked `model:` array. Cost bands are abstract — the skill maps them to each provider's pricing or entitlement model at run-time.

The skill also enforces these merge rules:

- The array is ordered, and the harness chooses the first available entry.
- For `FREE` profiles, put qualifying free models first. In practice, this means free KiloCode models and GitHub Copilot models with premium multiplier `0`, but only when they pass the same task-fit and specialisation filters as every other candidate. Subscription-included models are **not** automatically free.
- For `LOW`, `MEDIUM`, and `HIGH` profiles, do **not** put free models first by default. Treat free options as optional fallbacks that must be explicitly validated as competitive with the paid candidates for the task.
- After the free-first prefix, reserve provider coverage in this order: **Claude Code**, **OpenAI-backed models available through Codex**, then **GitHub Copilot**.
- Always include at least one **Claude Code-backed** model, one **OpenAI-backed model available through Codex**, and one **GitHub Copilot** model when that provider still has a candidate after cost-band filtering.
- KiloCode is optional and free-only: include it only when a free KiloCode model is genuinely strong enough for the task, and never spend KiloCode credits.
- Interpret `cost` as a ceiling, not as an instruction to maximize cheapness. Within the allowed band, specialization and task fit outrank small cost differences.
- Use the exact accepted model display strings in `model:` arrays. Preserve casing and provider-specific spellings, and do not normalize names across providers. For example, `GPT-5.4 mini (copilot)` and `GPT-5.4 Mini (unify-chat-provider)` are distinct valid strings.

Authoritative sources are maintained in the `meta-update-models` skill frontmatter (`metadata.provenance.authoritativeSpec`) and currently cover GitHub Copilot, Claude Code, OpenAI Codex, and KiloCode.

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

VSCode Prompts map to Claude Code Commands (`.claude/commands/`) — both create user-invocable slash commands. Commands are superseded by Skills in Claude Code; this mapping is for basic compatibility only.

## Upstream Update Tooling

Use the `meta-updater` agent together with the `meta-upstream-sync` skill to audit and synthesize upstream updates.

For GitHub API authentication, use a **Fine-grained Personal Access Token** whenever possible:

- Repository access: only the repositories you need to audit
- Repository permissions: `Contents` = **Read-only**
- No write permissions are required for update checks

Provide the token via `GITHUB_TOKEN`/`GH_TOKEN`, or pass `-GitHubToken` to `./skills/meta-upstream-sync/scripts/check-updates.ps1`.
