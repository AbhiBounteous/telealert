# MULTI-REGION DEPLOYMENT
# Deploy same infrastructure to Mumbai and US East

provider "aws" {
  alias  = "mumbai"
  region = "ap-south-1"
}

provider "aws" {
  alias  = "us_east"
  region = "us-east-1"
}

# Mumbai deployment handled by default provider
# US East deployment example:

# module "eks_us_east" {
#   source  = "terraform-aws-modules/eks/aws"
#   version = "~> 20.0"
#   providers = {
#     aws = aws.us_east
#   }
#   cluster_name = "telealert-prod-us-east"
#   ...same config...
# }

output "deployment_regions" {
  value = {
    primary   = "ap-south-1 (Mumbai)"
    secondary = "us-east-1 (N. Virginia)"
    strategy  = "Active-Active"
  }
}
