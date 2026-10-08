data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.name

  oidc_provider_arn = var.create_oidc_provider ? (
    length(aws_iam_openid_connect_provider.github) > 0 ? aws_iam_openid_connect_provider.github[0].arn : ""
  ) : "arn:aws:iam::${local.account_id}:oidc-provider/token.actions.githubusercontent.com"
}

# ------------------------------------------------------------------------------
# GitHub Actions OIDC Identity Provider (Created once per AWS account)
# ------------------------------------------------------------------------------
resource "aws_iam_openid_connect_provider" "github" {
  count = var.create_oidc_provider ? 1 : 0

  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [
    "1c58a3a8518e8759bf075b76b750d4f2df264fcd",
    "06d927fecd0a84aeba28aad1d808139470fe95c3"
  ]

  tags = {
    Name = "GitHub-Actions-OIDC-Provider"
  }
}

# ------------------------------------------------------------------------------
# Amazon ECR Repository for Acedra
# ------------------------------------------------------------------------------
resource "aws_ecr_repository" "acedra" {
  name                 = var.ecr_repository_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name        = var.ecr_repository_name
    Application = "Acedra"
  }
}

# ------------------------------------------------------------------------------
# ECR Lifecycle Policy (Auto-cleanup stale and untagged images to reduce costs)
# ------------------------------------------------------------------------------
resource "aws_ecr_lifecycle_policy" "acedra_cleanup" {
  repository = aws_ecr_repository.acedra.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged images older than 7 days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 7
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Retain the latest 20 tagged production images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["latest", "v", "sha-"]
          countType     = "imageCountMoreThan"
          countNumber   = 20
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# ------------------------------------------------------------------------------
# IAM Role for GitHub Actions with OIDC Web Identity Federation
# ------------------------------------------------------------------------------
resource "aws_iam_role" "github_actions" {
  name        = var.iam_role_name
  description = "Role assumed by GitHub Actions for building and pushing Acedra images to ECR"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "GitHubActionsFederatedAssumeRole"
        Effect = "Allow"
        Principal = {
          Federated = local.oidc_provider_arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            "token.actions.githubusercontent.com:sub" = [
              "repo:${var.github_repository}:*",
              "repo:${lower(var.github_repository)}:*",
              "repo:${split("/", var.github_repository)[0]}*/${split("/", var.github_repository)[1]}*:*"
            ]
          }
        }
      }
    ]
  })

  tags = {
    Name        = var.iam_role_name
    Repository  = var.github_repository
  }
}

# ------------------------------------------------------------------------------
# IAM Policy: Least-Privilege Permissions for ECR Push & Pull
# ------------------------------------------------------------------------------
resource "aws_iam_policy" "ecr_push_policy" {
  name        = "${var.iam_role_name}-Policy"
  description = "Allows GitHub Actions runner to authenticate and push images to Acedra ECR repository"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ECRAuthToken"
        Effect   = "Allow"
        Action   = [
          "ecr:GetAuthorizationToken"
        ]
        Resource = "*"
      },
      {
        Sid      = "ECRPushPull"
        Effect   = "Allow"
        Action   = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:GetRepositoryPolicy",
          "ecr:DescribeRepositories",
          "ecr:ListImages",
          "ecr:DescribeImages",
          "ecr:BatchGetImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:PutImage"
        ]
        Resource = aws_ecr_repository.acedra.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "attach_ecr_push" {
  role       = aws_iam_role.github_actions.name
  policy_arn = aws_iam_policy.ecr_push_policy.arn
}
