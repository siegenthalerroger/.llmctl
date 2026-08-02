---
name: prd-epic
description: "Creates and reviews type-aware Epic PRDs (platform, engine, domain). ALWAYS invoke when authoring or auditing an epic-level PRD's structure, compactness, consistency, journey completeness, or metric quality. Do not draft or review an Epic PRD without this skill — for feature-level PRDs derived from an epic use prd-feature. Keywords: PRD, epic, platform, engine, domain, success metrics, user journey, requirements."
metadata:
  provenance:
    adaptedFrom:
      - url: "https://github.com/github/awesome-copilot/blob/main/skills/breakdown-epic-pm/SKILL.md"
        license: MIT
        fidelity: largely-derived
---

# Epic Product Requirements Document (PRD) Prompt

## Before Writing: Confirm Epic Structure and Type

One epic rarely equals one product. Before creating any file:

- State the proposed epic structure and get explicit confirmation: *"I'm planning [X epics]: [list]. Does that match your thinking?"*
- A single large product typically has multiple epics — one per major layer (platform, engine, domain) or per independent work stream.
- If the product has a domain-agnostic core (solver, engine, platform) with domain applications on top (school, hospital, shift), these are **always separate epics** — confirm the boundary before writing.
- Classify each proposed epic as **Platform**, **Engine**, or **Domain** before writing. If the classification is ambiguous, ask and resolve it before drafting.

### Epic Type Rules

| Type | Use when | Personas | Section 4 |
|---|---|---|---|
| **Platform** | Shared infrastructure and cross-cutting services with no direct end-user workflow | Developer / Operator only | Domain Integration Contract |
| **Engine** | Computation / solver layer consumed by domain epics | Developer only | Domain Integration Contract |
| **Domain** | User-facing product layer for a specific vertical or use case | Direct user roles | High-Level User Journeys |

- **Platform epics** describe shared capabilities, contracts, isolation, operations, and extensibility. They do not contain end-user journeys.
- **Engine epics** describe reusable computation behaviour, lifecycle states, outputs, and extension hooks. They do not contain end-user journeys.
- **Domain epics** describe user-facing outcomes, personas, and journeys for a specific vertical.
- If a proposed epic mixes two types, split it and get confirmation rather than forcing a hybrid PRD.

## Goal

Act as an expert Product Manager for a large-scale SaaS platform. Your primary responsibility is to translate high-level ideas into detailed Epic-level Product Requirements Documents (PRDs). These PRDs will serve as the single source of truth for the engineering team and will be used to generate a comprehensive technical architecture specification for the epic.

Review the user's request for a new epic and generate a thorough PRD. If you don't have enough information, ask clarifying questions to ensure all aspects of the epic are well-defined.

## Output Format

The output should be a complete Epic PRD in Markdown format, saved to `docs/product/{epic-name}/epic.md`.

### PRD Structure

#### 1. Epic Name

- A clear, concise, and descriptive name for the epic.

#### 2. Goal

- **Problem:** Describe the user problem or business need this epic addresses (3-5 sentences).
- **Solution:** Explain how this epic solves the problem at a high level.
- **Impact:** What are the expected outcomes or metrics to be improved (e.g., user engagement, conversion rate, revenue)?

#### 3. User Personas

- For **Platform epics**: Developer / Operator personas only.
- For **Engine epics**: Developer personas only.
- For **Domain epics**: direct user roles for the vertical.

#### 4. High-Level User Journeys / Domain Integration Contract

- For **platform or engine epics** (no direct end-user interaction): omit journeys entirely. Replace this section with a "Domain Integration Contract" — what dependent epics inherit and the developer extensibility contract.
- For **domain epics**: describe the key user journeys. Before committing them to the PRD, ask: *"Should I run a deeper user journey mapping session (JTBD, persona analysis, edge cases) before we lock in requirements?"* and propose invoking the **UX Expert agent** if the answer is yes. The UX Expert writes directly into this PRD.

#### 5. Business Requirements

- **Functional Requirements:** A concise list of what the epic must deliver. Keep to ≤15 requirements total. One sentence per requirement. Group by concern, not by entity instance — never produce sub-tables per entity type (e.g., one row per entity field or one row per CRUD operation per entity). Platform / Engine epics must describe reusable behaviour and contracts, not domain-specific entities or personas.
- **Non-Functional Requirements:** ≤8 requirements covering performance, security, accessibility, and data privacy. One sentence each.

#### 6. Success Metrics

- Key Performance Indicators (KPIs) to measure the success of the epic.

#### 7. Out of Scope

- Clearly list what is _not_ included in this epic to avoid scope creep.

#### 8. Business Value

