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
  cluster_name = "telealert-dev"
  worker_count = 1
}

module "namespaces" {
  source      = "../../modules/namespaces"
  environment = "dev"
  namespaces  = ["argocd", "monitoring", "telealert-dev"]

  depends_on = [module.cluster]
}
