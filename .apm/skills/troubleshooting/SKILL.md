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

## Prefer Structured Tools; Handle Large Outputs
- When a capability is exposed by **both an MCP server and a native CLI** (Kubernetes, GitHub, etc.), prefer the MCP for structured reads; fall back to the native CLI for operations the MCP does not cover (e.g. `helm`) and when the MCP result would be very large.
- When a tool/MCP result is too large and gets **persisted to a file**, slice it with `jq`/`grep`/offset reads — do NOT re-run the call. For search APIs (Jira JQL, Confluence CQL), narrow the query and request only the fields you need rather than re-fetching everything.
- **Never echo secret values** while diagnosing. Read a credential via the tool that already holds it (e.g. a pod's own env vars) and compare with a boolean (`MATCH`/`MISMATCH`) — do not print the value.

## Verify Capabilities and Prerequisites — Don't Infer
- **Names lie about access.** Never assume an access level from a context/account/role name (a context called `read-only` may still have namespace-scoped write). Probe the real capability before acting or before ruling out an operation: `kubectl auth can-i <verb> <resource>`, a `--dry-run`, or a harmless write.
- **When a pre-flight check is impossible from your vantage, don't block on it.** If credentials/scope prevent verifying a prerequisite (an image tag in a registry you can't reach, node capacity you can't list), identify the fail-fast signal that surfaces it during execution (`ImagePullBackOff`/`manifest unknown`, `Pending`/`Unschedulable`) and monitor that instead. State the residual risk rather than stalling.

## Diagnose the Root, Not the Wrapper
- When an orchestrator reports a child failure (helm "hook failed / Job not ready", a controller event), the real cause is in the **child's own logs** — read those, find the root `Caused by:`, and act on that, not the wrapper summary.
- For a crashed/restarted container, use `logs --previous` (the live log is the next attempt, not the one that failed).
- **Inspect the shipped artifact for ground truth.** To learn what a new image actually expects (its config, DB changelog, an enum's valid values), run a throwaway pod with that image, override the entrypoint (`--command -- sleep 1200`), then `exec` in to `find`/`cat`/`javap`/`unzip -p`. Delete it after. Beats guessing from docs or the previous version.
- A failed orchestrated step leaves **state that blocks retry** (a release stuck `failed`, leftover hook Jobs, a partial lock). Clean it up before re-running.

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
