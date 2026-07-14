# OpenTofu Syntax, K8s Secret & Comment Examples

Worked examples for the **OpenTofu-Specific Syntax**, **Kubernetes Secret Management**, and **Comment Minimalism** rules in `SKILL.md`.

## Conditional Resource Creation

Use `lifecycle.enabled` for conditional resource creation, not `count` or `for_each` with boolean logic.

✅ **GOOD** — OpenTofu native:
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

❌ **BAD** — Terraform-style count workaround:
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

❌ **BAD** — Incorrect for_each usage:
```hcl
resource "kubernetes_secret" "client_credentials" {
  for_each = var.create_kubernetes_secret ? { "enabled" = true } : {}
  # for_each is for multiple instances, not conditionals
}
```

## Variable Declaration for Conditionals

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

Make Kubernetes secret creation optional via `lifecycle.enabled`, defaulting to `false` (opt-in) for security.

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

Only add comments to explain non-obvious logic, complex algorithms, or important constraints. Never comment self-explanatory code.

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
