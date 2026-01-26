#!/usr/bin/env bash
# =============================================================================
# L9 Memory Backup to S3
# Version: 1.0.0
#
# Backs up PostgreSQL (memories, embeddings), Neo4j (graph), and configs.
# Designed for 12-hour intervals, 3-day local retention, 30-day S3 retention.
#
# GOVERNANCE: IGOR_ONLY for cron setup and S3 configuration
# CURSOR_SAFE: true (read-only backup operations)
# =============================================================================

set -euo pipefail

# Add user-local bin to PATH (for AWS CLI installed via user installer)
export PATH="$HOME/.local/bin:$PATH"

# =============================================================================
# CONFIGURATION
# =============================================================================

# Paths
BACKUP_DIR="${BACKUP_DIR:-/opt/l9/backups}"
L9_DIR="${L9_DIR:-/opt/l9}"
LOG_DIR="${LOG_DIR:-/var/log}"

# S3 Configuration
S3_BUCKET="${S3_BUCKET:-l9-backups}"
S3_REGION="${S3_REGION:-us-east-1}"

# Retention
LOCAL_RETENTION_DAYS=3      # Keep 6 backups locally (12hr × 6 = 3 days)
S3_RETENTION_DAYS=30        # S3 lifecycle policy handles this

# Database Configuration
DB_CONTAINER="${DB_CONTAINER:-l9-postgres}"
DB_NAME="${POSTGRES_DB:-l9_memory}"
DB_USER="${POSTGRES_USER:-postgres}"

# Neo4j Configuration
NEO4J_CONTAINER="${NEO4J_CONTAINER:-l9-neo4j}"
NEO4J_DATA_DIR="${NEO4J_DATA_DIR:-/opt/l9/neo4j/data}"

# Timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/l9_backup_${TIMESTAMP}.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# =============================================================================
# LOGGING
# =============================================================================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE"
}

log_step() {
    echo "" | tee -a "$LOG_FILE"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}" | tee -a "$LOG_FILE"
    echo -e "${BLUE}  $1${NC}" | tee -a "$LOG_FILE"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}" | tee -a "$LOG_FILE"
}

# =============================================================================
# BACKUP FUNCTIONS
# =============================================================================

backup_postgres() {
    log_step "Backing up PostgreSQL (memories + embeddings)"

    local backup_file="${BACKUP_DIR}/postgres_${TIMESTAMP}.sql.gz"

    # Check container is running
    if ! docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
        log_error "PostgreSQL container '$DB_CONTAINER' is not running"
        return 1
    fi

    # Dump with all extensions and data
    docker exec "$DB_CONTAINER" pg_dump \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --create \
        --clean \
        --if-exists \
        --no-owner \
        --no-privileges \
        2>> "$LOG_FILE" | gzip > "$backup_file"

    # Verify backup
    local size=$(stat --printf="%s" "$backup_file" 2>/dev/null || echo "0")
    if [[ "$size" -lt 1000 ]]; then
        log_error "PostgreSQL backup too small (${size} bytes) - may have failed"
        return 1
    fi

    # Verify contains critical data
    local vector_count=$(zcat "$backup_file" | grep -c "vector" || echo "0")
    if [[ "$vector_count" -lt 10 ]]; then
        log_warn "Low vector count ($vector_count) - embeddings may be missing!"
    fi

    local size_mb=$(echo "scale=2; $size / 1048576" | bc)
    log_info "PostgreSQL backup: ${size_mb}MB, vectors: ${vector_count}"
    log_info "File: $backup_file"

    echo "$backup_file"
}

