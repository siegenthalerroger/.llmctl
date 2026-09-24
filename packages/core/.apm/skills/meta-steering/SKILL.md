---
name: "meta-steering"
description: "Authoring guide for every steering file an agent harness reads: skills (SKILL.md), subagents (*.agent.md), instructions (*.instructions.md, applyTo/paths) and prompts (*.prompt.md) — frontmatter, description shape, discovery budgets, provenance. ALWAYS load before creating or editing one of those files, and when deciding which customization type a new rule belongs in. Do not hand-write customization frontmatter, a skill or agent description, or path scoping from recall — the discovery budgets and cross-harness field names are version-specific and this skill pins them. Does not cover hooks, MCP servers or plugin bundles — see meta-harness. Keywords: skill, SKILL.md, agent, subagent, persona, handoff, instructions, rules, conventions, applyTo, prompt, template, frontmatter, description, progressive disclosure, provenance."
metadata:
  provenance:
    adaptedFrom:
      - url: "https://github.com/github/awesome-copilot/blob/main/instructions/agent-skills.instructions.md"
        license: MIT
        fidelity: structural-echo
        took: "The section skeleton for a skill-authoring guide."
      - url: "https://github.com/github/awesome-copilot/blob/main/instructions/agents.instructions.md"
        license: MIT
        fidelity: structural-echo
        took: "The shape of a checklist-driven agent-authoring guide."
      - url: "https://github.com/github/awesome-copilot/blob/main/instructions/prompt.instructions.md"
        license: MIT
        fidelity: structural-echo
        took: "The prompt-file authoring guide framing."
      - url: "https://github.com/netresearch/agent-rules-skill/blob/main/skills/agent-rules/SKILL.md"
        license: CC-BY-SA-4.0
        fidelity: partly-derived
        took: "The Detect/Extract/Draft/Verify bootstrap loop, the root-as-thin-index plus scoped-children model with explicit precedence, the root-file section skeleton, the generate-vs-curate split, and the run-the-command and exact-path verification rules."
    authoritativeSpec:
      # Skills — SKILL.md
      - "https://agentskills.io/"
      - "https://agentskills.io/specification"
      - "https://code.claude.com/docs/en/skills"
      - "https://code.visualstudio.com/docs/agent-customization/agent-skills"
      - "https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills"
      - "https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference"
      - "https://learn.chatgpt.com/docs/build-skills"
      - "https://microsoft.github.io/apm/producer/author-primitives/skills/"
      # Agents — *.agent.md
      - "https://code.claude.com/docs/en/sub-agents"
      - "https://code.claude.com/docs/en/agent-sdk/subagents"
      - "https://code.claude.com/docs/en/errors"
      - "https://code.visualstudio.com/docs/agent-customization/custom-agents"
      - "https://docs.github.com/en/copilot/reference/custom-agents-configuration"
      - "https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/create-custom-agents-for-cli"
      - "https://learn.chatgpt.com/docs/agent-configuration/subagents"
      - "https://developers.openai.com/api/docs/guides/agents/orchestration"
      # Instructions — *.instructions.md, AGENTS.md, CLAUDE.md
      - "https://agents.md/"
      - "https://code.claude.com/docs/en/memory"
      - "https://code.visualstudio.com/docs/agent-customization/custom-instructions"
      - "https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/add-custom-instructions/add-repository-instructions"
      - "https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions"
      - "https://microsoft.github.io/apm/producer/author-primitives/instructions-and-agents/"
      # Prompts — *.prompt.md (deployed as slash commands)
      - "https://code.claude.com/docs/en/slash-commands"
      - "https://code.visualstudio.com/docs/agent-customization/prompt-files"
      - "https://learn.chatgpt.com/docs/custom-prompts"
      - "https://microsoft.github.io/apm/producer/author-primitives/prompts/"
      # Deploy translation — what APM keeps, drops or reshapes per target
      - "https://microsoft.github.io/apm/reference/targets-matrix/"
      - "https://microsoft.github.io/apm/concepts/primitives-and-targets/"
      - "https://github.com/microsoft/apm/blob/8fd10ac5eafee7ca77d41cc34ba139d812fdacd5/src/apm_cli/integration/command_integrator.py"
      - "https://github.com/microsoft/apm/blob/8fd10ac5eafee7ca77d41cc34ba139d812fdacd5/src/apm_cli/integration/agent_integrator.py"
      - "https://github.com/microsoft/apm/blob/8fd10ac5eafee7ca77d41cc34ba139d812fdacd5/src/apm_cli/integration/instruction_integrator.py"
