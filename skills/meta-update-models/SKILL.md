---
name: "meta-update-models"
description: "Resolve a metadata.modelProfile declaration in any customization file that supports the `model` frontmatter field to a current `model:` array by fetching authoritative model-provider documentation at run-time. Use when asked to update model lists, refresh model arrays, or regenerate model selections from a modelProfile."
metadata:
  provenance:
    authoritativeSpec:
      - "https://docs.github.com/en/copilot/reference/ai-models/supported-models"
      - "https://docs.github.com/en/copilot/reference/ai-models/model-comparison"
      - "https://claude.com/pricing"
      - "https://platform.claude.com/docs/en/about-claude/models/choosing-a-model#model-selection-matrix"
      - "https://developers.openai.com/codex/pricing"
      - "https://developers.openai.com/api/docs/models"
      - "https://api.kilo.ai/api/gateway/models"
---

# Update Models Skill

Reads a `metadata.modelProfile` block from any customization file that supports the top-level `model` frontmatter field, fetches the authoritative model list from **all supported model providers in parallel**, applies filter and ranking logic, and rewrites the `model:` array with the combined best-matching models across those providers.

`cost`, `latency`, and `specialisation` are abstract tiers — this skill maps them to each provider's pricing or entitlement model at run-time. Because GitHub Copilot uses premium multipliers, Claude Code and Codex use subscription entitlements plus usage ceilings, and KiloCode exposes per-model pricing flags, cost-band assignment is **approximate**. When the fetched docs are ambiguous, supplement them with a web search before committing to a selection.

Assume the user has **GitHub Copilot**, **Claude Code**, and **OpenAI Codex** subscriptions available. Do **not** treat models merely included in those subscriptions as `FREE` — they still consume limited included usage and must be mapped into `LOW`, `MEDIUM`, or `HIGH` based on relative burn, allowance, or premium status. By contrast, **KiloCode is hard-capped to truly free models only** — never spend KiloCode credits and never relax KiloCode above `isFree=true`.

Use the current on-disk file contents as the only source of truth. Read every target file before changing it, write the new `model:` array, and verify the saved file before reporting completion. Never describe a proposed model list as if it has already been applied.

## Authority and Freshness

- Treat live provider docs and API responses as higher authority than examples in this skill
- Prefer current provider capability labels and product guidance over hard-coded model families
- Treat concrete model names in examples as illustrative snapshots only; do not encode them as durable ranking rules

## Supported Scenarios

- User asks to "update models", "refresh model lists", or "regenerate model arrays"
- A customization file both supports the `model` frontmatter field and contains a `metadata.modelProfile` block, but the `model:` array is stale or missing
- After running this skill on multiple files to bring all agents up to date

## Schema Documentation Locations

The `modelProfile` schema (especially the `specialisation` enum) is documented in **multiple files**. When adding or changing allowed values, update **all** of these in a single pass:

| File | What to update |
|---|---|
| `CONTRIBUTING.md` | Field reference table + YAML example comment |
| `skills/meta-update-models/SKILL.md` | Step 1 profile example comment + Step 4 filter rules |
| `skills/meta-agent/SKILL.md` | Dual-compatible frontmatter example |
| `skills/meta-agent/references/FRONTMATTER.md` | `metadata.modelProfile` schema table |

Use `grep -r "specialisation" .` (or equivalent) before starting to catch any other locations.

## Process

### Step 1 — Validate the target and read the profile

Read the target file, confirm it supports the top-level `model` frontmatter field, and extract `metadata.modelProfile`:

```yaml
metadata:
  modelProfile:
    specialisation: NONE   # NONE | CODE | REASONING | LONG-CONTEXT
    cost: MEDIUM           # FREE | LOW | MEDIUM | HIGH
    latency: LOW           # LOW | MEDIUM | HIGH
    minDate: "2025-01-01"
```

If no `modelProfile` is present, or the file does not support the `model` frontmatter field, stop and ask the user how to proceed, using a tool if available.

### Step 2 — Fetch all providers in parallel

Fetch the model catalogue from **every supported provider** concurrently. The URLs are listed in this skill's `metadata.provenance.authoritativeSpec`. Do not rely on cached data — these pages change frequently.

