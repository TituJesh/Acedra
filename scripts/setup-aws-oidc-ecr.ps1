<#
.SYNOPSIS
    Automated setup script for AWS ECR and GitHub Actions OIDC federation.
.DESCRIPTION
    Provisions Amazon ECR repository, GitHub OIDC Identity Provider (if not already present),
    and an IAM Role with least-privilege permissions scoped to the GitHub repository.
.EXAMPLE
    .\scripts\setup-aws-oidc-ecr.ps1 -AwsRegion "ap-south-1" -GitHubRepo "TituJesh/Acedra"
#>

[CmdletBinding()]
param(
    [string]$AwsRegion = "ap-south-1",
    [string]$EcrRepo = "acedra-backend",
    [string]$GitHubRepo = "TituJesh/Acedra",
    [string]$RoleName = "AcedraGitHubActionsECRRole",
    [string]$PolicyName = "AcedraECRPushPolicy"
)

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Acedra AWS ECR & GitHub Actions OIDC Setup Automation    " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Verify AWS CLI is installed and authenticated
Write-Host "`n[1/6] Verifying AWS CLI authentication..." -ForegroundColor Yellow
try {
    $callerIdentityJson = aws sts get-caller-identity --output json 2>$null
    if (-not $callerIdentityJson) {
        throw "AWS CLI returned empty identity."
    }
    $callerIdentity = $callerIdentityJson | ConvertFrom-Json
    $accountId = $callerIdentity.Account
    Write-Host " [+] Authenticated to AWS Account ID: $accountId ($($callerIdentity.Arn))" -ForegroundColor Green
} catch {
    Write-Host " [!] AWS CLI is not configured or authenticated." -ForegroundColor Red
    Write-Host "     Please run 'aws configure' first with your AWS credentials." -ForegroundColor Red
    exit 1
}

# 2. Check / Create GitHub OIDC Identity Provider
Write-Host "`n[2/6] Checking GitHub OIDC Identity Provider in IAM..." -ForegroundColor Yellow
$oidcUrl = "token.actions.githubusercontent.com"
$oidcProviderArn = "arn:aws:iam::${accountId}:oidc-provider/${oidcUrl}"

$existingProviders = aws iam list-open-id-connect-providers --query "OpenIDConnectProviderList[*].Arn" --output text 2>$null

if ($existingProviders -match $oidcUrl) {
    Write-Host " [+] OIDC Provider already exists: $oidcProviderArn" -ForegroundColor Green
} else {
    Write-Host " [*] Creating GitHub OIDC Provider..." -ForegroundColor Cyan
    aws iam create-open-id-connect-provider `
        --url "https://${oidcUrl}" `
        --client-id-list "sts.amazonaws.com" `
        --thumbprint-list "6938fd4d98bab03faadb97b34396831e3780aea1" "1c5860a5f213b826072174ee934fc5bc60e1893d" `
        --tags Key=Project,Value=Acedra | Out-Null
    Write-Host " [+] GitHub OIDC Provider created: $oidcProviderArn" -ForegroundColor Green
}

# 3. Check / Create Amazon ECR Repository
Write-Host "`n[3/6] Checking Amazon ECR Repository '$EcrRepo'..." -ForegroundColor Yellow
$ecrCheck = aws ecr describe-repositories --repository-names $EcrRepo --region $AwsRegion 2>$null

if ($LASTEXITCODE -eq 0) {
    Write-Host " [+] ECR repository already exists." -ForegroundColor Green
} else {
    Write-Host " [*] Creating ECR repository '$EcrRepo' in region $AwsRegion..." -ForegroundColor Cyan
    aws ecr create-repository `
        --repository-name $EcrRepo `
        --image-tag-mutability MUTABLE `
        --image-scanning-configuration scanOnPush=true `
        --encryption-configuration encryptionType=AES256 `
        --region $AwsRegion `
        --tags Key=Project,Value=Acedra | Out-Null
    Write-Host " [+] ECR repository created." -ForegroundColor Green
}

$ecrUri = "${accountId}.dkr.ecr.${AwsRegion}.amazonaws.com/${EcrRepo}"
Write-Host " [+] ECR URI: $ecrUri" -ForegroundColor Green