backup_neo4j() {
    log_step "Backing up Neo4j (graph relationships)"

    local backup_file="${BACKUP_DIR}/neo4j_${TIMESTAMP}.tar.gz"

    # Check if Neo4j data exists
    if [[ ! -d "$NEO4J_DATA_DIR" ]]; then
        log_warn "Neo4j data directory not found: $NEO4J_DATA_DIR"
        log_info "Skipping Neo4j backup (no data)"
        return 0
    fi

    # Stop Neo4j for consistent backup (Community Edition doesn't support online backup)
    local neo4j_was_running=false
    if docker ps --format '{{.Names}}' | grep -q "^${NEO4J_CONTAINER}$"; then
        neo4j_was_running=true
        log_info "Stopping Neo4j for consistent backup..."
        docker stop "$NEO4J_CONTAINER" >> "$LOG_FILE" 2>&1 || true
        sleep 2
    fi

    # Create backup
    tar -czf "$backup_file" -C "$(dirname "$NEO4J_DATA_DIR")" "$(basename "$NEO4J_DATA_DIR")" 2>> "$LOG_FILE"

    # Restart Neo4j if it was running
    if [[ "$neo4j_was_running" == "true" ]]; then
        log_info "Restarting Neo4j..."
        docker start "$NEO4J_CONTAINER" >> "$LOG_FILE" 2>&1 || true
    fi

    local size=$(stat --printf="%s" "$backup_file" 2>/dev/null || echo "0")
    local size_mb=$(echo "scale=2; $size / 1048576" | bc)
    log_info "Neo4j backup: ${size_mb}MB"
    log_info "File: $backup_file"

    echo "$backup_file"
}

backup_configs() {
    log_step "Backing up Configs (secrets not in git)"

    local backup_file="${BACKUP_DIR}/config_${TIMESTAMP}.tar.gz"
    local files_to_backup=""

    # Collect files that exist
    [[ -f "${L9_DIR}/.env" ]] && files_to_backup="${files_to_backup} ${L9_DIR}/.env"
    [[ -f "${L9_DIR}/private/kernel_hashes.json" ]] && files_to_backup="${files_to_backup} ${L9_DIR}/private/kernel_hashes.json"

    if [[ -z "$files_to_backup" ]]; then
        log_warn "No config files found to backup"
        return 0
    fi

    # shellcheck disable=SC2086
    tar -czf "$backup_file" $files_to_backup 2>> "$LOG_FILE" || true

    local size=$(stat --printf="%s" "$backup_file" 2>/dev/null || echo "0")
    log_info "Config backup: ${size} bytes"
    log_info "File: $backup_file"

    echo "$backup_file"
}

upload_to_s3() {
    log_step "Uploading to S3"

    local files=("$@")

    if [[ -z "$S3_BUCKET" ]]; then
        log_warn "S3_BUCKET not set - skipping S3 upload"
        return 0
    fi

    # Check AWS CLI is available
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not installed - skipping S3 upload"
        return 1
    fi

    for file in "${files[@]}"; do
        if [[ -f "$file" ]]; then
            local filename=$(basename "$file")
            local prefix=""

            # Determine S3 prefix based on filename
            case "$filename" in
                postgres_*) prefix="postgres" ;;
                neo4j_*) prefix="neo4j" ;;
                config_*) prefix="config" ;;
                *) prefix="other" ;;
            esac

            log_info "Uploading: $filename -> s3://${S3_BUCKET}/${prefix}/"
            aws s3 cp "$file" "s3://${S3_BUCKET}/${prefix}/${filename}" \
                --region "$S3_REGION" \
                --storage-class STANDARD_IA \
                >> "$LOG_FILE" 2>&1
        fi
    done

    log_info "S3 upload complete"
}

cleanup_old_backups() {
    log_step "Cleaning Old Local Backups"

    # Delete backups older than LOCAL_RETENTION_DAYS
    find "$BACKUP_DIR" -name "postgres_*.sql.gz" -mtime +"$LOCAL_RETENTION_DAYS" -delete 2>/dev/null || true
    find "$BACKUP_DIR" -name "neo4j_*.tar.gz" -mtime +"$LOCAL_RETENTION_DAYS" -delete 2>/dev/null || true
    find "$BACKUP_DIR" -name "config_*.tar.gz" -mtime +"$LOCAL_RETENTION_DAYS" -delete 2>/dev/null || true

    # Count remaining backups
    local pg_count=$(ls -1 "$BACKUP_DIR"/postgres_*.sql.gz 2>/dev/null | wc -l || echo "0")
    local neo_count=$(ls -1 "$BACKUP_DIR"/neo4j_*.tar.gz 2>/dev/null | wc -l || echo "0")

    log_info "Local backups remaining: PostgreSQL=$pg_count, Neo4j=$neo_count"
    log_info "S3 lifecycle policy handles remote cleanup (${S3_RETENTION_DAYS} days)"
}

