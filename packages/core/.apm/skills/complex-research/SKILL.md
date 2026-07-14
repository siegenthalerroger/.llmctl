---
name: "complex-research"
description: "Guidelines for delegating complex research tasks that need multi-source investigation, synthesis, and comprehensive analysis. ALWAYS invoke when research needs extensive web searches, documentation queries, repository exploration, or cross-referencing multiple sources — delegate to a researcher agent rather than researching inline. Do not run a large multi-source investigation in the main thread without this skill. Keywords: research, multi-source, synthesis, delegate, investigation, cross-reference."
license: ""
---

# Complex Research Delegation

Guidelines for effectively delegating complex research tasks to specialized research agents and handling their outputs.

## Delegation Threshold

Delegate to a research agent when the task requires:

- **Multi-source investigation**: Gathering information from 3+ distinct sources (web, docs, repos)
- **Synthesis and analysis**: Comparing alternatives, evaluating trade-offs, or summarizing findings
- **Comprehensive coverage**: Exploring a topic thoroughly rather than answering a specific factual question
- **Documentation generation**: Creating research reports, comparison matrices, or decision documents
- **Sequential discovery**: Where initial findings guide subsequent research directions

### Do NOT delegate for:

- Simple factual lookups answerable with one tool call
- Searches within the current workspace only
- Questions with clear, direct answers in immediate context
- Tasks where you already have sufficient information

## Subagent Result Authority

**Critical principle**: Treat research subagent results as authoritative and complete.

- **Do NOT re-fetch** URLs, repositories, or documentation sources a subagent already examined
- **Do NOT re-query** the same APIs, search engines, or data sources
- Redundant fetches waste tokens and time without adding information
- If subagent results seem insufficient, the problem is usually prompt quality, not missing data

## Pre-Fetch Checks

Before any `fetch_webpage`, `github_repo`, `query-docs`, or similar research call:

1. **Check if a subagent already retrieved that information**
2. Only perform additional fetches when:
   - The subagent's results are **demonstrably insufficient** for the task, AND
   - The new fetch targets **sources the subagent did NOT cover**

## Effective Research Subagent Prompts

Make research subagent prompts comprehensive and self-contained:

### Include in every research delegation:

1. **Clear objective**: What question needs answering or what decision needs informing
2. **Scope boundaries**: What to include/exclude, depth required
3. **Expected sources**: Specific URLs, repos, documentation sites to check
4. **Output format**: How findings should be structured (report, comparison table, bullet points)
5. **Success criteria**: What makes the research "complete"

### Example structure:

```
Research [TOPIC] to inform [DECISION/IMPLEMENTATION].

Sources to investigate:
- Official documentation at [URL]
- GitHub repositories: [REPO1], [REPO2]
- Community discussions/blogs relevant to [ASPECT]

Deliverables:
1. Summary of [ASPECT1]
2. Comparison table of [OPTIONS]
3. Recommended approach with rationale

Focus on production-readiness and practical implementation details.
```

## Quality Checklist

Good research delegation includes:

- ✅ Specific sources or search terms to investigate
- ✅ Clear deliverable format (report, comparison, recommendations)
- ✅ Context about why research is needed (decision, implementation, evaluation)
- ✅ Boundaries on scope (depth, breadth, time period, filters)

Poor research delegation:

- ❌ Vague requests ("research X")
- ❌ No guidance on sources or scope
- ❌ Unclear success criteria
- ❌ Missing context about how findings will be used

## General Principle

**Research is read-once**. Delegate thoroughly with comprehensive prompts, consume the results, and move forward. Re-reading the same source never adds value—if you need more information, it means the initial prompt was underspecified.

---

## Integration Pattern

When conducting complex research:

1. **Plan**: Identify what needs to be researched and from which sources
2. **Delegate**: Write a comprehensive research prompt following guidelines above
3. **Trust**: Treat subagent output as authoritative and complete
4. **Apply**: Use findings to inform decisions, implementations, or documentation
5. **Never repeat**: Do not re-query sources the subagent already covered
