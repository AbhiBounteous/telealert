terraform {
  backend "local" {
    path = "terraform.tfstate.d/${terraform.workspace}/terraform.tfstate"
  }
}
