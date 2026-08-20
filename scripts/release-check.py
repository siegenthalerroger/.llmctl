#!/usr/bin/env python3
"""Run every release gate. Writes nothing, so it is safe on a PR or before a push.

This is the single entry point for "is the repo releasable?", and it is a plain
script on purpose: the GitHub workflows call exactly this, so a green CI run and
a green local run mean the same thing. Nothing is inlined into a workflow step.

Gates, cheapest first so an obvious failure reports fast:

  frontmatter     .apm/hooks/validate-customization-frontmatter.py --all -- the
                  same rules the edit-time hook applies, over the whole tree.
                  The hook only sees files edited in a Claude session
  licences        scripts/check-licenses.py -- every file's licence can carry the
                  upstream terms its provenance records
  parser parity   check-licenses.py and check-updates.ps1 must find the same
                  tracked entries. They parse the same frontmatter in different
                  languages, and the object form fails *silently* when they
                  disagree -- a file just stops being tracked, with no error
  notices         gen-notices.py --check -- THIRD-PARTY-NOTICES.md is current
  versions        apm pack --check-versions -- per-package versions agree with
                  the manifest (exit 3 means they do not)
  manifest drift  apm pack --check-clean -- the committed marketplace.json files
                  match what would be generated (exit 4 means they do not)
  plugin validity claude plugin validate on each bundle, when the CLI is present
  lockfile        apm audit --ci

Usage:
  python scripts/release-check.py --repo PATH --marketplace PATH [--skip NAME]

  --repo         the workspace to check
  --marketplace  the marketplace it publishes into

Exit codes: 0 all gates pass, 1 one or more failed.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import workspace  # noqa: E402

# The repo being checked, set once from --repo. Module-level rather than a
# `cwd=` default, which would bind before the flags are parsed and point every
# gate at the tooling checkout instead of the workspace under test.
WORKSPACE = None


class Gates(object):
    def __init__(self, skip):
        self.skip = set(skip)
        self.failures = []

    def run(self, key, title, fn):
        if key in self.skip:
            print("- %-16s skipped" % key)
            return
        print("- %-16s %s" % (key, title))
        ok, detail = fn()
        if ok:
            print("  pass%s" % ("  (%s)" % detail if detail else ""))
        else:
            print("  FAIL  %s" % detail)
            self.failures.append((key, detail))


def sh(args, cwd=None):
    # errors="replace": these tools emit box-drawing and arrows, which the
    # Windows console codepage cannot decode. A gate must not die on output it
    # only ever prints.
    return subprocess.run(args, cwd=cwd or WORKSPACE, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


def gate_frontmatter():
    """The edit-time hook's rules, applied to every file rather than one."""
    got = sh([sys.executable,
              workspace.script(".apm", "hooks",
                               "validate-customization-frontmatter.py"),
              "--repo", WORKSPACE, "--all"])
    lines = [l.strip() for l in (got.stdout + got.stderr).split("\n") if l.strip()]
    if got.returncode == 0:
        return True, lines[-1].replace("[customization-frontmatter] ", "") if lines else ""
    errors = [l for l in lines if "error:" in l]
    return False, "; ".join(errors[:3])[:200]


def gate_licenses():
    got = sh([sys.executable, workspace.script("scripts", "check-licenses.py"),
              "--repo", WORKSPACE])
    tail = (got.stderr or got.stdout).strip().split("\n")[-1] if got.returncode else \
        (got.stdout.strip().split("\n")[0] if got.stdout.strip() else "")
    return got.returncode == 0, tail


def gate_parity():
    """The two provenance parsers must agree on what is tracked."""
    py = sh([sys.executable, workspace.script("scripts", "check-licenses.py"),
             "--repo", WORKSPACE, "--json"])
    if py.returncode not in (0, 1) or not py.stdout.strip():
        return False, "check-licenses.py --json produced no output"
    mine = {(e["file"], e["url"]) for e in json.loads(py.stdout)["entries"]
            if e["kind"] == "adaptedFrom"}

    # The PowerShell audit only scans *.agent.md / SKILL.md / *.instructions.md /
    # *.prompt.md, so reference files it never sees are not a disagreement.
    scanned = {m for m in mine if os.path.basename(m[0]) in ("SKILL.md",) or
               m[0].endswith((".agent.md", ".instructions.md", ".prompt.md"))}

    # A workspace of wholly original content tracks nothing, and check-updates.ps1
    # treats an empty scan as an error. Two parsers that both found nothing agree.
    if not scanned:
        return True, "no tracked provenance entries; parity is vacuous"

    pwsh = shutil.which("pwsh") or shutil.which("powershell")
    if not pwsh:
        return True, "PowerShell absent; parity not checked"
    script = workspace.script(".apm", "skills", "meta-upstream-sync",
                              "scripts", "check-updates.ps1")
    ps = sh([pwsh, "-NoProfile", "-File", script, "-RepoRoot", WORKSPACE,
             "-OutputJson"])
    if ps.returncode != 0 or not ps.stdout.strip():
        return False, "check-updates.ps1 failed: " + ps.stderr.strip()[:160]
    try:
        theirs = {(r["id"], r["sourceUrl"]) for r in json.loads(ps.stdout)["results"]}
    except ValueError:
        return False, "check-updates.ps1 emitted unparseable JSON"

    if scanned != theirs:
        only_py = sorted(scanned - theirs)[:3]
        only_ps = sorted(theirs - scanned)[:3]
        return False, ("parsers disagree: %d vs %d entries; py-only=%s ps-only=%s"
                       % (len(scanned), len(theirs), only_py, only_ps))
    return True, "%d tracked entries, both parsers agree" % len(theirs)


