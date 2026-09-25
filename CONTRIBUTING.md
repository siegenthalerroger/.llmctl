# Contributing

## Packaging Model

`.llmctl` is an APM **monorepo**: one repository that exposes several independently installable, context-scoped sub-packages under `packages/`, plus repo-local dev tooling at the root. This keeps every context loading only what it needs instead of the whole collection.

| Package | Scope | Contents | Typical install |
|---|---|---|---|
| `packages/baseline` | Global baseline | Domain-neutral agents (plan, explore, executor-\*, researcher); troubleshooting/batch/research/mermaid skills; the `meta-steering` + `meta-harness` authoring skills; documentation, troubleshooting + meta instructions; `reflect` + `setup-mcp` prompts; universal MCP servers | `apm install -g <repo-location>/packages/baseline` |
| `packages/workflow` | Global (code work) | The `code-reviewer` agent; delivery-discipline skills sourced upstream (TDD, git worktrees, merge conflicts, code-review reception, lint pipelines) | `apm install -g <repo-location>/packages/workflow` |
| `packages/ops` | Per-project (ops/infra) | Helm/K8s/OpenTofu skills; helm + tf instructions; cloud/IaC doc MCP servers | `apm install <repo>/packages/ops` |
| `packages/product` | Per-project (product) | PRD skills; product-manager + ux-expert agents | `apm install <repo>/packages/product` |
| `packages/design` | Per-project (design) | `design-direction`, `colour`, `typography`, `presentation` skills; upstream layout/identity/dataviz practice | `apm install <repo>/packages/design` |
| `packages/python` | Per-project (Python) | `python-standards` + `python-scripts` skills; python instructions; upstream `modern-python` project tooling | `apm install <repo>/packages/python` |
| `packages/travel` | Per-project (travel) | `destination-calendar` (scripted holiday/event check), `trip-planning`, `travel-entry-requirements` (scripted Schengen count), `itinerary-authoring` skills; the `plan-trip` prompt; flight / hotel / ferry / stay MCP servers |
| root `.apm/` | Repo-local only | `meta-updater` dispatcher + the `meta-update-repo` / `meta-update-models` / `meta-refresh-steering` / `meta-review-steering`  procedures, the frontmatter-validation hook | Deployed only when developing this repo |

### Rules

