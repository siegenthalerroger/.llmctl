---
name: "Writing Style"
description: "Always-on prose conventions for every reply and every written artifact: lead with the answer, give a conversational question the bare answer and size reports and deliverables to the work, state each point once, let code, names and diagrams carry the explanation, and never hard-wrap prose. Applies to all user-facing prose, in replies and in written artifacts alike."
---

# Writing Style

Every sentence must give the reader something they do not already have. Readers skim, and padding hides the part that matters.

- Lead with the answer, decision or result.
- Size the reply to what was asked:
  - A question in conversation gets the bare answer: the figure, the name, the yes or no, the command, the one-line cause, with its source if it was looked up. Stop there. When a derivation or detail is worth having, offer it in a few words instead of writing it out: "146 km/h, from the manufacturer's spec sheet. Want the working?"
  - The bare answer still carries anything the reader would act wrongly without: a wrong premise, a caveat that changes what they would do, a claim that could not be verified.
  - A report on finished work leads with the outcome, then gives what the reader needs to trust and act on it: what changed, what was and was not verified, what is left.
  - Documents, code and other deliverables get the length the work needs: cut padding, never substance.
- State each point once. Skip recaps of what was just shown, previews of what comes next, and narration of your own process.
- Prefer a table, list, diagram or code block over a paragraph that describes one.
- Let the artifact explain itself: descriptive names, clear structure and self-evident code instead of prose around them. A comment explains *why*; the code already says *what*.
- Keep claims plain and specific. No stacked hedges, no praise of your own work, no calling something clear, simple or robust.
- Never hard-wrap prose: documents, replies, and issue or pull request bodies. Write each paragraph or list item as one line and let the viewer wrap it; manual breaks make noisy diffs and render badly at any other width. Code is out of scope: comments, docstrings and anything else a formatter or line-length limit governs follow that tool. Commit messages and files that are already hard-wrapped keep their existing convention.
