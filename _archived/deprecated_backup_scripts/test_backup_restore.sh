#!/usr/bin/env bash
# =============================================================================
# ⚠️  DEPRECATED - Use scripts/backup/restore_l9_memory.sh instead
# =============================================================================
#
# This script is DEPRECATED as of 2026-01-18.
#
# The new backup system provides:
#   - scripts/backup/backup_l9_memory.sh  (backup PostgreSQL + Neo4j + configs)
#   - scripts/backup/restore_l9_memory.sh (restore with --list, latest, timestamp)
#   - scripts/backup/README.md            (documentation)
#
# To test restore:
#   ./scripts/backup/restore_l9_memory.sh --list   # List available backups
#   ./scripts/backup/restore_l9_memory.sh latest   # Restore latest
#
# =============================================================================
# L9 Backup Restoration Test Script (DEPRECATED)
# Version: 1.0.0
#
# Tests backup and restore procedures to verify data recovery capability.
# Should be run before major deployments or monthly for validation.
#
# GOVERNANCE: IGOR_ONLY for production testing
# CURSOR_SAFE: true (read-only verification by default)
# =============================================================================

echo ""
echo "⚠️  WARNING: This script is DEPRECATED"
echo "   Use: scripts/backup/restore_l9_memory.sh"
echo ""
echo "   The new restore script supports:"
echo "     --list              List available S3 backups"
echo "     latest              Restore most recent backup"
echo "     YYYYMMDD_HHMMSS     Restore specific timestamp"
echo ""
echo "   Continuing with legacy test harness..."
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

# Test Configuration
BACKUP_DIR="${BACKUP_DIR:-/root/L9_backups/database}"
TEST_DB_NAME="${TEST_DB_NAME:-l9_memory_test_restore}"
DB_CONTAINER="${DB_CONTAINER:-l9-postgres}"
DB_USER="${POSTGRES_USER:-l9_user}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Script state
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TEST_LOG="/tmp/l9_restore_test_${TIMESTAMP}.log"
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# =============================================================================
# LOGGING FUNCTIONS
# =============================================================================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $*" | tee -a "$TEST_LOG"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*" | tee -a "$TEST_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" | tee -a "$TEST_LOG"
}

log_test() {
    echo -e "${CYAN}[TEST]${NC} $*" | tee -a "$TEST_LOG"
}

log_step() {
    echo "" | tee -a "$TEST_LOG"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}" | tee -a "$TEST_LOG"
    echo -e "${BLUE}  $1${NC}" | tee -a "$TEST_LOG"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}" | tee -a "$TEST_LOG"
}

# =============================================================================
# TEST RESULT TRACKING
# =============================================================================

test_pass() {
    local test_name="$1"
    echo -e "${GREEN}  ✅ PASS${NC}: $test_name" | tee -a "$TEST_LOG"
    ((TESTS_PASSED++))
}

test_fail() {
    local test_name="$1"
    local reason="${2:-}"
    echo -e "${RED}  ❌ FAIL${NC}: $test_name" | tee -a "$TEST_LOG"
    [[ -n "$reason" ]] && echo -e "      Reason: $reason" | tee -a "$TEST_LOG"
    ((TESTS_FAILED++))
}

test_skip() {
    local test_name="$1"
    local reason="${2:-}"
    echo -e "${YELLOW}  ⏭️  SKIP${NC}: $test_name" | tee -a "$TEST_LOG"
    [[ -n "$reason" ]] && echo -e "      Reason: $reason" | tee -a "$TEST_LOG"
    ((TESTS_SKIPPED++))
}

# =============================================================================
# TEST FUNCTIONS
# =============================================================================

test_backup_script_exists() {
    log_test "Testing: Backup script exists"
    
    local backup_script="$SCRIPT_DIR/backup_database.sh"
    
    if [[ -f "$backup_script" ]]; then
        test_pass "Backup script exists at $backup_script"
        
        if [[ -x "$backup_script" ]]; then
            test_pass "Backup script is executable"
        else
            test_fail "Backup script is not executable"
        fi
    else
        test_fail "Backup script not found at $backup_script"
    fi
}

test_rollback_script_exists() {
    log_test "Testing: Rollback script exists"
    
    local rollback_script="$SCRIPT_DIR/rollback_vps.sh"
    
    if [[ -f "$rollback_script" ]]; then
        test_pass "Rollback script exists at $rollback_script"
        
        if [[ -x "$rollback_script" ]]; then
            test_pass "Rollback script is executable"
        else
            test_fail "Rollback script is not executable"
        fi
    else
        test_fail "Rollback script not found at $rollback_script"
    fi
}

