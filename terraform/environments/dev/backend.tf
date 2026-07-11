terraform {
  backend "local" {
    path = "/tmp/terraform-state/dev/terraform.tfstate"
  }
}
