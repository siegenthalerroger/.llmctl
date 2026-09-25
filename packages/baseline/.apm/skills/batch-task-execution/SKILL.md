---
name: "batch-task-execution"
description: "Guidelines for planning and executing batches of tasks from todo lists, backlogs, or multi-item requests. ALWAYS invoke when asked to work through a list of tasks, start multiple sub-agents in parallel, or tackle several items at once. Do not fan out sub-agents or start a multi-item batch without this skill — it covers task confirmation, parallelisation, and overlap detection. Keywords: batch, todo list, backlog, parallel, sub-agents, multi-item, overlap."
metadata:
  provenance:
    adaptedFrom:
      - url: "https://github.com/obra/superpowers/blob/main/skills/subagent-driven-development/SKILL.md"
        license: MIT
        fidelity: partly-derived
        took: "The dispatch-brief contract, the DONE/DONE_WITH_CONCERNS/NEEDS_CONTEXT/BLOCKED outcome protocol, the spec-compliance-before-quality review order, the fix-round cap with explicit adjudication, and the ledger-survives-compaction rule."
---

# Batch Task Execution

## Confirm Before Starting

Before executing any batch of tasks — especially ones involving sub-agents, file changes, or irreversible operations — **present the proposed task selection to the user and wait for confirmation**.

Include in the confirmation:

- Which tasks you plan to tackle (and which you are skipping, if any)
- Proposed grouping or parallelisation strategy
- Any assumptions about scope or priority

✅ Ask once, concisely. A table or short bullet list is sufficient.
❌ Do not launch agents or make changes before receiving confirmation.

This step is non-negotiable when:

- Tasks come from a pre-existing TODO list or backlog
- Any task involves installing packages, modifying config files, or touching many files
- Sub-agents will be used (their changes are hard to selectively undo)

## Parallelisation Rules

Once tasks are confirmed:

- Group tasks by **independence** — tasks must share no files, no dependencies, and no overlapping scope
- Assign one sub-agent per group; never let two agents touch the same file
- State the grouping explicitly so the user can spot overlap before agents start

## Sub-Agent Task Sizing

Choose the right worker tier and enforce sizing discipline. Tier by **how much context the task spans**, not by how large its output is. Both tiers execute any kind of work — code, configuration, IaC, documentation, specs. Read the *Executor (Focused)* and *Executor (Broad)* agent definitions for full details.

### Definition of "touch"

A file is **touched** if it must be **read for context** or **edited**. Count both.

A task that edits 2 files but must consult 4 others to produce correct output touches 6 files — even though only 2 files change.

### Executor (Focused) — ≤5 files touched, single component

- One task = one concrete outcome within a single component, module, or document
- Do not batch multiple file creations/rewrites into a single request
- Keep each request narrowly scoped enough that a failed result can be reverted or retried without collateral edits
- Prefer a short sequence of tiny tasks over a single broad "small" task as failures are isolated and retries are cheap

### Executor (Broad) — 6+ files touched or cross-component

- Use when a task requires cross-component reasoning or sustained context across many files
- Executor (Broad) may internally delegate isolated subtasks to Executor (Focused)
- Prefer Executor (Broad) over a chain of Executor (Focused) calls when subtasks share significant context that would need to be re-explained in each prompt

## Dispatch Briefs

A sub-agent starts cold. It inherits none of the session — not the user's wording, not decisions made earlier in the batch, not files already read. Construct the exact context each task needs.

Every dispatch contains:

- **One line on where the task sits in the batch** — enough orientation to make sensible local choices, no more
- **The exact values verbatim** — names, paths, versions, identifiers, command flags. State them **once**, in one place; never restate them in the surrounding prose, or the agent has two sources of truth and will pick the wrong one
- **Interfaces and decisions produced by earlier tasks** in this batch that this task must match
- **Ambiguities already resolved with the user**, as rulings — so the agent does not re-litigate them
- **Where to report** — the file path or response format the result must land in

