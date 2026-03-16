---
name: "troubleshooting"
description: "Behavioral rules for diagnostic and troubleshooting workflows. Use when diagnosing failures, tool quirks, command hangs, and root-cause analysis before editing configuration. Includes Docker container debugging patterns: terminal state, script execution, entrypoint overrides, and Alpine tool differences."
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

## Docker Container Debugging

### Avoid Getting Stuck Inside a Container
A non-background `mcp_run_in_terminal` call that runs `docker run -it` leaves the shell inside the container for all subsequent calls. Commands like `ls`, `docker`, and `cd` then run inside the container where the host filesystem and Docker daemon are unavailable.

- **Never use `-it` in non-background terminal calls** unless you immediately `exit`.
- For interactive exploration, use `isBackground: true` and check output with `mcp_get_terminal_output`.
- For one-shot execution (most cases), omit `-it` entirely and capture stdout/stderr.
- If stuck inside a container: run `exit` in the terminal to return to the host shell.
- Detection: if `docker: not found` or host paths like `/Users/...` are not found, the terminal is inside the container.

### Write Complex Logic to a Script File
Never pass multi-line logic via `-c "..."` arguments — complex quoting causes `dquote>` terminal state and command corruption.

✅ Write to a file, mount it, execute it:
```bash
cat > /tmp/run_tests.sh << 'EOF'
#!/bin/sh
# ... commands ...
EOF
docker run --rm --entrypoint sh \
  -v /path/to/workspace:/work -w /work \
  image:tag /work/run_tests.sh
```

### Entrypoint Overrides
Images with a custom entrypoint (e.g. `ENTRYPOINT ["openssl"]`) treat any argument as a subcommand, not a shell command.
```bash
# Non-interactive script execution:
docker run --rm --entrypoint sh image:tag /mounted/script.sh
```

### Alpine / Busybox Tool Differences
Alpine uses busybox with reduced tool support. Known differences:

| Tool        | Standard behavior            | Busybox/Alpine behavior      | Use instead           |
| ----------- | ---------------------------- | ---------------------------- | --------------------- |
| `fold -w64` | Wraps long lines at 64 chars | Inconsistent with streams    | Use `awk`             |
| `sed -i ''` | macOS BSD syntax             | Not supported                | Use `sed -i` (no arg) |
