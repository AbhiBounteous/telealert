output "cluster_name" {
  value = kind_cluster.this.name
}

output "endpoint" {
  value = kind_cluster.this.endpoint
}

output "kubeconfig" {
  value     = kind_cluster.this.kubeconfig
  sensitive = true
}
