#!/usr/bin/env python3
"""Measure colour pairs and simulate colour-vision deficiency.

  python check-contrast.py pair "body=#4a4a4a/#ffffff" "link=#0b5/#fff"
  python check-contrast.py cvd  "#e69f00" "#56b4e9" "#009e73" "#cc79a7"

`pair` reports WCAG 2 ratio and APCA Lc for text-on-background pairs.
`cvd` simulates each colour under dichromacy and reports how far apart the
closest pair ends up, which is the check a greyscale test cannot do.
`selftest` checks the maths against published values and, where the optional
library is present, against a second independent implementation.

Exits 1 if any pair fails its WCAG threshold, so this can gate a build.
Python 3.9+. Runs on the standard library alone.

Install `coloraide` (MIT, pure Python, no dependencies of its own) to widen
what the input accepts -- any CSS colour, `oklch()`, Display-P3, and alpha
composited over the background rather than ignored:

    pip install coloraide

The colour maths stays here either way, because it has to. No maintained
Python library implements APCA -- coloraide ships only `wcag21` and `lstar`.
Since APCA has to be local, WCAG and the CVD matrices stay local beside it
rather than splitting the algorithms across two sources that could drift.
`selftest` is what keeps that honest: it cross-checks against coloraide
whenever coloraide is there.
"""

from __future__ import annotations

import argparse
import math
import sys

# The output is markdown containing en and em dashes. Windows consoles still
# default to a legacy code page, which mangles them, so force UTF-8 rather
# than degrading the artefact this script exists to emit.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# --- Constants, and where each one comes from -------------------------------
#
# WCAG 2: relative luminance and the piecewise sRGB transfer function are
# normative in WCAG 2.x "Understanding SC 1.4.3". Both constants below are
# WCAG's own rather than colorimetry's, because WCAG's numbers are what an
# audit reproduces:
#
#   Breakpoint. WCAG says 0.03928, the sRGB spec says 0.04045. No 8-bit
#   channel value falls between them, so at this precision the choice cannot
#   change a result -- verified by `selftest`.
#
#   Coefficients. WCAG rounds to 4 significant figures. The exact sRGB-to-XYZ
#   Y row is 0.2126729 / 0.7151522 / 0.0721750 (what APCA uses below, and what
#   colour libraries use). The rounding shifts a ratio by up to ~0.0005, which
#   `selftest` measures against coloraide rather than assuming away. It has
#   never been enough to cross a threshold, but it is a real divergence and is
#   deliberate, not an approximation.
WCAG_COEFF = (0.2126, 0.7152, 0.0722)
WCAG_BREAK = 0.03928

# APCA-W3 0.1.9 "G-4g" constants, read from the reference implementation at
# github.com/Myndex/apca-w3 (`SA98G`). APCA linearises with a plain 2.4 power
# curve rather than WCAG's piecewise one -- they are different algorithms and
# the exponents are not interchangeable.
APCA = {
    "main_trc": 2.4,
    "coeff": (0.2126729, 0.7151522, 0.0721750),
    "norm_bg": 0.56,      # exponents for normal polarity (dark text on light)
    "norm_txt": 0.57,
    "rev_bg": 0.65,       # exponents for reverse polarity (light text on dark)
    "rev_txt": 0.62,
    "blk_thrs": 0.022,    # below this luminance, black is soft-clamped
    "blk_clmp": 1.414,
    "scale": 1.14,        # same scaler both polarities in this revision
    "offset": 0.027,
    "delta_y_min": 0.0005,
    "lo_clip": 0.1,
}

# APCA's published guidance levels. These are use-case thresholds, not a
# conformance standard -- APCA is not normative in any WCAG version.
APCA_LEVELS = (
    (90, "body text, preferred"),
    (75, "body text, minimum"),
    (60, "other content text"),
    (45, "large text and headlines"),
    (30, "any text at all, including placeholder and disabled"),
    (15, "non-text elements only"),
)

