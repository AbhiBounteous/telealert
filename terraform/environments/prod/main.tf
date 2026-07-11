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
  }
}

provider "kind" {}

provider "kubernetes" {
  config_path = "~/.kube/config"
}

module "cluster" {
  source       = "../../modules/kind-cluster"
  cluster_name = "telealert-prod"
  worker_count = 3
}

module "namespaces" {
  source      = "../../modules/namespaces"
  environment = "prod"
  namespaces  = ["argocd", "monitoring", "telealert-prod"]

  depends_on = [module.cluster]
}
