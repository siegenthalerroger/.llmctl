---
name: "troubleshooting"
description: "Behavioral rules for diagnosis and root-cause analysis: failures, tool quirks, command hangs, version-dependent behavior, and Docker container debugging (terminal state, script execution, entrypoint overrides, busybox differences). ALWAYS invoke when a command fails, hangs, or behaves unexpectedly, before editing configuration to fix it. Do not guess at a fix or change config without first diagnosing root cause via this skill. Keywords: troubleshoot, diagnose, debug, root cause, logs, version skew, docker, container, secret, hang."
license: ""
---

# Troubleshooting Workflow

## Execute, Don't Suggest
- Run **diagnostic** commands directly when the user asks to diagnose or fix an issue.
- Combine independent checks into a single invocation when practical.

## Search Before Iterating
- For tool/CLI quirks (hangs, unexpected prompts, silent failures), do one web search for known issues — GitHub issues and forums for open-source tools — before speculative retries. Avoid trial-and-error loops when an external known issue is likely.

## Prefer Structured Tools; Handle Large Outputs
- When a capability is exposed by **both an MCP server and a native CLI** (Kubernetes, GitHub, etc.), prefer the MCP for structured reads; fall back to the native CLI for operations the MCP does not cover (e.g. `helm`) or when the MCP result would be very large.
- When a tool/MCP result is too large and gets **persisted to a file**, slice it with `jq`/`grep`/offset reads — do NOT re-run the call. For search APIs (Jira JQL, Confluence CQL), narrow the query and request only the fields you need.

## Never Echo Secrets
Read a credential via the tool that already holds it (e.g. a pod's own env vars) and compare with a boolean (`MATCH`/`MISMATCH`) — never print the value while diagnosing.

## Verify Capabilities and Prerequisites — Don't Infer
- **Names lie about access.** Never assume an access level from a context/account/role name (a context called `read-only` may still have namespace-scoped write). Probe the real capability before acting or before ruling out an operation: `kubectl auth can-i <verb> <resource>`, a `--dry-run`, or a harmless write.
- **When a pre-flight check is impossible from your vantage, don't block on it.** If credentials/scope prevent verifying a prerequisite (an image tag in a registry you can't reach, node capacity you can't list), identify the fail-fast signal that surfaces it during execution (`ImagePullBackOff`/`manifest unknown`, `Pending`/`Unschedulable`) and monitor that instead. State the residual risk rather than stalling.

## Pin Deployed Versions Before Version-Dependent Reasoning
When a diagnosis hinges on version-specific behavior (a validation rule, a schema, a changed default), establish the **actual running version of every component involved** up front — not after building a theory.
- **A local source checkout is NOT evidence of what's deployed.** A clone sits on an arbitrary branch; its contents and dependency pins rarely match the deployed build.
- Confirm from an authoritative source, using whichever is cheapest: the running system itself (deployed image tag, `helm list`, a pod's manifest/env), release documentation, the issue tracker (`fixVersions`), or ask the user.
- A version you cannot confirm is an **explicit unverified assumption** — flag every conclusion that depends on it; never present it as fact.
- For **version skew between two communicating components** (producer/consumer, client/server): pin both deployed versions, locate the release where the relevant behavior changed (e.g. `git log -S`, comparing tags), and confirm each component sits on the expected side of that boundary.

## Diagnose the Root, Not the Wrapper
- When an orchestrator reports a child failure (helm "hook failed / Job not ready", a controller event), the real cause is in the **child's own logs** — read those, find the root `Caused by:`, and act on that, not the wrapper summary.
- For a crashed/restarted container, use `logs --previous` (the live log is the next attempt, not the one that failed).
- **Inspect the shipped artifact for ground truth.** To learn what a new image actually expects (its config, DB changelog, an enum's valid values), run a throwaway pod with that image, override the entrypoint with a long sleep (`--command -- sleep 3600`), then `exec` in to `find`/`cat`/`javap`/`unzip -p`. Delete it after. Beats guessing from docs or the previous version.
- A failed orchestrated step leaves **state that blocks retry** (a release stuck `failed`, leftover hook Jobs, a partial lock). Clean it up before re-running.

## Browser Debugging (Web Apps)
When diagnosing frontend or OIDC/auth issues, use the harness's browser automation tools (browser MCP, Playwright) instead of only reading code or guessing:
- Open the app in a live browser and navigate to the URLs that trigger guards/redirects.
- Snapshot the resulting DOM and URL — replaces guessing "what does the page show?".
- Run JS in the page context to inspect `sessionStorage`/`localStorage` or issue fetch requests to check CORS.
- Validate assumptions in the browser BEFORE iterating on code; one browser session is faster than multiple restart cycles.

## Docker Container Debugging

### Avoid Getting Stuck Inside a Container
A foreground terminal call that runs `docker run -it` (or `docker exec -it`) leaves the shell inside the container for all subsequent calls — `ls`, `docker`, and host paths then resolve inside the container, where the host filesystem and Docker daemon are unavailable.
- **Never use `-it` in foreground terminal calls.** For one-shot execution (most cases), omit `-it` entirely and capture stdout/stderr.
- For interactive exploration, run the container via a background terminal call and poll its output.
- Detection: `docker: not found` or missing host paths (`/Users/...`) means the terminal is inside the container — run `exit` to return to the host shell.

### Write Complex Logic to a Script File
Never pass multi-line logic via `-c "..."` arguments — nested quoting causes `dquote>` terminal state and command corruption. Write a script into the directory you mount, then execute it:

```bash
cat > /path/to/workspace/run_tests.sh << 'EOF'
#!/bin/sh
# ... commands ...
EOF
docker run --rm --entrypoint sh \
  -v /path/to/workspace:/work -w /work \
  image:tag /work/run_tests.sh
```

### Entrypoint Overrides
Images with a custom entrypoint (e.g. `ENTRYPOINT ["openssl"]`) treat any argument as a subcommand, not a shell command. Override it to run scripts non-interactively:

```bash
docker run --rm --entrypoint sh image:tag /mounted/script.sh
```

### Host vs. Container Tool Differences
- **Busybox (Alpine) applets are reduced implementations.** When one misbehaves on piped input (e.g. `fold -w`), switch to `awk` instead of debugging the applet.
- **Don't let host syntax leak into container commands.** macOS BSD `sed -i ''` fails in GNU/busybox sed — inside Linux containers use `sed -i` with no backup argument.
