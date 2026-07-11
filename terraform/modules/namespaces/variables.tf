variable "namespaces" {
  description = "List of namespaces to create"
  type        = list(string)
  default     = ["argocd", "monitoring", "telealert"]
}

variable "environment" {
  description = "Environment name"
  type        = string
}
