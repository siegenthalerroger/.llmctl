#!/usr/bin/env python3
"""Where the scripts live, and which repo they are acting on.

Those are two different directories, and conflating them is the whole reason
this module exists. The release scripts ship from `.llmctl`, but nothing about
them is specific to it: any repo laid out the same way can be released by them.
A private sibling holds its own `packages/`, `LICENSE`, `LICENSES/` and
`dependency-licenses.yml`, and borrows the code and nothing else.

  TOOLING    this checkout of `.llmctl`. Holds `scripts/` and the
             meta-upstream-sync skill. Derived from __file__, never passed.
  workspace  the repo being acted on. Always `--repo`, never guessed.

Neither flag has a default, and that is deliberate. A marketplace path that is
derived or read from the environment is how a private bundle ends up published
in a public marketplace -- a failure with no error and no obvious symptom.
Requiring both makes it unrepresentable; each repo's apm.yml supplies them.
"""
import os

TOOLING = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def add_arguments(parser, marketplace=True):
    """Declare the root flags, identically across every entry point."""
    parser.add_argument(
        "--repo", required=True, metavar="PATH",
        help="workspace to act on: its packages/, LICENSE, LICENSES/, "
             "dependency-licenses.yml and git history")
    if marketplace:
        parser.add_argument(
            "--marketplace", required=True, metavar="PATH",
            help="marketplace repo to publish into")


def resolve(args):
    """(workspace, marketplace) absolute; marketplace is None where unused."""
    marketplace = getattr(args, "marketplace", None)
    return (os.path.abspath(args.repo),
            os.path.abspath(marketplace) if marketplace else None)


def script(*parts):
    """A path inside the tooling checkout, for spawning a sibling script."""
    return os.path.join(TOOLING, *parts)
