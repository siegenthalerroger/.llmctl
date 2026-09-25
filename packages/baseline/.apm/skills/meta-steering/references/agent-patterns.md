# Common Agent Patterns

Before adding a persona below, apply the [default-to-one-agent gate](./agent-guide.md#default-to-one-agent): add a specialist only when it improves capability isolation, policy isolation, prompt clarity or trace legibility.

Tool postures are for dual-deployed files ([agent-guide.md, Tools field](./agent-guide.md#tools-field)): no `tools:`, restriction via `disallowedTools:`, and the same restriction restated in the body. Copilot-only equivalents are in [agent-tools.md](./agent-tools.md#tool-selection-patterns).

| Persona | Purpose | Tool posture | Body anti-drift line |
|---|---|---|---|
| Explorer | Answer codebase questions fast | `disallowedTools: Edit, Write, NotebookEdit` | "Read-only: never create, edit or delete files." |
| Implementation planner | Produce a plan others execute | `disallowedTools: Edit, Write, NotebookEdit` | "Never implement; return the plan." |
| Code reviewer | Report findings on a diff | `disallowedTools: Edit, Write, NotebookEdit` | "Do not fix; report with file references." |
| Security auditor | Find vulnerabilities, check OWASP | Read-only denylist; web allowed | "Report findings; hand remediation to the fixer." |
| Researcher | Multi-source research report | Read-only denylist; web and MCP docs allowed | "Never edit project files." |
| Refactoring specialist | Improve structure without behaviour change | Edit allowed; deny `Bash` unless tests must run | "No behaviour changes; run the tests you are given." |
| Testing specialist | Add tests for a change | Edit and execution allowed | "Do not modify production code; report bugs instead." |
| Executor | Implement a well-specified plan | All tools | "Follow the plan; note deviations; do not re-plan." |

See this repository's agents under `packages/baseline/.apm/agents/` for worked examples of the explorer, planner, researcher and executor rows.
