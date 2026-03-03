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
