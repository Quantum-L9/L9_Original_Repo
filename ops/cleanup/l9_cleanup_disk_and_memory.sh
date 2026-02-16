#!/usr/bin/env bash
# ops/cleanup/l9_cleanup_disk_and_memory.sh
# Purpose: Free disk space on C1/VPS and restore L9 memory substrate health.
# Safe: never deletes DB volumes, requires explicit confirmation, supports --dry-run.
# Aligned with L9 container naming: l9-postgres, l9-l9-api-1, l9-l9-mcp-memory-1, etc.
set -euo pipefail
IFS=$'\n\t'

# ── Configuration ────────────────────────────────────────────
readonly SCRIPT_NAME="$(basename "$0")"
readonly L9_ROOT="${L9_ROOT:-/opt/l9}"
readonly LOG_RETAIN_COUNT="${L9_LOG_RETAIN:-5}"
readonly LOG_MAX_AGE_DAYS="${L9_LOG_MAX_AGE_DAYS:-7}"
readonly DOCKER_COMPOSE_FILE="${L9_ROOT}/docker-compose.yml"

# Container names (match actual C1 deployment from MRI)
readonly API_CONTAINER="l9-l9-api-1"
readonly MCP_CONTAINER="l9-l9-mcp-memory-1"
readonly PG_CONTAINER="l9-postgres"
readonly NEO4J_CONTAINER="l9-neo4j"

# Paths safe to clean (L9-owned only)
readonly -a SAFE_CLEAN_DIRS=(
    "${L9_ROOT}/logs"
    "${L9_ROOT}/tmp"
    "${L9_ROOT}/cache"
    "/tmp/l9-api-last400.log"
    "/tmp/l9-*"
)

# Protected paths (NEVER touch)
readonly -a PROTECTED_PATTERNS=(
    "postgres_data"
    "neo4j_data"
    "redis_data"
    "grafana_data"
    "prometheus_data"
)

# ── Globals ──────────────────────────────────────────────────
DRY_RUN=false
CONFIRMED=false
TOTAL_FREED=0

# ── Functions ────────────────────────────────────────────────

usage() {
    cat <<EOF
Usage: ${SCRIPT_NAME} [OPTIONS]

Free disk space on C1 and restore L9 memory substrate health.

Options:
  --dry-run       Show what would be cleaned without deleting anything
  --yes           Skip interactive confirmation (for automation)
  --help          Show this help message

Environment:
  L9_ROOT              L9 install directory        (default: /opt/l9)
  L9_LOG_RETAIN        Number of log files to keep  (default: 5)
  L9_LOG_MAX_AGE_DAYS  Delete logs older than N days (default: 7)
  L9_ALLOW_CLEANUP     Set to 1 to allow on non-C1 hosts

Examples:
  ${SCRIPT_NAME} --dry-run          # Preview cleanup
  ${SCRIPT_NAME} --yes              # Execute without prompts
  ${SCRIPT_NAME}                    # Interactive mode
EOF
    exit 0
}

log_info()    { echo -e "\033[0;32m[INFO]\033[0m  $(date '+%Y-%m-%d %H:%M:%S') $*"; }
log_warn()    { echo -e "\033[0;33m[WARN]\033[0m  $(date '+%Y-%m-%d %H:%M:%S') $*"; }
log_error()   { echo -e "\033[0;31m[ERROR]\033[0m $(date '+%Y-%m-%d %H:%M:%S') $*"; }
log_action()  { echo -e "\033[0;36m[ACTION]\033[0m $(date '+%Y-%m-%d %H:%M:%S') $*"; }
log_dry()     { echo -e "\033[0;35m[DRY-RUN]\033[0m $*"; }

hr() { echo "────────────────────────────────────────────────────────────────"; }

bytes_to_human() {
    local bytes=$1
    if (( bytes >= 1073741824 )); then
        echo "$(awk "BEGIN {printf \"%.2f GB\", ${bytes}/1073741824}")"
    elif (( bytes >= 1048576 )); then
        echo "$(awk "BEGIN {printf \"%.2f MB\", ${bytes}/1048576}")"
    elif (( bytes >= 1024 )); then
        echo "$(awk "BEGIN {printf \"%.2f KB\", ${bytes}/1024}")"
    else
        echo "${bytes} B"
    fi
}

is_protected() {
    local path="$1"
    for pattern in "${PROTECTED_PATTERNS[@]}"; do
        if [[ "$path" == *"$pattern"* ]]; then
            return 0
        fi
    done
    return 1
}

