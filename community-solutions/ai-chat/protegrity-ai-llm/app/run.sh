#!/usr/bin/env bash
set -euo pipefail

SAMPLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SAMPLE_DIR/.backend.pid"
BACKEND_DIR="$SAMPLE_DIR/backend"
ENV_FILE="$BACKEND_DIR/.env"

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

cleanup() {
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      echo "Stopping backend (PID: $pid)..."
      kill "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
  fi
}

resolve_requirements_file() {
  if [[ -f "$SAMPLE_DIR/requirements.txt" ]]; then
    echo "$SAMPLE_DIR/requirements.txt"
    return 0
  fi

  if [[ -f "$BACKEND_DIR/requirements.txt" ]]; then
    echo "$BACKEND_DIR/requirements.txt"
    return 0
  fi

  return 1
}

port_in_use() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:"$port" -sTCP:LISTEN -n -P >/dev/null 2>&1
    return $?
  fi

  return 1
}

wait_for_protegrity_services() {
  local classification_url="http://localhost:8580/pty/data-discovery/v1.1/classify"
  local guardrail_url="http://localhost:8581/pty/semantic-guardrail/v1.1/conversations/messages/scan"
  local max_attempts=30
  local attempt=1

  echo "Waiting for Protegrity services to become ready..."
  while (( attempt <= max_attempts )); do
    if curl -sS -m 3 -o /dev/null -w "%{http_code}" \
      "$classification_url?score_threshold=0.6" \
      -H 'Content-Type: text/plain' \
      -d 'health check' | grep -q '^200$' \
      && curl -sS -m 3 -o /dev/null -w "%{http_code}" \
      "$guardrail_url" \
      -H 'Content-Type: application/json' \
      -d '{"messages":[{"from":"user","to":"ai","content":"health check","processors":["customer-support"]}]}' | grep -q '^200$'; then
      echo "Protegrity services are ready."
      return 0
    fi

    echo "  Attempt $attempt/$max_attempts: services not ready yet; retrying in 2s..."
    sleep 2
    ((attempt++))
  done

  echo "Error: Protegrity services did not become ready in time."
  return 1
}

trap cleanup EXIT INT TERM

if ! command -v docker >/dev/null 2>&1; then
  echo "Error: docker is not installed or not in PATH."
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Error: docker compose is not available. Install Docker Compose v2."
  exit 1
fi

REPO_ROOT="$(find_repo_root || true)"
if [[ -z "$REPO_ROOT" ]]; then
  echo "Error: could not find repository root with docker-compose.yml."
  exit 1
fi

if [[ ! -f "$BACKEND_DIR/manage.py" ]]; then
  echo "Error: Django entrypoint not found at $BACKEND_DIR/manage.py"
  exit 1
fi

REQUIREMENTS_FILE="$(resolve_requirements_file || true)"
if [[ -z "$REQUIREMENTS_FILE" ]]; then
  echo "Error: could not find requirements file at sample root or backend directory."
  exit 1
fi

echo "Starting Protegrity Developer Edition services from repo root..."
if ! (cd "$REPO_ROOT" && docker compose up -d); then
  echo "Error: failed to start docker compose services from repo root."
  exit 1
fi

if ! wait_for_protegrity_services; then
  exit 1
fi

PYTHON_BIN="python3"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Error: python3 is not installed or not in PATH."
  exit 1
fi

if [[ ! -d "$SAMPLE_DIR/.venv" ]]; then
  echo "Creating virtual environment at $SAMPLE_DIR/.venv ..."
  "$PYTHON_BIN" -m venv "$SAMPLE_DIR/.venv"
fi

echo "Installing backend dependencies..."
"$SAMPLE_DIR/.venv/bin/pip" install -r "$REQUIREMENTS_FILE"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Error: missing backend environment file: $ENV_FILE"
  echo "Create it first by running: cp backend/.env.example backend/.env"
  echo "Then fill required values and rerun ./run.sh"
  exit 1
fi

echo "Validating LLM provider configuration..."
if ! (
  cd "$BACKEND_DIR"
  "$SAMPLE_DIR/.venv/bin/python" manage.py shell <<'PY'
from apps.core.llm_config import validate_llm_provider_configuration

enabled = sorted(validate_llm_provider_configuration())
print("Enabled LLM providers:", ", ".join(enabled))
PY
); then
  echo ""
  echo "LLM provider validation failed."
  echo "Configure at least one provider in backend/.env (copied from backend/.env.example) and rerun ./run.sh"
  exit 1
fi

echo "Running Django migrations..."
(cd "$BACKEND_DIR" && "$SAMPLE_DIR/.venv/bin/python" manage.py migrate)

echo "Seeding LLM providers, tools, and agents..."
(cd "$BACKEND_DIR" && "$SAMPLE_DIR/.venv/bin/python" manage.py seed_llm_data)

