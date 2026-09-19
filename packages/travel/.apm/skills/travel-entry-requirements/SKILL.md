---
name: "travel-entry-requirements"
description: "Establishes whether a traveller may enter a destination: visa and travel-authorisation requirements, passport validity rules, the Schengen 90-in-180 rolling count, vaccination and health entry rules, customs limits, and government travel advisories. ALWAYS invoke before any cross-border trip is recommended, priced or booked, and whenever asked about visas, entry rules, passport validity, border requirements or how long someone may stay. Do not answer any of this from recall — entry rules change without notice, differ per nationality on the same trip, and a wrong answer is a refused boarding or a refused entry at the border, not a corrigible mistake. Keywords: visa, visa-free, entry requirements, travel authorisation, ESTA, ETA, ETIAS, EES, passport validity, six month rule, Schengen, 90 days, 180 days, overstay, vaccination, yellow fever, customs, duty free, travel advisory, border."
metadata:
  provenance:
    authoritativeSpec:
      - https://home-affairs.ec.europa.eu/policies/schengen-borders-and-visa_en
---

# Travel Entry Requirements

The highest-harm area in travel planning. Everything else costs money when it
goes wrong; this costs the trip, at the airport, with no recovery.

So it is narrow and source-bound by design.

## The rule that governs everything here

**Never answer from recall.** Not the visa requirement, not the passport
validity rule, not the vaccination list, not whether an authorisation scheme
has started yet.

Entry rules change without notice and without press coverage, schemes get
postponed repeatedly, and requirements differ by nationality, by purpose of
travel, by length of stay, and sometimes by port of entry. A remembered answer
that was correct once is the most dangerous output available here, because it
is confident and specific and wrong.

Retrieve it. Date it. Say where it came from.

## What has to be established

Work through these for **each traveller**, because a party with mixed
nationalities faces different rules on the same itinerary.

1. **Nationality and document.** Which passport, expiring when. Dual nationals
   choose which to travel on, and it changes the answer.
2. **Authorisation.** Visa, visa on arrival, or an electronic authorisation.
   Check whether a scheme is actually in force, not merely announced.
3. **Passport validity.** Many destinations require validity beyond the return
   date — commonly six months, and for Schengen three months beyond the
   intended departure. Check the issue date too: some states refuse passports
   issued more than ten years ago even if unexpired.
4. **Length of stay permitted**, and how it is counted. See below for Schengen.
5. **Transit.** A change of planes can need its own authorisation even airside.
   Check every country touched, not just the destination.
6. **Health.** Required vaccinations, certificates, and any entry health
   declaration.
7. **Customs.** What may be carried in, and cash declaration thresholds.
8. **Advisory.** The traveller's own government's advice for the destination,
   which also bears on insurance validity.

## Sources

See [official-sources.md](references/official-sources.md).

Two sources, always, and only these two kinds:

- **The destination government's own page**, which is authoritative on what it
  will admit.
- **The traveller's own foreign ministry**, which is authoritative on advisories
  and often states the destination's requirements for that nationality
  specifically.

Airline, OTA and aggregator pages are convenient summaries and are frequently
out of date. They may be used to find the rule; they may not be cited as the
rule.

## Schengen 90-in-180

Do not compute this by hand or by reasoning. Run the script:

```bash
python3 scripts/schengen_window.py check 2026-01-10:2026-01-24 2026-03-02:2026-03-20
python3 scripts/schengen_window.py plan 2026-01-01:2026-03-01 --enter 2026-09-10 --days 21
```

Both entry and exit days count as whole days present. The window rolls — it is
not an allowance that resets — so a stay can breach in the middle and come back
under by its end, which is why `plan` tests every day rather than the last.
`selftest` runs offline.

The script is arithmetic only. It covers the short-stay rule and knows nothing
about visas, residence permits, national long-stay visas or the bilateral
agreements that exempt some nationalities.

## Answering

- **Date every answer.** "As of <date>, checked against <source>." A rule
  without a date cannot be trusted later, and these answers get re-read weeks
  after they were written.
- **Give the source URL**, so the traveller can verify it themselves. They
  should.
- **State it per traveller** where the party is mixed.
- **Say what you could not establish.** An unreachable source is an open
  question, not a clear result.
- **Set a re-check point.** Entry rules move between planning and departure.
  Name a date — typically a week or two out — and say what to re-check.
- **Never soften a hard requirement.** If a passport does not meet the validity
  rule, say it will not be accepted, not that it "may" be an issue.

## Scope

This skill establishes requirements. It is not immigration advice, it cannot
predict an officer's decision, and for anything beyond a straightforward
tourist or business visit — residence, work, study, long stays, prior refusals,
criminal record questions — the answer is to consult the destination's
consulate, said plainly rather than guessed around.
