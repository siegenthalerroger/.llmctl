# Variable & Tfvars Examples

Worked examples for the **Variable Defaults Strategy**, **URL and Domain Variable Patterns**, and **Tfvars Minimalism** rules in `SKILL.md`.

## Variable Defaults Strategy

Provide sensible defaults in `variables.tf` for all non-sensitive configuration. Require explicit values only for environment-specific, sensitive, or truly variable data. For application URLs, prefer single base URL variables over split scheme/host/port components.

✅ **GOOD** — `variables.tf`:
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

✅ **GOOD** — `terraform.tfvars`:
```hcl
# Only specify what varies or is sensitive
keycloak_url = "https://keycloak.example.com"
realm_name   = "production"
client_secret = "secret-value-from-vault"
```

❌ **BAD** — `variables.tf`:
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

❌ **BAD** — `terraform.tfvars`:
```hcl
# Requiring obvious values in tfvars
client_port = 8080
enable_monitoring = true
timeout_seconds = 30
max_retries = 3
```

## Tfvars Minimalism

When authoring `.tfvars` files, only set attributes that differ from their defaults. Never set `optional(bool, false)` to `false` or `optional(string)` to `null` — omit them.

❌ **BAD**:
```hcl
tenants = {
  "acm" = {
    keycloak_realm = { id = "acm" }
    is_default     = true       # Unnecessary if only one tenant
    detect_tenants = [
      { aml_tenant = "0001", business_unit = "...", is_global = true }
    ]
  }
  "acm2" = {
    keycloak_realm = { id = "acm2" }
    is_default     = false      # Redundant — already the default
    detect_tenants = [...]
  }
}
```

✅ **GOOD**:
```hcl
tenants = {
  "acm" = {
    keycloak_realm = { id = "acm" }
    detect_tenants = [
      { aml_tenant = "0001", business_unit = "...", is_global = true }
    ]
  }
  "acm2" = {
    keycloak_realm = { id = "acm2" }
    detect_tenants = [
      { aml_tenant = "0002", business_unit = "..." }
    ]
  }
}
```
