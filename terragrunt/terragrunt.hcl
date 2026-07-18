locals {
  environment = basename(get_terragrunt_dir())
}

remote_state {
  backend = "local"
  config = {
    path = "${get_terragrunt_dir()}/terraform.tfstate"
  }
  generate = {
    path      = "backend.tf"
    if_exists = "overwrite"
  }
}

inputs = {
  cluster_name = "telealert-${local.environment}"
}