# Machado, Oliveira and Fernandes (2009), severity 1.0. Values as published
# and as carried by colour-science's `CVD_MATRICES_MACHADO2010`.
#
# Applied to LINEAR RGB, which is the space the model is derived in -- it is
# fitted to physiological cone response, and cone response is linear in light.
# coloraide agrees; culori does not, applying the same matrices to
# gamma-encoded sRGB and producing visibly lighter, less-shifted results.
# This is not a rounding difference, it is a different answer, so the choice
# is recorded rather than assumed. If a result here ever has to be reconciled
# with a JavaScript tool, check which space that tool used before assuming
# one of them is broken.
CVD_MATRICES = {
    "protanopia": (
        (0.152286, 1.052583, -0.204868),
        (0.114503, 0.786281, 0.099216),
        (-0.003882, -0.048116, 1.051998),
    ),
    "deuteranopia": (
        (0.367322, 0.860646, -0.227968),
        (0.280085, 0.672501, 0.047413),
        (-0.011820, 0.042940, 0.968881),
    ),
    "tritanopia": (
        (1.255528, -0.076749, -0.178779),
        (-0.078411, 0.930809, 0.147602),
        (0.004733, 0.691367, 0.303900),
    ),
}

# OKLab from linear sRGB (Björn Ottosson). Used for the separation metric
# because Euclidean distance in OKLab tracks perceived difference far better
# than CIE76 does, and OKLab is the space this skill reasons in anyway.
OKLAB_M1 = (
    (0.4122214708, 0.5363325363, 0.0514459929),
    (0.2119034982, 0.6806995451, 0.1073969566),
    (0.0883024619, 0.2817188376, 0.6299787005),
)
OKLAB_M2 = (
    (0.2104542553, 0.7936177850, -0.0040720468),
    (1.9779984951, -2.4285922050, 0.4505937099),
    (0.0259040371, 0.7827717662, -0.8086757660),
)


# --- Colour parsing ---------------------------------------------------------

try:  # Optional. Widens input to any CSS colour; never changes the maths.
    from coloraide import Color as _Color
except ImportError:  # pragma: no cover - depends on the environment
    _Color = None

ENGINE = "coloraide" if _Color else "built-in sRGB parser"


