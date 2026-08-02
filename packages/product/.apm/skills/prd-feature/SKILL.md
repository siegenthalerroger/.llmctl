---
name: prd-feature
description: "Creates type-aware Feature PRDs derived from a parent epic (platform, engine, domain). ALWAYS invoke when writing or auditing a feature-level PRD so personas, workflows, requirements, and UX depth inherit the parent epic's type. Do not draft a Feature PRD without this skill — for the parent epic-level PRD use prd-epic. Keywords: PRD, feature, epic, persona, workflow, requirements, UX."
metadata:
  provenance:
    adaptedFrom:
      - url: "https://github.com/github/awesome-copilot/blob/main/skills/breakdown-feature-prd/SKILL.md"
        license: MIT
        fidelity: largely-derived
---

# Feature PRD Prompt

## Before Writing: Read the Parent Epic and Inherit Its Type

Before drafting the feature PRD:

- Read the parent epic first and classify it as **Platform**, **Engine**, or **Domain**.
- The feature **inherits the parent epic type**. If the requested feature does not fit that type, stop and ask whether it belongs in another epic instead of forcing it into the wrong template.

| Parent Epic Type | Personas | Section 5 | UX Discovery |
|---|---|---|---|
| **Platform** | Developer / Operator only | Operational or integration workflows | Only if the feature has a real human workflow |
| **Engine** | Developer only | Integration / lifecycle workflows | Rare |
| **Domain** | Direct user roles | Standard user stories | Common when flows need depth |

- **Platform / Engine features** focus on contracts, states, failure handling, extensibility, and operations.
- **Domain features** focus on direct user value, workflows, and user-facing outcomes.
- If a Platform / Engine feature starts to require domain-user journeys, challenge the epic boundary.

## Goal

Act as an expert Product Manager for a large-scale SaaS platform. Your primary responsibility is to take a high-level feature or enabler from an Epic and create a detailed Product Requirements Document (PRD). This PRD will serve as the single source of truth for the engineering team and will be used to generate a comprehensive technical specification.

Review the user's request for a new feature and the parent Epic, and generate a thorough PRD. If you don't have enough information, ask clarifying questions to ensure all aspects of the feature are well-defined.

## Output Format

The output should be a complete PRD in Markdown format, saved to `docs/product/{epic-name}/{feature-name}/prd.md`.

### PRD Structure

#### 1. Feature Name

- A clear, concise, and descriptive name for the feature.

#### 2. Epic

- Link to the parent Epic PRD and Architecture documents.

#### 3. Goal

- **Problem:** Describe the user problem or business need this feature addresses (3-5 sentences).
- **Solution:** Explain how this feature solves the problem.
- **Impact:** What are the expected outcomes or metrics to be improved (e.g., user engagement, conversion rate, etc.)?

#### 4. User Personas

- Inherit the parent epic type: direct user roles for **Domain** features, Developer / Operator personas for **Platform / Engine** features.

#### 5. User Stories / Workflows

- For **Domain** features, ask: *"Should I run a UX discovery session first (JTBD analysis, full journey map, edge cases) before we commit to requirements?"* Propose the **UX Expert agent** if the feature involves a meaningful user workflow. The UX Expert writes directly into this PRD.
- For **Platform / Engine** features, use developer/operator or integration workflows instead of forcing consumer-style end-user stories. Capture contracts, state transitions, failure handling, and extension points.
- Write stories or workflows in the format that best matches the parent type, while still covering primary paths and edge cases.

#### 6. Requirements

- **Functional Requirements:** A concise list of what the system must do. Keep to ≤12 requirements total. One sentence per requirement. Group by concern — never produce sub-tables per entity instance (e.g., one row per CRUD operation per entity type). A single requirement like "Admin can create, edit, and delete [entity] with deletion safeguards" is better than four separate rows. For Platform / Engine features, include contracts, state transitions, failure modes, observability expectations, and extension hooks where relevant.
- **Non-Functional Requirements:** ≤6 requirements. One sentence each, covering performance, accessibility, and security.

#### 7. Acceptance Criteria

- For each user story or major requirement, provide a set of acceptance criteria.
- Use a clear format, such as a checklist or Given/When/Then. This will be used to validate that the feature is complete and correct.

#### 8. Out of Scope

- Clearly list what is _not_ included in this feature to avoid scope creep.

## Context Template

- **Epic:** [Link to the parent Epic documents]
- **Feature Idea:** [A high-level description of the feature request from the user]
- **Target Users:** [Optional: Any initial thoughts on who this is for]