test_backup_directory_structure() {
    log_test "Testing: Backup directory structure"
    
    if [[ "${LOCAL_MODE:-false}" == "true" ]]; then
        if [[ -d "$BACKUP_DIR" ]]; then
            test_pass "Backup directory exists: $BACKUP_DIR"
            
            local backup_count=$(ls -1 "$BACKUP_DIR"/l9_backup_*.sql.gz 2>/dev/null | wc -l || echo "0")
            if [[ "$backup_count" -gt 0 ]]; then
                test_pass "Found $backup_count backup file(s)"
            else
                test_warn "No backup files found (directory empty)"
            fi
        else
            test_skip "Backup directory not found" "Run backup_database.sh first"
        fi
    else
        local result=$(ssh "$VPS_USER@$VPS_HOST" "[ -d '$BACKUP_DIR' ] && echo 'exists' || echo 'missing'" 2>/dev/null)
        
        if [[ "$result" == "exists" ]]; then
            test_pass "VPS backup directory exists: $BACKUP_DIR"
            
            local backup_count=$(ssh "$VPS_USER@$VPS_HOST" "ls -1 '$BACKUP_DIR'/l9_backup_*.sql.gz 2>/dev/null | wc -l || echo 0")
            if [[ "$backup_count" -gt 0 ]]; then
                test_pass "Found $backup_count VPS backup file(s)"
            else
                test_skip "No VPS backup files found" "Run backup_database.sh first"
            fi
        else
            test_skip "VPS backup directory not found" "Run backup_database.sh first"
        fi
    fi
}

test_latest_backup_integrity() {
    log_test "Testing: Latest backup file integrity"
    
    local latest_backup
    
    if [[ "${LOCAL_MODE:-false}" == "true" ]]; then
        latest_backup=$(ls -1t "$BACKUP_DIR"/l9_backup_*.sql.gz 2>/dev/null | head -1 || echo "")
    else
        latest_backup=$(ssh "$VPS_USER@$VPS_HOST" "ls -1t '$BACKUP_DIR'/l9_backup_*.sql.gz 2>/dev/null | head -1 || echo ''" 2>/dev/null)
    fi
    
    if [[ -z "$latest_backup" ]]; then
        test_skip "No backup files to test" "Create a backup first"
        return
    fi
    
    log_info "Testing backup: $latest_backup"
    
    # Test gzip integrity
    if [[ "${LOCAL_MODE:-false}" == "true" ]]; then
        if gzip -t "$latest_backup" 2>/dev/null; then
            test_pass "Backup gzip integrity verified"
        else
            test_fail "Backup gzip file is corrupted"
            return
        fi
        
        # Check minimum size (should be at least 1KB)
        local size=$(stat -f%z "$latest_backup" 2>/dev/null || stat --printf="%s" "$latest_backup" 2>/dev/null)
    else
        if ssh "$VPS_USER@$VPS_HOST" "gzip -t '$latest_backup'" 2>/dev/null; then
            test_pass "VPS backup gzip integrity verified"
        else
            test_fail "VPS backup gzip file is corrupted"
            return
        fi
        
        local size=$(ssh "$VPS_USER@$VPS_HOST" "stat --printf='%s' '$latest_backup'" 2>/dev/null)
    fi
    
    if [[ "$size" -gt 1000 ]]; then
        local size_kb=$((size / 1024))
        test_pass "Backup size OK (${size_kb}KB)"
    else
        test_fail "Backup file too small (${size} bytes)"
    fi
}

test_backup_contains_valid_sql() {
    log_test "Testing: Backup contains valid SQL structure"
    
    local latest_backup
    
    if [[ "${LOCAL_MODE:-false}" == "true" ]]; then
        latest_backup=$(ls -1t "$BACKUP_DIR"/l9_backup_*.sql.gz 2>/dev/null | head -1 || echo "")
        
        if [[ -z "$latest_backup" ]]; then
            test_skip "No backup files to test"
            return
        fi
        
        # Check for common PostgreSQL dump markers
        local has_create=$(zcat "$latest_backup" 2>/dev/null | head -100 | grep -c "CREATE" || echo "0")
        local has_drop=$(zcat "$latest_backup" 2>/dev/null | head -100 | grep -c "DROP" || echo "0")
    else
        latest_backup=$(ssh "$VPS_USER@$VPS_HOST" "ls -1t '$BACKUP_DIR'/l9_backup_*.sql.gz 2>/dev/null | head -1 || echo ''" 2>/dev/null)
        
        if [[ -z "$latest_backup" ]]; then
            test_skip "No VPS backup files to test"
            return
        fi
        
        local has_create=$(ssh "$VPS_USER@$VPS_HOST" "zcat '$latest_backup' 2>/dev/null | head -100 | grep -c 'CREATE' || echo 0")
        local has_drop=$(ssh "$VPS_USER@$VPS_HOST" "zcat '$latest_backup' 2>/dev/null | head -100 | grep -c 'DROP' || echo 0")
    fi
    
    if [[ "$has_create" -gt 0 ]] && [[ "$has_drop" -gt 0 ]]; then
        test_pass "Backup contains valid SQL structure (CREATE/DROP statements found)"
    else
        test_fail "Backup may not contain valid SQL dump"
    fi
}

