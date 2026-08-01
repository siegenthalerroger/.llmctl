---
name: "tf-standards"
description: "Authoring conventions for TF (OpenTofu/Terraform) source files: provider version pinning and auth patterns, variable/tfvars defaults and validation, OpenTofu-native syntax, and file/module organization. ALWAYS invoke when creating, reviewing, or modifying .tf/.tofu/.tfvars content — provider blocks, variables, modules, or resource definitions. Covers how the code is written, not how it is run: state operations, drift, CI/CD pipelines, module testing, and provider-upgrade risk belong to the `terraform-skill` skill. Do not write or review OpenTofu/Terraform source without this skill. Keywords: terraform, opentofu, tofu, provider, variables, tfvars, module, lifecycle, hcl."
---

# TF Standards and Patterns

Authoring conventions for TF (OpenTofu/Terraform) infrastructure code: provider configuration, variable management, TF-specific syntax, and code organization.

Worked ✅/❌ examples live in `references/` and are linked from each rule — load them on demand rather than reading them all up front.

**Scope boundary.** This skill governs the *source text*. Execution and operational risk — state operations and recovery, plan/apply and destroy safety, CI drift, module testing frameworks, provider upgrades, compliance scanning — are owned by the `terraform-skill` skill installed as an APM dependency of this package. Invoke both when a task spans authoring and execution.

## Provider Documentation Research

Use OpenTofu Registry MCP tools to research provider resource schemas and arguments instead of local schema parsing or web searches.

- Use `mcp_opentofu-regi_search-opentofu-registry` to find providers
- Use `mcp_opentofu-regi_get-provider-details` to get provider overview and available resources/data sources
- Use `mcp_opentofu-regi_get-resource-docs` to get resource argument details
- Use `mcp_opentofu-regi_get-datasource-docs` for data source documentation
- NEVER use `fetch_webpage` for registry.terraform.io or registry.opentofu.org — use the MCP tools instead

## Provider Version Selection

Always use the latest stable major version of providers unless specific compatibility requirements dictate otherwise.

- Use latest stable major version numbers explicitly (e.g., `3.0` not `2.0`)
- Avoid version constraints like `>= 2.0` that may pull outdated versions
- Check provider documentation for current stable release before setting versions
- Only pin to older versions when explicitly required by dependencies

**Reasoning**: Using outdated provider versions misses bug fixes, new features, and security patches. Explicit latest versions ensure predictable, modern behavior.

