# TERRAFORM CLOUD BACKEND EXAMPLE
# Use this instead of backend.tf for team collaboration

# terraform {
#   cloud {
#     organization = "bounteous-telealert"
#
#     workspaces {
#       name = "telealert-dev"
#     }
#   }
# }
#
# Benefits:
# → State stored in Terraform Cloud
# → Team can see state in UI
# → Auto-apply on git push
# → Drift detection
# → Cost estimation
# → Policy as code (Sentinel)
# → Free for up to 5 users

locals {
  terraform_cloud_config = {
    organization = "bounteous-telealert"
    workspaces = {
      dev     = "telealert-dev"
      staging = "telealert-staging"
      prod    = "telealert-prod"
    }
  }
}

output "terraform_cloud_workspace" {
  description = "Terraform Cloud workspace for this environment"
  value       = lookup(
    local.terraform_cloud_config.workspaces,
    terraform.workspace,
    "telealert-default"
  )
}
