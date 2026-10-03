variable "aws_region" {
  description = "AWS region for ECR repository and infrastructure resources"
  type        = string
  default     = "ap-south-1"
}

variable "environment" {
  description = "Deployment environment name (e.g. production, staging, dev)"
  type        = string
  default     = "production"
}

variable "ecr_repository_name" {
  description = "Name of the Amazon ECR repository for the Acedra backend"
  type        = string
  default     = "acedra-backend"
}

variable "github_repository" {
  description = "GitHub repository in 'owner/repo' format (e.g. TituJesh/Acedra)"
  type        = string
  default     = "TituJesh/Acedra"
}

variable "iam_role_name" {
  description = "Name of the IAM role to create for GitHub Actions OIDC federation"
  type        = string
  default     = "AcedraGitHubActionsECRRole"
}

variable "create_oidc_provider" {
  description = "Whether to create the GitHub Actions OIDC provider. Set to false if it already exists in your AWS account."
  type        = bool
  default     = true
}
