#!/usr/bin/env bash
#
# L9 Local Development Launcher
# Brings up the FastAPI server with correct env, venv, and LOCAL_DEV behavior.
#

set -e  # stop on any error

# Resolve script directory → repo root
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$REPO_ROOT"

echo "🔧 [L9] Starting local development environment..."
echo "📁 Repo root: $REPO_ROOT"

# --- Check venv existence ---
if [[ ! -d "venv" ]]; then
  echo "❌ ERROR: venv/ not found. Create it first:"
  echo "   python3.12 -m venv venv"
  exit 1
fi

# Activate venv
echo "🐍 Activating virtual environment..."
source venv/bin/activate

# --- Check .env.local existence ---
if [[ ! -f ".env.local" ]]; then
  echo "❌ ERROR: .env.local not found in repo root."
  echo "   Copy your VPS .env to .env.local before running."
  exit 1
fi

# Load environment variables safely
echo "🔑 Loading environment variables from .env.local..."
set -a
source .env.local
set +a

# Force LOCAL_DEV mode so Postgres isn't touched
export LOCAL_DEV=true
echo "🔧 LOCAL_DEV=$LOCAL_DEV"

# Show key env confirmations (not the secrets)
echo "🔍 Environment loaded:"
env | grep -E "EXECUTOR|OPENAI_API_KEY|LOCAL_DEV" | sed 's/=.*/=*** (hidden)/'

# Launch server
echo "🚀 Launching L9 FastAPI server..."
uvicorn api.server_memory:app --reload --host 127.0.0.1 --port 8000
