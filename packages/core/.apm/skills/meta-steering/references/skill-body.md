# SKILL.md Body Structure

Not all the following sections will always be required. It is better to start with a minimal set and build up as required. It is also possible for new titles to be added, depending on the specific case.

**Example Sections:**

| Section | Purpose |
| --- | --- |
| `# Title` | One sentence stating what the skill enables; be specific about the domain |
| `## Prerequisites` | Only tools, services or configuration that cannot be assumed, with exact install commands |
| `## Guidelines` | Best practices and rules for using this skill |
| `## Step-by-Step Workflows` | Numbered steps where order or dependencies matter. Describe what to accomplish at each stage rather than hardcoded paths; move workflows over ~5 steps into `references/` |
| `## Gotchas` | Proactive warnings about non-obvious behavior: bold the key constraint, then explain why. Include whenever the skill has non-obvious behavior |
| `## Validation Checklist` | Checklist of required properties of output |
| `## Troubleshooting` | Reactive fixes as a symptom → solution table |
| `## References` | Links to bundled docs, external documentation or related skills |

Never add a `## When to Use` section: the body loads only after activation, so trigger text belongs in `description`.

## Organizational Patterns

- **Workflow-Based** (best for processes with ordering or dependencies)
   - Structure: `## Overview → ## Workflow Decision Tree → ## Step 1 → ## Step 2...`
   - Example: PDF form filling with analyze → map → validate → fill → verify

- **Task-Based** (best for tool collections)
   - Structure: `## Overview → ## Quick Start → ## Task Category 1 → ## Task Category 2...`
   - Example: PDF skill with "Merge PDFs", "Split PDFs", "Extract Text"

- **Reference/Guidelines** (best for standards or specifications)
   - Structure: `## Overview → ## Guidelines → ## Specifications → ## Usage...`
   - Example: Brand styling with "Colors", "Typography", "Features"

- **Capabilities-Based** (best for integrated systems)
   - Structure: `## Overview → ## Core Capabilities → ### 1. Feature → ### 2. Feature...`
   - Example: Product Management with numbered capability list

Patterns can be mixed. Most skills combine patterns (e.g., start task-based, add workflow for complex operations).

Use decision criteria for open-ended work. When numbered steps and progress checklists earn their place is in [Workflow Requirements](./skills.md#workflow-requirements).

## Body Content Quality

### Delete, Don't Polish

Coherent-but-irrelevant content measurably hurts more than incoherent filler — models perform worse when a distractor preserves logical flow ([Chroma context-rot research](https://www.trychroma.com/research/context-rot)). When trimming a skill, cut marginal content outright instead of wordsmithing it shorter; a well-written aside that isn't load-bearing is worse than no aside at all.

### Author Reactively

Don't pre-empt every conceivable mistake or append a gotcha after every wrong result. Diagnose observed failures, then correct, clarify or consolidate existing guidance before adding a rule. Recurring mistakes can justify a durable gotcha; established requirements and evidenced serious hazards should be documented without waiting for recurrence.

### Curate Examples, Don't Enumerate

Prefer a few diverse canonical examples over exhaustive edge-case prose — one concrete example beats three paragraphs of description. Cap the example count: too many examples cause the agent to overfit to their exact phrasing instead of generalizing the underlying pattern.

### Make Verification Visible

Record verification results in existing tool output, a diff or a concise summary so completion can be checked. A separate artifact or checklist is useful only when the task needs it. For sensitive or side-effectful workflows, include a final completeness check before finalizing.

### Scripts Execute, They Don't Load

Bundled scripts run via the shell without their source loading into context — only their output consumes tokens, so a large script is cheaper than an equivalent inline example. Make scripts solve the task completely rather than punting the hard part back to the agent to interpret; see [Script Requirements](./skills.md#script-requirements) for the magic-number rule.
