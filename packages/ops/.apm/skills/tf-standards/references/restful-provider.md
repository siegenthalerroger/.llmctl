# Managing Pre-Existing or Unsupported Resources with magodo/restful

When a TF provider lacks support for a resource, or a resource is auto-created by the upstream system (e.g., Keycloak's built-in authentication flows), use the `magodo/restful` provider for proper CRUD lifecycle with drift detection.

## When to Use

- The native provider does not expose a resource type for what you need to manage
- A resource is auto-created by the system and you only need to patch specific properties
- You need drift detection (not just fire-and-forget like `local-exec`)
- The API endpoint is RESTful (GET to read, PUT/PATCH to update)

## Key Patterns

**OAuth2 Password Authentication** (e.g., Keycloak):
```hcl
provider "restful" {
  base_url = var.keycloak_url
  security = {
    oauth2 = {
      password = {
        token_url = "${var.keycloak_url}/realms/${var.admin_realm}/protocol/openid-connect/token"
        client_id = var.keycloak_client_id
        username  = var.keycloak_username
        password  = var.keycloak_password
      }
    }
  }
}
```

**Patching a pre-existing resource** (adopt + manage a single property):
```hcl
resource "restful_resource" "patch_execution" {
  path          = "/admin/realms/my-realm/authentication/flows/my flow/executions"
  create_method = "PUT"   # Idempotent — PUT is safe for pre-existing resources
  update_method = "PUT"

  # Read returns an array — use gjson selector to pick the target item
  read_path     = "/admin/realms/my-realm/authentication/flows/my flow/executions"
  read_selector = "#(providerId==\"idp-review-profile\")"

  # Normalize server response to only fields we manage (prevents false drift)
  read_response_template = jsonencode({
    id          = "$(body.id)"
    requirement = "$(body.requirement)"
  })

  # Only these fields trigger drift detection in plan output
  output_attrs = ["requirement"]

  body = {
    id          = data.some_data_source.execution.id
    requirement = "DISABLED"
  }
}
```

## Critical Lessons

- **`read_response_template`** — Always use when the server returns more fields than your `body` declares. Without it, the provider stores the full server response in state, causing perpetual drift from extra fields.
- **`read_selector`** — Use gjson query syntax (`#(field=="value")`) when the GET endpoint returns an array and you need to select one item.
- **`output_attrs`** — Limits which fields appear in `output` and are compared for drift. Set this to only the fields you actually manage.
- **`create_method = "PUT"`** — Use for pre-existing resources where "create" is really just the first update. PUT is idempotent, so it works whether the resource exists or not.
- **`check_existance = true`** — Do NOT use for adoption of pre-existing resources. It triggers "resource already exists" errors requiring manual import. Use `create_method = "PUT"` instead.
- **URL encoding** — Use literal spaces in paths (`/flows/first broker login/executions`). The provider handles URL encoding. Manually encoding (`%20`) can cause double-encoding.
- **`import` blocks** — Only work in root modules, never in child modules. Do not attempt to use them inside `module "..."` sources.