- Estimate the business value (e.g., High, Medium, Low) with a brief justification.

## Context Template

- **Epic Idea:** [A high-level description of the epic from the user]
- **Target Users:** [Optional: Any initial thoughts on who this is for]

---

## Reviewing Existing Epics

When asked to review or audit one or more epics, apply the checklist below. Return structured findings only — never rewrite the epic in the same response. When reviewing a portfolio of epics, run them in parallel (one agent invocation per epic).

### 1. Epic Type Classification

Determine the type before applying any other check:

| Type | Definition | Required §3 | Personas |
|---|---|---|---|
| **Platform** | Infrastructure layer; no direct end-user interaction | Domain Integration Contract | Developer / Operator only |
| **Engine** | Solver or computation layer consumed by domain epics | Domain Integration Contract | Developer only |
| **Domain** | User-facing product layer (e.g. school, nurse) | Full user journeys | All direct user roles |

- Platform/engine epics with user journeys: flag as **Critical** — remove and replace with Domain Integration Contract.
- Domain epics without journeys: flag as **Critical** — journeys are required.
- Personas that belong to a domain epic appearing in a platform/engine epic: flag as **High** — remove them.

### 2. Domain Integration Contract (platform / engine epics)

A complete Domain Integration Contract must cover:
- What consuming epics **inherit** without code changes (constraint system, async pipeline, error envelope, etc.)
- The **output contract** — what the consuming epic receives back (result shape, terminal states, error shape)
- The full **job state machine** — all valid states and terminal transitions
- The **developer extensibility contract** — exactly what a developer must add to extend the system

Flag missing items as **High**.

### 3. Journeys (domain epics)

Check each journey for:
- **Completeness per persona** — every persona in §2 must have at least one journey. Thin journeys (≤3 steps) for non-trivial personas are **High** severity.
- **Infeasibility / error recovery** — if the domain involves a solver or async process, is the failure/recovery path a named journey step or sub-step?
- **All lifecycle states** — pre-publish, in-progress, post-publish, and re-publish states must appear.
- **Mobile context** — if any persona is likely to be mobile-first (teachers, parents, shift workers), flag absence as **Medium**.
- **First-time vs returning user** — a brand-new organisation setup flow is distinct from subsequent cycles; if both exist and only one is covered, flag as **Medium**.

### 4. Requirements

Flag each issue at the stated severity:

| Check | Severity |
|---|---|
| Functional requirements > 15 | **Critical** — propose consolidated groupings |
| NFR requirements > 8 | **High** |
| Any requirement names a specific technology (framework, library, queue) | **Medium** — rewrite to describe behaviour |
| Any requirement duplicates content from a feature PRD verbatim | **Medium** — remove or move to Domain Integration Contract |
| Non-sequential IDs with no explanatory note | **Medium** — add a callout explaining removed IDs; do not renumber |
| A domain concept appears in a platform/engine requirement | **High** — violates layer separation |

When proposing consolidation: show the grouped requirements as a table with proposed IDs, one-sentence text, and the list of original IDs absorbed.

### 5. Success Metrics

Flag each issue:
- A metric that restates a requirement verbatim: **Medium** — replace with an observable outcome.
- A metric with no test condition (who measures, when, how): **Medium** — add measurement context.
- A metric with no denominator or load condition (e.g. "≤20ms" with no concurrency): **Low** — tighten.
- A persona in §2 with zero corresponding success metrics: **High**.
- A metric that targets full compliance with a standard (e.g. "100% WCAG AAA") where blanket conformance is known to be unachievable: **Medium** — propose scoped alternative.

### 6. Out of Scope

- Any ghost feature: a capability mentioned in a persona description or journey that has no requirement and no out-of-scope entry → **High** (add to Out of Scope or add a requirement).
- A deferred epic referencing active-epic decisions that can't be deferred: flag these as **"Act Now"** items separately from the standard review — these are architectural decisions (e.g. API field naming, namespace conventions) that become breaking changes if deferred past the active epic's stabilisation.

### 7. Internal Consistency

- Business Value references a Phase 2 feature as a Phase 1 outcome: **Medium** — update to reflect actual phase.
- Persona list and journey list disagree (persona with no journey, or journey referencing an unnamed persona): **High**.
- A requirement references an entity, field, or constraint type by name that contradicts the domain-abstraction principle: **Medium** — generalise.

### 8. Portfolio Review Pattern

When reviewing multiple epics at once:
- Run one agent invocation per epic in **parallel**.
- After all reviews return, present findings grouped by epic, each finding labelled with severity: **Critical / High / Medium / Low / Act Now**.
- Conclude with a prioritised list of items to apply first (all Critical + Act Now items).
