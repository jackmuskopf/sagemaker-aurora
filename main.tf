resource "aws_sagemaker_notebook_instance" "main" {
  name          = "${local.prefix}"
  role_arn      = "${aws_iam_role.sgmkr.arn}"
  instance_type = "ml.t2.medium"
  subnet_id     = "${local.sgmkr_subnet}"
  security_groups = [
    "${aws_security_group.sgmkr.id}"
  ]
}

resource "aws_iam_role" "sgmkr" {
  name = "${local.prefix}-sgmkr"

  assume_role_policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "sagemaker.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF
}

resource "aws_iam_role_policy" "sgmkr" {
  role   = "${aws_iam_role.sgmkr.name}"
  policy = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
      	"s3:Get*",
      	"s3:List*",
        "dynamodb:BatchGet*",
        "dynamodb:DescribeStream",
        "dynamodb:DescribeTable",
        "dynamodb:Get*",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:BatchWrite*",
        "dynamodb:CreateTable",
        "dynamodb:Delete*",
        "dynamodb:Update*",
        "dynamodb:PutItem"
      ],
      "Effect": "Allow",
      "Resource": "*"
    },
    {
      "Action": "ssm:GetParameter",
      "Effect": "Allow",
      "Resource": "${aws_ssm_parameter.database_connection.arn}"
    }
  ]
}
POLICY
}

resource "aws_rds_cluster_instance" "main" {
  count              = 1
  identifier         = "${local.prefix}-${count.index}"
  cluster_identifier = "${aws_rds_cluster.main.id}"
  instance_class     = "db.t3.medium"
  engine             = "aurora-postgresql"

  // netorking
  publicly_accessible  = false
  db_subnet_group_name = "${aws_db_subnet_group.main.name}"
}

resource "aws_rds_cluster" "main" {
  cluster_identifier = "${local.prefix}"
  database_name      = "${local.db_name}"
  engine             = "aurora-postgresql"
  port               = "${local.db_port}"

  // credentials
  master_password = "${local.db_password}"
  master_username = "${local.db_username}"

  // networking
  db_subnet_group_name = "${aws_db_subnet_group.main.name}"
  vpc_security_group_ids = [
    "${aws_security_group.aurora.id}"
  ]
}

locals {
  database_connection = {
    host     = "${aws_rds_cluster.main.endpoint}"
    port     = "${local.db_port}"
    name     = "${local.db_name}"
    username = "${local.db_username}"
    password = "${local.db_password}"
  }
}

resource "aws_ssm_parameter" "database_connection" {
  name  = "${local.prefix}-database-connection"
  type  = "String"
  value = "${jsonencode(local.database_connection)}"
}

resource "aws_db_subnet_group" "main" {
  name       = "${local.prefix}"
  subnet_ids = "${local.aurora_subnets}"
}

resource "aws_security_group" "aurora" {
  name        = "${local.prefix}-aurora"
  description = "Allow allow from sagemaker on db port"
  vpc_id      = "${local.vpc_id}"

  ingress {
    from_port       = "${local.db_port}"
    to_port         = "${local.db_port}"
    protocol        = "tcp"
    security_groups = ["${aws_security_group.sgmkr.id}"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "sgmkr" {
  name        = "${local.prefix}-sgmkr"
  description = "sagemaker sg"
  vpc_id      = "${local.vpc_id}"

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}


