---
name: "tf-standards"
description: "Configuration standards, conventions, and patterns for TF (OpenTofu/Terraform). Includes provider versioning, variable defaults, syntax patterns, file organization, and security best practices."
---

# TF Standards and Patterns

Standards and conventions for writing TF (OpenTofu/Terraform) infrastructure code, focusing on provider configuration, variable management, TF-specific syntax, and code organization.

## Provider Documentation Research

Use OpenTofu Registry MCP tools to research provider resource schemas and arguments instead of local schema parsing or web searches.

- Use `search-opentofu-registry` to find providers
- Use `get-resource-docs` to get resource argument details
- Use `get-datasource-docs` for data source documentation
- Reference official provider documentation for examples and complete attribute lists

## Provider Version Selection

Always use the latest stable major version of providers unless specific compatibility requirements dictate otherwise.

- Use latest stable major version numbers explicitly (e.g., `3.0` not `2.0`)
- Avoid version constraints like `>= 2.0` that may pull outdated versions
- Check provider documentation for current stable release before setting versions
- Only pin to older versions when explicitly required by dependencies

**Reasoning**: Using outdated provider versions misses bug fixes, new features, and security patches. Explicit latest versions ensure predictable, modern behavior.

✅ **GOOD**:
```hcl
terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 3.0"  # Latest stable major version
    }
    keycloak = {
      source  = "mrparkers/keycloak"
      version = "~> 4.4"  # Latest stable version
    }
  }
}
```

❌ **BAD**:
```hcl
terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"  # Outdated major version
    }
  }
}
```

## Provider Authentication Patterns

Support multiple authentication methods for providers when the provider supports them. Default to the most user-friendly secure method.

- Support both client credentials and username/password for Keycloak provider
- Use conditional logic (optional variables) to support multiple auth methods
- Document which authentication method requires which variables
- Prefer service account/client credentials in production, username/password for development

✅ **GOOD**:
```hcl
# variables.tf
variable "keycloak_client_id" {
  description = "Keycloak admin client ID (for client credentials auth)"
  type        = string
  default     = "admin-cli"
}

variable "keycloak_client_secret" {
  description = "Client secret for Keycloak authentication (optional, use for client credentials)"
  type        = string
  sensitive   = true
  default     = null
}

variable "keycloak_username" {
  description = "Username for Keycloak authentication (optional, use if not using client credentials)"
  type        = string
  default     = null
}

variable "keycloak_password" {
  description = "Password for Keycloak authentication (optional, use if not using client credentials)"
  type        = string
  sensitive   = true
  default     = null
}

# main.tofu
provider "keycloak" {
  client_id     = var.keycloak_client_id
  url           = var.keycloak_url
  client_secret = var.keycloak_client_secret
  username      = var.keycloak_username
  password      = var.keycloak_password
}
```

## File Organization

Separate infrastructure code by resource type and concern. Use descriptive file names that indicate content.

- `main.tofu`: Provider configuration and terraform block only
- `variables.tf`: All variable declarations
- `outputs.tf`: All output declarations
- `{resource-type}.tf`: Resources of a specific type (e.g., `realm.tf`, `database.tf`)
- `{resource-name}.tf`: Individual complex resources (e.g., `client-webapp.tf`, `client-api.tf`)
- `modules/{name}/`: Reusable module with its own main/variables/outputs

**Reasoning**: Logical separation makes code easier to navigate, review, and maintain. Finding "where is the realm configuration" should be immediate, not require searching through a monolithic file.

✅ **GOOD**:
```
keycloak/
  main.tofu              # Providers and terraform config
  variables.tf           # All variables
  outputs.tf             # All outputs
  realm.tf               # Realm resource
  client-webapp.tf       # Web app client config
  client-api.tf          # API client config
  client-mobile.tf       # Mobile client config
  modules/
    oidc-client/
      main.tofu
      variables.tf
      outputs.tf
      client.tf
      k8s-secret.tf
```

❌ **BAD**:
```
keycloak/
  main.tofu              # Everything mixed together:
                         # - providers
                         # - realm
                         # - all clients
                         # - variables
                         # - outputs
```

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