See [provider-config.md](./references/provider-config.md#provider-version-selection) for ✅/❌ examples.

## Provider Authentication Patterns

Support multiple authentication methods for providers when the provider supports them. Default to the most user-friendly secure method.

- Support both client credentials and username/password for Keycloak provider
- Use conditional logic (optional variables) to support multiple auth methods
- Document which authentication method requires which variables
- Prefer service account/client credentials in production, username/password for development

See [provider-config.md](./references/provider-config.md#provider-authentication-patterns) for a full ✅ example.

## File Organization

Separate infrastructure code by resource type and concern. Use descriptive file names that indicate content.

- `main.tofu`: Provider configuration and terraform block only
- `variables.tf`: All variable declarations, `validation` blocks, and `check` blocks for input invariants
- `outputs.tf`: All output declarations
- `{resource-type}.tf`: Resources of a specific type (e.g., `realm.tf`, `database.tf`)
- `{resource-name}.tf`: Individual complex resources (e.g., `client-webapp.tf`, `client-api.tf`)
- `modules/{name}/`: Reusable module with its own main/variables/outputs

### Locals Placement

Colocate `locals` blocks with the resources that consume them. Do NOT centralize all locals into a single `locals.tf`.

- Place derived values in the same file as the resources that reference them
- A file must be self-contained: reading it alone reveals what locals drive its resources
- Multiple `locals {}` blocks across files is idiomatic and preferred
- Only create a separate `locals.tf` for truly cross-cutting values used in 3+ files

### Check Block Placement

Place `check` blocks next to the validation concern they enforce:
- Input-shape invariants → in `variables.tf` alongside `validation` blocks
- Resource-state assertions → in the file containing the asserted resources

**Reasoning**: Logical separation makes code easier to navigate, review, and maintain. Finding "where is the realm configuration" should be immediate, not require searching through a monolithic file.

See [organization.md](./references/organization.md#file-organization) for ✅/❌ directory-layout examples.

## Module Design

When creating reusable modules, follow these principles:

- Modules should represent a single logical component (e.g., "OIDC Client", "SAML Client")
- Expose configuration through variables with sensible defaults
- Output all resource attributes that consumers might need
- Include README.md with usage examples
- Keep modules focused and composable
- Use consistent structure across modules for similar resource types (same file layout, variable patterns, outputs)

**Module Structure Consistency**: When adding new modules for different resource types in the same domain (e.g., OIDC client vs SAML client), mirror the structure:
- Same file organization (main.tofu, variables.tf, outputs.tf, client.tf)
- Similar variable naming patterns (realm_id, client_id, enabled)
- Consistent output patterns (client_id, client_resource_id)
- Parallel optional features (K8s secrets, logging, monitoring)

See [organization.md](./references/organization.md#module-design) for ✅ module structure and usage examples.

## Naming Conventions

- Use snake_case for resource names, variable names, and output names
- Use descriptive names that indicate purpose: `keycloak_url` not `url`
- Prefix related resources: `client_webapp`, `client_api`, `client_mobile`
- Use full words, avoid abbreviations except common ones (e.g., `k8s`, `oidc`, `url`)

See [organization.md](./references/organization.md#naming-conventions) for ✅/❌ examples.

## Optional Resource Attributes

Pass `null` for empty optional string/list attributes instead of empty strings or empty lists. Use ternary conditionals in resource blocks.

- Check for empty strings with `!= ""` before passing to optional string attributes
- Check for empty lists with `length() > 0` before passing to optional list attributes
- This prevents provider warnings and ensures clean resource state

**Reasoning**: Many providers treat empty strings differently from `null`. Passing `null` signals "use provider default" while empty string may cause validation errors or unexpected behavior.

## Variable Defaults Strategy

Provide sensible defaults in `variables.tf` for all non-sensitive configuration. Only require explicit values in `.tfvars` files for environment-specific, sensitive, or truly variable data.

- Set reasonable defaults for ports, resource names, timeouts, boolean flags
- Require explicit values only for: URLs, secrets, realm/namespace names, endpoints
- Document defaults in variable descriptions
- Use `null` as default for truly optional resources

**Reasoning**: Users shouldn't need to specify obvious values like `port = 8080` or `enabled = true`. Defaults reduce boilerplate and make `.tfvars` files focus on what actually varies between environments.

### URL and Domain Variable Patterns

For application URLs and endpoints, prefer single base URL variables over split scheme/host/port components.

- Keep URL format **consistent** across all application/service variables in the same configuration
- Avoid splitting into separate `scheme`, `host`, `port` variables unless environment requires different combinations

### Tfvars Minimalism

When authoring `.tfvars` files, only set attributes that differ from their defaults.

- Never set `optional(bool, false)` fields to `false` — omit them entirely
- Never set `optional(string)` fields to `null` — that's already the default
- Only include values that are environment-specific or override a default
- Rely on variable defaults to express "normal" configuration; tfvars express deviations

See [variables.md](./references/variables.md) for ✅/❌ examples of defaults, URL patterns, and tfvars minimalism.

## Variable Flow Tracing

When constructing URLs or paths from variables passed through module boundaries, trace the actual value from `.tfvars` → root variables → module call → resource usage.

- Verify whether URL variables include the scheme (`https://`) before prepending one
- Variable descriptions must accurately reflect the expected format (with or without scheme)
- Check `.tfvars.example` files and root `variables.tf` descriptions to determine the canonical format

## Cleanup Scope

When asked for a "once-over", "nit fixes", or "cleanup", restrict changes to:

- Actual bugs (validation errors, wrong values, broken references)
- Incorrect variable descriptions that contradict usage
- Dead code only when it contains errors (wrong attribute names, invalid syntax)

Do NOT change during cleanup unless explicitly requested:

- Reword or consolidate TODO comments
- Remove commented-out code the user may be keeping as reference
- Restructure working code for style preferences

## OpenTofu-Specific Syntax

OpenTofu has native features that differ from Terraform. Use OpenTofu-native constructs instead of Terraform workarounds.

### Conditional Resource Creation

Use `lifecycle.enabled` for conditional resource creation, not `count` or `for_each` with boolean logic.

**Reasoning**: OpenTofu's `lifecycle.enabled` is cleaner and more explicit than Terraform's `count = var.enabled ? 1 : 0` pattern. It clearly expresses intent and avoids index-based resource references.

### Variable Declaration for Conditionals

When using `lifecycle.enabled`, declare the controlling boolean variable with a clear, descriptive name.

See [opentofu-patterns.md](./references/opentofu-patterns.md#conditional-resource-creation) for ✅/❌ examples.

## Kubernetes Secret Management

When creating Kubernetes secrets from provider resources, follow security best practices.

- Make Kubernetes secret creation optional via `lifecycle.enabled`
- Default to `false` for security (opt-in model)
- Include namespace variable with clear naming
- Document that users need appropriate Kubernetes RBAC permissions

**Reasoning**: Not all users want or need Kubernetes secrets created automatically. Some use external secret management (Vault, Sealed Secrets). Making it optional and opt-in prevents unexpected resource creation in clusters.

See [opentofu-patterns.md](./references/opentofu-patterns.md#kubernetes-secret-management) for a full ✅ example.

## Comment Minimalism

Only add comments to explain non-obvious logic, complex algorithms, or important constraints. Never comment on code that is self-explanatory.

- Do not add section header comments for obvious provider/resource blocks
- Do not comment obvious variable names or simple assignments
- Do comment: complex conditional logic, workarounds, security considerations
- Do comment: why a particular approach was chosen over alternatives

**Reasoning**: Redundant comments create noise and maintenance burden. Code structure (file names, resource types, variable names) should be self-documenting. Comments are for explaining intention, not repeating what the code says.

See [opentofu-patterns.md](./references/opentofu-patterns.md#comment-minimalism) for ✅/❌ examples.

## Managing Pre-Existing or Unsupported Resources

When a TF provider lacks support for a resource, or a resource is auto-created by the upstream system, use the `magodo/restful` provider for proper CRUD lifecycle with drift detection. See [restful provider patterns](./references/restful-provider.md) for authentication setup, patching patterns, and critical lessons.

## Quality Checklist

Before committing OpenTofu code, verify:

- [ ] Provider versions use latest stable major versions
- [ ] Variables have sensible defaults where appropriate
- [ ] Only environment-specific/sensitive values required in tfvars
- [ ] Conditional resources use `lifecycle.enabled` not `count`
- [ ] Comments only explain non-obvious logic
- [ ] Files organized by resource type/concern; locals colocated with consumers
- [ ] Sensitive values marked with `sensitive = true`
- [ ] Module structure follows single-responsibility principle
- [ ] Outputs only expose values that are actually consumed downstream
- [ ] Tfvars only set values that differ from defaults
- [ ] Resource and variable names use snake_case
- [ ] README or documentation exists for modules
- [ ] Variables use consistent pattern across configuration
- [ ] Related modules use consistent structure and naming patterns
- [ ] Variables traced through module boundaries for expected formats
- [ ] Optional resource attributes pass `null` for empty values (not empty strings/lists)

## References

- **Provider config** — [Version selection & authentication examples](./references/provider-config.md)
- **Organization** — [File layout, module structure & naming examples](./references/organization.md)
- **Variables** — [Defaults, URL patterns & tfvars minimalism examples](./references/variables.md)
- **OpenTofu patterns** — [Conditional creation, K8s secrets & comment examples](./references/opentofu-patterns.md)
- **Restful provider** — [Managing pre-existing/unsupported resources](./references/restful-provider.md)
