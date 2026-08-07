---
name: "design-direction"
description: "Sets the visual direction for design work by deriving palette, type and layout register from the subject, audience and medium instead of a house default, then screening the result against known AI design tells. ALWAYS invoke before producing a page, deck, document, chart, layout or identity, and whenever output is called generic, templated or AI-looking. Routes to the layout, typography, colour, identity, dataviz and presentation skills and settles precedence between them; it does not itself teach any single domain. Do not choose a colour, typeface or layout before establishing the brief this skill defines. Keywords: design direction, art direction, brief, aesthetic, style, register, visual identity, AI slop, generic design, design critique."
metadata:
  provenance:
    adaptedFrom:
      - url: "https://github.com/Vinayak-Shukla-03/anti-ai-slop"
        license: MIT
        fidelity: inspiration-only
        took: "The premise that AI design output converges on an enumerable set of defaults, so naming them is what makes them avoidable."
      - url: "https://github.com/funboy322/avoid-ai-design"
        license: MIT
        fidelity: inspiration-only
        took: "Grouping tells by the surface they appear on rather than as one flat list."
      - url: "https://github.com/github/awesome-copilot/blob/main/skills/anti-ui-slop/SKILL.md"
        license: MIT
        fidelity: inspiration-only
        took: "Fixing a design contract up front so later choices are checked against it rather than judged ad hoc."
      - url: "https://github.com/yetone/kill-ai-slop"
        license: Apache-2.0
        fidelity: inspiration-only
        took: "Screening finished output against a named tell inventory as a separate pass, not only screening the plan."
---

# Design Direction

Establishes the brief a design decision answers to, derives a direction from it, and screens the result for the defaults an agent reaches for when the brief is thin.

