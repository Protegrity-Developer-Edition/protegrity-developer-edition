#!/usr/bin/env bash
set -euo pipefail

SAMPLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SAMPLE_DIR/.backend.pid"

find_repo_root() {
  if command -v git >/dev/null 2>&1; then
    local git_root
    git_root="$(git -C "$SAMPLE_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
    if [[ -n "$git_root" && -f "$git_root/docker-compose.yml" ]]; then
      echo "$git_root"
      return 0
    fi
  fi

  local dir="$SAMPLE_DIR"
  while [[ "$dir" != "/" ]]; do
    if [[ -f "$dir/docker-compose.yml" ]]; then
      echo "$dir"
      return 0
    fi
    dir="$(dirname "$dir")"
  done

  return 1
}

if [[ -f "$PID_FILE" ]]; then
  PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
    echo "Stopping backend process (PID: $PID)..."
    kill "$PID" 2>/dev/null || true
    wait "$PID" 2>/dev/null || true
  fi
  rm -f "$PID_FILE"
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker not found; backend PID cleanup complete."
  exit 0
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "docker compose not available; backend PID cleanup complete."
  exit 0
fi

REPO_ROOT="$(find_repo_root || true)"
if [[ -z "$REPO_ROOT" ]]; then
  echo "Could not locate repository root with docker-compose.yml."
  exit 1
fi

echo "Stopping Dev Edition services from repo root..."
(cd "$REPO_ROOT" && docker compose down --remove-orphans)
echo "Done. Stopped docker compose services and cleaned local backend PID state."
