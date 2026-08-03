# TODO

## 1 — Default Permissions / Auto-Approved Commands

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

- [ ] **1a — Investigate APM support** for deploying permission/settings configuration across targets; if unsupported, track upstream (file/find an issue) or deploy out-of-band.
- [ ] **1b — Define the default allow-list** of safe read-only commands.
- [ ] **1c — Map the allow-list to each target's native format** and verify the deployed result with `apm install -g`.
- [ ] **1d — Add a deny-side guardrail hook pair** (destructive-command guard + secret-write guard) as cross-platform scripts, following the pattern above and the [meta-hook skill](packages/meta/.apm/skills/meta-hook/SKILL.md). Independent of 1a — hook deployment is already supported.

---

## 2 — LSP Server Configuration Support

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

- [ ] **2a — Investigate per-tool LSP config support and format** across `claude` and `copilot` (and Codex if relevant); fill in the matrix above from authoritative docs. Lead from the 2026-08-01 upstream survey: [github/awesome-copilot `skills/lsp-setup`](https://github.com/github/awesome-copilot/tree/main/skills/lsp-setup) (MIT, subdir-consumable) — check whether it already documents the per-harness matrix.
- [ ] **2b — Verify the `dependencies.lsp` block against the installed APM version** (0.26) — confirm output path(s), per-target behaviour, and whether transitive LSP deps survive like/unlike MCP; the shape above is verified only on 0.22.
- [ ] **2c — Create an LSP configuration reference** as a `meta-lsp` skill (matching the `meta-mcp` pattern: `packages/meta/.apm/skills/meta-lsp/SKILL.md` + references), documenting the per-tool config matrix and the APM block.
- [ ] **2d — Create a cross-tool LSP setup prompt** (e.g. `packages/meta/.apm/prompts/setup-lsp.prompt.md`), scoped to emit the APM dependency block and delegating schema knowledge to the `meta-lsp` skill.
- [ ] **2e — Update `README.md`** — add an LSP Servers row to the steering matrix and a subsection referencing the `meta-lsp` skill.
- [ ] **2f — Adapt `code-intelligence` into a local skill** (`packages/core`, or `packages/workflow` if it should load only for code work) once 2a–2c land: copy the precedence/anchoring/degradation/disclosure rules, generalise to the three-tier capability model above, and record `metadata.provenance.adaptedFrom: https://github.com/antonbabenko/agent-plugins/blob/master/plugins/code-intelligence/skills/code-intelligence/SKILL.md`. Gated on 2a — the tiers can only be named once the per-harness matrix is filled in.

---

## 3 — Upstream APM Tracking / Add When Needed

**Priority: waiting.** Ongoing tracking and items gated on a demonstrated need.

- [ ] **3a — Track upstream APM evolution (esp. deployed-file gitignore / local-settings targeting).** APM deploys Claude hook wiring only to `settings.json` (project) or `~/.claude/settings.json` (user) — it cannot target the git-ignored `settings.local.json` variant ([hook_integrator.py](https://github.com/microsoft/apm/blob/main/src/apm_cli/integration/hook_integrator.py) hardcodes `config_filename="settings.json"`). Watch microsoft/apm [#1342](https://github.com/microsoft/apm/issues/1342) (related: [#990](https://github.com/microsoft/apm/issues/990), [#290](https://github.com/microsoft/apm/issues/290)). When a `.local`-target option or deployed-file gitignore mode ships, revisit the [`.gitignore`](.gitignore) comment above the `.claude/` entries and the deploy guidance in [CONTRIBUTING.md](CONTRIBUTING.md#hooks-hookjson). More broadly, periodically review APM releases for changes affecting this repo's deploy assumptions.
- [ ] **3b — First plugin:** Add a plugin bundle when tool/MCP capabilities are insufficient for a task. Authoring guidance lives in the [meta-plugin skill](packages/meta/.apm/skills/meta-plugin/SKILL.md).
- [ ] **3c — Track two APM 0.25 environment issues found during clean redeploy.**

  1. **Aggregator not `-g`-installable (aggregator removed, reinstate later).** A prototyped `packages/global` aggregator (an `apm.yml` with only `dependencies.apm` → `../core`, `../meta`) resolved its transitive *local-path* deps but deployed **zero** primitives at user scope (worked at project scope). It was **removed** to avoid documenting a broken command; global install names `core` + `meta` directly for now. **To reinstate:** recreate `packages/global/apm.yml` (deps: `./../core`, `./../meta`, + third-party global recs), point `~/.apm/apm.yml` at it, and make it the single-command global profile + home for third-party global recommendations. File/find an upstream APM issue for transitive local-path deploy at `-g`; do this once it's fixed.
  2. **`copilot-cowork` + multiple OneDrive mounts** aborts any global install at lockfile generation (`--exclude copilot-cowork` does not help). Workaround: export `APM_COPILOT_COWORK_SKILLS_DIR` to a single dir. Noted in README prerequisites.
- [ ] **3d — Track APM per-target agent tool-policy mapping.** APM 0.26.0 copies agent frontmatter verbatim to every target (no per-target normalization, unlike hooks), so a Copilot `tools:` array deploys unchanged to `~/.claude/agents/` and makes the agent unspawnable on Claude Code. Repo agents work around this by omitting `tools:` and scoping Claude via `disallowedTools` (see [meta-agent skill](packages/meta/.apm/skills/meta-agent/SKILL.md#tools-field)); the trade-off is that Copilot loses allow-list scoping (inherits all tools). Watch microsoft/apm [#2108](https://github.com/microsoft/apm/issues/2108) (portable agent semantics) under epic [#2112](https://github.com/microsoft/apm/issues/2112); related: [#293](https://github.com/microsoft/apm/issues/293) (consumer tool overrides), [#2261](https://github.com/microsoft/apm/issues/2261) (per-file target declaration — would let us stop deploying `plan`/`explore` to Claude), [#581](https://github.com/microsoft/apm/issues/581) (declined intra-file translation precedent). When per-target agent frontmatter mapping ships, restore precise Copilot allow-lists.

---

## 4 — CI for Steering-File Correctness and Deployability

**Goal:** Catch structurally broken or undeployable steering content before it lands, instead of relying on local edit-time hooks and manual `apm install -g` runs.

**Priority: medium-high (protects every other workstream).**

### Background

Two validation layers exist as of 2026-08-02, and neither covers this workstream:

- [.apm/hooks/validate-customization-frontmatter.py](.apm/hooks/validate-customization-frontmatter.py), a Claude Code `PostToolUse` hook — it fires only on files edited in a Claude session, so drift in untouched files, edits made from other harnesses, and APM version skew all go unnoticed until a deploy misbehaves (cf. **3c**, **3d**).
- [scripts/release-check.py](scripts/release-check.py) and the gates it drives (licences, parser parity, notices, versions, manifest drift, bundle validity, lockfile). These are repo-wide and run in CI, but they only cover provenance/licensing and the release path — not the frontmatter conventions below.
fir
Two distinct failure classes are worth checking separately:

| Class | Question | Signal |
| --- | --- | --- |
| Semantic correctness | Is each file well-formed per the repo's conventions? | Frontmatter fields, name↔directory match, kebab-case, description length/single-line, reserved words, provenance metadata |
| Deployability | Does APM actually see and place every item? | Every authored primitive appears at the expected path for each target after an install into a throwaway home/workspace |

**APM ships most of the deployability gate already.** Commands verified against APM 0.22 in [dirien/my-claude-apm-setup → docs/APM-ADOPTION.md](https://github.com/dirien/my-claude-apm-setup/blob/main/docs/APM-ADOPTION.md); re-verify on 0.26 before wiring:

| Command | What it gives us |
| ---------------------------------------------------- | -------------------------------------------------------------------------------------- |
| `apm compile -t claude,copilot --validate`            | Validates every primitive, writes nothing — cheapest gate, covers part of **4a**        |
| `apm install --frozen`                                | Reproducible install from `apm.lock.yaml` (the `npm ci` equivalent) — basis for **4d**   |
| `apm audit --ci`                                      | Fails on orphaned / undeployed packages                                                  |
| `apm compile --clean --local-only` + `git diff --exit-code` | Drift check for generated files                                                    |
| `apm lock export -f cyclonedx\|spdx --timestamp`      | Offline, reproducible SBOM of the pinned APM dependencies in `packages/*/apm.yml`     |
| `apm outdated` → `apm update --dry-run` → `apm update -y` | Maintenance loop for the SHA-pinned deps in `packages/*/apm.yml`                                     |

Two caveats from that repo: `devDependencies` entries are reported as orphaned by `apm audit --ci` under a frozen install, and generated files carry an APM-version stamp that trips a hard `git diff` gate whenever the runner's APM is newer than the author's — which is why they keep the drift check local rather than in CI.

### Tasks

- [ ] **4a — Run the frontmatter validator over the whole tree in CI.** Add a batch/`--all` mode (or a thin wrapper) to [validate-customization-frontmatter.py](.apm/hooks/validate-customization-frontmatter.py) so the same rules apply repo-wide, not just to edited files. Keep the hook and the CI entrypoint sharing one implementation.
- [ ] **4b — Extend validation to metadata this repo relies on but the hook ignores** — `model:` frontmatter on agents and the `tools:`-omission convention from **3d**.

  **The provenance half of this task shipped.** [scripts/check-licenses.py](scripts/check-licenses.py) now hard-errors on an `adaptedFrom` block that parses to zero URLs and on an object entry with no `url`, and it parses through the shared [scripts/provenance.py](scripts/provenance.py) so the validator and the [drift audit](.apm/skills/meta-upstream-sync/scripts/check-updates.ps1) cannot disagree about what counts as tracked — enforced by release-check's `parity` gate. It also requires an upstream `license` wherever `fidelity` copies expression. Two lint-grade checks from the original list remain unimplemented, both warnings rather than errors:

  - a `took` value written as a block scalar (`|` / `>`) — both parsers are single-line and silently drop the content
  - a `took` value containing `Not taken` / `Original locally`, or a `%` measurement — removed from the convention on 2026-08-01 because they rot with no local change to trigger a refresh; see [CONTRIBUTING.md](CONTRIBUTING.md#scoping-an-adaptation-with-fidelity-and-took)

- [ ] **4c — Fix the drift audit's dead-URL blind spot.** Found 2026-08-01 while annotating `took`: [check-updates.ps1](.apm/skills/meta-upstream-sync/scripts/check-updates.ps1) never verifies the provenance path still **exists**. `GET /repos/{o}/{r}/commits?path=<deleted-path>` happily returns the commit that *deleted* the path, so the script reads a real date, compares it, and reports `up_to_date` — forever. Two of the repo's own entries were pointing at 404s and reporting healthy: `researcher-advanced` (upstream restructured 2026-05-29) and `code-reviewer` (moved into `skills/requesting-code-review/`). Both re-pointed; the blind spot remains. Fix: probe `contents/<path>` (or check whether the newest commit for the path is a deletion) and emit a distinct `source_missing` status with recommendation `repoint_or_drop_provenance`. Without this, provenance rots silently, which defeats the point of tracking it.
- [ ] **4d — Add a deployability check.** Install each package into a disposable `HOME`/workspace and assert that every authored primitive lands in the expected per-target location, comparing against an inventory derived from `packages/*/.apm/`. Confirm the cheapest reliable mechanism first (lockfile inspection, a dry-run flag, or a real install into a temp dir) rather than assuming one exists.
- [ ] **4e — Add link/reference integrity checking** for relative markdown links (the README/TODO/CONTRIBUTING cross-links and skill→reference paths); optionally check external links on a schedule only, to avoid flaky PR runs.
- [ ] **4f — Wire it into GitHub Actions**: run 4a–4e on PRs, plus a scheduled run so a new APM release that breaks deployment surfaces on its own rather than during the next manual deploy (ties into **3a**).

  **Partly done 2026-08-02** [.github/workflows/checks.yml](.github/workflows/checks.yml) now exists and runs [scripts/release-check.py](scripts/release-check.py) on PRs, pushes to `main`, and weekly — carrying the licence, parser-parity, notices, version-alignment, manifest-drift, plugin-validity and `apm audit --ci` gates. The workflow is a thin wrapper by design: every step shells out to `scripts/`, so a gate can always be run locally. What remains is adding 4a–4e's own checks as steps in that same file.

- [ ] **4g — Enforce the commit convention with a `commit-msg` hook.** The format is now documented in [CONTRIBUTING.md](CONTRIBUTING.md#commit-convention) and [AGENTS.md](AGENTS.md) and is load-bearing as of **6d**: [release.py](scripts/release.py) reads the type to size each package's version bump. Nothing enforces it. Add a `commit-msg` hook validating `<type>(<scope>): <description>` against the documented type list, plus the matching CI check for PR titles. Note the scope is *not* what selects the released package — paths are — but a wrong scope still mislabels history, and `release.py` currently only warns. Cross-platform script per the repo convention (see [meta-hook](packages/meta/.apm/skills/meta-hook/SKILL.md)); note APM cannot deploy git hooks, so this installs out-of-band or via a `scripts/` bootstrap.

---

## 5 — Eval Framework for Steering Effectiveness

**Goal:** Be able to answer "did that change actually make the steering better?" with evidence, and detect when a model upgrade makes existing steering redundant, harmful, or newly necessary.

**Priority: medium (high leverage, meaningful build cost — scope a minimal version first).**

### Background

Section 5 checks that content is *well-formed and deployed*; nothing checks that it is *effective*. Steering quality is currently judged by hand, so revisions are unfalsifiable and each new model release silently shifts the baseline (the [meta-update-models skill](.apm/skills/meta-update-models/SKILL.md) tracks model *identifiers*, not behaviour). A usable framework needs: a fixture set of representative tasks per package, a rubric or programmatic assertion per fixture, and A/B runs (steering on vs off, revision A vs B) across at least two model versions. Harness choice is open — a headless agent SDK loop, an off-the-shelf eval runner, or LLM-as-judge scoring — and should be decided before authoring fixtures.

Cost and non-determinism mean this is unlikely to belong on every PR; assume a manually triggered and/or scheduled job, reported as a tracked score over time rather than a pass/fail gate.

### Prior art — three upstream approaches, cheapest first

| Approach | Source | Shape | Cost / fidelity |
| --- | --- | --- | --- |
| **Per-skill eval fixtures** | [rshade/agent-skills](https://github.com/rshade/agent-skills) — e.g. [`skills/markdownlint/evals/`](https://github.com/rshade/agent-skills/tree/main/skills/markdownlint/evals) | One `evals.json` per skill: `{prompt, expected_output, files[], expectations[]}` with fixture files alongside; `expectations` are natural-language assertions for a judge | Cheapest. Fixtures live next to the skill, so they survive refactors. Good candidate for **5a**'s format |
| **Pressure tests + coverage matrix** | [antonbabenko/terraform-skill](https://github.com/antonbabenko/terraform-skill/tree/master/tests) | `baseline-scenarios.md` (expected *and* forbidden signals per scenario) plus `rationalization-table.md` mapping each hallucination surface → the scenario that exercises it → the guard line that must catch it, marked ✅/◐/❌ | Medium. The coverage matrix is the transferable idea: it makes "which steering line earns its place" auditable — directly serves **5c** |
| **Subagent behaviour drills** | [obra/superpowers](https://github.com/obra/superpowers) — `skills/*/test-pressure-*.md`, `tests/explicit-skill-requests/`, [superpowers-evals](https://github.com/prime-radiant-inc/superpowers-evals/) | Skill run against fresh subagents under adversarial prompts that tempt it to skip the process; also a token-usage analyzer | Highest fidelity, highest cost. Their `writing-skills` skill frames skill authoring as TDD: write the pressure scenario, watch the baseline fail, write the skill, watch it pass |

All three are "prompt + assertions, judged by a model" — none requires a bespoke harness, which lowers the bar for **5a** considerably.

### Tasks

- [ ] **5a — Choose the eval harness and scoring model** (runner, judge vs deterministic assertions, how a run is pinned to a model version and a repo revision). Decide before writing fixtures — it dictates their format.
- [ ] **5b — Build evals for this repo's own content.** Fixtures per package (`core`, `meta`, `ops`, `product`) covering the behaviours the steering is meant to produce, run with and without the steering loaded, scored and recorded so revisions can be compared. Start with one package end-to-end before fanning out.
- [ ] **5c — Track scores across model versions.** Re-run the suite on new model releases to see where steering stops earning its place (or where a regression needs new steering), and feed the outcome back into `meta-update-models` and the [reflect prompt](packages/meta/.apm/prompts/reflect.prompt.md).
- [ ] **5d — Fold the skill-as-TDD method into the `meta-*` skills** once 5a exists. [obra/superpowers `writing-skills`](https://github.com/obra/superpowers/blob/main/skills/writing-skills/SKILL.md) treats authoring as test-driven: write the pressure scenario, run it against a *fresh subagent* to establish the failing baseline, write the skill, re-run until the agent complies, then refactor to close the loopholes it rationalised through — with [`testing-skills-with-subagents.md`](https://github.com/obra/superpowers/blob/main/skills/writing-skills/testing-skills-with-subagents.md) as the procedure. That closes the gap in [meta-skill](packages/meta/.apm/skills/meta-skill/SKILL.md), which specifies structure and description rules but has no way to show a skill actually changes behaviour. Extend to the other `meta-*` skills (agent, prompt, instruction, hook) where the same subagent-pressure method applies. Blocked on 5a: the method needs a harness to run the drills. Record as `metadata.provenance.adaptedFrom`.
- [ ] **5e — Extend evals to third-party / integrated content.** Cover the pinned APM dependencies in `packages/*/apm.yml` and `adaptedFrom` content so an upstream update can be scored before adoption, and so vendored adaptations can be compared against their upstream original. Gated on 5a–5b proving out.

---

## 6 — Marketplace Repository: Licensing, Versioning, Release Automation

**Goal:** Make [`.llmctl-marketplace`](https://github.com/siegenthalerroger/.llmctl-marketplace) publishable without hand-maintenance — correct attribution in every bundle, versions that move on their own, and a release path that does not depend on someone remembering to run a script.

**Priority: low** No public consumers

### Background — what exists now

Marketplace manifests and packed bundles live in a **separate private repository**, generated by [scripts/pack-marketplace.py](scripts/pack-marketplace.py) (wired as `apm run pack-marketplace`). The split exists because a plugin host clones the marketplace repo and reads each `packages[].source` path *as committed* — it never runs `apm install` — so packages carrying APM dependencies must ship as bundles with those skills vendored in. `apm pack` also rejects `..` in a marketplace output path, so the manifest has to be generated in the marketplace repo itself. License files are manually added by the script to ensure proper attetestations.

### Tasks

- [ ] **6a — Go public and verify end to end.** The marketplace repo is private, which is fine for `claude plugin marketplace add <local path>` but blocks Cowork and any other host that clones anonymously. **Unblocked as of 2026-08-02** — the split licensing is settled and every bundle carries its `LICENSE`, `LICENSES/` and generated `THIRD-PARTY-NOTICES.md`. Flipping the repo public is a GitHub setting, so it needs doing by hand. Then install a plugin end to end from Cowork and record what actually loaded (skills, commands, and whether 0.26's packed `agents/`, `instructions/`, and `.mcp.json` are honoured — the previous finding that they do not travel predates 0.26).