# 4. Configure Lifecycle Policy
Write-Host "`n[4/6] Setting ECR Lifecycle Policy (Auto-cleanup)..." -ForegroundColor Yellow
$lifecyclePolicy = @'
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Expire untagged images older than 7 days",
      "selection": {
        "tagStatus": "untagged",
        "countType": "sinceImagePushed",
        "countUnit": "days",
        "countNumber": 7
      },
      "action": { "type": "expire" }
    },
    {
      "rulePriority": 2,
      "description": "Retain latest 20 tagged production images",
      "selection": {
        "tagStatus": "tagged",
        "tagPrefixList": ["latest", "v", "sha-"],
        "countType": "imageCountMoreThan",
        "countNumber": 20
      },
      "action": { "type": "expire" }
    }
  ]
}
'@

$tempPolicyFile = [System.IO.Path]::GetTempFileName()
Set-Content -Path $tempPolicyFile -Value $lifecyclePolicy -Encoding utf8
aws ecr put-lifecycle-policy --repository-name $EcrRepo --lifecycle-policy-text "file://$tempPolicyFile" --region $AwsRegion | Out-Null
Remove-Item $tempPolicyFile -Force
Write-Host " [+] ECR Lifecycle Policy applied." -ForegroundColor Green

# 5. Create or Update IAM Role for OIDC
Write-Host "`n[5/6] Creating / Updating IAM Role '$RoleName'..." -ForegroundColor Yellow
$trustPolicy = @"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "GitHubActionsFederatedAssumeRole",
      "Effect": "Allow",
      "Principal": {
        "Federated": "$oidcProviderArn"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:${GitHubRepo}:*"
        }
      }
    }
  ]
}
"@

$tempTrustFile = [System.IO.Path]::GetTempFileName()
Set-Content -Path $tempTrustFile -Value $trustPolicy -Encoding utf8

$roleArn = ""
try {
    $existingRole = aws iam get-role --role-name $RoleName --output json 2>$null | ConvertFrom-Json
    Write-Host " [*] Role exists. Updating trust relationship policy..." -ForegroundColor Cyan
    aws iam update-assume-role-policy --role-name $RoleName --policy-document "file://$tempTrustFile" | Out-Null
    $roleArn = $existingRole.Role.Arn
} catch {
    Write-Host " [*] Creating IAM Role '$RoleName'..." -ForegroundColor Cyan
    $newRole = aws iam create-role `
        --role-name $RoleName `
        --assume-role-policy-document "file://$tempTrustFile" `
        --description "Role for GitHub Actions to push images to Acedra ECR" `
        --tags Key=Project,Value=Acedra Key=Repository,Value=$GitHubRepo `
        --output json | ConvertFrom-Json
    $roleArn = $newRole.Role.Arn
}
Remove-Item $tempTrustFile -Force
Write-Host " [+] IAM Role ARN: $roleArn" -ForegroundColor Green

# 6. Attach ECR Permissions Policy
Write-Host "`n[6/6] Attaching ECR Push/Pull Policy..." -ForegroundColor Yellow
$ecrRepoArn = "arn:aws:ecr:${AwsRegion}:${accountId}:repository/${EcrRepo}"
$permissionsPolicy = @"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECRAuthToken",
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ECRPushPull",
      "Effect": "Allow",
      "Action": [
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
      ],
      "Resource": "$ecrRepoArn"
    }
  ]
}
"@

$tempPermFile = [System.IO.Path]::GetTempFileName()
Set-Content -Path $tempPermFile -Value $permissionsPolicy -Encoding utf8

aws iam put-role-policy `
    --role-name $RoleName `
    --policy-name $PolicyName `
    --policy-document "file://$tempPermFile" | Out-Null
Remove-Item $tempPermFile -Force

Write-Host " [+] Permissions policy attached successfully." -ForegroundColor Green

# Output Instructions
Write-Host "`n============================================================" -ForegroundColor Green
Write-Host "  SETUP COMPLETE! Next Step: Configure GitHub Repository   " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "Navigate to: https://github.com/$GitHubRepo/settings/secrets/actions" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Under 'Repository secrets', add:" -ForegroundColor Yellow
Write-Host "   Name:  AWS_ROLE_ARN" -ForegroundColor White
Write-Host "   Value: $roleArn" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. (Optional) Under 'Repository variables', add:" -ForegroundColor Yellow
Write-Host "   Name:  AWS_REGION       Value: $AwsRegion" -ForegroundColor White
Write-Host "   Name:  ECR_REPOSITORY   Value: $EcrRepo" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor Green
