# L9 VPS Scripts

All scripts related to VPS deployment, maintenance, and post-pull automation.

## Post-Pull Automation (runs automatically after `git pull`)

| Script | Purpose | When |
|--------|---------|------|
| `sync_env_vars.sh` | Add missing env vars from .env.example | Always |
| `verify_vps_env.sh` | Verify all required vars are set | Always |
| `run_migrations.sh` | Run pending SQL migrations | If new .sql files |

## Manual Operations

| Script | Purpose | Usage |
|--------|---------|-------|
| `backup_database.sh` | PostgreSQL backup with S3 support | `./backup_database.sh` or via cron |
| `vps-mri.sh` | Full system diagnostic (MRI scan) | `./vps-mri.sh` |

## Setup

Run once after cloning on VPS:

```bash
./ops/setup-git-hooks.sh
```

This installs a post-merge hook that runs the automation scripts after every `git pull`.

## Script Details

### sync_env_vars.sh
Compares `.env` against `.env.example` and adds any missing variables with their default values.

```bash
./scripts/vps/sync_env_vars.sh           # Normal mode
./scripts/vps/sync_env_vars.sh --quiet   # Minimal output (for hooks)
./scripts/vps/sync_env_vars.sh --dry-run # Show what would be added
```

### verify_vps_env.sh
Checks that all required environment variables are set.

```bash
./scripts/vps/verify_vps_env.sh          # Full verification with details
./scripts/vps/verify_vps_env.sh --quick  # Summary only (for hooks)
```

### run_migrations.sh
Detects and runs pending SQL migrations from `migrations/` directory.

```bash
./scripts/vps/run_migrations.sh              # Run pending migrations
./scripts/vps/run_migrations.sh --quiet      # Minimal output
./scripts/vps/run_migrations.sh --dry-run    # Show what would run
./scripts/vps/run_migrations.sh --force      # Re-run all migrations
```

Tracking file: `.migrations_applied`

### backup_database.sh
Automated PostgreSQL backup with optional S3 upload.

```bash
./scripts/vps/backup_database.sh              # Backup VPS database
./scripts/vps/backup_database.sh --local      # Backup local Docker
./scripts/vps/backup_database.sh --dry-run    # Show what would happen
./scripts/vps/backup_database.sh --no-s3      # Skip S3 upload
```

Cron setup (2 AM UTC daily):
```bash
0 2 * * * /opt/l9/scripts/vps/backup_database.sh >> /var/log/l9_backup.log 2>&1
```

### vps-mri.sh
Comprehensive system diagnostic that checks:
- System resources (disk, memory, CPU)
- Network and ports
- Docker containers
- Database connectivity
- L9 API health
- Reverse proxy (Caddy/Nginx)
- Recent errors

```bash
./scripts/vps/vps-mri.sh
```

## Environment Variables

Required variables are defined in `.env.example`. Critical ones:
- `MEMORY_DSN` - PostgreSQL connection string
- `POSTGRES_USER/PASSWORD/DB` - Database credentials
- `OPENAI_API_KEY` - Required for embeddings

## Troubleshooting

### Missing environment variables
```bash
./scripts/vps/verify_vps_env.sh
# Shows missing vars with copy-paste commands to add them
```

### Database migration issues
```bash
./scripts/vps/run_migrations.sh --dry-run
# Check tracking file
cat .migrations_applied
```

### System health check
```bash
./scripts/vps/vps-mri.sh | less
```
