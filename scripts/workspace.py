"""Which repo a script acts on, and the readers every script shares.

`--repo` is the workspace being acted on and is never defaulted; the tooling
checkout is derived from __file__. One copy of the package list, the pins in a
manifest and the commits a lockfile resolved them to, so the gates, the packer
and the release cannot disagree. See CONTRIBUTING.md#releasing-another-workspace.
"""
from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import typer
from ruamel.yaml import YAML

TOOLING = Path(__file__).resolve().parent.parent


class WorkspaceError(Exception):
    """Anything a caller should report and exit on, rather than trace back."""


def die(exc: Exception) -> typer.Exit:
    """Print a library error the way every CLI here reports one."""
    sys.stderr.write("%s\n" % exc)
    return typer.Exit(1)


REPO_OPTION = typer.Option(
    ..., "--repo", metavar="PATH", show_default=False,
    help="Workspace to act on: its packages/, LICENSE, LICENSES/, "
         "dependency-licenses.yml, *.marketplace.* sources and git history.")
MARKETPLACE_OPTION = typer.Option(
    ..., "--marketplace", metavar="PATH", show_default=False,
    help="Marketplace repo to publish into.")

# What `apm install` writes into a package beside the lockfile. Git-ignored,
# never exported, never committed -- one list, so the .gitignore, the worktree
# export and the update command cannot disagree about what is install output.
INSTALL_OUTPUT = (".claude", ".agents", ".codex", ".github", "apm_modules",
                  ".mcp.json", ".gitignore")


def script(*parts: str) -> Path:
    """A path inside the tooling checkout, for spawning a sibling script."""
    return TOOLING.joinpath(*parts)


# --- YAML ------------------------------------------------------------------


def yaml_rt() -> YAML:
    """A round-trip loader that keeps comments, order and quoting.

    Every apm.yml here is mostly comment -- the reasoning behind each pin lives
    there -- so a rewrite that dropped them would be a regression even when the
    data is right.
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
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        if header:
            handle.write(header.rstrip("\n") + "\n")
        yaml_rt().dump(data, handle)


# --- Git -------------------------------------------------------------------


def git(args: list[str], cwd: Path | str, check: bool = True,
        capture: bool = True) -> str:
    """Run git in `cwd`. `cwd` is required: a default would act on the tooling
    checkout, which is never the repo being released."""
    result = subprocess.run(["git"] + list(args), cwd=str(cwd),
                            capture_output=capture, text=True)
    if check and result.returncode != 0:
        raise WorkspaceError("git %s failed in %s\n%s"
                             % (" ".join(args), cwd, (result.stderr or "").strip()))
    return (result.stdout or "").strip()


def tag(repo: Path | str, name: str, message: str, at: str | None = None) -> None:
    """Create an annotated tag. `--follow-tags` carries annotated tags only, so
    a lightweight one would never reach the remote on the push that follows."""
    git(["tag", "-a", name, "-m", message] + ([at] if at else []), repo)


def remote_slug(repo: Path | str, remote: str = "origin") -> tuple[str, str]:
    """(owner, repo) of a GitHub remote, from either URL form."""
    url = git(["remote", "get-url", remote], repo)
    m = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$", url)
    if not m:
        raise WorkspaceError("cannot read owner/repo from remote %r (%s)" % (remote, url))
    return m.group(1), m.group(2)


def dirty(repo: Path | str) -> list[str]:
    """Everything `git add -A` would stage here, tracked or not."""
    return [line for line in git(["status", "--porcelain"], repo).split("\n")
            if line.strip()]


def fetch_tags(repo: Path | str, log=None) -> None:
    """Fetch tags, and say so when it fails.

    Tags are the baseline for every version plan, so a silent failure here is
    the one that measures every package from the start of history.
    """
    result = subprocess.run(["git", "fetch", "--tags", "origin"], cwd=str(repo),
                            capture_output=True, text=True)
    if result.returncode != 0 and log:
        log("[warn] git fetch --tags failed (%s). Versions are derived from the "
            "tags in this clone, so a package with none will be measured from "
            "the start of its history."
            % (result.stderr or "").strip().split("\n")[-1][:120])


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
        raise WorkspaceError("no packages/ in %s" % ws)
    found = []
    for entry in sorted(root.iterdir()):
        manifest = entry / "apm.yml"
        if not manifest.is_file():
            continue
        data = read_yaml(manifest)
        name = data.get("name") if data else None
        if not name:
            raise WorkspaceError("%s: missing name" % manifest)
        found.append(Package(entry.name, entry.resolve(), str(name), data))
    return found


def select(ws: Path | str, wanted: list[str]) -> list[Package]:
    """The packages named by directory or package name; all of them when none."""
    found = packages(ws)
    if not wanted:
        return found
    names = set(wanted)
    chosen = [p for p in found if p.directory in names or p.name in names]
    if not chosen:
        raise WorkspaceError("no package matched %s" % ", ".join(sorted(names)))
    return chosen


SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def parse_pin(spec: str) -> tuple[tuple[str, str], str]:
    """`[host/]owner/repo[/subpath]#ref` -> ((owner/repo lowercased, subpath), ref).

    The key mirrors how APM identifies a dependency in the lockfile (`repo_url`
    plus `virtual_path`), so the two compare directly. Case is folded because
    APM lowercases `repo_url`.
    """
    location, _, ref = spec.partition("#")
    segments = [s for s in location.strip().split("/") if s]
    if segments and "." in segments[0]:
        segments = segments[1:]          # a leading host such as github.com
    if len(segments) < 2:
        raise WorkspaceError("not an owner/repo dependency: %r" % spec)
    repo = "/".join(segments[:2]).lower()
    subpath = "/".join(segments[2:])
    return (repo, subpath), ref.strip()


def label(key: tuple[str, str]) -> str:
    """`owner/repo` or `owner/repo/subpath`, for a message about one pin."""
    return "%s%s" % (key[0], "/" + key[1] if key[1] else "")


def pins_of(manifest: dict) -> dict[tuple[str, str], str]:
    """The git dependencies a package manifest declares, keyed like the lockfile."""
    deps = (manifest.get("dependencies") or {}).get("apm") or []
    pins = {}
    for dep in deps:
        if not isinstance(dep, str):
            raise WorkspaceError("unsupported dependency form: %r" % (dep,))
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


def diff_pins(before: dict[tuple[str, str], str], after: dict[tuple[str, str], str],
              gone: str = "%s is gone", new: str = "%s appeared",
              moved: str = "%s %s -> %s") -> list[str]:
    """How two `{key: sha}` maps differ, one message per difference.

    Both callers compare the same two things by the same key -- a manifest's
    pins against a lockfile's resolved commits, or a lockfile against itself
    across an install -- and only the wording differs.
    """
    problems = []
    for key in sorted(set(before) | set(after)):
        if key not in after:
            problems.append(gone % label(key))
        elif key not in before:
            problems.append(new % label(key))
        elif before[key].lower() != after[key].lower():
            problems.append(moved % (label(key), before[key][:12], after[key][:12]))
    return problems
