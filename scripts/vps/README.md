# VPS Deployment Scripts

Scripts for L9 VPS deployment operations. These are called by the main deployment pipeline (`scripts/deployment/10X_Deploy_Script.sh`).

## Scripts

### `sync_env_vars.sh`
Syncs environment variables from `.env.example` to `.env`, adding any missing variables with their default values.

```bash
./sync_env_vars.sh           # Normal mode - add missing vars
./sync_env_vars.sh --quiet   # Quiet mode for automated pipelines
./sync_env_vars.sh --dry-run # Preview what would be added
```

### `verify_vps_env.sh`
Verifies that all required environment variables are set in `.env`.

```bash
./verify_vps_env.sh         # Full verification with details
./verify_vps_env.sh --quick # Quick check for CI/hooks
```

### `run_migrations.sh`
Applies pending SQL migrations from `migrations/` directory.

```bash
./run_migrations.sh           # Apply all pending migrations
./run_migrations.sh --dry-run # Preview what would be applied
./run_migrations.sh --status  # Show migration status only
```

## Path Resolution

These scripts automatically detect whether they're running on:
- **VPS**: `/opt/l9/` (production)
- **Local**: Repository root (development)

## Integration

These scripts are called by the 10X deployment pipeline:
- Phase 4: `sync_env_vars.sh --quiet` and `verify_vps_env.sh --quick`
- Phase 4.5: `run_migrations.sh` (if `--run-migrations` flag is set)

## Relationship to `scripts/deployment/`

The canonical implementations live in `scripts/deployment/`. These wrapper scripts call the canonical versions when available, with inline fallbacks for minimal VPS environments.
