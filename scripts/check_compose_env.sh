#!/usr/bin/env bash
# =============================================================================
# L9 Compose Env Validation - NO MISSING VARIABLES TOLERATED
# =============================================================================
# Fails if required env vars are missing or empty. Use before any docker compose.
# Usage: scripts/check_compose_env.sh [path/to/.env]
#        Default: .env (repo root)
# =============================================================================
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
ENV_ARG="${1:-.env}"
# Resolve env file: if relative, from repo root
if [[ "$ENV_ARG" != /* ]]; then
  ENV_FILE="$REPO_ROOT/$ENV_ARG"
else
  ENV_FILE="$ENV_ARG"
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: Env file not found: $ENV_FILE" >&2
  echo "Create from .env.template: cp .env.template $ENV_ARG" >&2
  exit 1
fi

# Required variables - NO MISSING VARIABLES TOLERATED
REQUIRED=(
  POSTGRES_PASSWORD
  NEO4J_PASSWORD
  GRAFANA_PASSWORD
  OPENAI_API_KEY
  L9_API_KEY
)

# Load env file (key=value lines); first = separates key from value
set +u
while IFS= read -r line || [[ -n "$line" ]]; do
  [[ "$line" =~ ^#.*$ ]] && continue
  [[ -z "$line" ]] && continue
  key="${line%%=*}"
  value="${line#*=}"
  [[ -n "$key" ]] && export "$key=$value"
done < "$ENV_FILE"
set -u

MISSING=()
for var in "${REQUIRED[@]}"; do
  val="${!var:-}"
  if [[ -z "${val}" ]] || [[ "$val" == *"CHANGEME"* ]]; then
    MISSING+=("$var")
  fi
done

if [[ ${#MISSING[@]} -gt 0 ]]; then
  echo "ERROR: Required env variables missing or still CHANGEME in $ENV_FILE:" >&2
  printf '  - %s\n' "${MISSING[@]}" >&2
  echo "NO MISSING VARIABLES TOLERATED. Set all required vars in $ENV_FILE and retry." >&2
  exit 1
fi

echo "OK: All required env variables set in $ENV_FILE"
