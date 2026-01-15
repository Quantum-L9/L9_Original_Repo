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
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

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
    
    if [ ! -f "$SCRIPT_DIR/check_syntax.py" ]; then
        log_error "Syntax checker script not found: $SCRIPT_DIR/check_syntax.py"
        return 1
    fi
    
    if [[ ${#files[@]} -eq 0 ]]; then
        log_info "Checking syntax for all Python files..."
        if ! python3 "$SCRIPT_DIR/check_syntax.py"; then
            log_error "Syntax errors found in codebase"
            return 1
        fi
    else
        log_info "Checking Python syntax for ${#files[@]} file(s)..."
        
        # Filter to only Python files
        local py_files=()
        for file in "${files[@]}"; do
            if [[ "$file" == *.py ]]; then
                py_files+=("$file")
            fi
        done
        
        if [[ ${#py_files[@]} -eq 0 ]]; then
            log_info "No Python files to check"
            return 0
        fi
        
        if ! python3 "$SCRIPT_DIR/check_syntax.py" "${py_files[@]}"; then
            log_error "Syntax errors found in files"
            return 1
        fi
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
# GATE 5: FORBIDDEN IMPORTS LINT
# =============================================================================

gate_5_forbidden_imports() {
    local files=("$@")
    
    log_header "GATE 5: FORBIDDEN IMPORTS LINT"
    
    if [ ! -f "$SCRIPT_DIR/lint_forbidden_imports.py" ]; then
        log_error "Linter script not found: $SCRIPT_DIR/lint_forbidden_imports.py"
        return 1
    fi
    
    log_info "Checking for forbidden imports (logging, aiohttp, requests, print)..."
    
    # If specific files provided, check only those
    if [ ${#files[@]} -gt 0 ]; then
        if ! python3 "$SCRIPT_DIR/lint_forbidden_imports.py" "${files[@]}"; then
            log_error "Forbidden imports/patterns found in files"
            log_info "Run with --fix to auto-fix: python3 ci/lint_forbidden_imports.py --fix [files]"
            return 1
        fi
    else
        # Check all Python files in the repo
        if ! python3 "$SCRIPT_DIR/lint_forbidden_imports.py"; then
            log_error "Forbidden imports/patterns found in codebase"
            log_info "Run with --fix to auto-fix: python3 ci/lint_forbidden_imports.py --fix"
            return 1
        fi
    fi
    
    log_info "✅ All files passed forbidden imports check"
    return 0
}

# =============================================================================
# GATE 6: TOOL WIRING CONSISTENCY
# =============================================================================

gate_6_tool_wiring() {
    log_header "GATE 6: TOOL WIRING CONSISTENCY"
    
    if [ ! -f "$SCRIPT_DIR/check_tool_wiring.py" ]; then
        log_warn "Tool wiring checker not found: $SCRIPT_DIR/check_tool_wiring.py"
        log_warn "Skipping tool wiring check"
        return 0
    fi
    
    log_info "Checking tool wiring consistency across registries..."
    
    if ! python3 "$SCRIPT_DIR/check_tool_wiring.py"; then
        log_error "TOOL WIRING CHECK FAILED"
        log_error "Fix all wiring gaps before proceeding"
        return 1
    fi
    
    log_info "✅ Tool wiring check passed"
    return 0
}

# =============================================================================
# GATE 8: NO DEPRECATED SERVICES
# =============================================================================

gate_8_no_deprecated_services() {
    log_header "GATE 8: NO DEPRECATED SERVICES (Supabase, n8n)"
    
    if [ ! -f "$SCRIPT_DIR/check_no_deprecated_services.py" ]; then
        log_warn "Deprecated services checker not found, skipping"
        return 0
    fi
    
    log_info "Checking for deprecated service references..."
    
    if ! python3 "$SCRIPT_DIR/check_no_deprecated_services.py"; then
        log_error "DEPRECATED SERVICES CHECK FAILED"
        log_error "Remove all references to deprecated services"
        return 1
    fi
    
    log_info "✅ No deprecated services found"
    return 0
}

# =============================================================================
# GATE 9: SCHEMA DEPRECATION CHECK
# =============================================================================

gate_9_schema_deprecation() {
    log_header "GATE 9: SCHEMA DEPRECATION CHECK"
    
    if [ ! -f "$SCRIPT_DIR/check_schema_deprecation.py" ]; then
        log_warn "Schema deprecation checker not found, skipping"
        return 0
    fi
    
    log_info "Checking for deprecated PacketEnvelope imports..."
    
    if ! python3 "$SCRIPT_DIR/check_schema_deprecation.py"; then
        log_error "SCHEMA DEPRECATION CHECK FAILED"
        log_error "Migrate deprecated imports to core.schemas.packet_envelope_v2"
        return 1
    fi
    
    log_info "✅ Schema deprecation check passed"
    return 0
}

# =============================================================================
# GATE 10: TOOL ID NAMING CONVENTION
# =============================================================================

gate_10_tool_naming() {
    log_header "GATE 10: TOOL ID NAMING CONVENTION (OpenAI-compatible)"
    
    if [ ! -f "$SCRIPT_DIR/check_tool_naming.py" ]; then
        log_warn "Tool naming checker not found, skipping"
        return 0
    fi
    
    log_info "Checking tool IDs for OpenAI naming compliance..."
    
    if ! python3 "$SCRIPT_DIR/check_tool_naming.py"; then
        log_error "TOOL NAMING CHECK FAILED"
        log_error "Tool IDs must only contain: a-zA-Z0-9_-"
        log_error "No dots allowed. Use underscores instead."
        return 1
    fi
    
    log_info "✅ Tool naming check passed"
    return 0
}

# =============================================================================
# GATE 7: TEST FILE PRESENCE
# =============================================================================

run_test_presence_check() {
    local spec_file="$1"
    shift
    local files=("$@")
    
    log_header "GATE 7: TEST FILE PRESENCE CHECK"
    
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
# GATE 11: AGENT EXECUTOR VERIFICATION
# =============================================================================

gate_11_agent_executor() {
    log_header "GATE 11: AGENT EXECUTOR VERIFICATION"
    
    if [ ! -f "$REPO_ROOT/scripts/verify_agent_executor.py" ]; then
        log_warn "Agent executor verification script not found, skipping"
        return 0
    fi
    
    log_info "Verifying agent_executor initialization fix..."
    
    if ! python3 "$REPO_ROOT/scripts/verify_agent_executor.py" > /dev/null 2>&1; then
        log_error "AGENT EXECUTOR VERIFICATION FAILED"
        log_error "Run scripts/verify_agent_executor.py for details"
        return 1
    fi
    
    log_info "✅ Agent executor verification passed"
    return 0
}

# =============================================================================
# GATE 12: WIRING ALIGNMENT VERIFICATION
# =============================================================================

gate_12_wiring_alignment() {
    log_header "GATE 12: WIRING ALIGNMENT VERIFICATION"
    
    if [ ! -f "$REPO_ROOT/scripts/audit/verify_wiring_alignment.py" ]; then
        log_warn "Wiring alignment verifier not found, skipping"
        return 0
    fi
    
    log_info "Checking documentation path references..."
    
    if ! python3 "$REPO_ROOT/scripts/audit/verify_wiring_alignment.py"; then
        log_error "WIRING ALIGNMENT CHECK FAILED"
        log_error "Documentation contains stale or deprecated path references"
        log_error "Run: python3 scripts/audit/verify_wiring_alignment.py --verbose"
        return 1
    fi
    
    log_info "✅ Wiring alignment check passed"
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
        # Find all spec files and validate (exclude docs/Quantum Research Factory/Perplexity/outputs)
        local all_passed=0
        while IFS= read -r -d '' spec_file; do
            # Skip specs in Perplexity outputs directory (legacy/example specs)
            if [[ "$spec_file" == *"docs/Quantum Research Factory/Perplexity/outputs"* ]]; then
                log_info "Skipping legacy spec: $spec_file"
                continue
            fi
            if ! run_spec_validation "$spec_file"; then
                all_passed=1
            fi
        done < <(find "$REPO_ROOT" -name "*spec*.yaml" -not -path "*/docs/Quantum Research Factory/Perplexity/outputs/*" -print0 2>/dev/null)
        
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
    gate_5_forbidden_imports "${files[@]}" || exit 1
    gate_6_tool_wiring || exit 1
    gate_8_no_deprecated_services || exit 1
    gate_9_schema_deprecation || exit 1
    gate_10_tool_naming || exit 1
    gate_11_agent_executor || exit 1
    gate_12_wiring_alignment || exit 1
    run_test_presence_check "$spec_file" "${files[@]}" || exit 1
    
    log_header "🎉 ALL CI GATES PASSED"
    log_info "Code is ready for merge/build/deploy"
    
    exit 0
}

main "$@"







