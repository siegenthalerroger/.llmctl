---
metadata:
  provenance:
    authoritativeSpec:
      - "https://nausika.app"
      - "https://api.windy.com/point-forecast/docs"
      - "https://api.windy.com/point-forecast/pricing"
---

# Sources and Fallbacks

Use the first source that answers the question, and name it next to the figure. When a server is not in the session's tool list, go to the next row instead of reporting a dead end.

| Need | First | Then | Last |
| --- | --- | --- | --- |
| Marinas, ports, anchorages near a point | `nausika` place search | Navily web API (below) | Cruising guides and wikis, web search |
| Ratings, review text, facility scores | Navily review API | Navily page; `nausika` ratings tool | Review sites, with dates |
| Marine forecast at a point | `nausika` marine forecast; `windy` with a Professional key | Navily `meteo` endpoint | Public forecast sites, read manually |
| Sea route and distance | `nausika` routing | Chart plotter or the skipper's chart | Straight-line distance, flagged as such |
| Berth and mooring prices | Operator or port-authority price list | Navily `priceTonight` (bookable ports only) | Third-party tables, with their year |
| Land services (parking, supermarket, fuel, taxi) | A places search tool with a location bias | Web search | — |
| Reverse geocoding a coordinate | `nausika` geocode | Places search | Leave the coordinate unnamed |

## nausika

Remote server at `https://mcp.nausika.app`. The client handles OAuth on first use. It covers routing, marine forecast up to seven days, tides and curated places. Coverage is strongest in the Mediterranean, and forecasts, tides and geocoding work anywhere.

- **Read the place schema tool first.** Filter names have differed between calls (`type` versus `types`), and a wrong filter returns nothing rather than an error.
- **Place data is map-derived.** Phone numbers and names come from OpenStreetMap; treat them as leads to confirm. A boat-profile tool exists, so check it before asking the skipper for dimensions.
- It is not a parking or shore-services directory. Use a places search for those.

## windy

Local stdio server (`windy-mcp-server`) wrapping Windy's Point Forecast API, with a selectable model for weather and waves.

- **A Testing-tier key returns randomly shuffled, modified data by design.** Use output only when the skipper confirms a Professional key. Otherwise state that the Windy figures are not real and use another source.
- Wave forecasts are capped shorter than weather forecasts. Pick the model deliberately and name it in the answer.

## Navily web API (no MCP server)

Navily has no published API and no MCP server. Its website calls the JSON endpoints below, and a plain web fetch reaches them. They are undocumented and can change without notice: on an error, fall back to fetching the HTML page. Observed working 2026-10-16.

| Endpoint | Returns |
| --- | --- |
| `GET https://www.navily.com/api/search?q=<name>` | `results.ports[]` and `results.moorings[]` with `id`, `name`, `coordinate`, `rating`, `counts.comments`. Ports add `maxLength`, `maxDraft`, `multihullFriendly`, `mooringTypes`, `phone`, `bookable` and, when bookable, `priceTonight`. Anchorages add `seabeds`, `protections` (wind directions), `hasMooringBuoy`, `hasDock`, `hasHawser`, `authorizeAnchor`, `hasBeach`, `hasShop` and `hasWaterSource` |
| `GET https://www.navily.com/api/ports/get-reviews?id=<id>&page=1&per_page=20&sort=recent&lang=en` | `reviews[]`: `message.original` (and `translated`), `createdAt`, `note` (the reviewer's rating), and `author.boat` (`length`, `isMultihull`) |
| `GET https://www.navily.com/api/moorings/get-reviews?id=<id>&…` | The same, for anchorages and buoy fields |
| `GET https://www.navily.com/port/<id>/meteo` · `/mouillage/<id>/meteo` | Hourly forecast at the spot: wind, gusts, waves, swell, air and water temperature |
| `https://www.navily.com/port/<slug>/<id>` · `/mouillage/<slug>/<id>` | HTML page with category scores such as cleanliness and welcome. Fetch it when a score is needed that the API does not return |

- **Filter reviews by `author.boat`.** Reviews from boats of similar length, and multihull reviews for a multihull, carry most weight on spacing, depth and berth assignment. Quote the count and date range behind any summary.
- Confirm the meaning of `protections` against the page's shelter diagram before ranking on it.
- `get-items-around` endpoints exist but returned empty lists when tested; don't rely on them.

## Other sources

- **Cruising guides and wikis**: approach notes, hazards, holding and history. Note when each entry was last edited.
- **Port authorities and marina operators**: price lists and rules. They are often published only in the local language, sometimes as PDFs that block automated reading.
- **Recent forum or review posts**: season status and closures. Date every claim taken from them.
