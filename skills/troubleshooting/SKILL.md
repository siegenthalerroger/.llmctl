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
