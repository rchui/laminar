data "aws_ssm_parameter" "protected_subnet_ids" { name = "/vpc/main/subnets/protected/ids" }
data "aws_ssm_parameter" "vpc_id" { name = "/vpc/main/id" }

data "aws_iam_policy_document" "instance" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type = "Service"
      identifiers = [
        "ec2.amazonaws.com"
      ]
    }
  }
}

resource "aws_iam_role" "instance" {
  name = "LaminarBatchInstance"

  assume_role_policy = data.aws_iam_policy_document.instance.json

  managed_policy_arns = [
    "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
  ]
}

resource "aws_iam_instance_profile" "instance" {
  name = "LaminarBatch"
  role = aws_iam_role.instance.name
}

data "aws_iam_policy_document" "service" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type = "Service"
      identifiers = [
        "batch.amazonaws.com"
      ]
    }
  }
}

resource "aws_iam_role" "service" {
  name = "LaminarBatchService"

  assume_role_policy = data.aws_iam_policy_document.service.json

  managed_policy_arns = [
    "arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole"
  ]
}

resource "aws_security_group" "instance" {
  name   = "LaminarBatchInstance"
  vpc_id = data.aws_ssm_parameter.vpc_id.value
}

resource "aws_security_group_rule" "instance_egress" {
  security_group_id = aws_security_group.instance.id
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
}

resource "aws_batch_compute_environment" "main" {
  compute_environment_name_prefix = "laminar-"
  service_role                    = aws_iam_role.service.arn
  type                            = "MANAGED"

  compute_resources {
    allocation_strategy = "BEST_FIT_PROGRESSIVE"

    instance_role = aws_iam_instance_profile.instance.arn
    instance_type = [
      "m5",
      "m5a",
      "r5",
      "r5a",
      "c5",
      "c5a",
    ]

    desired_vcpus = 0
    min_vcpus     = 0
    max_vcpus     = 20

    security_group_ids = [
      aws_security_group.instance.id,
    ]

    subnets = split(",", data.aws_ssm_parameter.protected_subnet_ids.value)

    type = "EC2"
  }
}

resource "aws_batch_job_queue" "main" {
  name     = "laminar"
  state    = "ENABLED"
  priority = 1
  compute_environments = [
    aws_batch_compute_environment.main.arn,
  ]
}

resource "aws_cloudwatch_log_group" "main" {
  name              = "laminar"
  retention_in_days = 30
}

resource "aws_ecs_cluster" "main" {
  name               = "laminar"
  capacity_providers = ["FARGATE"]
}

resource "aws_ecs_task_definition" "scheduler" {
  family                   = "laminar"
  requires_compatibilities = ["FARGATE"]

  cpu          = 256
  memory       = 512
  network_mode = "awsvpc"

  container_definitions = jsonencode(
    [
      {
        name    = "scheduler"
        image   = "rchui/laminar:3.8"
        command = ["python", "main.py"]
        logConfiguration = {
          logDriver = "awslogs"
          options = {
            awslogs-group = "laminar"
            awslogs-region = "us-west-2"
            awslogs-stream-prefix = "scheduler"
          }
        }
      }
    ]
  )

  depends_on = [
    aws_cloudwatch_log_group.main
  ]
}
