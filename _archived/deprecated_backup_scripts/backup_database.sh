#!/usr/bin/env bash
# =============================================================================
# ⚠️  DEPRECATED - Use scripts/backup/backup_l9_memory.sh instead
# =============================================================================
#
# This script is DEPRECATED as of 2026-01-18.
#
# The new backup system provides:
#   - PostgreSQL + Neo4j + configs (this only did PostgreSQL)
#   - S3 upload with lifecycle policies
#   - 12-hour intervals (this was daily)
#   - Restore script included
#
# New scripts:
#   - scripts/backup/backup_l9_memory.sh  (backup)
#   - scripts/backup/restore_l9_memory.sh (restore)
#   - scripts/backup/setup_s3_bucket.sh   (S3 setup)
#   - scripts/backup/README.md            (documentation)
#
# =============================================================================
# L9 Automated Database Backup Script (DEPRECATED)
# Version: 1.0.0
#
# Creates automated PostgreSQL backups with multiple storage options.
# Designed to run via cron at 2 AM UTC daily.
#
# GOVERNANCE: IGOR_ONLY for cron setup
# CURSOR_SAFE: true (backup operations only)
# =============================================================================

echo ""
echo "⚠️  WARNING: This script is DEPRECATED"
echo "   Use: scripts/backup/backup_l9_memory.sh"
echo ""
echo "   The new script includes Neo4j + configs backup."
echo "   Continuing with legacy PostgreSQL-only backup..."
echo ""
sleep 2

set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================

# VPS Configuration
VPS_HOST="${VPS_HOST:-157.180.73.53}"
VPS_USER="${VPS_USER:-root}"
VPS_L9_DIR="${VPS_L9_DIR:-/opt/l9}"

# Backup Configuration
BACKUP_DIR="${BACKUP_DIR:-/root/L9_backups/database}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
MAX_BACKUPS="${MAX_BACKUPS:-30}"

# Database Configuration (from docker-compose environment)
DB_CONTAINER="${DB_CONTAINER:-l9-postgres}"
DB_NAME="${POSTGRES_DB:-l9_memory}"
DB_USER="${POSTGRES_USER:-l9_user}"

# S3 Configuration (optional)
S3_BUCKET="${S3_BUCKET:-}"
S3_PATH="${S3_PATH:-l9-backups/database}"
AWS_PROFILE="${AWS_PROFILE:-default}"

# Notification Configuration (optional)
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"
NOTIFY_ON_SUCCESS="${NOTIFY_ON_SUCCESS:-false}"
NOTIFY_ON_FAILURE="${NOTIFY_ON_FAILURE:-true}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Script state
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILENAME="l9_backup_${TIMESTAMP}.sql.gz"
LOG_FILE="/tmp/l9_backup_${TIMESTAMP}.log"

# =============================================================================
# LOGGING FUNCTIONS
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
# NOTIFICATION FUNCTIONS
# =============================================================================

send_slack_notification() {
    local status="$1"
    local message="$2"
    
    if [[ -z "$SLACK_WEBHOOK" ]]; then
        return 0
    fi
    
    local color="good"
    if [[ "$status" == "failure" ]]; then
        color="danger"
    fi
    
    curl -s -X POST "$SLACK_WEBHOOK" \
        -H 'Content-Type: application/json' \
        -d "{
            \"attachments\": [{
                \"color\": \"$color\",
                \"title\": \"L9 Database Backup - ${status^^}\",
                \"text\": \"$message\",
                \"footer\": \"L9 Backup System\",
                \"ts\": $(date +%s)
            }]
        }" > /dev/null 2>&1 || true
}

notify_success() {
    local message="$1"
    if [[ "$NOTIFY_ON_SUCCESS" == "true" ]]; then
        send_slack_notification "success" "$message"
    fi
}

notify_failure() {
    local message="$1"
    if [[ "$NOTIFY_ON_FAILURE" == "true" ]]; then
        send_slack_notification "failure" "$message"
    fi
}

