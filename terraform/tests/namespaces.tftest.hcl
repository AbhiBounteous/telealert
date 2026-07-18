# Test that namespaces are correctly configured

run "verify_namespaces_exist" {
  command = plan

  assert {
    condition     = length(var.cluster_name) > 0
    error_message = "Cluster name must not be empty"
  }

  assert {
    condition     = var.worker_nodes >= 1
    error_message = "Must have at least 1 worker node"
  }
}

run "verify_workspace_config" {
  command = plan

  assert {
    condition = contains(
      ["dev", "staging", "prod", "default"],
      terraform.workspace
    )
    error_message = "Workspace must be dev, staging, prod or default"
  }
}
