resource "aws_db_subnet_group" "telealert" {
  name       = "telealert-${var.environment}"
  subnet_ids = aws_subnet.private[*].id
  tags = {
    Name = "telealert-db-subnet-group"
  }
}

resource "aws_security_group" "rds" {
  name   = "telealert-rds-${var.environment}"
  vpc_id = aws_vpc.telealert.id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "telealert" {
  identifier        = "telealert-${var.environment}"
  engine            = "postgres"
  engine_version    = "15.4"
  instance_class    = "db.t3.micro"
  allocated_storage = 20

  db_name  = "telealert"
  username = "admin"
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.telealert.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  backup_retention_period = 7
  deletion_protection     = false
  skip_final_snapshot     = true
  multi_az                = false

  tags = {
    Name = "telealert-postgres"
  }
}
