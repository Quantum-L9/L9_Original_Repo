#!/usr/bin/env bash
# =============================================================================
# C1 Memory Backup to S3
# Version: 1.0.0
#
# Backs up C1 Hetzner Server (46.62.243.82) PostgreSQL + Neo4j to S3.
# Designed for 24-hour intervals, 7-day local retention, 30-day S3 retention.
#
# C1 is the PRIMARY memory server per 03-mcp-memory.mdc:
#   - PostgreSQL: 46.62.243.82:30432
#   - Neo4j: 46.62.243.82:30474
#   - MCP Memory: 46.62.243.82:30902
#
# GOVERNANCE: IGOR_ONLY for cron setup and S3 configuration
# CURSOR_SAFE: true (read-only backup operations)
# =============================================================================

set -euo pipefail

# Add user-local bin to PATH (for AWS CLI installed via user installer)
export PATH="$HOME/.local/bin:$PATH"

# =============================================================================
# C1 SERVER CONFIGURATION
# =============================================================================

# C1 Hetzner Server
C1_HOST="${C1_HOST:-46.62.243.82}"
C1_SSH_USER="${C1_SSH_USER:-admin}"
C1_SSH_KEY="${C1_SSH_KEY:-$HOME/.ssh/id_ed25519}"

# C1 Database Ports (NodePort exposed)
C1_POSTGRES_PORT="${C1_POSTGRES_PORT:-30432}"
C1_NEO4J_PORT="${C1_NEO4J_PORT:-30474}"
C1_NEO4J_BOLT_PORT="${C1_NEO4J_BOLT_PORT:-30687}"

# Database Credentials (from C1 .env or environment)
C1_POSTGRES_USER="${C1_POSTGRES_USER:-l9_user}"
C1_POSTGRES_PASSWORD="${C1_POSTGRES_PASSWORD:-}"
C1_POSTGRES_DB="${C1_POSTGRES_DB:-l9_memory}"

# =============================================================================
# LOCAL CONFIGURATION
# =============================================================================

# Paths (local machine running backup)
BACKUP_DIR="${BACKUP_DIR:-$HOME/.l9/backups/c1}"
LOG_DIR="${LOG_DIR:-$HOME/.l9/logs}"

# S3 Configuration
S3_BUCKET="${S3_BUCKET:-l9-backups}"
S3_PREFIX="${S3_PREFIX:-c1}"  # Prefix for C1 backups
S3_REGION="${S3_REGION:-us-east-1}"

# Retention
LOCAL_RETENTION_DAYS=7      # Keep 7 backups locally (24hr × 7 = 7 days)
S3_RETENTION_DAYS=30        # S3 lifecycle policy handles this

# Timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/c1_backup_${TIMESTAMP}.log"

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
# CONNECTIVITY CHECK
# =============================================================================

check_c1_connectivity() {
    log_step "Checking C1 Connectivity"

    # Check if C1 is reachable
    if ! nc -z -w5 "$C1_HOST" "$C1_POSTGRES_PORT" 2>/dev/null; then
        log_error "Cannot reach C1 PostgreSQL at ${C1_HOST}:${C1_POSTGRES_PORT}"
        log_info "Ensure C1 server is running and ports are exposed"
        return 1
    fi

    log_info "✓ C1 PostgreSQL reachable at ${C1_HOST}:${C1_POSTGRES_PORT}"

    # Check Neo4j (optional)
    if nc -z -w5 "$C1_HOST" "$C1_NEO4J_PORT" 2>/dev/null; then
        log_info "✓ C1 Neo4j reachable at ${C1_HOST}:${C1_NEO4J_PORT}"
    else
        log_warn "C1 Neo4j not reachable at ${C1_HOST}:${C1_NEO4J_PORT} (may be OK)"
    fi

    return 0
}

# =============================================================================
# BACKUP FUNCTIONS
# =============================================================================