---

# Authoring Steering Files

Covers the four file types a harness **reads as prose**: skills, agents, instructions, prompts. The config a harness **executes or installs** — hooks, MCP servers, plugin bundles — is the [`meta-harness`](../meta-harness/SKILL.md) skill.

## 1) Pick the customization type first

Answer this before opening a file. Getting it wrong costs more than any amount of polish on the wrong artifact.

| What you need | Use | Decisive because |
|---|---|---|
| A task workflow, or domain knowledge with its own scripts and references, that the model pulls in when it becomes relevant | **Skill** | Model-triggered by description match; runs in the caller's context; carries its own resources |
| That same workflow, but needing a context of its own and a tool ceiling the caller must not hold | **Agent** | Session-scoped role; isolated context window, own tool policy |
| Durable conventions that must already be in force whenever a class of files is in scope | **Instruction** | Path-scoped (`applyTo` / `paths`) or always-on; steering only, no side effects |
| A task the *user* triggers by name, with inputs | **Prompt** | Explicitly invoked slash command; defines inputs, output shape and failure, nothing more |
| Something that must happen **every** time, independent of model judgment | **Hook** → [`meta-harness`](../meta-harness/SKILL.md#1-is-it-actually-harness-config) | Deterministic and event-triggered; prose cannot guarantee it |
| A new external capability — API, registry, browser, docs lookup | **MCP server** → [`meta-harness`](../meta-harness/SKILL.md#1-is-it-actually-harness-config) | Adds runtime tools; not a steering mechanism |
| One install surface for several of the above | **Plugin** → [`meta-harness`](../meta-harness/SKILL.md#1-is-it-actually-harness-config) | Versioned, marketplace-distributable bundle |

**When two rows match.** The four steering types overlap by design; three tiebreaks resolve almost every case.

- **Skill vs agent** — does the work need its own context window, or a tool policy the caller must not hold? Only then an agent. Default to one agent and make each new one clear the gate in [agent-guide.md](./references/agent-guide.md#default-to-one-agent).
- **Skill vs prompt** — who decides it runs? Model-triggered by relevance is a skill; user-triggered by name with arguments is a prompt.
- **Skill vs instruction** — is it a capability or a convention? Capabilities are skills. Instructions earn their place for durable conventions and for `applyTo`-driven skill loading — not as a home for procedures.

**The escalation gate.** Autonomous skill and instruction triggering is probabilistic. When something has to happen every single time, the answer is never stronger description prose — it is a hook or an explicit invocation (slash command, `Skill(name)` mention, path-scoped rule). Reach for [`meta-harness`](../meta-harness/SKILL.md#1-is-it-actually-harness-config) at that point rather than rewriting the description a third time.

## 2) Route to the detail

Read the row for the file being authored. Load the depth files only when the first file points at them.

| Authoring | Read first | Then, for depth |
|---|---|---|
| `SKILL.md` | [skills.md](./references/skills.md) | [skill-frontmatter.md](./references/skill-frontmatter.md), [skill-body.md](./references/skill-body.md), [skill-structure.md](./references/skill-structure.md), [skill-spec.md](./references/skill-spec.md) |
| `*.agent.md` | [agent-guide.md](./references/agent-guide.md) | [agent-frontmatter.md](./references/agent-frontmatter.md), [agent-tools.md](./references/agent-tools.md), [agent-subagent.md](./references/agent-subagent.md), [agent-handoff.md](./references/agent-handoff.md), [agent-patterns.md](./references/agent-patterns.md) |
| `*.instructions.md`, `AGENTS.md`, `CLAUDE.md` | [instructions.md](./references/instructions.md) | [instruction-bootstrapping.md](./references/instruction-bootstrapping.md) — writing a repository's *first* context files |
| `*.prompt.md` | [prompts.md](./references/prompts.md) | — |
| Any frontmatter key meant for more than one target, or a dropped-keys warning from `apm install` | [frontmatter-deploy.md](./references/frontmatter-deploy.md) | — |

## 3) Description craft — all four types

`name` and `description` are the primary discovery mechanism: the agent reads **only** these to decide whether to load a file. The lever is **shape and naming, not keyword density** — a 650-trial Claude Code activation study found keyword density had "zero measurable effect", while directive phrasing with an explicit negative constraint was ~20x more likely to trigger (OR=20.6, p<0.0001). Passive "Use when…" phrasing caps at ~77-87% activation and collapses to ~37% under competing siblings.

1. **Invest in the name first.** A discriminating, purpose-revealing name (`processing-invoices`, not `helper`) is the cheapest routing lever; treat `description` as the secondary disambiguator.
2. **Shape it as a directive with a negative constraint:**

   ```
   <What it does/domain>. ALWAYS invoke when <concrete triggers>. Do not <the default action the model would otherwise take> — use this first.
   ```

3. **Front-load** the differentiating verb and scope — the entry may be truncated and must still match on its first part.
4. **Keywords are coverage, not density.** List the concrete words a user would say inside the trigger clause; do not pad with synonyms.
5. **State sibling negative space.** Where two files overlap, say what each does NOT cover — overlapping descriptions make the model invoke every match or hesitate to invoke any.
6. Third person, active voice, present tense. Spell out acronyms. No XML tags in `name` or `description`. No reserved words in `name`: Anthropic reserves `anthropic` and `claude`; this repository adds `copilot` and `openai`.
7. **Single-line YAML.** A multi-line or block-scalar `description` is spec-valid but silently registers as invisible to some loaders.

Per-type shading: agent descriptions are keyed against sibling *agents* and have their own length target ([agent-guide.md](./references/agent-guide.md#description-length)); VS Code instruction descriptions also support semantic discovery, while the Copilot CLI contract uses `applyTo` file matches; prompt descriptions populate the slash-command menu, so lead with a verb.

### Context budget — four distinct surfaces

**Use the "Design to" column as a conservative repository target.** Per-field spec limits are requirements; aggregate targets are planning estimates, not a guarantee that every consumer will list every installed skill.

| Surface | Harness rule | Design to | Failure past the limit |
|---|---|---|---|
| One skill's `description` | agentskills.io spec: 1-1024 chars | **1024 chars** | Field is invalid |
| One skill's `description` + `when_to_use` | Claude Code: `skillListingMaxDescChars`, default 1536 chars | **1536 chars** | Cut at the cap in the listing |
| Codex: all installed skills together | 2% of the context window, or 8,000 chars when the window is unknown; names, descriptions and paths count | **8,000 chars**, including paths | Descriptions shortened first, then skills left out of the initial list with a warning |
| Claude Code: all installed skills together | `skillListingBudgetFraction`, default 1% of the context window | **2,000 tokens, roughly 8,000 chars** (1% of a 200K window) | Every name stays; descriptions of the least-used skills are dropped first, which removes their trigger words |

- **Why 200K:** current Claude models run with a 1M window, but Claude Code holds them at 200K when 1M is disabled (`CLAUDE_CODE_DISABLE_1M_CONTEXT`) or unavailable on the plan. At 1M the budget is 10,000 tokens. The char figure assumes about 4 chars per token and is an estimate.
- **The aggregate budget is shared**, including skills from other packages. About 8,000 chars is a conservative house target; Claude's token estimate and Codex's unknown-window fallback are different accounting rules.
- **Overflow differs by harness.** Claude retains names while reducing the least-used descriptions. Codex shortens descriptions and may omit entire skills; its documentation does not establish least-invoked ordering. Keep bundles focused and front-load descriptions, then inspect the actual discovery list and warnings on the target.
- Claude consumers can raise the ceilings (`skillListingBudgetFraction`, `SLASH_COMMAND_TOOL_CHAR_BUDGET`, `skillListingMaxDescChars`) or demote entries to `"name-only"` via `skillOverrides`. These are not portable Codex settings, and an author cannot assume consumers changed them.

Always-loaded instructions have their own shared budget: frontier models reliably follow ~150-200 instructions total and the harness system prompt already spends ~50. Every rule added anywhere degrades adherence to every other rule.

## 4) Frontmatter shared by all four types

**Provenance** — one convention for skills, agents, instructions and prompts: `metadata.provenance.adaptedFrom` records where content came from (with `license`, `fidelity` and `took`), and `metadata.provenance.authoritativeSpec` lists the specs that define the format. The rules, including how `fidelity` decides what `license` a file may carry, are in [skill-frontmatter.md](./references/skill-frontmatter.md#provenance-metadata-recommended). If the upstream is available as an APM package, consume it via `apm.yml` instead of copying it in.

Keys under `metadata.*` are this repository's conventions, except `metadata.short-description`, which Codex reads. The agentskills.io spec types `metadata` as a string-to-string map, so nested `metadata.provenance` is not spec-shaped.

**Author against the harness specs, not against the deployer.** APM filters or reshapes frontmatter per target before the harness reads it, so classify every key per target: case 1 **honoured** (author it), case 2 **ignored or stripped** (author it anyway and restate its intent in the body; a dropped-keys warning is not a licence to delete) or case 3 **destructive** (omit it only with an observed failure recorded and a tracker linked). A key valid on no target is not a key; put the intent in the body. The type × target matrix, the Copilot CLI authoring baseline and APM's caveats are in [frontmatter-deploy.md](./references/frontmatter-deploy.md).

- **`tools:` on a dual-deployed agent** is the one case 3 on record. Omit it unless every entry is a Claude Code tool name that Copilot documents as an alias (`Read`, `Edit`, `Grep`, `Bash`, …); MCP tool names diverge between the two. Scope Claude with `disallowedTools:` instead. See [agent-guide.md](./references/agent-guide.md#tools-field).
- **`applyTo` is load-bearing** on a scoped instruction: APM builds Claude's `paths` from `applyTo` alone. Write both, kept aligned.

## 5) Anti-patterns across all four types

- **Blurred requirements and defaults** — state hard boundaries unambiguously, without subjective escape hatches. Label preferences and defaults, and give concrete criteria for adapting them; "prefer" and "unless" are useful when that discretion is intended.
- **Skipping the consistency pass** — newer, more literal-following models are MORE damaged by contradictory instructions, not less. A lower-priority clause that conflicts with a higher one degrades adherence to both.
- **"When to use" sections in the body** — the body loads only after activation. All trigger text belongs in `description`.
- **Second person** ("you should") — use imperative mood.
- **Time-sensitive content** without an escape hatch, and **Windows-style paths** — always forward slashes.
- **Restating a tool's schema** — duplicated prose interferes with autonomous tool selection.
- **Polishing marginal content** — delete it. Coherent-but-irrelevant text measurably hurts more than incoherent filler.
- **Accumulating speculative rules** — recurring observed mistakes justify durable gotchas; first correct or consolidate existing guidance. Document established requirements and evidenced serious hazards without waiting for repeat failures, but do not append a rule after every wrong result.

**Model-generation effects** (current reasoning models): scope literally and in absolute terms ("EXACTLY and ONLY the files listed above") — models do not silently generalize a rule from one example to a whole class, nor infer unrequested work. Prefer positive output-style examples over "don't do X" lists in body prose; reserve negative constraints for the `description` field and hard guardrails.

## References

- [skills.md](./references/skills.md) · [agent-guide.md](./references/agent-guide.md) · [instructions.md](./references/instructions.md) · [prompts.md](./references/prompts.md) — the per-type guides; section 2 routes to the depth files behind each
- [frontmatter-deploy.md](./references/frontmatter-deploy.md): which keys each harness accepts and which survive APM, per type and target
- [`meta-harness`](../meta-harness/SKILL.md) — hooks, MCP servers, plugin bundles
- **Skills** — [Agent Skills spec](https://agentskills.io/) · [Claude Code](https://code.claude.com/docs/en/skills) · [VS Code](https://code.visualstudio.com/docs/agent-customization/agent-skills) · [Codex](https://learn.chatgpt.com/docs/build-skills) · [APM](https://microsoft.github.io/apm/producer/author-primitives/skills/)
- **Agents** — [Claude Code subagents](https://code.claude.com/docs/en/sub-agents) · [VS Code custom agents](https://code.visualstudio.com/docs/agent-customization/custom-agents) · [Copilot config reference](https://docs.github.com/en/copilot/reference/custom-agents-configuration) · [APM](https://microsoft.github.io/apm/producer/author-primitives/instructions-and-agents/)
- **Instructions** — [AGENTS.md convention](https://agents.md/) · [Claude Code memory](https://code.claude.com/docs/en/memory) · [VS Code custom instructions](https://code.visualstudio.com/docs/agent-customization/custom-instructions)
- **Prompts** — [Claude Code slash commands](https://code.claude.com/docs/en/slash-commands) · [VS Code prompt files](https://code.visualstudio.com/docs/agent-customization/prompt-files) · [APM](https://microsoft.github.io/apm/producer/author-primitives/prompts/)
- [Context Rot research](https://www.trychroma.com/research/context-rot) — why coherent-but-irrelevant content still hurts
- [Activation hardening](https://scottspence.com/posts/how-to-make-claude-code-skills-activate-reliably) — the 650-trial study behind the description shape
