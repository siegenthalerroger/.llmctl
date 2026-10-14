"""Shared provenance/licence model for the gates, the notices and the drift audit.

One parse of `metadata.provenance`, one obligation table, one path->default-licence
rule, so the four consumers cannot disagree about what a file claims. Anything outside
the documented shape -- a block that yields no entries, an entry with no `url`, a block
or a file licence written somewhere the parser does not read, an unknown key or field --
is reported as malformed rather than skipped: a file that silently stops being tracked
is the failure this exists to make loud. The convention itself is in
CONTRIBUTING.md#repository-frontmatter-provenance-convention.
"""

from __future__ import annotations

import difflib
import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import frontmatter

from .workspace import INSTALL_OUTPUT

__all__ = [
    "ADAPTED",
    "BINDING",
    "DEFAULT_CODE",
    "DEFAULT_CONTENT",
    "ENTRY_FIELDS",
    "FIDELITIES",
    "KNOWN_LICENSES",
    "OBLIGATION",
    "PERMITTED_OUTBOUND",
    "PROVENANCE_KEYS",
    "Entry",
    "Record",
    "default_license_for",
    "effective_fidelity",
    "iter_files",
    "parse",
]

# --- The licence model -----------------------------------------------------

# Repo defaults by path. Content is CC-BY-SA-4.0, tooling is MIT; see LICENSE.
DEFAULT_CONTENT = "CC-BY-SA-4.0"
DEFAULT_CODE = "MIT"

# Fidelity -> does upstream expression travel into the local file?
# Ideas and structure are not protected expression, so the first two attach nothing.
OBLIGATION = {
    "inspiration-only": False,
    "structural-echo": False,
    "partly-derived": True,
    "largely-derived": True,
}
FIDELITIES = tuple(OBLIGATION)

# Upstream licence -> what the local file may be licensed under, when terms attach.
# MIT permits sublicensing, so an MIT upstream can be carried under either default
# as long as the notice travels. The copyleft licences permit only themselves.
PERMITTED_OUTBOUND = {
    "MIT": ("MIT", "CC-BY-SA-4.0"),
    "BSD-2-Clause": ("MIT", "CC-BY-SA-4.0"),
    "BSD-3-Clause": ("MIT", "CC-BY-SA-4.0"),
    "ISC": ("MIT", "CC-BY-SA-4.0"),
    "Apache-2.0": ("Apache-2.0",),
    "CC-BY-4.0": ("CC-BY-4.0", "CC-BY-SA-4.0"),
    "CC-BY-SA-4.0": ("CC-BY-SA-4.0",),
    "GPL-3.0": ("GPL-3.0",),
    "MPL-2.0": ("MPL-2.0",),
    # Public-domain dedications reserve nothing, so any outbound licence is
    # permitted and no notice has to travel. Still recorded, and still credited
    # under Acknowledgements, because attribution is a courtesy we keep.
    "Unlicense": ("MIT", "CC-BY-SA-4.0"),
    "CC0-1.0": ("MIT", "CC-BY-SA-4.0"),
    # CC-BY-NC-4.0 permits copying with attribution but forbids commercial use,
    # which neither repo default can absorb: CC-BY-SA-4.0's ShareAlike requires
    # the adaptation be licensed CC-BY-SA, which permits commercial use, and MIT
    # cannot carry an NC restriction either. Listed with no permitted outbound,
    # so a source under it is usable only at a fidelity that attaches nothing --
    # take the shape, never the prose -- and anything above `structural-echo`
    # fails the gate rather than silently relicensing.
    "CC-BY-NC-4.0": (),
    # W3C-20150513 permits copying and porting with the full notice carried, so
    # in isolation it would sit with the permissive licences above. It is listed
    # with no permitted outbound deliberately, to force a re-read of LICENSE.md
    # before anything above `structural-echo` is used.
    "W3C-20150513": (),
    # No grant of rights at all -- nothing is permitted. Such a source is usable
    # only at a fidelity that attaches no obligation (`inspiration-only` or
    # `structural-echo`): take the idea or the shape, never the wording. `NONE`
    # is a source that states no licence (a repository without LICENSE, a book,
    # a blog), `Proprietary` a vendor documentation site that reserves all rights,
    # `NOASSERTION` a licence not yet established. Reproducing any of them has
    # no licensable remedy, so the only fix is rewriting.
    "NONE": (),
    "NOASSERTION": (),
    "Proprietary": (),
}
KNOWN_LICENSES = tuple(PERMITTED_OUTBOUND)