# =============================================================================
# BACKUP FUNCTIONS
# =============================================================================

check_prerequisites() {
    log_step "Checking Prerequisites"
    
    # Check if running locally or remotely
    if [[ "${LOCAL_MODE:-false}" == "true" ]]; then
        log_info "Running in local mode"
        
        # Check Docker is running
        if ! docker info > /dev/null 2>&1; then
            log_error "Docker is not running"
            return 1
        fi
        
        # Check container exists
        if ! docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
            log_error "Database container '$DB_CONTAINER' is not running"
            return 1
        fi
    else
        log_info "Running in remote mode (VPS: $VPS_HOST)"
        
        # Check SSH connectivity
        if ! ssh -q -o BatchMode=yes -o ConnectTimeout=5 "$VPS_USER@$VPS_HOST" exit 2>/dev/null; then
            log_error "Cannot connect to VPS at $VPS_HOST"
            return 1
        fi
    fi
    
    log_info "Prerequisites check passed"
    return 0
}

create_backup_directory() {
    log_step "Creating Backup Directory"
    
    if [[ "${LOCAL_MODE:-false}" == "true" ]]; then
        mkdir -p "$BACKUP_DIR"
        log_info "Created local backup directory: $BACKUP_DIR"
    else
        ssh "$VPS_USER@$VPS_HOST" "mkdir -p $BACKUP_DIR"
        log_info "Created VPS backup directory: $BACKUP_DIR"
    fi
}

perform_backup() {
    log_step "Performing Database Backup"
    
    local backup_path="$BACKUP_DIR/$BACKUP_FILENAME"
    local start_time=$(date +%s)
    
    if [[ "${LOCAL_MODE:-false}" == "true" ]]; then
        log_info "Backing up database locally..."
        
        docker exec "$DB_CONTAINER" pg_dump \
            -U "$DB_USER" \
            -d "$DB_NAME" \
            --clean \
            --if-exists \
            --no-owner \
            --no-privileges \
            2>> "$LOG_FILE" | gzip > "$backup_path"
    else
        log_info "Backing up database on VPS..."
        
        ssh "$VPS_USER@$VPS_HOST" bash <<REMOTE_EOF
            set -e
            cd "$VPS_L9_DIR"
            
            docker exec "$DB_CONTAINER" pg_dump \
                -U "$DB_USER" \
                -d "$DB_NAME" \
                --clean \
                --if-exists \
                --no-owner \
                --no-privileges \
                2>/dev/null | gzip > "$backup_path"
REMOTE_EOF
    fi
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    # Verify backup exists and has content
    local backup_size
    if [[ "${LOCAL_MODE:-false}" == "true" ]]; then
        backup_size=$(stat -f%z "$backup_path" 2>/dev/null || stat --printf="%s" "$backup_path" 2>/dev/null || echo "0")
    else
        backup_size=$(ssh "$VPS_USER@$VPS_HOST" "stat --printf='%s' '$backup_path' 2>/dev/null || echo 0")
    fi
    
    if [[ "$backup_size" -lt 1000 ]]; then
        log_error "Backup file is too small (${backup_size} bytes). Backup may have failed."
        return 1
    fi
    
    local size_mb=$(echo "scale=2; $backup_size / 1048576" | bc)
    log_info "Backup created: $backup_path"
    log_info "Size: ${size_mb}MB, Duration: ${duration}s"
    
    echo "$backup_path"
    return 0
}

upload_to_s3() {
    local backup_path="$1"
    
    if [[ -z "$S3_BUCKET" ]]; then
        log_info "S3 upload skipped (S3_BUCKET not configured)"
        return 0
    fi
    
    log_step "Uploading to S3"
    
    local s3_uri="s3://${S3_BUCKET}/${S3_PATH}/${BACKUP_FILENAME}"
    
    if [[ "${LOCAL_MODE:-false}" == "true" ]]; then
        aws s3 cp "$backup_path" "$s3_uri" --profile "$AWS_PROFILE" 2>> "$LOG_FILE"
    else
        ssh "$VPS_USER@$VPS_HOST" "aws s3 cp '$backup_path' '$s3_uri' --profile '$AWS_PROFILE'" 2>> "$LOG_FILE"
    fi
    
    log_info "Uploaded to S3: $s3_uri"
}

