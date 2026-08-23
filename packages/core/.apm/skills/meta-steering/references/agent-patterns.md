# Common Agent Patterns

Before adding a new persona below, apply the default-to-one-agent gate in [agents.md](./agents.md#default-to-one-agent) — add a specialist only when it improves capability isolation, policy isolation, prompt clarity, or trace legibility.

## Personas

### Testing Specialist

**Purpose**: Focus on test coverage and quality

**Tools**: All tools (for comprehensive test creation)

**Approach**: Analyze, identify gaps, write tests, avoid production code changes

### Implementation Planner

**Purpose**: Create detailed technical plans and specifications

**Tools**: Limited to `['read', 'search', 'edit']`

**Approach**: Analyze requirements, create documentation, avoid implementation

### Code Reviewer

**Purpose**: Review code quality and provide feedback

**Tools**: `['read', 'search']` only

**Approach**: Analyze, suggest improvements, no direct modifications

### Refactoring Specialist

**Purpose**: Improve code structure and maintainability

**Tools**: `['read', 'search', 'edit']`

**Approach**: Analyze patterns, propose refactorings, implement safely

### Security Auditor

**Purpose**: Identify security issues and vulnerabilities

**Tools**: `['read', 'search', 'web']`

**Approach**: Scan code, check against OWASP, report findings