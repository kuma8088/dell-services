# ============================================================================
# Terraform Outputs
# ============================================================================
# Purpose: Expose key resource identifiers for integrations and diagnostics.
# ============================================================================

output "vpc_id" {
  description = "VPC ID for mail server infrastructure"
  value       = aws_vpc.mailserver_vpc.id
}

output "vpc_cidr" {
  description = "VPC CIDR block"
  value       = aws_vpc.mailserver_vpc.cidr_block
}

output "internet_gateway_id" {
  description = "Internet Gateway ID"
  value       = aws_internet_gateway.mailserver_igw.id
}

output "public_subnet_1a_id" {
  description = "Public subnet ID in ap-northeast-1a"
  value       = aws_subnet.public_subnet_1a.id
}

output "public_subnet_1c_id" {
  description = "Public subnet ID in ap-northeast-1c"
  value       = aws_subnet.public_subnet_1c.id
}

output "route_table_id" {
  description = "Public route table ID"
  value       = aws_route_table.mailserver_public_rt.id
}

output "security_group_id" {
  description = "Fargate security group ID"
  value       = aws_security_group.fargate_sg.id
}

output "elastic_ip" {
  description = "Elastic IP address for mail server"
  value       = aws_eip.mailserver_eip.public_ip
}

output "elastic_ip_allocation_id" {
  description = "Elastic IP allocation ID"
  value       = aws_eip.mailserver_eip.id
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.mailserver_cluster.name
}

output "ecs_cluster_arn" {
  description = "ECS cluster ARN"
  value       = aws_ecs_cluster.mailserver_cluster.arn
}

output "cloudwatch_log_group_name" {
  description = "CloudWatch Logs group name"
  value       = aws_cloudwatch_log_group.ecs_mailserver_mx.name
}

output "execution_role_arn" {
  description = "ECS task execution role ARN"
  value       = aws_iam_role.execution_role.arn
}

output "task_role_arn" {
  description = "ECS task role ARN"
  value       = aws_iam_role.task_role.arn
}

output "ec2_instance_id" {
  description = "EC2 MX Gateway instance ID"
  value       = aws_instance.mailserver_mx.id
}

output "ec2_instance_public_ip" {
  description = "EC2 MX Gateway public IP (Elastic IP)"
  value       = aws_eip.mailserver_eip.public_ip
}

output "ec2_instance_private_ip" {
  description = "EC2 MX Gateway private IP"
  value       = aws_instance.mailserver_mx.private_ip
}

output "ec2_cloudwatch_log_group" {
  description = "CloudWatch Logs group for EC2"
  value       = aws_cloudwatch_log_group.ec2_mx_logs.name
}
