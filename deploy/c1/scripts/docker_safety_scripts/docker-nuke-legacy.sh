#!/usr/bin/env bash
set -euo pipefail
docker ps -a --format '{{.Names}}' | grep '^l9-' | xargs -r docker rm -f
