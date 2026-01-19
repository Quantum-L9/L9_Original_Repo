# L9 Infrastructure as Code

Automated provisioning and configuration for L9 VPS servers.

## Quick Start (Rebuild Server)

If you just need to rebuild from backup:

```bash
# On fresh Ubuntu 22.04 VPS
curl -sL https://raw.githubusercontent.com/YOUR_REPO/l9/main/scripts/infra/bootstrap_vps.sh | \
  AWS_ACCESS_KEY="xxx" AWS_SECRET_KEY="xxx" sudo bash
```

## Full IaC Setup

### Option A: Just Bootstrap Script (Simplest)

You already have a VPS? Run the bootstrap script:

```bash
# 1. SSH to your VPS
ssh root@YOUR_VPS_IP

# 2. Run bootstrap
curl -sL https://raw.githubusercontent.com/YOUR_REPO/l9/main/scripts/infra/bootstrap_vps.sh > bootstrap.sh
chmod +x bootstrap.sh

# 3. Edit configuration
nano bootstrap.sh  # Set L9_REPO, AWS credentials, etc.

# 4. Run
sudo ./bootstrap.sh
```

### Option B: Terraform + Bootstrap (Full IaC)

Provision a new VPS from scratch:

```bash
# 1. Install Terraform
brew install terraform  # Mac
# or: apt-get install terraform  # Ubuntu

# 2. Configure
cd scripts/infra/terraform
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars  # Edit settings

# 3. Set cloud provider token
export HCLOUD_TOKEN="your-hetzner-api-token"
# or: export DIGITALOCEAN_TOKEN="..."
# or: export AWS_ACCESS_KEY_ID="..." AWS_SECRET_ACCESS_KEY="..."

# 4. Provision
terraform init
terraform plan
terraform apply

# 5. Note the IP from output
# 6. Run bootstrap on the new server
ssh admin@NEW_IP
curl -sL https://raw.githubusercontent.com/YOUR_REPO/l9/main/scripts/infra/bootstrap_vps.sh | sudo bash
```

## What Gets Provisioned

### Terraform Creates:
- Ubuntu 22.04 VPS (2 vCPU, 4GB RAM)
- Firewall (22, 80, 443 open)
- Admin user with sudo

### Bootstrap Script Installs:
- Docker + Docker Compose
- Caddy (reverse proxy)
- AWS CLI
- L9 repository
- Restores from S3 backup (if available)

## Backup ↔ Restore Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    PRODUCTION SERVER                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│  │PostgreSQL│  │  Neo4j   │  │  Caddy   │  │   systemd    │ │
│  │   +      │  │  graph   │  │ reverse  │  │   services   │ │
│  │ pgvector │  │          │  │  proxy   │  │              │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘ │
│       │             │             │               │         │
│       └─────────────┴─────────────┴───────────────┘         │
│                           │                                  │
│              backup_l9_memory.sh (every 12h)                │
│              backup_server_config.sh (manual)               │
│                           │                                  │
└───────────────────────────┼──────────────────────────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │   S3 Bucket     │
                   │  l9-backups/    │
                   │  ├── postgres/  │
                   │  ├── neo4j/     │
                   │  ├── config/    │
                   │  └── server-    │
                   │      config/    │
                   └────────┬────────┘
                            │
                            ▼
┌───────────────────────────┼──────────────────────────────────┐
│                    NEW/REBUILT SERVER                        │
│                           │                                  │
│              bootstrap_vps.sh + restore_l9_memory.sh        │
│                           │                                  │
│       ┌───────────────────┴───────────────────┐             │
│       │             │             │           │             │
│  ┌────┴─────┐  ┌────┴─────┐  ┌────┴─────┐  ┌──┴──────────┐  │
│  │PostgreSQL│  │  Neo4j   │  │  Caddy   │  │   systemd   │  │
│  │ (full    │  │ (full    │  │ (config  │  │  (services  │  │
│  │  data)   │  │  data)   │  │  from S3)│  │   from S3)  │  │
│  └──────────┘  └──────────┘  └──────────┘  └─────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

## Cost Comparison

| Provider | Specs | Cost/Month |
|----------|-------|------------|
| **Hetzner CX21** | 2 vCPU, 4GB RAM, 40GB SSD | €4.85 |
| DigitalOcean | 2 vCPU, 4GB RAM, 80GB SSD | $24 |
| AWS t3.medium | 2 vCPU, 4GB RAM, 30GB EBS | ~$30 |
| Vultr | 2 vCPU, 4GB RAM, 80GB SSD | $24 |

**Recommendation:** Hetzner CX21 is ~5x cheaper with similar performance.

## Directory Structure

```
scripts/infra/
├── README.md                    # This file
├── bootstrap_vps.sh             # Main bootstrap script
└── terraform/
    ├── main.tf                  # Terraform config
    └── terraform.tfvars.example # Example variables
```

## Cloud Provider Setup

### Hetzner (Recommended)

1. Create account: https://console.hetzner.cloud
2. Generate API token: Project → Security → API Tokens
3. Add SSH key: Project → Security → SSH Keys

```bash
export HCLOUD_TOKEN="your-token"
```

### DigitalOcean

1. Create account: https://cloud.digitalocean.com
2. Generate API token: API → Generate New Token
3. Add SSH key: Settings → Security → Add SSH Key

```bash
export DIGITALOCEAN_TOKEN="your-token"
```

### AWS

1. Create IAM user with EC2 permissions
2. Generate access keys

```bash
export AWS_ACCESS_KEY_ID="xxx"
export AWS_SECRET_ACCESS_KEY="xxx"
```

## Disaster Recovery Playbook

### Total Server Loss

1. **Provision new VPS:**
   ```bash
   cd scripts/infra/terraform
   terraform apply
   ```

2. **Bootstrap and restore:**
   ```bash
   ssh admin@NEW_IP
   curl -sL https://raw.githubusercontent.com/.../bootstrap_vps.sh | \
     AWS_ACCESS_KEY="xxx" AWS_SECRET_KEY="xxx" sudo bash
   ```

3. **Verify:**
   ```bash
   docker compose ps
   curl -s http://localhost:8000/health
   ```

### Duplicate Server (Staging/Testing)

```bash
# 1. Provision with different name
terraform apply -var="server_name=l9-staging"

# 2. Bootstrap without restore
ssh admin@STAGING_IP
sudo ./bootstrap_vps.sh --no-restore

# 3. Manually copy specific data if needed
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `L9_DOMAIN` | Your domain | - |
| `L9_EMAIL` | Email for Let's Encrypt | - |
| `L9_REPO` | Git repository URL | - |
| `L9_BRANCH` | Git branch | main |
| `ADMIN_USER` | Non-root user | admin |
| `S3_BUCKET` | S3 backup bucket | l9-backups |
| `AWS_ACCESS_KEY` | AWS access key | - |
| `AWS_SECRET_KEY` | AWS secret key | - |
| `AWS_REGION` | AWS region | us-east-1 |

## Security Notes

- SSH key auth only (no passwords)
- Firewall allows only 22, 80, 443
- AWS credentials stored in `~/.aws/` (chmod 600)
- Secrets in `.env` file (not in git)
- systemd override files contain sensitive env vars

## Maintenance

### After changing server configs:

```bash
# On VPS
sudo ./scripts/backup/backup_server_config.sh

# Upload to S3 automatically
```

### Rotate AWS credentials:

```bash
# 1. Create new key in AWS Console
# 2. Update on VPS
nano ~/.aws/credentials

# 3. Backup new credentials
sudo ./scripts/backup/backup_server_config.sh

# 4. Delete old key in AWS Console
```
