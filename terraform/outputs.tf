output "cluster_name" {
  description = "Kind cluster name"
  value       = kind_cluster.telealert.name
}

output "cluster_endpoint" {
  description = "Kubernetes API endpoint"
  value       = kind_cluster.telealert.endpoint
}

output "argocd_namespace" {
  description = "ArgoCD namespace"
  value       = kubernetes_namespace.argocd.metadata[0].name
}

output "telealert_namespace" {
  description = "TeleAlert namespace"
  value       = kubernetes_namespace.telealert.metadata[0].name
}

output "kubeconfig" {
  description = "Kubeconfig for cluster"
  value       = kind_cluster.telealert.kubeconfig
  sensitive   = true
}
