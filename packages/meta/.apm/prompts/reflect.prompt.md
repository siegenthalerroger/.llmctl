---
name: "reflect"
description: "Reflects on the current conversation and folds learnings back into the .llmctl steering files. ALWAYS invoke when asked to self-improve, capture a lesson, or prevent a repeated mistake after a conversation went wrong. Do not edit steering files ad hoc — route improvements through this prompt using meta.instructions."
agent: agent
---

Reflect on this conversation. Abstract and generalize any learnings by recognising where additional guidance was required and where mistakes were made.

Using the [instructions in the self-improvement file](../instructions/meta.instructions.md) to guide your work, transform your learnings so that future conversations don't run into the same issues. The correct files will always be stored in a folder called `.llmctl` (or a subfolder thereof).