backup_c1_postgres() {
    log_step "Backing up C1 PostgreSQL (memories + embeddings)"

    local backup_file="${BACKUP_DIR}/c1_postgres_${TIMESTAMP}.sql.gz"

    # Check password is set
    if [[ -z "$C1_POSTGRES_PASSWORD" ]]; then
        log_error "C1_POSTGRES_PASSWORD not set"
        log_info "Set via: export C1_POSTGRES_PASSWORD='your_password'"
        return 1
    fi

    # Dump via pg_dump with remote connection
    log_info "Connecting to ${C1_HOST}:${C1_POSTGRES_PORT}..."

    PGPASSWORD="$C1_POSTGRES_PASSWORD" pg_dump \
        -h "$C1_HOST" \
        -p "$C1_POSTGRES_PORT" \
        -U "$C1_POSTGRES_USER" \
        -d "$C1_POSTGRES_DB" \
        --create \
        --clean \
        --if-exists \
        --no-owner \
        --no-privileges \
        2>> "$LOG_FILE" | gzip > "$backup_file"

    # Verify backup
    local size
    if [[ "$(uname)" == "Darwin" ]]; then
        size=$(stat -f%z "$backup_file" 2>/dev/null || echo "0")
    else
        size=$(stat --printf="%s" "$backup_file" 2>/dev/null || echo "0")
    fi

    if [[ "$size" -lt 1000 ]]; then
        log_error "C1 PostgreSQL backup too small (${size} bytes) - may have failed"
        return 1
    fi

    # Verify contains critical data
    local vector_count=$(zcat "$backup_file" | grep -c "vector" || echo "0")
    if [[ "$vector_count" -lt 10 ]]; then
        log_warn "Low vector count ($vector_count) - embeddings may be missing!"
    fi

    local size_mb=$(echo "scale=2; $size / 1048576" | bc)
    log_info "C1 PostgreSQL backup: ${size_mb}MB, vectors: ${vector_count}"
    log_info "File: $backup_file"

    echo "$backup_file"
}

backup_c1_neo4j() {
    log_step "Backing up C1 Neo4j (graph relationships)"

    local backup_file="${BACKUP_DIR}/c1_neo4j_${TIMESTAMP}.cypher.gz"

    # For remote Neo4j, we use cypher-shell to export
    # This requires neo4j-admin or cypher-shell to be available locally

    if ! command -v cypher-shell &> /dev/null; then
        log_warn "cypher-shell not installed - skipping Neo4j backup"
        log_info "Install with: brew install neo4j (includes cypher-shell)"
        return 0
    fi

    # Check if Neo4j is reachable
    if ! nc -z -w5 "$C1_HOST" "$C1_NEO4J_BOLT_PORT" 2>/dev/null; then
        log_warn "C1 Neo4j Bolt not reachable at ${C1_HOST}:${C1_NEO4J_BOLT_PORT}"
        log_info "Skipping Neo4j backup"
        return 0
    fi

    log_info "Exporting Neo4j graph via Cypher..."

    # Export all nodes and relationships as Cypher statements
    # Note: This is a basic export. For large graphs, consider APOC export.
    cypher-shell \
        -a "bolt://${C1_HOST}:${C1_NEO4J_BOLT_PORT}" \
        -u "${NEO4J_USER:-neo4j}" \
        -p "${NEO4J_PASSWORD:-}" \
        --format plain \
        "CALL apoc.export.cypher.all(null, {format: 'cypher-shell', stream: true}) YIELD cypherStatements RETURN cypherStatements" \
        2>> "$LOG_FILE" | gzip > "$backup_file" || {
            log_warn "Neo4j export failed - may need APOC plugin"
            return 0
        }

    local size
    if [[ "$(uname)" == "Darwin" ]]; then
        size=$(stat -f%z "$backup_file" 2>/dev/null || echo "0")
    else
        size=$(stat --printf="%s" "$backup_file" 2>/dev/null || echo "0")
    fi

    local size_mb=$(echo "scale=2; $size / 1048576" | bc)
    log_info "C1 Neo4j backup: ${size_mb}MB"
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
                *postgres*) prefix="${S3_PREFIX}/postgres" ;;
                *neo4j*) prefix="${S3_PREFIX}/neo4j" ;;
                *config*) prefix="${S3_PREFIX}/config" ;;
                *) prefix="${S3_PREFIX}/other" ;;
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
    find "$BACKUP_DIR" -name "c1_postgres_*.sql.gz" -mtime +"$LOCAL_RETENTION_DAYS" -delete 2>/dev/null || true
    find "$BACKUP_DIR" -name "c1_neo4j_*.cypher.gz" -mtime +"$LOCAL_RETENTION_DAYS" -delete 2>/dev/null || true

    # Count remaining backups
    local pg_count=$(ls -1 "$BACKUP_DIR"/c1_postgres_*.sql.gz 2>/dev/null | wc -l || echo "0")
    local neo_count=$(ls -1 "$BACKUP_DIR"/c1_neo4j_*.cypher.gz 2>/dev/null | wc -l || echo "0")

    log_info "Local backups remaining: PostgreSQL=$pg_count, Neo4j=$neo_count"
    log_info "S3 lifecycle policy handles remote cleanup (${S3_RETENTION_DAYS} days)"
}

