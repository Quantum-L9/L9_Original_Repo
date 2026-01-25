# ADR 0066: AWS S3 Storage Architecture

- **Status**: Accepted
- **Date**: 2026-01-25
- **Deciders**: Igor Beylin, L9 Architecture Team
- **GMP**: GMP-S3-INFRASTRUCTURE

## Context and Problem Statement

L9 requires reliable, scalable storage for:
1. Database backups (PostgreSQL, Neo4j)
2. Large content offloading (blob storage for packets >512KB)
3. File storage (Slack attachments, documents)
4. Audit logs for compliance

Local storage is insufficient for disaster recovery and cross-region availability.

## Decision Drivers

- **Durability**: 11 9's durability for critical data
- **Scalability**: Handle growing data without infrastructure changes
- **Security**: Encryption at rest, versioning, access logging
- **Cost**: Pay-per-use, lifecycle policies for cost optimization
- **Compliance**: Immutable audit trail for governance

## Considered Options

1. **Local disk storage**: Simple but no DR, limited scalability
2. **Self-hosted MinIO**: S3-compatible but requires maintenance
3. **AWS S3**: Managed, highly durable, rich feature set
4. **Google Cloud Storage**: Similar to S3 but different ecosystem

## Decision Outcome

Chosen option: **AWS S3** (us-east-1 region), because it provides the best balance of durability, features, and ecosystem integration.

### S3 Bucket Architecture

| Bucket | Purpose | Lifecycle | Versioning |
|--------|---------|-----------|------------|
| `l9-backups` | Database backups (PostgreSQL, Neo4j) | 30 days → Glacier | ✅ Enabled |
| `l9-blobs` | Large content offloading (>512KB) | 90 days retention | ✅ Enabled |
| `l9-files` | Slack files, documents | 365 days retention | ✅ Enabled |
| `l9-audit` | S3 access logs, compliance | 7 years retention | ❌ (immutable) |

### Key Structure

```
l9-backups/
├── c1/                      # C1 Hetzner server backups
│   ├── postgres/            # PostgreSQL dumps
│   │   └── YYYY-MM-DD/
│   └── neo4j/               # Neo4j backups
│       └── YYYY-MM-DD/
└── local/                   # Local dev backups (optional)

l9-blobs/
└── packets/                 # Blob offloading
    └── {hash[0:4]}/         # Partitioned by hash prefix
        └── {sha256_hash}    # Content-addressed storage

l9-files/
└── slack/                   # Slack attachments
    └── {file_id}/
        └── {filename}

l9-audit/
└── access-logs/             # S3 server access logs
    └── {bucket}/
        └── YYYY-MM-DD/
```

### Security Configuration

- **Encryption**: SSE-S3 (AES-256) on all buckets
- **Block Public Access**: Enabled on all buckets
- **Versioning**: Enabled for data recovery
- **Cross-Region Replication**: Optional for DR (us-east-1 → us-west-2)

### Backup Schedule

- **C1 Memory Backups**: Every 12 hours (`0 */12 * * *`)
- **Retention**: 30 days in S3, then Glacier for 1 year

## Implementation

### Scripts Created

| Script | Purpose |
|--------|---------|
| `scripts/backup/backup_c1_memory.sh` | Backup C1 PostgreSQL + Neo4j to S3 |
| `scripts/backup/enable_s3_versioning.sh` | Enable versioning, encryption, lifecycle |
| `scripts/backup/setup_s3_audit.sh` | Configure S3 access logging |

### Code Integration

| Module | Purpose |
|--------|---------|
| `memory/blob_store.py` | S3 client for large content offloading |
| `services/slack_files.py` | S3 backend for Slack file storage |

## Positive Consequences

- 11 9's durability for all critical data
- Automatic lifecycle management reduces costs
- Versioning enables recovery from accidental deletions
- Audit logs provide compliance trail
- Presigned URLs enable secure, time-limited access

## Negative Consequences

- AWS dependency and vendor lock-in
- Network latency for blob retrieval
- S3 costs scale with data volume
- Requires IAM configuration

## IAM Permissions Required

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::l9-backups/*",
        "arn:aws:s3:::l9-blobs/*",
        "arn:aws:s3:::l9-files/*"
      ]
    }
  ]
}
```

## Related

- ADR 0067: AWS Secrets Manager Integration
- ADR 0058: C1 Kubernetes Deployment Workflow
- `memory/blob_store.py` - Blob storage implementation
- Commit: `8cec1524` (GMP-S3-INFRASTRUCTURE)
