#!/bin/bash
# =============================================================================
# L9 VPS Database Migration Runner
# Applies SQL migrations from migrations/ directory in order
#
# Usage:
#   ./run_migrations.sh           # Apply all pending migrations
#   ./run_migrations.sh --dry-run # Show what would be applied
#   ./run_migrations.sh --status  # Show migration status
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Flags
DRY_RUN=false
STATUS_ONLY=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run) DRY_RUN=true; shift ;;
        --status) STATUS_ONLY=true; shift ;;
        *) shift ;;
    esac
done

log() {
    echo -e "$1"
}

# Determine paths
if [ -d "/opt/l9" ]; then
    REPO_ROOT="/opt/l9"
fi

MIGRATIONS_DIR="$REPO_ROOT/migrations"
APPLIED_FILE="$REPO_ROOT/.migrations_applied"

# Load environment
if [ -f "$REPO_ROOT/.env" ]; then
    set -a
    source "$REPO_ROOT/.env"
    set +a
fi

log "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
log "${BLUE}║  L9 Database Migration Runner                                  ║${NC}"
log "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
log ""

# Check for migrations directory
if [ ! -d "$MIGRATIONS_DIR" ]; then
    log "${YELLOW}⚠️  No migrations directory found at $MIGRATIONS_DIR${NC}"
    exit 0
fi

# Create applied file if not exists
touch "$APPLIED_FILE"

# Get list of migration files
MIGRATION_FILES=$(ls -1 "$MIGRATIONS_DIR"/*.sql 2>/dev/null | sort || true)

if [ -z "$MIGRATION_FILES" ]; then
    log "${GREEN}✅ No migration files found${NC}"
    exit 0
fi

# Count pending
PENDING_COUNT=0
APPLIED_COUNT=0

log "${BLUE}Migration Status:${NC}"
log "─────────────────────────────────────────────────────────────────"

while IFS= read -r migration_file; do
    migration_name=$(basename "$migration_file")

    if grep -q "^$migration_name$" "$APPLIED_FILE" 2>/dev/null; then
        log "  ${GREEN}✅${NC} $migration_name (applied)"
        ((APPLIED_COUNT++))
    else
        log "  ${YELLOW}○${NC}  $migration_name (pending)"
        ((PENDING_COUNT++))
    fi
done <<< "$MIGRATION_FILES"

log ""
log "Applied: ${GREEN}$APPLIED_COUNT${NC} | Pending: ${YELLOW}$PENDING_COUNT${NC}"
log ""

if [ "$STATUS_ONLY" = true ]; then
    exit 0
fi

if [ "$PENDING_COUNT" -eq 0 ]; then
    log "${GREEN}✅ All migrations already applied${NC}"
    exit 0
fi

# Dry run mode
if [ "$DRY_RUN" = true ]; then
    log "${YELLOW}DRY RUN - Would apply these migrations:${NC}"
    while IFS= read -r migration_file; do
        migration_name=$(basename "$migration_file")
        if ! grep -q "^$migration_name$" "$APPLIED_FILE" 2>/dev/null; then
            log "  - $migration_name"
        fi
    done <<< "$MIGRATION_FILES"
    exit 0
fi

# Build connection string
if [ -n "$MEMORY_DSN" ]; then
    DB_CONN="$MEMORY_DSN"
elif [ -n "$DATABASE_URL" ]; then
    DB_CONN="$DATABASE_URL"
else
    # Construct from parts
    DB_HOST="${POSTGRES_HOST:-localhost}"
    DB_PORT="${POSTGRES_PORT:-5432}"
    DB_USER="${POSTGRES_USER:-postgres}"
    DB_PASS="${POSTGRES_PASSWORD:-}"
    DB_NAME="${POSTGRES_DB:-l9}"
    DB_CONN="postgresql://$DB_USER:$DB_PASS@$DB_HOST:$DB_PORT/$DB_NAME"
fi

log "${BLUE}Applying pending migrations...${NC}"
log ""

# Apply each pending migration
FAILED=false
while IFS= read -r migration_file; do
    migration_name=$(basename "$migration_file")

    # Skip if already applied
    if grep -q "^$migration_name$" "$APPLIED_FILE" 2>/dev/null; then
        continue
    fi

    log "  ${BLUE}➜${NC} Applying $migration_name..."

    # Try to apply via psql
    if command -v psql &> /dev/null; then
        if PGPASSWORD="$POSTGRES_PASSWORD" psql -h "${POSTGRES_HOST:-localhost}" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$migration_file" 2>&1; then
            echo "$migration_name" >> "$APPLIED_FILE"
            log "    ${GREEN}✅${NC} Applied successfully"
        else
            log "    ${RED}❌${NC} Failed to apply $migration_name"
            FAILED=true
            break
        fi
    else
        # Try via docker exec if psql not available locally
        if docker exec -i l9-postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$migration_file" 2>&1; then
            echo "$migration_name" >> "$APPLIED_FILE"
            log "    ${GREEN}✅${NC} Applied successfully (via docker)"
        else
            log "    ${RED}❌${NC} Failed to apply $migration_name"
            FAILED=true
            break
        fi
    fi
done <<< "$MIGRATION_FILES"

log ""

if [ "$FAILED" = true ]; then
    log "${RED}❌ Migration failed! Check logs above.${NC}"
    exit 1
else
    log "${GREEN}✅ All migrations applied successfully!${NC}"
fi
