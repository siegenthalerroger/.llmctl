# Contributing

## Packaging Model

`.llmctl` is an APM **monorepo**: one repository that exposes several independently installable, context-scoped sub-packages under `packages/`, plus repo-local dev tooling at the root. This keeps every context loading only what it needs instead of the whole collection.

| Package | Scope | Contents | Typical install |
|---|---|---|---|
| `packages/core` | Global baseline | Domain-neutral agents (plan, explore, executor-\*, researcher); troubleshooting/batch/research/mermaid skills; the `meta-steering` + `meta-harness` authoring skills; documentation, troubleshooting + meta instructions; `reflect` + `setup-mcp` prompts; universal MCP servers | `apm install -g <repo-location>/packages/core` |
| `packages/workflow` | Global (code work) | The `code-reviewer` agent; delivery-discipline skills sourced upstream (TDD, git worktrees, merge conflicts, code-review reception, lint pipelines) | `apm install -g <repo-location>/packages/workflow` |
| `packages/ops` | Per-project (ops/infra) | Helm/K8s/OpenTofu skills; helm + tf instructions; cloud/IaC doc MCP servers | `apm install <repo>/packages/ops` |
| `packages/product` | Per-project (product) | PRD skills; product-manager + ux-expert agents | `apm install <repo>/packages/product` |
| `packages/design` | Per-project (design) | `design-direction`, `colour`, `typography`, `presentation` skills; upstream layout/identity/dataviz practice | `apm install <repo>/packages/design` |
| `packages/python` | Per-project (Python) | `python-standards` + `python-scripts` skills; python instructions; upstream `modern-python` project tooling | `apm install <repo>/packages/python` |
| root `.apm/` | Repo-local only | `meta-updater` dispatcher + the `meta-update-repo` / `meta-update-models` / `meta-refresh-steering` / `meta-review-steering` procedures, frontmatter-validation hook | Deployed only when developing this repo |

### Rules

