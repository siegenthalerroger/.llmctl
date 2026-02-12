---
name: "Research Delegation Instructions"
description: "Rules for efficient research delegation and avoiding redundant fetches"
applyTo: "**"
source: ""
license: ""
---

# Research Delegation

## Subagent Result Authority

- Treat subagent research results as authoritative output.
- Do NOT re-fetch URLs, re-search repositories, or re-query documentation sources a subagent already examined.
- Redundant fetches waste context window tokens and time without adding information.

## Pre-Fetch Checks

- Before any `fetch_webpage`, `github_repo`, `query-docs`, or similar research call, verify a subagent has not already retrieved that information.
- Only perform additional fetches when:
  - The subagent's results are demonstrably insufficient for the task, AND
  - The new fetch targets sources the subagent did NOT cover.

## Subagent Dispatch Quality

- Make research subagent prompts comprehensive: specify all target URLs, repos, search queries, and expected output format upfront.
- Include enough context in the dispatch prompt that the subagent can gather everything in a single pass.
- Prefer one well-scoped subagent call over multiple narrow ones when the research targets are related.

## General Principle

Research is read-once. Delegate thoroughly, consume the results, and move forward. Re-reading the same source is never productive.