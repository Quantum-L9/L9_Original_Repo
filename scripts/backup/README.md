# L9 Memory Backup & Restore

Automated backup system for L9 memories, embeddings, graph data, and server configs to S3.

## Scripts

| Script | Purpose | Runs As | Schedule |
|--------|---------|---------|----------|
| `backup_l9_memory.sh` | PostgreSQL + Neo4j + .env | admin | Every 12h (cron) |
| `backup_server_config.sh` | Systemd + Caddy + AWS | sudo/root | Manual (after changes) |
| `restore_l9_memory.sh` | Restore from S3 | admin | Manual |
| `setup_s3_bucket.sh` | Create S3 bucket | admin | One-time |

## What Gets Backed Up

### Automated (Every 12 Hours)

| Component | Contents | Size Est. | Critical? |
|-----------|----------|-----------|-----------|
| **PostgreSQL** | packet_store, knowledge_facts, semantic_facts, pgvector embeddings | 50-500MB | ✅ YES |
| **Neo4j** | Graph relationships, entity links, causal graph | 10-100MB | ⚠️ Important |
| **Configs** | `.env`, `kernel_hashes.json` | <10KB | ⚠️ Important |

### Manual (After System Changes)

| Component | Contents | Location |
|-----------|----------|----------|
| **Crontab** | Scheduled jobs | `crontab -l` |
| **Caddy** | Reverse proxy, HTTPS | `/etc/caddy/Caddyfile` |
| **Systemd Services** | l9.service, l9-agent.service, l9-mcp.service | `/etc/systemd/system/` |
| **Systemd Overrides** | twilio.conf, waba.conf, environment.conf | `/etc/systemd/system/l9.service.d/` |
| **AWS Credentials** | S3 backup access | `~/.aws/` |

## What Does NOT Need Backup

- **Code repository** → Git handles this
- **Logs** → Ephemeral, recreated on restart
- **Redis** → Cache only, ephemeral

## Schedule

| Interval | Local Retention | S3 Retention |
|----------|-----------------|--------------|
| Every 12 hours | 3 days (6 backups) | 30 days |

## Setup

### 1. S3 Bucket (One-time)

```bash
# Create bucket
aws s3 mb s3://l9-backups --region us-east-1

# Set lifecycle policy (auto-delete after 30 days)
aws s3api put-bucket-lifecycle-configuration \
  --bucket l9-backups \
  --lifecycle-configuration '{
    "Rules": [{
      "ID": "AutoExpire30Days",
      "Status": "Enabled",
      "Filter": {},
      "Expiration": {"Days": 30}
    }]
  }'
```

### 2. AWS Credentials on VPS

```bash
# Install AWS CLI
apt-get install awscli

# Configure credentials
aws configure
# Enter: Access Key, Secret Key, Region (us-east-1), Output (json)
```

### 3. Cron Job (Every 12 hours)

```bash
# On VPS: crontab -e
0 */12 * * * /opt/l9/scripts/backup/backup_l9_memory.sh >> /var/log/l9-backup.log 2>&1
```

## Usage

### Backup (Manual)

```bash
# Full backup
./backup_l9_memory.sh

# Local only (no S3)
./backup_l9_memory.sh --no-s3

# Skip Neo4j
./backup_l9_memory.sh --no-neo4j

# Dry run
./backup_l9_memory.sh --dry-run
```

### Restore

```bash
# List available backups
./restore_l9_memory.sh --list

# Restore latest
./restore_l9_memory.sh latest

# Restore specific timestamp
./restore_l9_memory.sh 20260118_120000

# Restore only PostgreSQL
./restore_l9_memory.sh latest --postgres-only

# Skip confirmation
./restore_l9_memory.sh latest --yes
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `S3_BUCKET` | `l9-backups` | S3 bucket name |
| `S3_REGION` | `us-east-1` | AWS region |
| `BACKUP_DIR` | `/opt/l9/backups` | Local backup directory |
| `L9_DIR` | `/opt/l9` | L9 installation directory |
| `DB_CONTAINER` | `l9-postgres` | PostgreSQL container name |
| `NEO4J_CONTAINER` | `l9-neo4j` | Neo4j container name |

## Backup File Structure

```
s3://l9-backups/
├── postgres/
│   ├── postgres_20260118_120000.sql.gz
│   └── postgres_20260118_000000.sql.gz
├── neo4j/
│   ├── neo4j_20260118_120000.tar.gz
│   └── neo4j_20260118_000000.tar.gz
├── config/
│   ├── config_20260118_120000.tar.gz      # .env, kernel_hashes
│   └── config_20260118_000000.tar.gz
└── server-config/
    ├── system-configs-latest.tar.gz       # Caddy, systemd
    ├── system-configs_20260119_165512.tar.gz
    ├── crontab_admin.txt
    ├── aws_credentials
    └── aws_config
```

## Verification

The backup script records row counts for verification:

```bash
# Check counts file after backup
cat /opt/l9/backups/counts_TIMESTAMP.txt
```

After restore, compare with:

```bash
docker exec l9-postgres psql -U l9_user -d l9_memory -c "
  SELECT 
    (SELECT COUNT(*) FROM packet_store) as packets,
    (SELECT COUNT(*) FROM knowledge_facts) as facts
"
```

## Cost Estimate

| Item | Cost |
|------|------|
| S3 Storage (100MB × 30 days) | ~$0.07/month |
| S3 Requests | ~$0.01/month |
| **Total** | **~$0.10/month** |

## Disaster Recovery

### Full Server Rebuild

1. **Provision new VPS** (Ubuntu 22.04+, Docker installed)

2. **Clone L9 repo:**
   ```bash
   git clone https://github.com/yourusername/l9.git /opt/l9
   cd /opt/l9
   ```

3. **Restore server configs (Caddy, systemd, cron):**
   ```bash
   # Download from S3
   aws s3 cp s3://l9-backups/server-config/system-configs-latest.tar.gz .
   aws s3 cp s3://l9-backups/server-config/crontab_admin.txt .
   aws s3 cp s3://l9-backups/server-config/aws_credentials ~/.aws/credentials
   aws s3 cp s3://l9-backups/server-config/aws_config ~/.aws/config
   
   # Extract system configs
   sudo tar -xzvf system-configs-latest.tar.gz -C /
   
   # Reload systemd
   sudo systemctl daemon-reload
   
   # Restore crontab
   crontab crontab_admin.txt
   ```

4. **Start containers:**
   ```bash
   docker compose up -d
   ```

5. **Restore memory data:**
   ```bash
   ./scripts/backup/restore_l9_memory.sh latest
   ```

6. **Start services:**
   ```bash
   sudo systemctl restart caddy l9 l9-agent l9-mcp
   ```

### Partial Data Loss

```bash
# Restore only PostgreSQL
./restore_l9_memory.sh latest --postgres-only
```

## Troubleshooting

### Backup fails with "container not running"

```bash
docker compose up -d l9-postgres
```

### S3 upload fails

Check AWS credentials:
```bash
aws sts get-caller-identity
```

### Restore fails with "corrupt gzip"

Download backup directly and verify:
```bash
aws s3 cp s3://l9-backups/postgres/FILE.sql.gz ./
gzip -t FILE.sql.gz
```

## Related Scripts

- `backup_server_config.sh` - System configs backup (requires sudo)
- ~~`scripts/deployment/backup_database.sh`~~ - DEPRECATED (moved to `_archived/`)
- ~~`scripts/deployment/test_backup_restore.sh`~~ - DEPRECATED (moved to `_archived/`)