# Files carrying steering content. Everything else in the tree is code/config.
# `.md` alone, deliberately: the customization types (`*.agent.md`,
# `*.prompt.md`, `*.instructions.md`, `SKILL.md`) are all Markdown, and so are
# the `references/` files they link to -- which is where a reproduced spec table
# is most likely to land. Listing the four types would exclude exactly those, and
# every consumer (licence gate, notices, drift audit) reads them all alike: a
# reference page declares its own upstream, and `SKILL.md` never stands in for it.
CONTENT_SUFFIXES = (".md",)

# `authoritativeSpec` holds binding normative sources; `adaptedFrom` holds ordinary
# adaptations and borrowed material. The key says which, whether or not anything
# was copied -- so a drift review of the former assesses every normative change
# relevant to the declared subject, and `took` never narrows it.
BINDING = "authoritativeSpec"
ADAPTED = "adaptedFrom"
PROVENANCE_KEYS = (ADAPTED, BINDING)

# The fields an object entry may carry. Anything else is a misspelling (`licence`,
# `fidelty`), not an extension, and reading past it would judge the entry without it.
ENTRY_FIELDS = ("url", "license", "fidelity", "took")

# Names a misplaced block or file licence goes by, compared after `_norm`, so a case,
# separator or dotted spelling of a key in the wrong place is caught along with the key.
_PROVENANCE_NAMES = {"provenance", "adaptedfrom", "authoritativespec"}
_LICENSE_NAMES = {"license", "licence", "licenses", "licences"}

# What each kind of malformed declaration costs, said in the message that reports it.
_BLOCK = "nothing in it is tracked"
_ENTRY = "this entry is not tracked"
_FIELD = "the field is ignored, so the entry is judged without it"


def default_license_for(path: str | Path) -> str:
    """The repo default for a path, before any per-file `license:` override."""
    return DEFAULT_CONTENT if str(path).replace("\\", "/").endswith(".md") else DEFAULT_CODE


# --- Frontmatter parsing ---------------------------------------------------


@dataclass(frozen=True, slots=True)
class Entry:
    """One upstream a file declares, under the provenance key it came from."""

    url: str | None
    form: Literal["string", "object"]
    kind: str = ""
    license: str | None = None
    fidelity: str | None = None
    took: str | None = None


@dataclass(frozen=True, slots=True)
class Record:
    """One file's provenance: what it claims, and what it got wrong claiming it."""

    path: str
    declared: str | None
    effective: str
    entries: tuple[Entry, ...] = ()
    malformed: tuple[str, ...] = ()


def _norm(key: object) -> list[str]:
    """`key`'s dotted segments, lowercased to letters only. YAML keys need not be strings."""
    return ["".join(c for c in part.lower() if c.isalpha()) for part in str(key).split(".")]


def _kind_of(value: object) -> str:
    """How a value that is not the expected type reads in a message."""
    if value is None:
        return "empty"
    for types, name in (
        (bool, "a boolean"),  # before int: bool is an int
        ((int, float), "a number"),
        (str, "a string"),
        (list, "a list"),
        (dict, "a mapping"),
    ):
        if isinstance(value, types):
            return name
    return f"a {type(value).__name__}"


def _hint(name: object, allowed: tuple[str, ...]) -> str:
    folded = {a.lower(): a for a in allowed}
    close = difflib.get_close_matches(str(name).lower(), folded, n=1)
    return f"; did you mean `{folded[close[0]]}`?" if close else ""


def _allowed(names: tuple[str, ...]) -> str:
    return ", ".join(f"`{n}`" for n in names)


