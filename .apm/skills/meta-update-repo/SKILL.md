---
name: "meta-update-repo"
description: "Refreshes this repository's upstream inputs — the pinned APM dependencies and their lockfiles, a newly added APM dependency, the APM CLI version the gates run on, the third-party Python its own tooling pins, the files adapted from an upstream via metadata.provenance.adaptedFrom, and the specification URLs under authoritativeSpec — by running the repository's own update and audit commands and reading the diff of everything that moved before any of it is committed. ALWAYS use when asked to update dependencies, add or bump a pin, sync upstream, refresh a lockfile, move the APM version, raise a Python version pin, or check adapted files for drift. Do not run apm update or uv lock --upgrade directly, edit a #sha by hand, or merge an upstream change without this procedure and its safety review. Keywords: apm update, apm outdated, new dependency, APM version, lockfile, pin bump, upstream sync, uv lock, pyproject, exclude-newer, adaptedFrom, authoritativeSpec, drift audit, safety review."
compatibility: "Repo-local: needs `apm`, `uv`, `git`, `gh` and a GitHub token, and drives this repository's `llmctl-update`, `llmctl-check-updates` and `llmctl-check` commands plus `uv lock`, none of which are bundled with the skill. If they cannot be run, reproduce each step with equivalent repository or MCP tools and report the fallback used."
---

# meta-update-repo

Bring this repository's third-party inputs up to date deliberately, and read every diff before it lands.

## Scope

Each kind of upstream is audited separately, because each fails in a different way:

