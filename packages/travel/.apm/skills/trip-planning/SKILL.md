---
name: "trip-planning"
description: "Runs a trip from a vague idea to a booked plan: intake, a mandatory destination-timing check before dates are fixed, two or three positioned options, logistics, itinerary, and a reservation tracker with deadlines. ALWAYS invoke when asked to plan, research, cost or book a trip, holiday, city break or multi-stop journey, and before recommending destinations or dates. Do not price, recommend or book anything before the timing check has run and the traveller has said what booking authority is being given — an agent that books on assumed authority spends real money on non-refundable inventory. Keywords: plan a trip, trip planning, travel planning, holiday, vacation, city break, itinerary, where should I go, when should I go, book flights, book hotel, travel budget, multi-stop, road trip, honeymoon, family holiday."
metadata:
  provenance:
    adaptedFrom:
      - url: "https://github.com/apljacob/travel-agent"
        license: CC-BY-NC-4.0
        fidelity: structural-echo
        took: "The phase sequence from discovery through positioned options to a tracked deliverable."
---

# Trip Planning

Seven phases. The second one is the point of this package, and nothing
downstream may start before it finishes.

## 0. Establish authority and tools, before anything else

Two questions, asked once, at the start.

**What may be booked?** See [booking-authority.md](references/booking-authority.md).
The three modes are research-only, plan-and-hand-off, and book-for-me. Never
infer this from enthusiasm; ask.

**What can this session actually reach?** See [tool-inventory.md](references/tool-inventory.md).
Work out which capabilities the trip needs and which are unserved, then search
for what could fill the gap rather than reciting a list. Say plainly when a
capability is missing and the answer is coming from web search instead.

## 1. Intake

Get the constraints before the ideas. [intake.md](references/intake.md) has the
question set — ask in one batch, skip what the request already answered, and
stop at what changes the plan.

The two that most often go unasked: **who holds which passports** (it decides
the entry-requirements work) and **what the dates can actually flex by** (it
decides whether phase 2 can act on a finding).

## 2. Timing check — the gate

Run the **destination-calendar** skill for every candidate destination across
the candidate window. It is not optional and not a background nicety.

Nothing proceeds until this returns: no pricing, no shortlisting, no
availability checks, no bookings. A finding is only useful while the dates can
still move.

If the traveller's dates are immovable, run it anyway — the verdict changes
from "shift the dates" to "book now, and here is what to book first".

## 3. Shape two or three options

Not one recommendation, and not a menu of ten. Each option carries:

- What it is, and who it suits
- What it costs, roughly, and what drives that
- What it gives up against the others
- Any timing finding from phase 2 that bears on it

Position them against each other. "Cheaper but a 90-minute transfer each way"
is a decision the traveller can make; "great value" is not.

## 4. Logistics

Transport, accommodation and entry requirements, in that order, because each
constrains the next.

- **Entry requirements** go through the **travel-entry-requirements** skill.
  Never answer visa, passport-validity or vaccination questions from recall.
- **Transport**: use the servers this package declares where they are running.
  Compare metasearch against a direct fare before concluding.
- **Accommodation**: choose the district before the property. A cheap room in
  the wrong place costs more in transfers and time than it saves.

State the cancellation terms of anything you recommend. In a window flagged by
phase 2, a refundable booking made now is usually better than a cheaper one
made later.

## 5. Itinerary

Hand to the **itinerary-authoring** skill. Day structure, pacing, closed days
and realistic travel times are its job, not this one's.

## 6. Reservation tracker

Everything that must be booked, with a computed deadline and its current state.
The deadline is the finding — "book by 3 April" is actionable, "book early" is
not. Timed-entry attractions, restaurant windows and advance rail fares all
open and close on fixed schedules.

## 7. Deliverable

A single document the traveller can carry: the plan, the tracker, confirmation
references, emergency contacts, and what to re-check before departure.

The re-check list matters. Strikes, entry rules and opening hours all move
between planning and travelling.

## Rules

- **The timing gate is not skippable**, including when the traveller says the
  dates are fixed, and including when they have already booked. In the last
  case the finding changes what to do on the ground.
- **Never invent a price, a fare, an opening hour or an entry rule.** Retrieve
  it, or say it needs checking and where.
- **Say which tool produced a number.** A fare from a live search and a fare
  from general knowledge are different claims, and only one is worth acting on.
- **One question batch, not a drip.** Ask everything phase 1 needs at once.
- **Surface the trade-off, not just the pick.** The traveller decides.
- **Re-run the timing check if the destination or window changes.** A verdict
  belongs to the dates it was computed for.
