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
      - "https://code.claude.com/docs/en/skills"
      - "https://code.visualstudio.com/docs/agent-customization/agent-skills"
      - "https://learn.chatgpt.com/docs/build-skills"
      - "https://microsoft.github.io/apm/producer/author-primitives/skills/"
      # Agents — *.agent.md
      - "https://code.claude.com/docs/en/sub-agents"
      - "https://code.claude.com/docs/en/agent-sdk/subagents"
      - "https://code.visualstudio.com/docs/agent-customization/custom-agents"
      - "https://docs.github.com/en/copilot/reference/custom-agents-configuration"
      - "https://developers.openai.com/api/docs/guides/agents/orchestration"
      # Instructions — *.instructions.md, AGENTS.md, CLAUDE.md
      - "https://agents.md/"
      - "https://code.claude.com/docs/en/memory"
      - "https://code.visualstudio.com/docs/agent-customization/custom-instructions"
      - "https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/add-custom-instructions/add-repository-instructions"
      - "https://microsoft.github.io/apm/producer/author-primitives/instructions-and-agents/"
      # Prompts — *.prompt.md (deployed as slash commands)
      - "https://code.claude.com/docs/en/slash-commands"
      - "https://code.visualstudio.com/docs/agent-customization/prompt-files"
      - "https://microsoft.github.io/apm/producer/author-primitives/prompts/"
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