❌ Never dispatch with "continue what we were doing" or a reference to earlier conversation.
❌ Never let the agent infer an exact value it could get wrong; if it matters, write it down.

## Handling Sub-Agent Outcomes

Require every dispatch to close with one of four statuses, and handle each differently:

| Status | Meaning | What to do |
| --- | --- | --- |
| `DONE` | Work complete | Review it (below) before starting the next task |
| `DONE_WITH_CONCERNS` | Complete, but the agent flagged doubts | Read the concerns. Correctness doubts: resolve before review. Observational: record and proceed |
| `NEEDS_CONTEXT` | Missing information it could not obtain | Supply the missing context, then re-dispatch |
| `BLOCKED` | Cannot complete | Classify the blocker — missing context, wrong worker tier, scope too large, or a defective task — and fix that cause |

❌ Never re-dispatch an unchanged prompt after a failure. A retry with no change is a guess.
❌ Never silently absorb a `BLOCKED` result into your own work; report it.

## Review Each Task Before Starting the Next

Review the diff the task produced, not the whole tree. Run two stages, in this order:

1. **Spec compliance** — does the result do what the brief asked, with nothing missing and nothing extra? Check against the brief, not against your memory of the request.
2. **Quality** — tests, existing patterns, maintainability. Dispatch the *Code Reviewer* agent for code changes.

Stage 1 first: quality feedback on work that solves the wrong problem is wasted.

After the last task, run **one review across the whole batch** — cross-task inconsistencies are invisible to per-task reviews.

### Fix rounds are capped

Cap fix rounds at **five per task**:

- Rounds 1–3: send the open findings back to the same executor
- Rounds 4–5: dispatch a fresh *Executor (Broad)* with the findings and the original brief

At the cap, rule explicitly on every finding still open:

- **Reviewer is wrong or the point is contestable** → record why the current result stands
- **Real but not blocking** → record it as deferred, with the follow-up
- **Real and load-bearing** → stop the batch and report to the user

❌ Never discard a finding without a written ruling.
❌ Never continue past the cap hoping the next round converges.

## Conversational Agents as Subagents

`mcp_runSubagent` is **single-shot** — the agent receives one prompt and returns one response. It cannot ask the user follow-up questions.

**How to detect a conversational agent:** check the agent's description for keywords like "interactive", "requires user dialogue", "asks questions", or "multi-turn". These agents lose their core value when run single-shot.

### When the agent's value is the conversation, not just the output

- Do **not** run conversational agents as subagents when design decisions require user input
- Instead, present the task to the user and recommend they invoke the agent directly (e.g. "This needs UX discovery — switch to the UX Expert agent to work through it interactively")
- If multiple conversational tasks exist, list them for the user and let them sequence the conversations

### When subagent delegation is acceptable

Conversational agents may run as subagents only when:

- All design decisions are already resolved (user explicitly confirmed direction)
- The task is purely mechanical (e.g. "write up these agreed requirements as a PRD")
- The handover prompt contains the user's own words/decisions, not your assumptions

### Handover prompt rules for conversational agents

❌ Never pre-decide design choices in the prompt ("Recommended Design Direction: X")
❌ Never instruct the agent to skip questions ("you do NOT need to ask clarifying questions")
❌ Never fill in answers the user hasn't given

✅ Provide context (what exists, what's missing, what the gap is)
✅ Include the user's stated preferences and prior decisions verbatim
✅ Flag open questions as open — let the agent surface them in its output as "decisions needed"

## Handling Stale or Ambiguous Tasks

TODO lists go stale. Before executing:

- Flag tasks that conflict with each other or with the stated intent
- Ask for clarification on tasks that are vague or that have multiple valid interpretations

## After Execution

- Update the TODO / tracking file **as each task closes**, not once at the end — a long batch will outlive the context window, and the tracking file is what survives compaction. Trust it over session memory when the two disagree
- Record deferred and overruled findings in the tracking file alongside the completed items, with the ruling
- Report what was done, what was skipped, and any follow-ups required
- Do not create separate summary markdown files unless explicitly requested