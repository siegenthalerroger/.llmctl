#!/usr/bin/env python3
"""The gate runner shared by check.py and release-check.py.

Both entry points are the same shape -- named checks, run cheapest first, each
reporting pass or FAIL with a one-line detail, none of them raising -- and they
differ only in which checks they hold. That shape lives here so the two scripts
stay lists of gates rather than two copies of a runner that can drift apart.

A gate is a callable returning `(ok, detail)`. `detail` is one line: on a pass
it is context worth seeing (a count, a "skipped because"), on a failure it is
the reason, already truncated. Gates never raise and never exit -- the runner
owns the exit code, so one failure does not hide the gates behind it.
"""
import subprocess


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

    def report(self):
        """Print the tally; return the exit code the caller should exit with."""
        print("")
        if self.failures:
            print("%d gate(s) failed: %s" % (len(self.failures),
                                             ", ".join(k for k, _ in self.failures)))
            return 1
        print("all gates pass")
        return 0


def add_arguments(parser):
    parser.add_argument("--skip", action="append", default=[], metavar="NAME",
                        help="gate key to skip (repeatable)")


def sh(args, cwd):
    """Run a gate's subprocess. `cwd` is required, never defaulted.

    errors="replace": these tools emit box-drawing and arrows, which the Windows
    console codepage cannot decode. A gate must not die on output it only prints.
    """
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
