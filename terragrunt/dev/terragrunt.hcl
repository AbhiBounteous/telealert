include "root" {
  path = find_in_parent_folders()
}

terraform {
  source = "../../terraform"
}

inputs = {
  cluster_name = "telealert-dev"
  worker_nodes = 1
  telealert_namespace = "telealert-dev"
}