| Provider | What to extract |
| --- | --- |
| **GitHub Copilot** | Display name, premium request multiplier, release status, retirement date, training date, plan inclusion, task guidance |
| **Claude Code** | Current Claude model names/families, availability or entitlement notes, usage/cost notes, and model-role guidance from Anthropic docs |
| **OpenAI Codex** | Current OpenAI model names/families available through Codex, including non-Codex models, plus availability or entitlement notes, usage/cost notes, preview status, and model-role guidance |
| **KiloCode** | `id`, `name`, `isFree`, context length, pricing fields, release status, and training date/knowledge cutoff fields when present |

> To add a new provider: fetch its model docs, add the URL to `metadata.provenance.authoritativeSpec` in this file, update `CONTRIBUTING.md`, and add its entitlement/cost-band mapping to Step 3.

### Step 3 — Map cost bands to provider metrics

Translate the abstract `cost` tier to each provider's pricing or entitlement model. **This mapping is approximate** — pricing structures differ across providers and change over time. Use the table below as a starting point, but treat the boundaries as fuzzy:

| Cost tier | GitHub Copilot | Claude Code | OpenAI Codex | KiloCode |
| --- | --- | --- | --- | --- |
| `FREE` | Multiplier = 0; qualifying entries belong in the free-first prefix | Only models explicitly documented as zero-burn or otherwise truly free-to-use. Do **not** treat bundled subscription usage as `FREE` | Only models explicitly documented as zero-burn or otherwise truly free-to-use through Codex. Do **not** treat bundled subscription usage as `FREE` | `isFree = true` or all relevant pricing fields are `0` |
| `LOW` | Multiplier ≤ 0.33 | Lowest-burn models documented as available | Lowest-burn models documented as available through Codex | **Not allowed** |
| `MEDIUM` | Multiplier ≤ 1 | Standard generally available models with moderate usage burn | Standard generally available models with moderate usage burn through Codex | **Not allowed** |
| `HIGH` | Any multiplier | Any documented premium or add-on tier available | Any documented premium, preview, or credit-backed tier available through Codex | **Not allowed** |

Interpret `cost` as a **ceiling**, not as an instruction to maximize cheapness. Once candidates are inside the allowed cost band, task fit and specialization outweigh small cost savings.

**When the mapping is unclear or the fetched docs don't provide explicit pricing tiers**, do a targeted web search (e.g. `"KiloCode free models"`, `"OpenAI models available in Codex"`, `"Claude Code available models"`) to find current pricing information. Prefer recent community sources, changelogs, or official blog posts when docs are ambiguous. Note any uncertainty in the summary reported to the user.

### Step 4 — Filter (per provider)

For each provider's catalogue, apply these filters **in order**, discarding models that fail any check:

| Filter | Rule |
| --- | --- |
| **Retired / unavailable** | Exclude any model with a retirement date on or before today's date, or any model no longer listed as available in the relevant product docs |
| **Training Date** | Exclude any model trained before `minDate`; ensures intrinsic knowledge up to that date |
| **Entitlement** | For Claude Code and OpenAI Codex, keep only models the current docs or user context show as available; for Copilot, keep models available; for KiloCode, keep only free models |
| **Cost band** | Apply the provider-specific mapping from Step 3. KiloCode remains free-only even when the profile cost is higher |
| **Specialisation** | `CODE` → keep only models described as code-optimised, coding-specialised, or agentic-coding-oriented in the docs, falling back to clear family identifiers only when the docs lack richer labels; `REASONING` → keep only models explicitly labeled for reasoning, thinking, deep debugging, or similar deliberate-reasoning tasks; `LONG-CONTEXT` → keep only models with context windows ≥ 200K tokens, sorted by context window size (largest first); `NONE` → keep all remaining models |
| **Task match** | Based on the agent's task descriptions, ensure the model is appropriate for that type of task using the product guidance in the fetched docs |

Apply the same capability bar to free and paid candidates. Do **not** include a KiloCode or multiplier-0 Copilot model merely because it is free.
For `LOW`, `MEDIUM`, and `HIGH` profiles, a free candidate must be **explicitly validated as competitive** with the paid candidates for that task. "Acceptable" is not sufficient.

### Step 5 — Format model names

Before merging, format each model's display name and append the provider suffix used by this repository's frontmatter.

Use the **exact accepted display strings** for this repository's harness. Preserve spelling and casing exactly. Do **not** normalize names across providers when the working display strings differ.

If the same working model name already appears elsewhere in the workspace, reuse that exact spelling/casing unless you have evidence that it is broken.

