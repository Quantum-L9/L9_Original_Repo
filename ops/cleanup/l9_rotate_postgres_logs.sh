#!/usr/bin/env bash
# ops/cleanup/l9_rotate_postgres_logs.sh
# Purpose: Rotate and compress Postgres logs to prevent disk exhaustion.
# Safe: only targets L9 Postgres container logs, never touches data volumes.
set -euo pipefail
IFS=$'\n\t'

readonly PG_CONTAINER="l9-postgres"
readonly RETAIN_COUNT="${L9_PG_LOG_RETAIN:-7}"
readonly MAX_AGE_DAYS="${L9_PG_LOG_MAX_AGE:-14}"
readonly DRY_RUN="${1:-}"

log_info()   { echo -e "\033[0;32m[INFO]\033[0m  $(date '+%Y-%m-%d %H:%M:%S') $*"; }
log_action() { echo -e "\033[0;36m[ACTION]\033[0m $(date '+%Y-%m-%d %H:%M:%S') $*"; }
log_dry()    { echo -e "\033[0;35m[DRY-RUN]\033[0m $*"; }

# ── Rotate Docker JSON logs for Postgres container ───────────

rotate_docker_json_log() {
    local docker_root
    docker_root=$(docker info --format '{{.DockerRootDir}}' 2>/dev/null || echo "/var/lib/docker")

    local container_id
    container_id=$(docker inspect --format='{{.Id}}' "${PG_CONTAINER}" 2>/dev/null || echo "")

    if [[ -z "$container_id" ]]; then
        log_info "Postgres container not found, skipping Docker log rotation."
        return 0
    fi

    local json_log="${docker_root}/containers/${container_id}/${container_id}-json.log"

    if [[ ! -f "$json_log" ]]; then
        log_info "No Docker JSON log found at: ${json_log}"
        return 0
    fi

    local log_size
    log_size=$(stat -c%s "$json_log" 2>/dev/null || echo 0)
    local log_size_mb=$(( log_size / 1048576 ))

    log_info "Postgres Docker log: ${json_log} (${log_size_mb} MB)"

    if (( log_size_mb > 50 )); then
        if [[ "$DRY_RUN" == "--dry-run" ]]; then
            log_dry "Would truncate ${json_log} (${log_size_mb} MB)"
        else
            log_action "Truncating Postgres Docker log (${log_size_mb} MB)..."
            : > "$json_log"
            log_info "Truncated. Freed ~${log_size_mb} MB."
        fi
    else
        log_info "Log size (${log_size_mb} MB) below 50 MB threshold, skipping."
    fi
}

# ── Rotate Postgres internal logs (inside container) ─────────

rotate_pg_internal_logs() {
    local pg_state
    pg_state=$(docker inspect --format='{{.State.Status}}' "${PG_CONTAINER}" 2>/dev/null || echo "not_found")

    if [[ "$pg_state" != "running" ]]; then
        log_info "Postgres container not running (state=${pg_state}), skipping internal log rotation."
        return 0
    fi

    local pg_log_dir="/var/lib/postgresql/data/log"
    local has_logs
    has_logs=$(docker exec "${PG_CONTAINER}" sh -c "test -d ${pg_log_dir} && ls ${pg_log_dir}/*.log 2>/dev/null | wc -l" 2>/dev/null || echo "0")

    if (( has_logs == 0 )); then
        log_info "No Postgres internal logs found at ${pg_log_dir} inside container."
        return 0
    fi

    log_info "Found ${has_logs} Postgres log files inside container."

    if [[ "$DRY_RUN" == "--dry-run" ]]; then
        log_dry "Would compress and rotate logs in ${pg_log_dir} (retain=${RETAIN_COUNT}, max_age=${MAX_AGE_DAYS}d)"
        docker exec "${PG_CONTAINER}" sh -c "du -sh ${pg_log_dir}" 2>/dev/null || true
    else
        log_action "Compressing logs older than ${MAX_AGE_DAYS} days..."
        docker exec "${PG_CONTAINER}" sh -c "
            find ${pg_log_dir} -name '*.log' -mtime +${MAX_AGE_DAYS} -exec gzip -f {} \; 2>/dev/null
        " || true

        log_action "Removing compressed logs, keeping last ${RETAIN_COUNT}..."
        docker exec "${PG_CONTAINER}" sh -c "
            ls -1t ${pg_log_dir}/*.log.gz 2>/dev/null | tail -n +$((RETAIN_COUNT + 1)) | xargs rm -f 2>/dev/null
        " || true

        log_info "Postgres internal log rotation complete."
        docker exec "${PG_CONTAINER}" sh -c "du -sh ${pg_log_dir}" 2>/dev/null || true
    fi
}

# ── Vacuum Postgres WAL if oversized ─────────────────────────

check_wal_size() {
    local pg_state
    pg_state=$(docker inspect --format='{{.State.Status}}' "${PG_CONTAINER}" 2>/dev/null || echo "not_found")

    if [[ "$pg_state" != "running" ]]; then
        return 0
    fi

    local wal_size_bytes
    wal_size_bytes=$(docker exec "${PG_CONTAINER}" sh -c "du -sb /var/lib/postgresql/data/pg_wal 2>/dev/null | awk '{print \$1}'" 2>/dev/null || echo "0")
    local wal_size_mb=$(( wal_size_bytes / 1048576 ))

    log_info "Postgres WAL size: ${wal_size_mb} MB"

    if (( wal_size_mb > 2048 )); then
        log_info "WAL is large (${wal_size_mb} MB). Running checkpoint to reclaim..."
        if [[ "$DRY_RUN" == "--dry-run" ]]; then
            log_dry "Would run: CHECKPOINT inside Postgres"
        else
            docker exec "${PG_CONTAINER}" psql -U postgres -c "CHECKPOINT;" 2>/dev/null || true
            log_info "Checkpoint issued. WAL should shrink on next cycle."
        fi
    fi
}

# ── Main ─────────────────────────────────────────────────────

main() {
    echo ""
    echo "  L9 POSTGRES LOG ROTATION"
    echo "  Mode: $([[ "$DRY_RUN" == "--dry-run" ]] && echo 'DRY-RUN' || echo 'LIVE')"
    echo ""

    rotate_docker_json_log
    rotate_pg_internal_logs
    check_wal_size

    log_info "Postgres log rotation complete."
}

main
