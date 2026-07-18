module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version

  cluster_endpoint_public_access = true

  vpc_id     = aws_vpc.telealert.id
  subnet_ids = aws_subnet.private[*].id

  eks_managed_node_groups = {
    telealert_workers = {
      instance_types = ["t3.medium"]
      min_size       = 1
      max_size       = 5
      desired_size   = 2

      labels = {
        role = "worker"
        app  = "telealert"
      }
    }

    telealert_spot = {
      instance_types = ["t3.medium", "t3.large"]
      capacity_type  = "SPOT"
      min_size       = 0
      max_size       = 10
      desired_size   = 1

      labels = {
        role = "worker-spot"
        app  = "telealert"
      }
    }
  }

  tags = {
    Environment = var.environment
    Application = "telealert"
  }
}
