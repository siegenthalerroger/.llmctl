# Search Protocol

How to rule each event class in or out. The aim is bounded effort with an
honest account of what was not covered — not exhaustiveness, which is not
achievable.

## Bound the query before running it

Every search needs the place, the date range and the year stated explicitly.
Without the year, results skew to whichever year was most written about.

Prefer `"<city>" events June 2026` over `<city> summer events`, and always
include the month and year even when the range spans two months — run both.

## Sources, in order of reliability

1. **The venue's or organiser's own calendar.** A circuit, arena, convention
   centre or festival publishes its own dates and is the primary source.
2. **The convention centre's exhibition listing.** Almost every Messe and
   congress centre publishes a forward calendar by month. This is the highest
   value source per minute spent, because it covers the class nobody checks.
3. **The city tourism board's event calendar.** Official, date-filterable,
   and covers the municipal events no aggregator carries.
4. **The national rail operator's disruption page** for planned engineering,
   plus recent news for strike ballots.
5. **General news search**, last, and only to catch what the above missed.

Aggregators and ticket sites are useful for discovery and unreliable for dates.
Confirm anything found there against the organiser.

## A workable sweep

For a city and a date window, this is enough for a defensible answer:

- The convention centre calendar for the months in range.
- The two or three principal venues — main stadium, arena, racing circuit if
  there is one within an hour.
- The tourism board calendar, date-filtered.
- One search for `"<city>" <month> <year> festival OR marathon OR pride`.
- One search for `<country> rail strike <month> <year>` if travel involves
  trains.
- If the window includes a religious season, one check of how the destination
  observes it.

Six to eight queries. Stop there and report the boundary.

## Confirm before reporting

Three checks on anything found:

- **The year is right.** Annual events move, and search results from previous
  editions read identically.
- **The city is right.** Fairs and championships rotate between hosts.
- **The dates are the organiser's**, not an aggregator's restatement.

An unconfirmed hit is reported as unconfirmed, with the date you have and the
source you got it from.

## What to record

For each finding: what it is, exact dates, where it is within the city, which
effect axes it touches, and the source. A finding with no source cannot be
acted on, because the traveller cannot check it.

## What not to do

- Do not assert an event's dates from recall, then search only to confirm.
  Search first; confirmation bias in this domain is expensive.
- Do not treat an empty result as an absence. It is an absence *of evidence*,
  and for municipal events that is the normal case.
- Do not extend a finding across a region without checking. A fair in Düsseldorf
  does not move Cologne's rates, but it does move Neuss's.