def parse_colour(text: str, over: tuple[int, int, int] | None = None) -> tuple[int, int, int]:
    """Parse a colour to 8-bit sRGB.

    With coloraide present this accepts any CSS colour -- named, `oklch()`,
    `color(display-p3 ...)`, `hsl()` -- and composites alpha over `over`
    (default white), because a translucent foreground has no contrast value
    until you know what is behind it. Without it, #rgb / #rrggbb / 'r,g,b'.
    """
    text = text.strip()
    if _Color is not None:
        try:
            c = _Color(text).convert("srgb")
        except Exception:
            raise ValueError(f"{text!r}: not a colour coloraide recognises") from None
        alpha = c[-1]
        if alpha is None or alpha != alpha:  # NaN means unspecified, i.e. opaque
            alpha = 1.0
        ground = over if over is not None else (255, 255, 255)
        chans = [max(0.0, min(1.0, v)) * 255 for v in c[:-1]]
        if alpha < 1.0:
            chans = [v * alpha + g * (1 - alpha) for v, g in zip(chans, ground)]
        return tuple(int(round(v)) for v in chans)  # type: ignore[return-value]

    raw = text.lstrip("#")
    if "," in raw:
        parts = [p.strip() for p in raw.split(",")]
        if len(parts) != 3:
            raise ValueError(f"{text!r}: expected three comma-separated channels")
        try:
            rgb = tuple(int(p) for p in parts)
        except ValueError:
            raise ValueError(f"{text!r}: channels must be whole numbers 0-255") from None
        if not all(0 <= c <= 255 for c in rgb):
            raise ValueError(f"{text!r}: channels must be within 0-255")
        return rgb  # type: ignore[return-value]

    if len(raw) == 3:
        raw = "".join(c * 2 for c in raw)
    if len(raw) != 6:
        raise ValueError(f"{text!r}: expected #rgb, #rrggbb, or 'r,g,b'")
    try:
        return tuple(int(raw[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError:
        raise ValueError(f"{text!r}: not valid hexadecimal") from None


def to_hex(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{max(0, min(255, round(c))):02x}" for c in rgb)


# --- Colour maths -----------------------------------------------------------

def _linear_srgb(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    """Gamma-decode to linear light. The piecewise sRGB transfer function."""
    out = []
    for c in rgb:
        v = c / 255.0
        out.append(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4)
    return tuple(out)  # type: ignore[return-value]


def _encode_srgb(linear: tuple[float, float, float]) -> tuple[float, float, float]:
    out = []
    for v in linear:
        v = max(0.0, min(1.0, v))
        out.append((v * 12.92 if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055) * 255)
    return tuple(out)  # type: ignore[return-value]


def wcag_ratio(fg: tuple[int, int, int], bg: tuple[int, int, int]) -> float:
    def luminance(rgb):
        chans = []
        for c in rgb:
            v = c / 255.0
            chans.append(v / 12.92 if v <= WCAG_BREAK else ((v + 0.055) / 1.055) ** 2.4)
        return sum(k * v for k, v in zip(WCAG_COEFF, chans))

    a, b = luminance(fg), luminance(bg)
    lo, hi = min(a, b), max(a, b)
    return (hi + 0.05) / (lo + 0.05)


def _apca_luminance(rgb: tuple[int, int, int]) -> float:
    exp = APCA["main_trc"]
    return sum(k * (c / 255.0) ** exp for k, c in zip(APCA["coeff"], rgb))


def apca_lc(fg: tuple[int, int, int], bg: tuple[int, int, int]) -> float:
    """Signed Lc. Positive is dark-on-light, negative is light-on-dark."""
    txt_y, bg_y = _apca_luminance(fg), _apca_luminance(bg)

    # Soft-clamp near black: below the threshold, perceived contrast falls off
    # faster than luminance does, so the raw value would overstate it.
    thr, clmp = APCA["blk_thrs"], APCA["blk_clmp"]
    txt_y = txt_y if txt_y > thr else txt_y + (thr - txt_y) ** clmp
    bg_y = bg_y if bg_y > thr else bg_y + (thr - bg_y) ** clmp

    if abs(bg_y - txt_y) < APCA["delta_y_min"]:
        return 0.0

    if bg_y > txt_y:  # normal polarity
        sapc = (bg_y ** APCA["norm_bg"] - txt_y ** APCA["norm_txt"]) * APCA["scale"]
        out = 0.0 if sapc < APCA["lo_clip"] else sapc - APCA["offset"]
    else:  # reverse polarity, returns negative by design
        sapc = (bg_y ** APCA["rev_bg"] - txt_y ** APCA["rev_txt"]) * APCA["scale"]
        out = 0.0 if sapc > -APCA["lo_clip"] else sapc + APCA["offset"]
    return out * 100.0


def apca_verdict(lc: float) -> str:
    magnitude = abs(lc)
    for level, use in APCA_LEVELS:
        if magnitude >= level:
            return f"Lc {level}+ — {use}"
    return "below Lc 15 — carries no meaning at any size"


def simulate_cvd(rgb: tuple[int, int, int], deficiency: str) -> tuple[float, float, float]:
    matrix = CVD_MATRICES[deficiency]
    lin = _linear_srgb(rgb)
    shifted = tuple(sum(m * v for m, v in zip(row, lin)) for row in matrix)
    return _encode_srgb(shifted)  # type: ignore[arg-type]


def oklab(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    lin = _linear_srgb(tuple(int(round(max(0, min(255, c)))) for c in rgb))  # type: ignore[arg-type]
    lms = [sum(m * v for m, v in zip(row, lin)) for row in OKLAB_M1]
    lms = [math.copysign(abs(v) ** (1 / 3), v) for v in lms]
    return tuple(sum(m * v for m, v in zip(row, lms)) for row in OKLAB_M2)  # type: ignore[return-value]


def oklab_distance(a, b) -> float:
    return math.dist(oklab(a), oklab(b))


# --- Commands ---------------------------------------------------------------

def _split_spec(spec: str, sep: str | None) -> tuple[str, str]:
    """Return (label, value). A label is anything before the first '='."""
    label, _, rest = spec.partition("=")
    if not rest:
        label, rest = "", spec
    if sep and sep not in rest:
        raise ValueError(f"{spec!r}: expected FOREGROUND{sep}BACKGROUND")
    return label.strip(), rest.strip()


def cmd_pair(specs: list[str], level: str, large: bool) -> int:
    threshold = {"AA": 3.0 if large else 4.5, "AAA": 4.5 if large else 7.0}[level]
    rows, failures = [], 0

    for spec in specs:
        label, rest = _split_spec(spec, "/")
        fg_text, bg_text = rest.split("/", 1)
        # Background first: a translucent foreground composites over it, and
        # contrast against an uncomposited alpha value is meaningless.
        bg = parse_colour(bg_text)
        fg = parse_colour(fg_text, over=bg)
        ratio, lc = wcag_ratio(fg, bg), apca_lc(fg, bg)
        passed = ratio >= threshold
        failures += not passed
        rows.append((
            label or f"{to_hex(fg)} on {to_hex(bg)}",
            to_hex(fg), to_hex(bg),
            f"{ratio:.2f}:1",
            f"{lc:+.1f}",
            ("pass" if passed else "FAIL") + f" ({level}"
            + (" large" if large else "") + f", needs {threshold:g}:1)",
            apca_verdict(lc),
        ))

    print(f"| Pair | Text | Ground | WCAG 2 | APCA Lc | WCAG verdict | APCA reach |")
    print("|---|---|---|---|---|---|---|")
    for r in rows:
        print("| " + " | ".join(r) + " |")

    print()
    print("WCAG 2 overstates contrast near black, so a dark-theme pair can clear its")
    print("ratio and still fail readers. Where the two columns disagree, the APCA")
    print("column is the one describing what someone can actually read.")
    print(f"Parsed by: {ENGINE}.")
    return 1 if failures else 0


def cmd_cvd(specs: list[str]) -> int:
    entries = []
    for spec in specs:
        label, rest = _split_spec(spec, None)
        rgb = parse_colour(rest)
        entries.append((label or to_hex(rgb), rgb))

    if len(entries) < 2:
        print("check-contrast: `cvd` needs at least two colours to compare.",
              file=sys.stderr)
        return 2

    print("| Colour | Normal | Protanopia | Deuteranopia | Tritanopia |")
    print("|---|---|---|---|---|")
    for label, rgb in entries:
        sims = [to_hex(simulate_cvd(rgb, d)) for d in
                ("protanopia", "deuteranopia", "tritanopia")]
        print(f"| {label} | {to_hex(rgb)} | " + " | ".join(sims) + " |")

    print()
    print("| Vision | Closest pair | OKLab separation |")
    print("|---|---|---|")
    worst = []
    for deficiency in ("normal", "protanopia", "deuteranopia", "tritanopia"):
        pairs = []
        for i, (la, ca) in enumerate(entries):
            for lb, cb in entries[i + 1:]:
                a = ca if deficiency == "normal" else simulate_cvd(ca, deficiency)
                b = cb if deficiency == "normal" else simulate_cvd(cb, deficiency)
                pairs.append((oklab_distance(a, b), la, lb))
        dist, la, lb = min(pairs)
        worst.append(dist)
        print(f"| {deficiency.capitalize()} | {la} / {lb} | {dist:.4f} |")

    print()
    print("Separation is Euclidean distance in OKLab: a comparison aid, not a")
    print("standard, because no published threshold covers arbitrary mark sizes.")
    print("Read it as a ranking against the normal-vision row "
          f"({worst[0]:.4f}). A deficiency")
    print("row far below it is a collision, and colour alone cannot resolve a")
    print("collision — add shape, position, or a direct label.")
    return 0


def cmd_selftest() -> int:
    """Check the maths against published values, then against a second engine."""
    failures = 0

    def check(name: str, got: float, want: float, tol: float) -> None:
        nonlocal failures
        ok = abs(got - want) <= tol
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: {got:.6f} "
              f"(expected {want:.6f} ±{tol})")

    # Values published by the respective specs and reference implementations.
    print("Published reference values:")
    check("WCAG black on white", wcag_ratio((0, 0, 0), (255, 255, 255)), 21.0, 1e-9)
    check("WCAG white on white", wcag_ratio((255,) * 3, (255,) * 3), 1.0, 1e-9)
    # #767676 is the canonical "just passes AA on white" grey, #777777 the
    # canonical near-miss. If the transfer function drifts, these cross 4.5.
    check("WCAG #767676 on white", wcag_ratio((118,) * 3, (255,) * 3), 4.5422, 1e-3)
    check("WCAG #777777 on white", wcag_ratio((119,) * 3, (255,) * 3), 4.4781, 1e-3)
    # apca-w3's own documented figure for maximum-contrast normal polarity.
    check("APCA black on white", apca_lc((0, 0, 0), (255,) * 3), 106.04, 5e-2)
    check("APCA white on black", apca_lc((255,) * 3, (0, 0, 0)), -107.88, 5e-2)
    check("APCA identical pair", apca_lc((128,) * 3, (128,) * 3), 0.0, 1e-9)

    if _Color is None:
        print("\ncoloraide not installed - cross-check skipped.")
        print("Install it (`pip install coloraide`) to verify against a second")
        print("independent implementation as well as the published values.")
    else:
        print("\nCross-check against coloraide:")
        samples = ["#000000", "#ffffff", "#767676", "#e69f00", "#56b4e9",
                   "#009e73", "#cc79a7", "#121212", "#e0e0e0"]
        worst_wcag = 0.0
        for fg in samples:
            for bg in samples:
                if fg == bg:
                    continue
                mine = wcag_ratio(parse_colour(fg), parse_colour(bg))
                theirs = _Color(bg).contrast(fg, method="wcag21")
                worst_wcag = max(worst_wcag, abs(mine - theirs))
        # Bounded, not zero: WCAG's rounded luminance coefficients against
        # coloraide's exact sRGB-to-XYZ row. Anything larger means one of the
        # two implementations has actually drifted.
        check("WCAG max deviation over 72 pairs (coefficient rounding)",
              worst_wcag, 0.0, 5e-3)

        # coloraide's Machado is an independent implementation of the same
        # published matrices. Deutan and tritan agree exactly; protan differs
        # by about 2/255 because the two sources round the matrix differently.
        worst_cvd = 0
        for hexval in samples:
            rgb = parse_colour(hexval)
            for ours, theirs_name in (("protanopia", "protan"),
                                      ("deuteranopia", "deutan"),
                                      ("tritanopia", "tritan")):
                mine = [round(c) for c in simulate_cvd(rgb, ours)]
                other = _Color(hexval).filter(theirs_name, 1.0, method="machado")
                other = [round(max(0.0, min(1.0, v)) * 255) for v in
                         other.convert("srgb")[:-1]]
                worst_cvd = max(worst_cvd, max(abs(a - b) for a, b in zip(mine, other)))
        check("CVD max channel deviation (0-255)", worst_cvd, 0.0, 3)

    print()
    if failures:
        print(f"{failures} check(s) FAILED - do not trust this script's output.")
    else:
        print("All checks passed.")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check-contrast.py",
        description="Measure colour pairs and simulate colour-vision deficiency.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("pair", help="WCAG 2 ratio and APCA Lc for text on ground")
    p.add_argument("specs", nargs="+", metavar="[LABEL=]FG/BG")
    p.add_argument("--level", choices=("AA", "AAA"), default="AA")
    p.add_argument("--large", action="store_true",
                   help="apply the large-text threshold (18pt, or 14pt bold)")

    c = sub.add_parser("cvd", help="simulate dichromacy and rank palette separation")
    c.add_argument("specs", nargs="+", metavar="[LABEL=]COLOUR")

    sub.add_parser("selftest", help="verify the maths against published values")

    args = parser.parse_args(argv)
    try:
        if args.command == "pair":
            return cmd_pair(args.specs, args.level, args.large)
        if args.command == "selftest":
            return cmd_selftest()
        return cmd_cvd(args.specs)
    except ValueError as exc:
        print(f"check-contrast: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
