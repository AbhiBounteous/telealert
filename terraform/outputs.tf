output "cluster_name" {
  description = "Kind cluster name"
  value       = kind_cluster.telealert.name
}

output "cluster_endpoint" {
  description = "Kubernetes API endpoint"
  value       = kind_cluster.telealert.endpoint
}

output "current_workspace" {
  description = "Current Terraform workspace"
  value       = terraform.workspace
}

output "worker_nodes" {
  description = "Number of worker nodes"
  value       = local.current.worker_count
}

output "namespaces" {
  description = "Created namespaces"
  value       = local.current.namespaces
}

output "kubeconfig" {
  description = "Kubeconfig for cluster"
  value       = kind_cluster.telealert.kubeconfig
  sensitive   = true
}