safe_delete() {
    local target="$1"
    local desc="${2:-file}"

    if is_protected "$target"; then
        log_warn "SKIPPED protected path: ${target}"
        return 0
    fi

    if [[ ! -e "$target" ]] && [[ ! -d "$target" ]]; then
        return 0
    fi

    local size=0
    if [[ -f "$target" ]]; then
        size=$(stat -c%s "$target" 2>/dev/null || echo 0)
    elif [[ -d "$target" ]]; then
        size=$(du -sb "$target" 2>/dev/null | awk '{print $1}' || echo 0)
    fi

    if $DRY_RUN; then
        log_dry "Would delete ${desc}: ${target} ($(bytes_to_human "$size"))"
    else
        log_action "Deleting ${desc}: ${target} ($(bytes_to_human "$size"))"
        rm -rf "$target"
    fi
    TOTAL_FREED=$((TOTAL_FREED + size))
}

# ── Safety Gate ──────────────────────────────────────────────

safety_gate() {
    if [[ "${L9_ALLOW_CLEANUP:-0}" == "1" ]]; then
        log_info "L9_ALLOW_CLEANUP=1 set, proceeding."
        return 0
    fi

    if [[ -d "${L9_ROOT}" ]]; then
        log_info "L9_ROOT=${L9_ROOT} exists, proceeding."
        return 0
    fi

    log_error "L9_ROOT=${L9_ROOT} not found and L9_ALLOW_CLEANUP != 1. Aborting."
    exit 1
}

# ── Phase: Diagnostics ──────────────────────────────────────

phase_diagnostics() {
    hr
    log_info "PHASE: DIAGNOSTICS"
    hr

    log_info "Filesystem usage:"
    df -h / /var/lib/docker "${L9_ROOT}" 2>/dev/null | sort -u || df -h /
    echo ""

    log_info "Docker disk usage:"
    docker system df 2>/dev/null || log_warn "docker system df failed"
    echo ""

    log_info "L9 container states:"
    docker ps -a --filter "name=l9-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || log_warn "docker ps failed"
    echo ""

    local pg_state
    pg_state=$(docker inspect --format='{{.State.Status}}' "${PG_CONTAINER}" 2>/dev/null || echo "not_found")
    log_info "Postgres container state: ${pg_state}"

    if [[ "$pg_state" == "restarting" ]]; then
        log_warn "Postgres is crash-looping. Disk pressure is the likely cause."
    fi
}

# ── Phase: Clean Docker Artifacts ────────────────────────────

phase_clean_docker() {
    hr
    log_info "PHASE: DOCKER CLEANUP (dangling images, stopped containers, build cache)"
    hr

    if $DRY_RUN; then
        log_dry "Would run: docker system prune -f (no --volumes, no -a)"
        log_dry "Would run: docker builder prune -f --keep-storage=1GB"

        local dangling_size
        dangling_size=$(docker system df --format '{{.Reclaimable}}' 2>/dev/null | head -1 || echo "unknown")
        log_dry "Estimated reclaimable from dangling: ${dangling_size}"
    else
        log_action "Pruning dangling images and stopped containers..."
        docker system prune -f 2>&1 | tail -1 || true

        log_action "Pruning build cache (keeping 1GB)..."
        docker builder prune -f --keep-storage=1073741824 2>&1 | tail -1 || true
    fi
}

# ── Phase: Clean L9 Logs and Temp Files ──────────────────────

