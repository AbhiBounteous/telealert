output "cluster_name" {
  value = module.eks.cluster_name
}

output "cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "rds_endpoint" {
  value     = aws_db_instance.telealert.endpoint
  sensitive = true
}

output "s3_bucket" {
  value = aws_s3_bucket.telealert.bucket
}

output "vpc_id" {
  value = aws_vpc.telealert.id
}
