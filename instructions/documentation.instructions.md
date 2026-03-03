---
name: "Technical Documentation Instructions"
description: "Instructions for writing succinct technical documentation"
# Copilot
applyTo: "**/*.md"
# Claude Code
paths: ["**/*.md"]
---

# Documentation Guidelines

## General Guidelines

- Write clear and concise documentation.
- Reference and link to other documentation (both internal and publicly available) when possible.
- Use consistent terminology and style. Check pre-existing project documentation to match.
- Consider using diagrams and graphs as alternatives to long explanations. Use mermaid diagrams to achieve this.
- Use standard markdown. The usage of GitHub/GitLab flavored Alerts is allowed (aka Callouts).

## Documenting Volatile Content

When documenting tools, APIs, plugins, extensions, or other items that vary by environment or change frequently:

- Focus on categories and patterns, not exhaustive lists
- Document discovery mechanisms (how users find what's available)
- Provide selection criteria (when to use what type)
- Link to authoritative external documentation for comprehensive, up-to-date listings

**Good Examples:**
- "Use grep/search tools to locate code patterns. Common options include semantic_search for natural language queries and grep_search for exact string matching."
- "Commands support various flags. Use `command --help` or consult man pages to discover available options for your environment."
- "For a complete list of available services, see the [official service directory](https://docs.example.com/services/)." (pattern: link to authoritative listing)
- "Consult the [API documentation](https://docs.example.com/api/reference) for all available commands." (pattern: link to maintained reference)

**Bad Examples:**
- ❌ Listing all 50+ available VS Code commands (they change with updates)
- ❌ Enumerating every command-line flag for a tool (varies by version)
- ❌ Comprehensive lists of plugins/extensions (differ per installation)

## Maintaining Documentation Consistency

When updating documentation structure, scope, or terminology:

- Identify all files that reference the changed documentation before making changes
- Use grep/search tools to find all references across the codebase
- Update all references in a single pass to maintain consistency
- Update both links AND descriptions of what the referenced document contains
- Verify that cross-references remain accurate after structural changes

**Example Workflow:**
1. Before changing TOOLS.md from "comprehensive tool list" to "tool patterns guide":
   - Search for all references to TOOLS.md: `grep -r "TOOLS.md" .`
   - Note files with descriptions like "see TOOLS.md for all available tools"
2. Update the target document (TOOLS.md)
3. Update all referring documents in the same session:
   - Change links if path/name changed
   - Update descriptions: "all available tools" → "tool categories and patterns"

**Common Mistakes:**
- ❌ Updating a reference document without checking what references it
- ❌ Changing document scope but leaving old descriptions intact
- ❌ Updating some references now and planning to "fix others later"