✅ **GOOD** - Module structure:
```
modules/
  oidc-client/
    README.md           # Usage documentation
    main.tofu           # Provider requirements
    variables.tf        # Input variables
    outputs.tf          # Output values
    client.tf           # OIDC client resource
    k8s-secret.tf       # Optional K8s secret
```

✅ **GOOD** - Module usage:
```hcl
module "webapp_client" {
  source = "./modules/oidc-client"

  keycloak_url          = var.keycloak_url
  realm_name           = var.realm_name
  client_id            = "webapp"
  client_name          = "Web Application"
  valid_redirect_uris  = ["https://app.example.com/*"]

  # Optional features
  create_kubernetes_secret = true
  kubernetes_namespace     = "production"
}

output "webapp_client_secret" {
  value     = module.webapp_client.client_secret
  sensitive = true
}
```

## Naming Conventions

- Use snake_case for resource names, variable names, and output names
- Use descriptive names that indicate purpose: `keycloak_url` not `url`
- Prefix related resources: `client_webapp`, `client_api`, `client_mobile`
- Use full words, avoid abbreviations except common ones (e.g., `k8s`, `oidc`, `url`)

✅ **GOOD**:
```hcl
variable "keycloak_url" { }
variable "realm_name" { }
variable "client_id" { }
variable "valid_redirect_uris" { }
resource "keycloak_openid_client" "webapp_client" { }
output "client_secret" { }
```

❌ **BAD**:
```hcl
variable "kcUrl" { }           # camelCase
variable "rName" { }           # abbreviated
variable "cid" { }             # too short
variable "redirectURIs" { }   # inconsistent case
resource "keycloak_openid_client" "c" { }  # non-descriptive
output "secret" { }            # ambiguous
```

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

✅ **GOOD** - `variables.tf`:
```hcl
variable "keycloak_url" {
  description = "Keycloak server URL"
  type        = string
  # No default - environment-specific
}

variable "realm_name" {
  description = "Keycloak realm name"
  type        = string
  # No default - varies by deployment
}

variable "client_port" {
  description = "Client service port"
  type        = number
  default     = 8080  # Sensible default
}

variable "enable_monitoring" {
  description = "Enable monitoring integration"
  type        = bool
  default     = true  # Most deployments want this
}
```

✅ **GOOD** - `terraform.tfvars`:
```hcl
# Only specify what varies or is sensitive
keycloak_url = "https://keycloak.example.com"
realm_name   = "production"
client_secret = "secret-value-from-vault"
```

❌ **BAD** - `variables.tf`:
```hcl
variable "client_port" {
  description = "Client service port"
  type        = number
  # No default forces users to specify obvious values
}

variable "enable_monitoring" {
  description = "Enable monitoring"
  type        = bool
  # No default for boolean flag
}
```

❌ **BAD** - `terraform.tfvars`:
```hcl
# Requiring obvious values in tfvars
client_port = 8080
enable_monitoring = true
timeout_seconds = 30
max_retries = 3
```

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

✅ **GOOD** - OpenTofu native:
```hcl
resource "kubernetes_secret" "client_credentials" {
  lifecycle {
    enabled = var.create_kubernetes_secret
  }

  metadata {
    name      = "${var.client_id}-credentials"
    namespace = var.kubernetes_namespace
  }

  data = {
    client_id     = keycloak_openid_client.client.client_id
    client_secret = keycloak_openid_client.client.client_secret
  }
}
```

❌ **BAD** - Terraform-style count workaround:
```hcl
resource "kubernetes_secret" "client_credentials" {
  count = var.create_kubernetes_secret ? 1 : 0

  metadata {
    name      = "${var.client_id}-credentials"
    namespace = var.kubernetes_namespace
  }

  data = {
    # Awkward to reference with [0] everywhere
    client_id     = keycloak_openid_client.client.client_id
    client_secret = keycloak_openid_client.client.client_secret
  }
}
```

❌ **BAD** - Incorrect for_each usage:
```hcl
resource "kubernetes_secret" "client_credentials" {
  for_each = var.create_kubernetes_secret ? { "enabled" = true } : {}
  # for_each is for multiple instances, not conditionals
}
```