record_counts() {
    log_step "Recording Row Counts (for restore verification)"

    local counts_file="${BACKUP_DIR}/c1_counts_${TIMESTAMP}.txt"

    if [[ -z "$C1_POSTGRES_PASSWORD" ]]; then
        log_warn "C1_POSTGRES_PASSWORD not set - skipping counts"
        return 0
    fi

    PGPASSWORD="$C1_POSTGRES_PASSWORD" psql \
        -h "$C1_HOST" \
        -p "$C1_POSTGRES_PORT" \
        -U "$C1_POSTGRES_USER" \
        -d "$C1_POSTGRES_DB" \
        -c "
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
C1 Memory Backup Script v1.0.0

Backs up C1 Hetzner Server (46.62.243.82) PostgreSQL + Neo4j to S3.
C1 is the PRIMARY memory server per L9 governance rules.

Usage: $0 [OPTIONS]

Options:
    --no-s3         Skip S3 upload (local backup only)
    --no-neo4j      Skip Neo4j backup
    --no-cleanup    Skip cleanup of old backups
    --dry-run       Show what would be done
    -h, --help      Show this help

Environment Variables (REQUIRED):
    C1_POSTGRES_PASSWORD    PostgreSQL password for C1

Environment Variables (OPTIONAL):
    C1_HOST                 C1 server IP (default: 46.62.243.82)
    C1_POSTGRES_PORT        PostgreSQL port (default: 30432)
    C1_POSTGRES_USER        PostgreSQL user (default: l9_user)
    C1_POSTGRES_DB          Database name (default: l9_memory)
    S3_BUCKET               S3 bucket name (default: l9-backups)
    S3_PREFIX               S3 prefix (default: c1)
    S3_REGION               AWS region (default: us-east-1)
    BACKUP_DIR              Local backup directory (default: ~/.l9/backups/c1)

Schedule (cron daily):
    0 2 * * * C1_POSTGRES_PASSWORD='xxx' $HOME/Projects/L9/scripts/backup/backup_c1_memory.sh >> ~/.l9/logs/c1-backup.log 2>&1

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
    log_step "C1 Memory Backup - $TIMESTAMP"
    log_info "Target: ${C1_HOST}:${C1_POSTGRES_PORT} (C1 Hetzner Server)"

    if [[ "$dry_run" == "true" ]]; then
        log_warn "DRY RUN - No actual backup will be created"
        log_info "Would backup: C1 PostgreSQL, C1 Neo4j"
        log_info "Would upload to: s3://${S3_BUCKET}/${S3_PREFIX}/"
        exit 0
    fi

    # Create directories
    mkdir -p "$BACKUP_DIR"
    mkdir -p "$LOG_DIR"

    # Check connectivity
    if ! check_c1_connectivity; then
        log_error "C1 connectivity check failed - aborting"
        exit 1
    fi

    # Collect backup files
    local backup_files=()

    # 1. PostgreSQL (critical)
    local pg_file
    if pg_file=$(backup_c1_postgres); then
        backup_files+=("$pg_file")
    else
        log_error "C1 PostgreSQL backup FAILED - aborting"
        exit 1
    fi

    # 2. Neo4j (optional)
    if [[ "$skip_neo4j" != "true" ]]; then
        local neo_file
        if neo_file=$(backup_c1_neo4j); then
            [[ -n "$neo_file" ]] && backup_files+=("$neo_file")
        fi
    fi

    # 3. Record counts for verification
    record_counts

    # 4. Upload to S3
    if [[ "$skip_s3" != "true" ]] && [[ ${#backup_files[@]} -gt 0 ]]; then
        upload_to_s3 "${backup_files[@]}"
    fi

    # 5. Cleanup old local backups
    if [[ "$skip_cleanup" != "true" ]]; then
        cleanup_old_backups
    fi

    # Summary
    log_step "Backup Complete"
    log_info "✅ C1 memory backup successful"
    log_info "   Target: ${C1_HOST} (C1 Hetzner Server)"
    log_info "   Timestamp: $TIMESTAMP"
    log_info "   Local: $BACKUP_DIR"
    log_info "   S3: s3://${S3_BUCKET}/${S3_PREFIX}/"
    log_info "   Log: $LOG_FILE"
}

main "$@"
