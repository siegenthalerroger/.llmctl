# Bootstrapping Instructions for a Repository That Has None

Procedure for producing a repository's first root context file (`AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md`) and its scoped children. Load this when the target repo has no instruction files at all, or when the existing ones are stale enough to rebuild.

The controlling constraint is the same one that governs every instruction file: **only document what is not derivable from the code the agent will read anyway.** A bootstrapped file that restates the obvious is worse than no file, because it spends always-loaded budget for nothing.

## The Loop: Detect → Extract → Draft → Verify

Never draft first. Each rule must trace to something the repository already declares.

### 1. Detect

Establish what the repository *is* before writing a line about it:

| Signal | Read from |
| --- | --- |
| Language, runtime, version | `go.mod`, `pyproject.toml`, `package.json` (`engines`), `composer.json`, `*.csproj` |
| Package/workspace layout | lockfiles, `pnpm-workspace.yaml`, `go.work`, Cargo workspace members |
| Subsystems worth scoping | top-level directories with their own manifest, their own lockfile, or a different language |
| Quality gates | linter/formatter/type-checker config files, pre-commit config |
| Actual enforcement | CI workflow files — what the pipeline *runs* is the real standard, not what the README claims |

### 2. Extract

Pull facts, not impressions:

- **Commands** from `Makefile` targets, `package.json` scripts, `composer.json` scripts, CI job steps
- **Enforced thresholds** as literal numbers from config — coverage percentage, type-check strictness level, lint rule set
- **Architectural boundaries** from import restrictions, module visibility (`internal/`), dependency-cruiser or ArchUnit-style config
- **Decisions and their reasons** from ADRs, `docs/decisions/`, long-lived design docs
- **Merge and review policy** from branch protection, `CODEOWNERS`, PR templates

Prefer the machine-readable source over prose describing it. A rule extracted from CI stays true when CI changes; a rule copied from a README rots silently.

### 3. Draft

Write only the residue: what an experienced engineer who knows the stack, but not this repository, could not work out from the code.

**Litmus test per line:** *would a senior engineer who knows this stack but not this repo learn something from this line?* If no, cut it.

Common lines that always fail the test:

| Do not write | Why | Instead |
| --- | --- | --- |
| Restating what a filename or type name already says | The agent reads the code | Document only the non-derivable part |
| Generic advice ("write tests", "use clear names") | Universal, not project-specific | Cut it |
| A tutorial on well-known tech (what JWT or Docker *is*) | The model knows | One line stating the project's *choice*: `Auth: JWT (HS256), Bearer token` |
| One-off history ("fixed the login bug in #123") | Will not recur | Cut it; git has it |
| Content duplicated from a scoped file | Breaks the pointer principle | Link to the scoped file |
| Code-style rules | Linter's job | Delegate to linter config entirely |

### 4. Verify — mandatory, not optional

**Never trust an instruction file's own claims, including one you just wrote.** An instruction that names a command that does not run, or a file that does not exist, costs the agent more tokens than it saves: it tries the command, fails, and debugs a phantom.

Before shipping:

- **Run every documented command.** Not `grep` for the target — run it (or at minimum `make -n <target>` / `npm run <script> --dry-run`)
- **Match every documented path exactly.** `AjaxController.php` documented as `CowriterAjaxController.php` sends the agent hunting for a file that does not exist. Existence is not enough; the string must match
- **Re-derive every number** from its config file rather than from memory or from an older version of the file
- **Delete documentation for anything that no longer exists**, rather than leaving it as harmless clutter

Then, on every later regeneration: extract current state → compare against documented state → fix the discrepancies. Updating only dates and counts is not verification.

## Root File Section Skeleton

A root context file is auto-loaded into every session, so keep it thin (target well under 60 lines) and make each section carry information the agent cannot cheaply derive.

| Section | Purpose | Shape |
| --- | --- | --- |
| Commands | Verified executable commands | Table; add a rough runtime so the agent can pick test scope |
| File map | Directory → purpose, for navigation | `dir/ → purpose`, one line each |
| Golden samples | Canonical files to imitate | Table: for what / reference file / key pattern |
| Utilities | Existing helpers, so they get reused instead of rewritten | Table: need / use / location |
| Heuristics | Recurring decisions, pre-made | Table: when / do |
| Boundaries | Always do / Ask first / Never do | Three tiers; lead the Never tier with the highest-stakes item |
| Codebase state | In-flight migrations, known-bad areas, tech debt | Bullets |
| Terminology | Domain terms whose meaning is not obvious | Table: term / means |
| Scope index | Links to the scoped child files | List with one-line descriptions |

Structured beats prose throughout: tables and maps are faster to parse and harder to pad.

### What to generate vs what to curate

| Generate from the repo | Curate by hand |
| --- | --- |
| Commands, file map, scope index, language/framework, test commands | Golden samples, heuristics, boundaries, codebase state, terminology, decision rationale |

Generated sections are objective and should be regenerated rather than edited. Curated sections encode judgement and must survive regeneration — fence generated blocks with markers (`<!-- GENERATED:START -->` / `<!-- GENERATED:END -->`) and keep everything else outside them.

## Scoped Files

Give a directory its own context file when it has genuinely different conventions — a different language, a different test runner, a different set of boundaries. Do not create one per directory as a matter of course; an empty scoped file is pure overhead.

Directories that typically earn one:

| Directory | Typical content |
| --- | --- |
| `src/` (or the language's equivalent) | Source patterns, DI/service conventions, import boundaries |
| `tests/` | Test layout, fixture conventions, how to run a single test |
| `config/` | Framework configuration, what may and may not be edited by hand |
| `docs/` | Documentation format and build |
| A nested app in another language | The whole stack switch — its own commands, its own gates |

Scoped files load on demand, so they can afford detail that the root cannot. Push depth down; keep the root as the index.

**Precedence must be stated, not inferred.** List the children in the root file's scope index and say which wins on conflict. Harnesses differ: Codex concatenates by proximity (nearer the working directory wins), others merge less predictably. Do not rely on the merge order — narrow the scopes so conflicts do not arise, and where an override is intentional, say so in the scoped file (`House rules: linting is disabled in this directory because …`).

## Multi-Harness Output

One authored body, several filenames. Keep a single source of truth and link the rest:

- Symlink or generate `CLAUDE.md`, `GEMINI.md`, and `.github/copilot-instructions.md` from the canonical `AGENTS.md` rather than maintaining parallel copies
- Where a harness needs its own frontmatter or location, generate that wrapper — do not fork the body
- Divergent copies drift within weeks, and the drift is silent