All model names in this section are illustrative examples only. Always use the current names returned by the fetched live documentation or API.

**GitHub Copilot:** Use the exact display name from the official documentation, append `(copilot)`.

**Claude Code:** Use the exact accepted display name for the unify provider and append `(unify-chat-provider)`. In practice this usually omits vendor prefixes.

**OpenAI Codex:** Use the exact accepted display name for the unify provider and append `(unify-chat-provider)`. In practice this usually omits vendor prefixes.

**KiloCode / unify-backed non-Copilot entries:** Start from the API or provider display name, strip vendor prefixes such as `Anthropic: `, `OpenAI: `, `Google: `, `xAI: `, `MiniMax: `, or `Xiaomi: ` unless existing workspace usage shows the prefix is required, then append `(unify-chat-provider)`.

The same model family can legitimately have different accepted strings across providers. For example, `GPT-5.4 mini (copilot)` and `GPT-5.4 Mini (unify-chat-provider)` are different strings and must not be normalized to match each other.

| API `name` field                          | Display name                                    |
| ----------------------------------------- | ----------------------------------------------- |
| `OpenAI: GPT-5.4 Mini`                    | `GPT-5.4 Mini (unify-chat-provider)`           |
| `Anthropic: Claude Sonnet 4.6`            | `Claude Sonnet 4.6 (unify-chat-provider)`      |
| `xAI: Grok Code Fast 1 Optimized (experimental, free)` | `Grok Code Fast 1 Optimized (experimental, free) (unify-chat-provider)` |
| `Xiaomi: MiMo-V2-Pro (free)`              | `MiMo-V2-Pro (free) (unify-chat-provider)`     |

| Provider | Suffix | Example |
| --- | --- | --- |
| GitHub Copilot | ` (copilot)` | `Example Copilot Model (copilot)` |
| Claude Code | ` (unify-chat-provider)` | `Example Claude Model (unify-chat-provider)` |
| OpenAI Codex | ` (unify-chat-provider)` | `Example Codex Model (unify-chat-provider)` |
| KiloCode | ` (unify-chat-provider)` | `Example Free Model (unify-chat-provider)` |

### Step 6 — Merge and rank

Combine the filtered, suffixed lists from all providers into a single pool.

The `model:` array is ordered, and the harness chooses the **first available** option.

For `FREE` profiles, validated free-capable candidates belong first.
For `LOW`, `MEDIUM`, and `HIGH` profiles, **do not** start with a free-first prefix. Prefer the strongest paid candidates inside the requested band, and only include a free candidate if it has been explicitly validated as competitive.

**Ordering rules:**
1. If `cost = FREE`, build a **free-first prefix** from candidates that pass the full filter set:
  - Top **KiloCode free** model, but only if it is genuinely good enough for the task and profile
  - Any qualifying **GitHub Copilot** models with premium multiplier = 0
2. If `cost` is `LOW`, `MEDIUM`, or `HIGH`, start with the best-fitting **paid** coverage in this order when those providers still have candidates left after cost filtering:
  - Top **Claude Code-backed** model
  - Top **OpenAI-backed** model available through Codex
  - Top **GitHub Copilot** model not already included in the free-first prefix
3. For non-`FREE` profiles, append a free KiloCode or multiplier-0 Copilot model only when it remains genuinely competitive after side-by-side comparison with the paid candidates and does not displace a stronger paid fit.
4. After the reserved coverage is in place, fill remaining slots from the merged ranking.
5. Within each provider group, sort by:
  - **Specialisation and task fit** — models explicitly optimized for the job ahead of generic or mini variants. For example: `REASONING` profiles usually prefer full reasoning-oriented models over mini or fast variants; `CODE` profiles prefer coding-specialized families over general-purpose models when both remain within the allowed band
  - **Latency** — `LOW` profile: prefer smallest/fastest models first; `HIGH`: prefer largest/most capable; `MEDIUM`: neutral
  - **Cost** — lower incremental cost or usage burn first, but only as a tie-breaker after task fit and latency, normalised by the provider-specific rules above
  - **Recency** — newer release date first; prefer GA over preview within the same capability tier

