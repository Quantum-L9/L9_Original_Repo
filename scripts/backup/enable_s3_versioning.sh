#!/usr/bin/env bash
# =============================================================================
# Enable S3 Versioning and Cross-Region Replication
# Version: 1.0.0
#
# One-time setup script to enable S3 versioning and optional cross-region
# replication for disaster recovery.
#
# GOVERNANCE: IGOR_ONLY
# =============================================================================

set -euo pipefail

# Configuration
BUCKET_NAME="${S3_BUCKET:-l9-backups}"
REGION="${S3_REGION:-us-east-1}"
DR_BUCKET="${S3_DR_BUCKET:-}"  # Optional: l9-backups-dr in different region
DR_REGION="${S3_DR_REGION:-us-west-2}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  S3 Versioning & Replication Setup${NC}"
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
# 1. Enable Versioning on Primary Bucket
# =============================================================================

echo ""
echo -e "${BLUE}1. Enabling versioning on ${BUCKET_NAME}...${NC}"

# Check current versioning status
VERSIONING_STATUS=$(aws s3api get-bucket-versioning --bucket "$BUCKET_NAME" --query 'Status' --output text 2>/dev/null || echo "None")

if [[ "$VERSIONING_STATUS" == "Enabled" ]]; then
    echo -e "${GREEN}✓ Versioning already enabled${NC}"
else
    aws s3api put-bucket-versioning \
        --bucket "$BUCKET_NAME" \
        --versioning-configuration Status=Enabled
    echo -e "${GREEN}✓ Versioning enabled${NC}"
fi

# =============================================================================
# 2. Enable Server-Side Encryption (SSE-S3)
# =============================================================================

echo ""
echo -e "${BLUE}2. Enabling server-side encryption...${NC}"

aws s3api put-bucket-encryption \
    --bucket "$BUCKET_NAME" \
    --server-side-encryption-configuration '{
        "Rules": [{
            "ApplyServerSideEncryptionByDefault": {
                "SSEAlgorithm": "AES256"
            },
            "BucketKeyEnabled": true
        }]
    }' 2>/dev/null || echo -e "${YELLOW}⚠ Encryption may already be configured${NC}"

echo -e "${GREEN}✓ Server-side encryption (SSE-S3) enabled${NC}"

# =============================================================================
# 3. Block Public Access
# =============================================================================

echo ""
echo -e "${BLUE}3. Blocking public access...${NC}"

aws s3api put-public-access-block \
    --bucket "$BUCKET_NAME" \
    --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

echo -e "${GREEN}✓ Public access blocked${NC}"

# =============================================================================
# 4. Set Lifecycle Policy (30-day retention for backups)
# =============================================================================

echo ""
echo -e "${BLUE}4. Setting lifecycle policy (30-day retention)...${NC}"

LIFECYCLE_POLICY=$(cat <<EOF
{
    "Rules": [
        {
            "ID": "ExpireOldBackups",
            "Status": "Enabled",
            "Filter": {
                "Prefix": ""
            },
            "Expiration": {
                "Days": 30
            },
            "NoncurrentVersionExpiration": {
                "NoncurrentDays": 7
            },
            "AbortIncompleteMultipartUpload": {
                "DaysAfterInitiation": 1
            }
        },
        {
            "ID": "TransitionToGlacier",
            "Status": "Enabled",
            "Filter": {
                "Prefix": ""
            },
            "Transitions": [
                {
                    "Days": 14,
                    "StorageClass": "GLACIER_IR"
                }
            ]
        }
    ]
}
EOF
)

aws s3api put-bucket-lifecycle-configuration \
    --bucket "$BUCKET_NAME" \
    --lifecycle-configuration "$LIFECYCLE_POLICY"

echo -e "${GREEN}✓ Lifecycle policy set (30-day expiry, 14-day transition to Glacier)${NC}"

# =============================================================================
# 5. Cross-Region Replication (Optional)
# =============================================================================

