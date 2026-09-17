"""Where the scripts live, which repo they act on, and the readers they share.

Those are two different directories, and conflating them is the whole reason
this module exists. The release scripts ship from `.llmctl`, but nothing about
them is specific to it: any repo laid out the same way can be released by them.
A private sibling holds its own `packages/`, `LICENSE`, `LICENSES/`,
`dependency-licenses.yml` and `*.marketplace.*` sources, and borrows the code
and nothing else.

  TOOLING    this checkout of `.llmctl`. Holds `scripts/` and the repo-local
             hook. Derived from __file__, never passed.
  workspace  the repo being acted on. Always `--repo`, never guessed.

Neither flag has a default, and that is deliberate. A marketplace path that is
derived or read from the environment is how a private bundle ends up published
in a public marketplace -- a failure with no error and no obvious symptom.
Requiring both makes it unrepresentable; each repo's apm.yml supplies them.

Everything below the flags is the reading every entry script needs: the
package list, the pins in a manifest, the commits a lockfile resolved them to,
and a git helper with one error convention. One copy, so the gates, the packer
and the release cannot disagree about what a package declares.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import typer
from ruamel.yaml import YAML

TOOLING = Path(__file__).resolve().parent.parent

# Typer options shared by every entry point, declared once so the help text and
# the "never defaulted" rule stay identical across scripts.
REPO_OPTION = typer.Option(
    ..., "--repo", metavar="PATH", show_default=False,
    help="Workspace to act on: its packages/, LICENSE, LICENSES/, "
         "dependency-licenses.yml, *.marketplace.* sources and git history.")
MARKETPLACE_OPTION = typer.Option(
    ..., "--marketplace", metavar="PATH", show_default=False,
    help="Marketplace repo to publish into.")


def script(*parts: str) -> Path:
    """A path inside the tooling checkout, for spawning a sibling script."""
    return TOOLING.joinpath(*parts)


# --- YAML ------------------------------------------------------------------


def yaml_rt() -> YAML:
    """A round-trip loader/dumper that keeps comments, order and quoting.

    Every apm.yml in this repo is mostly comment -- the reasoning behind each
    pin lives there -- so a rewrite that drops them would be a regression even
    when the data is right. The indent settings match how the files are written
    (two-space mappings, sequences indented under their key), so a load/dump
    round trip is a no-op on an untouched file.
    """
    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    yaml.width = 4096
    yaml.indent(mapping=2, sequence=4, offset=2)
    return yaml


def read_yaml(path: Path):
    with open(path, encoding="utf-8") as handle:
        return yaml_rt().load(handle)


def write_yaml(path: Path, data, header: str = "") -> None:
    """Dump `data` to `path`, optionally under a leading comment block."""
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        if header:
            handle.write(header.rstrip("\n") + "\n")
        yaml_rt().dump(data, handle)


# --- Git -------------------------------------------------------------------


def git(args: list[str], cwd: Path | str, check: bool = True,
        capture: bool = True) -> str:
    """Run git in `cwd`; on failure print the command and exit 1.

    `cwd` is required, never defaulted: every caller acts on a repo it was told
    about, and a default that resolved to the tooling checkout would commit and
    tag in the wrong repository.
    """
    result = subprocess.run(["git"] + list(args), cwd=str(cwd),
                            capture_output=capture, text=True)
    if check and result.returncode != 0:
        sys.stderr.write("git %s failed in %s\n%s\n"
                         % (" ".join(args), cwd, (result.stderr or "").strip()))
        raise SystemExit(1)
    return (result.stdout or "").strip()


def tag(repo: Path | str, name: str, message: str, at: str | None = None) -> None:
    """Create an annotated tag. Annotated, not lightweight: `--follow-tags`
    carries annotated tags only, so a lightweight one would never reach the
    remote on the push that follows."""
    git(["tag", "-a", name, "-m", message] + ([at] if at else []), repo)


def remote_slug(repo: Path | str, remote: str = "origin") -> tuple[str, str]:
    """(owner, repo) of a GitHub remote, from either URL form."""
    url = git(["remote", "get-url", remote], repo)
    m = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$", url)
    if not m:
        sys.stderr.write("cannot read owner/repo from remote %r (%s)\n" % (remote, url))
        raise SystemExit(1)
    return m.group(1), m.group(2)


def dirty(repo: Path | str) -> list[str]:
    """Everything `git add -A` would stage here, tracked or not."""
    return [line for line in git(["status", "--porcelain"], repo).split("\n")
            if line.strip()]


# --- Packages --------------------------------------------------------------


@dataclass(frozen=True)
class Package:
    directory: str      # packages/<directory>
    path: Path          # absolute
    name: str           # apm.yml `name:`
    manifest: dict      # the parsed apm.yml (round-trip map)


def packages(ws: Path | str) -> list[Package]:
    """Every packages/<dir>/ holding an apm.yml, in directory order."""
    root = Path(ws) / "packages"
    if not root.is_dir():
        sys.stderr.write("no packages/ in %s\n" % ws)
        raise SystemExit(1)
    found = []
    for entry in sorted(root.iterdir()):
        manifest = entry / "apm.yml"
        if not manifest.is_file():
            continue
        data = read_yaml(manifest)
        name = data.get("name") if data else None
        if not name:
            sys.stderr.write("%s: missing name\n" % manifest)
            raise SystemExit(1)
        found.append(Package(entry.name, entry.resolve(), str(name), data))
    return found


SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def parse_pin(spec: str) -> tuple[tuple[str, str], str]:
    """`[host/]owner/repo[/subpath]#ref` -> ((owner/repo lowercased, subpath), ref).

    The key mirrors how APM identifies a dependency in the lockfile (`repo_url`
    plus `virtual_path`), so the two can be compared directly. Case is folded
    because APM lowercases `repo_url` and GitHub treats names case-insensitively.
    """
    location, _, ref = spec.partition("#")
    segments = [s for s in location.strip().split("/") if s]
    if segments and "." in segments[0]:
        segments = segments[1:]          # a leading host such as github.com
    if len(segments) < 2:
        raise ValueError("not an owner/repo dependency: %r" % spec)
    repo = "/".join(segments[:2]).lower()
    subpath = "/".join(segments[2:])
    return (repo, subpath), ref.strip()


def pins_of(manifest: dict) -> dict[tuple[str, str], str]:
    """The git dependencies a package manifest declares, keyed like the lockfile."""
    deps = (manifest.get("dependencies") or {}).get("apm") or []
    pins = {}
    for dep in deps:
        if not isinstance(dep, str):
            # Object-form and registry dependencies are not used here; refusing
            # them is safer than half-understanding them.
            raise ValueError("unsupported dependency form: %r" % (dep,))
        key, ref = parse_pin(dep)
        pins[key] = ref
    return pins


def locked_of(lock: dict) -> dict[tuple[str, str], str]:
    """Every git dependency a lockfile resolved, keyed like `pins_of`."""
    locked = {}
    for dep in (lock or {}).get("dependencies") or []:
        if dep.get("source") == "local" or dep.get("local_path"):
            continue
        if not dep.get("repo_url"):
            continue
        key = (str(dep["repo_url"]).lower(), str(dep.get("virtual_path") or ""))
        locked[key] = str(dep.get("resolved_commit") or "")
    return locked


def read_lock(path: Path):
    """A lockfile as plain data, or None when absent."""
    if not Path(path).is_file():
        return None
    with open(path, encoding="utf-8") as handle:
        return YAML(typ="safe").load(handle)


def env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")
