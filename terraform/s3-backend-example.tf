# S3 BACKEND CONFIGURATION
# Use this when you have AWS account
# Replace backend.tf with this content

# terraform {
#   backend "s3" {
#     bucket         = "telealert-tf-state"
#     key            = "terraform.tfstate"
#     region         = "ap-south-1"
#     encrypt        = true
#     dynamodb_table = "telealert-tf-lock"
#   }
# }

# HOW TO SETUP:
# Step 1: Create S3 bucket
# aws s3 mb s3://telealert-tf-state \
#   --region ap-south-1
#
# Step 2: Enable versioning
# aws s3api put-bucket-versioning \
#   --bucket telealert-tf-state \
#   --versioning-configuration Status=Enabled
#
# Step 3: Create DynamoDB table for locking
# aws dynamodb create-table \
#   --table-name telealert-tf-lock \
#   --attribute-definitions \
#     AttributeName=LockID,AttributeType=S \
#   --key-schema \
#     AttributeName=LockID,KeyType=HASH \
#   --billing-mode PAY_PER_REQUEST \
#   --region ap-south-1
#
# Step 4: Replace backend.tf with S3 config above
# Step 5: terraform init -migrate-state
#
# WORKSPACE KEYS per environment:
# dev:     "env/dev/terraform.tfstate"
# staging: "env/staging/terraform.tfstate"
# prod:    "env/prod/terraform.tfstate"

locals {
  backend_config = {
    bucket         = "telealert-tf-state"
    region         = "ap-south-1"
    encrypt        = true
    dynamodb_table = "telealert-tf-lock"
    workspace_keys = {
      dev     = "env/dev/terraform.tfstate"
      staging = "env/staging/terraform.tfstate"
      prod    = "env/prod/terraform.tfstate"
    }
  }
}

output "s3_backend_config" {
  description = "S3 backend configuration reference"
  value = {
    bucket         = local.backend_config.bucket
    region         = local.backend_config.region
    workspace_key  = lookup(local.backend_config.workspace_keys, terraform.workspace, "env/default/terraform.tfstate")
    dynamodb_table = local.backend_config.dynamodb_table
  }
}
