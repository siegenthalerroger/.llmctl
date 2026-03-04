---
name: "batch-task-execution"
description: "Guidelines for planning and executing batches of tasks from todo lists, backlogs, or multi-item requests. Use when asked to work through a list of tasks, start multiple sub-agents in parallel, or tackle several items at once. Covers task confirmation, parallelisation, and overlap detection."
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

Choose the right worker tier and enforce sizing discipline. See agent definitions for full details:

- [Simple-Worker](../../agents/generic-worker-simple.agent.md)
- [Complex-Worker](../../agents/generic-worker-complex.agent.md)

### Definition of "touch"

A file is **touched** if it must be **read for context** or **edited**. Count both.

A task that edits 2 files but must consult 4 others to produce correct output touches 6 files — even though only 2 files change.

### Simple-Worker (≤5 files touched)

- One task = one concrete outcome
- Do not batch multiple file creations/rewrites into a single request
- Keep each request narrowly scoped enough that a failed result can be reverted or retried without collateral edits
- Prefer a short sequence of tiny tasks over a single broad "small" task as failures are isolated and retries are cheap

### Complex-Worker (6+ files touched)

- Use when a task requires cross-component reasoning or sustained context across many files
- The Complex-Worker may internally delegate isolated subtasks to Simple-Worker
- Prefer Complex-Worker over a chain of Simple-Worker calls when the subtasks share significant context that would need to be re-explained in each prompt

## Handling Stale or Ambiguous Tasks

TODO lists go stale. Before executing:

- Flag tasks that conflict with each other or with the stated intent
- Ask for clarification on tasks that are vague or that have multiple valid interpretations

## After Execution

- Update the TODO / tracking file to reflect completed items immediately
- Report what was done, what was skipped, and any follow-ups required
- Do not create separate summary markdown files unless explicitly requested