| Input | Declared in | Phase |
| --- | --- | --- |
| APM dependencies, existing | `dependencies.apm` in `packages/*/apm.yml`, resolved in `packages/*/apm.lock.yaml` | [A](#phase-a--pinned-dependencies) |
| Tooling dependencies | `[project.dependencies]` and `[dependency-groups] dev` in `pyproject.toml`, resolved in `uv.lock` | [B](#phase-b--the-toolings-own-dependencies) |
| Adapted content | `metadata.provenance.adaptedFrom` in a primitive's frontmatter | [C](#phase-c--adapted-content) |
| Specifications | `metadata.provenance.authoritativeSpec`, except in the three files whose owners audit their own | [D](#phase-d--specifications) |
| APM dependencies, new | a `dependencies.apm` entry that has no lockfile record yet | [E](#phase-e--a-new-apm-dependency) |
| The APM CLI | the `apm-version` default in `.github/actions/setup/action.yml` | [F](#phase-f--the-apm-cli-version) |

Out of scope, and owned elsewhere:
- Model selections belong to `meta-update-models`.
- Description and structure conventions belong to `meta-steering` and `meta-harness`.
- The specifications cited by those two skills belong to `meta-refresh-steering`.

**Nothing here commits.** Every command writes the working tree at most. Deciding what to keep is the judgement this skill exists to support.

## Prerequisites

- A GitHub token in `GITHUB_TOKEN`/`GH_TOKEN`, passed with `--github-token`, or from `gh auth login` (the default). A fine-grained token needs only `Contents: Read-only`. Without a token the diffs cannot be fetched, which is most of the point, and the audits report rate-limit rows that look like broken URLs.
- Run `git fetch --tags`, and start from a tree with no uncommitted change under `packages/`. The update measures every move against `HEAD`, so an uncommitted edit there gets mixed into what looks like an upstream move. If `git status --short packages/` is not empty, stop and ask whether to commit or stash first.

## Phase A — pinned dependencies

```bash
uv run llmctl-update --repo . --dry-run          # what would move; writes nothing
apm run update                                   # every package
uv run llmctl-update --repo . --package core     # or one
```

Per package, the command:
1. moves each pin as far as it goes
2. installs
3. proves the lockfile followed
4. scans what was materialised with `apm audit`
5. prints the upstream's own diff for everything that moved, filtered to the path this repository consumes

It deliberately does not do two things. It never bumps a tagged upstream to HEAD: where `apm update` declines, the pin stays. And it commits nothing.

`apm update` resolves a full-SHA pin only to the newest *annotated* semver tag. An upstream that publishes none (`blader/humanizer` and `rshade/agent-skills` today) gets the HEAD bump that `update.py` applies for exactly that case. Where a tag does exist, APM rewrites the pin and appends the tag as a comment (`#<sha> # v1.2.3`).

**Then read every diff**, against [references/safety-review.md](references/safety-review.md), which says what to look for and what each finding means. This is the step the command exists to set up. A pinned dependency is content an agent loads as instructions, and some of it ships hooks and scripts that run locally. `apm approve` gates execution, not content.

The printed diff is not always the whole diff:

- It holds at most `--max-files` patches per pin (default 10). When it says "and N more file(s)", re-run `uv run llmctl-update --repo . --review-only --package <dir> --max-files <N+10>`.
- A file printed as "(no textual patch: binary or too large)" has not been read. Fetch it at the new SHA and read it whole: `gh api repos/<owner>/<repo>/contents/<path>?ref=<sha> --jq .content | base64 -d`.
- The diff is filtered to the consumed subpath, so it cannot show scope creep. List every file the bump touched with `gh api repos/<owner>/<repo>/compare/<before>...<after> --jq '.files[].filename'`, and judge it against the scope-creep row of the safety review.

To keep a package, commit its two files together:

```bash
git add packages/<dir>/apm.yml packages/<dir>/apm.lock.yaml
git commit -m "build(<dir>): bump <dependency> to <sha7>"
```

To reject one, run `git checkout -- packages/<dir>` and say why.

### When a package cannot be updated

**`apm update` failed.** The run carries on with the other packages, then exits non-zero and lists the failed package under "could not be updated". Read the error tail it printed.

- "Expected exactly one apm.yml entry for `<sha>`, found N": APM 0.31 cannot move several subpaths of one repository pinned at the same commit, and it writes nothing. `packages/design` is in that state today. Report it. Do not work around it by hand-editing the pins, because a hand-moved pin skips the tag `apm update` would have chosen.
- Anything else, including APM 0.31's refusal to install a package that deploys to no target: run `git diff packages/<dir>` to see whether the manifest or lockfile was partly written. Report the error and the state of the files, and revert with `git checkout -- packages/<dir>` if either moved.

**`apm install` failed after an untagged HEAD bump.** The run **stops**. Packages processed earlier keep their moved pins in the working tree, and their diffs were never printed. Do not start another update over them. Then:

1. Revert the failing package with `git checkout -- packages/<dir>` and record its error.
2. Print the diffs of what already moved: `uv run llmctl-update --repo . --review-only`. This measures the working tree against `HEAD` and installs nothing.
3. Continue with the remaining packages one at a time, using `--package`.

## Phase B — the tooling's own dependencies

The release tooling is a uv project, so it pins third-party Python the way a package pins APM content:
- exact versions in [pyproject.toml](../../../pyproject.toml)
- resolved with hashes in `uv.lock`
- under a `[tool.uv] exclude-newer` cutoff that bounds what the resolver may even see

Two tables move together:
- `[project.dependencies]`, which is what a workspace installing from git resolves against
- `[dependency-groups] dev`, which holds ruff and ty for this checkout and CI

**`uv lock --upgrade` on its own reports "No lockfile changes detected" no matter what has been released, and that is not an answer.** The `==` pins and the cutoff each hold it back independently, so both have to move:

```bash
# in pyproject.toml: raise exclude-newer to today, and relax each `==` to `>=`
uv lock --upgrade      # names the cutoff it ignored, then re-resolves
git diff uv.lock       # what moved, including transitive packages nothing pins
```

Read what moved before keeping it. These are not content an agent reads. They are code that runs wherever a gate or a release runs, including CI with a token in the environment, so the question is supply chain rather than instruction:
- Read each project's own release notes for the range.
- Treat a change of maintainer or build system as the thing to look at.
- Check anything surprising against the source.

`uv.lock` records a hash per artefact; keep it that way.

Then pin back, with `==` at exactly what `uv.lock` resolved, so a consumer installing from git gets this resolution and not a newer one. Then re-lock:

```bash
uv lock && uv run llmctl-check --repo . --only tooling
```

A ruff or ty bump is the one that can fail on more than the lockfile. A new release adds rules and tightens inference, so the gate's `ruff check` and `ty check` halves are where it surfaces. Fix what the new version found. Where a rule is wrong for this code rather than right, add it to the `ignore` list in `pyproject.toml` **with the reason in a comment beside it**. An ignore nobody can explain later is how a linter stops meaning anything.

Keep it as one commit with both files, since either alone fails that gate:

```bash
git add pyproject.toml uv.lock
git commit -m "build(tooling): bump <package> to <version>"
```

A `uv pip list --outdated` run reports the project itself as outdated against an unrelated `llmctl` on PyPI. That is a name collision, not a finding.

### When the Python guidance moves

`packages/python` carries the rules this tooling is written to: `python-standards` and `python-scripts` locally, and `modern-python` pinned upstream. When phase A moves that pin, or either local skill changes, re-read what moved and check `src/llmctl/` and `pyproject.toml` against it. Look for:
- a build-backend or dependency-group convention
- a typing or error-handling rule
- a project-layout rule
- a ruff rule family the `select` list does not yet enable
- a linter or type-checker the repository does not yet run

Report the outcome either way. "Nothing to change" is a result, and an unrecorded one gets re-derived next time.

This is the question `meta-review-steering` asks of steering files, asked of the code instead. Neither skill covers the other's files.

## Phase C — adapted content

```bash
apm run check-updates                                                          # broad
uv run llmctl-check-updates --repo . --include "<pattern>" --change-details --json
```

When the target is known, scope directly with `--include` and never run a broad scan first. This applies even when the request is indirect: if a specific file can be identified from context, treat it as an identified target. `took`, `license` and `fidelity` appear only in `--json`, so use it whenever a row is going to be reviewed.

| Case | Status | Action |
| --- | --- | --- |
| APM-eligible upstream: a git repository whose path APM can install as a subdirectory dependency (`owner/repo/path#<sha>`) | `update_available` | recommend converting it to an APM dependency ([phase E](#phase-e--a-new-apm-dependency)) instead of merging |
| Single source | `update_available` | merge review |
| Multi-source | one or more `update_available` | synthesised merge review across all changed upstreams |
| `took` present | `update_available` | scope the review to `took` first. If the upstream change touches nothing on its list, close as no action and say so |
| Upstream path gone | `source_missing` | re-point the URL, or drop the provenance entry if nothing of it remains |
| Request failed | `fetch_failed` | check the token (`Auth:` line) and the URL shape, then re-run that file alone. Report it if it still fails |
| Local file never committed | `missing_local_commit` | ask whether to commit it first, or re-run with `--allow-no-local-commit` to treat it as a bootstrap |
| any | `up_to_date`, `not_trackable` | no action |

For a stub or empty local file, fetch the full upstream content: commit summaries alone are not reviewable when there is nothing local to diff against. For GitHub sources, prefer a GitHub API tool or `gh api` over a generic web fetch.

**Multi-source files** are checked per upstream, one row each. When more than one flags `update_available`:
1. Run the detailed check for each.
2. Compare the changes against the local file to separate overlapping sections from independent ones.
3. Recommend a **single merged update**.
4. Flag any conflict where two upstreams changed the same idea differently.

**After any merge, re-check `fidelity` and `license` in the same edit**, against [meta-steering's provenance rules](../../../packages/core/.apm/skills/meta-steering/references/skill-frontmatter.md#provenance-metadata-recommended). Never leave that to a follow-up.

## Phase D — specifications

```bash
uv run llmctl-check-updates --repo . --specs \
  --exclude meta-steering/SKILL.md --exclude meta-harness/SKILL.md --exclude meta-update-models/SKILL.md
```

The three excluded files audit their own specifications: `meta-refresh-steering` owns the first two and `meta-update-models` the third. A row for one of them is not this phase's to act on.

A GitHub source is dated from its commits; anything else is probed over HTTP. How each status arises is in [references/source-url-reference.md](references/source-url-reference.md#statuses).

- `update_available` means the page changed since the local file last did. Read it and check the claims the local file makes about it: a field name, a limit, a schema.
- `source_missing` needs a re-point. Open the URL in a browser first, because a site that refuses scripted clients answers ≥ 400 too.
- `not_trackable` means no date was available, not that nothing changed. Leave it, unless the request was specifically about that file.

Record the outcome either way. Edit only when asked.

## Phase E — a new APM dependency

Adding a dependency is a bump from nothing, so it gets the same reading as any bump, over **all** of the content rather than a diff. `apm install -g` is not how a package gains a dependency: it writes `~/.apm/`, never `packages/<dir>/apm.lock.yaml`.

1. **Place it** by the [packaging rules](../../../CONTRIBUTING.md#rules): the package whose work needs it, in the git subdir form `owner/repo/path/to/skill`, never a vendored copy. Confirm there is no local `adaptedFrom` copy of the same upstream. If there is, this conversion replaces it.
2. **Pin a full commit SHA.** Use the newest annotated semver tag where the upstream publishes one (`git ls-remote --tags https://github.com/<owner>/<repo>`, rows ending `^{}`), otherwise HEAD. Add the tag comment if there is one (`#<sha> # v1.2.3`). Above the entry, record why this upstream was chosen and what was deliberately left behind.
3. **Materialise it in the package**, then drop the deploy output:
   ```bash
   cd packages/<dir> && apm install --target claude
   ```
   This writes the package's `apm.lock.yaml` and what it deployed. The deploy output (`.claude/`, `apm_modules/` and the others in `workspace.INSTALL_OUTPUT`) is git-ignored. Delete it once read.
4. **Read all of it** against [references/safety-review.md](references/safety-review.md): every file under `packages/<dir>/apm_modules/<owner>/<repo>/<path>`, not a sample. Every row applies, and the executable-surface row most of all. Run `apm audit --ci --no-policy` in the package too.
5. **Record its licence** in [dependency-licenses.yml](../../../dependency-licenses.yml). Read the upstream `LICENSE` itself rather than trusting the GitHub label.
6. **Verify** with `uv run llmctl-check --repo . --only lockfiles --only licences`, then the full [phase G](#phase-g--verify).

Commit `apm.yml`, `apm.lock.yaml` and `dependency-licenses.yml` together, as `build(<dir>): add <dependency> at <sha7>`.

## Phase F — the APM CLI version

What a bundle contains depends on the APM that packed it, and several documents record behaviour observed on one APM version. So a CLI bump is a change to the tooling's input like any other, and it is kept or rejected on evidence.

1. **Read the release notes** for every version in the range (`gh api repos/microsoft/apm/releases --jq '.[] | .tag_name, .body'`), looking for breaking changes to `install`, `update`, `pack`, `audit` and frontmatter translation. List what each one touches here: `update.py` and `pack_marketplace.py` shell out to `apm install`, `apm update` and `apm audit`, and CI runs `apm install`.
2. **Install the new CLI locally.** Move the pin: the `apm-version` default in [.github/actions/setup/action.yml](../../../.github/actions/setup/action.yml).
3. **Run every gate** with `uv run llmctl-check --repo .`. The pack gate is the one that exercises the packer.
4. **Re-run the frontmatter probe** that produced meta-steering's deploy matrix. It is described under "The matrix" in [frontmatter-deploy.md](../../../packages/core/.apm/skills/meta-steering/references/frontmatter-deploy.md#the-matrix): one scratch package outside this repo, one file per type declaring the union of every harness's keys, deployed per target, with authored and deployed frontmatter diffed. Update any row whose result changed, and the "Established … against APM …" line with the new version, short SHA and date.
5. **Re-pin the APM source permalinks** in the `authoritativeSpec` of [meta-steering](../../../packages/core/.apm/skills/meta-steering/SKILL.md), the `apm_cli/integration/*_integrator.py` URLs, to the commit the new release tag points at. They are SHA-pinned, so the spec audit reports them `up_to_date` forever. Re-pinning is the only way they move. Diff each file across the range (`gh api repos/microsoft/apm/compare/<old>...<new> --jq '.files[].filename'`) and re-read the ones that changed.
6. **Re-test every recorded APM workaround**, and update or close what changed:
   - [TODO 4l](../../../TODO.md) (`--frozen` cannot restore `core` from a cold cache): run `apm install --frozen` in a scratch copy of `packages/core` with an empty `apm_modules/`.
   - The multi-subpath `apm update` failure on `packages/design` ([phase A](#when-a-package-cannot-be-updated)): run `apm update --dry-run` there.
   - TODO 3a, 3c, 3d and 6c.
7. **Update the version strings** that name the old version: `grep -rn "APM 0\.\|on 0\.[0-9]" --include='*.md' --include='*.py' --include='*.yml' . | grep -v apm_modules`.

Commit as `ci: move APM to <version>`, with the doc updates in their own commits scoped to what they touch.

## Phase G — verify

```bash
apm run check
```

`check` runs every gate except `commits`, which it skips without `--since`. The pack gate installs every package into a scratch export, so it needs `apm` and the network. When a gate fails:
- **`lockfiles`**: a pin moved without its lockfile, or the reverse. Re-run the phase that moved it; never hand-edit the lockfile.
- **`licences`**: a provenance block parses to nothing, or an obligation-bearing entry has no upstream `license`. Fix the block.
- **`pack`**: installing moved a locked commit, or APM refused the package. The first line names it. Read the error, and if it is APM's rather than the package's, record it against [phase F](#phase-f--the-apm-cli-version) rather than working around it.

Then report:
- which pins moved and to what, per package and for the tooling
- which dependency was added, if any
- the verdict of each safety review
- which adaptations and specifications were flagged
- what the Python guidance asked of the code, if it moved
- what was deliberately left alone, and why

## Guidelines

- Propose, do not apply: commit nothing without confirmation.
- One package per commit, with `apm.yml` and `apm.lock.yaml` together. Either without the other fails the `lockfiles` gate.
- Never hand-edit `apm.lock.yaml`. It is generated.
- An object entry that loses its `url` drops out of the audit silently: no error, no row. After editing any provenance block, run `uv run llmctl-check --repo . --only licences`, which is the one place that failure shows.
- Treat `adaptedFrom` entries as merge-review candidates, never blind replacements.
- When an upstream change alters workflow, process or opinionated behaviour rather than correcting a fact, ask before replicating it.
- Report unknown or unreachable sources explicitly rather than omitting them.
- A licence that moved upstream is reported at the end of phase A. Update `dependency-licenses.yml`, then re-run `apm run check`.

## Notes

- How the audit parses provenance, which files it reads, and every status it reports are in [references/source-url-reference.md](references/source-url-reference.md). It parses through the same [provenance.py](../../../src/llmctl/provenance.py) as the licence gate, so the two cannot disagree about what is tracked.
- `authoritativeSpec` declares which specification a file conforms to, not where content came from, so it is not in the phase C scan. It is not inert: the `licences` gate reads it too, treating a bare URL as a citation that reproduces nothing.
- Another workspace runs these commands from this repository's git, the same way it runs the rest: `uvx --from git+https://github.com/siegenthalerroger/.llmctl@main llmctl-update --repo .`.
