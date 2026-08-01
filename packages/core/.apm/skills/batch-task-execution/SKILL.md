---
name: "batch-task-execution"
description: "Guidelines for planning and executing batches of tasks from todo lists, backlogs, or multi-item requests. ALWAYS invoke when asked to work through a list of tasks, start multiple sub-agents in parallel, or tackle several items at once. Do not fan out sub-agents or start a multi-item batch without this skill — it covers task confirmation, parallelisation, and overlap detection. Keywords: batch, todo list, backlog, parallel, sub-agents, multi-item, overlap."
license: ""
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

- Update the TODO / tracking file to reflect completed items immediately
- Report what was done, what was skipped, and any follow-ups required
- Do not create separate summary markdown files unless explicitly requested