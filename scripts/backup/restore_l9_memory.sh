#!/usr/bin/env bash
# =============================================================================
# L9 Memory Restore from S3
# Version: 1.0.0
#
# Restores PostgreSQL (memories, embeddings), Neo4j (graph), and configs from S3.
#
# GOVERNANCE: IGOR_ONLY (destructive operation)
# CURSOR_SAFE: false (overwrites data)
# =============================================================================

set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================

# Paths
RESTORE_DIR="${RESTORE_DIR:-/opt/l9/backups/restore}"
L9_DIR="${L9_DIR:-/opt/l9}"
LOG_DIR="${LOG_DIR:-/var/log}"

# S3 Configuration
S3_BUCKET="${S3_BUCKET:-l9-backups}"
S3_REGION="${S3_REGION:-us-east-1}"

# Database Configuration
DB_CONTAINER="${DB_CONTAINER:-l9-postgres}"
DB_NAME="${POSTGRES_DB:-l9_memory}"
DB_USER="${POSTGRES_USER:-l9_user}"

# Neo4j Configuration
NEO4J_CONTAINER="${NEO4J_CONTAINER:-l9-neo4j}"
NEO4J_DATA_DIR="${NEO4J_DATA_DIR:-/opt/l9/neo4j/data}"

# Timestamp for logs
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/l9_restore_${TIMESTAMP}.log"

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
# RESTORE FUNCTIONS
# =============================================================================

list_available_backups() {
    log_step "Available S3 Backups"

    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not installed"
        return 1
    fi

    echo ""
    echo "PostgreSQL backups:"
    aws s3 ls "s3://${S3_BUCKET}/postgres/" --region "$S3_REGION" 2>/dev/null | sort -r | head -10

    echo ""
    echo "Neo4j backups:"
    aws s3 ls "s3://${S3_BUCKET}/neo4j/" --region "$S3_REGION" 2>/dev/null | sort -r | head -10

    echo ""
    echo "Config backups:"
    aws s3 ls "s3://${S3_BUCKET}/config/" --region "$S3_REGION" 2>/dev/null | sort -r | head -10
}

get_latest_timestamp() {
    local prefix="$1"
    aws s3 ls "s3://${S3_BUCKET}/${prefix}/" --region "$S3_REGION" 2>/dev/null \
        | sort -r \
        | head -1 \
        | awk '{print $4}' \
        | sed "s/${prefix}_//" \
        | sed 's/\..*//'
}

download_from_s3() {
    local target_timestamp="$1"

    log_step "Downloading from S3 (timestamp: $target_timestamp)"

    mkdir -p "$RESTORE_DIR"

    # Download PostgreSQL backup
    local pg_file="postgres_${target_timestamp}.sql.gz"
    log_info "Downloading: $pg_file"
    aws s3 cp "s3://${S3_BUCKET}/postgres/${pg_file}" "${RESTORE_DIR}/" \
        --region "$S3_REGION" >> "$LOG_FILE" 2>&1 || {
        log_error "Failed to download PostgreSQL backup"
        return 1
    }

    # Download Neo4j backup (optional)
    local neo_file="neo4j_${target_timestamp}.tar.gz"
    log_info "Downloading: $neo_file (optional)"
    aws s3 cp "s3://${S3_BUCKET}/neo4j/${neo_file}" "${RESTORE_DIR}/" \
        --region "$S3_REGION" >> "$LOG_FILE" 2>&1 || {
        log_warn "Neo4j backup not found (may not exist)"
    }

    # Download config backup (optional)
    local config_file="config_${target_timestamp}.tar.gz"
    log_info "Downloading: $config_file (optional)"
    aws s3 cp "s3://${S3_BUCKET}/config/${config_file}" "${RESTORE_DIR}/" \
        --region "$S3_REGION" >> "$LOG_FILE" 2>&1 || {
        log_warn "Config backup not found (may not exist)"
    }

    log_info "Downloads complete"
}

restore_postgres() {
    local target_timestamp="$1"

    log_step "Restoring PostgreSQL"

    local backup_file="${RESTORE_DIR}/postgres_${target_timestamp}.sql.gz"

    if [[ ! -f "$backup_file" ]]; then
        log_error "Backup file not found: $backup_file"
        return 1
    fi

    # Verify container is running
    if ! docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
        log_error "PostgreSQL container '$DB_CONTAINER' is not running"
        return 1
    fi

    # Verify backup integrity
    if ! gzip -t "$backup_file" 2>/dev/null; then
        log_error "Backup file is corrupt: $backup_file"
        return 1
    fi

    log_warn "⚠️  This will OVERWRITE the current database!"
    log_info "Restoring from: $backup_file"

    # Restore
    gunzip -c "$backup_file" | docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d postgres >> "$LOG_FILE" 2>&1

    # Verify restore
    local packet_count=$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM packet_store" 2>/dev/null | tr -d ' ')
    local fact_count=$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM knowledge_facts" 2>/dev/null | tr -d ' ')

    log_info "PostgreSQL restored"
    log_info "  Packets: $packet_count"
    log_info "  Facts: $fact_count"
}

