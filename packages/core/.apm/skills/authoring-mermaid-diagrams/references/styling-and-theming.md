# Styling and Theming

How to make a diagram legible everywhere it will be read, and when not to style it at all. Grounded in [`docs/config/theming.md`](https://github.com/mermaid-js/mermaid/blob/develop/docs/config/theming.md).

## Contents

- [The default is no styling](#the-default-is-no-styling)
- [The dark-mode failure](#the-dark-mode-failure)
- [Themes](#themes)
- [Theme variables](#theme-variables)
- [Per-node styling with classDef](#per-node-styling-with-classdef)
- [Link styling](#link-styling)
- [look and layout](#look-and-layout)

## The default is no styling

Mermaid's built-in themes already handle contrast, borders and fonts, and they adapt to the host. Every colour you add is a decision the host can no longer make on the reader's behalf. Add styling only when a colour **carries information** the shapes and labels do not — a failure path, a boundary of ownership, a deprecated component.

When it does carry information, carry it twice: colour **and** a label, shape or line style. A reader with a colour-vision deficiency, or one printing to greyscale, gets nothing from hue alone.

## The dark-mode failure

GitHub, GitLab and VS Code render the same fenced block against light or dark page chrome depending on the reader's setting, and they pick the Mermaid theme to match. A hardcoded colour does not move with them.

The rule that prevents this is narrow and absolute:

> **Never set `fill:` without `color:`, or `color:` without `fill:`.**

Set both and the pair is self-contained: whatever the surrounding theme does, that node's text sits on that node's background at the contrast you chose. Set one and the other is inherited from a theme you cannot see — light grey text on a light grey box, or black text on a near-black box.

```
%% wrong — text colour comes from whichever theme the reader's browser picked
classDef risky fill:#ffd7d7

%% right — the pair is legible on its own terms
classDef risky fill:#7f1d1d,stroke:#450a0a,color:#ffffff
```

`stroke:` matters less, but an unset stroke on a saturated fill tends to vanish against a dark background — set it a shade or two darker than the fill.

## Themes

Five built-in themes: `default`, `neutral` (built for greyscale printing), `dark`, `forest`, `base`. Select one per diagram in frontmatter:

```
---
config:
  theme: neutral
---
```

**Only `base` accepts `themeVariables`.** Setting them under any other theme is silently ignored — a common reason a "custom theme" appears to do nothing.

## Theme variables

Recolour a whole diagram consistently, without touching a single node, by overriding the roots that everything else derives from:

```
---
config:
  theme: base
  themeVariables:
    darkMode: true
    primaryColor: "#1e3a5f"
    primaryTextColor: "#f4f7fb"
    primaryBorderColor: "#0f1f33"
    lineColor: "#8fa8c4"
---
```

- **Hex only.** `red` is not understood; `#ff0000` is.
- Most variables are *calculated* from a few roots — `secondaryColor`, `tertiaryColor`, `mainBkg`, all the `*BorderColor` and `*TextColor` values derive from `primaryColor` and `background`. Set the roots and let the rest follow; overriding twenty variables individually is how palettes drift out of sync.
- `darkMode: true` changes how those derivations are computed. Set it whenever the palette you are supplying is a dark one, or the derived borders and text come out wrong.
- The ones worth knowing by name: `background`, `primaryColor`, `primaryTextColor`, `primaryBorderColor`, `lineColor`, `textColor`, `mainBkg`, `noteBkgColor`, `fontFamily`, `fontSize`. Diagram-specific blocks (flowchart, sequence, gantt, ...) sit under their own headings in the upstream doc.

This is the preferred mechanism. It survives a theme switch, applies to node types you did not think about, and keeps one palette in one place.

## Per-node styling with classDef

When a *specific* node needs to stand out from its neighbours, use a class — not an inline `style` on each node.

```
flowchart LR
    ok[Charge card] --> fail[Declined]

    classDef failure fill:#7f1d1d,stroke:#450a0a,color:#ffffff
    class fail failure
```

- Declare the class once, apply it to every member. Inline `style nodeId ...` is fine for exactly one node and a maintenance problem for more than one.
- `class a,b,c myClass` applies to several at once; `nodeId:::myClass` applies inline at declaration.
- Name classes after what they *mean* (`failure`, `external`, `deprecated`), never after what they look like (`red`, `box2`). The colour will change; the meaning will not.
- Keep the palette to three or four classes. Past that, readers stop decoding it.

## Link styling

`linkStyle` addresses edges by **positional index in declaration order**:

```
linkStyle 3 stroke:#b91c1c,stroke-width:2px
```

Insert an edge above it and the styling silently lands on the wrong link. Treat `linkStyle` as a last resort — prefer distinguishing edges with the syntax itself (`-.->` for asynchronous, `==>` for a primary path) and labelling them, which is both self-describing and stable under edits.

## look and layout

```
---
config:
  look: handDrawn
  layout: elk
---
```

- `look: handDrawn` signals "sketch, not specification" — useful for a design doc in flight, wrong for reference documentation.
- `layout: elk` untangles dense graphs that `dagre` (the default) routes badly. **ELK is not bundled**: the host must register `@mermaid-js/layout-elk`. It works on mermaid.live and in an application you control; on GitHub it does not.
- Both apply to flowcharts and state diagrams only.
