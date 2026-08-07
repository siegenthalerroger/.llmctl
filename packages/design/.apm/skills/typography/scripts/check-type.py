#!/usr/bin/env python3
"""Verify a type scale against the baseline grid, and the measure against the range.

  python check-type.py scale   --base 16 --ratio 2 --steps 5 --baseline 8
  python check-type.py measure --char-ratio 0.48 "mobile=16/288" "desktop=18/640"
  python check-type.py selftest

`scale` builds the three-property scale (f0, r, n) and reports, per step, the
leading that follows from it and whether that leading lands on a whole multiple
of the baseline. That check is the one SKILL.md names as the step that gets
skipped, and skipping it is what makes a system feel loose.

`measure` reports characters per line at each size/width pair, so a fluid setting
can be checked across its whole viewport range rather than at one width. Measure
is a function of size, so a setting correct at one end of the range is not
evidence about the other.

Exits 1 when any step misses the baseline or any measure falls outside 45-75, so
this can gate a build.
Python 3.9+. Runs on the standard library alone -- no font files are read, which
is why `measure` needs `--char-ratio` rather than guessing at one.

This script does arithmetic. It cannot tell you whether the typeface is right,
whether the rag is clean, or whether the hierarchy reads -- SKILL.md's remaining
verification questions are judgement and stay judgement.
"""

from __future__ import annotations

import argparse
import math
import sys

# Markdown output uses en and em dashes; Windows consoles still default to a
# legacy code page. Same reason as check-contrast.py in the colour skill.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Bringhurst's comfortable range, and the single-column ideal. SKILL.md carries
# the same table; these are the numbers the verdict column is measured against.
MEASURE_IDEAL = 66
MEASURE_MIN = 45
MEASURE_MAX = 75

# Leading starting points from SKILL.md, as ratios of the size. They are not
# constants of typography -- they follow from "larger sizes need proportionally
# less" -- so each band is overridable and the band in use is printed. The
# boundaries are expressed as multiples of the base size so they move with f0
# rather than being pinned to a particular medium's pixel values.
LEADING_BANDS = (
    # (upper bound as a multiple of f0, label, starting ratio)
    (1.25, "body", 1.5),
    (2.0, "heading", 1.25),
    (math.inf, "display", 1.05),
)


def band_for(size: float, base: float, overrides: dict[str, float]) -> tuple[str, float]:
    """The leading band a size falls in, and the ratio to start from."""
    for limit, label, ratio in LEADING_BANDS:
        if size <= base * limit:
            return label, overrides.get(label, ratio)
    raise AssertionError("unreachable: last band is unbounded")


# --- Scale ------------------------------------------------------------------


def scale_sizes(base: float, ratio: float, steps: int, lo: int, hi: int) -> list[tuple[int, float]]:
    """f_i = f0 * r^(i/n), for i in [lo, hi]."""
    if steps < 1:
        raise ValueError("--steps (n) must be at least 1")
    if ratio <= 1:
        raise ValueError("--ratio (r) must be greater than 1")
    if base <= 0:
        raise ValueError("--base (f0) must be positive")
    return [(i, base * ratio ** (i / steps)) for i in range(lo, hi + 1)]


def cmd_scale(args) -> int:
    overrides = {}
    for label, value in (("body", args.body), ("heading", args.heading),
                         ("display", args.display)):
        if value is not None:
            overrides[label] = value

    sizes = scale_sizes(args.base, args.ratio, args.steps, args.min_step, args.max_step)
    unit, baseline = args.unit, args.baseline
    rows, failures = [], 0

    for index, size in sizes:
        label, target = band_for(size, args.base, overrides)
        ideal = size * target
        # The rhythm is non-negotiable and the scale bends to serve it, so the
        # leading is snapped to the grid and the resulting ratio reported. A
        # snapped leading of zero baselines would be nonsense, hence the floor.
        multiples = max(1, round(ideal / baseline))
        snapped = multiples * baseline
        actual_ratio = snapped / size

        # Snapping always yields a whole multiple, so "lands on the grid" is
        # never the interesting question -- what matters is whether the leading
        # the reader ends up with is still the leading this band asked for.
        # Judge the resulting ratio, which is the thing anyone can see.
        error = abs(actual_ratio - target) / target
        ok = error <= args.tolerance
        failures += not ok
        rows.append((
            f"{index:+d}",
            f"{size:.2f}{unit}",
            label,
            f"{target:.2f}",
            f"{ideal:.2f}{unit}",
            f"{multiples}x{baseline:g}{unit} = {snapped:g}{unit}",
            f"{actual_ratio:.3f}",
            "ok" if ok else f"OFF by {error * 100:.0f}%",
        ))

    print(f"Scale: f0={args.base:g}{unit}, r={args.ratio:g}, n={args.steps}, "
          f"baseline={baseline:g}{unit}")
    print(f"Step ratio: {args.ratio ** (1 / args.steps):.4f}")
    print()
    print("| Step | Size | Band | Target ratio | Ideal leading | Snapped to baseline | Actual ratio | Verdict |")
    print("|---|---|---|---|---|---|---|---|")
    for r in rows:
        print("| " + " | ".join(r) + " |")

    print()
    print("Every leading above is a whole multiple of the baseline by construction.")
    print(f"The verdict is whether snapping left it within {args.tolerance * 100:.0f}% of "
          "the ratio the band")
    print("asked for -- that is the part a reader can see.")
    if failures:
        print()
        print(f"{failures} step(s) drifted past that. SKILL.md: the rhythm is "
              "non-negotiable and")
        print("the scale bends -- adjust that size or drop the step. Changing --steps (n)")
        print("moves every size at once and is usually the fix; a baseline that fights the")
        print("scale everywhere should be re-derived from the medium instead.")
    else:
        print("Every step holds its band.")
    return 1 if failures else 0