cleanup_old_backups() {
    log_step "Cleaning Up Old Backups"
    
    if [[ "${LOCAL_MODE:-false}" == "true" ]]; then
        # Delete backups older than RETENTION_DAYS
        find "$BACKUP_DIR" -name "l9_backup_*.sql.gz" -mtime +"$RETENTION_DAYS" -delete 2>/dev/null || true
        
        # Keep only MAX_BACKUPS most recent
        local backup_count=$(ls -1 "$BACKUP_DIR"/l9_backup_*.sql.gz 2>/dev/null | wc -l || echo "0")
        if [[ "$backup_count" -gt "$MAX_BACKUPS" ]]; then
            local to_delete=$((backup_count - MAX_BACKUPS))
            ls -1t "$BACKUP_DIR"/l9_backup_*.sql.gz | tail -n "$to_delete" | xargs rm -f
            log_info "Deleted $to_delete old backups (keeping $MAX_BACKUPS)"
        fi
    else
        ssh "$VPS_USER@$VPS_HOST" bash <<REMOTE_EOF
            # Delete backups older than RETENTION_DAYS
            find "$BACKUP_DIR" -name "l9_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
            
            # Keep only MAX_BACKUPS most recent
            backup_count=\$(ls -1 "$BACKUP_DIR"/l9_backup_*.sql.gz 2>/dev/null | wc -l || echo "0")
            if [[ "\$backup_count" -gt "$MAX_BACKUPS" ]]; then
                to_delete=\$((backup_count - $MAX_BACKUPS))
                ls -1t "$BACKUP_DIR"/l9_backup_*.sql.gz | tail -n "\$to_delete" | xargs rm -f
                echo "Deleted \$to_delete old backups"
            fi
REMOTE_EOF
    fi
    
    # Clean up S3 if configured
    if [[ -n "$S3_BUCKET" ]]; then
        log_info "S3 lifecycle policies should handle S3 cleanup"
    fi
    
    log_info "Cleanup complete"
}

verify_backup_integrity() {
    local backup_path="$1"
    
    log_step "Verifying Backup Integrity"
    
    # Test that the gzip file is valid
    if [[ "${LOCAL_MODE:-false}" == "true" ]]; then
        if gzip -t "$backup_path" 2>/dev/null; then
            log_info "Backup integrity verified (gzip OK)"
        else
            log_error "Backup integrity check failed (corrupt gzip)"
            return 1
        fi
    else
        if ssh "$VPS_USER@$VPS_HOST" "gzip -t '$backup_path'" 2>/dev/null; then
            log_info "Backup integrity verified (gzip OK)"
        else
            log_error "Backup integrity check failed (corrupt gzip)"
            return 1
        fi
    fi
    
    return 0
}

generate_backup_manifest() {
    local backup_path="$1"
    
    log_step "Generating Backup Manifest"
    
    local manifest_file="$BACKUP_DIR/backup_manifest.json"
    local backup_size
    local backup_hash
    
    if [[ "${LOCAL_MODE:-false}" == "true" ]]; then
        backup_size=$(stat -f%z "$backup_path" 2>/dev/null || stat --printf="%s" "$backup_path" 2>/dev/null)
        backup_hash=$(md5sum "$backup_path" 2>/dev/null | cut -d' ' -f1 || md5 -q "$backup_path" 2>/dev/null)
    else
        backup_size=$(ssh "$VPS_USER@$VPS_HOST" "stat --printf='%s' '$backup_path'")
        backup_hash=$(ssh "$VPS_USER@$VPS_HOST" "md5sum '$backup_path' | cut -d' ' -f1")
    fi
    
    local manifest_entry="{
  \"timestamp\": \"$TIMESTAMP\",
  \"filename\": \"$BACKUP_FILENAME\",
  \"path\": \"$backup_path\",
  \"size_bytes\": $backup_size,
  \"md5_hash\": \"$backup_hash\",
  \"database\": \"$DB_NAME\",
  \"s3_uploaded\": $([ -n "$S3_BUCKET" ] && echo "true" || echo "false"),
  \"retention_days\": $RETENTION_DAYS
}"

    if [[ "${LOCAL_MODE:-false}" == "true" ]]; then
        echo "$manifest_entry" >> "$manifest_file"
    else
        ssh "$VPS_USER@$VPS_HOST" "echo '$manifest_entry' >> '$manifest_file'"
    fi
    
    log_info "Manifest updated: $manifest_file"
}

