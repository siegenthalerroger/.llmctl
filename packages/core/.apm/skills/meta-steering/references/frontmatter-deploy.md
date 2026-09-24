# Frontmatter Across Harness and Deployer

**Contents:** [Three layers, not two](#three-layers-not-two) · [Classify every key](#classify-every-key) · [Degrade gracefully](#degrade-gracefully) · [The matrix](#the-matrix) · [Deployer caveats](#deployer-caveats) · [Upstream trackers](#upstream-trackers)

Whether a frontmatter key does anything is decided in three places. Author against the first; record the second as a caveat; never let the third leak into the source.

## Three layers, not two

| Layer | Question it answers | Source of truth |
|---|---|---|
| **Harness spec** | Is this key valid, and what does it do? | The vendor page cited under `authoritativeSpec` |
| **Deployer** | Does the key reach the harness at all? | APM's per-primitive pages, its source, and a probe |
| **This repo** | What does the author intend? | The source file under `packages/*/.apm/` |

"The harness ignores unknown keys" is a claim about layer 1 and says nothing about layer 2. APM filters or reshapes frontmatter per target **before** the harness reads the file, so a key can be valid for the harness and still never arrive.

**Author against the harness specs, not against the deployer.** APM is how this repository deploys today. Its gaps are not the authoring standard. Where the harness spec and the deployed result disagree, the spec wins for authoring and the gap becomes a documented caveat. The reverse never applies.

## Classify every key

For each key and each target the file deploys to, decide which case applies. The matrix's **Case** column uses exactly these values.

| Case | What happens on this target | Action |
|---|---|---|
| **1** | Valid and acted on | Author it |
| **2 (stripped)** | Valid on at least one deployed target; APM removes it before this target reads the file | **Author it anyway**; restate its intent in the body |
| **2 (ignored)** | Valid on at least one deployed target; it arrives here and this harness disregards it with no side effect | **Author it anyway** |
| **3** | Reaches this target and breaks or degrades it (observed) | Omit it, write down why in the guidance, link the tracker |
| **deployer input** | Read only by APM, which generates a harness key from it: `applyTo` → `paths` for Claude rules, `input` → `arguments` for Claude commands | Author it wherever that generation is wanted |
| **unestablished** | No documentation or probe settles the effect | Treat as case 2 |
| **n/a** | The type is not deployed to this target | Nothing to author |
| **Not a key** | Valid for **no** target and read by no deployer | Do not author it; express the intent in the body |

- **Case 2 is the default and the safe one.** A stripped or ignored key costs only that it did nothing on that one target. Deleting it from the source loses author intent, degrades every target that honours it, and silently stays lost after the deployer closes the gap.
- **A dropped-keys warning is not a licence to delete.** `apm install` prints "frontmatter keys not supported for claude commands and were dropped: …". That describes layer 2. Check each named key against layer 1 before touching it.
- **Case 3 needs an observed failure, not a suspicion.** Record the error text or the documented behaviour, the harness version, and the tracker. Suspected harm is `unestablished`, and `unestablished` is treated as case 2.
- **Do not merge case 2 into case 3.** The case 3 on record for the deployed repo is [`tools:` on a dual-deployed agent](./agent-guide.md#tools-field): omit it unless every entry is a Claude Code tool name that Copilot documents as an alias.
- **Unknown-key behaviour differs per harness, type and distribution path.**
  - Claude Code documents "any other field is ignored without an error" for rules; skills and commands are observed to behave the same. It **skips** a subagent file whose YAML is malformed, and loads a rule with malformed YAML as if it had no `paths`, which makes it always-on.
  - claude.ai skill upload, the Skills API and `package_skill.py` hard-fail on any top-level key outside the Agent Skills spec ("Unexpected key(s) in SKILL.md frontmatter"). For a skill distributed that way, Claude Code-only keys (`when_to_use`, `hooks`, `effort`, `context`, …) are case 3 **on that path**, while staying case 1 for the APM-deployed copy.
  - GitHub documents particular ignored cloud-agent fields (`argument-hint`, `handoffs`), not a general unknown-key policy for every Copilot runtime. Missing CLI documentation is `unestablished`, not evidence of case 3.
  - The agentskills.io reference validator rejects extra fields; that does not establish runtime loading behaviour.

## Degrade gracefully

Where a key is case 2 on a target, express its behavioral intent a second time somewhere that survives stripping: body prose, an explicit relative link to a skill, or an instruction. Keep the valid source key. Distinguish a usable behavioral fallback from a runtime capability the deployed artifact no longer has.

- **This is deliberate, not redundancy.** Declare the better mechanism and stay correct when only the lesser one arrives. A reviewer who "tidies" the body copy away breaks the stripped target.
- **Binding a skill from a prompt has no frontmatter form on any current target**, so the body link is the only binding, not the fallback. `skills:` exists only on Claude Code *subagents*. VS Code prompt files and Claude commands do not document it (see the matrix). The pattern to write on purpose is: *load the `[skill-name](../skills/skill-name/SKILL.md)` skill before anything else*, as a relative link in the body.
- **Behavioral fallback:** for a prompt's stripped `agent`/`tools`, describe the role, required capabilities and confirmation policy in the body. This guides the model; it does not select an agent or enforce a tool allowlist.
- **Execution controls need a native mechanism.** A description cannot enforce `disable-model-invocation`, and an agent body cannot choose its executing model, effort or sandbox. Record the lost control and the supported harness configuration, spawn parameter or deployment fix needed when correctness depends on it. For example, use the harness's model-selection configuration for a Codex agent whose authored `model` APM strips. Do not claim prose restores the control or rely on it as a permission boundary.
- **Loss remains case 2.** Keep the source field and supplementary intent; describe the deployment limitation explicitly. It becomes case 3 only if a field reaches the harness and an observed failure demonstrates harm, not merely because an intended control was stripped. See [Claude invocation controls](https://code.claude.com/docs/en/skills) and [Codex agent configuration](https://learn.chatgpt.com/docs/agent-configuration/subagents).

## The matrix

Established on 2026-09-24 against APM 0.30.0 (`8c2e0d9`) with a scratch-package probe (one file per type declaring the union of every harness's keys, deployed per target, then authored and deployed frontmatter diffed); re-probed against APM 0.31.0 (`8fd10ac`) the same day, deploy output byte-identical. `vscode` and `agents` remain aliases for `copilot`; `--target agents` is deprecated.

**Copilot authoring baseline: Copilot CLI.** For new Copilot behavior, use only fields documented by the CLI-specific references below. VS Code and cloud rows record compatibility, not additional fields to introduce for new Copilot authoring. Preserve existing keys valid on another deployed target; a CLI baseline is not a reason to strip them. Future convergence is an authoring preference, not an established runtime fact. An APM target name selects output paths, not a single Copilot runtime contract.

The validity and classification columns were refined against vendor documentation on 2026-09-24; the deployment probe above was not repeated for each runtime. The same APM output can have different effects in CLI, VS Code Local and cloud.

| Type × target — keys valid per harness spec | Keys surviving `apm install` | Case | Established by |
|---|---|---|---|
| Skill → claude (`.claude/skills/`): `name` `description` `when_to_use` `argument-hint` `arguments` `disable-model-invocation` `user-invocable` `allowed-tools` `disallowed-tools` `model` `effort` `context` `agent` `background` `hooks` `paths` `shell` `metadata` `license` `compatibility` | **All keys, byte-for-byte** | 1 for behavioral keys; 2 (ignored) for runtime-inert `metadata`, `license`, `compatibility` and foreign fields | [Claude skills](https://code.claude.com/docs/en/skills), APM doc, probe |
| Skill → copilot, CLI baseline (`.agents/skills/`): `name` `description` `argument-hint` `allowed-tools` `user-invocable` `disable-model-invocation` `license` | All keys, byte-for-byte | 1 for documented behavior (`allowed-tools` pre-approves use, not a denylist); 2 (ignored) for `license`; unestablished for foreign keys | [CLI reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference), [CLI skills](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills), APM doc, deployment probe |
| Skill → copilot, VS Code compatibility: `name` `description` `argument-hint` `user-invocable` `disable-model-invocation` experimental `context` | Same skill output | 1 for documented fields; unestablished otherwise. Do not assume CLI supports `context: fork` | VS Code vendor doc, same APM deployment |
| Skill → codex (`.agents/skills/`): reads `name` `description` `metadata.short-description`. Behavior sidecar is `agents/openai.yaml`, not frontmatter | All keys, byte-for-byte | 1 for discovery fields; 2 (ignored) for other frontmatter (per Codex source) | Vendor doc, Codex source, probe |
| Skill → agent-skills (`.agents/skills/`): spec `name` `description` `license` `compatibility` `metadata` (string→string) experimental `allowed-tools` | All keys, byte-for-byte | unestablished: depends on the consumer; spec validity is not proof of a behavioral effect | Agent Skills spec, probe |
| Agent → claude (`.claude/agents/`): `name` `description` `tools` `disallowedTools` `model` `permissionMode` `maxTurns` `skills` `mcpServers` `hooks` `memory` `background` `omitClaudeMd` `effort` `isolation` `color` `initialPrompt` `experimental` | **All keys, verbatim** | 1 for supported fields; 2 (ignored) for foreign fields; **3 for `tools:` unless every entry is a Claude Code tool name Copilot documents as an alias**. Plugin-agent restrictions are separate | Claude vendor doc, APM doc and source, probe |
| Agent → copilot, CLI baseline (`.github/agents/`): `description` required; `name` `include-custom-instructions` `infer` `mcp-servers` `model` `models` `modelPolicy` `reasoningEffort` `tools` | All keys, verbatim. The CLI also discovers `.claude/agents/`; `.github/agents/` wins at the same level | 1 per CLI-specific reference; unestablished for fields not listed there. See the `infer` conflict below | [CLI reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference), [CLI agents](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/create-custom-agents-for-cli), APM source, deployment probe |
| Agent → copilot, VS Code compatibility: `name` `description` `argument-hint` `tools` `agents` `model` `user-invocable` `disable-model-invocation` `target` (`vscode`/`github-copilot`) `handoffs` Local-only `hooks` | Same agent output; VS Code also discovers `.claude/agents/` | 1 for supported fields in the named runtime; 2 (ignored) for `mcp-servers` in IDE agents; unestablished for foreign keys and for duplicate handling | VS Code agent doc, GitHub configuration reference, same APM deployment |
| Agent → copilot, cloud compatibility: `name` `description` `target` `tools` `model` `disable-model-invocation` `user-invocable` `mcp-servers` `metadata` | Same agent output | 1 for supported fields; 2 (ignored) for documented `argument-hint` and `handoffs`; unestablished for other keys | GitHub configuration reference, same APM deployment |
| Agent → codex (`.codex/agents/*.toml`): TOML `name` `description` `developer_instructions` required, plus supported session configuration (`model`, `model_reasoning_effort`, `sandbox_mode`, `mcp_servers`, …) | `name`, `description`; body → `developer_instructions`. Other frontmatter dropped; `tools` alone warns | 1 for delivered fields; 2 (stripped) for the rest. Keep valid native controls in source; prose cannot restore their runtime effects | Vendor doc, APM doc and source, probe |
| Agent → agent-skills: no agent contract | Not deployed | n/a | Probe |
| Instruction → claude (`.claude/rules/`): `paths` only (YAML list or comma-separated string) | `paths` **generated from `applyTo`**; authored `paths` overwritten; other fields dropped; no `applyTo` → no frontmatter | deployer input for `applyTo`; 1 for the generated `paths`; 2 (stripped) for authored `paths`, `name`, `description` | [Claude rules](https://code.claude.com/docs/en/memory), APM source, probe |
| Instruction → copilot, CLI baseline (`.github/instructions/`): `applyTo` as comma-separated globs; `excludeAgent` (`code-review`/`cloud-agent`) | All keys, verbatim | 1 for `applyTo`; `excludeAgent` is documented on the CLI page but both values name non-CLI agents; unestablished for `name`, `description`, `paths`. Do not assume description-based activation | [CLI instructions](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions), APM doc, deployment probe |
| Instruction → copilot, compatibility: VS Code `applyTo` (one glob string) `name` `description`; GitHub `applyTo` `excludeAgent` | Same instruction output; VS Code also reads `.claude/rules/` | 1 per documented runtime; unestablished for duplicate handling when both directories are deployed | VS Code and GitHub instruction docs, same APM deployment |
| Instruction → codex: `AGENTS.md` has no frontmatter and no path scoping | Not installed. `apm compile --target codex` consumes all frontmatter and turns `applyTo` into a "Files matching" heading plus directory placement | 2 (stripped) for every key (scoping degrades to prose) | Vendor doc, APM doc, probe |
| Instruction → agent-skills: no instruction contract | Not deployed | n/a | Probe |
| Prompt → claude (`.claude/commands/`): skill schema except `name` and `paths` | `description` `allowed-tools` `model` `argument-hint`; `input` becomes `arguments` plus a generated hint. Others dropped with warning | 1 for delivered fields; deployer input for `input`; 2 (stripped) for other valid fields; `skills` is not a prompt key | Claude vendor doc, APM doc and source, probe |
| Prompt → copilot, CLI baseline: native `.claude/commands/*.md` accepts `argument-hint` `description` `allowed-tools` `disable-model-invocation`; filename supplies name | The `claude` target's `.claude/commands/` output, when deployed, carries `description` `argument-hint` `allowed-tools` (+`model`). The `copilot` target writes `.github/prompts/` | 1 via `.claude/commands/`; 2 (stripped) for `disable-model-invocation`; unestablished for `.github/prompts/` loading. Author new CLI workflows as skills | [CLI reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference), APM doc and source, deployment probe |
| Prompt → copilot, VS Code Local compatibility (`.github/prompts/`): `name` `description` `argument-hint` `agent` `model` `tools` | All keys, verbatim | 1 for Local-supported fields; Agent Host does not load these files; unestablished for foreign keys | VS Code prompt doc, APM doc, probe |
| Prompt → codex: deprecated native custom prompts in `~/.codex/prompts/` accept `description` `argument-hint` | No prompt artifact or frontmatter deployed by APM | 2 (stripped): valid native fields are not delivered; preserve them in source. Use skills for workflows distributed to Codex through APM | [Codex custom prompts](https://learn.chatgpt.com/docs/custom-prompts), APM source, deployment probe |
| Prompt → agent-skills: no prompt contract | Not deployed | n/a | Probe |

**Documentation conflicts.** The CLI reference documents agent `infer` (default true); the shared cloud configuration reference calls it retired. Follow the CLI reference for the CLI baseline and do not claim retirement across runtimes. The CLI instruction references disagree on absolute imports; use repository-contained relative imports until that conflict is resolved. The CLI agent fields (`models`, `modelPolicy`, `include-custom-instructions`) are owned by [agent-guide.md](./agent-guide.md#tools-field) and its CLI contract section.

Not established: generic unknown-key behavior across Copilot runtimes; CLI effects of fields absent from its specific reference; CLI loading of APM's `.github/prompts/` output; how VS Code and the CLI resolve the same agent or rule arriving from both `.github/` and `.claude/`; unknown-key handling in Codex agent TOML and `agents/openai.yaml`; the `-g` user-scope deploy. The deployment probe did not test runtime loading or resolve conflicts between vendor pages. None of these gaps is evidence of case 3.

## Deployer caveats

**Agents are copied, commands are filtered.** This asymmetry is why intuition from one type transfers wrongly to the other.

- **Agents:** copied verbatim to claude and copilot (also cursor, opencode, grok-build). The exceptions are Codex, which keeps `name` and `description` in TOML, and Kiro, which keeps `description`, `model` and `tools`. One agent file therefore delivers the *same* value of a shared key to both Claude and Copilot, which is exactly why a `tools:` value rarely suits both.
- **One source, several discoveries.** VS Code and the Copilot CLI also read `.claude/agents/`, VS Code reads `.claude/rules/`, the CLI reads `.claude/commands/`, and both Claude Code (when no `CLAUDE.md` exists) and the CLI read `AGENTS.md`. A dual deploy is therefore discovered twice by Copilot runtimes, and `apm compile` output can double-load next to `.claude/rules/`. The CLI gives `.github/agents/` precedence at the same level; VS Code's duplicate handling is not established.
- **Prompts → commands:** a fixed allowlist (`description`, `allowed-tools`, `model`, `argument-hint`, `input`, plus camelCase aliases) for every target using the shared command transformer: claude, cursor, grok-build, and opencode and windsurf (`workflows/`) through the same code path. Gemini gets a separate TOML writer. Copilot receives the prompt verbatim.
- **`${input:…}` rewriting is conditional.** APM rewrites `${input:name}` to `$name` only when the `input:` key lists `name`, and only the placeholder-free form. `${input:name:placeholder}` and VS Code context variables (`${selection}`, `${file}`, …) reach the Claude command as literal text. Claude binds `arguments` by position, so `$name` receives one whitespace-separated token, not free text.
- **Links:** APM rewrites a relative body link that resolves into a package (a skill link becomes an `apm_modules/…` path). Other relative links are copied unchanged and break at the deployed location; link repository files by URL or by name instead.
- **Instructions → Claude rules:** always write `applyTo` on a scoped instruction. APM builds Claude's `paths` from `applyTo` alone, so an instruction carrying only `paths` deploys with no frontmatter and becomes **always-on** in Claude Code. Keep `paths` too, aligned with `applyTo`, because it is the valid key for Claude Code's own `.claude/rules/` and VS Code's reading of that directory.
- **`applyTo: "**"` is not always-on in Claude Code.** A path-scoped rule loads "when Claude reads files matching the pattern", so a `**` rule stays absent until the first file read. The only unconditional Claude rule APM can produce is one without `applyTo`, which in turn is not auto-applied by VS Code or the CLI; put always-on Copilot content in `copilot-instructions.md` or `AGENTS.md`.
- **APM deploys skills, agents and compiled instructions to Codex, but no prompts.** Codex's deprecated native prompt support is a separate harness capability.
- **Skills are the only type that arrives identically on every target.** Where one file must behave the same everywhere, a skill is the most faithful carrier.

## Upstream trackers

- microsoft/apm [#2108](https://github.com/microsoft/apm/issues/2108): portable agent semantics without lossy vendor pivots (the `tools:` case).
- microsoft/apm [#2106](https://github.com/microsoft/apm/issues/2106): command semantics and per-target renderers, replacing the shared Claude-shaped subset.
- microsoft/apm [#2110](https://github.com/microsoft/apm/issues/2110): transformation and loss-report contract.
- microsoft/apm [#3067](https://github.com/microsoft/apm/issues/3067): the Claude command allowlist is narrower than Claude Code itself. It drops `disable-model-invocation`, `user-invocable`, `when_to_use`, `context`, `agent`, `effort`, `disallowed-tools`, `hooks` and an authored `arguments` on the very harness it targets, and the Copilot CLI reading the same `.claude/commands/` output loses `disable-model-invocation` too.
