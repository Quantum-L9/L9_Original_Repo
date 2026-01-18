#!/usr/bin/env bash
# =============================================================================
# L9 S3 Backup Bucket Setup
# Version: 1.0.0
#
# One-time setup script to create S3 bucket with lifecycle policy.
# Run this from your Mac (not VPS).
#
# GOVERNANCE: IGOR_ONLY
# =============================================================================

set -euo pipefail

# Configuration
BUCKET_NAME="${S3_BUCKET:-l9-backups}"
REGION="${S3_REGION:-us-east-1}"
RETENTION_DAYS=30

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  L9 S3 Backup Bucket Setup${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI not installed${NC}"
    echo "Install with: brew install awscli"
    exit 1
fi

# Check credentials
echo -e "${BLUE}Checking AWS credentials...${NC}"
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}Error: AWS credentials not configured${NC}"
    echo "Run: aws configure"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✓ Authenticated as account: $ACCOUNT_ID${NC}"

# Check if bucket exists
echo ""
echo -e "${BLUE}Checking if bucket exists...${NC}"
if aws s3api head-bucket --bucket "$BUCKET_NAME" 2>/dev/null; then
    echo -e "${GREEN}✓ Bucket '$BUCKET_NAME' already exists${NC}"
else
    echo -e "${YELLOW}Creating bucket '$BUCKET_NAME' in $REGION...${NC}"
    
    if [[ "$REGION" == "us-east-1" ]]; then
        aws s3api create-bucket --bucket "$BUCKET_NAME" --region "$REGION"
    else
        aws s3api create-bucket --bucket "$BUCKET_NAME" --region "$REGION" \
            --create-bucket-configuration LocationConstraint="$REGION"
    fi
    
    echo -e "${GREEN}✓ Bucket created${NC}"
fi

# Set lifecycle policy
echo ""
echo -e "${BLUE}Setting lifecycle policy (${RETENTION_DAYS}-day retention)...${NC}"

LIFECYCLE_POLICY=$(cat <<EOF
{
    "Rules": [
        {
            "ID": "AutoExpire${RETENTION_DAYS}Days",
            "Status": "Enabled",
            "Filter": {},
            "Expiration": {
                "Days": ${RETENTION_DAYS}
            },
            "NoncurrentVersionExpiration": {
                "NoncurrentDays": 7
            }
        }
    ]
}
EOF
)

aws s3api put-bucket-lifecycle-configuration \
    --bucket "$BUCKET_NAME" \
    --lifecycle-configuration "$LIFECYCLE_POLICY"

echo -e "${GREEN}✓ Lifecycle policy set${NC}"

# Enable versioning (optional but recommended)
echo ""
echo -e "${BLUE}Enabling versioning...${NC}"
aws s3api put-bucket-versioning \
    --bucket "$BUCKET_NAME" \
    --versioning-configuration Status=Enabled

echo -e "${GREEN}✓ Versioning enabled${NC}"

# Block public access
echo ""
echo -e "${BLUE}Blocking public access...${NC}"
aws s3api put-public-access-block \
    --bucket "$BUCKET_NAME" \
    --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

echo -e "${GREEN}✓ Public access blocked${NC}"

# Summary
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ S3 Bucket Setup Complete${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Bucket: s3://${BUCKET_NAME}"
echo "Region: $REGION"
echo "Retention: ${RETENTION_DAYS} days (auto-delete)"
echo "Versioning: Enabled"
echo "Public Access: Blocked"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Copy AWS credentials to VPS: ~/.aws/credentials"
echo "2. Set cron job on VPS:"
echo "   crontab -e"
echo "   0 */12 * * * /opt/l9/scripts/backup/backup_l9_memory.sh >> /var/log/l9-backup.log 2>&1"
echo ""
