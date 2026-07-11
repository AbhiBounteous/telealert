variable "cluster_name" {
  description = "Name of the Kind cluster"
  type        = string
}

variable "node_image" {
  description = "Kubernetes node image"
  type        = string
  default     = "kindest/node:v1.29.0"
}

variable "worker_count" {
  description = "Number of worker nodes"
  type        = number
  default     = 2
}
