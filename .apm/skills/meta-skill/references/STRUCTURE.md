# Agent Skill Resource Structuring

## Example Directory Tree

```
.github/skills/my-skill/
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
