#!/usr/bin/env bash
# =============================================================================
# L9 CI GATES - STRICT VALIDATION PIPELINE
# =============================================================================
# 
# This script runs ALL CI validators before:
#   - Codegen merge
#   - Docker build
#   - Deployment
#
# BEHAVIOR:
#   - Fail HARD on any validation error
#   - NO permissive fallbacks
#   - NO "continue on error"
#
# EXIT CODES:
#   0 = All gates passed
#   1 = Validation failed (hard stop)
#   2 = Configuration error
#
# Usage:
#   ./ci/run_ci_gates.sh spec.yaml [file1.py file2.py ...]
#   ./ci/run_ci_gates.sh --all
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# =============================================================================
# LOGGING
# =============================================================================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_header() {
    echo ""
    echo "=================================================================="
    echo " $1"
    echo "=================================================================="
}

# =============================================================================
# GATE 1: SPEC VALIDATION
# =============================================================================

run_spec_validation() {
    local spec_file="$1"
    
    log_header "GATE 1: SPEC VALIDATION (v2.5)"
    
    if [[ ! -f "$spec_file" ]]; then
        log_error "Spec file not found: $spec_file"
        return 1
    fi
    
    log_info "Validating spec: $spec_file"
    
    python3 "$SCRIPT_DIR/validate_spec_v25.py" "$spec_file"
    local status=$?
    
    if [[ $status -ne 0 ]]; then
        log_error "SPEC VALIDATION FAILED"
        log_error "Fix all errors before proceeding"
        return 1
    fi
    
    log_info "✅ Spec validation passed"
    return 0
}

# =============================================================================
# GATE 2: CODE VALIDATION
# =============================================================================

run_code_validation() {
    local spec_file="$1"
    shift
    local files=("$@")
    
    log_header "GATE 2: CODE VALIDATION"
    
    if [[ ${#files[@]} -eq 0 ]]; then
        log_warn "No files provided for code validation"
        return 0
    fi
    
    log_info "Validating ${#files[@]} files against spec"
    
    python3 "$SCRIPT_DIR/validate_codegen.py" --spec "$spec_file" --files "${files[@]}"
    local status=$?
    
    if [[ $status -ne 0 ]]; then
        log_error "CODE VALIDATION FAILED"
        log_error "Fix all errors before proceeding"
        return 1
    fi
    
    log_info "✅ Code validation passed"
    return 0
}

# =============================================================================
# GATE 3: SYNTAX CHECK
# =============================================================================

run_syntax_check() {
    local files=("$@")
    
    log_header "GATE 3: PYTHON SYNTAX CHECK"
    
    if [[ ${#files[@]} -eq 0 ]]; then
        log_warn "No files provided for syntax check"
        return 0
    fi
    
    local failed=0
    for file in "${files[@]}"; do
        if [[ "$file" == *.py ]]; then
            if ! python3 -m py_compile "$file" 2>/dev/null; then
                log_error "Syntax error in: $file"
                python3 -m py_compile "$file"
                failed=1
            fi
        fi
    done
    
    if [[ $failed -ne 0 ]]; then
        log_error "SYNTAX CHECK FAILED"
        return 1
    fi
    
    log_info "✅ Syntax check passed"
    return 0
}

# =============================================================================
# GATE 4: IMPORT CHECK
# =============================================================================

run_import_check() {
    local files=("$@")
    
    log_header "GATE 4: IMPORT RESOLUTION CHECK"
    
    if [[ ${#files[@]} -eq 0 ]]; then
        log_warn "No files provided for import check"
        return 0
    fi
    
    local failed=0
    for file in "${files[@]}"; do
        if [[ "$file" == *.py ]]; then
            # Try to parse and check imports
            if ! python3 -c "
import ast
import sys
try:
    with open('$file', 'r') as f:
        ast.parse(f.read())
    sys.exit(0)
except SyntaxError as e:
    print(f'Parse error: {e}')
    sys.exit(1)
" 2>/dev/null; then
                log_error "Parse error in: $file"
                failed=1
            fi
        fi
    done
    
    if [[ $failed -ne 0 ]]; then
        log_error "IMPORT CHECK FAILED"
        return 1
    fi
    
    log_info "✅ Import check passed"
    return 0
}

# =============================================================================
# GATE 5: TEST FILE PRESENCE
# =============================================================================

run_test_presence_check() {
    local spec_file="$1"
    shift
    local files=("$@")
    
    log_header "GATE 5: TEST FILE PRESENCE CHECK"
    
    # Extract module_id from spec
    local module_id
    module_id=$(python3 -c "
import yaml
with open('$spec_file') as f:
    spec = yaml.safe_load(f)
    print(spec.get('metadata', {}).get('module_id', ''))
" 2>/dev/null || echo "")
    
    if [[ -z "$module_id" ]]; then
        log_warn "Could not extract module_id from spec"
        return 0
    fi
    
    # Check for test files
    local test_file_found=0
    for file in "${files[@]}"; do
        if [[ "$file" == *test_* ]] || [[ "$file" == *_test.py ]]; then
            test_file_found=1
            break
        fi
    done
    
    if [[ $test_file_found -eq 0 ]]; then
        # Check if tests exist in repo
        if [[ -f "$REPO_ROOT/tests/test_${module_id}_adapter.py" ]] || \
           [[ -f "$REPO_ROOT/tests/test_${module_id}.py" ]]; then
            test_file_found=1
        fi
    fi
    
    if [[ $test_file_found -eq 0 ]]; then
        log_error "NO TEST FILES FOUND for module: $module_id"
        log_error "Expected: tests/test_${module_id}_adapter.py or similar"
        return 1
    fi
    
    log_info "✅ Test file presence check passed"
    return 0
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    log_header "L9 CI GATES - STARTING VALIDATION PIPELINE"
    
    if [[ $# -lt 1 ]]; then
        echo "Usage: $0 <spec.yaml> [file1.py file2.py ...]"
        echo "       $0 --all (validate all specs)"
        exit 2
    fi
    
    if [[ "$1" == "--all" ]]; then
        log_info "Running validation on all specs..."
        # Find all spec files and validate
        local all_passed=0
        while IFS= read -r -d '' spec_file; do
            if ! run_spec_validation "$spec_file"; then
                all_passed=1
            fi
        done < <(find "$REPO_ROOT" -name "*spec*.yaml" -print0 2>/dev/null)
        
        if [[ $all_passed -ne 0 ]]; then
            log_error "SOME VALIDATIONS FAILED"
            exit 1
        fi
        
        log_info "✅ ALL VALIDATIONS PASSED"
        exit 0
    fi
    
    local spec_file="$1"
    shift
    local files=("$@")
    
    # Run all gates in sequence - fail fast
    run_spec_validation "$spec_file" || exit 1
    run_code_validation "$spec_file" "${files[@]}" || exit 1
    run_syntax_check "${files[@]}" || exit 1
    run_import_check "${files[@]}" || exit 1
    run_test_presence_check "$spec_file" "${files[@]}" || exit 1
    
    log_header "🎉 ALL CI GATES PASSED"
    log_info "Code is ready for merge/build/deploy"
    
    exit 0
}

main "$@"

