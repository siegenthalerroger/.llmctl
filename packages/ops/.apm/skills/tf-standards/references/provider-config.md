# Provider Configuration Examples

Worked examples for the **Provider Version Selection** and **Provider Authentication Patterns** rules in `SKILL.md`.

## Provider Version Selection

Always use the latest stable major version of providers unless specific compatibility requirements dictate otherwise.

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

Support multiple authentication methods for providers when the provider supports them, using conditional logic (optional variables). Default to the most user-friendly secure method.

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