**Count rules:**
- Always include **at least 1 Claude Code-backed model**, **1 OpenAI-backed model available through Codex**, and **1 GitHub Copilot model** when that provider has at least one candidate left after entitlement and cost-band filtering.
- For `FREE` profiles, it is valid for Claude Code and OpenAI Codex to contribute **0** models when the fetched docs do not show any truly zero-burn options.
- For `LOW`, `MEDIUM`, and `HIGH` profiles, include **0 KiloCode models by default**. Add one only when the free model has been explicitly validated as competitive for the task and is being kept as an additional fallback rather than displacing a stronger paid option.
- For `LOW`, `MEDIUM`, and `HIGH` profiles, do **not** automatically include multiplier-0 GitHub Copilot models before paid entries. Treat them as optional extra fallbacks, not default leaders.
- Take the **top 1–8 models total** from the merged ranking. Fewer is acceptable when not enough models pass the filters for the requested cost band.

**Reasoning output (required):**
When reporting results to the user, provide a brief justification for each addition or removal compared to the previous `model:` array. Format as a bullet list per agent file:
- `+ Model Name (provider)` — reason for addition
- `- Model Name (provider)` — reason for removal

### Step 7 — Rewrite the `model:` array

Replace the existing `model:` line in the frontmatter with the new array. If it is absent, insert it at the top level of the frontmatter alongside the other Copilot fields: after `tools:` if present, otherwise before `metadata:` if present, otherwise before the closing `---`. Use single-quoted YAML array format.

```yaml
model: ['Example Free Model (unify-chat-provider)', 'Example Free Copilot Model (copilot)', 'Example Claude Model (unify-chat-provider)', 'Example Codex Model (unify-chat-provider)', 'Example Copilot Model (copilot)']
```

Do **not** modify any other frontmatter fields. Do **not** remove `metadata.modelProfile` — it is the source of truth for future updates.

## Example

**Profile:**

```yaml
metadata:
  modelProfile:
    specialisation: CODE
    cost: LOW
    latency: LOW
    minDate: "2025-01-01"
```

**Resolution:**

- KiloCode: default to excluding free models because the profile is not `FREE`; only include one after explicit validation if it is genuinely competitive with the paid options
- Claude Code: choose a current available Claude coding-oriented model with low relative usage burn that still meets the CODE and LOW-latency profile
- OpenAI Codex: choose a current available OpenAI model through Codex that still meets the CODE and LOW-latency profile; prefer coding-specialized models over generic mini models when both are within band
- Copilot: prefer current coding-specialized Copilot models within the allowed band; do not lead with multiplier-0 entries merely because they are cheaper
- Start with the best paid candidates, then add any validated free fallback only if it remains competitive and useful

**Result** *(illustrative; final names must come from the live docs and API)*:

```yaml
model: ['Example Claude Coding Model (unify-chat-provider)', 'Example OpenAI Codex Model (unify-chat-provider)', 'Example Copilot Coding Model (copilot)']
```

**Reasoning output:**
- `+ Example Claude Coding Model (unify-chat-provider)` — best low-latency Claude fit for a non-`FREE` CODE profile
- `+ Example OpenAI Codex Model (unify-chat-provider)` — CODE-specialized model preferred over a cheaper generic mini alternative within the allowed band
- `+ Example Copilot Coding Model (copilot)` — satisfies Copilot coverage with a coding-focused model rather than a multiplier-0 generic fallback
- `- Example Free Model (unify-chat-provider)` — rejected because the profile is non-`FREE` and the free candidate was not materially stronger than the paid options
- `- Example Mini Model (copilot)` — rejected because a coding-specialized model was available within the same allowed band

## Bulk Updates

To update all supported customization files:

1. List all relevant customization files in the workspace (`*.agent.md`, `SKILL.md`, `*.prompt.md`, `*.instructions.md`)
2. Keep only files that both contain `metadata.modelProfile` and support the top-level `model` frontmatter field, then capture each file's current `model:` array from disk
3. For each target file, run Steps 1–7
4. Re-read or diff every changed file before preparing the final response
5. Report a summary table: file → old model count → verified new model list

## Constraints

- Always fetch docs fresh — never rely on a cached or remembered model list
- Preserve all other frontmatter fields exactly as-is
- Never claim a file was "updated" until the edit has been applied and verified on disk
- If a target file changes after the initial read, re-read it before editing
- If the docs are unreachable, report the error and do not modify the file

## Provider-Specific Considerations

### KiloCode Integration

1. **Pricing Data**: Consult the KiloCode API endpoint `https://api.kilo.ai/api/gateway/models` to retrieve current model pricing information.

