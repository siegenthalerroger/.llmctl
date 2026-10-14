# Agent Skill Resource Structuring

Directory layout for a skill's bundled resources, and the rule for choosing between `assets/` and `templates/`. Frontmatter is in [skill-frontmatter.md](./skill-frontmatter.md); body sections are in [skill-body.md](./skill-body.md).

## Example Directory Tree

```
.agents/skills/my-skill/
├── SKILL.md              # Required: Main instructions
├── scripts/              # Optional: Executable automation
│   ├── helper.py         # Python script
│   └── helper.ps1        # PowerShell script
├── references/           # Optional: Documentation loaded into context
│   ├── api_reference.md
│   ├── workflow-setup.md     # Detailed workflow (>5 steps)
│   └── workflow-deployment.md
├── assets/               # Optional: Static files used AS-IS in output
│   ├── baseline.png      # Reference image for comparison
│   └── report-template.html
└── templates/            # Optional: Starter code the AI agent modifies
    ├── scaffold.py       # Code scaffold the AI agent customizes
    └── config.template   # Config template the AI agent fills in
```

## Assets vs Templates: Key Distinction

**Assets** are static resources **consumed unchanged** in the output:

- A `logo.png` that gets embedded into a generated document
- A `report-template.html` copied as output format
- A `custom-font.ttf` applied to text rendering

**Templates** are starter code/scaffolds that **the AI agent actively modifies**:

- A `scaffold.py` where the AI agent inserts logic
- A `config.template` where the AI agent fills in values based on user requirements
- A `hello-world/` project directory that the AI agent extends with new features

**Rule of thumb**: If the AI agent reads and builds upon the file content → `templates/`. If the file is used as-is in output → `assets/`.

> [!NOTE]
> `templates/` is a **non-standard extension** not in the [official spec](https://agentskills.io/). The spec places template files under `assets/`. Use `templates/` when portability across implementations is not a concern.

## Provenance on bundled files

The convention is in [provenance.md](./provenance.md). This is what a skill adds for the files it ships.

- **Shared binding authority is declared once, at the widest file it binds.** A source that binds the skill's declared subject as a whole goes in `SKILL.md`. It applies to everything the skill ships (references, scripts, assets) without being repeated, and a drift review of it assesses normative changes relevant to the skill's subject wherever they land in the skill. A source that binds only one reference's narrower subject goes in that reference, and its review is scoped to that reference's subject.
- **A reference page declares its own copying.** `SKILL.md` never stands in for it: a reference that reproduces or adapts material declares the source itself, as an object entry with `license` and `fidelity`, and a top-level `license:` where the upstream's terms need one. The same URL may appear in `SKILL.md` (authority, usually bare) and in a reference (copying): those are two facts, not duplication.
- **Reference Markdown** (`references/*.md`) takes frontmatter only to declare provenance or a licence: `license` and `metadata.provenance`. Omit `name` and `description`, which identify a primitive for discovery and a reference is not one. Frontmatter is optional; a reference with nothing to declare has none.
- **Scripts, assets and templates cannot carry frontmatter, so a Markdown declaration does not cover them unless it names them.** Attribute a source-derived companion in the provenance of the Markdown file that owns it (the `SKILL.md` of the skill that ships it), as an ordinary entry in the same format, with `took` naming the companion's path and the material taken from it ("The G-4g constants, reimplemented in `scripts/check-contrast.py`"). There is no second register. The companion is licensed by the repository default for its path (MIT, not CC-BY-SA-4.0), so record only upstreams whose terms that default can carry; where they cannot, rewrite the companion instead.
