# TODO

## 1 — Add New Upstream Content as APM Dependencies

**Goal:** Consume beneficial upstream content via `apm.yml` `dependencies.apm` rather than authoring it locally.

**Priority: medium.** The vendored upstream *packages* (`angular-*`, `frontend-design`, `i-*`) are already deleted — what remains locally is either original or intentionally *adapted* (`metadata.provenance.adaptedFrom`, 18 files) content, plus 5 `mirror:` reference docs. So this is about pulling in **new** upstream content where it adds value, not removing duplicates.

### First pass — landed 2026-08-01

Eight upstream skills adopted as pinned `dependencies.apm` entries, using the git subdir form `owner/repo/path/to/skill#<sha>` (resolution + deployment verified against APM 0.26; `references/` subdirectories travel with the skill):

| Package | Skills |
| --- | --- |
| `core` | `grilling`, `grill-me` ([mattpocock/skills](https://github.com/mattpocock/skills), MIT) |
| `workflow` (new) | `using-git-worktrees`, `receiving-code-review` ([obra/superpowers](https://github.com/obra/superpowers), MIT); `tdd`, `resolving-merge-conflicts` (mattpocock, MIT); `lint-fix` ([rshade/agent-skills](https://github.com/rshade/agent-skills), Apache-2.0) |
| `ops` | `terraform-skill` ([antonbabenko/terraform-skill](https://github.com/antonbabenko/terraform-skill), Apache-2.0) |

Deliberately rejected: the Superpowers bootstrap (`using-superpowers` + session-start hook — mandates skill invocation before any response, conflicts with local steering); mattpocock's tracker-coupled flow (`code-review`, `to-spec`, `to-tickets`, `triage`, `implement`, `wayfinder` — require `/setup-matt-pocock-skills`); rshade's linter wrappers (`markdownlint`, `actionlint`, `shellcheck`, `commitlint` — deterministic checks belong in CI per **5**, not the skill budget); [ComposioHQ/awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills) (index, not a dependency — no root LICENSE, and its Anthropic-authored skills should come from [anthropics/skills](https://github.com/anthropics/skills)); [Jeffallan/claude-skills](https://github.com/Jeffallan/claude-skills) (stale, unevaluated persona packs); [santifer/career-ops](https://github.com/santifer/career-ops) (an application, not steering, and not subdir-consumable).

### Tasks

- [ ] **1a — Survey remaining upstream sources.** First pass above covers general steering. Still open: the 5 items tracked only via `metadata.provenance.mirror` — check whether a maintained package can replace each.
- [x] **1b — Add confirmed packages to `apm.yml`** and verify installation. Done for the first pass; re-verify with `apm install -g` after the next batch.
- [ ] **1c — Adapt `subagent-driven-development` into `batch-task-execution`.** [obra/superpowers](https://github.com/obra/superpowers/blob/main/skills/subagent-driven-development/SKILL.md) dispatches a *fresh* subagent per task that never inherits session context (the caller constructs exactly the context it needs), then runs a two-stage review after each task — spec compliance first, then code quality — followed by one broad whole-branch review at the end. Take the dispatch-and-review discipline into the local skill; do **not** consume it as a dependency (it cross-references `writing-plans` / `executing-plans` / `finishing-a-development-branch`, which are not adopted). Record as `metadata.provenance.adaptedFrom`.
- [ ] **1d — Add `agent-rules` as an additional `adaptedFrom` source for `meta-instruction`.** [netresearch/agent-rules-skill](https://github.com/netresearch/agent-rules-skill) (v3.13.x, MIT AND CC-BY-SA-4.0, `evals/` + harness-verify CI) generates and maintains AGENTS.md / `.github/copilot-instructions.md` per the agents.md convention, including scoped rule files. Mine its scoping model and section structure for the [meta-instruction skill](packages/meta/.apm/skills/meta-instruction/SKILL.md) — it covers bootstrapping a repo from nothing, which `meta-instruction` does not. Not consumed as a dependency: it shells out to `bash 4.3+`/`jq` and carries a dual-licence attribution obligation.
- [ ] **1e — Research prose de-slopping skills before adopting one.** [blader/humanizer](https://github.com/blader/humanizer) (MIT, 32.5k★, v2.9.x) is the obvious candidate — detects and rewrites inflated symbolism, promotional language, vague attribution, em-dash overuse, rule of three, negative parallelism and filler, based on Wikipedia's "Signs of AI writing" — but its SKILL.md is a single ~29 KB body with no progressive disclosure, and it is not the only implementation in this space. Survey the alternatives, compare on trigger precision, body size, and whether the rules are opinionated-but-checkable, then adopt or adapt one. Target `core` (applies to README/CONTRIBUTING prose) or `product` (PRD prose) depending on the winner's scope.
- [x] **1f — Publish `packages/workflow` (and every other package) to marketplace-only surfaces.** Done: the marketplace moved to the sibling [`.llmctl-marketplace`](https://github.com/siegenthalerroger/.llmctl-marketplace) repository and `scripts/pack-marketplace.py` vendors each package's APM dependencies into a committed bundle there. Remaining work is tracked in **7**.

---

## 2 — Default Permissions / Auto-Approved Commands

**Goal:** Provide a curated set of default permissions — safe, read-only commands (e.g. `git diff`, `diff`, `git status`, `git log`, `ls`) auto-approved without prompting — that deploy to all supported harnesses (`claude`, `copilot`).

**Priority: medium (concrete user value).**

### Background

Each harness expresses its command allow-list differently, and it's unconfirmed whether APM can deploy permission/settings blocks per target (it currently handles skills, agents, prompts, instructions, hooks, and MCP).

| Tool            | File            | Setting (to verify)                                           |
| --------------- | --------------- | ------------------------------------------------------------- |
| Claude Code     | `settings.json` | `permissions.allow` — e.g. `Bash(git diff:*)`, `Bash(diff:*)` |
| VS Code Copilot | `settings.json` | terminal auto-approve allow-list (confirm exact key)          |
| APM             | `apm.yml`       | confirm whether permission/settings deployment is supported   |

Related: the `fewer-permission-prompts` skill derives allow-lists from transcripts — useful as a source for the default set.

### Guardrail hooks — the portable deny-side complement

An allow-list is per-harness settings config (possibly undeployable via APM); a deterministic **deny** guard is a hook, which APM already deploys to every target. [dirien/my-claude-apm-setup](https://github.com/dirien/my-claude-apm-setup) wires two POSIX scripts through a single [`.apm/hooks/guardrails.json`](https://github.com/dirien/my-claude-apm-setup/blob/main/.apm/hooks/guardrails.json):

| Hook | Script | Behaviour |
| ------------- | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ |
| `PreToolUse`  | [`scripts/guard.sh`](https://github.com/dirien/my-claude-apm-setup/blob/main/scripts/guard.sh)     | Blocks destructive Bash — `rm -rf /`, `git push --force`, `git reset --hard`, `mkfs`, `dd if=` — by exiting 2        |
| `PostToolUse` | [`scripts/post-edit.sh`](https://github.com/dirien/my-claude-apm-setup/blob/main/scripts/post-edit.sh) | Blocks writes adding a credential (AWS key, private key, `ghp_…`, `sk-…`, Slack token); formats with `gofmt`/`prettier`/`ruff` when present |

Both read the hook JSON on stdin and exit 2 to block. Note the repo convention prefers cross-platform Python/Node hook scripts over POSIX shell ([AGENTS.md](AGENTS.md)), so port rather than copy.

### Tasks

- [ ] **2a — Investigate APM support** for deploying permission/settings configuration across targets; if unsupported, track upstream (file/find an issue) or deploy out-of-band.
- [ ] **2b — Define the default allow-list** of safe read-only commands.
- [ ] **2c — Map the allow-list to each target's native format** and verify the deployed result with `apm install -g`.
- [ ] **2d — Add a deny-side guardrail hook pair** (destructive-command guard + secret-write guard) as cross-platform scripts, following the pattern above and the [meta-hook skill](packages/meta/.apm/skills/meta-hook/SKILL.md). Independent of 2a — hook deployment is already supported.

---

## 3 — LSP Server Configuration Support

**Goal:** Document and provide cross-tool compatible LSP (Language Server Protocol) server configuration guidance within `.llmctl`, analogous to the MCP support — so agent harnesses can be configured with language servers (diagnostics, hover, go-to-definition, etc.) as a deployable unit via APM.

**Priority: medium-low (investigative, mirrors the MCP pattern).**

### Background

Agent harnesses increasingly support configuring LSP servers to give agents richer code intelligence. As with MCP, the config format likely differs across tools in file location and structure. **APM support is confirmed** (see below); the per-harness rows still need verification against current docs before authoring.

| Tool             | File          | Format        | Key/Section                                                                 |
| ---------------- | ------------- | ------------- | ----------------------------------------------------------------------------- |
| VS Code Copilot  | _(to verify)_ | _(to verify)_ | _(to verify)_                                                                 |
| Claude Code      | _(to verify)_ | _(to verify)_ | _(to verify)_                                                                 |
| OpenAI Codex CLI | _(to verify)_ | _(to verify)_ | _(to verify)_                                                                 |
| APM              | `apm.yml`     | YAML          | `dependencies.lsp` — **supported**, emits `.lsp.json` (verified on APM 0.22)  |

**APM block shape**, from [dirien/my-claude-apm-setup/apm.yml](https://github.com/dirien/my-claude-apm-setup/blob/main/apm.yml) (four servers: `gopls`, `typescript-language-server`, `pyright`, `csharp-ls`):

```yaml
dependencies:
  lsp:
    - name: gopls
      command: gopls
      args: ["serve"]
      extensionToLanguage:
        ".go": go
```

APM writes the config only — the binaries are the user's responsibility, exactly like the MCP pattern. Open questions: whether `.lsp.json` is a single harness-neutral file or gets per-target placement on 0.26, and which harnesses actually read it.

**Companion content — adapt, do not consume.** Config alone just adds an unused capability; the *usage* half is [antonbabenko/agent-plugins → `code-intelligence`](https://github.com/antonbabenko/agent-plugins/tree/master/plugins/code-intelligence) (Apache-2.0): tool precedence (LSP for symbol relationships, `rg` for exact text, semantic search for "where might this live"), position-anchored LSP calls, a three-part degradation gate before declaring the server unavailable, first-line disclosure of any tool substitution, and a proof requirement before claiming a tool is missing.

**Verdict: not properly cross-harness — copy but adapt to more generic tool naming.** Its *vocabulary* is already neutral ("host exposes no language-server tool", "semantic/neural search, if host provides", "host-approved text search") — it names no Claude tool. Its *procedure*, however, is LSP-protocol-shaped: `documentSymbol` probes, cold-start retries, `prepareRename`, call hierarchy. On an IDE-integrated harness (VS Code Copilot) the equivalent intelligence arrives as IDE diagnostics and editor navigation rather than position-anchored protocol calls, so its degradation gate would classify a fully-capable IDE session as "no LSP at all → fall back to text search" and under-use what is actually there. The adaptation is a three-tier capability model — **LSP tool | IDE diagnostics/navigation | text search** — with the precedence, disclosure, and anti-phantom-shim rules kept as-is. Its `/setup-code-intelligence` command is POSIX-only (`uname -s`, `command -v`) and would need a cross-platform rewrite if wanted.

See also [terraform-skill's `references/code-intelligence-lsp.md`](https://github.com/antonbabenko/terraform-skill/blob/master/skills/terraform-skill/references/code-intelligence-lsp.md) for a domain-specific extension (the `terraform-ls` capability matrix) — that dependency is already installed via `packages/ops`.

### Tasks

- [ ] **3a — Investigate per-tool LSP config support and format** across `claude` and `copilot` (and Codex if relevant); fill in the matrix above from authoritative docs.
- [ ] **3b — Verify the `dependencies.lsp` block against the installed APM version** (0.26) — confirm output path(s), per-target behaviour, and whether transitive LSP deps survive like/unlike MCP; the shape above is verified only on 0.22.
- [ ] **3c — Create an LSP configuration reference** as a `meta-lsp` skill (matching the `meta-mcp` pattern: `packages/meta/.apm/skills/meta-lsp/SKILL.md` + references), documenting the per-tool config matrix and the APM block.
- [ ] **3d — Create a cross-tool LSP setup prompt** (e.g. `packages/meta/.apm/prompts/setup-lsp.prompt.md`), scoped to emit the APM dependency block and delegating schema knowledge to the `meta-lsp` skill.
- [ ] **3e — Update `README.md`** — add an LSP Servers row to the steering matrix and a subsection referencing the `meta-lsp` skill.
- [ ] **3f — Adapt `code-intelligence` into a local skill** (`packages/core`, or `packages/workflow` if it should load only for code work) once 3a–3c land: copy the precedence/anchoring/degradation/disclosure rules, generalise to the three-tier capability model above, and record `metadata.provenance.adaptedFrom: https://github.com/antonbabenko/agent-plugins/blob/master/plugins/code-intelligence/skills/code-intelligence/SKILL.md`. Gated on 3a — the tiers can only be named once the per-harness matrix is filled in.

---

## 4 — Upstream APM Tracking / Add When Needed

**Priority: waiting.** Ongoing tracking and items gated on a demonstrated need.

- [ ] **4a — Track upstream APM evolution (esp. deployed-file gitignore / local-settings targeting).** APM deploys Claude hook wiring only to `settings.json` (project) or `~/.claude/settings.json` (user) — it cannot target the git-ignored `settings.local.json` variant ([hook_integrator.py](https://github.com/microsoft/apm/blob/main/src/apm_cli/integration/hook_integrator.py) hardcodes `config_filename="settings.json"`). Watch microsoft/apm [#1342](https://github.com/microsoft/apm/issues/1342) (related: [#990](https://github.com/microsoft/apm/issues/990), [#290](https://github.com/microsoft/apm/issues/290)). When a `.local`-target option or deployed-file gitignore mode ships, revisit the `.gitignore` comment ([.gitignore:7-10](.gitignore#L7-L10)) and the deploy guidance in [CONTRIBUTING.md:127](CONTRIBUTING.md#L127). More broadly, periodically review APM releases for changes affecting this repo's deploy assumptions.
- [ ] **4b — First plugin:** Add a plugin bundle when tool/MCP capabilities are insufficient for a task. Authoring guidance lives in the [meta-plugin skill](packages/meta/.apm/skills/meta-plugin/SKILL.md).
- [ ] **4c — Track two APM 0.25 environment issues found during clean redeploy.**

  1. **Aggregator not `-g`-installable (aggregator removed, reinstate later).** A prototyped `packages/global` aggregator (an `apm.yml` with only `dependencies.apm` → `../core`, `../meta`) resolved its transitive *local-path* deps but deployed **zero** primitives at user scope (worked at project scope). It was **removed** to avoid documenting a broken command; global install names `core` + `meta` directly for now. **To reinstate:** recreate `packages/global/apm.yml` (deps: `./../core`, `./../meta`, + third-party global recs), point `~/.apm/apm.yml` at it, and make it the single-command global profile + home for third-party global recommendations. File/find an upstream APM issue for transitive local-path deploy at `-g`; do this once it's fixed.
  2. **`copilot-cowork` + multiple OneDrive mounts** aborts any global install at lockfile generation (`--exclude copilot-cowork` does not help). Workaround: export `APM_COPILOT_COWORK_SKILLS_DIR` to a single dir. Noted in README prerequisites.
- [ ] **4d — Track APM per-target agent tool-policy mapping.** APM 0.26.0 copies agent frontmatter verbatim to every target (no per-target normalization, unlike hooks), so a Copilot `tools:` array deploys unchanged to `~/.claude/agents/` and makes the agent unspawnable on Claude Code. Repo agents work around this by omitting `tools:` and scoping Claude via `disallowedTools` (see [meta-agent skill](packages/meta/.apm/skills/meta-agent/SKILL.md#tools-field)); the trade-off is that Copilot loses allow-list scoping (inherits all tools). Watch microsoft/apm [#2108](https://github.com/microsoft/apm/issues/2108) (portable agent semantics) under epic [#2112](https://github.com/microsoft/apm/issues/2112); related: [#293](https://github.com/microsoft/apm/issues/293) (consumer tool overrides), [#2261](https://github.com/microsoft/apm/issues/2261) (per-file target declaration — would let us stop deploying `plan`/`explore` to Claude), [#581](https://github.com/microsoft/apm/issues/581) (declined intra-file translation precedent). When per-target agent frontmatter mapping ships, restore precise Copilot allow-lists.

---

## 5 — CI for Steering-File Correctness and Deployability

**Goal:** Catch structurally broken or undeployable steering content before it lands, instead of relying on local edit-time hooks and manual `apm install -g` runs.

**Priority: medium-high (protects every other workstream).**

### Background

There is no `.github/workflows/` in the repo. The only automated validation is [.apm/hooks/validate-customization-frontmatter.py](.apm/hooks/validate-customization-frontmatter.py), a Claude Code `PostToolUse` hook — it fires only on files edited in a Claude session, so drift in untouched files, edits made from other harnesses, and APM version skew all go unnoticed until a deploy misbehaves (cf. **4c**, **4d**). Two distinct failure classes are worth checking separately:

| Class | Question | Signal |
| --- | --- | --- |
| Semantic correctness | Is each file well-formed per the repo's conventions? | Frontmatter fields, name↔directory match, kebab-case, description length/single-line, reserved words, provenance metadata |
| Deployability | Does APM actually see and place every item? | Every authored primitive appears at the expected path for each target after an install into a throwaway home/workspace |

**APM ships most of the deployability gate already.** Commands verified against APM 0.22 in [dirien/my-claude-apm-setup → docs/APM-ADOPTION.md](https://github.com/dirien/my-claude-apm-setup/blob/main/docs/APM-ADOPTION.md); re-verify on 0.26 before wiring:

| Command | What it gives us |
| ---------------------------------------------------- | -------------------------------------------------------------------------------------- |
| `apm compile -t claude,copilot --validate`            | Validates every primitive, writes nothing — cheapest gate, covers part of **5a**        |
| `apm install --frozen`                                | Reproducible install from `apm.lock.yaml` (the `npm ci` equivalent) — basis for **5c**   |
| `apm audit --ci`                                      | Fails on orphaned / undeployed packages                                                  |
| `apm compile --clean --local-only` + `git diff --exit-code` | Drift check for generated files                                                    |
| `apm lock export -f cyclonedx\|spdx --timestamp`      | Offline, reproducible SBOM of agent dependencies — only meaningful once **1b** lands     |
| `apm outdated` → `apm update --dry-run` → `apm update -y` | Maintenance loop for SHA-pinned deps from **1b**                                     |

Two caveats from that repo: `devDependencies` entries are reported as orphaned by `apm audit --ci` under a frozen install, and generated files carry an APM-version stamp that trips a hard `git diff` gate whenever the runner's APM is newer than the author's — which is why they keep the drift check local rather than in CI.

### Tasks

- [ ] **5a — Run the frontmatter validator over the whole tree in CI.** Add a batch/`--all` mode (or a thin wrapper) to [validate-customization-frontmatter.py](.apm/hooks/validate-customization-frontmatter.py) so the same rules apply repo-wide, not just to edited files. Keep the hook and the CI entrypoint sharing one implementation.
- [ ] **5b — Extend validation to metadata this repo relies on but the hook ignores** — `metadata.provenance` (`adaptedFrom` / `mirror` / source URLs, per the [meta-upstream-sync source-url reference](.apm/skills/meta-upstream-sync/references/source-url-reference.md)), `model:` frontmatter on agents, and the `tools:`-omission convention from **4d**.
- [ ] **5c — Add a deployability check.** Install each package into a disposable `HOME`/workspace and assert that every authored primitive lands in the expected per-target location, comparing against an inventory derived from `packages/*/.apm/`. Confirm the cheapest reliable mechanism first (lockfile inspection, a dry-run flag, or a real install into a temp dir) rather than assuming one exists.
- [ ] **5d — Add link/reference integrity checking** for relative markdown links (the README/TODO/CONTRIBUTING cross-links and skill→reference paths); optionally check external links on a schedule only, to avoid flaky PR runs.
- [ ] **5e — Wire it into GitHub Actions**: run 5a–5d on PRs, plus a scheduled run so a new APM release that breaks deployment surfaces on its own rather than during the next manual deploy (ties into **4a**).

---

## 6 — Eval Framework for Steering Effectiveness

**Goal:** Be able to answer "did that change actually make the steering better?" with evidence, and detect when a model upgrade makes existing steering redundant, harmful, or newly necessary.

**Priority: medium (high leverage, meaningful build cost — scope a minimal version first).**

### Background

Section 5 checks that content is *well-formed and deployed*; nothing checks that it is *effective*. Steering quality is currently judged by hand, so revisions are unfalsifiable and each new model release silently shifts the baseline (the [meta-update-models skill](.apm/skills/meta-update-models/SKILL.md) tracks model *identifiers*, not behaviour). A usable framework needs: a fixture set of representative tasks per package, a rubric or programmatic assertion per fixture, and A/B runs (steering on vs off, revision A vs B) across at least two model versions. Harness choice is open — a headless agent SDK loop, an off-the-shelf eval runner, or LLM-as-judge scoring — and should be decided before authoring fixtures.

Cost and non-determinism mean this is unlikely to belong on every PR; assume a manually triggered and/or scheduled job, reported as a tracked score over time rather than a pass/fail gate.

### Prior art — three upstream approaches, cheapest first

| Approach | Source | Shape | Cost / fidelity |
| --- | --- | --- | --- |
| **Per-skill eval fixtures** | [rshade/agent-skills](https://github.com/rshade/agent-skills) — e.g. [`skills/markdownlint/evals/`](https://github.com/rshade/agent-skills/tree/main/skills/markdownlint/evals) | One `evals.json` per skill: `{prompt, expected_output, files[], expectations[]}` with fixture files alongside; `expectations` are natural-language assertions for a judge | Cheapest. Fixtures live next to the skill, so they survive refactors. Good candidate for **6a**'s format |
| **Pressure tests + coverage matrix** | [antonbabenko/terraform-skill](https://github.com/antonbabenko/terraform-skill/tree/master/tests) | `baseline-scenarios.md` (expected *and* forbidden signals per scenario) plus `rationalization-table.md` mapping each hallucination surface → the scenario that exercises it → the guard line that must catch it, marked ✅/◐/❌ | Medium. The coverage matrix is the transferable idea: it makes "which steering line earns its place" auditable — directly serves **6c** |
| **Subagent behaviour drills** | [obra/superpowers](https://github.com/obra/superpowers) — `skills/*/test-pressure-*.md`, `tests/explicit-skill-requests/`, [superpowers-evals](https://github.com/prime-radiant-inc/superpowers-evals/) | Skill run against fresh subagents under adversarial prompts that tempt it to skip the process; also a token-usage analyzer | Highest fidelity, highest cost. Their `writing-skills` skill frames skill authoring as TDD: write the pressure scenario, watch the baseline fail, write the skill, watch it pass |

All three are "prompt + assertions, judged by a model" — none requires a bespoke harness, which lowers the bar for **6a** considerably.

### Tasks

- [ ] **6a — Choose the eval harness and scoring model** (runner, judge vs deterministic assertions, how a run is pinned to a model version and a repo revision). Decide before writing fixtures — it dictates their format.
- [ ] **6b — Build evals for this repo's own content.** Fixtures per package (`core`, `meta`, `ops`, `product`) covering the behaviours the steering is meant to produce, run with and without the steering loaded, scored and recorded so revisions can be compared. Start with one package end-to-end before fanning out.
- [ ] **6c — Track scores across model versions.** Re-run the suite on new model releases to see where steering stops earning its place (or where a regression needs new steering), and feed the outcome back into `meta-update-models` and the [reflect prompt](packages/meta/.apm/prompts/reflect.prompt.md).
- [ ] **6d — Fold the skill-as-TDD method into the `meta-*` skills** once 6a exists. [obra/superpowers `writing-skills`](https://github.com/obra/superpowers/blob/main/skills/writing-skills/SKILL.md) treats authoring as test-driven: write the pressure scenario, run it against a *fresh subagent* to establish the failing baseline, write the skill, re-run until the agent complies, then refactor to close the loopholes it rationalised through — with [`testing-skills-with-subagents.md`](https://github.com/obra/superpowers/blob/main/skills/writing-skills/testing-skills-with-subagents.md) as the procedure. That closes the gap in [meta-skill](packages/meta/.apm/skills/meta-skill/SKILL.md), which specifies structure and description rules but has no way to show a skill actually changes behaviour. Extend to the other `meta-*` skills (agent, prompt, instruction, hook) where the same subagent-pressure method applies. Blocked on 6a: the method needs a harness to run the drills. Record as `metadata.provenance.adaptedFrom`.
- [ ] **6e — Extend evals to third-party / integrated content.** Cover APM dependencies (**1b**) and `adaptedFrom`/`mirror` content so an upstream update can be scored before adoption, and so vendored adaptations can be compared against their upstream original. Gated on 6a–6b proving out.

---

## 7 — Marketplace Repository: Licensing, Versioning, Release Automation

**Goal:** Make [`.llmctl-marketplace`](https://github.com/siegenthalerroger/.llmctl-marketplace) publishable without hand-maintenance — correct attribution in every bundle, versions that move on their own, and a release path that does not depend on someone remembering to run a script.

**Priority: medium.** The mechanism works and is verified; what is missing is everything that keeps it correct over time.

### Background — what exists now

Marketplace manifests and packed bundles live in a **separate private repository**, generated by [scripts/pack-marketplace.py](scripts/pack-marketplace.py) (wired as `apm run pack-marketplace`). The split exists because a plugin host clones the marketplace repo and reads each `packages[].source` path *as committed* — it never runs `apm install` — so packages carrying APM dependencies must ship as bundles with those skills vendored in. `apm pack` also rejects `..` in a marketplace output path, so the manifest has to be generated in the marketplace repo itself.

Verified against APM 0.26 and Claude Code `plugin validate`:

| Behaviour | Result |
| --- | --- |
| Dependencies vendored into a bundle | ✅ `apm install` + `apm pack` carries every dependency skill with its `references/` |
| `packages[].source` validation | ❌ none — an unresolvable path emits a manifest entry silently |
| `version` in the manifest | Only when declared explicitly per package; it is **not** read from a packed bundle |
| Bundle directory name | Always `<name>-<version>` — no flag to flatten, hence the `source:` rewrite in the script |
| What packs | `skills/`, `commands/`, `agents/`, `instructions/`, `.mcp.json`, `plugin.json`, enriched `apm.lock.yaml` |
| Packed MCP fidelity | Partial — `headers` are dropped, so an API-keyed server (e.g. `context7`) will not authenticate |
| `claude plugin validate .` | Passes, with one warning: it wants `metadata.description`, APM emits top-level `description` |

### Tasks

- [ ] **7a — Licensing.** Decide the licence for `.llmctl` itself (no `LICENSE` file exists, so the SBOM records NOASSERTION and the marketplace README currently has to say "unlicensed by default"), add it to both repos, then **generate** `THIRD-PARTY-NOTICES.md` from each bundle's embedded `apm.lock.yaml` instead of maintaining it by hand — the lockfile already records `repo_url` and per-file SHA-256 for every vendored skill. `apm pack` copies skill files only, so upstream `LICENSE` text has to be added deliberately: MIT needs the notice to travel, Apache-2.0 needs the licence, attribution notices, and a statement of changes.
- [ ] **7b — Versioning.** `marketplace.versioning.strategy` is `lockstep`, so every package moves together and the packing script keeps `source:`/`version:` in sync. Decide what actually drives a bump (conventional commits? a release command? `apm publish`?), then automate it — including the upstream-dependency loop (`apm outdated` → `apm update` → re-pack → bump) so a pinned SHA moving is a normal release rather than a manual edit. Evaluate `per_package` versioning if lockstep becomes noisy.
- [ ] **7c — Release automation.** A workflow that packs, validates (`apm pack --check-versions --check-clean`, `claude plugin validate`), commits, and pushes the marketplace repo — either from `.llmctl` CI (needs a cross-repo token) or a scheduled job in the marketplace repo. Ties into **5**: the same gates belong on PRs here.
- [ ] **7d — Go public and verify end to end.** The marketplace repo is private, which is fine for `claude plugin marketplace add <local path>` but blocks Cowork and any other host that clones anonymously. Flip it public when the licensing in **7a** is settled, then install a plugin end to end from Cowork and record what actually loaded (skills, commands, and whether 0.26's packed `agents/`, `instructions/`, and `.mcp.json` are honoured — the previous finding that they do not travel predates 0.26).
- [ ] **7e — Manifest schema mismatch.** `claude plugin validate` warns that the marketplace description belongs under `metadata.description` while APM emits it top-level. Confirm whether Claude reads the top-level field anyway; if not, raise it upstream with microsoft/apm rather than post-processing the generated file.