phase_clean_logs() {
    hr
    log_info "PHASE: L9 LOG & TEMP CLEANUP"
    hr

    for dir_pattern in "${SAFE_CLEAN_DIRS[@]}"; do
        for target in $dir_pattern; do
            if [[ -d "$target" ]]; then
                log_info "Scanning: ${target}"

                # Delete log files older than threshold
                while IFS= read -r -d '' logfile; do
                    safe_delete "$logfile" "old log"
                done < <(find "$target" -type f \( -name "*.log" -o -name "*.log.*" -o -name "*.log.gz" \) -mtime +${LOG_MAX_AGE_DAYS} -print0 2>/dev/null)

                # For remaining logs, keep only the N most recent
                local log_files
                log_files=$(find "$target" -maxdepth 2 -type f \( -name "*.log" -o -name "*.log.*" \) 2>/dev/null | sort -t/ -k+2 | head -n -${LOG_RETAIN_COUNT} 2>/dev/null || true)
                for lf in $log_files; do
                    safe_delete "$lf" "excess log (retain=${LOG_RETAIN_COUNT})"
                done

                # Clean .tmp, .cache, __pycache__ under L9-owned dirs only
                while IFS= read -r -d '' tmpfile; do
                    safe_delete "$tmpfile" "temp/cache file"
                done < <(find "$target" -type f \( -name "*.tmp" -o -name "*.pyc" -o -name "*.pyo" \) -print0 2>/dev/null)

                while IFS= read -r -d '' cachedir; do
                    safe_delete "$cachedir" "__pycache__ dir"
                done < <(find "$target" -type d -name "__pycache__" -print0 2>/dev/null)

            elif [[ -f "$target" ]]; then
                safe_delete "$target" "temp file"
            fi
        done
    done

    # Clean container logs (JSON log files managed by Docker daemon)
    log_info "Scanning Docker container log files..."
    local docker_root
    docker_root=$(docker info --format '{{.DockerRootDir}}' 2>/dev/null || echo "/var/lib/docker")

    if [[ -d "${docker_root}/containers" ]]; then
        while IFS= read -r -d '' json_log; do
            local log_size
            log_size=$(stat -c%s "$json_log" 2>/dev/null || echo 0)
            if (( log_size > 104857600 )); then  # > 100MB
                if $DRY_RUN; then
                    log_dry "Would truncate container log: ${json_log} ($(bytes_to_human "$log_size"))"
                else
                    log_action "Truncating container log: ${json_log} ($(bytes_to_human "$log_size"))"
                    : > "$json_log"
                fi
                TOTAL_FREED=$((TOTAL_FREED + log_size))
            fi
        done < <(find "${docker_root}/containers" -name "*-json.log" -print0 2>/dev/null)
    fi
}

# ── Phase: Clean Old Docker Images ───────────────────────────

phase_clean_old_images() {
    hr
    log_info "PHASE: OLD L9 IMAGE CLEANUP"
    hr

    # Remove old L9 images that are NOT currently in use
    local current_images
    current_images=$(docker ps --format '{{.Image}}' 2>/dev/null | sort -u)

    while IFS= read -r image_line; do
        local repo tag image_id size
        repo=$(echo "$image_line" | awk '{print $1}')
        tag=$(echo "$image_line" | awk '{print $2}')
        image_id=$(echo "$image_line" | awk '{print $3}')
        size=$(echo "$image_line" | awk '{print $NF}')

        if [[ "$repo" == *"cryptoxdog/l9"* ]] || [[ "$repo" == *"l9-"* ]]; then
            local full="${repo}:${tag}"
            if echo "$current_images" | grep -qF "$full"; then
                log_info "KEEP (in use): ${full} [${size}]"
            else
                if $DRY_RUN; then
                    log_dry "Would remove unused L9 image: ${full} [${size}]"
                else
                    log_action "Removing unused L9 image: ${full} [${size}]"
                    docker rmi "$image_id" 2>/dev/null || log_warn "Failed to remove ${full}"
                fi
            fi
        fi
    done < <(docker images --format "{{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}" 2>/dev/null)
}

# ── Phase: Restart Substrates ────────────────────────────────

phase_restart_substrates() {
    hr
    log_info "PHASE: SUBSTRATE RESTART"
    hr

    if $DRY_RUN; then
        log_dry "Would restart: ${PG_CONTAINER}"
        log_dry "Would wait for Postgres healthy, then restart: ${API_CONTAINER}"
        return 0
    fi

    # Restart Postgres
    local pg_state
    pg_state=$(docker inspect --format='{{.State.Status}}' "${PG_CONTAINER}" 2>/dev/null || echo "not_found")

    if [[ "$pg_state" == "restarting" ]] || [[ "$pg_state" == "exited" ]]; then
        log_action "Stopping crash-looping Postgres..."
        docker stop "${PG_CONTAINER}" 2>/dev/null || true
        sleep 2
        log_action "Starting Postgres..."
        docker start "${PG_CONTAINER}" 2>/dev/null || true
    else
        log_action "Restarting Postgres..."
        docker restart "${PG_CONTAINER}" 2>/dev/null || true
    fi

    # Wait for Postgres to accept connections
    log_info "Waiting for Postgres to become ready (max 60s)..."
    local retries=0
    while (( retries < 12 )); do
        if docker exec "${PG_CONTAINER}" pg_isready -U postgres -q 2>/dev/null; then
            log_info "Postgres is ready."
            break
        fi
        retries=$((retries + 1))
        sleep 5
    done

    if (( retries >= 12 )); then
        log_error "Postgres did not become ready within 60s."
        log_error "Run: docker logs --tail 50 ${PG_CONTAINER}"
        log_error "Check for WAL corruption or shared memory issues."
        return 1
    fi

    # Check Neo4j health
    local neo4j_state
    neo4j_state=$(docker inspect --format='{{.State.Health.Status}}' "${NEO4J_CONTAINER}" 2>/dev/null || echo "unknown")
    if [[ "$neo4j_state" != "healthy" ]]; then
        log_action "Restarting Neo4j (was: ${neo4j_state})..."
        docker restart "${NEO4J_CONTAINER}" 2>/dev/null || true
        sleep 5
    fi

    # Restart API container
    log_action "Restarting L9 API container..."
    docker restart "${API_CONTAINER}" 2>/dev/null || true

    # Wait for API health
    log_info "Waiting for API health (max 90s)..."
    retries=0
    while (( retries < 18 )); do
        local http_code
        http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://127.0.0.1:8000/health" 2>/dev/null || echo "000")
        if [[ "$http_code" == "200" ]]; then
            log_info "L9 API is healthy (HTTP 200)."
            break
        fi
        retries=$((retries + 1))
        sleep 5
    done

    if (( retries >= 18 )); then
        log_warn "API did not return 200 within 90s. Check: docker logs --tail 100 ${API_CONTAINER}"
    fi

    # Restart MCP memory
    log_action "Restarting MCP memory container..."
    docker restart "${MCP_CONTAINER}" 2>/dev/null || true
    sleep 5
}

