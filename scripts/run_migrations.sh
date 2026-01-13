#!/bin/bash
# =============================================================================
# L9 Database Migration Runner
# Detects and runs pending SQL migrations from migrations/ directory
# Tracks applied migrations in .migrations_applied file
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Flags
QUIET=false
DRY_RUN=false
FORCE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --quiet|-q) QUIET=true; shift ;;
        --dry-run) DRY_RUN=true; shift ;;
        --force|-f) FORCE=true; shift ;;
        *) shift ;;
    esac
done

log() {
    if [ "$QUIET" = false ]; then
        echo -e "$1"
    fi
}

log_always() {
    echo -e "$1"
}

# Determine paths
if [ -d "/opt/l9" ]; then
    REPO_ROOT="/opt/l9"
fi

MIGRATIONS_DIR="$REPO_ROOT/migrations"
TRACKING_FILE="$REPO_ROOT/.migrations_applied"
ENV_FILE="$REPO_ROOT/.env"

# Check migrations directory exists
if [ ! -d "$MIGRATIONS_DIR" ]; then
    log "${YELLOW}⚠️  No migrations directory found${NC}"
    exit 0
fi

# Load MEMORY_DSN from .env
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

# Validate we have database connection
if [ -z "$MEMORY_DSN" ]; then
    log "${YELLOW}⚠️  MEMORY_DSN not set - skipping migrations${NC}"
    exit 0
fi

log "${BLUE}🗄️  Checking for pending migrations...${NC}"

# Create tracking file if not exists
if [ ! -f "$TRACKING_FILE" ]; then
    touch "$TRACKING_FILE"
fi

# Get list of all migration files (sorted)
MIGRATION_FILES=$(ls -1 "$MIGRATIONS_DIR"/*.sql 2>/dev/null | sort)

if [ -z "$MIGRATION_FILES" ]; then
    log "${GREEN}✅ No migration files found${NC}"
    exit 0
fi

# Find pending migrations
PENDING=()
PENDING_NAMES=()

for file in $MIGRATION_FILES; do
    filename=$(basename "$file")
    if ! grep -q "^$filename$" "$TRACKING_FILE" 2>/dev/null || [ "$FORCE" = true ]; then
        PENDING+=("$file")
        PENDING_NAMES+=("$filename")
    fi
done

# Check if any pending
if [ ${#PENDING[@]} -eq 0 ]; then
    if [ "$QUIET" = true ]; then
        echo -e "${GREEN}✅ Migrations: all applied${NC}"
    else
        log "${GREEN}✅ All migrations already applied${NC}"
    fi
    exit 0
fi

if [ "$QUIET" = true ]; then
    log_always "${YELLOW}⚠️  Migrations: ${#PENDING[@]} pending${NC}"
else
    log_always "${YELLOW}📋 Found ${#PENDING[@]} pending migration(s):${NC}"
    for name in "${PENDING_NAMES[@]}"; do
        log_always "   - $name"
    done
fi

# Dry run mode
if [ "$DRY_RUN" = true ]; then
    if [ "$QUIET" = false ]; then
        log_always ""
        log_always "${YELLOW}DRY RUN - Would apply these migrations:${NC}"
        for file in "${PENDING[@]}"; do
            log_always "   psql \$MEMORY_DSN -f $file"
        done
        log_always ""
        log_always "${YELLOW}Run without --dry-run to apply.${NC}"
    fi
    exit 0
fi

# Apply migrations
log_always ""
log_always "${BLUE}🚀 Applying migrations...${NC}"

FAILED=0
for i in "${!PENDING[@]}"; do
    file="${PENDING[$i]}"
    filename="${PENDING_NAMES[$i]}"
    
    log_always "   Applying: $filename"
    
    # Run migration
    if psql "$MEMORY_DSN" -f "$file" -q 2>/dev/null; then
        # Mark as applied
        echo "$filename" >> "$TRACKING_FILE"
        log_always "   ${GREEN}✅ $filename applied${NC}"
    else
        log_always "   ${RED}❌ $filename FAILED${NC}"
        FAILED=$((FAILED + 1))
        # Don't continue on failure
        break
    fi
done

log_always ""

if [ $FAILED -gt 0 ]; then
    log_always "${RED}❌ Migration failed - check database and retry${NC}"
    exit 1
fi

log_always "${GREEN}✅ All migrations applied successfully!${NC}"
