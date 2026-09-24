# Tool Inventory

Resolve this at runtime, per trip. Never work from a stored list of named integrations — directories change constantly, and what is worth connecting depends on the destination, not on a table written months ago.

## The method

**1. Establish the capabilities this trip needs.** Four, usually:

| Capability | Needed when |
|---|---|
| Lodging | Always |
| Long-haul transport | Always — flights, rail, ferry as the geography dictates |
| Activities and tickets | Timed-entry attractions, tours, events |
| Local movement | Transfers, city transport, car hire |

Plus, for this package specifically, holiday and event data — which **destination-calendar** covers with its own scripted sources and needs no integration.

**2. Check what is already reachable.** Which of those capabilities do the tools in this session already serve?

**3. For each gap, search rather than recall.** If the session offers a way to search for connectors, integrations or servers — most do — query it for the capability that is missing, in the traveller's own terms. Surface what comes back and let the traveller decide what to connect.

**4. Say what you fell back to.** Where a gap stays open, web search is the fallback. It is a legitimate answer and a weaker one: no live availability, no real prices, no booking. Name that limitation in the output rather than letting a searched estimate read like a quoted fare.

## Why the search, not a list

A stored list of integrations is wrong in three ways at once: it goes stale as directories change, it is generic where the need is destination-specific — a tours integration matters in Rome and not during a trade-fair week in Hannover — and it pushes the traveller toward whatever was fashionable when the list was written rather than what serves this trip.

## Declared servers

This package declares its own search servers. They are visible as tools when running, and absent when not. Absent is normal: a stdio server needs its runtime present, and a keyed server needs its key. Neither is an error, and neither is a reason to stop — it is a reason to say what the answer is based on.

Check for their presence rather than assuming it, and when one that would have helped is missing, say which and what it would have added.

## What not to do

- Do not claim a capability that is not present. A price that came from a search result is not a quote.
- Do not enumerate every possible integration. Ask about the gaps that bear on *this* trip.
- Do not block on a missing tool. Degrade, disclose, continue.
