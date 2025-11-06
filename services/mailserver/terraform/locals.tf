# ============================================================================
# Terraform Locals
# ============================================================================
# Purpose: Shared derived values used across multiple resources.
# ============================================================================

locals {
  is_staging       = terraform.workspace == "staging"
  workspace_suffix = local.is_staging ? "-staging" : ""

  ec2_log_group_name     = "/ec2/mailserver-mx${local.workspace_suffix}"
  ec2_log_group_tag_name = "mailserver-mx-ec2-logs${local.workspace_suffix}"

  ec2_role_name              = "mailserver-ec2-mx-role${local.workspace_suffix}"
  ec2_secrets_policy_name    = "mailserver-ec2-secrets-policy${local.workspace_suffix}"
  ec2_cloudwatch_policy_name = "mailserver-ec2-cloudwatch-policy${local.workspace_suffix}"
  ec2_profile_name           = "mailserver-ec2-mx-profile${local.workspace_suffix}"
  ec2_instance_name          = "mailserver-mx-ec2${local.workspace_suffix}"

  user_data_filename = local.is_staging ? "user_data_staging.sh" : "user_data.sh"

  ecs_log_group_name     = "/ecs/mailserver-mx${local.workspace_suffix}"
  ecs_log_group_tag_name = "mailserver-mx-logs${local.workspace_suffix}"

  ecs_execution_role_name   = "mailserver-execution-role${local.workspace_suffix}"
  ecs_task_role_name        = "mailserver-task-role${local.workspace_suffix}"
  ecs_execution_policy_name = "mailserver-execution-secrets-access${local.workspace_suffix}"
  ecs_task_policy_name      = "mailserver-secrets-access${local.workspace_suffix}"
}
