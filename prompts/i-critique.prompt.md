---
name: i-critique
description: Evaluate design from a UX perspective, assessing visual hierarchy, information architecture, emotional resonance, cognitive load, and overall quality with quantitative scoring, persona-based testing, and actionable feedback. Use when the user asks to review, critique, evaluate, or give feedback on a design or component.
argument-hint: "[AREA=<value>]"
agent: agent
license: Apache-2.0
metadata:
  provenance:
    adaptedFrom: "https://github.com/pbakaus/impeccable/blob/main/source/skills/critique/SKILL.md"
---

Conduct a holistic design critique, evaluating whether the interface actually works - not just technically, but as a designed experience. Think like a design director giving feedback.

## MANDATORY PREPARATION

Use the frontend-design skill for design principles, anti-patterns, and the context gathering protocol. If no design context exists yet, run i-teach-impeccable first. Additionally gather what the interface is trying to accomplish.

If any of that context is still unclear after reviewing the current thread and codebase, ask the user directly before proceeding.

## Phase 1: Design Critique

Evaluate the interface across these dimensions:

### 1. AI Slop Detection (CRITICAL)

**This is the most important check.** Does this look like every other AI-generated interface from 2024-2025?

Review the design against ALL the **DON'T** guidelines in the frontend-design skill - they are the fingerprints of AI-generated work. Check for the AI color palette, gradient text, dark mode with glowing accents, glassmorphism, hero metric layouts, identical card grids, generic fonts, and all other tells.

**The test**: If you showed this to someone and said "AI made this," would they believe you immediately? If yes, that's the problem.

### 2. Visual Hierarchy
- Does the eye flow to the most important element first?
- Is there a clear primary action? Can you spot it in 2 seconds?
- Do size, color, and position communicate importance correctly?
- Is there visual competition between elements that should have different weights?

### 3. Information Architecture & Cognitive Load
- Is the structure intuitive? Would a new user understand the organization?
- Is related content grouped logically?
- Are there too many choices at once? Count visible options at each decision point - if there are more than 4, flag it.
- Is the navigation clear and predictable?
- Is complexity revealed only when needed, or dumped on the user upfront?

### 4. Emotional Journey
- What emotion does this interface evoke? Is that intentional?
- Does it match the brand personality?
- Does it feel trustworthy, approachable, premium, playful - whatever it should feel?
- Would the target user feel "this is for me"?
- Is the most intense moment positive? Does the experience end well?
- Where are the frustration valleys, anxiety spikes, or confidence cliffs?

### 5. Discoverability & Affordance
- Are interactive elements obviously interactive?
- Would a user know what to do without instructions?
- Are hover/focus states providing useful feedback?
- Are there hidden features that should be more visible?

### 6. Composition & Balance
- Does the layout feel balanced or uncomfortably weighted?
- Is whitespace used intentionally or just leftover?
- Is there visual rhythm in spacing and repetition?
- Does asymmetry feel designed or accidental?

### 7. Typography as Communication
- Does the type hierarchy clearly signal what to read first, second, third?
- Is body text comfortable to read?
- Do font choices reinforce the brand and tone?
- Is there enough contrast between heading levels?

### 8. Color with Purpose
- Is color used to communicate, not just decorate?
- Does the palette feel cohesive?
- Are accent colors drawing attention to the right things?
- Does it work for colorblind users in a meaningful way?

### 9. States & Edge Cases
- Empty states: Do they guide users toward action, or just say "nothing here"?
- Loading states: Do they reduce perceived wait time?
- Error states: Are they helpful and non-blaming?
- Success states: Do they confirm and guide next steps?

### 10. Microcopy & Voice
- Is the writing clear and concise?
- Does it sound like a human - the right human for this brand?
- Are labels and buttons unambiguous?
- Does error copy help users fix the problem?

## Phase 2: Present Findings

### Design Health Score

Score Nielsen's 10 heuristics 0-4 and present them as a table:

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | ? | [specific finding or "--"] |
| 2 | Match System / Real World | ? | |
| 3 | User Control and Freedom | ? | |
| 4 | Consistency and Standards | ? | |
| 5 | Error Prevention | ? | |
| 6 | Recognition Rather Than Recall | ? | |
| 7 | Flexibility and Efficiency | ? | |
| 8 | Aesthetic and Minimalist Design | ? | |
| 9 | Error Recovery | ? | |
| 10 | Help and Documentation | ? | |
| **Total** | | **??/40** | **[rating band]** |

Be honest with scores. A 4 means genuinely excellent. Most real interfaces score in the 20-32 range.

### Anti-Patterns Verdict

**Start here.** Pass/fail: Does this look AI-generated? List specific tells from the frontend-design skill. Be brutally honest.

### Overall Impression

A brief gut reaction - what works, what doesn't, and the single biggest opportunity.

### What's Working

Highlight 2-3 things done well. Be specific about why they work.

### Priority Issues

The 3-5 most impactful design problems, ordered by importance.

For each issue, tag it with **P0-P3 severity**:
- **[P?] What**: Name the problem clearly
- **Why it matters**: How this hurts users or undermines goals
- **Fix**: What to do about it
- **Suggested command**: Which existing command could address it

### Persona Red Flags

Auto-select 2-3 personas relevant to this interface type. If project instructions already contain a `## Design Context` section from i-teach-impeccable, generate 1-2 project-specific personas from that context as well.

For each selected persona, walk through the primary user action and list the specific red flags they would hit.

### Minor Observations

Quick notes on smaller issues worth addressing.

## Phase 3: Ask the User

After presenting findings, ask 2-4 targeted questions based on what you actually found. Keep the questions concrete and tied to the critique.

Ask along these lines when relevant:
1. **Priority direction**: Which problem category matters most right now?
2. **Design intent**: Was the current tone intentional, or should it feel different?
3. **Scope**: Fix the top 3, all issues, or only the critical issues?
4. **Constraints**: Is any area off-limits?

If the findings are straightforward, skip the questions and go directly to the action summary.

## Phase 4: Recommended Actions

Present a prioritized action summary reflecting the user's priorities and scope.

1. **`/i-command`** - Brief description of what to fix, with the relevant context from the critique
2. **`/i-command`** - Brief description of what to fix, with the relevant context from the critique

Only recommend commands that exist in this repo. Order by the user's stated priorities first, then by impact. End with `/i-polish` if any fixes were recommended.

Tell the user they can run the commands one at a time, all at once, or in any order they prefer, and that they can re-run `/i-critique` after fixes to see whether the score improves.

**Remember**:
- Be direct - vague feedback wastes everyone's time
- Be specific - name exact elements and interactions
- Say what's wrong AND why it matters to users
- Give concrete suggestions
- Prioritize ruthlessly
- Don't soften criticism