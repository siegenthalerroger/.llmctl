# Implementing Colour Decisions

How a derived palette survives contact with code: layering tokens so meaning is separable from value, encoding the decision instead of its frozen result, and using the colour features the platform already has.

## Contents

- [Layer the tokens](#layer-the-tokens)
- [Encode the decision, not the result](#encode-the-decision-not-the-result)
- [The token graph](#the-token-graph)
- [CSS Color 4 and 5](#css-color-4-and-5)
- [Where colour systems rot](#where-colour-systems-rot)

## Layer the tokens

Put a semantic layer between raw values and the places that consume them. Three levels, in every language — CSS custom properties, Swift enums, design-token JSON, whatever the target uses:

| Level | Holds | Example |
|---|---|---|
| **Reference** | Concrete colours | `ref.red = #f00` |
| **Semantic** | Meaning mapped onto them | `semantic.warning = ref.red` |
| **Component** | Consumption, via semantic tokens only | `button.bg = semantic.warning` |

Raw colour literals belong in reference definitions, conversions and diagnostics. **A literal in a component is a bug that has not surfaced yet** — it is the line nobody updates when the theme changes.

This is not a CSS pattern. It is the same three levels wherever colour is stored, and the reason is always the same: theming means swapping the middle layer without touching the outer ones.

## Encode the decision, not the result

The generator hands over primitives. The *mapping* onto roles is where designs rot, because a manual mapping frozen into literals cannot re-derive when anything upstream moves.

Emit the rule:

- `text := bestContrastWith(surface, palette)` — recomputes when the palette regenerates.
- `accent := mostVivid(palette, { against: surface, minContrast: 4.5, not: [danger, success] })` — vividness gated by readability, with role-reserved tokens excluded so brand cannot eat a semantic colour.
- `surface := nth(ramp, 0)`, `text := nth(ramp, -1)` — roles pinned to *position*, so they survive regenerating the ramp with a different number of stops.
- `hover := mix(accent, ink, 12%)` — or an adaptive `shade(surface)` that flips darken/lighten by the input's lightness, so it does not collapse on a dark theme.

Each of these answers "why is this value what it is" without anyone having to remember. That is the whole point: a palette you can regenerate is a palette you can revise.

## The token graph

For anything larger than a single page, a flat token dump stops being enough. Prefer a graph: references, semantic roles, derived functions, and scope inheritance.

What the graph buys that a dump does not:

- **Dependents recompute.** Change the ground and every derived foreground follows.
- **Decisions are auditable.** You can ask why a value won, rather than reading a hex and guessing.
- **Accessibility becomes a stored constraint** rather than a test that runs after the fact.
- **Multi-platform export is mechanical**, because the meaning was never encoded in the syntax.

## CSS Color 4 and 5

On the web the platform does perceptual colour natively. Reach for these before adding a library — the browser re-runs them, so the decision stays live rather than being resolved once at build time.

| Need | Syntax |
|---|---|
| Perceptual colour | `oklch(70% 0.12 250)`, `oklab(0.7 -0.1 0.1)` |
| Wide gamut | `color(display-p3 1 0.2 0.3)` |
| Mixing without a grey middle | `color-mix(in oklab, blue 30%, white)` |
| Hue path on a cylinder | `color-mix(in oklch longer hue, …)` |
| Derive from a base | `oklch(from var(--brand) l c h / 0.5)` |
| A shade with no second hex | `oklch(from var(--brand) calc(l * 0.9) c h)` |
| Light and dark without a media query | `light-dark(white, black)`, with `color-scheme: light dark` |
| Gamut targeting | `@media (color-gamut: p3) { … }` |
| Gradient in a chosen space | `linear-gradient(in oklch, red, blue)` |

**Relative colour syntax is the piece that changes how palettes are written.** `oklch(from …)` means a hover state, a border tint and a disabled variant are all derivations of one token rather than four unrelated values that drift apart.

Broadly supported in evergreen browsers; relative colour syntax is the newest of these, so verify against current support for the audience rather than assuming.

## Where colour systems rot

- **A hex pasted into a component.** It will not update, and nobody will find it.
- **A dark theme built by inverting.** See the main skill — it is re-derived, never flipped.
- **A semantic role spent on brand.** Cheap to reserve up front, expensive to reclaim.
- **A ramp whose roles are pinned to names rather than positions.** Regenerate it with a different stop count and every reference is off by one.
- **Contrast checked once, at the end.** At the tiers body text needs, passing by luck is rare enough that this always means rework.
