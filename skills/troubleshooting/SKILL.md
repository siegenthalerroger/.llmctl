---
name: "troubleshooting"
description: "Behavioral rules for diagnostic and troubleshooting workflows. Use when diagnosing failures, tool quirks, command hangs, and root-cause analysis before editing configuration."
license: ""
---

# Troubleshooting Workflow

## Execute, Don’t Suggest
- Run **diagnostic** commands directly when the user asks to diagnose or fix an issue.
- Combine independent checks into a single invocation when practical.

## Search Before Iterating
- For tool/CLI quirks (hangs, unexpected prompts, silent failures), do one web search for known issues before speculative retries.
- Especially for open-source tools, check GitHub issues and forums for similar reports.
- Avoid trial-and-error loops when external known issues are likely.

## Browser Debugging (Web Apps)
When diagnosing frontend or OIDC/auth issues, use the built-in browser MCP tools instead of only reading code or guessing:
- `mcp_open_browser_page` — open the app in a live browser
- `mcp_navigate_page` — navigate to a specific URL to trigger guards/redirects
- `mcp_read_page` — snapshot the DOM/URL after navigation (replaces guessing "what does the page show?")
- `mcp_run_playwright_code` — execute arbitrary JS in the page context, e.g. inspect `sessionStorage`, `localStorage`, or make fetch requests to check CORS
- Use this to validate assumptions BEFORE iterating on code; one browser session is faster than multiple restart cycles.