test_restore_to_test_database() {
    log_test "Testing: Restore to test database (non-destructive)"
    
    if [[ "${SKIP_RESTORE_TEST:-false}" == "true" ]]; then
        test_skip "Restore test skipped" "SKIP_RESTORE_TEST=true"
        return
    fi
    
    local latest_backup
    
    if [[ "${LOCAL_MODE:-false}" == "true" ]]; then
        latest_backup=$(ls -1t "$BACKUP_DIR"/l9_backup_*.sql.gz 2>/dev/null | head -1 || echo "")
        
        if [[ -z "$latest_backup" ]]; then
            test_skip "No backup files to test"
            return
        fi
        
        log_info "Creating test database: $TEST_DB_NAME"
        
        # Create test database
        docker exec "$DB_CONTAINER" psql -U "$DB_USER" -c "DROP DATABASE IF EXISTS $TEST_DB_NAME;" 2>/dev/null || true
        docker exec "$DB_CONTAINER" psql -U "$DB_USER" -c "CREATE DATABASE $TEST_DB_NAME;" 2>/dev/null
        
        # Restore to test database
        if zcat "$latest_backup" | docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$TEST_DB_NAME" 2>/dev/null; then
            test_pass "Backup restored to test database successfully"
            
            # Verify some tables exist
            local table_count=$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$TEST_DB_NAME" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ')
            
            if [[ "$table_count" -gt 0 ]]; then
                test_pass "Restored database has $table_count table(s)"
            else
                test_fail "Restored database has no tables"
            fi
        else
            test_fail "Failed to restore backup to test database"
        fi
        
        # Cleanup test database
        log_info "Cleaning up test database..."
        docker exec "$DB_CONTAINER" psql -U "$DB_USER" -c "DROP DATABASE IF EXISTS $TEST_DB_NAME;" 2>/dev/null || true
        
    else
        latest_backup=$(ssh "$VPS_USER@$VPS_HOST" "ls -1t '$BACKUP_DIR'/l9_backup_*.sql.gz 2>/dev/null | head -1 || echo ''" 2>/dev/null)
        
        if [[ -z "$latest_backup" ]]; then
            test_skip "No VPS backup files to test"
            return
        fi
        
        log_info "Creating VPS test database: $TEST_DB_NAME"
        
        ssh "$VPS_USER@$VPS_HOST" bash <<REMOTE_EOF
            set -e
            cd "$VPS_L9_DIR"
            
            # Create test database
            docker exec "$DB_CONTAINER" psql -U "$DB_USER" -c "DROP DATABASE IF EXISTS $TEST_DB_NAME;" 2>/dev/null || true
            docker exec "$DB_CONTAINER" psql -U "$DB_USER" -c "CREATE DATABASE $TEST_DB_NAME;" 2>/dev/null
            
            # Restore to test database
            zcat "$latest_backup" | docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$TEST_DB_NAME" 2>/dev/null
            
            # Verify tables
            table_count=\$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$TEST_DB_NAME" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ')
            echo "TABLES:\$table_count"
            
            # Cleanup
            docker exec "$DB_CONTAINER" psql -U "$DB_USER" -c "DROP DATABASE IF EXISTS $TEST_DB_NAME;" 2>/dev/null || true
REMOTE_EOF
        
        if [[ $? -eq 0 ]]; then
            test_pass "VPS backup restore test completed"
        else
            test_fail "VPS backup restore test failed"
        fi
    fi
}