This skill decides *what kind of thing to make*. The domain skills decide how to make it well — see [Routing](#routing).

## Precedence

Design authority runs in one order. A lower level never overrides a higher one; it only fills what the higher one left open.

1. **What the user said.** Explicit words about look, feel, colour, type, or a reference they like win outright — including when what they ask for appears in [references/ai-tells.md](./references/ai-tells.md). A stated preference is a brief, not a mistake to correct.
2. **What the project already has.** A design system, token or theme file, brand guide, existing components, or the conventions of a sibling document. Look for these before choosing anything.
3. **What the subject implies.** Derived direction — see [Derive, don't default](#derive-dont-default).
4. **Your own defaults.** Reached only when 1–3 are all silent. This is the level where slop lives.

**If you cannot name the audience and the register from levels 1–3, ask before producing.** One question about audience, formality, or a reference they like beats a confident guess. Do not resolve the gap by producing something neutral.

## Establish the brief

Four answers, before any visual choice:

- **Audience** — who reads this, what they already know, what they need from it. "Engineers on this team" and "prospective customers" produce different work.
- **Medium** — screen, deck, print, identity, or data graphic. Decides which domain skill leads and which constraints are physically real.
- **Job** — the one thing this artefact must accomplish. If it has several, rank them.
- **Register** — how formal, how loud, how much personality the context supports.

Register is the answer most often skipped and the one that most determines whether output feels appropriate to its setting. **Utilitarian is a valid register and usually the right one.** Most requests want real typographic hierarchy, considered spacing and a deliberate palette — not a visual identity. Over-designing a runbook is as much a failure as under-designing a launch page.

## Derive, don't default

A choice is *derived* when you can point at the thing in the subject or brief that produced it. It is a *default* when the identical choice would have appeared for any other subject in the category.

Work from the subject's own world — its materials, vocabulary, instruments, era, physical artefacts, the constraints its practitioners actually work under. That world is where distinctive and *defensible* choices come from; a direction derived this way survives the question "why this and not something else."

Before building, commit the direction to specifics:

| Commit to | Concretely | Domain skill |
|---|---|---|
| Palette | 4–6 values with a stated role for each, and what the neutrals are biased toward | `colour` |
| Type | A face per role (display, body, plus a utility face where data or captions need one) and the scale | `typography` |
| Structure | The layout or sequencing concept, in one or two sentences | `layout` / `presentation` |

If you cannot state the direction that concretely, you do not have one yet. Keep this to a few lines — it is a means, not a deliverable.

## Critique the direction, then build

Read the direction back and ask one question: **would I have produced this for any other subject in this category?**

Wherever the answer is yes, that part is a default wearing a rationale. Replace it, and say what you changed and why. Run this on the plan rather than the finished artefact — revising a plan is cheap.

Then screen it against the tells for your medium: [references/ai-tells.md](./references/ai-tells.md).

> **The tells are exhausted defaults, not banned choices.** Nothing listed there is bad design; it is design that has gone invisible through repetition. Precedence level 1 overrides the list completely — when someone asks for the warm-cream editorial look, build it, and build it well. The list governs only what you reach for when nobody specified.

## Critique the artefact against the brief

After building, check the result against the brief you wrote, not against a general feeling of quality:

- Does it do the **job**, for the stated **audience**, at the stated **register**?
- Does every structural device encode something true? Numbering implies sequence; a divider implies separation; an eyebrow implies a category. Decoration shaped like structure misleads the reader.
- Is the copy written from the reader's side — naming things as they recognise them, not as the system implements them?
- Would removing any element lose information? If not, remove it.
- Do the accessibility floors hold — measured contrast, visible focus, reduced-motion support?

## Routing

| Working on | Leads | Also load |
|---|---|---|
| Web page, app screen, document layout | `layout` | `typography`, `colour` |
| Slide deck, or anything projected | `presentation` | `typography`, `colour` |
| Chart, diagram, dashboard, infographic | `dataviz` — [which one](#two-skills-can-answer-to-dataviz) | `colour` |
| Logo, mark, brand system | `identity` | `typography`, `colour` |
| Print or editorial | `layout` | `typography`, `colour` |

### When the harness ships its own design skill

Some harnesses load design skills of their own alongside this package's, and they cannot be suppressed. **They are not duplicates, and they disagree.** Never average two positions into a compromise neither would endorse — resolve by medium and by ownership.

**A built-in artifact, page or document design skill.** It owns its runtime and you follow it there without argument: content-security limits, how fonts must be embedded, how themes are switched, what the renderer supports. It does **not** replace the brief. Run [Establish the brief](#establish-the-brief) and [Derive, don't default](#derive-dont-default) once, then feed that output into its plan step rather than starting a second, parallel direction — two design plans for one artefact is how a page ends up half-derived and half-default. Where its list of AI tells is shorter than [references/ai-tells.md](./references/ai-tells.md), the longer list stands; they agree on the underlying failures.

### Two skills can answer to `dataviz`

This package depends on a `dataviz` skill, and some harnesses ship one of their own under the same name. **Identify by content, never by name** — the name may resolve to either, or the harness may namespace them, and which one you get is not something to assume.

| | Recognise it by | It leads for |
|---|---|---|
| **Editorial** | Graphical integrity, the data-ink argument, source and date disclosure; cites Tufte, Wong, Franchi | Print, report, editorial, anything whose point is a finding |
| **Product** | A build procedure: mark specs, a colour formula with a runnable validator, interaction and dashboard rules | Screen and product UI |

Then apply whichever case you are in:

- **Only one is visible.** Use it, whichever it is. Its guidance is sound in its own domain and the gaps are covered below — this is not a problem to work around.
- **Both are visible.** Read each one's opening lines, match them against the table, and let **the medium** pick the leader. Where they contradict directly — legends versus direct labelling, whether a pie chart is admissible, bar geometry, shading nominal categories, how far apart series colours must sit — the medium decides outright, per the rule above.
- **Either way, `colour` covers what neither does.** The editorial skill has no categorical/sequential/diverging vocabulary and no colour-vision-deficiency method; the product one is absent outside its own harness. Load `colour` for encoding choice and colour-vision safety regardless of medium, and follow the leader's accessibility floors where they are stricter.

## Gotchas

- **"Clean, modern, minimal" is not a brief.** Those words describe the absence of a decision, and accepting them as direction lands you at precedence level 4 while believing you are at level 1. Ask for the audience and the job instead.
- **Matching an existing system beats improving on it.** A page consistent with a mediocre design system serves its reader better than a better-looking page that fights it. Raise the improvement as a separate proposal.
- **Accessibility is not part of the register.** Contrast floors, focus states and reduced-motion support hold at every register. They are not what "utilitarian" trades away, and not what "expressive" earns an exemption from.
- **Spend boldness in one place.** Hierarchy is made of contrast, and contrast requires restraint around it. Several competing bold moves read as noise, and noise is itself a tell.
- **Do not let the brief become the output.** Establishing direction is a short internal step. Producing paragraphs of design rationale in place of the artefact is a failure of this skill, not a use of it.

## References

- [references/ai-tells.md](./references/ai-tells.md) — the tell inventory, grouped by medium. Read the section for the medium you are working in; the tells differ sharply between screen, deck, print, identity and data graphics.