# =============================================================================
# MAIN
# =============================================================================

usage() {
    cat <<EOF
L9 Database Backup Script v1.0.0

Usage: $0 [OPTIONS]

Options:
    --local             Run in local mode (backup local Docker)
    --dry-run           Show what would be done without doing it
    --no-cleanup        Skip cleanup of old backups
    --no-s3             Skip S3 upload even if configured
    --verbose           Show verbose output
    -h, --help          Show this help message

Environment Variables:
    VPS_HOST            VPS hostname (default: 157.180.73.53)
    VPS_USER            VPS username (default: root)
    BACKUP_DIR          Backup directory (default: /root/L9_backups/database)
    RETENTION_DAYS      Days to keep backups (default: 30)
    MAX_BACKUPS         Maximum backups to keep (default: 30)
    S3_BUCKET           S3 bucket for remote backup (optional)
    SLACK_WEBHOOK       Slack webhook for notifications (optional)

Example:
    # Backup VPS database
    $0

    # Backup local Docker database
    $0 --local

    # Dry run
    $0 --dry-run

Cron Setup (2 AM UTC daily):
    0 2 * * * /opt/l9/scripts/deployment/backup_database.sh >> /var/log/l9_backup.log 2>&1
EOF
}

main() {
    local dry_run=false
    local no_cleanup=false
    local no_s3=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --local)
                export LOCAL_MODE=true
                shift
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            --no-cleanup)
                no_cleanup=true
                shift
                ;;
            --no-s3)
                no_s3=true
                S3_BUCKET=""
                shift
                ;;
            --verbose)
                set -x
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
    
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  L9 Database Backup - $(date '+%Y-%m-%d %H:%M:%S UTC')${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    if [[ "$dry_run" == "true" ]]; then
        log_warn "DRY RUN MODE - No actual backup will be created"
        log_info "Would backup database: $DB_NAME"
        log_info "Would save to: $BACKUP_DIR/$BACKUP_FILENAME"
        [[ -n "$S3_BUCKET" ]] && log_info "Would upload to S3: s3://${S3_BUCKET}/${S3_PATH}/"
        exit 0
    fi
    
    # Execute backup pipeline
    local backup_path=""
    local exit_code=0
    
    if check_prerequisites; then
        create_backup_directory
        
        if backup_path=$(perform_backup); then
            if verify_backup_integrity "$backup_path"; then
                generate_backup_manifest "$backup_path"
                
                if [[ "$no_s3" != "true" ]]; then
                    upload_to_s3 "$backup_path" || log_warn "S3 upload failed (non-fatal)"
                fi
                
                if [[ "$no_cleanup" != "true" ]]; then
                    cleanup_old_backups
                fi
                
                log_step "Backup Complete"
                log_info "✅ Database backup successful: $BACKUP_FILENAME"
                notify_success "Backup completed: $BACKUP_FILENAME"
            else
                exit_code=1
            fi
        else
            exit_code=1
        fi
    else
        exit_code=1
    fi
    
    if [[ $exit_code -ne 0 ]]; then
        log_error "❌ Database backup FAILED"
        notify_failure "Backup failed. Check logs: $LOG_FILE"
    fi
    
    exit $exit_code
}

main "$@"