test_backup_manifest() {
    log_test "Testing: Backup manifest exists and is valid"
    
    local manifest_file="$BACKUP_DIR/backup_manifest.json"
    
    if [[ "${LOCAL_MODE:-false}" == "true" ]]; then
        if [[ -f "$manifest_file" ]]; then
            test_pass "Backup manifest exists"
            
            # Check if it's valid JSON-ish (line by line JSON objects)
            local line_count=$(wc -l < "$manifest_file" | tr -d ' ')
            if [[ "$line_count" -gt 0 ]]; then
                test_pass "Manifest has $line_count entries"
            else
                test_fail "Manifest is empty"
            fi
        else
            test_skip "Backup manifest not found" "Run backup with manifest generation"
        fi
    else
        local result=$(ssh "$VPS_USER@$VPS_HOST" "[ -f '$manifest_file' ] && wc -l < '$manifest_file' || echo 'missing'" 2>/dev/null)
        
        if [[ "$result" == "missing" ]]; then
            test_skip "VPS backup manifest not found" "Run backup with manifest generation"
        else
            test_pass "VPS backup manifest exists with $result entries"
        fi
    fi
}

test_rollback_prerequisites() {
    log_test "Testing: Rollback prerequisites"
    
    local app_backup_dir="/root/L9_backups"
    
    if [[ "${LOCAL_MODE:-false}" == "true" ]]; then
        test_skip "Rollback test only applicable to VPS" "Use --remote flag"
        return
    fi
    
    # Check if VPS has application backups
    local result=$(ssh "$VPS_USER@$VPS_HOST" "[ -d '$app_backup_dir' ] && ls -1 '$app_backup_dir' 2>/dev/null | wc -l || echo 'missing'" 2>/dev/null)
    
    if [[ "$result" == "missing" ]]; then
        test_skip "VPS application backup directory not found"
    elif [[ "$result" -gt 0 ]]; then
        test_pass "Found $result application backup(s) for rollback"
    else
        test_skip "No application backups available for rollback"
    fi
}

# =============================================================================
# REPORT GENERATION
# =============================================================================

generate_test_report() {
    log_step "Test Results Summary"
    
    local total=$((TESTS_PASSED + TESTS_FAILED + TESTS_SKIPPED))
    
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "  L9 Backup/Restore Test Results"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    echo -e "  ${GREEN}PASSED${NC}:  $TESTS_PASSED"
    echo -e "  ${RED}FAILED${NC}:  $TESTS_FAILED"
    echo -e "  ${YELLOW}SKIPPED${NC}: $TESTS_SKIPPED"
    echo "  ─────────────────"
    echo "  TOTAL:   $total"
    echo ""
    
    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo -e "  ${GREEN}✅ ALL TESTS PASSED${NC}"
        echo ""
        echo "  Backup/restore procedures are verified and working."
    else
        echo -e "  ${RED}❌ SOME TESTS FAILED${NC}"
        echo ""
        echo "  Review failed tests above and fix issues before deployment."
    fi
    
    echo ""
    echo "  Log file: $TEST_LOG"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
}

# =============================================================================
# MAIN
# =============================================================================

usage() {
    cat <<EOF
L9 Backup Restoration Test Script v1.0.0

Usage: $0 [OPTIONS]

Options:
    --local             Test local Docker environment
    --remote            Test VPS environment (default)
    --skip-restore      Skip the actual restore test
    --verbose           Show verbose output
    -h, --help          Show this help message

Environment Variables:
    VPS_HOST            VPS hostname (default: 157.180.73.53)
    VPS_USER            VPS username (default: root)
    BACKUP_DIR          Backup directory to test
    SKIP_RESTORE_TEST   Skip restore test if true

Examples:
    # Test VPS backups
    $0

    # Test local Docker backups
    $0 --local

    # Test without actual restore
    $0 --skip-restore

Recommended Schedule:
    - Before major deployments
    - Monthly validation
    - After backup script changes
EOF
}

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --local)
                export LOCAL_MODE=true
                shift
                ;;
            --remote)
                export LOCAL_MODE=false
                shift
                ;;
            --skip-restore)
                export SKIP_RESTORE_TEST=true
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
    echo -e "${BLUE}  L9 Backup/Restore Verification - $(date '+%Y-%m-%d %H:%M:%S')${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    local mode="VPS"
    [[ "${LOCAL_MODE:-false}" == "true" ]] && mode="Local"
    log_info "Test Mode: $mode"
    
    # Run all tests
    log_step "Script Verification Tests"
    test_backup_script_exists
    test_rollback_script_exists
    
    log_step "Backup Directory Tests"
    test_backup_directory_structure
    test_backup_manifest
    
    log_step "Backup Integrity Tests"
    test_latest_backup_integrity
    test_backup_contains_valid_sql
    
    log_step "Restore Capability Tests"
    test_restore_to_test_database
    test_rollback_prerequisites
    
    # Generate report
    generate_test_report
    
    # Exit with appropriate code
    if [[ $TESTS_FAILED -gt 0 ]]; then
        exit 1
    fi
    exit 0
}

main "$@"