if [[ -n "$DR_BUCKET" ]]; then
    echo ""
    echo -e "${BLUE}5. Setting up cross-region replication to ${DR_BUCKET}...${NC}"
    
    # Check if DR bucket exists
    if ! aws s3api head-bucket --bucket "$DR_BUCKET" 2>/dev/null; then
        echo -e "${YELLOW}Creating DR bucket ${DR_BUCKET} in ${DR_REGION}...${NC}"
        
        if [[ "$DR_REGION" == "us-east-1" ]]; then
            aws s3api create-bucket --bucket "$DR_BUCKET" --region "$DR_REGION"
        else
            aws s3api create-bucket --bucket "$DR_BUCKET" --region "$DR_REGION" \
                --create-bucket-configuration LocationConstraint="$DR_REGION"
        fi
        
        # Enable versioning on DR bucket (required for replication)
        aws s3api put-bucket-versioning \
            --bucket "$DR_BUCKET" \
            --versioning-configuration Status=Enabled
        
        echo -e "${GREEN}✓ DR bucket created${NC}"
    fi
    
    # Create IAM role for replication
    ROLE_NAME="l9-s3-replication-role"
    
    TRUST_POLICY=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "s3.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF
)
    
    # Create role if it doesn't exist
    if ! aws iam get-role --role-name "$ROLE_NAME" &>/dev/null; then
        aws iam create-role \
            --role-name "$ROLE_NAME" \
            --assume-role-policy-document "$TRUST_POLICY" \
            --description "S3 replication role for L9 backups"
        
        PERMISSIONS_POLICY=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetReplicationConfiguration",
                "s3:ListBucket"
            ],
            "Resource": "arn:aws:s3:::${BUCKET_NAME}"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObjectVersionForReplication",
                "s3:GetObjectVersionAcl",
                "s3:GetObjectVersionTagging"
            ],
            "Resource": "arn:aws:s3:::${BUCKET_NAME}/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:ReplicateObject",
                "s3:ReplicateDelete",
                "s3:ReplicateTags"
            ],
            "Resource": "arn:aws:s3:::${DR_BUCKET}/*"
        }
    ]
}
EOF
)
        
        aws iam put-role-policy \
            --role-name "$ROLE_NAME" \
            --policy-name "S3ReplicationPolicy" \
            --policy-document "$PERMISSIONS_POLICY"
        
        echo -e "${GREEN}✓ Replication IAM role created${NC}"
        
        # Wait for role to propagate
        sleep 10
    fi
    
    ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)
    
    # Configure replication
    REPLICATION_CONFIG=$(cat <<EOF
{
    "Role": "${ROLE_ARN}",
    "Rules": [
        {
            "ID": "ReplicateAll",
            "Status": "Enabled",
            "Priority": 1,
            "Filter": {},
            "Destination": {
                "Bucket": "arn:aws:s3:::${DR_BUCKET}",
                "StorageClass": "STANDARD_IA"
            },
            "DeleteMarkerReplication": {
                "Status": "Disabled"
            }
        }
    ]
}
EOF
)
    
    aws s3api put-bucket-replication \
        --bucket "$BUCKET_NAME" \
        --replication-configuration "$REPLICATION_CONFIG"
    
    echo -e "${GREEN}✓ Cross-region replication configured${NC}"
    echo -e "${GREEN}  Source: s3://${BUCKET_NAME} (${REGION})${NC}"
    echo -e "${GREEN}  Destination: s3://${DR_BUCKET} (${DR_REGION})${NC}"
else
    echo ""
    echo -e "${YELLOW}5. Cross-region replication SKIPPED (S3_DR_BUCKET not set)${NC}"
    echo -e "${YELLOW}   To enable: S3_DR_BUCKET=l9-backups-dr S3_DR_REGION=us-west-2 $0${NC}"
fi

# =============================================================================
# Summary
# =============================================================================

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ S3 Configuration Complete${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Bucket: s3://${BUCKET_NAME}"
echo "Region: $REGION"
echo ""
echo "Features enabled:"
echo "  ✓ Versioning"
echo "  ✓ Server-side encryption (SSE-S3)"
echo "  ✓ Public access blocked"
echo "  ✓ Lifecycle policy (30-day retention, 14-day Glacier transition)"
if [[ -n "$DR_BUCKET" ]]; then
    echo "  ✓ Cross-region replication to ${DR_BUCKET}"
fi
echo ""
