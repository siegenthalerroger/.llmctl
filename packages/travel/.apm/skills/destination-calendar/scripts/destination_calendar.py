#!/usr/bin/env python3
"""List the public holidays, school holidays and observances at a destination.

  python destination_calendar.py report GB 2026-06-20 2026-07-10
  python destination_calendar.py holidays CH 2026-07-28 2026-08-04
  python destination_calendar.py school DE 2026-04-01 2026-04-20 --subdivision DE-BY
  python destination_calendar.py sources
  python destination_calendar.py selftest

`report` is the one to run: it merges both sources into one dated table and
annotates the dates that move prices -- bridge days and the long weekends they
create, and school-holiday spans, which drive family demand harder than public
holidays do and which most holiday APIs do not carry at all.

Two sources, both keyless, because neither covers the whole job:

  Nager.Date          200+ countries, public holidays only. The global floor.
                      Served from nagerholidays.com; the older date.nager.at
                      host is no longer the documented one.
  OpenHolidays API    European coverage, public *and* school holidays, with
                      subdivisions -- which matters because German Land and
                      Swiss canton calendars diverge by weeks.

Outside Europe `school` returns nothing and says so; that is a coverage gap to
state in the answer, not a finding of "no school holidays".

What this script deliberately does not do is find events. A Grand Prix, a Pride
weekend, a trade fair and a rail strike are what actually wreck a booking
window, and no keyless API ranks them. That half is the skill's search
protocol; this half is the half a machine can be trusted with.

Exits 2 when a source fails, so a silent skip is impossible -- an empty table
because the network was down must never read as a clean window.

Python 3.9+. Runs on the standard library alone.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, timedelta

# Nager serves the same v3 API from two hosts. The first is what the project's
# README documents today; the second is the long-standing one still in wide use.
# Both are tried, because a CDN in front of either can refuse a request that the
# other answers, and a refused host must not look like a country with no holidays.
NAGER_HOSTS = (
    "https://nagerholidays.com/api/v3",
    "https://date.nager.at/api/v3",
)
OPENHOLIDAYS = "https://openholidaysapi.org"
TIMEOUT = 20

# Identify honestly. The default urllib agent string is blocked by CDNs on sight,
# which is the likeliest reason a keyless public API returns 403; the fix is to
# say who is calling, not to impersonate a browser.
USER_AGENT = "llmctl-destination-calendar/1.0 (+https://github.com/siegenthalerroger/.llmctl)"

# The host that last answered, so a run does not re-pay for a dead one.
_preferred_host = ""

# Weekday -> the working day that gets taken off to bridge to the weekend.
# Tuesday holidays pull Monday, Thursday holidays push Friday. Wednesday
# bridges either way and is reported as ambiguous rather than guessed.
BRIDGE = {1: "Monday before", 3: "Friday after"}

PUBLIC, SCHOOL, OBSERVANCE = "public", "school", "observance"


class SourceError(RuntimeError):
    """A data source could not be reached or did not return usable JSON."""


@dataclass
class Event:
    """One dated thing, spanning a single day or a range."""

    start: date
    end: date
    kind: str
    name: str
    scope: str
    source: str

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    def overlaps(self, start: date, end: date) -> bool:
        return self.start <= end and self.end >= start


# --- Fetching --------------------------------------------------------------


def fetch_json(url: str) -> object:
    """GET a URL and parse JSON, turning every failure into SourceError."""
    request = urllib.request.Request(
        url, headers={"Accept": "application/json", "User-Agent": USER_AGENT}
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            payload = response.read()
    except urllib.error.HTTPError as exc:
        raise SourceError(f"{url} -> HTTP {exc.code}") from exc
    except (urllib.error.URLError, OSError) as exc:
        raise SourceError(f"{url} -> {exc}") from exc
    try:
        return json.loads(payload)
    except ValueError as exc:
        raise SourceError(f"{url} -> not JSON: {exc}") from exc


def host_order() -> tuple:
    """Nager hosts to try, the one that last answered first."""
    if _preferred_host in NAGER_HOSTS:
        return (_preferred_host,) + tuple(h for h in NAGER_HOSTS if h != _preferred_host)
    return NAGER_HOSTS


def nager_fetch(path: str, fetch=fetch_json) -> object:
    """GET `path` from the first Nager host that answers.

    Raises a SourceError naming *every* host tried and what each returned. One
    host and one status is not enough to act on: the whole point of a fallback
    is knowing whether the service is down or just one edge of it.
    """
    global _preferred_host
    attempts = []
    for host in host_order():
        try:
            payload = fetch(f"{host}/{path}")
        except SourceError as exc:
            attempts.append(str(exc))
            continue
        _preferred_host = host
        return payload
    _preferred_host = ""
    raise SourceError("no Nager host answered -- " + "; ".join(attempts))


def nager_public(country: str, start: date, end: date) -> list:
    """Public holidays from Nager.Date, one call per year the window touches."""
    events = []
    for year in range(start.year, end.year + 1):
        rows = nager_fetch(f"publicholidays/{year}/{country}")
        if not isinstance(rows, list):
            raise SourceError(f"Nager.Date returned {type(rows).__name__}, expected a list")
        for row in rows:
            events.extend(parse_nager_row(row))
    return [event for event in events if event.overlaps(start, end)]


def probe(fetch=fetch_json) -> list:
    """Which sources answer right now, as (label, url, status) rows."""
    year = date.today().year
    checks = [(f"Nager.Date  {host}", f"{host}/publicholidays/{year}/CH") for host in NAGER_HOSTS]
    checks.append(
        (
            f"OpenHolidays  {OPENHOLIDAYS}",
            f"{OPENHOLIDAYS}/PublicHolidays?countryIsoCode=CH&languageIsoCode=EN"
            f"&validFrom={year}-01-01&validTo={year}-01-31",
        )
    )
    rows = []
    for label, url in checks:
        try:
            payload = fetch(url)
        except SourceError as exc:
            detail = str(exc)
            rows.append((label, "unreachable", detail.split(" -> ", 1)[-1]))
            continue
        count = len(payload) if isinstance(payload, list) else "?"
        rows.append((label, "ok", f"{count} row(s)"))
    return rows


def parse_nager_row(row: dict) -> list:
    """One Nager row -> zero or one Event. Types decide public vs observance."""
    try:
        day = date.fromisoformat(row["date"])
    except (KeyError, TypeError, ValueError):
        return []
    types = row.get("types") or []
    kind = PUBLIC if "Public" in types or "Bank" in types else OBSERVANCE
    # Upstream is renaming `counties` to `subdivisionCodes`; accept both so the
    # rename does not silently turn every regional holiday into a nationwide one.
    counties = row.get("subdivisionCodes") or row.get("counties") or []
    scope = "nationwide" if row.get("global", True) else ", ".join(counties) or "regional"
    name = row.get("localName") or row.get("name") or "unnamed"
    english = row.get("name")
    if english and english != name:
        name = f"{name} ({english})"
    return [Event(day, day, kind, name, scope, "Nager.Date")]


def openholidays(
    endpoint: str, country: str, start: date, end: date, subdivision: str = ""
) -> list:
    """Public or school holidays from OpenHolidays, which takes a date range."""
    query = {
        "countryIsoCode": country,
        "languageIsoCode": "EN",
        "validFrom": start.isoformat(),
        "validTo": end.isoformat(),
    }
    if subdivision:
        query["subdivisionCode"] = subdivision
    rows = fetch_json(f"{OPENHOLIDAYS}/{endpoint}?{urllib.parse.urlencode(query)}")
    if not isinstance(rows, list):
        raise SourceError(f"OpenHolidays returned {type(rows).__name__}, expected a list")
    kind = SCHOOL if endpoint == "SchoolHolidays" else PUBLIC
    return [event for event in (parse_openholidays_row(row, kind) for row in rows) if event]


def parse_openholidays_row(row: dict, kind: str):
    """One OpenHolidays row -> an Event, or None when the dates are unusable."""
    try:
        start = date.fromisoformat(row["startDate"])
        end = date.fromisoformat(row["endDate"])
    except (KeyError, TypeError, ValueError):
        return None
    return Event(
        start,
        end,
        kind,
        pick_name(row.get("name")),
        openholidays_scope(row),
        "OpenHolidays",
    )


def pick_name(names) -> str:
    """OpenHolidays names are a list of {language, text}; prefer English."""
    if not isinstance(names, list) or not names:
        return "unnamed"
    for entry in names:
        if isinstance(entry, dict) and entry.get("language") == "EN":
            return entry.get("text") or "unnamed"
    first = names[0]
    return (first.get("text") if isinstance(first, dict) else None) or "unnamed"


def openholidays_scope(row: dict) -> str:
    if row.get("nationwide"):
        return "nationwide"
    codes = [
        sub.get("code") or sub.get("shortName") or ""
        for sub in (row.get("subdivisions") or [])
        if isinstance(sub, dict)
    ]
    return ", ".join(code for code in codes if code) or "regional"


# --- Analysis --------------------------------------------------------------


def bridge_note(event: Event) -> str:
    """Why a single-day public holiday costs more than one day.

    A holiday landing next to the weekend takes the whole block out of the
    working week -- Monday and Friday holidays make a three-day weekend on
    their own, Tuesday and Thursday ones do it via a bridge day most of the
    country also takes. That is the difference between a normal rate and a
    peak one, and it is invisible in a bare list of dates.
    """
    if event.kind != PUBLIC or event.days != 1:
        return ""
    weekday = event.start.weekday()
    if weekday in BRIDGE:
        return f"bridge day likely ({BRIDGE[weekday]}) -> four-day weekend"
    if weekday == 2:
        return "midweek; bridges either side are possible"
    if weekday in (0, 4):
        return "three-day weekend"
    return "falls on the weekend; look for a substitute day"


def sort_key(event: Event):
    return (event.start, event.kind, event.name)


def merge(*groups) -> list:
    """Combine source groups, dropping same-day same-name duplicates.

    Nager and OpenHolidays both carry public holidays for European countries,
    and the overlap is near-total. Keep the first occurrence so the table shows
    a country's holidays once.
    """
    seen = set()
    merged = []
    for event in sorted([e for group in groups for e in group], key=sort_key):
        fingerprint = (event.start, event.end, event.kind, event.name.split(" (")[0].lower())
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        merged.append(event)
    return merged


def render(events: list, start: date, end: date) -> str:
    """The dated table, plus the one-line reading of the window."""
    if not events:
        return f"No holidays recorded between {start} and {end}."
    rows = [("DATES", "DAY", "KIND", "NAME", "SCOPE", "NOTE")]
    for event in events:
        when = event.start.isoformat()
        if event.days > 1:
            when = f"{when}..{event.end.isoformat()} ({event.days}d)"
        rows.append(
            (
                when,
                event.start.strftime("%a"),
                event.kind,
                event.name,
                event.scope,
                bridge_note(event),
            )
        )
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]
    lines = ["  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)).rstrip() for row in rows]
    lines.insert(1, "  ".join("-" * width for width in widths))
    return "\n".join(lines)


def summarise(events: list) -> str:
    counts = {}
    for event in events:
        counts[event.kind] = counts.get(event.kind, 0) + 1
    school_days = sum(event.days for event in events if event.kind == SCHOOL)
    parts = [f"{counts.get(kind, 0)} {kind}" for kind in (PUBLIC, SCHOOL, OBSERVANCE)]
    tail = f"; {school_days} school-holiday days in range" if school_days else ""
    return f"{', '.join(parts)}{tail}."


# --- Self-check ------------------------------------------------------------


def selftest() -> int:
    """Offline assertions on everything that is not a network call."""
    failures = []

    def check(label, got, want):
        if got != want:
            failures.append(f"{label}: got {got!r}, want {want!r}")

    # Bridge classification, the bit most likely to be quietly wrong.
    # 2026-08-01 is a Saturday, 2026-12-25 a Friday, 2026-12-24 a Thursday.
    def note_for(iso):
        return bridge_note(Event(date.fromisoformat(iso), date.fromisoformat(iso), PUBLIC, "x", "y", "z"))

    check("saturday", note_for("2026-08-01"), "falls on the weekend; look for a substitute day")
    check("friday", note_for("2026-12-25"), "three-day weekend")
    check("thursday", note_for("2026-12-24"), "bridge day likely (Friday after) -> four-day weekend")
    check("tuesday", note_for("2026-12-29"), "bridge day likely (Monday before) -> four-day weekend")
    check("wednesday", note_for("2026-12-30"), "midweek; bridges either side are possible")

    # A multi-day span is never a bridge day, whatever weekday it starts on.
    span = Event(date(2026, 4, 2), date(2026, 4, 17), SCHOOL, "Easter", "DE-BY", "OpenHolidays")
    check("span days", span.days, 16)
    check("span note", bridge_note(span), "")

    # Overlap is inclusive at both ends -- an event ending on the arrival date
    # still closes the shops on the arrival date.
    check("overlap start", span.overlaps(date(2026, 4, 17), date(2026, 4, 20)), True)
    check("overlap after", span.overlaps(date(2026, 4, 18), date(2026, 4, 20)), False)
    check("overlap before", span.overlaps(date(2026, 3, 1), date(2026, 4, 2)), True)

    # Nager row parsing: types decide kind, `global` decides scope.
    rows = parse_nager_row(
        {"date": "2026-08-01", "localName": "Nationalfeiertag", "name": "National Day",
         "types": ["Public"], "global": True}
    )
    check("nager kind", rows[0].kind, PUBLIC)
    check("nager scope", rows[0].scope, "nationwide")
    check("nager name", rows[0].name, "Nationalfeiertag (National Day)")
    observance = parse_nager_row(
        {"date": "2026-02-14", "localName": "Valentine's Day", "name": "Valentine's Day",
         "types": ["Observance"], "global": False, "counties": ["GB-ENG"]}
    )
    check("observance kind", observance[0].kind, OBSERVANCE)
    check("observance scope", observance[0].scope, "GB-ENG")
    check("bad row", parse_nager_row({"date": "not-a-date"}), [])

    # OpenHolidays name selection prefers English, falls back to the first.
    check("name EN", pick_name([{"language": "DE", "text": "Ostern"}, {"language": "EN", "text": "Easter"}]), "Easter")
    check("name fallback", pick_name([{"language": "FR", "text": "Paques"}]), "Paques")
    check("name empty", pick_name([]), "unnamed")
    check("scope nationwide", openholidays_scope({"nationwide": True}), "nationwide")
    check(
        "scope subdivision",
        openholidays_scope({"nationwide": False, "subdivisions": [{"code": "DE-BY"}]}),
        "DE-BY",
    )

    # The subdivisionCodes rename must not read as nationwide.
    renamed = parse_nager_row(
        {"date": "2026-08-01", "localName": "Kantonsfeiertag", "name": "Cantonal Day",
         "types": ["Public"], "global": False, "subdivisionCodes": ["CH-ZH"]}
    )
    check("subdivisionCodes scope", renamed[0].scope, "CH-ZH")

    # Host fallback: the second host answers when the first refuses, and the
    # winner is remembered so the next call does not re-pay for the dead one.
    global _preferred_host
    _preferred_host = ""
    tried = []

    def only_second(url):
        tried.append(url)
        if url.startswith(NAGER_HOSTS[0]):
            raise SourceError(f"{url} -> HTTP 403")
        return [{"date": "2026-01-01", "localName": "x", "name": "x", "types": ["Public"], "global": True}]

    payload = nager_fetch("publicholidays/2026/CH", fetch=only_second)
    check("fallback returns data", isinstance(payload, list), True)
    check("fallback tried both", len(tried), 2)
    check("fallback remembers winner", _preferred_host, NAGER_HOSTS[1])
    check("preferred host goes first", host_order()[0], NAGER_HOSTS[1])

    # When every host refuses, the error names every one of them.
    _preferred_host = ""

    def all_refuse(url):
        raise SourceError(f"{url} -> HTTP 403")

    try:
        nager_fetch("publicholidays/2026/CH", fetch=all_refuse)
    except SourceError as exc:
        message = str(exc)
        check("error names host 1", NAGER_HOSTS[0] in message, True)
        check("error names host 2", NAGER_HOSTS[1] in message, True)
        check("error keeps the status", "403" in message, True)
    else:
        failures.append("nager_fetch should have raised when every host refused")
    check("failure clears preference", _preferred_host, "")

    # The probe reports a refusal as a row rather than raising.
    rows = probe(fetch=all_refuse)
    check("probe covers every source", len(rows), len(NAGER_HOSTS) + 1)
    check("probe marks unreachable", rows[0][1], "unreachable")

    # Merge drops the duplicate a two-source lookup always produces.
    day = date(2026, 12, 25)
    a = Event(day, day, PUBLIC, "Christmas Day", "nationwide", "Nager.Date")
    b = Event(day, day, PUBLIC, "Christmas Day (Christmas)", "nationwide", "OpenHolidays")
    c = Event(day, day, SCHOOL, "Christmas break", "nationwide", "OpenHolidays")
    check("merge dedupes", len(merge([a], [b, c])), 2)

    if failures:
        print("selftest FAILED", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1
    print("selftest passed")
    return 0


# --- CLI -------------------------------------------------------------------


def window(args) -> tuple:
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    if end < start:
        raise SystemExit("end date is before start date")
    if end - start > timedelta(days=400):
        raise SystemExit("window longer than 400 days; narrow it")
    return start, end


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("holidays", "school", "report"):
        child = sub.add_parser(name)
        child.add_argument("country", help="ISO 3166-1 alpha-2 code, e.g. GB, CH, DE")
        child.add_argument("start", help="YYYY-MM-DD")
        child.add_argument("end", help="YYYY-MM-DD")
        child.add_argument("--subdivision", default="", help="e.g. DE-BY, CH-ZH")
    sub.add_parser("sources")
    sub.add_parser("selftest")
    args = parser.parse_args(argv)

    if args.command == "selftest":
        return selftest()

    if args.command == "sources":
        rows = probe()
        width = max(len(label) for label, _, _ in rows)
        for label, status, detail in rows:
            print(f"{label.ljust(width)}  {status:<12} {detail}")
        return 0 if any(status == "ok" for _, status, _ in rows) else 2

    country = args.country.strip().upper()
    start, end = window(args)

    try:
        if args.command == "holidays":
            events = nager_public(country, start, end)
        elif args.command == "school":
            events = openholidays("SchoolHolidays", country, start, end, args.subdivision)
        else:
            school = []
            try:
                school = openholidays("SchoolHolidays", country, start, end, args.subdivision)
            except SourceError as exc:
                print(f"note: school holidays unavailable for {country} ({exc})", file=sys.stderr)
            events = merge(nager_public(country, start, end), school)
    except SourceError as exc:
        print(f"source failed: {exc}", file=sys.stderr)
        print("Treat this as UNKNOWN, not as a clear window.", file=sys.stderr)
        return 2

    print(f"{country} {start} .. {end}")
    print(render(events, start, end))
    print()
    print(summarise(events))
    if args.command == "report":
        print("Holidays only. Events -- sport, festivals, trade fairs, strikes -- are not in here.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
