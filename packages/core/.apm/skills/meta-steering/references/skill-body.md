# SKILL.md Body Structure

Not all the following sections will always be required. It is better to start with a minimal set and build up as required. It is also possible for new titles to be added, depending on the specific case.

**Example Sections:**

| Section                     | Purpose                                         |
| --------------------------- | ----------------------------------------------- |
| `# Title`                   | Brief overview of what this skill enables       |
| `## Prerequisites`          | Required tools, dependencies, environment setup |
| `## Guidelines`             | Best practices and rules for using this skill   |
| `## Step-by-Step Workflows` | Numbered steps for common tasks                 |
| `## Validation Checklist`   | Checklist of required properties of output      |
| `## Troubleshooting`        | Common issues and solutions table               |
| `## References`             | Links to bundled docs or external resources     |

## Organizational Patterns

1. **Workflow-Based** (best for multi-step processes)
   - Structure: `## Overview → ## Workflow Decision Tree → ## Step 1 → ## Step 2...`
   - Example: PDF form filling with analyze → map → validate → fill → verify

2. **Task-Based** (best for tool collections)
   - Structure: `## Overview → ## Quick Start → ## Task Category 1 → ## Task Category 2...`
   - Example: PDF skill with "Merge PDFs", "Split PDFs", "Extract Text"

3. **Reference/Guidelines** (best for standards or specifications)
   - Structure: `## Overview → ## Guidelines → ## Specifications → ## Usage...`
   - Example: Brand styling with "Colors", "Typography", "Features"

4. **Capabilities-Based** (best for integrated systems)
   - Structure: `## Overview → ## Core Capabilities → ### 1. Feature → ### 2. Feature...`
   - Example: Product Management with numbered capability list

Patterns can be mixed. Most skills combine patterns (e.g., start task-based, add workflow for complex operations).

## Body Content Quality

### Delete, Don't Polish

Coherent-but-irrelevant content measurably hurts more than incoherent filler — models perform worse when a distractor preserves logical flow ([Chroma context-rot research](https://www.trychroma.com/research/context-rot)). When trimming a skill, cut marginal content outright instead of wordsmithing it shorter; a well-written aside that isn't load-bearing is worse than no aside at all.

### Author Reactively

Don't pre-empt every conceivable mistake. Promote a rule into the skill only after the same mistake recurs — ask the agent for a short retrospective on what went wrong, then encode that specific lesson as a gotcha.

### Curate Examples, Don't Enumerate

Prefer a few diverse canonical examples over exhaustive edge-case prose — one concrete example beats three paragraphs of description. Cap the example count: too many examples cause the agent to overfit to their exact phrasing instead of generalizing the underlying pattern.

### Make Verification Visible

Convert silent checks into steps that emit a visible output artifact (a file, a printed diff, a checked-off list item) — an unemitted, skipped verification step is otherwise undetectable. For sensitive or side-effectful workflows, add a final self-evaluation/completeness gate before finalizing, not just per-step checks.

### Scripts Execute, They Don't Load

Bundled scripts run via the shell without their source loading into context — only their output consumes tokens, so a large script is cheaper than an equivalent inline example. Make scripts solve the task completely rather than punting the hard part back to the agent to interpret; see [Script Requirements](./skills.md#script-requirements) for the magic-number rule.