- **Each sub-package uses the `.apm/` layout.** A package is `packages/<name>/apm.yml` + `packages/<name>/.apm/{agents,skills,prompts,instructions,hooks}/`. Everything must live under `.apm/`: it is the only layout both `apm install` and `apm pack` read in full. A package with root-level directories deploys only its skills — agents, instructions, prompts and hooks are dropped for every target without a warning — and `apm pack` drops its prompts from the bundle.
- **`name` is the plugin identifier; `displayName` is its title.** `name` is `llmctl-<directory>`, lowercase kebab-case, because every host namespaces the package's skills and agents under it (`llmctl-baseline:troubleshooting`) and Copilot accepts nothing looser. The optional `displayName:` in the package's `apm.yml` is what a plugin UI shows instead. APM ignores that key, so [`llmctl-pack-marketplace`](src/llmctl/pack_marketplace.py) copies it into the bundle's Claude and Codex manifests. Every package also carries `author` as an object (`name` plus the GitHub profile `url`), `homepage` (the marketplace, where the plugin is consumed from), `repository` (this repository, its source), `keywords` and `category`. APM carries those into the Claude manifest itself, and the packer copies them into the Codex one, using `homepage` for `interface.websiteURL`. The marketplace catalogue is generated from the same manifests: each entry takes the package's `name`, `description` and `category`, so `apm.marketplace.yml` holds only the marketplace's own fields. Renaming a package changes its plugin identity: installed copies have to be uninstalled and the new name installed.
- **The root workspace depends on `packages/baseline`, `packages/python` and `packages/workflow`.** Those are the three an agent editing this repo needs in context: `baseline` carries `meta-steering` and `meta-harness`, which every steering file here is written against, plus the prose and research skills the docs get written with; `python` carries the standards `src/llmctl/` is held to; `workflow` carries the delivery skills the editing itself runs on — worktrees, TDD, merge-conflict resolution, receiving code review, lint pipelines — and the `code-reviewer` agent for `src/llmctl/`. Deploying the root [apm.yml](apm.yml) therefore brings all three along beside the repo-local procedures. Nothing else is added — `ops`, `product` and `design` are domain steering for work that does not happen in this repository.
- **Place a new primitive by scope, not by type.** Ask: universal and domain-neutral (baseline, which also owns the authoring guidance), code-specific (workflow), domain-specific (ops/product/design or a new package), or operates on *this repo's own files* (root `.apm/`)? `baseline` loads in *every* context, including ones with no code in them — anything that presumes a codebase belongs in `workflow`.
- **Scope each MCP server to the package whose work needs it.** Universal dev servers (`github`, `context7`) live in `packages/baseline/apm.yml`; domain servers live in their domain package (cloud/IaC doc servers in `packages/ops/apm.yml`). A server loads only where its package is installed, so keep global tool surface minimal.
- **Consume upstream content as a pinned `dependencies.apm` entry, never a vendored copy** (see the APM-first rule below). Use the git subdir form to take a single skill out of a larger repo — `owner/repo/path/to/skill#<sha>` — and always pin a commit or tag; an unpinned entry tracks the default branch and drifts. Scope the dependency to the package whose work needs it, exactly like MCP servers, and record in a comment why that upstream was chosen and what was deliberately left behind. Bump through the `meta-update-repo` skill, which runs that loop per package, reads the diff of everything that moved before it is committed, and keeps `apm.yml` and `apm.lock.yaml` in one commit. **Every pin is a full commit SHA and every package commits its `apm.lock.yaml`** — see [Lockfiles](#lockfiles).
- **The marketplace is a separate repository.** Manifests and packed plugin bundles live in [`.llmctl-marketplace`](https://github.com/siegenthalerroger/.llmctl-marketplace), not here. A plugin host (claude.ai Cowork, Claude Desktop/Code) clones the marketplace repo and reads each `packages[].source` path *as committed* — it never runs `apm install` — so any package carrying APM dependencies has to be published as a bundle with those skills already vendored into it. Keeping that generated output out of this repo is the point of the split; `apm pack` also refuses to write a manifest across a `..` boundary, which rules out generating it here.
- **The marketplace repository holds nothing that is authored there.** Its `README.md`, `LICENSE`, `.gitignore` and `apm.yml` all have a source in this workspace — `README.marketplace.md`, `LICENSE.marketplace`, `.gitignore.marketplace`, `apm.marketplace.yml` — and [`llmctl-pack-marketplace`](src/llmctl/pack_marketplace.py) writes them out beside the bundles it packs, adding one catalogue entry per package with its `source` and `version`. Anything else it finds in that tree is **deleted**, so "everything there is generated" is enforced rather than asserted. Edit the sources here and regenerate; never edit the marketplace.
- **A release publishes; it does not commit here.** [`llmctl-release`](src/llmctl/release.py) (or `apm run release`, which previews) derives each package's calendar version, packs from a scratch export of `HEAD`, commits and pushes the marketplace, and records the version as an annotated `<name>@<version>` tag plus the GitHub release beside it. Both roots are explicit flags with no defaults — `--repo` for the workspace being released and `--marketplace` for the repo it publishes into — because a derived marketplace path would silently publish into the wrong repo; [apm.yml](apm.yml) supplies them. **Packages version independently** (`per_package`); see [Releasing](#releasing).
- **Content that cannot be public lives in a separate workspace, never in `packages/` here.** This repo and its marketplace are public. A private package gets its own private source repo and its own private marketplace, laid out identically but holding none of this tooling — it runs this repo's commands from git and shares nothing else. `LICENSES/` and `dependency-licenses.yml` are read from the workspace being released, so a private repo carries its own copies rather than resolving against this one. See [Releasing another workspace](#releasing-another-workspace).
- **The plugin path is reduced-fidelity; `apm install` remains the full deploy.** What a marketplace consumer actually receives, per primitive, is in [meta-harness](packages/baseline/.apm/skills/meta-harness/SKILL.md#6-this-repositorys-conventions).

## Content Strategy: APM-First

APM is the primary mechanism for consuming upstream content. Prefer declaring upstream packages in `apm.yml` and installing them into the git-ignored `apm_modules/` directory. Only create local copies when upstream content cannot be managed by APM.

| Category | When to use | Provenance field | Storage / update |
|---|---:|---|---|
| APM dependency (default) | Upstream package available as APM | none required (declare in `apm.yml`) | Installed to `apm_modules/` (git-ignored). Added and bumped through `meta-update-repo` |
| Adapted / synthesised (local) | Any local copy of upstream material, from a light borrowing to a near-verbatim carry-over — only if APM cannot manage it | `metadata.provenance.adaptedFrom` | Tracked by `meta-update-repo` for drift detection; file lives in repo |

### APM dependency (default)

- Default for any content available from an APM-compatible upstream source.
- To add one, follow the `meta-update-repo` skill's new-dependency phase: it pins a full SHA, writes the package's `apm.lock.yaml`, reads the whole upstream content before it is kept, and records its licence. `apm install -g` is not the way in: it writes `~/.apm/`, never the package's lockfile.
- Installed into `apm_modules/` (git-ignored). No `metadata.provenance` tracking is required for pure APM dependencies.
- Do NOT vendor upstream content by copying files into this repository.

### Adapted / synthesised (local)

- Use whenever anything at all was taken from an upstream file that APM cannot manage — whether the local file restructures the material for local conventions, synthesises several sources, or carries most of one upstream across near-verbatim.
- Add `metadata.provenance.adaptedFrom` listing upstream sources, and set each entry's `fidelity` to say how much was taken plus its `license` wherever that fidelity copies expression. These files are tracked by `meta-update-repo` for drift and merge-review workflows.
- Before adding one, verify the upstream isn't available as an APM package.
- Run `apm run check` afterwards. Its `licences` gate is the only thing that catches a provenance block which parses to nothing — a file that stops being tracked looks exactly like one with nothing to track.

Local-only skills (not available upstream) remain directly in this repository.

## Authoring Customization Files

The authoring rules live in two skills, and nowhere else. Load the one that owns the file before editing it:

- [`meta-steering`](packages/baseline/.apm/skills/meta-steering/SKILL.md): skills, agents, instructions, prompts. It covers frontmatter per harness, which keys survive APM's deploy to each target ([frontmatter-deploy.md](packages/baseline/.apm/skills/meta-steering/references/frontmatter-deploy.md)), description shape and budgets, and provenance fields.
- [`meta-harness`](packages/baseline/.apm/skills/meta-harness/SKILL.md): hooks, MCP servers, plugin bundles.

This file keeps only what is specific to working in this repository.

### Hooks (`*.hook.json`)

Hook authoring, including the `*.hook.json` naming convention, is in [meta-harness](packages/baseline/.apm/skills/meta-harness/references/hooks.md). Two repository facts stay here:

- **Do not commit machine-generated hook wiring.** APM deploys hooks into each target's native location — `.claude/settings.json` and `.claude/apm-hooks.json` at project scope, `~/.claude/settings.json` at user scope, and the `.codex/` and `.agents/` equivalents. All of it is output, so `.claude/`, `.codex/` and `.agents/` are git-ignored in full and a clone gets its own by running `apm install`. The consequence: this repository's own frontmatter hook is not wired until that first install.
- APM cannot yet deploy into the `settings.local.json` variant, so there is no committed `settings.json` to hold shared project settings alongside the generated wiring. [TODO 3a](TODO.md) tracks the upstream issue.

## Repository Frontmatter Provenance Convention

`metadata.provenance.adaptedFrom` and `metadata.provenance.authoritativeSpec` are a convention of this repository, not a universal standard. They are defined once, in two halves:

- **What to write** (the three forms, what `fidelity`, `license` and `took` mean, and how to keep `took` from rotting): [meta-steering's provenance section](packages/baseline/.apm/skills/meta-steering/references/skill-frontmatter.md#provenance-metadata-recommended).
- **How the tooling reads it** (which files are audited, both audit modes, supported URL forms, every status, how an entry silently drops out of the audit): [source-url-reference.md](.apm/skills/meta-update-repo/references/source-url-reference.md).

[`llmctl-check-licenses`](src/llmctl/check_licenses.py) enforces the licence half; see [Licensing](#licensing).

## Model Profile Convention (`metadata.modelProfile`)

A file whose type supports the top-level `model` frontmatter field may declare a `metadata.modelProfile` instead of hard-coding a model. The `meta-update-models` skill ([SKILL.md](.apm/skills/meta-update-models/SKILL.md)) turns it into the active Claude Code `model:` and `effort:` plus a non-functional multi-provider comment, and owns the field meanings and maps — change them there. The schema table for authors is in [agent-frontmatter.md](packages/baseline/.apm/skills/meta-steering/references/agent-frontmatter.md).

## Upstream Update Tooling

Four maintenance procedures, run separately and never as a pipeline — dependencies, pins, the APM CLI and adapted files; model selections; the authoring guidance; the steering files against it. The [`meta-updater`](.apm/agents/meta-updater.agent.md) agent routes a request to the one that owns it; each command and its caveats live in that procedure's skill.

## Licensing

`.llmctl` is licensed under a split, because it is two different kinds of thing — see [LICENSE](LICENSE) for the authoritative statement:

| What | Licence |
| --- | --- |
| Every `*.md` file — skills, agents, prompts, instructions, `references/`, repo docs | **CC-BY-SA-4.0** |
| Everything else — `src/`, hooks, `*.py`, `*.ps1`, `*.json`, `*.yml` | **MIT** |

Three rules follow from that, and [`llmctl-check-licenses`](src/llmctl/check_licenses.py) enforces all three:

- **The content half is copyleft.** Adapting a `*.md` file from here means releasing your adaptation under CC-BY-SA-4.0 too. That is deliberate.
- **A file's provenance decides its licence.** Where `metadata.provenance` records an obligation-bearing `fidelity`, the upstream's `license` constrains what the local file may be licensed under: MIT upstream permits either default; CC-BY-SA-4.0 upstream forces CC-BY-SA-4.0; Apache-2.0 and GPL-3.0 upstreams force their own licence and need a per-file override; `NONE` permits nothing beyond `inspiration-only`. Declare an override with a **top-level `license:` field** in the file's frontmatter — that always wins over the table above.
- **Attribution is generated, never hand-written.** `THIRD-PARTY-NOTICES.md` in the marketplace repo is produced by [`llmctl-gen-notices`](src/llmctl/gen_notices.py) from provenance metadata plus each bundle's `apm.lock.yaml`. Sources whose terms attach land under *Notices*; everything else, including `inspiration-only` sources and upstreams with no licence at all, is still credited under *Acknowledgements*.

`CC-BY-NC-4.0` is recognised inbound with **no permitted outbound**. Its NonCommercial term is one neither default can carry — CC-BY-SA-4.0's ShareAlike requires the adaptation permit commercial use, and MIT cannot express the restriction at all — so such an upstream is usable only at a fidelity that attaches nothing. Take the shape, never the prose; `partly-derived` or above fails the `licences` gate by design rather than silently relicensing.

Adding a dependency or an adaptation from a **new** upstream means recording its licence in [dependency-licenses.yml](dependency-licenses.yml) or the entry's `license:` field. Run `apm run check` before opening a pull request.

## Commit Convention

Commits are **conventional**:

```text
<type>(<scope>): <description>
```

- `type` — `feat` `fix` `docs` `refactor` `chore` `test` `build` `ci`. Append `!` before the colon for a breaking change (`refactor(baseline)!: …`).
- `scope` — optional. For a change under `packages/`, the package directory: `baseline`, `design`, `ops`, `product`, `python`, `travel`, `workflow`. Outside it, the area the paths belong to: `tooling` (`src/`, `pyproject.toml`, `uv.lock`), `ci` (`.github/`), `meta` (the root `.apm/`), `docs` (a root `*.md`), `repo` (root config — `apm.yml`, `apm.lock.yaml`, `.gitignore`, `dependency-licenses.yml` — plus `LICENSE*`, `LICENSES/` and the `*.marketplace.*` sources). The mapping is [commits.py](src/llmctl/commits.py)'s `AREAS`.

**The type sizes nothing.** Versions are calendar-derived, so `feat` and `fix` no longer mean "minor" and "patch"; they decide which heading a commit lands under in the generated release notes, and nothing else. That is worth keeping, so the convention is now *enforced* rather than merely read: the `commits` gate refuses a subject outside the type list, and refuses a scope that names nothing the commit touched.

**Which package a commit releases is decided by the paths it touched, not by the scope.** Paths are what actually changed and cannot be mistyped. A scope is optional; when present it has to name a package or an area from the list above that the commit actually touched.

The gate lints a range, not all of history: CI passes the pull request's base (and its title), and a run with no range reports the gate skipped rather than inventing one. Locally: `uv run llmctl-check --repo . --since origin/main`.

**Prose for the release notes goes in the pull request body**, under a `## Release notes` heading. The release copies that section, and only that section, into the GitHub release of every package the pull request touched; ordinary review discussion in the same body stays out.

## Releasing

Versions are **calendar-derived**: `YYYY.M.N`, where `N` counts that package's releases within the UTC month, from 1. `llmctl-baseline@2026.9.1`, then `2026.9.2`. No zero padding, so the string stays semver-shaped for the hosts that parse it as one.

There is no API to break here and no consumer who can act on "minor" versus "patch"; what a reader of a steering package wants to know is how old it is. The commit types are still enforced, but they group the release notes rather than sizing a number.

Packages version **independently** (`marketplace.versioning.strategy: per_package`). A change to `ops` releases `ops` only, so a version always means something in that package changed.

### A release writes nothing to this repository

`packages/*/apm.yml` carries `version: 0.0.0`, a placeholder. The real version is stamped into a scratch export at pack time, and the record of it is the annotated `<name>@<version>` tag plus the GitHub release beside it.

That is what lets a release run on a push to protected `main` with no pull request, no bypass and no second CI cycle — pushing a tag is not pushing a branch.

The tag and the release page are two writes, so they can end up out of step: the tag pushes, then the release is created against the commit the tag points at. Re-running finishes the job rather than reporting nothing to do — `ensure_releases` asks for each package's newest tag and creates only what is missing, so a release that landed half-way heals on the next run without re-packing anything.

What a failed page does to the run depends on the status, because the two kinds say different things:

- **403** — this token may not create releases here, and no re-run changes that. The run says so and carries on green: the tags and bundles it published are the whole release it is allowed to make, and failing every future run over a permission that is not the tooling's to grant would leave the workspace permanently red with nothing to fix. `.llmctl-private` is in exactly this state, holding `Contents: write` and still refused `POST /releases`.
- **anything else** — the request was wrong, which *is* the tooling's. The run fails and names every tag still missing a page. This is not hypothetical: a 422 hid here for a whole release, a tag name sent where a commitish belongs, because a failed page only ever warned.

The marketplace is the opposite case: it is generated output, entirely, so it is committed and pushed directly. Protecting it would gate a robot against itself.

```bash
apm run check       # every gate, over this workspace alone
apm run versions    # what each package's next version would be, and why
apm run release     # what a release would publish, and its notes. Writes nothing
```

The real release runs in CI, on a push to `main`. To rehearse the whole thing locally against a throwaway clone of the marketplace:

```bash
uv run llmctl-release --repo . --marketplace ../scratch-marketplace --no-push
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

**`apm install --frozen` is not what enforces that**, and this is the one place that fact is written down. A frozen install checks that every dependency in `apm.yml` *appears* in the lockfile, keyed by repository and subpath, never at which commit — so a pin moved without a lockfile refresh passes it. It also fails to restore `packages/baseline` from a cold cache: on 0.31.0 the error names the manifestless repo-root dependency `blader/humanizer`, and it appears only while the package declares a non-empty `dependencies.mcp` — the same dependencies with `mcp: []` restore frozen. Which of the two conditions APM actually trips on, and whether `ops`, which also declares MCP servers, is affected, has not been established ([TODO 4l](TODO.md)). That is why packing installs normally and compares the resolved commits before and after, and why the workflows' deploy step is not frozen either. The `lockfiles` gate compares manifest against lockfile directly, offline, and refuses any pin that is not a full commit SHA. `apm audit --ci` checks the same thing where a package is already installed, and the pack gate runs it over each scratch export.

New lockfiles carry no `generated_at`, so two independent runs produce the same bytes. Deleting that line from an older one is permanent; APM does not add it back.

A lockfile moves only through the `meta-update-repo` skill — `apm run update` for a bump, its new-dependency phase for an addition — and always in the same commit as the `apm.yml` pin it belongs to. Never hand-edit one.

### Releasing another workspace

Nothing in this tooling is specific to this repo. A private sibling laid out the same way — its own `packages/`, `LICENSE`, `LICENSES/`, `dependency-licenses.yml` and `*.marketplace.*` sources, none of this code — runs the same commands straight from this repository's git, with the flags pointed at itself:

```bash
uvx --from git+https://github.com/siegenthalerroger/.llmctl@main llmctl-release --repo . --marketplace ../<its-marketplace>
```

`uvx` builds the project at that ref and runs the command, so nothing is cloned or installed by hand; the private workspace's `apm.yml` carries that one-liner for every command, and its workflows hand the same requirement to this repository's composite actions. Nothing is shared but the code. Licence texts, dependency records and marketplace sources are read from the workspace only, so a private repo's upstreams never resolve against this one's.

## Continuous Integration

GitHub Actions runs the same entry points a contributor runs. The tooling is a locked uv project, so here every step is `uv run --locked` and nothing is installed first; the private workspace runs the same commands through `uvx --from` a git ref.

| Workflow | Trigger | What it runs | Locally |
| --- | --- | --- | --- |
| [checks.yml](.github/workflows/checks.yml) | pull request, manual | every gate | `apm run check` |
| [release.yml](.github/workflows/release.yml) | push to `main`, manual | every gate, then the release | `apm run release` (previews) |

**There is one gate set, and it lives in [check.py](src/llmctl/check.py).** The marketplace-shaped gates pack into a scratch directory and validate that, so one checkout runs everything — the tooling's own lint, frontmatter conventions, the commit convention, licence obligations, lockfiles against their pins, and a full pack that every bundle must survive.

The `tooling` gate is `uv lock --check`, `ruff format --check`, `ruff check` and `ty check`, in that order. Both linters read their configuration out of `pyproject.toml`, and `uv.lock` only exists beside it, so the gate skips with its reason stated in a workspace running the tooling from git — there is nothing there to lint, and linting an installed copy against default rules it was never written for would report noise rather than findings.

A push to `main` runs those same gates inside `release.yml`, immediately before publishing what they passed on, so `checks.yml` does not duplicate it.

A gate declares what it needs, and the runner decides what a missing need means: no `--since` skips the commit gate and says so, a missing `claude` CLI skips bundle validation and says so, a missing `apm` fails the pack gate outright. Skipped is never silent and never green-by-omission.

Both workflows here, and the private workspace's two, are thin: the shared steps live in composite actions under [.github/actions/](.github/actions/), referenced by path here and as `siegenthalerroger/.llmctl/.github/actions/<name>@main` from the private workspace. This repository is public, so that needs no checkout there and no cross-repository Actions permission.

The private workspace holds none of this code. Its workflows pass the actions a `tooling` requirement — `git+https://github.com/siegenthalerroger/.llmctl@main` — which they hand to `uvx --from`, exactly as its `apm.yml` does locally. No checkout, no secret and no pinned ref: the default branch is what runs, there as here.

**One APM version, pinned in one place.** What a bundle contains depends on the packer that made it, so the gates have to pass on the version that will pack it: the pin is the `apm-version` default in [.github/actions/setup](.github/actions/setup/action.yml), and every workflow in both workspaces inherits it. Moving it is a commit, and the gates on that commit are the proof — not a scheduled run against whatever was newest that morning. The `meta-update-repo` skill's APM CLI phase is the procedure: release notes, gates, the frontmatter deploy probe, and every recorded workaround re-tested.

**The marketplace repositories have no CI at all.** There is nothing left there to check: every file in them is regenerated from this repository on every release, and anything else is deleted.

### Secrets

- **`MARKETPLACE_TOKEN`** — `contents: write` on the marketplace repo. Set on this repo and on the private workspace. A release regenerates and pushes the marketplace, so even a dry run has to read it.

The release needs no token of its own beyond the workflow's: it pushes tags and creates releases, both of which `contents: write` on `GITHUB_TOKEN` covers.