- **Each sub-package uses the `.apm/` layout.** A package is `packages/<name>/apm.yml` + `packages/<name>/.apm/{agents,skills,prompts,instructions,hooks}/`. Bare `agents/`/`skills/` at a package root are misclassified by APM as a single skill bundle — everything must live under `.apm/`.
- **The root workspace depends on `packages/core` and `packages/python`.** Those are the two an agent editing this repo needs in context: `core` carries `meta-steering` and `meta-harness`, which every steering file here is written against, plus the prose and research skills the docs get written with; `python` carries the standards `scripts/` is held to. Deploying the root [apm.yml](apm.yml) therefore brings both along beside the repo-local procedures. Nothing else is added — the remaining packages are domain steering for work that does not happen in this repository.
- **Place a new primitive by scope, not by type.** Ask: universal and domain-neutral (core, which also owns the authoring guidance), code-specific (workflow), domain-specific (ops/product/design or a new package), or operates on *this repo's own files* (root `.apm/`)? `core` is the baseline that loads in *every* context, including ones with no code in them — anything that presumes a codebase belongs in `workflow`.
- **Scope each MCP server to the package whose work needs it.** Universal dev servers (`github`, `context7`) live in `packages/core/apm.yml`; domain servers live in their domain package (cloud/IaC doc servers in `packages/ops/apm.yml`). A server loads only where its package is installed, so keep global tool surface minimal.
- **Consume upstream content as a pinned `dependencies.apm` entry, never a vendored copy** (see the APM-first rule below). Use the git subdir form to take a single skill out of a larger repo — `owner/repo/path/to/skill#<sha>` — and always pin a commit or tag; an unpinned entry tracks the default branch and drifts. Scope the dependency to the package whose work needs it, exactly like MCP servers, and record in a comment why that upstream was chosen and what was deliberately left behind. Bump through the `meta-update-repo` skill, which runs that loop per package, reads the diff of everything that moved before it is committed, and keeps `apm.yml` and `apm.lock.yaml` in one commit. **Every pin is a full commit SHA and every package commits its `apm.lock.yaml`** — see [Lockfiles](#lockfiles).
- **The marketplace is a separate repository.** Manifests and packed plugin bundles live in [`.llmctl-marketplace`](https://github.com/siegenthalerroger/.llmctl-marketplace), not here. A plugin host (claude.ai Cowork, Claude Desktop/Code) clones the marketplace repo and reads each `packages[].source` path *as committed* — it never runs `apm install` — so any package carrying APM dependencies has to be published as a bundle with those skills already vendored into it. Keeping that generated output out of this repo is the point of the split; `apm pack` also refuses to write a manifest across a `..` boundary, which rules out generating it here.
- **The marketplace repository holds nothing that is authored there.** Its `README.md`, `LICENSE`, `.gitignore` and `apm.yml` all have a source in this workspace — `README.marketplace.md`, `LICENSE.marketplace`, `.gitignore.marketplace`, `apm.marketplace.yml` — and [scripts/pack_marketplace.py](scripts/pack_marketplace.py) writes them out beside the bundles it packs, filling in each catalogue entry's `source` and `version`. Anything else it finds in that tree is **deleted**, so "everything there is generated" is enforced rather than asserted. Edit the sources here and regenerate; never edit the marketplace.
- **A release publishes; it does not commit here.** [scripts/release.py](scripts/release.py) (or `apm run release`, which previews) derives each package's calendar version, packs from a scratch export of `HEAD`, commits and pushes the marketplace, and records the version as an annotated `<name>@<version>` tag plus the GitHub release beside it. Both roots are explicit flags with no defaults — `--repo` for the workspace being released and `--marketplace` for the repo it publishes into — because a derived marketplace path would silently publish into the wrong repo; [apm.yml](apm.yml) supplies them. **Packages version independently** (`per_package`); see [Releasing](#releasing).
- **Content that cannot be public lives in a separate workspace, never in `packages/` here.** This repo and its marketplace are public. A private package gets its own private source repo and its own private marketplace, laid out identically but with no `scripts/` — it borrows this repo's release code by sibling clone and shares nothing else. `LICENSES/` and `dependency-licenses.yml` are read from the workspace being released, so a private repo carries its own copies rather than resolving against this one. See [Releasing another workspace](#releasing-another-workspace).
- **The plugin path is reduced-fidelity; `apm install` remains the full deploy.** Treat **skills** and **commands** (prompts) as the only primitives you can rely on reaching a marketplace consumer. APM 0.26 does pack `agents/`, `instructions/`, and `.mcp.json` into the bundle, but whether a given host loads them is version-dependent and unverified — and packed MCP entries lose their `headers` (so an API-keyed server will not authenticate). Use `apm install` where those primitives matter. The marketplace also does not reach claude.ai Chat or hosted ChatGPT.

## Content Strategy: APM-First

APM is the primary mechanism for consuming upstream content. Prefer declaring upstream packages in `apm.yml` and installing them into the git-ignored `apm_modules/` directory. Only create local copies when upstream content cannot be managed by APM.

| Category | When to use | Provenance field | Storage / update |
|---|---:|---|---|
| APM dependency (default) | Upstream package available as APM | none required (declare in `apm.yml`) | Installed to `apm_modules/` (git-ignored). Update with `apm install -g` |
| Adapted / synthesised (local) | Any local copy of upstream material, from a light borrowing to a near-verbatim carry-over — only if APM cannot manage it | `metadata.provenance.adaptedFrom` | Tracked by `meta-update-repo` for drift detection; file lives in repo |

### APM dependency (default)

- Default for any content available from an APM-compatible upstream source.
- To add: declare the package in `apm.yml` and run `apm install -g`.
- Installed into `apm_modules/` (git-ignored). No `metadata.provenance` tracking is required for pure APM dependencies.
- Do NOT vendor upstream content by copying files into this repository.

### Adapted / synthesised (local)

- Use whenever anything at all was taken from an upstream file that APM cannot manage — whether the local file restructures the material for local conventions, synthesises several sources, or carries most of one upstream across near-verbatim.
- Add `metadata.provenance.adaptedFrom` listing upstream sources, and set each entry's `fidelity` to say how much was taken plus its `license` wherever that fidelity copies expression. These files are tracked by `meta-update-repo` for drift and merge-review workflows.
- Before adding one, verify the upstream isn't available as an APM package.
- Run `apm run check` afterwards. Its `licences` gate is the only thing that catches a provenance block which parses to nothing — a file that stops being tracked looks exactly like one with nothing to track.

Local-only skills (not available upstream) remain directly in this repository.

## Cross-Tool Compatibility

### Agents (`*.agent.md`)

Both VS Code Copilot and Claude Code use markdown files with YAML frontmatter for agent definitions. Each tool safely ignores frontmatter fields it doesn't recognize, so a single file can work for both.

- **Shared fields:** `name`, `description`, and the markdown body (system prompt) are fully compatible.
- **Tools:** Copilot and Claude Code have different tool ecosystems. **Omit `tools:`; scope Claude Code via the Claude-only `disallowedTools` denylist.** A Copilot `tools:` array does **not** fall back to inherit-all on Claude Code — Claude parses it as a strict allowlist and refuses to spawn the agent when no entry resolves. APM copies agent frontmatter verbatim to every target, so a shared file cannot carry a Copilot allowlist. See the [meta-steering router](packages/core/.apm/skills/meta-steering/SKILL.md#4-frontmatter-shared-by-all-four-types).
- **Model:** the active `model:` is a single Claude Code value (alias / full ID / `inherit`) resolved from `metadata.modelProfile`, alongside a Claude-Code `effort:` value; the multi-provider ranking lives in a non-functional comment. Copilot does not recognize the alias and is expected to fall back to its default model.
- **Extra fields:** Each tool safely ignores the other's unique fields.

See [agents.md](packages/core/.apm/skills/meta-steering/references/agents.md) for full cross-tool compatibility documentation.

### Skills (`*/SKILL.md`)

Both tools support skill discovery from user-level directories. The [Agent Skills](https://agentskills.io/) standard (`SKILL.md` + folder structure) is shared — no format changes are needed.

- **Discovery:** Copilot uses `chat.agentSkillsLocations` in VS Code settings. Claude Code discovers skills from `~/.claude/skills/`.
- **Frontmatter:** Both tools read `name` and `description` for discovery. Unknown fields are ignored.
- **References:** Relative paths to reference files (e.g., `references/*.md`) work in both tools since the folder structure is preserved via symlink.
- **Descriptions:** follow the directive, naming-first shape defined in the [meta-steering skill](packages/core/.apm/skills/meta-steering/SKILL.md). Four distinct char budgets govern different surfaces (1024 per-field / 1536 combined discovery / 15k Claude Code total / 8k Codex aggregate) — see that skill rather than duplicating the detail here.

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

## Repository Frontmatter Provenance Convention

This repository defines a local provenance convention for customization files (`*.agent.md`, `*.prompt.md`, `*.instructions.md`, `*/SKILL.md`).

Provenance fields are grouped under `metadata.provenance` in YAML frontmatter:

```yaml
metadata:
  provenance:
    adaptedFrom:                                               # string, or array — synthesised from
      - "https://github.com/org-a/repo/blob/main/skill.md"
      - url: "https://github.com/org-b/repo/blob/main/skill.md"   # scoped adaptation
        license: MIT                                              # SPDX id of the upstream
        fidelity: inspiration-only                                # obligation level
        took: "The severity-tiering concept."
    authoritativeSpec:                                          # array — format specifications
      - "https://code.visualstudio.com/docs/copilot/customization/custom-agents"
      - "https://code.claude.com/docs/en/sub-agents"
```

- `metadata.provenance.adaptedFrom` (string, array of URLs, or array of objects): where local content was adapted/synthesised from. Tracked by the update script for content drift, which recommends a merge review against upstream.
- `metadata.provenance.authoritativeSpec` (array): authoritative specifications that define the file format, frontmatter schema, or behavioral contract. Not tracked for content drift. A bare URL string means **cited only, nothing reproduced**, and carries no obligation; if a reference file reproduces a spec's wording or tables, switch that entry to the object form so the licence is recorded. Vendor documentation sites generally grant no reuse rights at all, so there the fix is rewriting, not attribution.

#### Scoping an adaptation with `fidelity` and `took`

A bare URL means **the whole file** derives from that upstream. Prefer the object form, which scopes the adaptation and records the terms it arrives under, so a drift review can be closed without opening the upstream diff: if the upstream change touches nothing on the list, there is nothing to merge.

`fidelity` is the obligation level:

| Value | Meaning | Upstream terms attach? |
| --- | --- | --- |
| `inspiration-only` | an idea or approach, no expression | no |
| `structural-echo` | the shape or section skeleton | no |
| `partly-derived` | some passages carried over | **yes** |
| `largely-derived` | most of the file, up to a near-verbatim copy | **yes** |

Absent means whole-file derivation, treated as `largely-derived`.

`license` is the SPDX id of the **upstream**, not of this file — `NONE` when the upstream has no LICENSE file, which grants no rights at all and is only safe at `inspiration-only`. It is required wherever `fidelity` implies an obligation, because it decides what the local file may be licensed under. [scripts/check_licenses.py](scripts/check_licenses.py) enforces this; see [Licensing](#licensing) below.

`took` then records **what was taken**, and nothing else. Three rules keep it from rotting:

- **Never record what was *not* taken** (or what is original locally). That is an open set — upstream can add sections indefinitely, so the list is wrong the moment upstream grows, and no local change ever triggers a refresh. What *was* taken is bounded by the local file, so it only goes stale when someone is already editing that file.
- **Never record measurements** (line-overlap percentages, sizes, counts). Both sides move; `fidelity` carries the same signal durably. Keep numbers in the commit or the TODO item that motivated them.
- **Never overload it.** `took` records what was taken — nothing else. Licensing belongs in the sibling `license:` field, and the obligation level in `fidelity:`. The one exception: a short note on why the URL is *not* a line-for-line comparison base (upstream moved or restructured the adapted path) belongs, because it changes how the next reviewer reads the diff.

Full rules and parser behaviour: [source-url-reference.md](.apm/skills/meta-update-repo/references/source-url-reference.md).

This is a **repository convention**, not a universal standard.

> **APM-first rule:** If upstream content is available as an APM package, consume it as a dependency in `apm.yml` rather than copying it locally. Use `adaptedFrom` only for content that cannot be APM-managed.

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

## Upstream Update Tooling

Three kinds of upstream feed this repository. `apm run update` handles the first; `apm run check-updates` audits the other two. The `meta-update-repo` skill is the procedure around them.

**Four procedures, no pipeline.** Updating is not one command, because the four things that go out of date go out of date on their own schedules. The `meta-updater` agent routes a request to one of them and asks which when the request does not say — it never runs all four because the ask was vague.

| Procedure | Moves | Run it when |
| --- | --- | --- |
| `meta-update-repo` | pins and lockfiles, adapted files, cited specs, upstream licences | an upstream may have moved |
| `meta-update-models` | `model:` / `effort:` where a `metadata.modelProfile` is declared | a new model shipped |
| `meta-refresh-steering` | `meta-steering` and `meta-harness` themselves | the harnesses have moved on |
| `meta-review-steering` | every steering file, against the guidance over it | the guidance changed, or it has been a while |

The last two are a pair: refreshing the guidance is what makes the files it governs due for review. `apm run check-steering` says which those are, by asking git which guidance commits landed after each file was last touched. That is a reading order and not a verdict — a cosmetic commit to the guidance marks everything it governs behind, and editing a file for an unrelated reason clears its flag with nobody having re-read it, so `current` means *not measurable* rather than *verified*.

| Input | Declared in | Command |
| --- | --- | --- |
| APM dependencies | `dependencies.apm`, resolved in `packages/*/apm.lock.yaml` | `apm run update` |
| Adapted content | `metadata.provenance.adaptedFrom` | `apm run check-updates` |
| Specifications | `metadata.provenance.authoritativeSpec` | the same, with `--specs` |

`apm run update` moves each package's pins as far as they go, installs, proves the lockfile followed, scans what was materialised with `apm audit`, and prints the upstream's own diff for everything that moved, filtered to the path this repository consumes. It commits nothing.

**Every bump is read before it is committed.** A pinned dependency is content an agent loads as instructions, and some of it ships scripts and hooks that run locally; `apm approve` gates *execution*, not content. The [safety-review reference](.apm/skills/meta-update-repo/references/safety-review.md) says what to look for. It is a reading, not a scan — a table of strings to grep for was built and dropped for flagging a vendor's own install one-liner while missing anything phrased differently.

**Two upstreams `apm update` cannot move on its own.** It resolves a full-SHA pin only to the newest *annotated* semver tag, so an upstream publishing none — `blader/humanizer` and `rshade/agent-skills` today — needs the HEAD bump that `update.py` applies for exactly that case. Where a tag does exist, APM rewrites the pin and appends it as a comment (`#<sha> # v1.2.3`), which is what a future Renovate `apm` manager would read.

**And one it refuses outright.** A package pinning several subpaths of one repository at the same commit fails on APM 0.31 with "Expected exactly one apm.yml entry for `<sha>`, found N", and APM writes nothing. `packages/design` is in that state. The update reports it and exits non-zero rather than hand-editing around it; a hand-moved pin would skip the tag `apm update` would have chosen.

A merge that pulls across more text than before raises the entry's `fidelity`, and a raised fidelity can attach upstream terms the local file's licence cannot carry. Update `fidelity` and `license` in the same edit as the merge, then run the gates.

The audit parses provenance through the same [provenance.py](scripts/provenance.py) as the licence gate, so the two cannot disagree about what is tracked. GitHub authentication uses `gh auth token` by default; for CI or non-`gh` environments supply a fine-grained token with `Contents: Read-only` via `GITHUB_TOKEN`/`GH_TOKEN`, or `--github-token`.

## Licensing

`.llmctl` is licensed under a split, because it is two different kinds of thing — see [LICENSE](LICENSE) for the authoritative statement:

| What | Licence |
| --- | --- |
| Every `*.md` file — skills, agents, prompts, instructions, `references/`, repo docs | **CC-BY-SA-4.0** |
| Everything else — `scripts/`, hooks, `*.py`, `*.ps1`, `*.json`, `*.yml` | **MIT** |

Three rules follow from that, and [scripts/check_licenses.py](scripts/check_licenses.py) enforces all three:

- **The content half is copyleft.** Adapting a `*.md` file from here means releasing your adaptation under CC-BY-SA-4.0 too. That is deliberate.
- **A file's provenance decides its licence.** Where `metadata.provenance` records an obligation-bearing `fidelity`, the upstream's `license` constrains what the local file may be licensed under: MIT upstream permits either default; CC-BY-SA-4.0 upstream forces CC-BY-SA-4.0; Apache-2.0 and GPL-3.0 upstreams force their own licence and need a per-file override; `NONE` permits nothing beyond `inspiration-only`. Declare an override with a **top-level `license:` field** in the file's frontmatter — that always wins over the table above.
- **Attribution is generated, never hand-written.** `THIRD-PARTY-NOTICES.md` in the marketplace repo is produced by [scripts/gen_notices.py](scripts/gen_notices.py) from provenance metadata plus each bundle's `apm.lock.yaml`. Sources whose terms attach land under *Notices*; everything else, including `inspiration-only` sources and upstreams with no licence at all, is still credited under *Acknowledgements*.

Adding a dependency or an adaptation from a **new** upstream means recording its licence in [dependency-licenses.yml](dependency-licenses.yml) or the entry's `license:` field. Run `apm run check` before opening a pull request.

## Commit Convention

Commits are **conventional**:

```text
<type>(<scope>): <description>
```

- `type` — `feat` `fix` `docs` `refactor` `chore` `test` `build` `ci`. Append `!` before the colon for a breaking change (`refactor(core)!: …`).
- `scope` — the package the change lands in: `core`, `design`, `meta`, `ops`, `product`, `workflow`. For anything outside `packages/`, use the area instead: `scripts`, `docs`, `ci`.

**The type sizes nothing.** Versions are calendar-derived, so `feat` and `fix` no longer mean "minor" and "patch"; they decide which heading a commit lands under in the generated release notes, and nothing else. That is worth keeping, so the convention is now *enforced* rather than merely read: the `commits` gate refuses a subject outside the type list, and refuses a scope that names nothing the commit touched.

**Which package a commit releases is decided by the paths it touched, not by the scope.** Paths are what actually changed and cannot be mistyped. A scope is optional; when present it has to be one of the packages under `packages/` the commit touched, or an area outside it — `scripts`, `ci`, `meta`, `docs`, `repo`.

The gate lints a range, not all of history: CI passes the pull request's base (and its title), and a run with no range reports the gate skipped rather than inventing one. Locally: `uv run scripts/check.py --repo . --since origin/main`.

**Prose for the release notes goes in the pull request body**, under a `## Release notes` heading. The release copies that section, and only that section, into the GitHub release of every package the pull request touched; ordinary review discussion in the same body stays out.

## Releasing

Versions are **calendar-derived**: `YYYY.M.N`, where `N` counts that package's releases within the UTC month, from 1. `llmctl-core@2026.9.1`, then `2026.9.2`. No zero padding, so the string stays semver-shaped for the hosts that parse it as one.

There is no API to break here and no consumer who can act on "minor" versus "patch"; what a reader of a steering package wants to know is how old it is. The commit types are still enforced, but they group the release notes rather than sizing a number.

Packages version **independently** (`marketplace.versioning.strategy: per_package`). A change to `ops` releases `ops` only, so a version always means something in that package changed.

### A release writes nothing to this repository

`packages/*/apm.yml` carries `version: 0.0.0`, a placeholder. The real version is stamped into a scratch export at pack time, and the record of it is the annotated `<name>@<version>` tag plus the GitHub release beside it.

That is what lets a release run on a push to protected `main` with no pull request, no bypass and no second CI cycle — pushing a tag is not pushing a branch.

The marketplace is the opposite case: it is generated output, entirely, so it is committed and pushed directly. Protecting it would gate a robot against itself.

```bash
apm run check       # every gate, over this workspace alone
apm run versions    # what each package's next version would be, and why
apm run release     # what a release would publish, and its notes. Writes nothing
```

The real release runs in CI, on a push to `main`. To rehearse the whole thing locally against a throwaway clone of the marketplace:

```bash
uv run scripts/release.py --repo . --marketplace ../scratch-marketplace --no-push
```

`--package NAME --force` re-releases a package with no commits; `--package NAME --version 2026.9.7` releases it at an exact version, which must be unused and must sort above its last tag — the highest tag is the baseline, so a lower one would be invisible to the next run.

**Tags are the baseline, and the clone has to have them.** Versions are derived from *local* tags, so a clone fetched without them measures from nothing: every package reads its entire history. Shallow clones and `--no-tags` fetches both land there — which is why the plan runs `git fetch --tags` first. Run releases from a full clone as well; `git log` on a shallow one cannot see past the fetch depth.

The tags created are annotated, because the marketplace is pushed with `--follow-tags`, which carries annotated tags only. Mixing them with the lightweight tags already on the remotes is harmless: `--sort=-v:refname` and `<tag>..HEAD` treat them alike, and version sort puts `2026.9.1` above `0.4.0` without a special case.

A repo that has **never** been released has no baseline for a package with no commits to release. Seed one by hand, once:

```bash
git tag -a llmctl-personal@2026.9.1 -m "llmctl-personal 2026.9.1" <commit>
git push origin --tags
```

### Lockfiles

Every package commits `apm.lock.yaml`, and it is the record of which upstream commit each pinned dependency resolved to. Packing installs from it and refuses to continue if installing moves any of those commits, so a bundle cannot ship something nobody reviewed.

**`apm install --frozen` is not what enforces that**, and this is the one place that fact is written down. A frozen install checks that every dependency in `apm.yml` *appears* in the lockfile, keyed by repository and subpath, never at which commit — so a pin moved without a lockfile refresh passes it. It also cannot restore *any* dependency from a cold cache once the package declares an MCP server — isolated on 0.31.0 to the `dependencies.mcp` block alone, so it hits `core` and `ops` and nothing else ([TODO 4l](TODO.md)). That is why packing installs normally and compares the resolved commits before and after, and why the workflows' deploy step is not frozen either. The `lockfiles` gate compares manifest against lockfile directly, offline, and refuses any pin that is not a full commit SHA. `apm audit --ci` checks the same thing where a package is already installed, and the pack gate runs it over each scratch export.

New lockfiles carry no `generated_at`, so two independent runs produce the same bytes. Deleting that line from an older one is permanent; APM does not add it back.

A lockfile moves only through `apm run update`, and always in the same commit as the `apm.yml` pin it belongs to. Never hand-edit one.

### Releasing another workspace

Nothing in these scripts is specific to this repo. A private sibling laid out the same way — its own `packages/`, `LICENSE`, `LICENSES/`, `dependency-licenses.yml` and `*.marketplace.*` sources, no `scripts/` — releases with this code by pointing the flags at it:

```bash
uv run ../.llmctl/scripts/release.py --repo . --marketplace ../<its-marketplace>
```

Nothing is shared but the code. Licence texts, dependency records and marketplace sources are read from the workspace only, so a private repo's upstreams never resolve against this one's.

## Continuous Integration

GitHub Actions runs the same entry points a contributor runs. The scripts declare their own dependencies in a PEP 723 header, so every step is `uv run` and nothing is installed first.

| Workflow | Trigger | What it runs | Locally |
| --- | --- | --- | --- |
| [checks.yml](.github/workflows/checks.yml) | pull request, manual | every gate | `apm run check` |
| [release.yml](.github/workflows/release.yml) | push to `main`, manual | every gate, then the release | `apm run release` (previews) |

**There is one gate set, and it lives in [check.py](scripts/check.py).** The marketplace-shaped gates pack into a scratch directory and validate that, so one checkout runs everything — the tooling's own lint, frontmatter conventions, the commit convention, licence obligations, lockfiles against their pins, and a full pack that every bundle must survive.

A push to `main` runs those same gates inside `release.yml`, immediately before publishing what they passed on, so `checks.yml` does not duplicate it.

A gate declares what it needs, and the runner decides what a missing need means: no `--since` skips the commit gate and says so, a missing `claude` CLI skips bundle validation and says so, a missing `apm` fails the pack gate outright. Skipped is never silent and never green-by-omission.

Both workflows here, and the private workspace's two, are thin: the shared steps live in composite actions under [.github/actions/](.github/actions/), referenced by path after the checkout. That needs no cross-repository Actions permission, which a reusable workflow between two private repos would.

The private workspace holds no `scripts/` — it checks this repo out beside itself and runs its code and its actions, exactly as a sibling clone does locally. That checkout needs no secret and names no ref: this repository is public, so the workflow's own token reads it, and its default branch is what runs.

**One APM version, pinned in one place.** What a bundle contains depends on the packer that made it, so the gates have to pass on the version that will pack it: the pin is the `apm-version` default in [.github/actions/setup](.github/actions/setup/action.yml), and every workflow in both workspaces inherits it. Moving it is a commit, and the gates on that commit are the proof — not a scheduled run against whatever was newest that morning.

**The marketplace repositories have no CI at all.** There is nothing left there to check: every file in them is regenerated from this repository on every release, and anything else is deleted.

### Secrets

- **`MARKETPLACE_TOKEN`** — `contents: write` on the marketplace repo. Set on this repo and on the private workspace. A release regenerates and pushes the marketplace, so even a dry run has to read it.

The release needs no token of its own beyond the workflow's: it pushes tags and creates releases, both of which `contents: write` on `GITHUB_TOKEN` covers.