2. **Free-only policy**: Only select models where `isFree=true` or where the relevant pricing fields are zero. Never relax KiloCode above free, even when the profile requests `LOW`, `MEDIUM`, or `HIGH` cost.

  For non-`FREE` profiles, default to excluding KiloCode entirely. Only include a free KiloCode model when it is genuinely strong enough for the task after the normal specialisation, latency, and task-fit filters **and** remains competitive with the paid options. Do not add a weak KiloCode entry just to keep a free option first.

3. **Model Naming**: Derive display names from the `name` field in the API response. Strip the vendor prefix (everything before and including `: `). Do NOT use the `id` field as the display name. Do NOT invent or hallucinate model names — only use names that appear in the API response.

   ❌ `corethink:free (unify-chat-provider)` — fabricated name
    ✅ `Example Model (unify-chat-provider)` — derived from API `name: "Vendor: Example Model"`

4. **Model Compatibility**: When filtering models for task compatibility:
   - For **code-focused agents**, prioritize models with `code` or `coder` in their `id` or those explicitly described as optimized for code generation
   - For **research-focused agents**, prioritize models with larger context windows and general knowledge capabilities
   - For **general-purpose agents**, consider a balance of cost, performance, and knowledge cutoff dates

5. **Knowledge Cutoff**: Use the `training_date` or `knowledge_cutoff` field from the KiloCode API response to apply the `minDate` filter correctly, ensuring models have intrinsic knowledge up to the specified date.

### Claude Code Integration

1. **Entitlement check**: Derive available Claude models from explicit user context and the current Claude Code / Anthropic docs. Do **not** treat generally available Claude models as `FREE` unless the docs explicitly mark them as zero-burn or otherwise free to use.

2. **Model Identification**: Use Claude model names from Anthropic's current Claude Code and model-selection documentation, appending `(unify-chat-provider)` in the final array.

3. **Task Compatibility**: When assessing Claude models:
  - **Code generation/completion**: Prefer the current balanced or coding-oriented Claude class before the smallest latency-first class; reserve the flagship reasoning tier for `HIGH` or deep-debugging profiles
  - **Research/analysis**: Prefer Claude models with the largest context windows and strongest reasoning guidance
  - **General assistance**: Prefer the balanced default class unless the profile explicitly favors latency or maximum reasoning depth
  - **Interactive product / UX / planning work**: Prefer the balanced or reasoning-oriented class over the smallest/fastest class on non-`FREE` `MEDIUM` / `HIGH` profiles unless the task is clearly lightweight

### OpenAI Codex Integration

1. **Entitlement check**: Derive available OpenAI models from explicit user context and the current Codex / OpenAI docs. Do **not** treat generally available OpenAI models as `FREE` unless the docs explicitly mark them as zero-burn or otherwise free to use through Codex.

2. **Model Identification**: Select from the full OpenAI model catalogue available through Codex, not only models whose names include `Codex`. Use the official Codex pricing and OpenAI models documentation, appending `(unify-chat-provider)` in the final array.

3. **Task Compatibility**: When assessing OpenAI models available through Codex:
  - **Code generation/completion**: Prefer the current coding-specialized or agentic-coding family first. Do not let a generic mini model outrank a coding-specialized model merely because it is cheaper when both remain within the requested cost band
  - **Low latency**: Prefer the lightest currently available OpenAI model that still meets the requested task profile, but do not trade away a materially better reasoning or coding-specialized fit solely for speed
  - **Deep reasoning/debugging**: Prefer the strongest currently available reasoning or coding model that still meets the requested cost tier
  - **Reasoning-heavy product / planning work**: Prefer full reasoning-capable models over mini or fast variants by default; use mini only when the profile explicitly prioritizes throughput over reasoning depth

### Copilot Integration

1. **Model Identification**: Use the display names from the official Copilot documentation, appending the `(copilot)` suffix for clarity in the final model array.

2. **Task Compatibility**: When assessing model suitability for specific agent tasks:
  - **Code generation/completion**: Prioritize coding-specialized or agentic-coding entries before generic mini models when the allowed cost band permits them
  - **Research/analysis**: Prioritize models with larger context windows and more recent knowledge cutoffs
  - **General assistance**: Consider a balance of cost and capability
  - **Reasoning-heavy discovery / planning agents**: Prefer models the docs position for deep reasoning before mini or latency-first variants