# --- Measure ----------------------------------------------------------------


CHAR_RATIO_HELP = """\
--char-ratio is the average character width of YOUR typeface as a fraction of
its font size. It is a property of the face, so there is no default worth
handing over -- a condensed grotesque and a wide humanist differ by 30%.

Measure it once, in the browser, with the real face and the real copy:

    const el = document.querySelector('p');           // a real body paragraph
    const s  = getComputedStyle(el);
    const cv = document.createElement('canvas').getContext('2d');
    cv.font = `${s.fontWeight} ${s.fontSize} ${s.fontFamily}`;
    const sample = el.textContent.trim().slice(0, 200);
    console.log(cv.measureText(sample).width / sample.length / parseFloat(s.fontSize));

Use a sample of the actual content, not a pangram: character frequency is what
the average is over, and prose is not evenly distributed."""


def cmd_measure(args) -> int:
    rows, failures = [], 0

    for spec in args.specs:
        label, _, rest = spec.partition("=")
        if not rest:
            label, rest = "", spec
        if "/" not in rest:
            raise ValueError(f"{spec!r}: expected [LABEL=]SIZE/WIDTH")
        size_text, width_text = rest.split("/", 1)
        try:
            size, width = float(size_text), float(width_text)
        except ValueError:
            raise ValueError(f"{spec!r}: size and width must be numbers "
                             "in the same unit") from None
        if size <= 0 or width <= 0:
            raise ValueError(f"{spec!r}: size and width must be positive")

        cpl = width / (size * args.char_ratio)
        if cpl < MEASURE_MIN:
            verdict, ok = f"SHORT (under {MEASURE_MIN})", False
        elif cpl > MEASURE_MAX:
            verdict, ok = f"LONG (over {MEASURE_MAX})", False
        else:
            verdict, ok = "in range", True
        failures += not ok

        # The width that would land on the single-column ideal, so a failure
        # comes with the correction rather than only the diagnosis.
        ideal_width = MEASURE_IDEAL * size * args.char_ratio
        rows.append((
            label.strip() or f"{size:g}/{width:g}",
            f"{size:g}",
            f"{width:g}",
            f"{cpl:.1f}",
            verdict,
            f"{ideal_width:.0f}",
        ))

    print(f"Character width ratio: {args.char_ratio:g} "
          f"(1 character averages {args.char_ratio:g} x the font size)")
    print()
    print("| Setting | Size | Width | Characters/line | Verdict | Width for 66 |")
    print("|---|---|---|---|---|---|")
    for r in rows:
        print("| " + " | ".join(r) + " |")

    print()
    print(f"Comfortable range is {MEASURE_MIN}-{MEASURE_MAX} characters, ideal {MEASURE_IDEAL} "
          "for a single column,")
    print("40-50 for multiple columns. Measure is a function of size, so a setting")
    print("correct at one end of a fluid range says nothing about the other -- pass")
    print("every breakpoint you actually ship.")
    if failures:
        print()
        print(f"{failures} setting(s) outside the range. Change the container width "
              "or the size;")
        print("leading follows from both, so re-run `scale` after either.")
    return 1 if failures else 0


# --- Selftest ---------------------------------------------------------------


