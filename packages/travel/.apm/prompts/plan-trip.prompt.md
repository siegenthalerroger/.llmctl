---
name: "plan-trip"
description: "Starts a trip plan: intake, the destination timing check before dates are fixed, positioned options, logistics, itinerary and a dated reservation tracker. ALWAYS invoke when asked to plan or research a trip from a standing start. Do not use to answer a single narrow travel question — load the relevant skill directly instead."
agent: agent
argument-hint: "where, when, who with, and anything already decided"
# Claude Code fields
skills: ['trip-planning']
---

Plan a trip from the brief supplied with this command: `${input:brief:where, when, who with, and anything already decided}`

Load the [trip-planning skill](../skills/trip-planning/SKILL.md) and follow its phases. The order is load-bearing — in particular, the timing check in phase 2 runs before anything is priced, shortlisted or booked.

## Before the first question

Settle two things, per that skill:

1. **Booking authority** — research only, plan and hand off, or book for me. Ask; do not infer it.
2. **What this session can reach** — which travel capabilities are served by tools that are actually running, and which will fall back to web search. Search for what could fill a gap rather than reciting known integrations.

## Then

- **Intake** in one batch, skipping whatever the brief already answers.
- **Run `destination-calendar`** for every candidate destination across the candidate window. Report its verdict before going further.
- **Two or three positioned options**, each with its trade-off stated.
- **Logistics** — entry requirements via `travel-entry-requirements`, then transport, then accommodation.
- **Itinerary** via `itinerary-authoring`.
- **Reservation tracker** with computed dates, sorted by deadline.

State which tool produced each price, fare and opening hour. Where something came from general search rather than a live lookup, say so rather than letting an estimate read as a quote.