echo "Syncing enabled LLM models from backend/.env ..."
(
  cd "$BACKEND_DIR"
  "$SAMPLE_DIR/.venv/bin/python" manage.py shell <<'PY'
import os
from apps.core.llm_config import validate_llm_provider_configuration
from apps.core.models import LLMProvider

enabled = sorted(validate_llm_provider_configuration())

# Optional strict filter for Azure deployment names.
# Example: AZURE_OPENAI_DEPLOYMENTS=gpt-4o,gpt-35-turbo-chat
raw_azure_deployments = os.getenv("AZURE_OPENAI_DEPLOYMENTS", "").strip()
azure_deployments = {
  item.strip()
  for item in raw_azure_deployments.split(",")
  if item.strip()
}

# Start from a clean slate and explicitly enable what's allowed.
LLMProvider.objects.update(is_active=False)

# Enable non-Azure providers fully when configured.
for provider in enabled:
  if provider == "azure":
    continue
  LLMProvider.objects.filter(provider_type=provider).update(is_active=True)

# Enable Azure models.
if "azure" in enabled:
  azure_qs = LLMProvider.objects.filter(provider_type="azure")
  if azure_deployments:
    azure_qs = azure_qs.filter(model_identifier__in=azure_deployments)
  azure_qs.update(is_active=True)

print("Enabled provider types:", ", ".join(enabled))
if "azure" in enabled and azure_deployments:
  print("Enabled Azure deployments:", ", ".join(sorted(azure_deployments)))
print("Active models:", list(LLMProvider.objects.filter(is_active=True).values_list("id", flat=True)))
PY
)

DEMO_USERNAME="${DEMO_USERNAME:-protegrity_demo}"
DEMO_PASSWORD="${DEMO_PASSWORD:-ProtegrityDemo!2026}"
DEMO_ROLE="${DEMO_ROLE:-PROTEGRITY}"

echo "Ensuring demo user account exists ($DEMO_USERNAME)..."
(
  cd "$BACKEND_DIR"
  DEMO_USERNAME="$DEMO_USERNAME" \
  DEMO_PASSWORD="$DEMO_PASSWORD" \
  DEMO_ROLE="$DEMO_ROLE" \
  "$SAMPLE_DIR/.venv/bin/python" manage.py shell <<'PY'
import os
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from apps.core.models import UserProfile

username = os.environ["DEMO_USERNAME"]
password = os.environ["DEMO_PASSWORD"]
role = os.environ.get("DEMO_ROLE", "PROTEGRITY")

if role not in {"PROTEGRITY", "STANDARD"}:
  role = "PROTEGRITY"

User = get_user_model()
user, created = User.objects.get_or_create(
  username=username,
  defaults={
    "email": f"{username}@local.dev",
    "is_active": True,
  },
)

if created:
  user.set_password(password)
  user.save(update_fields=["password"])
else:
  user.set_password(password)
  if not user.is_active:
    user.is_active = True
    user.save(update_fields=["password", "is_active"])
  else:
    user.save(update_fields=["password"])

profile, _ = UserProfile.objects.get_or_create(user=user)
if profile.role != role:
  profile.role = role
  profile.save(update_fields=["role", "updated_at"])

# Keep Django groups aligned with profile role for legacy role checks
protegrity_group, _ = Group.objects.get_or_create(name="Protegrity Users")
standard_group, _ = Group.objects.get_or_create(name="Standard Users")

if role == "PROTEGRITY":
  user.groups.add(protegrity_group)
  user.groups.remove(standard_group)
else:
  user.groups.add(standard_group)
  user.groups.remove(protegrity_group)

print(f"Demo user ready: {username} (role={profile.role})")
PY
)

if port_in_use 8000; then
  echo "Error: port 8000 is already in use. Stop the existing process and rerun ./run.sh"
  exit 1
fi

echo "Starting Django backend on http://127.0.0.1:8000 ..."
(
  cd "$BACKEND_DIR"
  exec "$SAMPLE_DIR/.venv/bin/python" manage.py runserver 127.0.0.1:8000
) &
BACKEND_PID=$!
echo "$BACKEND_PID" > "$PID_FILE"

sleep 2
if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
  echo "Error: Django failed to start on 127.0.0.1:8000"
  exit 1
fi

FRONTEND_DIR="$SAMPLE_DIR/frontend/console"
if [[ ! -d "$FRONTEND_DIR" ]]; then
  echo "Error: frontend directory not found at $FRONTEND_DIR"
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "Error: npm is not installed or not in PATH."
  exit 1
fi

if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  echo "Installing frontend dependencies..."
  (cd "$FRONTEND_DIR" && npm install)
fi

echo ""
echo "✅ Startup complete"
echo "Frontend: http://localhost:5173"
echo "Backend:  http://127.0.0.1:8000"
echo "Dev Edition services are running via docker compose from: $REPO_ROOT/docker-compose.yml"
echo "Login auto-fill: username=$DEMO_USERNAME"
echo ""
echo "Press Ctrl+C to stop frontend and backend (containers continue running; use ./stop.sh to stop containers)."

cd "$FRONTEND_DIR"
export VITE_DEMO_USERNAME="$DEMO_USERNAME"
export VITE_DEMO_PASSWORD="$DEMO_PASSWORD"
npm run dev -- --port 5173 --strictPort
