#!/usr/bin/env bash
# =============================================================================
# S3 Server Access Logging Setup (Audit Trail)
# Version: 1.0.0
#
# Configures S3 server access logging for compliance audit trail.
# Logs all access to l9-backups and l9-blobs buckets.
#
# GOVERNANCE: IGOR_ONLY
# =============================================================================

set -euo pipefail

# Configuration
SOURCE_BUCKETS="${S3_SOURCE_BUCKETS:-l9-backups l9-blobs l9-files}"
AUDIT_BUCKET="${S3_AUDIT_BUCKET:-l9-audit}"
REGION="${S3_REGION:-us-east-1}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  S3 Audit Logging Setup${NC}"
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

# =============================================================================
# 1. Create Audit Bucket
# =============================================================================

echo ""
echo -e "${BLUE}1. Creating audit bucket: ${AUDIT_BUCKET}...${NC}"

if aws s3api head-bucket --bucket "$AUDIT_BUCKET" 2>/dev/null; then
    echo -e "${GREEN}✓ Audit bucket already exists${NC}"
else
    if [[ "$REGION" == "us-east-1" ]]; then
        aws s3api create-bucket --bucket "$AUDIT_BUCKET" --region "$REGION"
    else
        aws s3api create-bucket --bucket "$AUDIT_BUCKET" --region "$REGION" \
            --create-bucket-configuration LocationConstraint="$REGION"
    fi
    echo -e "${GREEN}✓ Audit bucket created${NC}"
fi

# =============================================================================
# 2. Configure Audit Bucket Policy
# =============================================================================

echo ""
echo -e "${BLUE}2. Configuring audit bucket policy...${NC}"

# Allow S3 logging service to write to audit bucket
AUDIT_BUCKET_POLICY=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "S3ServerAccessLogsPolicy",
            "Effect": "Allow",
            "Principal": {
                "Service": "logging.s3.amazonaws.com"
            },
            "Action": "s3:PutObject",
            "Resource": "arn:aws:s3:::${AUDIT_BUCKET}/*",
            "Condition": {
                "StringEquals": {
                    "aws:SourceAccount": "${ACCOUNT_ID}"
                }
            }
        }
    ]
}
EOF
)

aws s3api put-bucket-policy \
    --bucket "$AUDIT_BUCKET" \
    --policy "$AUDIT_BUCKET_POLICY"

echo -e "${GREEN}✓ Audit bucket policy configured${NC}"

# =============================================================================
# 3. Block Public Access on Audit Bucket
# =============================================================================

echo ""
echo -e "${BLUE}3. Blocking public access on audit bucket...${NC}"

aws s3api put-public-access-block \
    --bucket "$AUDIT_BUCKET" \
    --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

echo -e "${GREEN}✓ Public access blocked${NC}"

# =============================================================================
# 4. Enable Encryption on Audit Bucket
# =============================================================================

echo ""
echo -e "${BLUE}4. Enabling encryption on audit bucket...${NC}"

aws s3api put-bucket-encryption \
    --bucket "$AUDIT_BUCKET" \
    --server-side-encryption-configuration '{
        "Rules": [{
            "ApplyServerSideEncryptionByDefault": {
                "SSEAlgorithm": "AES256"
            },
            "BucketKeyEnabled": true
        }]
    }'

echo -e "${GREEN}✓ Encryption enabled${NC}"

# =============================================================================
# 5. Set Lifecycle Policy on Audit Bucket (90-day retention)
# =============================================================================

echo ""
echo -e "${BLUE}5. Setting audit log retention policy (90 days)...${NC}"

AUDIT_LIFECYCLE=$(cat <<EOF
{
    "Rules": [
        {
            "ID": "RetainAuditLogs90Days",
            "Status": "Enabled",
            "Filter": {},
            "Expiration": {
                "Days": 90
            },
            "Transitions": [
                {
                    "Days": 30,
                    "StorageClass": "GLACIER_IR"
                }
            ]
        }
    ]
}
EOF
)

aws s3api put-bucket-lifecycle-configuration \
    --bucket "$AUDIT_BUCKET" \
    --lifecycle-configuration "$AUDIT_LIFECYCLE"

echo -e "${GREEN}✓ Audit log retention: 90 days (Glacier after 30)${NC}"

# =============================================================================
# 6. Enable Logging on Source Buckets
# =============================================================================

echo ""
echo -e "${BLUE}6. Enabling access logging on source buckets...${NC}"

for bucket in $SOURCE_BUCKETS; do
    echo -e "${BLUE}   Configuring logging for: ${bucket}${NC}"
    
    # Check if bucket exists
    if ! aws s3api head-bucket --bucket "$bucket" 2>/dev/null; then
        echo -e "${YELLOW}   ⚠ Bucket ${bucket} does not exist - skipping${NC}"
        continue
    fi
    
    # Configure logging
    LOGGING_CONFIG=$(cat <<EOF
{
    "LoggingEnabled": {
        "TargetBucket": "${AUDIT_BUCKET}",
        "TargetPrefix": "${bucket}/",
        "TargetObjectKeyFormat": {
            "PartitionedPrefix": {
                "PartitionDateSource": "EventTime"
            }
        }
    }
}
EOF
)
    
    aws s3api put-bucket-logging \
        --bucket "$bucket" \
        --bucket-logging-status "$LOGGING_CONFIG"
    
    echo -e "${GREEN}   ✓ Logging enabled: ${bucket} → ${AUDIT_BUCKET}/${bucket}/${NC}"
done

# =============================================================================
# 7. Object Lock (Optional - for immutable compliance)
# =============================================================================

echo ""
echo -e "${YELLOW}7. Object Lock (SKIPPED - requires bucket recreation)${NC}"
echo -e "${YELLOW}   For immutable audit logs, create a new bucket with Object Lock enabled:${NC}"
echo -e "${YELLOW}   aws s3api create-bucket --bucket l9-audit-immutable --object-lock-enabled-for-bucket${NC}"

# =============================================================================
# Summary
# =============================================================================

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ S3 Audit Logging Setup Complete${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Audit Bucket: s3://${AUDIT_BUCKET}"
echo "Region: $REGION"
echo ""
echo "Features enabled:"
echo "  ✓ Server access logging"
echo "  ✓ Encryption (SSE-S3)"
echo "  ✓ Public access blocked"
echo "  ✓ 90-day retention (Glacier after 30 days)"
echo ""
echo "Source buckets logging to audit:"
for bucket in $SOURCE_BUCKETS; do
    if aws s3api head-bucket --bucket "$bucket" 2>/dev/null; then
        echo "  ✓ ${bucket} → ${AUDIT_BUCKET}/${bucket}/"
    fi
done
echo ""
echo -e "${BLUE}Log format: ${AUDIT_BUCKET}/<source-bucket>/[EventTime]/<log-file>${NC}"
echo ""
echo "Example query (via S3 Select or Athena):"
echo "  aws s3 ls s3://${AUDIT_BUCKET}/l9-backups/ --recursive | head"
echo ""
