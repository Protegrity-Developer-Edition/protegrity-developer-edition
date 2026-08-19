#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# run.sh — Start the Protegrity Secure Data Bridge demo
#
# BEFORE FIRST RUN: UPDATE .env WITH YOUR OWN COMPOSIO API KEY
#   COMPOSIO_API_KEY=ck_...      <- from https://dashboard.composio.dev
#                                   (Connect -> Settings -> Sessions & API Key)
# It is the only platform credential this app uses; see .env.example for detail.
# ─────────────────────────────────────────────────────────────────────────────
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load .env if present
if [ -f .env ]; then
  set -o allexport; source .env; set +o allexport
  echo "✓ Loaded .env"
fi

PORT="${PORT:-8900}"

# Warn early rather than letting every Composio call fail with a 401.
case "${COMPOSIO_API_KEY:-}" in
  ""|*your-composio*|*your_api_key_here*)
    echo ""
    echo "  ⚠  COMPOSIO_API_KEY is missing or still a placeholder in .env"
    echo "     Get your own key at https://dashboard.composio.dev"
    echo "     (Connect -> Settings -> Sessions & API Key), then set:"
    echo "     COMPOSIO_API_KEY=ck_..."
    echo "     Without it the agent can only run on sample data."
    ;;
esac

# Use the venv python if available
PYTHON="${PYTHON_BIN:-/home/azure_usr/myenv/bin/python}"
if [ ! -f "$PYTHON" ]; then
  PYTHON="$(which python3)"
fi

echo ""
echo "  ╔═══════════════════════════════════════════════════════════╗"
echo "  ║   Protegrity — Secure Data Bridge                        ║"
echo "  ║   http://localhost:${PORT}                                    ║"
echo "  ╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "  Prerequisites:"
echo "  1. Run 'docker compose up -d' in the protegrity-developer-edition folder"
echo "  2. Set COMPOSIO_API_KEY in .env  (your own key — see .env.example)"
echo "  3. Connect your platforms at https://dashboard.composio.dev -> Connect Apps"
echo ""

exec "$PYTHON" -m uvicorn main:app --host 0.0.0.0 --port "$PORT" --reload
