---
name: "meta-update-models"
description: "Resolve a metadata.modelProfile declaration in an agent or skill file to a current model: array by fetching authoritative provider documentation at run-time. Use when asked to update model lists, refresh model arrays, or regenerate model selections from a modelProfile."
metadata:
  provenance:
    authoritativeSpec:
      - "https://docs.github.com/en/copilot/reference/ai-models/supported-models"
      - "https://docs.github.com/en/copilot/reference/ai-models/model-comparison"
      - "https://api.kilo.ai/api/gateway/models"
---

# Update Models Skill

Reads a `metadata.modelProfile` block from an agent or skill file, fetches the authoritative model list from **all supported providers in parallel**, applies filter and ranking logic, and rewrites the `model:` array with the combined best-matching models across providers.

`cost`, `latency`, and `specialisation` are abstract tiers — this skill maps them to each provider's pricing metric at run-time. Because provider pricing structures vary and change frequently, cost-band assignment is **approximate**. When the fetched docs are ambiguous, supplement them with a web search before committing to a selection.

Use the current on-disk file contents as the only source of truth. Read every target file before changing it, write the new `model:` array, and verify the saved file before reporting completion. Never describe a proposed model list as if it has already been applied.

## When to Use

- User asks to "update models", "refresh model lists", or "regenerate model arrays"
- A `metadata.modelProfile` block exists in a file but the `model:` array is stale or missing
- After running this skill on multiple files to bring all agents up to date

## Process

### Step 1 — Read the profile

Read the target file and extract `metadata.modelProfile`:

```yaml
metadata:
  modelProfile:
    specialisation: NONE   # NONE | CODE
    cost: MEDIUM           # FREE | LOW | MEDIUM | HIGH
    latency: LOW           # LOW | MEDIUM | HIGH
    minDate: "2025-01-01"
```

If no `modelProfile` is present, stop and ask the user how to proceed, using a tool if available.

### Step 2 — Fetch all providers in parallel

Fetch the model catalogue from **every supported provider** concurrently. The URLs are listed in this skill's `metadata.provenance.authoritativeSpec`. Do not rely on cached data — these pages change frequently.

| Provider     | What to extract                                                                           |
| ------------ | ----------------------------------------------------------------------------------------- |
| **Copilot**  | Display name, premium request multiplier, release status, retirement date, training date |
| **KiloCode** | `id`, context size length, cost indicators, release status, training date/knowledge cutoff |

> To add a new provider: fetch its model docs, add the URL to `metadata.provenance.authoritativeSpec` in this file and to `CONTRIBUTING.md`, and add its cost-band mapping to Step 3.

### Step 3 — Map cost bands to provider metrics

Translate the abstract `cost` tier to each provider's pricing metric. **This mapping is approximate** — pricing structures differ across providers and change over time. Use the table below as a starting point, but treat the boundaries as fuzzy:

| Cost tier | Copilot           | KiloCode                    |
| --------- | ----------------- | --------------------------- |
| `FREE`    | Multiplier = 0    | `price=0`                   |
| `LOW`     | Multiplier ≤ 0.33 | Lower price                 |
| `MEDIUM`  | Multiplier ≤ 1    | Standard price              |
| `HIGH`    | Any multiplier    | Any model                   |

**When the mapping is unclear or the fetched docs don't provide explicit pricing tiers**, do a targeted web search (e.g. `"KiloCode free models"`, `"Copilot model cost comparison 2026"`) to find current pricing information. Prefer recent community sources, changelogs, or official blog posts when docs are ambiguous. Note any uncertainty in the summary reported to the user.

### Step 4 — Filter (per provider)

For each provider's catalogue, apply these filters **in order**, discarding models that fail any check:

| Filter             | Rule                                                                                                 |
| ------------------ | ---------------------------------------------------------------------------------------------------- |
| **Retired**        | Exclude any model with a retirement date on or before today's date                                  |
| **Training Date**  | Exclude any model trained before `minDate`; ensures intrinsic knowledge up to that date              |
| **Cost band**      | Apply the provider-specific mapping from Step 3                                                      |
| **Specialisation** | `CODE` → keep only Codex-family and code-optimised variants (names containing "Codex", "Raptor", "Goldeneye", or described as code-optimised in the docs); `NONE` → keep all remaining models |
| **Task match**     | Based on the agent's task descriptions, ensure the model is appropriate for that type of task based on the recommendations in the docs. |

### Step 5 — Format model names

Before merging, format each model's display name and append the provider suffix:

**Copilot:** Use the display name from the official documentation, append `(copilot)`.

**KiloCode:** Derive the display name from the API `name` field by stripping the vendor prefix (text before and including the first `: `). Append `(unify-chat-provider)`.

| API `name` field                          | Display name                                    |
| ----------------------------------------- | ----------------------------------------------- |
| `DeepSeek: DeepSeek V3.2`                 | `DeepSeek V3.2 (unify-chat-provider)`           |
| `Anthropic: Claude 3.7 Sonnet (thinking)` | `Claude 3.7 Sonnet (thinking) (unify-chat-provider)` |