# ── Phase: Post-Clean Verification ───────────────────────────

phase_verify() {
    hr
    log_info "PHASE: POST-CLEANUP VERIFICATION"
    hr

    log_info "Filesystem usage after cleanup:"
    df -h / 2>/dev/null
    echo ""

    log_info "Container states:"
    docker ps -a --filter "name=l9-" --format "table {{.Names}}\t{{.Status}}" 2>/dev/null
    echo ""

    log_info "Total space freed/reclaimable: $(bytes_to_human ${TOTAL_FREED})"

    if ! $DRY_RUN; then
        local pg_ok=false api_ok=false
        if docker exec "${PG_CONTAINER}" pg_isready -U postgres -q 2>/dev/null; then
            pg_ok=true
        fi
        local http_code
        http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://127.0.0.1:8000/health" 2>/dev/null || echo "000")
        if [[ "$http_code" == "200" ]]; then
            api_ok=true
        fi

        hr
        echo ""
        echo "  SUBSTRATE STATUS"
        echo "  ├── Postgres:    $(${pg_ok} && echo '✅ ready' || echo '❌ not ready')"
        echo "  ├── API:         $(${api_ok} && echo '✅ healthy' || echo '❌ unhealthy')"
        echo "  └── Disk:        $(df -h / | tail -1 | awk '{print $5, "used", $4, "available"}')"
        echo ""

        if ! $pg_ok; then
            log_error "Postgres still unhealthy. Next steps:"
            log_error "  1. docker logs --tail 50 ${PG_CONTAINER}"
            log_error "  2. Check for WAL corruption: docker exec ${PG_CONTAINER} pg_controldata /var/lib/postgresql/data"
            log_error "  3. If data is corrupt, restore from backup."
        fi
        if ! $api_ok; then
            log_error "API still unhealthy. Next steps:"
            log_error "  1. docker logs --tail 100 ${API_CONTAINER}"
            log_error "  2. If Postgres is up but API fails, try: L9_MINIMAL_MODE=true"
        fi
    fi
}

# ── Main ─────────────────────────────────────────────────────

main() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --dry-run) DRY_RUN=true; shift ;;
            --yes)     CONFIRMED=true; shift ;;
            --help)    usage ;;
            *)         log_error "Unknown option: $1"; usage ;;
        esac
    done

    hr
    echo ""
    echo "  L9 DISK & MEMORY CLEANUP"
    echo "  Mode: $($DRY_RUN && echo 'DRY-RUN (no changes)' || echo 'LIVE')"
    echo "  L9_ROOT: ${L9_ROOT}"
    echo ""
    hr

    safety_gate
    phase_diagnostics

    if ! $DRY_RUN && ! $CONFIRMED; then
        echo ""
        read -rp "Proceed with cleanup? [y/N] " answer
        if [[ "${answer,,}" != "y" ]]; then
            log_info "Aborted by user."
            exit 0
        fi
    fi

    phase_clean_docker
    phase_clean_logs
    phase_clean_old_images
    phase_restart_substrates
    phase_verify

    hr
    log_info "Cleanup complete. Total freed/reclaimable: $(bytes_to_human ${TOTAL_FREED})"
    hr
}

main "$@"
