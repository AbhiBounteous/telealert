output "namespace_names" {
  value = [for ns in kubernetes_namespace.namespaces : ns.metadata[0].name]
}
