resource "kind_cluster" "telealert" {
  name           = "telealert-${terraform.workspace}"
  node_image     = local.current.node_image
  wait_for_ready = true

  kind_config {
    kind        = "Cluster"
    api_version = "kind.x-k8s.io/v1alpha4"

    node {
      role = "control-plane"
    }

    dynamic "node" {
      for_each = range(local.current.worker_count)
      content {
        role = "worker"
      }
    }
  }
}

resource "kubernetes_namespace" "namespaces" {
  for_each   = toset(local.current.namespaces)
  depends_on = [kind_cluster.telealert]

  metadata {
    name = each.value
    labels = {
      managed-by  = "terraform"
      project     = "telealert"
      environment = terraform.workspace
    }
  }
}