restore_neo4j() {
    local target_timestamp="$1"

    log_step "Restoring Neo4j"

    local backup_file="${RESTORE_DIR}/neo4j_${target_timestamp}.tar.gz"

    if [[ ! -f "$backup_file" ]]; then
        log_warn "Neo4j backup not found - skipping"
        return 0
    fi

    # Stop Neo4j
    log_info "Stopping Neo4j..."
    docker stop "$NEO4J_CONTAINER" >> "$LOG_FILE" 2>&1 || true
    sleep 2

    # Clear existing data
    log_warn "⚠️  Removing existing Neo4j data..."
    rm -rf "${NEO4J_DATA_DIR:?}/"* 2>/dev/null || true

    # Extract backup
    log_info "Extracting: $backup_file"
    tar -xzf "$backup_file" -C "$(dirname "$NEO4J_DATA_DIR")" >> "$LOG_FILE" 2>&1

    # Start Neo4j
    log_info "Starting Neo4j..."
    docker start "$NEO4J_CONTAINER" >> "$LOG_FILE" 2>&1 || true

    log_info "Neo4j restored"
}

restore_configs() {
    local target_timestamp="$1"

    log_step "Restoring Configs"

    local backup_file="${RESTORE_DIR}/config_${target_timestamp}.tar.gz"

    if [[ ! -f "$backup_file" ]]; then
        log_warn "Config backup not found - skipping"
        return 0
    fi

    log_warn "⚠️  This will OVERWRITE .env and kernel_hashes.json!"
    log_info "Extracting: $backup_file"

    # Extract to root (paths are absolute in tar)
    tar -xzf "$backup_file" -C / >> "$LOG_FILE" 2>&1 || {
        # Try relative extraction
        tar -xzf "$backup_file" -C "$L9_DIR" >> "$LOG_FILE" 2>&1 || true
    }

    log_info "Configs restored"
}

# =============================================================================
# MAIN
# =============================================================================

usage() {
    cat <<EOF
L9 Memory Restore Script v1.0.0

Restores PostgreSQL (memories + embeddings), Neo4j (graph), and configs from S3.

Usage: $0 [OPTIONS] [TIMESTAMP]

Arguments:
    TIMESTAMP       Backup timestamp (YYYYMMDD_HHMMSS) or "latest"
                    If omitted, lists available backups

Options:
    --list          List available backups
    --postgres-only Restore only PostgreSQL
    --neo4j-only    Restore only Neo4j
    --config-only   Restore only configs
    --skip-neo4j    Skip Neo4j restore
    --skip-config   Skip config restore
    --yes           Skip confirmation prompt
    -h, --help      Show this help

Examples:
    # List available backups
    $0 --list

    # Restore latest backup
    $0 latest

    # Restore specific timestamp
    $0 20260118_120000

    # Restore only PostgreSQL from latest
    $0 latest --postgres-only

Environment Variables:
    S3_BUCKET       S3 bucket name (default: l9-backups)
    S3_REGION       AWS region (default: us-east-1)
    RESTORE_DIR     Local restore directory (default: /opt/l9/backups/restore)

EOF
}

main() {
    local target_timestamp=""
    local list_only=false
    local postgres_only=false
    local neo4j_only=false
    local config_only=false
    local skip_neo4j=false
    local skip_config=false
    local skip_confirm=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --list) list_only=true; shift ;;
            --postgres-only) postgres_only=true; shift ;;
            --neo4j-only) neo4j_only=true; shift ;;
            --config-only) config_only=true; shift ;;
            --skip-neo4j) skip_neo4j=true; shift ;;
            --skip-config) skip_config=true; shift ;;
            --yes) skip_confirm=true; shift ;;
            -h|--help) usage; exit 0 ;;
            -*) log_error "Unknown option: $1"; usage; exit 1 ;;
            *) target_timestamp="$1"; shift ;;
        esac
    done

    echo ""
    log_step "L9 Memory Restore"

    # List mode
    if [[ "$list_only" == "true" ]] || [[ -z "$target_timestamp" ]]; then
        list_available_backups
        exit 0
    fi

    # Get latest timestamp if requested
    if [[ "$target_timestamp" == "latest" ]]; then
        target_timestamp=$(get_latest_timestamp "postgres")
        if [[ -z "$target_timestamp" ]]; then
            log_error "No backups found in S3"
            exit 1
        fi
        log_info "Latest backup: $target_timestamp"
    fi

    # Confirm
    if [[ "$skip_confirm" != "true" ]]; then
        echo ""
        echo -e "${RED}⚠️  WARNING: This will OVERWRITE your current L9 memory data!${NC}"
        echo ""
        echo "Timestamp: $target_timestamp"
        echo ""
        read -p "Are you sure you want to proceed? (yes/no): " confirm
        if [[ "$confirm" != "yes" ]]; then
            log_info "Restore cancelled"
            exit 0
        fi
    fi

    # Create restore directory
    mkdir -p "$RESTORE_DIR"

    # Download backups
    download_from_s3 "$target_timestamp"

    # Restore based on options
    if [[ "$postgres_only" == "true" ]]; then
        restore_postgres "$target_timestamp"
    elif [[ "$neo4j_only" == "true" ]]; then
        restore_neo4j "$target_timestamp"
    elif [[ "$config_only" == "true" ]]; then
        restore_configs "$target_timestamp"
    else
        # Full restore
        restore_postgres "$target_timestamp"

        if [[ "$skip_neo4j" != "true" ]]; then
            restore_neo4j "$target_timestamp"
        fi

        if [[ "$skip_config" != "true" ]]; then
            restore_configs "$target_timestamp"
        fi
    fi

    # Summary
    log_step "Restore Complete"
    log_info "✅ L9 memory restored from: $target_timestamp"
    log_info "   Log: $LOG_FILE"
    log_info ""
    log_info "⚠️  Recommended: Restart L9 services to pick up restored data"
    log_info "   cd $L9_DIR && docker compose restart l9-api"
}

main "$@"
