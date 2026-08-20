#!/usr/bin/env python3
"""Shared provenance/licence model for check-licenses.py and gen-notices.py.

One parse of `metadata.provenance`, one obligation table, one path->default-licence
rule. check-licenses.py, gen-notices.py and the meta-upstream-sync drift audit all
import from here, so they cannot disagree about what a file claims. The block is
walked line by line rather than matched with one spanning regex: the object form
nests, and a regex that tries to span it matches nothing, dropping the file from
every consumer at once with no error.

Deliberately dependency-free, matching pack-marketplace.py: it reads the handful of
keys it needs rather than pulling in a YAML parser, and every form it does not
recognise is reported rather than skipped.
"""
import io
import os
import re

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
    # No grant of rights at all — nothing is permitted. Such a source is usable
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
# the `references/` files they link to — which is where a reproduced spec table
# is most likely to land. Listing the four types would exclude exactly those.
CONTENT_SUFFIXES = (".md",)

# The four file types that define a primitive. `iter_files` yields every `.md`
# because a `references/` page can carry provenance too; the drift audit walks
# only these four, because only a primitive has an upstream to drift from.
CUSTOMIZATION_NAMES = ("SKILL.md",)
CUSTOMIZATION_SUFFIXES = (".agent.md", ".instructions.md", ".prompt.md")


def is_customization(path):
    """True for the four primitive-defining file types."""
    name = os.path.basename(path)
    return name in CUSTOMIZATION_NAMES or name.endswith(CUSTOMIZATION_SUFFIXES)


def default_license_for(path):
    """The repo default for a path, before any per-file `license:` override."""
    return DEFAULT_CONTENT if path.replace("\\", "/").endswith(".md") else DEFAULT_CODE


# --- Frontmatter parsing ---------------------------------------------------


def frontmatter(text):
    """Return the raw frontmatter block, or None when the file has none."""
    if not text.startswith("---"):
        return None
    lines = text.split("\n")
    if lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i])
    return None


def scalar(block, key):
    """A top-level scalar field's value, unquoted. None when absent."""
    m = re.search(r"(?m)^%s:[ \t]*(.*)$" % re.escape(key), block)
    if not m:
        return None
    return m.group(1).strip().strip("\"'") or None


def _parse_block(lines, start, key):
    """Parse one provenance key into entry dicts. Returns (entries, next_index).

    The block ends at the first line indented no deeper than the key. A spanning
    regex would match nothing on the nested form and drop the file silently --
    from this parse, and so from every tool that reads it.
    """
    key_indent = len(lines[start]) - len(lines[start].lstrip())
    inline = lines[start].split(":", 1)[1].strip()
    entries = []

    if re.match(r'^["\']?https?://', inline):
        entries.append({"url": inline.strip("\"'"), "license": None,
                        "fidelity": None, "took": None, "form": "string"})
        return entries, start + 1

    i = start + 1
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if len(line) - len(line.lstrip()) <= key_indent:
            break
        m = re.match(r'^[ \t]*-[ \t]*url[ \t]*:[ \t]*["\']?(https?://[^"\'\s]+)', line)
        if m:
            entries.append({"url": m.group(1), "license": None,
                            "fidelity": None, "took": None, "form": "object"})
        elif re.match(r'^[ \t]*-[ \t]*["\']?https?://', line):
            url = re.sub(r"^[ \t]*-[ \t]*", "", line).strip().strip("\"'")
            entries.append({"url": url, "license": None,
                            "fidelity": None, "took": None, "form": "string"})
        elif re.match(r"^[ \t]*-[ \t]*$", line):
            # A dash with the url on a following line: not a form we emit, but
            # accepting it silently would hide a malformed entry.
            entries.append({"url": None, "license": None,
                            "fidelity": None, "took": None, "form": "object"})
        else:
            for field in ("license", "fidelity", "took"):
                m = re.match(r"^[ \t]*%s[ \t]*:[ \t]*(.+?)[ \t]*$" % field, line)
                if m and entries:
                    entries[-1][field] = m.group(1).strip().strip("\"'")
                    break
        i += 1
    return entries, i


def parse(path):
    """Read one file's provenance.

    Returns a dict with `path`, `declared` (top-level `license:` or None),
    `effective` (declared or the path default), and `entries` — one record per
    upstream URL, tagged with the provenance key it came from.
    """
    text = io.open(path, encoding="utf-8").read()
    block = frontmatter(text)
    result = {
        "path": path,
        "declared": None,
        "effective": default_license_for(path),
        "entries": [],
        "malformed": [],
    }
    if block is None:
        return result

    result["declared"] = scalar(block, "license")
    if result["declared"]:
        result["effective"] = result["declared"]

    lines = block.split("\n")
    i = 0
    while i < len(lines):
        m = re.match(r"^[ \t]*(adaptedFrom|authoritativeSpec)[ \t]*:", lines[i])
        if not m:
            i += 1
            continue
        key = m.group(1)
        entries, i = _parse_block(lines, i, key)
        if not entries:
            result["malformed"].append("`%s` yields no entries" % key)
        for e in entries:
            if not e["url"]:
                result["malformed"].append("`%s` has an entry with no url" % key)
                continue
            e["kind"] = key
            result["entries"].append(e)
    return result


def effective_fidelity(entry):
    """The fidelity to judge an entry by, applying the documented defaults.

    A bare `authoritativeSpec` URL asserts a citation — nothing reproduced. A bare
    `adaptedFrom` URL asserts whole-file derivation.
    """
    if entry["fidelity"]:
        return entry["fidelity"]
    if entry["kind"] == "authoritativeSpec":
        return "inspiration-only"
    return "largely-derived"


def iter_files(root):
    """Every authored content file under `packages/` and `.apm/`.

    Repo-root docs (README, CONTRIBUTING, AGENTS, TODO) are covered by the same
    default rule but carry no provenance, so there is nothing to check on them.

    Every name in `skip` holds copies rather than sources — APM dependencies, the
    deploy mirrors `apm install` writes next to a package, and build scratch. A
    vendored upstream carries its own `adaptedFrom` and a deployed mirror carries
    the same one twice, so walking either would attribute an upstream's
    provenance to this repository.
    """
    skip = {".git", "apm_modules", "build", "node_modules", "__pycache__",
            ".claude", ".agents", "LICENSES"}
    for base in ("packages", ".apm"):
        top = os.path.join(root, base)
        if not os.path.isdir(top):
            continue
        for dirpath, dirnames, filenames in os.walk(top):
            dirnames[:] = sorted(d for d in dirnames if d not in skip)
            for name in sorted(filenames):
                if name.endswith(CONTENT_SUFFIXES):
                    yield os.path.join(dirpath, name)
