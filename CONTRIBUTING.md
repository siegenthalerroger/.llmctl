# Contributing

## Packaging Model

`.llmctl` is an APM **monorepo**: one repository that exposes several independently installable, context-scoped sub-packages under `packages/`, plus repo-local dev tooling at the root. This keeps every context loading only what it needs instead of the whole collection.

| Package | Scope | Contents | Typical install |
|---|---|---|---|
| `packages/core` | Global baseline | Domain-neutral agents (plan, explore, executor-\*, researcher); troubleshooting/batch/research/mermaid skills; documentation + troubleshooting instructions; universal MCP servers | `apm install -g <repo-location>/packages/core` |
| `packages/meta` | Global (authoring) | The `meta-*` authoring skills, `setup-mcp` + `reflect` prompts, meta instruction | `apm install -g <repo-location>/packages/meta` |
| `packages/workflow` | Global (code work) | The `code-reviewer` agent; delivery-discipline skills sourced upstream (TDD, git worktrees, merge conflicts, code-review reception, lint pipelines) | `apm install -g <repo-location>/packages/workflow` |
| `packages/ops` | Per-project (ops/infra) | Helm/K8s/OpenTofu skills; helm + tf instructions; cloud/IaC doc MCP servers | `apm install <repo>/packages/ops` |
| `packages/product` | Per-project (product) | PRD skills; product-manager + ux-expert agents | `apm install <repo>/packages/product` |
| root `.apm/` | Repo-local only | `meta-updater` agent + `meta-update-models` / `meta-upstream-sync` audit skills, frontmatter-validation hook | Deployed only when developing this repo |

### Rules