def _entries(value: object, kind: str) -> tuple[list[Entry], list[str]]:
    """Normalise one provenance key's value into entries, and every problem found doing it.

    Three forms are accepted, as documented in source-url-reference.md: a URL string, a
    list of URL strings, or a list of objects carrying `url` plus any of `license` /
    `fidelity` / `took`. An entry with no usable `url` is reported and dropped.
    """
    if isinstance(value, str):
        value = [value]
    elif not isinstance(value, list):
        return [], [f"`{kind}` is {_kind_of(value)}, not a URL or a list of entries - {_BLOCK}"]
    if not value:
        return [], [f"`{kind}` yields no entries - {_BLOCK}"]
    entries, problems = [], []
    for item in value:
        if isinstance(item, dict):
            entry, found = _object_entry(item, kind)
            problems += found
        elif isinstance(item, str) and item.strip():
            entry = Entry(item.strip(), "string", kind)
        else:
            entry = None
            problems.append(f"`{kind}` has an entry with no url - {_ENTRY}")
        if entry:
            entries.append(entry)
    return entries, problems


def _object_entry(item: dict, kind: str) -> tuple[Entry | None, list[str]]:
    """One object-form entry, or None when it has no usable `url`, and its problems.

    A field outside `ENTRY_FIELDS`, or one that is not a string, is reported and ignored
    while the entry is kept, so the drift audit still tracks it.
    """
    url = item.get("url")
    if url is not None and not isinstance(url, str):
        return None, [
            f"`{kind}` has an entry whose `url` is {_kind_of(url)}, not a string - {_ENTRY}"
        ]
    url = (url or "").strip()
    where = f"{kind} -> {url}" if url else f"`{kind}` entry with no url"
    problems = [
        f"{where}: unknown field `{name}` (allowed: {_allowed(ENTRY_FIELDS)}"
        f"{_hint(name, ENTRY_FIELDS)}) - {_FIELD if url else _ENTRY}"
        for name in item
        if name not in ENTRY_FIELDS
    ]
    if not url:
        return None, [*problems, f"`{kind}` has an entry with no url - {_ENTRY}"]
    fields: dict[str, str | None] = {}
    for name in ("license", "fidelity", "took"):
        raw = item.get(name)
        if raw is None or isinstance(raw, str):
            fields[name] = _text(raw)
            continue
        # str() of a list or a YAML 1.1 boolean (`took: no`) reads as text, and a truthy
        # `took` would claim a borrowing nobody recorded.
        problems.append(f"{where}: `{name}` is {_kind_of(raw)}, not a string - {_FIELD}")
        fields[name] = None
    entry = Entry(url, "object", kind, fields["license"], fields["fidelity"], fields["took"])
    return entry, problems


def _text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _declared(provenance: dict) -> tuple[tuple[Entry, ...], tuple[str, ...]]:
    """Every entry under a provenance key, and every problem found reading the block.

    A key that is not one of `PROVENANCE_KEYS` is reported, never read as the key it
    resembles; the valid keys beside it are still read.
    """
    entries, malformed = [], []
    for key, value in provenance.items():
        if key not in PROVENANCE_KEYS:
            malformed.append(
                f"`metadata.provenance.{key}` is not a provenance key (allowed: "
                f"{_allowed(PROVENANCE_KEYS)}{_hint(key, PROVENANCE_KEYS)}) - {_BLOCK}"
            )
            continue
        found, problems = _entries(value, key)
        entries += found
        malformed += problems
    return tuple(entries), tuple(malformed)


