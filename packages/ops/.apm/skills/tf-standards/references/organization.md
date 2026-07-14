# File Organization, Module & Naming Examples

Worked examples for the **File Organization**, **Module Design**, and **Naming Conventions** rules in `SKILL.md`.

## File Organization

Separate infrastructure code by resource type and concern, with descriptive file names. Colocate `locals` with their consuming resources; place `check` blocks next to the validation concern they enforce.

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

Modules should represent a single logical component, expose configuration through variables with sensible defaults, and mirror structure across modules for similar resource types.

✅ **GOOD** — Module structure:
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

✅ **GOOD** — Module usage:
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

Use snake_case for resource, variable, and output names. Use descriptive, full-word names (`keycloak_url` not `url`); prefix related resources.

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