- **Each sub-package uses the `.apm/` layout.** A package is `packages/<name>/apm.yml` + `packages/<name>/.apm/{agents,skills,prompts,instructions,hooks}/`. Bare `agents/`/`skills/` at a package root are misclassified by APM as a single skill bundle — everything must live under `.apm/`.
- **Place a new primitive by scope, not by type.** Ask: universal and domain-neutral (core), code-specific (workflow), authoring guidance (meta), domain-specific (ops/product or a new package), or operates on *this repo's own files* (root `.apm/`)? `core` is the baseline that loads in *every* context, including ones with no code in them — anything that presumes a codebase belongs in `workflow`.
- **Scope each MCP server to the package whose work needs it.** Universal dev servers (`github`, `context7`) live in `packages/core/apm.yml`; domain servers live in their domain package (cloud/IaC doc servers in `packages/ops/apm.yml`). A server loads only where its package is installed, so keep global tool surface minimal.
- **Consume upstream content as a pinned `dependencies.apm` entry, never a vendored copy** (see the APM-first rule below). Use the git subdir form to take a single skill out of a larger repo — `owner/repo/path/to/skill#<sha>` — and always pin a commit or tag; an unpinned entry tracks the default branch and drifts. Scope the dependency to the package whose work needs it, exactly like MCP servers, and record in a comment why that upstream was chosen and what was deliberately left behind. Bump with `apm outdated` → `apm update --dry-run` → `apm update -y`.
- **The marketplace is a separate repository.** Manifests and packed plugin bundles live in [`.llmctl-marketplace`](https://github.com/siegenthalerroger/.llmctl-marketplace), not here. A plugin host (claude.ai Cowork, Claude Desktop/Code) clones the marketplace repo and reads each `packages[].source` path *as committed* — it never runs `apm install` — so any package carrying APM dependencies has to be published as a bundle with those skills already vendored into it. Keeping that generated output out of this repo is the point of the split; `apm pack` also refuses to write a manifest across a `..` boundary, which rules out generating it here.
- **Publish with `python scripts/pack-marketplace.py`** (or `apm run pack-marketplace`). It runs `apm install` + `apm pack -o <marketplace>/plugins` for every package, cleans the transient deploy output back out of the package directory, prunes superseded bundles, syncs each `source:`/`version:` in the marketplace `apm.yml`, and regenerates both manifests there. Point it elsewhere with `--marketplace PATH` or `LLMCTL_MARKETPLACE_DIR`. Never hand-edit anything under `plugins/` or either `marketplace.json`. Keep every package at the same version (`lockstep`).
- **The plugin path is reduced-fidelity; `apm install` remains the full deploy.** Treat **skills** and **commands** (prompts) as the only primitives you can rely on reaching a marketplace consumer. APM 0.26 does pack `agents/`, `instructions/`, and `.mcp.json` into the bundle, but whether a given host loads them is version-dependent and unverified — and packed MCP entries lose their `headers` (so an API-keyed server will not authenticate). Use `apm install` where those primitives matter. The marketplace also does not reach claude.ai Chat or hosted ChatGPT.

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

> **APM-first rule:** If upstream content is available as an APM package, consume it as a dependency in `apm.yml` rather than copying it locally. Use `adaptedFrom` or `mirror` only for content that cannot be APM-managed.

### Portable vs. private frontmatter in SKILL.md

The [agentskills.io](https://agentskills.io/) spec recognizes only `name`, `description`, and optionally `license` as top-level frontmatter. Everything under `metadata.*` (e.g., `metadata.provenance`, `metadata.modelProfile`) is a **private convention** of this repository — other tools and consumers safely ignore it.

## Model Profile Convention (`metadata.modelProfile`)

Customization files may declare a `metadata.modelProfile` block to describe the model capabilities required, instead of hardcoding model selections — but only when that file type supports the top-level `model` frontmatter field. The `meta-update-models` skill reads this profile and produces two things: (1) the **active** Claude Code fields `model:` (a single alias) and `effort:`, mapped deterministically from the profile; and (2) a **non-functional** commented multi-provider candidate list, regenerated by fetching the authoritative provider catalogues at run-time. Claude Code is the primary harness, so the active fields target it; the comment preserves cross-harness intent for reference.

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

### Active fields (Claude Code) — deterministic

The **functional** output is two single-value Claude Code fields, mapped directly from the profile (no fetch):

**`model:` alias from `cost`**

| `cost` | `model:` alias |
|--------|----------------|
| `HIGH` | `opus` |
| `MEDIUM` | `sonnet` |
| `LOW` | `haiku` |
| `FREE` | `haiku` |

Aliases auto-track the current model generation. Use `inherit` only when an agent must deliberately follow the session model.

**`effort:` from `specialisation` + `latency`**

| profile signal | `effort:` |
|---|---|
| `specialisation: REASONING` | `high` (→ `xhigh` when `cost: HIGH`) |
| `latency: HIGH` | `high` |
| `latency: MEDIUM` | `medium` |
| `latency: LOW` | `low` |

`specialisation: REASONING` overrides the latency row. `effort` is a Claude-Code-only field; values `low | medium | high | xhigh | max`.

### Candidate list (non-functional comment)

The `meta-update-models` skill also fetches **all supported providers in parallel** and combines the results into one ranked list, written as a **YAML comment block** below the active fields — never an active array, since no harness reads it. Cost bands are abstract — the skill maps them to each provider's pricing or entitlement model at run-time.

The skill enforces these merge rules for the comment list:

- The array is ordered, and the harness chooses the first available entry.
- For `FREE` profiles, put qualifying free models first. In practice, this means free KiloCode models and GitHub Copilot models with premium multiplier `0`, but only when they pass the same task-fit and specialisation filters as every other candidate. Subscription-included models are **not** automatically free.
- For `LOW`, `MEDIUM`, and `HIGH` profiles, do **not** put free models first by default. Treat free options as optional fallbacks that must be explicitly validated as competitive with the paid candidates for the task.
- After the free-first prefix, reserve provider coverage in this order: **Claude Code**, **OpenAI-backed models available through Codex**, then **GitHub Copilot**.
- Always include at least one **Claude Code-backed** model, one **OpenAI-backed model available through Codex**, and one **GitHub Copilot** model when that provider still has a candidate after cost-band filtering.
- KiloCode is optional and free-only: include it only when a free KiloCode model is genuinely strong enough for the task, and never spend KiloCode credits.
- Interpret `cost` as a ceiling, not as an instruction to maximize cheapness. Within the allowed band, specialization and task fit outrank small cost differences.
- Use the exact accepted model display strings in `model:` arrays. Preserve casing and provider-specific spellings, and do not normalize names across providers. For example, `GPT-5.4 mini (copilot)` and `GPT-5.4 Mini (unify-chat-provider)` are distinct valid strings.

Authoritative sources are maintained in the `meta-update-models` skill frontmatter (`metadata.provenance.authoritativeSpec`) and currently cover GitHub Copilot, Claude Code, OpenAI Codex, and KiloCode.

> **Note:** The active `model:` value is a single alias (or full ID / `inherit`) read by Claude Code — the primary harness. VS Code Copilot's `model:` expects provider-suffixed display strings, so the alias is not a valid Copilot model; Copilot is the secondary harness here and is expected to fall back to its default model. The multi-provider ranking is kept only as a **non-functional comment** — no harness reads it. `metadata.modelProfile` is a local repository convention, ignored by all tools.

## Cross-Tool Compatibility

### Agents (`*.agent.md`)

Both VS Code Copilot and Claude Code use markdown files with YAML frontmatter for agent definitions. Each tool safely ignores frontmatter fields it doesn't recognize, so a single file can work for both.

- **Shared fields:** `name`, `description`, and the markdown body (system prompt) are fully compatible.
- **Tools:** Copilot and Claude Code have different tool ecosystems. **Omit `tools:`; scope Claude Code via the Claude-only `disallowedTools` denylist.** A Copilot `tools:` array does **not** fall back to inherit-all on Claude Code — Claude parses it as a strict allowlist and refuses to spawn the agent when no entry resolves. APM copies agent frontmatter verbatim to every target, so a shared file cannot carry a Copilot allowlist. See the [meta-agent skill "Tools field"](packages/meta/.apm/skills/meta-agent/SKILL.md#tools-field).
- **Model:** the active `model:` is a single Claude Code value (alias / full ID / `inherit`) resolved from `metadata.modelProfile`, alongside a Claude-Code `effort:` value; the multi-provider ranking lives in a non-functional comment. Copilot does not recognize the alias and is expected to fall back to its default model.
- **Extra fields:** Each tool safely ignores the other's unique fields.

See the [meta-agent skill](packages/meta/.apm/skills/meta-agent/SKILL.md) for full cross-tool compatibility documentation.

### Skills (`*/SKILL.md`)

Both tools support skill discovery from user-level directories. The [Agent Skills](https://agentskills.io/) standard (`SKILL.md` + folder structure) is shared — no format changes are needed.

- **Discovery:** Copilot uses `chat.agentSkillsLocations` in VS Code settings. Claude Code discovers skills from `~/.claude/skills/`.
- **Frontmatter:** Both tools read `name` and `description` for discovery. Unknown fields are ignored.
- **References:** Relative paths to reference files (e.g., `references/*.md`) work in both tools since the folder structure is preserved via symlink.
- **Descriptions:** follow the directive, naming-first shape defined in the [meta-skill skill](packages/meta/.apm/skills/meta-skill/SKILL.md). Four distinct char budgets govern different surfaces (1024 per-field / 1536 combined discovery / 15k Claude Code total / 8k Codex aggregate) — see meta-skill rather than duplicating the detail here.

### Instructions (`*.instructions.md`)

Copilot calls these "Instructions" and Claude Code calls them "Rules" — both auto-load behavioral guidelines when matching file patterns are referenced. Each tool uses a different frontmatter key for path-scoping, but both safely ignore unknown keys, so a single file works for both.

- **Shared fields:** `name`, `description`, and the markdown body are fully compatible.
- **Path-scoping:** Copilot uses `applyTo` (string or array); Claude Code uses `paths` (array of strings). Include both in the frontmatter with `# Copilot` / `# Claude Code` comments.
- **Discovery:** Copilot uses `chat.instructionsFilesLocations` in VS Code settings. Claude Code discovers rules from `~/.claude/rules/`.

### Prompts (`*.prompt.md`)

VSCode Prompts map to Claude Code Commands (`.claude/commands/`) — both create user-invocable slash commands. Commands are superseded by Skills in Claude Code; this mapping is for basic compatibility only.

### Hooks (`*.hook.json`)

Standalone hook definition files use the `*.hook.json` extension — a repository naming convention analogous to `*.agent.md` / `*.prompt.md` / `*.instructions.md`. It is a strict subset of `*.json`, so it does not change how any harness discovers hooks:

- **VS Code Copilot** loads all `*.json` in a configured hook folder (`chat.hookFilesLocations`, and the `.github/hooks/*.json` default), so `*.hook.json` is discovered normally.
- **Claude Code** reads hooks from `settings.json`, not by scanning a `hooks/` directory, so the source filename is irrelevant to it.
- **APM** discovers hook primitives by glob (not a fixed filename) and rewrites them into each target's native location on deploy.

The fixed names `hooks.json` / `hooks/hooks.json` apply only inside **plugin** bundles, not to standalone hook files.

**Author one canonical hook, let APM transform it.** Write hooks in APM's canonical (Claude-Code-style) schema — a top-level `hooks` object keyed by lifecycle event, each entry carrying a `matcher` and a `hooks` array of `{ "type": "command", ... }`:

```json
{ "hooks": { "PostToolUse": [ { "matcher": "Edit|Write", "hooks": [ { "type": "command", "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/.apm/hooks/<script>\"", "timeout": 15 } ] } ] } }
```

APM is target-aware and reconciles event names, matchers, and paths per harness on deploy, so do **not** hand-maintain per-target variants. Use the portable `${CLAUDE_PLUGIN_ROOT}` root token (recognized by Claude and by Claude-compatible VS Code plugins) rather than a harness-specific token like `${workspaceFolder}`. APM hook support is still maturing — verify the deployed result with `apm install -g` before relying on it.

**Do not commit machine-generated hook wiring.** APM deploys hooks into each target's native location (e.g. `~/.claude/settings.json` at user scope). Personal or machine-generated Claude settings belong in `.claude/settings.local.json`, which is git-ignored; `.claude/settings.json` is left free for intentional, shared project settings should you ever want them committed.

## Deprecated Fields

### `infer:` (agent frontmatter)

The `infer:` field was an early experiment for automatic agent selection. It is now deprecated — VS Code Copilot removed support. Use `description` for discoverability and `disable-model-invocation: true` for agents that should not be auto-selected.

## Content Strategy: APM-First

APM is the primary mechanism for consuming upstream content. Prefer declaring upstream packages in `apm.yml` and installing them into the git-ignored `apm_modules/` directory. Only create local copies when upstream content cannot be managed by APM.

| Category | When to use | Provenance field | Storage / update |
|---|---:|---|---|
| APM dependency (default) | Upstream package available as APM | none required (declare in `apm.yml`) | Installed to `apm_modules/` (git-ignored). Update with `apm install -g` |
| Adapted / synthesised (local) | Significant local rewrite or merge of multiple sources | `metadata.provenance.adaptedFrom` | Tracked by `meta-upstream-sync` for drift detection; file lives in repo |
| Mirror (legacy / exceptional) | Exact local copy of an upstream file (only if APM cannot manage it) | `metadata.provenance.mirror` | Tracked by `meta-upstream-sync`. Deprecated when upstream is APM-available |

### APM dependency (default)

- Default for any content available from an APM-compatible upstream source.
- To add: declare the package in `apm.yml` and run `apm install -g`.
- Installed into `apm_modules/` (git-ignored). No `metadata.provenance` tracking is required for pure APM dependencies.
- Do NOT vendor upstream content by copying files into this repository.

### Adapted / synthesised (local)

- Use when the local file contains substantial original content, restructures the upstream material for local conventions, or synthesises multiple upstream sources.
- Add `metadata.provenance.adaptedFrom` listing upstream sources. These files are tracked by `meta-upstream-sync` for drift and merge-review workflows.

### Mirror (legacy / exceptional)

- Use only when an exact copy of an upstream file is necessary and APM cannot manage the upstream source (for example, an internal VS Code file not packaged for APM).
- Mark with `metadata.provenance.mirror`. Mirrors are tracked by `meta-upstream-sync` but are deprecated for content that can be consumed via APM.
- Before creating a mirror, verify the upstream isn't available as an APM package.

Local-only skills (not available upstream) remain directly in this repository.

## Upstream Update Tooling

The `meta-updater` agent and `meta-upstream-sync` skill audit **locally-committed files** with provenance declarations. APM dependencies are updated separately via `apm install -g`.

Use the `meta-updater` agent together with the `meta-upstream-sync` skill to audit and synthesize upstream updates.

GitHub API authentication uses the `gh` CLI by default — run `gh auth login` once and `check-updates.ps1` reuses that login (`gh auth token`) automatically.

For CI or non-`gh` environments, supply a **Fine-grained Personal Access Token** instead:

- Repository access: only the repositories you need to audit
- Repository permissions: `Contents` = **Read-only**
- No write permissions are required for update checks

Provide the token via `GITHUB_TOKEN`/`GH_TOKEN`, or pass `-GitHubToken` to `./.apm/skills/meta-upstream-sync/scripts/check-updates.ps1`.