### Variable Declaration for Conditionals

When using `lifecycle.enabled`, declare the controlling boolean variable with a clear, descriptive name.

✅ **GOOD**:
```hcl
variable "create_kubernetes_secret" {
  description = "Whether to create a Kubernetes secret with client credentials"
  type        = bool
  default     = false  # Opt-in for security
}
```

## Kubernetes Secret Management

When creating Kubernetes secrets from provider resources, follow security best practices.

- Make Kubernetes secret creation optional via `lifecycle.enabled`
- Default to `false` for security (opt-in model)
- Include namespace variable with clear naming
- Document that users need appropriate Kubernetes RBAC permissions

**Reasoning**: Not all users want or need Kubernetes secrets created automatically. Some use external secret management (Vault, Sealed Secrets). Making it optional and opt-in prevents unexpected resource creation in clusters.

✅ **GOOD**:
```hcl
variable "create_kubernetes_secret" {
  description = "Whether to create a Kubernetes secret with client credentials"
  type        = bool
  default     = false  # Opt-in for security
}

variable "kubernetes_namespace" {
  description = "Kubernetes namespace for the secret (required if create_kubernetes_secret is true)"
  type        = string
  default     = "default"
}

resource "kubernetes_secret" "client_credentials" {
  lifecycle {
    enabled = var.create_kubernetes_secret
  }

  metadata {
    name      = "${var.client_id}-credentials"
    namespace = var.kubernetes_namespace
  }

  data = {
    client_id     = keycloak_openid_client.client.client_id
    client_secret = keycloak_openid_client.client.client_secret
  }
}
```

## Comment Minimalism

Only add comments to explain non-obvious logic, complex algorithms, or important constraints. Never comment on code that is self-explanatory.

- Do not add section header comments for obvious provider/resource blocks
- Do not comment obvious variable names or simple assignments
- Do comment: complex conditional logic, workarounds, security considerations
- Do comment: why a particular approach was chosen over alternatives

**Reasoning**: Redundant comments create noise and maintenance burden. Code structure (file names, resource types, variable names) should be self-documenting. Comments are for explaining intention, not repeating what the code says.

✅ **GOOD**:
```hcl
# main.tofu
terraform {
  required_providers {
    keycloak = {
      source  = "mrparkers/keycloak"
      version = "~> 4.4"
    }
  }
}

provider "keycloak" {
  client_id  = var.keycloak_client_id
  url        = var.keycloak_url
  # Using username/password auth instead of client credentials
  # because service account tokens don't have realm management permissions
  username   = var.keycloak_username
  password   = var.keycloak_password
}
```

❌ **BAD**:
```hcl
# main.tofu

# Terraform Configuration
terraform {
  # Required Providers Block
  required_providers {
    # Keycloak Provider
    keycloak = {
      source  = "mrparkers/keycloak"  # Provider source
      version = "~> 4.4"               # Provider version
    }
  }
}

# Keycloak Provider Configuration
provider "keycloak" {
  client_id  = var.keycloak_client_id  # Client ID
  url        = var.keycloak_url        # Keycloak URL
  username   = var.keycloak_username   # Username
  password   = var.keycloak_password   # Password
}
```

## Quality Checklist

Before committing OpenTofu code, verify:

- [ ] Provider versions use latest stable major versions
- [ ] Variables have sensible defaults where appropriate
- [ ] Only environment-specific/sensitive values required in tfvars
- [ ] Conditional resources use `lifecycle.enabled` not `count`
- [ ] Comments only explain non-obvious logic
- [ ] Files organized by resource type/concern
- [ ] Sensitive values marked with `sensitive = true`
- [ ] Module structure follows single-responsibility principle
- [ ] Resource and variable names use snake_case
- [ ] README or documentation exists for modules
- [ ] Variables use consistent pattern across configuration
- [ ] Related modules use consistent structure and naming patterns
- [ ] Variables traced through module boundaries for expected formats
- [ ] Optional resource attributes pass `null` for empty values (not empty strings/lists)
