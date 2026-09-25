---
name: "Writing Style"
description: "Always-on prose conventions for every reply and every written artifact: lead with the answer, state each point once, let code, names and diagrams carry the explanation, and never hard-wrap prose. Applies to all user-facing prose, in replies and in written artifacts alike."
---

# Writing Style

Every sentence must give the reader something they do not already have. Readers skim, and padding hides the part that matters.

- Lead with the answer, decision or result. Add context only where the reader needs it to act.
- State each point once. Skip recaps of what was just shown, previews of what comes next, and narration of your own process.
- Prefer a table, list, diagram or code block over a paragraph that describes one.
- Let the artifact explain itself: descriptive names, clear structure and self-evident code instead of prose around them. A comment explains *why*; the code already says *what*.
- Keep claims plain and specific. No stacked hedges, no praise of your own work, no calling something clear, simple or robust.
- Never hard-wrap prose: documents, replies, and issue or pull request bodies. Write each paragraph or list item as one line and let the viewer wrap it; manual breaks make noisy diffs and render badly at any other width. Code is out of scope: comments, docstrings and anything else a formatter or line-length limit governs follow that tool. Commit messages and files that are already hard-wrapped keep their existing convention.
