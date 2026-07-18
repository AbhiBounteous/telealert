terraform {
  required_providers {
    kind = {
      source  = "tehcyx/kind"
      version = "0.2.1"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }
  }
  required_version = ">= 1.0"
}

provider "kind" {}

provider "kubernetes" {
  config_path = "~/.kube/config"
}

provider "helm" {
  kubernetes {
    config_path = "~/.kube/config"
  }
}

locals {
  workspace_config = {
    dev = {
      worker_count = 1
      node_image   = "kindest/node:v1.29.0"
      namespaces   = ["argocd", "monitoring", "telealert-dev"]
    }
    staging = {
      worker_count = 2
      node_image   = "kindest/node:v1.29.0"
      namespaces   = ["argocd", "monitoring", "telealert-staging"]
    }
    prod = {
      worker_count = 3
      node_image   = "kindest/node:v1.29.0"
      namespaces   = ["argocd", "monitoring", "telealert-prod"]
    }
    default = {
      worker_count = 1
      node_image   = "kindest/node:v1.29.0"
      namespaces   = ["argocd", "monitoring", "telealert"]
    }
  }

  current = local.workspace_config[terraform.workspace]

}
data "kubernetes_namespace" "kube_system" {
  metadata {
    name = "kube-system"
  }
}

data "kubernetes_namespace" "default" {
  metadata {
    name = "default"
  }
}

data "kubernetes_nodes" "all" {}