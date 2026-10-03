#!/usr/bin/env bash
# ==============================================================================
# Acedra: AWS ECR & GitHub Actions OIDC Setup Automation Script (Bash)
# ==============================================================================
# Usage:
#   chmod +x ./scripts/setup-aws-oidc-ecr.sh
#   ./scripts/setup-aws-oidc-ecr.sh
# ==============================================================================

set -euo pipefail

AWS_REGION="${AWS_REGION:-ap-south-1}"
ECR_REPO="${ECR_REPO:-acedra-backend}"
GITHUB_REPO="${GITHUB_REPO:-TituJesh/Acedra}"
ROLE_NAME="${ROLE_NAME:-AcedraGitHubActionsECRRole}"
POLICY_NAME="${POLICY_NAME:-AcedraECRPushPolicy}"

echo "============================================================"
echo "  Acedra AWS ECR & GitHub Actions OIDC Setup Automation    "
echo "============================================================"

# 1. Verify AWS CLI
echo ""
echo "[1/6] Verifying AWS CLI authentication..."
if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI is not installed. Please install it first."
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
CALLER_ARN=$(aws sts get-caller-identity --query "Arn" --output text)
echo " [+] Authenticated to AWS Account ID: ${ACCOUNT_ID} (${CALLER_ARN})"

# 2. Check / Create GitHub OIDC Provider
echo ""
echo "[2/6] Checking GitHub OIDC Identity Provider in IAM..."
OIDC_URL="token.actions.githubusercontent.com"
OIDC_PROVIDER_ARN="arn:aws:iam::${ACCOUNT_ID}:oidc-provider/${OIDC_URL}"

EXISTING_PROVIDERS=$(aws iam list-open-id-connect-providers --query "OpenIDConnectProviderList[*].Arn" --output text)
if echo "${EXISTING_PROVIDERS}" | grep -q "${OIDC_URL}"; then
    echo " [+] OIDC Provider already exists: ${OIDC_PROVIDER_ARN}"
else
    echo " [*] Creating GitHub OIDC Provider..."
    aws iam create-open-id-connect-provider \
        --url "https://${OIDC_URL}" \
        --client-id-list "sts.amazonaws.com" \
        --thumbprint-list "6938fd4d98bab03faadb97b34396831e3780aea1" "1c5860a5f213b826072174ee934fc5bc60e1893d" \
        --tags Key=Project,Value=Acedra > /dev/null
    echo " [+] GitHub OIDC Provider created."
fi

# 3. Check / Create ECR Repository
echo ""
echo "[3/6] Checking Amazon ECR Repository '${ECR_REPO}'..."
if aws ecr describe-repositories --repository-names "${ECR_REPO}" --region "${AWS_REGION}" &> /dev/null; then
    echo " [+] ECR repository already exists."
else
    echo " [*] Creating ECR repository '${ECR_REPO}' in region ${AWS_REGION}..."
    aws ecr create-repository \
        --repository-name "${ECR_REPO}" \
        --image-tag-mutability MUTABLE \
        --image-scanning-configuration scanOnPush=true \
        --encryption-configuration encryptionType=AES256 \
        --region "${AWS_REGION}" \
        --tags Key=Project,Value=Acedra > /dev/null
    echo " [+] ECR repository created."
fi

ECR_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}"
echo " [+] ECR URI: ${ECR_URI}"

# 4. Set Lifecycle Policy
echo ""
echo "[4/6] Setting ECR Lifecycle Policy..."
LIFECYCLE_POLICY='{
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
}'

aws ecr put-lifecycle-policy \
    --repository-name "${ECR_REPO}" \
    --lifecycle-policy-text "${LIFECYCLE_POLICY}" \
    --region "${AWS_REGION}" > /dev/null
echo " [+] ECR Lifecycle Policy applied."

# 5. Create or Update IAM Role
echo ""
echo "[5/6] Creating / Updating IAM Role '${ROLE_NAME}'..."
TRUST_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "GitHubActionsFederatedAssumeRole",
      "Effect": "Allow",
      "Principal": {
        "Federated": "${OIDC_PROVIDER_ARN}"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:${GITHUB_REPO}:*"
        }
      }
    }
  ]
}
EOF
)

if aws iam get-role --role-name "${ROLE_NAME}" &> /dev/null; then
    echo " [*] Role exists. Updating trust policy..."
    aws iam update-assume-role-policy \
        --role-name "${ROLE_NAME}" \
        --policy-document "${TRUST_POLICY}" > /dev/null
    ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
else
    echo " [*] Creating IAM Role '${ROLE_NAME}'..."
    ROLE_ARN=$(aws iam create-role \
        --role-name "${ROLE_NAME}" \
        --assume-role-policy-document "${TRUST_POLICY}" \
        --description "Role for GitHub Actions to push images to Acedra ECR" \
        --tags Key=Project,Value=Acedra Key=Repository,Value="${GITHUB_REPO}" \
        --query "Role.Arn" \
        --output text)
fi
echo " [+] IAM Role ARN: ${ROLE_ARN}"

# 6. Attach Permissions Policy
echo ""
echo "[6/6] Attaching ECR Push Policy to Role..."
ECR_REPO_ARN="arn:aws:ecr:${AWS_REGION}:${ACCOUNT_ID}:repository/${ECR_REPO}"
PERMISSIONS_POLICY=$(cat <<EOF
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
      "Resource": "${ECR_REPO_ARN}"
    }
  ]
}
EOF
)

aws iam put-role-policy \
    --role-name "${ROLE_NAME}" \
    --policy-name "${POLICY_NAME}" \
    --policy-document "${PERMISSIONS_POLICY}" > /dev/null
echo " [+] Permissions policy attached."

# Output Summary
echo ""
echo "============================================================"
echo "  SETUP COMPLETE! Next Step: Configure GitHub Repository   "
echo "============================================================"
echo "Navigate to: https://github.com/${GITHUB_REPO}/settings/secrets/actions"
echo ""
echo "1. Under 'Repository secrets', add:"
echo "   Name:  AWS_ROLE_ARN"
echo "   Value: ${ROLE_ARN}"
echo ""
echo "2. (Optional) Under 'Repository variables', add:"
echo "   Name:  AWS_REGION       Value: ${AWS_REGION}"
echo "   Name:  ECR_REPOSITORY   Value: ${ECR_REPO}"
echo "============================================================"