record_counts() {
    log_step "Recording Row Counts (for restore verification)"

    local counts_file="${BACKUP_DIR}/counts_${TIMESTAMP}.txt"

    docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "
        SELECT
            (SELECT COUNT(*) FROM packet_store) as packets,
            (SELECT COUNT(*) FROM knowledge_facts) as facts,
            (SELECT COUNT(*) FROM semantic_facts WHERE embedding IS NOT NULL) as semantic_embeddings
    " > "$counts_file" 2>/dev/null || true

    if [[ -f "$counts_file" ]]; then
        log_info "Row counts saved: $counts_file"
        cat "$counts_file" | tee -a "$LOG_FILE"
    fi
}

# =============================================================================
# MAIN
# =============================================================================

usage() {
    cat <<EOF
L9 Memory Backup Script v1.0.0

Backs up PostgreSQL (memories + embeddings), Neo4j (graph), and configs to S3.

Usage: $0 [OPTIONS]

Options:
    --no-s3         Skip S3 upload (local backup only)
    --no-neo4j      Skip Neo4j backup
    --no-cleanup    Skip cleanup of old backups
    --dry-run       Show what would be done
    -h, --help      Show this help

Environment Variables:
    S3_BUCKET       S3 bucket name (default: l9-backups)
    S3_REGION       AWS region (default: us-east-1)
    BACKUP_DIR      Local backup directory (default: /opt/l9/backups)
    L9_DIR          L9 installation directory (default: /opt/l9)

Schedule (cron every 12 hours):
    0 */12 * * * /opt/l9/scripts/backup/backup_l9_memory.sh >> /var/log/l9-backup.log 2>&1

EOF
}

main() {
    local skip_s3=false
    local skip_neo4j=false
    local skip_cleanup=false
    local dry_run=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --no-s3) skip_s3=true; shift ;;
            --no-neo4j) skip_neo4j=true; shift ;;
            --no-cleanup) skip_cleanup=true; shift ;;
            --dry-run) dry_run=true; shift ;;
            -h|--help) usage; exit 0 ;;
            *) log_error "Unknown option: $1"; usage; exit 1 ;;
        esac
    done

    echo ""
    log_step "L9 Memory Backup - $TIMESTAMP"

    if [[ "$dry_run" == "true" ]]; then
        log_warn "DRY RUN - No actual backup will be created"
        log_info "Would backup: PostgreSQL, Neo4j, Configs"
        log_info "Would upload to: s3://${S3_BUCKET}/"
        exit 0
    fi

    # Create backup directory
    mkdir -p "$BACKUP_DIR"

    # Collect backup files
    local backup_files=()

    # 1. PostgreSQL (critical)
    local pg_file
    if pg_file=$(backup_postgres); then
        backup_files+=("$pg_file")
    else
        log_error "PostgreSQL backup FAILED - aborting"
        exit 1
    fi

    # 2. Neo4j (optional)
    if [[ "$skip_neo4j" != "true" ]]; then
        local neo_file
        if neo_file=$(backup_neo4j); then
            [[ -n "$neo_file" ]] && backup_files+=("$neo_file")
        fi
    fi

    # 3. Configs
    local config_file
    if config_file=$(backup_configs); then
        [[ -n "$config_file" ]] && backup_files+=("$config_file")
    fi

    # 4. Record counts for verification
    record_counts

    # 5. Upload to S3
    if [[ "$skip_s3" != "true" ]] && [[ ${#backup_files[@]} -gt 0 ]]; then
        upload_to_s3 "${backup_files[@]}"
    fi

    # 6. Cleanup old local backups
    if [[ "$skip_cleanup" != "true" ]]; then
        cleanup_old_backups
    fi

    # Summary
    log_step "Backup Complete"
    log_info "✅ L9 memory backup successful"
    log_info "   Timestamp: $TIMESTAMP"
    log_info "   Local: $BACKUP_DIR"
    log_info "   S3: s3://${S3_BUCKET}/"
    log_info "   Log: $LOG_FILE"
}

main "$@"
