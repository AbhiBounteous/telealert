terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
  }
}

resource "kubernetes_namespace" "namespaces" {
  for_each = toset(var.namespaces)

  metadata {
    name = each.value
    labels = {
      environment = var.environment
      managed-by  = "terraform"
      project     = "telealert"
    }
  }
}