| Provider | Suffix                   | Example                                     |
| -------- | ------------------------ | ------------------------------------------- |
| Copilot  | ` (copilot)`             | `GPT-5 mini (copilot)`                      |
| KiloCode | ` (unify-chat-provider)` | `DeepSeek V3.2 (unify-chat-provider)`       |

### Step 6 — Merge and rank

Combine the filtered, suffixed lists from all providers into a single pool.

**Ordering rules:**
1. **KiloCode models always come first** in the final array, followed by Copilot models
2. Within each provider group, sort by:
   - **Latency** — `LOW` profile: prefer smallest/fastest models first; `HIGH`: prefer largest/most capable; `MEDIUM`: neutral
   - **Cost** — lower cost first (normalised across providers using the abstract tier)
   - **Recency** — newer release date first; prefer GA over preview within the same capability tier

**Count rules:**
- Always include **at least 2 KiloCode models**. If fewer than 2 pass the filters, relax the cost band one tier up until 2 models qualify.
- Take the **top 4–8 models total** from the merged ranking. Fewer is acceptable only when not enough models pass the filters even after relaxation.

**Reasoning output (required):**
When reporting results to the user, provide a brief justification for each addition or removal compared to the previous `model:` array. Format as a bullet list per agent file:
- `+ Model Name (provider)` — reason for addition
- `- Model Name (provider)` — reason for removal

### Step 7 — Rewrite the `model:` array

Replace the existing `model:` line (or insert one after the `tools:` line if absent) in the frontmatter with the new array. Use single-quoted YAML array format. KiloCode models always appear first:

```yaml
model: ['DeepSeek V3.2 (unify-chat-provider)', 'Claude 3.7 Sonnet (thinking) (unify-chat-provider)', 'GPT-5 mini (copilot)', 'Raptor mini (copilot)', 'GPT-4.1 (copilot)']
```

Do **not** modify any other frontmatter fields. Do **not** remove `metadata.modelProfile` — it is the source of truth for future updates.

## Example

**Profile:**

```yaml
metadata:
  modelProfile:
    specialisation: CODE
    cost: FREE
    latency: LOW
    minDate: "2025-01-01"
```

**Resolution:**

- KiloCode: `price=0` models trained after `2025-01-01` → resolved from live API, names derived from `name` field
- Copilot: multiplier = 0 → filter models trained after `2025-01-01` → `GPT-5 mini`, `GPT-4.1`, `Grok Code Fast 1`, `Raptor mini` (Codex-family free)
- KiloCode models placed first, then Copilot models; rank by latency LOW (smallest first)

**Result** *(Copilot models known; KiloCode names illustrative)*:

```yaml
model: ['DeepSeek V3.2 (unify-chat-provider)', 'Claude 3.7 Sonnet (thinking) (unify-chat-provider)', 'GPT-5 mini (copilot)', 'Raptor mini (copilot)', 'GPT-4.1 (copilot)', 'Grok Code Fast 1 (copilot)']
```

**Reasoning output:**
- `+ DeepSeek V3.2 (unify-chat-provider)` — free KiloCode model with code optimisation, large context
- `+ Claude 3.7 Sonnet (thinking) (unify-chat-provider)` — free KiloCode model with strong reasoning
- `+ GPT-5 mini (copilot)` — free Copilot model, fast for LOW latency profile
- `- Old Model X (copilot)` — retired or no longer meets cost/latency criteria

## Bulk Updates

To update all agent files:

1. List all `*.agent.md` files in the workspace
2. Read each file that contains `metadata.modelProfile` and capture its current `model:` array from disk
3. For each target file, run Steps 1–8
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

2. **Model Naming**: Derive display names from the `name` field in the API response. Strip the vendor prefix (everything before and including `: `). Do NOT use the `id` field as the display name. Do NOT invent or hallucinate model names — only use names that appear in the API response.

   ❌ `corethink:free (unify-chat-provider)` — fabricated name
   ✅ `DeepSeek V3.2 (unify-chat-provider)` — derived from API `name: "DeepSeek: DeepSeek V3.2"`

3. **Model Compatibility**: When filtering models for task compatibility:
   - For **code-focused agents**, prioritize models with `code` or `coder` in their `id` or those explicitly described as optimized for code generation
   - For **research-focused agents**, prioritize models with larger context windows and general knowledge capabilities
   - For **general-purpose agents**, consider a balance of cost, performance, and knowledge cutoff dates

4. **Knowledge Cutoff**: Use the `training_date` or `knowledge_cutoff` field from the KiloCode API response to apply the `minDate` filter correctly, ensuring models have intrinsic knowledge up to the specified date.

### Copilot Integration

1. **Model Identification**: Use the display names from the official Copilot documentation, appending the `(copilot)` suffix for clarity in the final model array.

2. **Task Compatibility**: When assessing model suitability for specific agent tasks:
   - **Code generation/completion**: Prioritize Codex-family models and those with explicit code optimization
   - **Research/analysis**: Prioritize models with larger context windows and more recent knowledge cutoffs
   - **General assistance**: Consider a balance of cost and capability
