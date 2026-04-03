---
name: i-audit
description: Run technical quality checks across accessibility, performance, theming, responsive design, and anti-patterns. Generates a scored report with P0-P3 severity ratings and actionable plan. Use when the user wants an accessibility check, performance audit, or technical quality review.
argument-hint: "[AREA=<value>]"
license: Apache-2.0
metadata:
  provenance:
    adaptedFrom: "https://github.com/pbakaus/impeccable/blob/main/source/skills/audit/SKILL.md"
---

Run systematic technical quality checks and generate a comprehensive report. Don't fix issues - document them for other commands to address.

This is a code-level audit, not a design critique. Check what is measurable and verifiable in the implementation.

## MANDATORY PREPARATION

Use the frontend-design skill for design principles, anti-patterns, and the context gathering protocol. If no design context exists yet, run i-teach-impeccable first.

If any of that context is still unclear after reviewing the current thread and codebase, ask the user directly before proceeding.

## Diagnostic Scan

Run comprehensive checks across 5 dimensions. Score each dimension 0-4 using the criteria below.

### 1. Accessibility (A11y)

**Check for**:
- **Contrast issues**: Text contrast ratios < 4.5:1 (or 7:1 for AAA)
- **Missing ARIA**: Interactive elements without proper roles, labels, or states
- **Keyboard navigation**: Missing focus indicators, illogical tab order, keyboard traps
- **Semantic HTML**: Improper heading hierarchy, missing landmarks, divs instead of buttons
- **Alt text**: Missing or poor image descriptions
- **Form issues**: Inputs without labels, poor error messaging, missing required indicators

**Score 0-4**: 0 = inaccessible (fails WCAG A), 1 = major gaps, 2 = partial coverage, 3 = good (mostly WCAG AA), 4 = excellent.

### 2. Performance

**Check for**:
- **Layout thrashing**: Reading/writing layout properties in loops
- **Expensive animations**: Animating layout properties (width, height, top, left) instead of transform/opacity
- **Missing optimization**: Images without lazy loading, unoptimized assets, missing will-change
- **Bundle size**: Unnecessary imports, unused dependencies
- **Render performance**: Unnecessary re-renders, missing memoization

**Score 0-4**: 0 = severe issues, 1 = major problems, 2 = partial optimization, 3 = good, 4 = excellent.

### 3. Theming

**Check for**:
- **Hard-coded colors**: Colors not using design tokens
- **Broken dark mode**: Missing dark mode variants, poor contrast in dark theme
- **Inconsistent tokens**: Using wrong tokens, mixing token types
- **Theme switching issues**: Values that don't update on theme change

**Score 0-4**: 0 = no theming, 1 = minimal tokens, 2 = partial consistency, 3 = good, 4 = excellent.

### 4. Responsive Design

**Check for**:
- **Fixed widths**: Hard-coded widths that break on mobile
- **Touch targets**: Interactive elements < 44x44px
- **Horizontal scroll**: Content overflow on narrow viewports
- **Text scaling**: Layouts that break when text size increases
- **Missing breakpoints**: No mobile/tablet variants

**Score 0-4**: 0 = desktop-only, 1 = major responsive failures, 2 = partial, 3 = good, 4 = excellent.

### 5. Anti-Patterns (CRITICAL)

Check against ALL the **DON'T** guidelines in the frontend-design skill. Look for AI slop tells (AI color palette, gradient text, glassmorphism, hero metrics, card grids, generic fonts) and general design anti-patterns (gray on color, nested cards, bounce easing, redundant copy).

**Score 0-4**: 0 = AI slop gallery, 1 = heavy AI aesthetic, 2 = some tells, 3 = mostly clean, 4 = no AI tells.

**CRITICAL**: This is an audit, not a fix. Document issues thoroughly with clear explanations of impact. Use other commands to fix issues after the audit.

## Generate Report

### Audit Health Score

| # | Dimension | Score | Key Finding |
|---|-----------|-------|-------------|
| 1 | Accessibility | ? | [most critical a11y issue or "--"] |
| 2 | Performance | ? | |
| 3 | Responsive Design | ? | |
| 4 | Theming | ? | |
| 5 | Anti-Patterns | ? | |
| **Total** | | **??/20** | **[rating band]** |

**Rating bands**: 18-20 Excellent, 14-17 Good, 10-13 Acceptable, 6-9 Poor, 0-5 Critical.

### Anti-Patterns Verdict

**Start here.** Pass/fail: Does this look AI-generated? List specific tells. Be brutally honest.

### Executive Summary

- Audit Health Score: **??/20** ([rating band])
- Total issues found (count by severity: P0/P1/P2/P3)
- Top 3-5 critical issues
- Recommended next steps

### Detailed Findings by Severity

Tag every issue with **P0-P3 severity**:
- **P0 Blocking**: Prevents task completion - fix immediately
- **P1 Major**: Significant difficulty or WCAG AA violation - fix before release
- **P2 Minor**: Annoyance, workaround exists - fix in next pass
- **P3 Polish**: Nice-to-fix, no real user impact - fix if time permits

For each issue, document:
- **[P?] Issue name**
- **Location**: Component, file, line
- **Category**: Accessibility / Performance / Theming / Responsive / Anti-Pattern
- **Impact**: How it affects users
- **WCAG/Standard**: Which standard it violates (if applicable)
- **Recommendation**: How to fix it
- **Suggested command**: Which command to use (prefer: /i-adapt, /i-animate, /i-clarify, /i-colorize, /i-critique, /i-delight, /i-distill, /i-extract, /i-harden, /i-normalize, /i-onboard, /i-optimize, /i-polish, /i-quieter)

### Patterns & Systemic Issues

Identify recurring problems that indicate systemic gaps rather than one-off mistakes.

### Positive Findings

Note what's working well and worth preserving or replicating.

## Recommended Actions

List recommended commands in priority order (P0 first, then P1, then P2):

1. **[P?] `/i-command`** - Brief description with the specific context to fix
2. **[P?] `/i-command`** - Brief description with the specific context to fix

**Rules**: Only recommend commands that exist in this repo. Map findings to the most appropriate command. End with `/i-polish` as the final step if any fixes were recommended.

After presenting the summary, tell the user:

> You can ask me to run these one at a time, all at once, or in any order you prefer.
>
> Re-run `/i-audit` after fixes to see your score improve.

**IMPORTANT**: Be thorough but actionable. Too many P3 issues creates noise. Focus on what actually matters.

**NEVER**:
- Report issues without explaining impact
- Provide generic recommendations
- Skip positive findings
- Forget to prioritize
- Report false positives without verification

Remember: You're a technical quality auditor. Document systematically, prioritize ruthlessly, cite specific code locations, and provide clear paths to improvement.