# Diagram Type Catalogue

Every diagram type Mermaid ships, with the exact keyword that opens the block and how risky that keyword is on a renderer you do not control. Keywords verified against the diagram detectors in [`packages/mermaid/src/diagrams/*`](https://github.com/mermaid-js/mermaid/tree/develop/packages/mermaid/src/diagrams) on `develop`; prose descriptions and syntax live in [`docs/syntax/*`](https://github.com/mermaid-js/mermaid/tree/develop/docs/syntax).

## Contents

- [Reading the tier column](#reading-the-tier-column)
- [Structure and behaviour](#structure-and-behaviour) — flowchart, swimlanes, sequence, state, class, ER, C4, architecture, block, ZenUML
- [Planning and process](#planning-and-process) — gantt, kanban, timeline, gitGraph, journey, requirement, eventmodeling
- [Data and comparison](#data-and-comparison) — pie, xychart, quadrant, sankey, radar, treemap, venn, packet
- [Thinking and analysis](#thinking-and-analysis) — mindmap, treeView, wardley, cynefin, ishikawa, railroad
- [Choosing between near-neighbours](#choosing-between-near-neighbours)

## Reading the tier column

| Tier | Meaning | What to do |
| --- | --- | --- |
| **Stable** | Long-shipped, no suffix. | Use anywhere. |
| **Beta-aliased** | Both the plain and the `-beta` keyword parse on current Mermaid; the type shipped under `-beta` first. | Write the `-beta` form when the renderer is unknown — it is the spelling older embedded renderers accept. |
| **Beta-only** | The `-beta` suffix is mandatory; the plain word does not parse at all. | Recent addition. Verify against the target renderer before using in a README. |
| **External** | Not in the bundle; the host must register a separate package. | Assume it fails unless the host is known to load it. |

Beta-only types are the newest and the least widely deployed. GitHub, GitLab and IDE previews pin older Mermaid builds — a type that renders on [mermaid.live](https://mermaid.live/) can still show a parse error in a README.

## Structure and behaviour

| Type | Keyword | Tier | Answers |
| --- | --- | --- | --- |
| Flowchart | `flowchart TD` (also `graph`) | Stable | The steps, branches and loops of a process. `flowchart` is the current renderer; `graph` is the legacy alias. |
| Swimlanes | `swimlane-beta LR` | Beta-only | The same, when the point is *which actor owns which step*. |
| Sequence | `sequenceDiagram` | Stable | Who calls whom, in what order, and what comes back. |
| State | `stateDiagram-v2` | Stable | The states a thing can occupy and the events that move it. `stateDiagram` selects the older renderer — always write `-v2`. |
| Class | `classDiagram` | Stable | Types, their members, and inheritance/composition/dependency between them. |
| Entity relationship | `erDiagram` | Stable | Entities, their attributes, keys, and cardinality between them. |
| C4 | `C4Context` (also `C4Container`, `C4Component`, `C4Dynamic`, `C4Deployment`) | Stable | Where the system boundary sits and who crosses it. |
| Architecture | `architecture-beta` | Beta-aliased | What runs where — services, groups, and the edges between them. |
| Block | `block-beta` | Beta-aliased | Coarse layout when you want manual control of the grid rather than an auto-layout. |
| ZenUML | `zenuml` | **External** | Sequence interactions in a code-like notation. Needs `@mermaid-js/mermaid-zenuml` registered by the host. |

## Planning and process

| Type | Keyword | Tier | Answers |
| --- | --- | --- | --- |
| Gantt | `gantt` | Stable | When each task runs and what blocks what. |
| Kanban | `kanban` | Stable | What sits in each column of a board right now. |
| Timeline | `timeline` | Stable | What happened when, as a narrative rather than a schedule. |
| Git graph | `gitGraph` | Stable | Branching, merging and tagging strategy. |
| User journey | `journey` | Stable | How a user feels at each step, scored 1–5. |
| Requirement | `requirementDiagram` | Stable | Requirements, their satisfaction, and traceability to elements. |
| Event modeling | `eventmodeling` | Stable | Commands, events, read models and their flow through a system over time. Recent addition — verify the target renderer. |

## Data and comparison

| Type | Keyword | Tier | Answers |
| --- | --- | --- | --- |
| Pie | `pie` | Stable | Parts of one whole. Use only for a handful of slices. |
| XY chart | `xychart-beta` | Beta-aliased | A bar or line series against an axis. |
| Quadrant | `quadrantChart` | Stable | Where items land against two dimensions. |
| Sankey | `sankey-beta` | Beta-aliased | How a quantity splits and flows between stages. |
| Radar | `radar-beta` | Beta-only | One or more entities scored across several axes. |
| Treemap | `treemap-beta` | Beta-aliased | Nested proportions — size of parts within parts. |
| Venn | `venn-beta` | Beta-only | Overlap between two or three sets. |
| Packet | `packet-beta` | Beta-aliased | Bit and byte layout of a wire format. |

For anything richer than these — real axes, tooltips, many series — a chart library beats Mermaid. Mermaid's charts exist so a diagram-shaped document does not need a second toolchain.

## Thinking and analysis

| Type | Keyword | Tier | Answers |
| --- | --- | --- | --- |
| Mind map | `mindmap` | Stable | The shape of an idea space radiating from one centre. |
| Tree view | `treeView-beta` | Beta-only | A strict hierarchy as an indented tree — file trees, org charts. |
| Wardley map | `wardley-beta` | Beta-only | Where each component sits on the value chain versus its evolution. |
| Cynefin | `cynefin-beta` | Beta-only | Which domain a problem belongs to: clear, complicated, complex, chaotic. |
| Ishikawa | `ishikawa-beta` | Beta-aliased | Causes contributing to one effect — the fishbone. |
| Railroad | `railroad-ebnf-beta` (also `railroad-abnf-beta`, `railroad-peg-beta`, `railroad-beta`) | Beta-only | A grammar as a syntax diagram. Pick the variant matching the grammar notation. |

## Choosing between near-neighbours

- **Flowchart vs. sequence** — a flowchart shows *what happens next*; a sequence diagram shows *who is talking*. If participants have lifelines that matter, use sequence.
- **Flowchart vs. state** — a flowchart's boxes are actions, a state diagram's are conditions the system rests in. If the same box can be re-entered from several places and the label is a noun, it is a state.
- **Flowchart vs. swimlanes** — reach for swimlanes only when ownership is the point. Otherwise a flowchart with `subgraph` per owner stays portable across older renderers.
- **C4 vs. architecture** — C4 is about boundaries and audience (who is inside, who is outside); architecture is about deployment topology. C4 is stable, architecture is not.
- **Class vs. ER** — class diagrams model code, ER models persisted data. A table with keys and cardinality is ER even when it maps 1:1 onto classes.
- **Mind map vs. treeView** — mind maps radiate and are for exploration; treeView is a strict indented hierarchy and is for lookup.
- **Timeline vs. gantt** — timeline narrates past events; gantt schedules future work with dependencies and durations.