def cmd_selftest() -> int:
    """Check the arithmetic against the published classical printer's scale."""
    failures = 0

    def check(name: str, got: float, want: float, tol: float) -> None:
        nonlocal failures
        ok = abs(got - want) <= tol
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: {got:.4f} "
              f"(expected {want:.4f} +/-{tol})")

    # The classical printer's scale is f0=12pt, r=2, n=5 -- SKILL.md and
    # references/type-scale.md both state this, so the formula must reproduce it.
    print("Classical printer's scale (f0=12pt, r=2, n=5):")
    check("step ratio = 5th root of 2", 2 ** (1 / 5), 1.148698, 1e-5)
    sizes = dict(scale_sizes(12, 2, 5, 0, 10))
    check("i=0  -> 12pt", sizes[0], 12.0, 1e-9)
    check("i=5  -> 24pt (one doubling)", sizes[5], 24.0, 1e-9)
    check("i=10 -> 48pt (two doublings)", sizes[10], 48.0, 1e-9)
    # The historical sequence rounds to 14, 16, 18, 21 over i=1..4.
    for i, want in ((1, 14), (2, 16), (3, 18), (4, 21)):
        check(f"i={i}  rounds to {want}pt", round(sizes[i]), want, 0)

    # A named ratio IS the step ratio, so n = log(2)/log(ratio) for r=2. The
    # first of these was recorded as n=4 until this check was written, which is
    # the argument for shipping the arithmetic rather than restating it.
    print("\nNamed ratios, per references/type-scale.md:")
    check("Augmented Fourth = r2 n2", 2 ** (1 / 2), 1.414214, 1e-5)
    check("Major Third ~= r2 n3", 2 ** (1 / 3), 1.259921, 1e-5)
    check("Classical step = r2 n5", 2 ** (1 / 5), 1.148698, 1e-5)
    check("n for a 1.414 step", math.log(2) / math.log(1.414214), 2.0, 1e-3)
    check("n for a 1.1487 step", math.log(2) / math.log(1.148698), 5.0, 1e-3)

    print("\nBand selection (base 16):")
    for size, want in ((16, "body"), (20, "body"), (24, "heading"),
                       (32, "heading"), (48, "display")):
        label, _ = band_for(size, 16, {})
        ok = label == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {size}px -> {label} (expected {want})")

    print("\nMeasure arithmetic:")
    # 640px wide, 16px type, 0.5 ratio -> each char is 8px -> exactly 80 chars.
    check("640/16 at ratio 0.5 = 80 chars", 640 / (16 * 0.5), 80.0, 1e-9)

    print()
    if failures:
        print(f"{failures} check(s) FAILED - do not trust this script's output.")
    else:
        print("All checks passed.")
    return 1 if failures else 0


# --- CLI --------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check-type.py",
        description="Verify a type scale against the baseline grid, and the "
                    "measure against the comfortable range.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    s = sub.add_parser("scale", help="build the scale and check it against the baseline")
    s.add_argument("--base", type=float, required=True,
                   help="f0, the body size -- the anchor everything derives from")
    s.add_argument("--ratio", type=float, default=2.0,
                   help="r, the interval ratio (default 2, the octave)")
    s.add_argument("--steps", type=int, required=True,
                   help="n, steps per interval -- the temperament")
    s.add_argument("--baseline", type=float, required=True,
                   help="the baseline unit, in the same unit as --base")
    s.add_argument("--unit", default="px", help="unit label for output (default px)")
    s.add_argument("--min-step", type=int, default=-2, help="lowest step index (default -2)")
    s.add_argument("--max-step", type=int, default=8, help="highest step index (default 8)")
    s.add_argument("--body", type=float, help="override the body leading ratio")
    s.add_argument("--heading", type=float, help="override the heading leading ratio")
    s.add_argument("--display", type=float, help="override the display leading ratio")
    s.add_argument("--tolerance", type=float, default=0.10,
                   help="how far the snapped leading may drift from its band's "
                        "ratio, as a fraction (default 0.10)")

    m = sub.add_parser("measure", help="characters per line at each size/width pair",
                       epilog=CHAR_RATIO_HELP,
                       formatter_class=argparse.RawDescriptionHelpFormatter)
    m.add_argument("specs", nargs="+", metavar="[LABEL=]SIZE/WIDTH",
                   help="size and container width, in the same unit")
    m.add_argument("--char-ratio", type=float, required=True,
                   help="average character width as a fraction of font size; "
                        "measure it for your face (see below) rather than guessing")

    sub.add_parser("selftest", help="verify the arithmetic against published scales")

    args = parser.parse_args(argv)
    try:
        if args.command == "scale":
            return cmd_scale(args)
        if args.command == "measure":
            if args.char_ratio <= 0:
                raise ValueError("--char-ratio must be positive\n\n" + CHAR_RATIO_HELP)
            return cmd_measure(args)
        return cmd_selftest()
    except ValueError as exc:
        print(f"check-type: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