- **Skill vs agent** — does the work need its own context window, or a tool policy the caller must not hold? Only then an agent. Default to one agent and make each new one clear the gate in [agents.md](./references/agents.md#default-to-one-agent).
- **Skill vs prompt** — who decides it runs? Model-triggered by relevance is a skill; user-triggered by name with arguments is a prompt.
- **Skill vs instruction** — is it a capability or a convention? Capabilities are skills. Instructions earn their place for durable conventions and for `applyTo`-driven skill loading — not as a home for procedures.

**The escalation gate.** Autonomous skill and instruction triggering is probabilistic. When something has to happen every single time, the answer is never stronger description prose — it is a hook or an explicit invocation (slash command, `Skill(name)` mention, path-scoped rule). Reach for [`meta-harness`](../meta-harness/SKILL.md#1-is-it-actually-harness-config) at that point rather than rewriting the description a third time.

## 2) Route to the detail

Read the row for the file being authored. Load the depth files only when the first file points at them.

| Authoring | Read first | Then, for depth |
|---|---|---|
| `SKILL.md` | [skills.md](./references/skills.md) | [skill-frontmatter.md](./references/skill-frontmatter.md), [skill-body.md](./references/skill-body.md), [skill-structure.md](./references/skill-structure.md), [skill-spec.md](./references/skill-spec.md) |
| `*.agent.md` | [agents.md](./references/agents.md) | [agent-frontmatter.md](./references/agent-frontmatter.md), [agent-tools.md](./references/agent-tools.md), [agent-subagent.md](./references/agent-subagent.md), [agent-handoff.md](./references/agent-handoff.md), [agent-patterns.md](./references/agent-patterns.md) |
| `*.instructions.md`, `AGENTS.md`, `CLAUDE.md` | [instructions.md](./references/instructions.md) | [instruction-bootstrapping.md](./references/instruction-bootstrapping.md) — writing a repository's *first* context files |
| `*.prompt.md` | [prompts.md](./references/prompts.md) | — |

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
6. Third person, active voice, present tense. Spell out acronyms. No XML tags, no reserved words (`anthropic`, `claude`, `copilot`, `openai`) in `name` or `description`.
7. **Single-line YAML.** A multi-line or block-scalar `description` is spec-valid but silently registers as invisible to some loaders.

Per-type shading: agent descriptions run shorter (~50-150 chars) and are keyed against sibling *agents*; instruction descriptions are a routing contract too — Copilot matches them semantically against the task even with no `applyTo` hit; prompt descriptions populate the slash-command menu, so lead with a verb.

### Context budget — four distinct surfaces

| Budget | Surface | Failure past the limit |
|---|---|---|
| 1024 chars | Per-skill `description` (agentskills.io spec limit) | Field is invalid |
| 1536 chars | Claude Code: combined `description` + `when_to_use` in the discovery listing | Overflow is truncated |
| 8000 chars | Codex: aggregate skills-preamble across **all** installed skills | Later skills get cut |
| ~15,000 chars | Claude Code: **total** name+description budget for the injected skills list | Skills past the cutoff are **invisible**, not down-ranked |

The last row dominates: past the total budget, excess skills are never considered. Pruning an unused skill helps more than trimming one description. `SLASH_COMMAND_TOOL_CHAR_BUDGET` raises the ceiling, but an author cannot assume a consumer raised it.

Always-loaded instructions have their own shared budget: frontier models reliably follow ~150-200 instructions total and the harness system prompt already spends ~50. Every rule added anywhere degrades adherence to every other rule.

## 4) Frontmatter shared by all four types

**Provenance** — the identical convention for skills, agents, instructions and prompts:

- `metadata.provenance.adaptedFrom` — a URL string, an array of URLs, or an array of objects carrying `url` plus `license` (the upstream's SPDX id), `fidelity` (`inspiration-only` / `structural-echo` / `partly-derived` / `largely-derived`) and `took` (only what was taken, never what was not). String and array forms mean the **whole file** derives from that upstream.
- `metadata.provenance.authoritativeSpec` — URLs of specs defining the format. A bare URL means cited only, nothing reproduced.
- `fidelity` decides whether upstream terms attach, and therefore what `license` the file may carry. Where `fidelity` copies expression, `license` is **required** — `scripts/check-licenses.py` rejects the file otherwise.
- `license` — omit to take the repo default for the path (`*.md` is CC-BY-SA-4.0); declare it only where an upstream obligation the default cannot satisfy forces another.

> **APM-first:** if the upstream is available as an APM package, consume it via `apm.yml` instead of copying it in. Use `adaptedFrom` only for content APM cannot manage.

Only `name`, `description` and `license` are portable spec fields. Everything under `metadata.*` is a private convention of this repository — other tools ignore it.

**Cross-harness field parity** — one file serves both Copilot and Claude Code, because each ignores the other's unknown keys:

| Concern | Copilot | Claude Code |
|---|---|---|
| Path scoping (instructions) | `applyTo` (string or array) | `paths` (array) — include both, kept aligned |
| Agent tool policy | `tools:` allowlist | `disallowedTools:` denylist |
| Agent model | provider-suffixed display strings | single alias / full ID / `inherit`, plus `effort` |

**Omit `tools:` in any dual-deployed agent.** Claude Code parses it as a strict allowlist against real tool names, Copilot vocabulary resolves to nothing, and Claude refuses to spawn the agent ("would be spawned with zero tools"). Scope Claude with `disallowedTools:` and accept that Copilot inherits all tools — APM copies agent frontmatter verbatim to every target, so one file cannot carry both. Tracked at microsoft/apm [#2108](https://github.com/microsoft/apm/issues/2108).

## 5) Anti-patterns across all four types

- **Soft-permission phrasing** — "prefer X, but Y if simpler", "unless Y makes more sense". Grep for "but … if" and "unless … makes more sense"; replace with binary rules.
- **Skipping the consistency pass** — newer, more literal-following models are MORE damaged by contradictory instructions, not less. A lower-priority clause that conflicts with a higher one degrades adherence to both.
- **"When to use" sections in the body** — the body loads only after activation. All trigger text belongs in `description`.
- **Second person** ("you should") — use imperative mood.
- **Time-sensitive content** without an escape hatch, and **Windows-style paths** — always forward slashes.
- **Restating a tool's schema** — duplicated prose interferes with autonomous tool selection.
- **Polishing marginal content** — delete it. Coherent-but-irrelevant text measurably hurts more than incoherent filler.
- **Authoring preemptively** — promote a rule only after the same mistake has recurred.

**Model-generation effects** (current reasoning models): scope literally and in absolute terms ("EXACTLY and ONLY the files listed above") — models do not silently generalize a rule from one example to a whole class, nor infer unrequested work. Prefer positive output-style examples over "don't do X" lists in body prose; reserve negative constraints for the `description` field and hard guardrails.

## References

- [skills.md](./references/skills.md) · [agents.md](./references/agents.md) · [instructions.md](./references/instructions.md) · [prompts.md](./references/prompts.md) — the per-type guides; section 2 routes to the depth files behind each
- [`meta-harness`](../meta-harness/SKILL.md) — hooks, MCP servers, plugin bundles
- **Skills** — [Agent Skills spec](https://agentskills.io/) · [Claude Code](https://code.claude.com/docs/en/skills) · [VS Code](https://code.visualstudio.com/docs/agent-customization/agent-skills) · [Codex](https://learn.chatgpt.com/docs/build-skills) · [APM](https://microsoft.github.io/apm/producer/author-primitives/skills/)
- **Agents** — [Claude Code subagents](https://code.claude.com/docs/en/sub-agents) · [VS Code custom agents](https://code.visualstudio.com/docs/agent-customization/custom-agents) · [Copilot config reference](https://docs.github.com/en/copilot/reference/custom-agents-configuration) · [APM](https://microsoft.github.io/apm/producer/author-primitives/instructions-and-agents/)
- **Instructions** — [AGENTS.md convention](https://agents.md/) · [Claude Code memory](https://code.claude.com/docs/en/memory) · [VS Code custom instructions](https://code.visualstudio.com/docs/agent-customization/custom-instructions)
- **Prompts** — [Claude Code slash commands](https://code.claude.com/docs/en/slash-commands) · [VS Code prompt files](https://code.visualstudio.com/docs/agent-customization/prompt-files) · [APM](https://microsoft.github.io/apm/producer/author-primitives/prompts/)
- [Context Rot research](https://www.trychroma.com/research/context-rot) — why coherent-but-irrelevant content still hurts
- [Activation hardening](https://scottspence.com/posts/how-to-make-claude-code-skills-activate-reliably) — the 650-trial study behind the description shape