def gate_notices(marketplace):
    got = sh([sys.executable, workspace.script("scripts", "gen-notices.py"),
              "--repo", WORKSPACE, "--marketplace", marketplace, "--check"])
    return got.returncode == 0, (got.stderr or got.stdout).strip().split("\n")[-1]


def gate_apm(marketplace, flag, bad_code, label):
    got = sh(["apm", "pack", "--dry-run", "--offline", flag], cwd=marketplace)
    if got.returncode == 0:
        return True, ""
    if got.returncode == bad_code:
        lines = [l.strip() for l in got.stdout.split("\n") if l.strip()]
        return False, "%s (exit %d): %s" % (label, bad_code,
                                            "; ".join(lines[-3:])[:200])
    return False, "apm pack exited %d: %s" % (got.returncode, got.stderr.strip()[:160])


def gate_plugins(marketplace):
    if not shutil.which("claude"):
        return True, "claude CLI absent; bundles not validated"
    plugins = os.path.join(marketplace, "plugins")
    if not os.path.isdir(plugins):
        return False, "no plugins/ directory"
    bad = []
    for entry in sorted(os.listdir(plugins)):
        path = os.path.join(plugins, entry)
        if not os.path.isdir(path):
            continue
        got = sh(["claude", "plugin", "validate", "."], cwd=path)
        if got.returncode != 0:
            bad.append("%s: %s" % (entry, (got.stderr or got.stdout).strip()[:90]))
    return not bad, "; ".join(bad)


def gate_audit():
    """apm audit --ci, minus one failure mode that is environmental, not a defect.

    The audit replays the install and diffs it against the working tree. When the
    local APM is newer than the one that wrote apm.lock.yaml, the replay deploys
    to targets the lockfile predates (0.26 added `.agents/skills/` and `.github/`
    over 0.25's `.claude/` only), and every one of those reports as
    `unintegrated`. That is APM version skew -- it says nothing about the change
    under review, and it would fail every contributor whose APM differs from
    whoever last refreshed the lockfile.

    So `unintegrated`-only drift is reported as a note. Modified or missing files
    still fail: those mean the deployed copy and its source disagree, which is a
    real defect. CI runs `apm install --frozen` first and reproduces the lockfile
    exactly, so it does not hit this path at all.
    """
    got = sh(["apm", "audit", "--ci"])
    if got.returncode == 0:
        return True, "no drift"

    out = got.stdout + got.stderr
    details = re.findall(r"^\s*-\s+(\w+):\s*(.+)$", out, re.M)
    failed_checks = re.findall(r"\[x\]\s+(\d+) of \d+ check\(s\) failed", out)

    only_unintegrated = details and all(kind == "unintegrated" for kind, _ in details)
    if only_unintegrated and failed_checks == ["1"]:
        return True, ("%d file(s) deployed by this APM but absent from the lockfile "
                      "(version skew, not a defect) - `apm install` to refresh"
                      % len(details))

    tail = [l.strip() for l in out.split("\n") if l.strip()]
    return False, "; ".join(tail[-2:])[:200]


def main():
    global WORKSPACE
    parser = argparse.ArgumentParser(description=__doc__)
    workspace.add_arguments(parser)
    parser.add_argument("--skip", action="append", default=[],
                        help="gate key to skip (repeatable)")
    args = parser.parse_args()
    WORKSPACE, marketplace = workspace.resolve(args)

    print("release-check: %s\n           -> %s\n" % (WORKSPACE, marketplace))
    gates = Gates(args.skip)
    gates.run("frontmatter", "customization frontmatter conventions",
              gate_frontmatter)
    gates.run("licences", "provenance obligations vs declared licences", gate_licenses)
    gates.run("parity", "both provenance parsers agree", gate_parity)
    # An empty directory is not a marketplace. `actions/checkout` git-inits the
    # target path before it discovers it cannot read the repository, so a failed
    # optional checkout leaves one behind -- and every marketplace gate then
    # fails against nothing instead of being skipped.
    if os.path.isfile(os.path.join(marketplace, "apm.yml")):
        gates.run("notices", "THIRD-PARTY-NOTICES.md is current",
                  lambda: gate_notices(marketplace))
        gates.run("versions", "per-package version alignment",
                  lambda: gate_apm(marketplace, "--check-versions", 3, "version alignment"))
        gates.run("drift", "marketplace manifests match",
                  lambda: gate_apm(marketplace, "--check-clean", 4, "manifest drift"))
        gates.run("plugins", "each bundle validates",
                  lambda: gate_plugins(marketplace))
    else:
        print("- marketplace      no apm.yml at %s; marketplace gates skipped"
              % marketplace)
    gates.run("lockfile", "apm audit --ci", gate_audit)

    print("")
    if gates.failures:
        print("%d gate(s) failed: %s" % (len(gates.failures),
                                         ", ".join(k for k, _ in gates.failures)))
        return 1
    print("all gates pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
