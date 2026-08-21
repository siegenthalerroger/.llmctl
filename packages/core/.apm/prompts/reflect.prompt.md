---
name: "reflect"
description: "Reflects on the current conversation and folds the learnings back into the steering files that produced them, tracing a file to its real source when it arrived from a plugin marketplace rather than this repo. ALWAYS invoke when asked to self-improve, capture a lesson, or stop a mistake from recurring after a conversation went wrong. Do not edit steering files ad hoc and never write a fix into an installed copy — route every improvement through this prompt to the source the copy was packed from."
agent: agent
---

Reflect on this conversation. Abstract and generalize the learnings by recognising where additional guidance was required and where mistakes were made.

**Every fix lands in a source file, never in an installed copy.** An installed copy is overwritten by the next install or update, so a lesson written into one disappears with no error and no trace — and the mistake returns. Establish where a file actually comes from (Steps 2–3) before editing it.

## Steps

1. **Name the learnings.** For each one, identify the customization file that should have prevented it and what type it belongs in — a skill for knowledge or a task, an instruction only to force a skill to load, a prompt for an entry point, a hook for a deterministic guardrail. Prefer a skill.

2. **Classify each target file by its path**, using the path it was actually loaded from:

   | Path shape | What it is | Where the fix goes |
   | --- | --- | --- |
   | `.llmctl/packages/*/.apm/…` or `.llmctl/.apm/…` | source | edit here |
   | `.apm/…` in the working repository | project-scoped source | edit here |
   | `.claude/…`, `.agents/…`, `.github/…`, `.codex/…` | deploy mirror | edit the `.apm/` source it was deployed from |
   | `apm_modules/…` | vendored APM dependency | upstream — Step 3 |
   | a plugin install directory | marketplace bundle | upstream — Step 3 |

   When unsure, look for the enclosing `.claude-plugin/plugin.json` or `apm.lock.yaml`. Either one means you are inside a generated bundle, not a source tree.

3. **Trace a bundled file back to the repository it was authored in.** Follow the chain, reading the artifact named at each hop — do not guess a repository from a plugin's name:

   1. Walk up from the file to the bundle root: the directory holding `.claude-plugin/plugin.json`. That file names the plugin and its version.
   2. Read the bundle's `apm.yml` for the source package's name and author, and its `apm.lock.yaml` for the `repo_url` and `resolved_commit` of every dependency packed into it. A file that came from a dependency is attributed there.
   3. Find the marketplace that supplied the bundle and read its `.claude-plugin/marketplace.json` entry, whose `source` points at the git repository behind it.
   4. **The marketplace repository is generated output.** Its bundles are rewritten wholesale on every release, so a change committed there is discarded silently. Follow it to the workspace it is packed *from* — never open a pull request against the marketplace itself.
   5. Read the file's own frontmatter in that workspace. A `metadata.provenance.adaptedFrom` entry means the content was adapted from somewhere else again; that URL is the last hop, and the one worth fixing when the problem is in the original rather than in the adaptation.

4. **Decide where the fix lands**, and say which you chose and why:
   - **Ours to change** — the trace ends in a repository you can commit to. Fix it at the source and note that the consuming install needs an update to pick it up.
   - **Someone else's** — raise it upstream (issue or pull request), and record the workaround locally so the lesson is not lost while you wait.
   - **Shadow it** — when upstream is unresponsive or the change is specific to how you use it, adapt the file into `.llmctl` and record `metadata.provenance.adaptedFrom` with the upstream `license` and a `fidelity` that matches how much you took.

5. **Make the change.** Load `meta.instructions.md` and the `meta-*` skill for the file type you are editing if the meta package is installed; both carry the structure and description rules this repo enforces. Use a subagent to create or substantially rewrite a file, and edit directly when the insertion point is known. Generalize — do not record what should have been done this one time.

## Output

- One line per learning: what went wrong, the file that now prevents it, and where in the chain that file lives.
- For anything traced past this repository: the upstream, the hop it was found at, and whether it was raised, shadowed, or deferred.
- Nothing at all when the conversation produced no generalizable lesson. A rule added for a mistake that has happened once costs more than it saves.
