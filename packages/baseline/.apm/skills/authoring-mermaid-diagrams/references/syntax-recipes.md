# Syntax Recipes

The smallest correct skeleton for each common diagram type, plus the traps that actually bite. Not a syntax reference — for the full grammar of any type, read its file under [`docs/syntax`](https://github.com/mermaid-js/mermaid/tree/develop/docs/syntax), which is the authoritative spec.

Every skeleton below omits the header block for brevity. Real diagrams still get `title`, `config:` and `accTitle`/`accDescr` — see [SKILL.md](../SKILL.md#every-diagram-gets-a-header-block).

## Contents

- [Flowchart](#flowchart)
- [Swimlanes](#swimlanes)
- [Sequence](#sequence)
- [State](#state)
- [Entity relationship](#entity-relationship)
- [Class](#class)
- [C4](#c4)
- [Architecture](#architecture)
- [Gantt](#gantt)
- [Git graph](#git-graph)
- [Mind map](#mind-map)
- [User journey](#user-journey)
- [Quadrant](#quadrant)
- [Sankey](#sankey)

## Flowchart

```
flowchart LR
    intake[/Order received/]
    check{In stock?}
    ship[Ship]
    hold[(Backorder queue)]
    done([Done])

    intake --> check
    check -->|yes| ship --> done
    check -->|no| hold
    hold -. nightly retry .-> check

    subgraph warehouse [Warehouse]
        direction TB
        ship
    end

    classDef terminal fill:#1f2933,stroke:#0b1215,color:#ffffff
    class done terminal
```

- Directions: `TB`/`TD`, `BT`, `LR`, `RL`. Set it on the first line; the layout engine cannot be argued with afterwards.
- Classic shapes: `[]` process, `()` rounded, `([])` stadium, `[()]` cylinder, `(())` circle, `{}` decision, `[//]` parallelogram, `[\\]` trapezoid, `>]` flag.
- Since v11.3 the extended form `id@{ shape: manual-file, label: "Text" }` unlocks ~30 further shapes. It is new enough that embedded renderers reject it — keep it out of anything destined for a README.
- Edge kinds: `-->` arrow, `---` line, `-.->` dotted, `==>` thick, `~~~` invisible (useful purely to nudge layout).
- Chain nodes on one line (`a --> b --> c`) for readability; declare shapes once, then wire them.
- Each extra dash asks for one more rank of separation (`a ----> b` spans three). It is a *minimum*, not a fixed length — the layout engine may still stretch a link further, so never use it to align things.
- **Trap:** the whole diagram is one namespace. An id reused inside a second `subgraph` moves that node rather than making a new one, which is how a flowchart ends up with mysteriously missing boxes.

## Swimlanes

```
swimlane-beta LR
  subgraph Customer
    request[Raise request]
  end
  subgraph Support
    triage[Triage]
  end
  request --> triage
```

- Flowchart syntax with one `subgraph` per lane; the lane title is the `subgraph` id.
- **v11.16.0+ only.** Every embedded renderer in circulation predates it. Use a plain flowchart with `subgraph` per owner unless the target is known-current.

## Sequence

```
sequenceDiagram
    autonumber
    actor U as User
    participant API
    participant DB

    U->>+API: POST /orders
    API->>+DB: INSERT order
    DB-->>-API: order_id
    alt payment authorised
        API-->>-U: 201 Created
    else declined
        API--)U: 402 Payment Required
    end
    Note over API,DB: single transaction
```

- Arrows: `->>` solid arrowhead (a call), `-->>` dashed (a return), `-x` cross (failure), `-)` open (async, no reply expected). Keep calls solid and returns dashed — readers rely on it.
- `+`/`-` on an arrow activate and deactivate the target; it is shorter and harder to unbalance than explicit `activate`/`deactivate`.
- Blocks: `alt`/`else`, `opt`, `loop`, `par`/`and`, `critical`/`option`, `break`, `rect`. All close with `end`.
- `autonumber` on line one turns messages into citable step numbers. Use it whenever prose refers to the diagram.
- `box Aqua Team Name ... end` groups participants; the colour comes **before** the description, and **hex colours do not work** there because `#` is comment syntax. Use a colour name or `transparent`.
- **Trap:** participant order is declaration order, not first-use order. Declare them left to right in the order a reader scans.

## State

```
stateDiagram-v2
    direction LR
    [*] --> Draft
    Draft --> Review: submit
    state Review {
        [*] --> Queued
        Queued --> WithReviewer: assign
        WithReviewer --> [*]
    }
    Review --> Published: approve
    Review --> Draft: reject
    Published --> [*]
    note right of Review: SLA 2 working days
```

- Always `stateDiagram-v2`. Bare `stateDiagram` selects the legacy renderer.
- `[*]` is both the start and the end pseudo-state; which one it is depends on the arrow direction.
- Long names: `state "Awaiting customer reply" as waiting`, then use `waiting` everywhere.
- `<<choice>>`, `<<fork>>` and `<<join>>` annotations give branch and concurrency nodes; `--` inside a composite state separates concurrent regions.
- **Trap:** label transitions with the *event*, not the outcome. `Draft --> Review: submit` reads correctly; `Draft --> Review: is reviewed` does not.

## Entity relationship

```
erDiagram
    CUSTOMER ||--o{ ORDER : places
    ORDER ||--|{ LINE_ITEM : contains
    PRODUCT }o--o{ LINE_ITEM : "appears in"

    CUSTOMER {
        uuid   id PK
        string email UK
        string display_name
    }
    ORDER {
        uuid    id PK
        uuid    customer_id FK
        decimal total_amount
        string  status "pending|shipped|delivered"
    }
```

- Cardinality reads outward from each entity: `|o` zero-or-one, `||` exactly-one, `}o` zero-or-more, `}|` one-or-more. Mirror the glyph on the right-hand side.
- `--` is an identifying relationship (solid), `..` non-identifying (dashed).
- Attribute lines are `type name [PK|FK|UK] ["comment"]`. Type and name are single tokens — no spaces. Everything else goes in the quoted comment.
- **Trap:** the `: label` is part of the relationship clause, not an optional extra — a relationship written without one is a parse error. Label it from the *first* entity's perspective; the reverse reading is left to the reader.

## Class

```
classDiagram
    direction LR
    class Repository~T~ {
        <<interface>>
        +find(id: string) T
        +save(entity: T) void
    }
    class OrderRepository {
        -db: Connection
        +find(id: string) Order
    }
    Repository <|.. OrderRepository : implements
    OrderRepository "1" --> "*" Order : returns
    note for OrderRepository "Wraps the primary replica only"
```

- Relations: `<|--` inheritance, `..|>` realisation, `*--` composition, `o--` aggregation, `-->` association, `..>` dependency, `--` plain link. The arrowhead sits at the *parent* end.
- Visibility prefixes: `+` public, `-` private, `#` protected, `~` package.
- Generics use tildes: `Repository~T~`, `List~Order~`.
- **Trap:** model the design, not the codebase. A class diagram that lists every field is a worse reference than the source file it duplicates.

## C4

```
C4Context
    title Order platform — system context

    Person(shopper, "Shopper", "Buys things")
    System(shop, "Shop", "Catalogue, cart, checkout")
    System_Ext(psp, "Payment provider", "Authorises cards")
    SystemDb(warehouse, "Warehouse system", "Stock and dispatch")

    Rel(shopper, shop, "Browses and buys", "HTTPS")
    Rel(shop, psp, "Authorises payment", "REST")
    Rel(shop, warehouse, "Reserves stock", "AMQP")

    UpdateLayoutConfig($c4ShapeInRow="3")
```

- The element set widens by level: `Person`/`System` for context, `Container`, `Component`, and `_Ext`/`_Boundary` variants below. Pick one level per diagram.
- Every `Rel` takes a verb and, ideally, a protocol — the protocol is what makes a C4 diagram worth more than a box drawing.
- **Trap:** C4 layout is barely steerable. `UpdateLayoutConfig($c4ShapeInRow=...)` and declaration order are the only levers; if the result is unreadable, cut elements rather than fight it.

## Architecture

```
architecture-beta
    group vpc(cloud)[Production VPC]

    service gateway(internet)[Gateway] in vpc
    service api(server)[API] in vpc
    service store(database)[Postgres] in vpc

    gateway:R --> L:api
    api:B --> T:store
```

- Edges name the port on each side: `source:R --> L:target` leaves the source's right edge and enters the target's left. Getting these wrong is the usual cause of tangled output.
- **Only five icons ship**: `cloud`, `database`, `disk`, `internet`, `server`. Any other name needs an iconify pack registered by the host and renders as an empty box everywhere else.
- `junction` nodes let several edges meet cleanly; `align row` / `align column` pin coordinates when the auto-layout stacks siblings.
- **Trap:** an `align` directive that contradicts an edge's declared direction makes the layout fail outright rather than degrade.

## Gantt

```
gantt
    title Migration
    dateFormat YYYY-MM-DD
    axisFormat %b %d
    excludes weekends

    section Preparation
        Inventory      :done,   inv,  2026-09-01, 10d
        Dry run        :active, dry,  after inv,  5d
    section Cutover
        Freeze         :crit,   frz,  after dry,  2d
        Switch traffic :milestone, sw, after frz, 0d
```

- Task line: `Label :tags, id, start, duration`. Tags are any of `done`, `active`, `crit`, `milestone`.
- `after <id>` chains dependencies; `until <id>` (v10.9+) runs a task up to another's start.
- `excludes weekends` and `excludes YYYY-MM-DD` keep durations honest against a working calendar.
- **Trap:** `dateFormat` describes the *input* you write, `axisFormat` the *output* on the axis. Mixing them up silently produces a chart starting in year 2001.

## Git graph

```
gitGraph
    commit id: "init"
    branch feature/checkout
    checkout feature/checkout
    commit
    commit tag: "rc1"
    checkout main
    merge feature/checkout
    commit type: HIGHLIGHT
```

- `commit` accepts `id:`, `tag:` and `type: NORMAL|REVERSE|HIGHLIGHT`.
- `cherry-pick id: "abc"` requires the source commit to carry an explicit `id:`.
- The default trunk is `main`; rename it with `config: gitGraph: mainBranchName:` in frontmatter rather than by branching from a differently-named node.

## Mind map

```
mindmap
  root((Release 4.0))
    Scope
      Billing rewrite
      SSO
    Risks
      Vendor lead time
    Owners
      Platform
```

- Structure comes entirely from **indentation**. There is no explicit nesting syntax and no error for getting it wrong — a mis-indented line silently reparents.
- Node shapes: `[]` square, `()` rounded, `(())` circle, `))((`  bang, `)(` cloud, `{{}}` hexagon.
- Exactly one root. Two top-level nodes is a parse error.

## User journey

```
journey
    title Renewing a subscription
    section Reminder
      Receive email:      4: Customer
      Open billing page:  3: Customer
    section Payment
      Update card:        2: Customer, Support
      Confirm:            5: Customer
```

- Task line: `Label: score: Actor[, Actor]`. Score is 1 (miserable) to 5 (delighted).
- The score column is the entire point — a journey where every step scores 5 is a flowchart with extra steps.

## Quadrant

```
quadrantChart
    title Effort against impact
    x-axis Low effort --> High effort
    y-axis Low impact --> High impact
    quadrant-1 Do now
    quadrant-2 Plan
    quadrant-3 Drop
    quadrant-4 Quick wins
    Search rewrite: [0.75, 0.85]
    Dark mode: [0.2, 0.35]
```

- Point coordinates are `[x, y]` in the range 0–1. They are positions, not data — the chart is for arguing about placement, not measuring.
- Quadrants number anticlockwise from the top right.

## Sankey

```
sankey-beta

Grid,Datacentre,480
Solar,Datacentre,120
Datacentre,Compute,420
Datacentre,Cooling,180
```

- The body is plain CSV: `source,target,value`. Nodes are created implicitly by being named.
- Wrap any name containing a comma in double quotes; escape a literal quote by doubling it.
- **Trap:** flows must balance at each node or the ribbon widths mislead. Check the arithmetic before publishing.
