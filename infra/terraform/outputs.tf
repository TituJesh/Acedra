output "aws_region" {
  description = "The AWS Region where resources are provisioned"
  value       = var.aws_region
}

output "ecr_repository_name" {
  description = "The name of the Amazon ECR repository"
  value       = aws_ecr_repository.acedra.name
}

output "ecr_repository_url" {
  description = "The URL of the Amazon ECR repository to push Docker images to"
  value       = aws_ecr_repository.acedra.repository_url
}

output "github_actions_role_arn" {
  description = "The IAM Role ARN to set in GitHub Repository Secret 'AWS_ROLE_ARN'"
  value       = aws_iam_role.github_actions.arn
}

output "github_secrets_instructions" {
  description = "Instructions for configuring GitHub Actions repository secrets & variables"
  value       = <<-EOT
    =============================================================================
    GitHub Repository Setup (https://github.com/${var.github_repository}/settings/secrets/actions)
    =============================================================================
    1. Go to: Settings -> Secrets and variables -> Actions
    2. Add Repository Secret:
       - Name:  AWS_ROLE_ARN
       - Value: ${aws_iam_role.github_actions.arn}

    3. (Optional) Under 'Variables' tab:
       - Name:  AWS_REGION
       - Value: ${var.aws_region}
       - Name:  ECR_REPOSITORY
       - Value: ${aws_ecr_repository.acedra.name}
    =============================================================================
  EOT
}
