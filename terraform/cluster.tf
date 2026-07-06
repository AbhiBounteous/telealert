resource "kind_cluster" "telealert" {
  name           = var.cluster_name
  node_image     = var.cluster_node_image
  wait_for_ready = true

  kind_config {
    kind        = "Cluster"
    api_version = "kind.x-k8s.io/v1alpha4"

    node {
      role = "control-plane"
    }

    dynamic "node" {
      for_each = range(var.worker_nodes)
      content {
        role = "worker"
      }
    }
  }
}

resource "kubernetes_namespace" "argocd" {
  depends_on = [kind_cluster.telealert]

  metadata {
    name = var.argocd_namespace
    labels = {
      managed-by = "terraform"
      project    = "telealert"
    }
  }
}

resource "kubernetes_namespace" "telealert" {
  depends_on = [kind_cluster.telealert]

  metadata {
    name = var.telealert_namespace
    labels = {
      managed-by = "terraform"
      project    = "telealert"
    }
  }
}

resource "kubernetes_namespace" "monitoring" {
  depends_on = [kind_cluster.telealert]

  metadata {
    name = "monitoring"
    labels = {
      managed-by = "terraform"
      project    = "telealert"
    }
  }
}
