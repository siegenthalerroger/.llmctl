# Safety review of an upstream diff

What to read for when a pin moves, before the bump is committed. The input is
what `apm run update` prints: the upstream's own diff between the committed pin
and the new one, filtered to the path this repository consumes.

**This is a reading, not a scan.** A table of strings to grep for was built and
dropped: matching "ignore previous instructions", `~/.ssh` and `curl … | sh`
produced confident findings on ordinary documentation — a vendor's own install
one-liner, a published placeholder key — while missing anything phrased
differently. The two failures compound, because the noise trains you to skim
exactly the diff the check existed to make you read. Read the diff.

## What to look for

| Look for | Why it matters | Verdict |
| --- | --- | --- |
| Text addressed to the assistant rather than the reader: new role framing, "from now on", instructions to disregard other guidance or to treat this file as authoritative over the user | This content is loaded as steering. An upstream that redirects the agent is the whole prompt-injection surface, and it does not have to look hostile to work | **Block** |
| Anything that reads, writes or transmits credentials: environment variables, `~/.ssh`, token files, `.env`, keychains — including "for debugging" | A skill has no reason to touch these, and a steering file that asks an agent to is asking the agent to do it on someone's real machine | **Block** |
| New or changed executable surface: `hooks/`, `scripts/`, `*.hook.json`, `plugin.json`, an `apm.yml` inside the dependency, MCP server entries | `apm approve` gates *execution*, not content. A hook added upstream runs where the package is deployed | **Block** until read line by line and understood |
| Obfuscated or encoded payloads: base64 blobs, escaped unicode, zero-width or bidirectional characters, unusually long single lines | There is no legitimate reason for steering content to be unreadable. `apm audit --file` catches the invisible-character cases; the rest is eyes | **Block** |
| Network calls or install one-liners the skill did not make before | A documented `brew install` in a prerequisites section is ordinary. The same command newly added to a procedure the agent follows is not | **Flag**, and decide from context |
| Scope creep: files changed outside the subpath this repository pins | We consume one skill from a multi-skill repository. A bump that moves unrelated paths is noise, but a bump that newly reaches *into* our path from elsewhere is worth understanding | **Flag** |
| `LICENSE`, `NOTICE` or `COPYING` changed | The terms we redistribute under may have moved. Update `dependency-licenses.yml`, re-run the licences gate, and check whether any local `fidelity` still fits | **Flag**, and fix before committing |
| Prose, examples, formatting, typo fixes, new sections that teach rather than instruct | This is what an upstream update normally is | **Fine** |

## How to record it

Whatever the verdict, say what you read and what you concluded. A bump committed
with "reviewed, no findings" and no sign of what was reviewed is the same as an
unreviewed bump the next time someone asks.

For a block, quote the hunk, name the row above that it matches, and leave the
pin at its committed value. For a flag, say what you decided and why.
