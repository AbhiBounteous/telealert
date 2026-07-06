variable "cluster_name" {
  description = "Name of the Kind cluster"
  type        = string
  default     = "telealert-tf"
}

variable "cluster_node_image" {
  description = "Kubernetes node image"
  type        = string
  default     = "kindest/node:v1.29.0"
}

variable "worker_nodes" {
  description = "Number of worker nodes"
  type        = number
  default     = 2
}

variable "argocd_namespace" {
  description = "Namespace for ArgoCD"
  type        = string
  default     = "argocd"
}

variable "telealert_namespace" {
  description = "Namespace for TeleAlert"
  type        = string
  default     = "telealert"
}
