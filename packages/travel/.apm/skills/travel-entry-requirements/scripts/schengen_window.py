#!/usr/bin/env python3
"""Count days against the Schengen 90-in-180 rolling limit.

  python schengen_window.py check 2026-01-10:2026-01-24 2026-03-02:2026-03-20
  python schengen_window.py check 2026-01-10:2026-01-24 --on 2026-09-01
  python schengen_window.py plan  2026-01-10:2026-01-24 --enter 2026-09-10 --days 21
  python schengen_window.py selftest

Stays are `ENTRY:EXIT`, inclusive at both ends, because the rule counts the day
of entry and the day of exit as whole days present -- a lunchtime arrival and a
breakfast departure are two days, not one.

The window is rolling, not a fixed allowance that resets: on any given day you
may not have spent more than 90 days inside the 180 days ending that day. That
is why `check` reports a per-day worst case rather than a single total, and why
`plan` tests every day of a proposed stay instead of only its last -- a trip
can breach in the middle and come back under by the end.

This is arithmetic, not advice. It covers the short-stay rule for the Schengen
area only. It knows nothing about visas, residence permits, national long-stay
D visas, or the bilateral agreements that still exempt some nationalities, and
none of those change the arithmetic anyway. Border officers compute this same
number from entry and exit stamps; getting it wrong is a refused entry.

Python 3.9+. Runs on the standard library alone.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta

WINDOW = 180
ALLOWANCE = 90


class StayError(ValueError):
    """A stay could not be parsed, or its dates are the wrong way round."""


def parse_stay(text: str) -> tuple:
    """`ENTRY:EXIT` -> (entry, exit), both inclusive."""
    if ":" not in text:
        raise StayError(f"{text!r} is not ENTRY:EXIT")
    left, _, right = text.partition(":")
    try:
        entry = date.fromisoformat(left.strip())
        leave = date.fromisoformat(right.strip())
    except ValueError as exc:
        raise StayError(f"{text!r}: {exc}") from exc
    if leave < entry:
        raise StayError(f"{text!r}: exit is before entry")
    return entry, leave


def days_present(stays: list) -> set:
    """Every calendar day spent inside the area, deduplicated.

    A set rather than a sum: overlapping or touching stays must not be
    double-counted, and a traveller who re-enters on their exit day spends one
    day, not two.
    """
    present = set()
    for entry, leave in stays:
        day = entry
        while day <= leave:
            present.add(day)
            day += timedelta(days=1)
    return present


def used_on(present: set, reference: date) -> int:
    """Days used in the 180-day window ending on -- and including -- reference."""
    start = reference - timedelta(days=WINDOW - 1)
    return sum(1 for day in present if start <= day <= reference)


def worst_day(present: set, days: list) -> tuple:
    """The day in `days` with the highest usage, and that usage."""
    worst = max(days, key=lambda day: (used_on(present, day), day))
    return worst, used_on(present, worst)


def next_free_day(present: set, after: date, limit: int = 400):
    """The first day from `after` on which at least one day is available."""
    day = after
    for _ in range(limit):
        if used_on(present, day) < ALLOWANCE:
            return day
        day += timedelta(days=1)
    return None


def render_check(stays: list, reference: date) -> str:
    present = days_present(stays)
    used = used_on(present, reference)
    remaining = ALLOWANCE - used
    start = reference - timedelta(days=WINDOW - 1)
    lines = [
        f"Reference day      {reference}  (window {start} .. {reference})",
        f"Days used          {used} of {ALLOWANCE}",
        f"Days remaining     {max(remaining, 0)}",
    ]
    if remaining < 0:
        lines.append(f"OVER by {-remaining} days on this reference day.")
        free = next_free_day(present, reference)
        if free:
            lines.append(f"Back within the limit on {free}.")
    elif remaining == 0:
        lines.append("At the limit: no further day may be spent inside on this day.")
    lines.append("")
    lines.append("Stays counted (inclusive of both ends):")
    for entry, leave in sorted(stays):
        span = (leave - entry).days + 1
        lines.append(f"  {entry} .. {leave}   {span} day(s)")
    return "\n".join(lines)


def render_plan(stays: list, enter: date, length: int) -> tuple:
    """Test a proposed stay day by day. Returns (text, ok)."""
    if length < 1:
        raise SystemExit("--days must be at least 1")
    leave = enter + timedelta(days=length - 1)
    present = days_present(stays + [(enter, leave)])
    proposed = [enter + timedelta(days=offset) for offset in range(length)]
    peak_day, peak = worst_day(present, proposed)
    ok = peak <= ALLOWANCE
    lines = [
        f"Proposed stay      {enter} .. {leave}   {length} day(s)",
        f"Peak usage         {peak} of {ALLOWANCE}, on {peak_day}",
    ]
    if ok:
        lines.append(f"Fits, with {ALLOWANCE - peak} day(s) of headroom at the worst point.")
    else:
        lines.append(f"DOES NOT FIT: over by {peak - ALLOWANCE} day(s) on {peak_day}.")
        trimmed = 0
        for offset in range(length):
            candidate_leave = enter + timedelta(days=offset)
            candidate = days_present(stays + [(enter, candidate_leave)])
            window_days = [enter + timedelta(days=i) for i in range(offset + 1)]
            if worst_day(candidate, window_days)[1] <= ALLOWANCE:
                trimmed = offset + 1
        if trimmed:
            lines.append(f"The longest stay from {enter} that fits is {trimmed} day(s).")
        else:
            lines.append(f"No stay starting {enter} fits; the window is already full.")
        free = next_free_day(days_present(stays), enter)
        if free and free != enter:
            lines.append(f"Earliest entry with any allowance: {free}.")
    return "\n".join(lines), ok


# --- Self-check ------------------------------------------------------------


def selftest() -> int:
    """Offline assertions. Every case is hand-checkable."""
    failures = []

    def check(label, got, want):
        if got != want:
            failures.append(f"{label}: got {got!r}, want {want!r}")

    # Inclusive counting: 10th to 24th January is 15 days, not 14.
    stay = parse_stay("2026-01-10:2026-01-24")
    check("inclusive span", len(days_present([stay])), 15)
    check("single day", len(days_present([parse_stay("2026-05-01:2026-05-01")])), 1)

    # Overlapping stays must not double-count.
    overlapping = [parse_stay("2026-01-10:2026-01-20"), parse_stay("2026-01-15:2026-01-24")]
    check("overlap dedupe", len(days_present(overlapping)), 15)

    # The window is 180 days *including* the reference day.
    present = days_present([parse_stay("2026-01-01:2026-01-01")])
    check("window last day", used_on(present, date(2026, 1, 1) + timedelta(days=179)), 1)
    check("window past end", used_on(present, date(2026, 1, 1) + timedelta(days=180)), 0)

    # A full 90 days is at the limit, not over.
    ninety = [(date(2026, 1, 1), date(2026, 1, 1) + timedelta(days=89))]
    check("ninety span", len(days_present(ninety)), 90)
    check("ninety used", used_on(days_present(ninety), date(2026, 1, 1) + timedelta(days=89)), 90)

    # One more day breaches.
    ninety_one = [(date(2026, 1, 1), date(2026, 1, 1) + timedelta(days=90))]
    check("ninety-one used", used_on(days_present(ninety_one), date(2026, 1, 1) + timedelta(days=90)), 91)

    # Planning tests every day, so a stay that breaches midway is caught even
    # though the earlier days roll out of the window by the end.
    history = [parse_stay("2026-01-01:2026-03-01")]  # 60 days
    text, ok = render_plan(history, date(2026, 3, 2), 40)
    check("midway breach caught", ok, False)
    check("breach reported", "DOES NOT FIT" in text, True)

    # And a stay that genuinely fits reports as such.
    _, ok_small = render_plan(history, date(2026, 3, 2), 20)
    check("fits", ok_small, True)

    # After a long absence the allowance is whole again.
    check("resets", used_on(days_present(history), date(2027, 1, 1)), 0)

    # Parsing rejects reversed and malformed input.
    for bad in ("2026-05-10:2026-05-01", "2026-05-10", "nonsense:2026-05-01"):
        try:
            parse_stay(bad)
        except StayError:
            pass
        else:
            failures.append(f"parse_stay({bad!r}) should have raised")

    if failures:
        print("selftest FAILED", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1
    print("selftest passed")
    return 0


# --- CLI -------------------------------------------------------------------


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    check_cmd = sub.add_parser("check")
    check_cmd.add_argument("stays", nargs="+", help="ENTRY:EXIT, inclusive")
    check_cmd.add_argument("--on", default="", help="reference day; defaults to the last exit")

    plan_cmd = sub.add_parser("plan")
    plan_cmd.add_argument("stays", nargs="*", help="past stays as ENTRY:EXIT")
    plan_cmd.add_argument("--enter", required=True, help="YYYY-MM-DD")
    plan_cmd.add_argument("--days", required=True, type=int)

    sub.add_parser("selftest")
    args = parser.parse_args(argv)

    if args.command == "selftest":
        return selftest()

    try:
        stays = [parse_stay(text) for text in args.stays]
    except StayError as exc:
        print(f"bad stay: {exc}", file=sys.stderr)
        return 1

    if args.command == "check":
        if not stays:
            print("no stays given", file=sys.stderr)
            return 1
        try:
            reference = date.fromisoformat(args.on) if args.on else max(leave for _, leave in stays)
        except ValueError as exc:
            print(f"bad --on: {exc}", file=sys.stderr)
            return 1
        print(render_check(stays, reference))
        return 0

    try:
        enter = date.fromisoformat(args.enter)
    except ValueError as exc:
        print(f"bad --enter: {exc}", file=sys.stderr)
        return 1
    text, ok = render_plan(stays, enter, args.days)
    print(text)
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
