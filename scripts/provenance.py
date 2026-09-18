"""Shared provenance/licence model for the gates, the notices and the drift audit.

One parse of `metadata.provenance`, one obligation table, one path->default-licence
rule, so the four consumers cannot disagree about what a file claims. A block that
yields no entries, or an entry with no `url`, is reported as malformed rather than
skipped: a file that silently stops being tracked is the failure this exists to
make loud. The convention itself is in CONTRIBUTING.md#repository-frontmatter-provenance-convention.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Literal

import frontmatter

from workspace import INSTALL_OUTPUT

__all__ = ["DEFAULT_CODE", "DEFAULT_CONTENT", "Entry", "FIDELITIES",
           "KNOWN_LICENSES", "OBLIGATION", "PERMITTED_OUTBOUND",
           "PROVENANCE_KEYS", "Record", "default_license_for",
           "effective_fidelity", "is_customization", "iter_files", "parse"]

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
    # W3C-20150513 permits copying and porting with the full notice carried, so
    # in isolation it would sit with the permissive licences above. It is listed
    # with no permitted outbound deliberately, to enforce re-evaluation of LICENSE.md
    # if any more than `inspiration-only` is used.
    "W3C-20150513": (),
    # No grant of rights at all -- nothing is permitted. Such a source is usable
    # only at a fidelity that attaches no obligation, i.e. cite it, never copy it.
    # `Proprietary` covers the vendor documentation sites: reproducing their
    # wording has no licensable remedy, so the only fix is rewriting.
    "NONE": (),
    "NOASSERTION": (),
    "Proprietary": (),
}
KNOWN_LICENSES = tuple(PERMITTED_OUTBOUND)

# Files carrying steering content. Everything else in the tree is code/config.
# `.md` alone, deliberately: the customization types (`*.agent.md`,
# `*.prompt.md`, `*.instructions.md`, `SKILL.md`) are all Markdown, and so are
# the `references/` files they link to -- which is where a reproduced spec table
# is most likely to land. Listing the four types would exclude exactly those.
CONTENT_SUFFIXES = (".md",)

# The four file types that define a primitive. `iter_files` yields every `.md`
# because a `references/` page can carry provenance too; the drift audit walks
# only these four, because only a primitive has an upstream to drift from.
CUSTOMIZATION_NAMES = ("SKILL.md",)
CUSTOMIZATION_SUFFIXES = (".agent.md", ".instructions.md", ".prompt.md")

PROVENANCE_KEYS = ("adaptedFrom", "authoritativeSpec")


def is_customization(path: str | Path) -> bool:
    """True for the four primitive-defining file types."""
    name = os.path.basename(str(path))
    return name in CUSTOMIZATION_NAMES or name.endswith(CUSTOMIZATION_SUFFIXES)


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


def _entries(value: object, kind: str) -> list[Entry]:
    """Normalise one provenance key's value into entries.

    Three forms are accepted, as documented in CONTRIBUTING.md: a URL string, a
    list of URL strings, or a list of objects carrying `url` plus any of
    `license` / `fidelity` / `took`. Anything else yields an entry with no url,
    which the caller reports as malformed.
    """
    if isinstance(value, str):
        return [Entry(value.strip() or None, "string", kind)]
    if not isinstance(value, list):
        return [Entry(None, "object", kind)]
    entries = []
    for item in value:
        if isinstance(item, str):
            entries.append(Entry(item.strip() or None, "string", kind))
        elif isinstance(item, dict):
            url = item.get("url")
            entries.append(Entry(
                str(url).strip() if url else None, "object", kind,
                license=_text(item.get("license")),
                fidelity=_text(item.get("fidelity")),
                took=_text(item.get("took"))))
        else:
            entries.append(Entry(None, "object", kind))
    return entries


def _text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _declared(provenance: dict) -> tuple[tuple[Entry, ...], tuple[str, ...]]:
    """Every entry under a known provenance key, and every problem found doing it."""
    entries, malformed = [], []
    for key in PROVENANCE_KEYS:
        if key not in provenance:
            continue
        found = _entries(provenance.get(key), key)
        if not found:
            malformed.append("`%s` yields no entries" % key)
        for entry in found:
            if not entry.url:
                malformed.append("`%s` has an entry with no url" % key)
                continue
            entries.append(entry)
    return tuple(entries), tuple(malformed)


def parse(path: str | Path) -> Record:
    """Read one file's provenance.

    A block that yields no entries, and an entry with no `url`, land in
    `malformed` rather than being dropped: a file that silently stops being
    tracked is the failure this exists to make loud.
    """
    default = default_license_for(path)
    text = Path(path).read_text(encoding="utf-8")
    if not text.startswith("---"):
        return Record(str(path), None, default)
    try:
        metadata = frontmatter.loads(text).metadata
    except Exception as exc:  # YAML errors surface as several exception types
        return Record(str(path), None, default, malformed=(
            "frontmatter does not parse as YAML: %s" % str(exc).split("\n")[0],))
    if not isinstance(metadata, dict):
        return Record(str(path), None, default)

    declared = _text(metadata.get("license"))
    container = metadata.get("metadata")
    provenance = container.get("provenance") if isinstance(container, dict) else None
    entries, malformed = (_declared(provenance) if isinstance(provenance, dict)
                          else ((), ()))
    return Record(str(path), declared, declared or default, entries, malformed)


def effective_fidelity(entry: Entry) -> str:
    """The fidelity to judge an entry by, applying the documented defaults.

    A bare `authoritativeSpec` URL asserts a citation -- nothing reproduced. A bare
    `adaptedFrom` URL asserts whole-file derivation.
    """
    if entry.fidelity:
        return entry.fidelity
    if entry.kind == "authoritativeSpec":
        return "inspiration-only"
    return "largely-derived"


# Copies rather than sources: APM dependencies, the deploy mirrors `apm install`
# writes beside a package, and build scratch. A vendored upstream carries its own
# adaptedFrom and a deployed mirror carries the same one twice, so walking either
# would attribute an upstream's provenance to this repository.
SKIP_DIRS = {".git", "build", "node_modules", "__pycache__", "LICENSES",
             *INSTALL_OUTPUT}


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
                    yield os.path.join(dirpath, name)