def _misplaced(metadata: dict, default: str) -> list[str]:
    """Provenance and file-licence keys written where the parser does not read them.

    Reported even beside a valid `metadata.provenance`, which is still read: the
    canonical placement is the only format, so a second one is an error, not an input.
    """
    licence = (
        "the file's own licence is the top-level `license` field - "
        f"the file keeps the repo default `{default}`"
    )
    elsewhere = f"provenance belongs under `metadata.provenance` - {_BLOCK}"
    found = []
    for key in metadata:
        name = _norm(key)
        if key in ("metadata", "license"):
            continue
        if name == ["metadata"]:
            found.append(f"`{key}` is not read: the key is `metadata`, and {elsewhere}")
        elif name[-1] in _PROVENANCE_NAMES:
            found.append(f"`{key}` is not read: {elsewhere}")
        elif name[-1] in _LICENSE_NAMES:
            found.append(f"`{key}` is not read: {licence}")
    container = metadata.get("metadata")
    for key in container if isinstance(container, dict) else ():
        name = _norm(key)
        if key == "provenance":
            continue
        if name[-1] in _PROVENANCE_NAMES:
            found.append(f"`metadata.{key}` is not read: {elsewhere}")
        elif name[-1] in _LICENSE_NAMES:
            found.append(f"`metadata.{key}` is not read: {licence}")
    return found


def parse(path: str | Path) -> Record:
    """Read one file's provenance.

    A block that yields no entries, an entry with no `url`, a `metadata.provenance` that
    is not a non-empty mapping, and a provenance block or file licence written anywhere
    the parser does not read, all land in `malformed` rather than being dropped: a file
    that silently stops being tracked is the failure this exists to make loud.
    """
    default = default_license_for(path)
    text = Path(path).read_text(encoding="utf-8")
    if not text.startswith("---"):
        return Record(str(path), None, default)
    try:
        metadata = frontmatter.loads(text).metadata
    except Exception as exc:  # YAML errors surface as several exception types
        return Record(
            str(path),
            None,
            default,
            malformed=(
                "frontmatter does not parse as YAML: {} - none of this frontmatter is read, "
                "so the file declares no provenance and no licence".format(str(exc).split("\n")[0]),
            ),
        )
    if not isinstance(metadata, dict):
        return Record(str(path), None, default)

    declared = _text(metadata.get("license"))
    malformed = _misplaced(metadata, default)
    entries: tuple[Entry, ...] = ()
    container = metadata.get("metadata")
    if container is not None and not isinstance(container, dict):
        malformed.append(
            f"`metadata` is {_kind_of(container)}, not a mapping - `metadata.provenance` "
            f"cannot be read, so {_BLOCK}"
        )
    elif isinstance(container, dict) and "provenance" in container:
        provenance = container["provenance"]
        if isinstance(provenance, dict) and provenance:
            entries, problems = _declared(provenance)
            malformed += problems
        else:
            what = "empty" if provenance in (None, {}, [], "") else _kind_of(provenance)
            malformed.append(
                f"`metadata.provenance` is {what}, not a mapping of "
                f"{_allowed(PROVENANCE_KEYS)} - {_BLOCK}"
            )
    return Record(str(path), declared, declared or default, entries, tuple(malformed))


def effective_fidelity(entry: Entry) -> str:
    """The fidelity to judge an entry by, applying the documented defaults.

    A bare `authoritativeSpec` URL asserts a citation -- nothing reproduced -- and
    so does an object entry that states no fidelity. The licence gate rejects such an
    object when it records `took`, so this default never judges a recorded borrowing.
    A bare `adaptedFrom` URL asserts whole-file derivation.
    """
    if entry.fidelity:
        return entry.fidelity
    if entry.kind == BINDING:
        return "inspiration-only"
    return "largely-derived"


# Copies rather than sources: APM dependencies, the deploy mirrors `apm install`
# writes beside a package, and build scratch. A vendored upstream carries its own
# adaptedFrom and a deployed mirror carries the same one twice, so walking either
# would attribute an upstream's provenance to this repository.
SKIP_DIRS = {".git", "build", "node_modules", "__pycache__", "LICENSES", *INSTALL_OUTPUT}


def iter_files(root: str | Path) -> Iterator[str]:
    """Every authored content file under `packages/` and `.apm/`.

    Repo-root docs carry no provenance, so there is nothing to check on them.
    """
    for base in ("packages", ".apm"):
        top = Path(root) / base
        if not top.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(top):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
            for name in sorted(filenames):
                if name.endswith(CONTENT_SUFFIXES):
                    yield str(Path(dirpath) / name)
