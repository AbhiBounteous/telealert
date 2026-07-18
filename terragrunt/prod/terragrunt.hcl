include "root" {
  path = find_in_parent_folders()
}

terraform {
  source = "../../terraform"
}

inputs = {
  cluster_name = "telealert-prod"
  worker_nodes = 3
  telealert_namespace = "telealert-prod"
}
