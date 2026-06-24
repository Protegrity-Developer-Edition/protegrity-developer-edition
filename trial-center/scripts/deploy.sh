#!/usr/bin/env bash
# ==============================================================================
# Protegrity AI Developer Edition Trial Center — Deployment Script
#
# Dockerised one-click deployment for Linux, macOS, and Windows (Git Bash/WSL).
#
# Strategy: Prerequisites are validated UPFRONT as a comparison table before any
# action is taken. The user sees all issues at once, resolves them, and re-runs.
#
# Usage:
#   ./scripts/deploy.sh              # Full deployment (docker compose up)
#   ./scripts/deploy.sh --check      # Prerequisite check only (no action)
#   ./scripts/deploy.sh --clean      # Tear down containers and volumes
#   ./scripts/deploy.sh --logs       # Tail container logs
#   ./scripts/deploy.sh --help       # Show usage
# ==============================================================================

set -euo pipefail

# ─── Configuration ────────────────────────────────────────────────────────────

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
# Not `readonly` — `.env` may legitimately re-export these (and we source `.env`
# inside check_env_file).
STREAMLIT_PORT="${TRIAL_CENTER_PORT:-8502}"
# Backend services are an external prerequisite (see docs/GETTING_STARTED.md).
# These URLs are reachability targets, not ports we will bind.
GUARDRAIL_URL="${SEMANTIC_GUARDRAIL_URL:-http://localhost:8581}"
DISCOVERY_URL="${CLASSIFICATION_SERVICE_URL:-http://localhost:8580}"
readonly MIN_DOCKER_MAJOR=20
readonly MIN_DOCKER_MINOR=10
readonly MIN_COMPOSE_MAJOR=2
readonly MIN_COMPOSE_MINOR=0

# ─── Colors & Formatting ─────────────────────────────────────────────────────

if [[ -t 1 ]] && command -v tput &>/dev/null; then
    RED=$(tput setaf 1)
    GREEN=$(tput setaf 2)
    YELLOW=$(tput setaf 3)
    BLUE=$(tput setaf 4)
    CYAN=$(tput setaf 6)
    BOLD=$(tput bold)
    DIM=$(tput dim)
    NC=$(tput sgr0)
else
    RED="" GREEN="" YELLOW="" BLUE="" CYAN="" BOLD="" DIM="" NC=""
fi

# Status symbols
readonly PASS="${GREEN}✅${NC}"
readonly FAIL="${RED}❌${NC}"
readonly WARN="${YELLOW}⚠️${NC} "

# ─── Logging ──────────────────────────────────────────────────────────────────

log_info()    { echo "${BLUE}[INFO]${NC}    $*"; }
log_success() { echo "${GREEN}[OK]${NC}      $*"; }
log_warn()    { echo "${YELLOW}[WARN]${NC}    $*"; }
log_error()   { echo "${RED}[ERROR]${NC}   $*" >&2; }

die() { log_error "$1"; exit "${2:-1}"; }

# ─── OS Detection ─────────────────────────────────────────────────────────────

detect_os() {
    case "$(uname -s)" in
        Linux*)   OS="linux" ;;
        Darwin*)  OS="macos" ;;
        CYGWIN*|MINGW*|MSYS*) OS="windows" ;;
        *)        OS="unknown" ;;
    esac

    ARCH="$(uname -m)"
    case "${ARCH}" in
        x86_64|amd64) ARCH="x64" ;;
        aarch64|arm64) ARCH="arm64" ;;
    esac
}

# ─── Prerequisite Check Engine ────────────────────────────────────────────────

# Arrays to collect results
declare -a CHECK_NAMES=()
declare -a CHECK_REQUIRED=()
declare -a CHECK_FOUND=()
declare -a CHECK_STATUS=()      # pass, fail, warn
declare -a REMEDIATION=()

add_result() {
    local name="$1" required="$2" found="$3" status="$4" fix="${5:-}"
    CHECK_NAMES+=("${name}")
    CHECK_REQUIRED+=("${required}")
    CHECK_FOUND+=("${found}")
    CHECK_STATUS+=("${status}")
    REMEDIATION+=("${fix}")
}

# ─── Individual Checks ────────────────────────────────────────────────────────

check_docker() {
    if ! command -v docker &>/dev/null; then
        local fix=""
        case "${OS}" in
            macos)   fix="brew install --cask docker  OR  https://docs.docker.com/desktop/install/mac-install/" ;;
            linux)   fix="curl -fsSL https://get.docker.com | sh" ;;
            windows) fix="winget install Docker.DockerDesktop  OR  https://docs.docker.com/desktop/install/windows-install/" ;;
            *)       fix="https://docs.docker.com/get-docker/" ;;
        esac
        add_result "Docker" ">= ${MIN_DOCKER_MAJOR}.${MIN_DOCKER_MINOR}" "not installed" "fail" "${fix}"
        return
    fi

    local ver
    ver="$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "")"

    if [[ -z "${ver}" ]]; then
        local fix="Start Docker Desktop or run: sudo systemctl start docker"
        add_result "Docker" ">= ${MIN_DOCKER_MAJOR}.${MIN_DOCKER_MINOR}" "installed (daemon not running)" "fail" "${fix}"
        return
    fi

    local major minor
    major="$(echo "${ver}" | cut -d. -f1)"
    minor="$(echo "${ver}" | cut -d. -f2)"

    if [[ ${major} -gt ${MIN_DOCKER_MAJOR} ]] || \
       [[ ${major} -eq ${MIN_DOCKER_MAJOR} && ${minor} -ge ${MIN_DOCKER_MINOR} ]]; then
        add_result "Docker" ">= ${MIN_DOCKER_MAJOR}.${MIN_DOCKER_MINOR}" "${ver}" "pass"
    else
        local fix="Update Docker: https://docs.docker.com/engine/install/"
        add_result "Docker" ">= ${MIN_DOCKER_MAJOR}.${MIN_DOCKER_MINOR}" "${ver} (too old)" "fail" "${fix}"
    fi
}

check_docker_compose() {
    local compose_cmd=""
    if docker compose version &>/dev/null 2>&1; then
        compose_cmd="docker compose"
    elif command -v docker-compose &>/dev/null; then
        compose_cmd="docker-compose"
    fi

    if [[ -z "${compose_cmd}" ]]; then
        local fix=""
        case "${OS}" in
            linux) fix="sudo apt-get install docker-compose-plugin  OR  https://docs.docker.com/compose/install/" ;;
            *)     fix="Included with Docker Desktop. Update Docker Desktop." ;;
        esac
        add_result "Docker Compose" ">= ${MIN_COMPOSE_MAJOR}.${MIN_COMPOSE_MINOR}" "not installed" "fail" "${fix}"
        return
    fi

    local ver
    ver="$(${compose_cmd} version --short 2>/dev/null || ${compose_cmd} version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)"
    ver="${ver#v}"  # Strip leading 'v'

    local major minor
    major="$(echo "${ver}" | cut -d. -f1)"
    minor="$(echo "${ver}" | cut -d. -f2)"

    if [[ ${major} -gt ${MIN_COMPOSE_MAJOR} ]] || \
       [[ ${major} -eq ${MIN_COMPOSE_MAJOR} && ${minor} -ge ${MIN_COMPOSE_MINOR} ]]; then
        add_result "Docker Compose" ">= ${MIN_COMPOSE_MAJOR}.${MIN_COMPOSE_MINOR}" "${ver}" "pass"
    else
        add_result "Docker Compose" ">= ${MIN_COMPOSE_MAJOR}.${MIN_COMPOSE_MINOR}" "${ver} (too old)" "fail" \
            "Update: https://docs.docker.com/compose/install/"
    fi
}

check_compose_file() {
    if [[ -f "${PROJECT_ROOT}/docker-compose.yml" ]] || [[ -f "${PROJECT_ROOT}/docker-compose.yaml" ]]; then
        add_result "docker-compose.yml" "present" "found" "pass"
    else
        add_result "docker-compose.yml" "present" "missing" "fail" \
            "File should exist at project root. Check your git clone."
    fi
}

check_port() {
    local port="$1" label="$2"
    local in_use=false
    local pid_info=""

    case "${OS}" in
        macos)
            if lsof -i :"${port}" -sTCP:LISTEN &>/dev/null 2>&1; then
                in_use=true
                pid_info="$(lsof -ti :"${port}" -sTCP:LISTEN 2>/dev/null | head -1)"
                if [[ -n "${pid_info}" ]]; then
                    local proc_name
                    proc_name="$(ps -p "${pid_info}" -o comm= 2>/dev/null || echo "unknown")"
                    pid_info="PID ${pid_info} (${proc_name})"
                fi
            fi
            ;;
        linux)
            if ss -tlnp 2>/dev/null | grep -q ":${port} " || \
               lsof -i :"${port}" -sTCP:LISTEN &>/dev/null 2>&1; then
                in_use=true
                pid_info="$(lsof -ti :"${port}" -sTCP:LISTEN 2>/dev/null | head -1)"
                if [[ -n "${pid_info}" ]]; then
                    local proc_name
                    proc_name="$(ps -p "${pid_info}" -o comm= 2>/dev/null || echo "unknown")"
                    pid_info="PID ${pid_info} (${proc_name})"
                fi
            fi
            ;;
        windows)
            if netstat -an 2>/dev/null | grep -q ":${port}.*LISTEN"; then
                in_use=true
                pid_info="check with: netstat -ano | findstr :${port}"
            fi
            ;;
    esac

    if [[ "${in_use}" == "true" ]]; then
        local detail="in use"
        [[ -n "${pid_info}" ]] && detail="in use by ${pid_info}"
        add_result "Port ${port} (${label})" "available" "${detail}" "fail" \
            "Free the port or set ${label}_PORT env var"
    else
        add_result "Port ${port} (${label})" "available" "available" "pass"
    fi
}

check_env_file() {
    local env_file="${PROJECT_ROOT}/.env"

    if [[ ! -f "${env_file}" ]]; then
        add_result ".env file" "present" "missing" "warn" \
            "cp .env.example .env && edit with your credentials"
        return
    fi

    # Source it to check variables
    local missing=()
    set -a
    # shellcheck disable=SC1090
    source "${env_file}"
    set +a

    [[ -z "${DEV_EDITION_EMAIL:-}" ]] && missing+=("DEV_EDITION_EMAIL")
    [[ -z "${DEV_EDITION_PASSWORD:-}" ]] && missing+=("DEV_EDITION_PASSWORD")
    [[ -z "${DEV_EDITION_API_KEY:-}" ]] && missing+=("DEV_EDITION_API_KEY")

    if [[ ${#missing[@]} -gt 0 ]]; then
        add_result ".env credentials" "all 3 set" "${#missing[@]} missing: ${missing[*]}" "warn" \
            "Edit .env and fill in: ${missing[*]}"
    else
        add_result ".env credentials" "all 3 set" "configured" "pass"
    fi
}

check_disk_space() {
    local required_mb=500  # ~500MB for images
    local available_mb

    case "${OS}" in
        macos|linux)
            available_mb="$(df -m "${PROJECT_ROOT}" | awk 'NR==2 {print $4}')"
            ;;
        *)
            available_mb=99999  # Skip on Windows (unreliable in Git Bash)
            ;;
    esac

    if [[ ${available_mb} -lt ${required_mb} ]]; then
        add_result "Disk space" ">= ${required_mb}MB" "${available_mb}MB" "fail" \
            "Free up disk space. Docker images require ~500MB."
    else
        add_result "Disk space" ">= ${required_mb}MB" "${available_mb}MB" "pass"
    fi
}

# ─── Run All Prerequisite Checks ──────────────────────────────────────────────

run_prerequisite_checks() {
    detect_os

    check_docker
    check_docker_compose
    check_compose_file
    check_port "${STREAMLIT_PORT}" "TRIAL_CENTER"
    check_backend "Semantic Guardrail" "${GUARDRAIL_URL}"
    check_backend "Classification Service" "${DISCOVERY_URL}"
    check_env_file
    check_disk_space
}

# ─── Backend Reachability Check ──────────────────────────────────────────────
# Backends are a prerequisite: they must already be running and reachable.

check_backend() {
    local label="$1" url="$2"
    if ! command -v curl &>/dev/null; then
        add_result "${label}" "reachable" "curl missing — skipped" "warn" \
            "Install curl to enable backend reachability checks."
        return
    fi
    # Any HTTP response (including 404) means the service is up; only network
    # failure / timeout is a failure.
    if curl -sf -o /dev/null --max-time 3 "${url}" 2>/dev/null \
       || curl -s -o /dev/null --max-time 3 -w '%{http_code}' "${url}" 2>/dev/null | grep -qE '^[1-5][0-9][0-9]$'; then
        add_result "${label}" "reachable" "reachable @ ${url}" "pass"
    else
        add_result "${label}" "reachable" "unreachable @ ${url}" "fail" \
            "Start the Protegrity AI Developer Edition backend (see docs/GETTING_STARTED.md → Prerequisites)."
    fi
}

# ─── Display Results Table ────────────────────────────────────────────────────

display_results() {
    local blockers=0
    local warnings=0

    echo ""
    echo "${BOLD}╔══════════════════════════════════════════════════════════════════════════╗${NC}"
    echo "${BOLD}║       Protegrity Trial Center — Prerequisite Check                      ║${NC}"
    echo "${BOLD}╠══════════════════════════════════════════════════════════════════════════╣${NC}"
    printf "${BOLD}║  %-22s %-16s %-22s %s${NC}\n" "Requirement" "Required" "Found" "Status"
    echo "${BOLD}╠══════════════════════════════════════════════════════════════════════════╣${NC}"

    for i in "${!CHECK_NAMES[@]}"; do
        local status_icon
        case "${CHECK_STATUS[$i]}" in
            pass) status_icon="${PASS}" ;;
            fail) status_icon="${FAIL}"; ((blockers++)) ;;
            warn) status_icon="${WARN}"; ((warnings++)) ;;
        esac

        printf "║  %-22s %-16s %-22s %s\n" \
            "${CHECK_NAMES[$i]}" "${CHECK_REQUIRED[$i]}" "${CHECK_FOUND[$i]}" "${status_icon}"
    done

    echo "${BOLD}╠══════════════════════════════════════════════════════════════════════════╣${NC}"

    # Summary line
    if [[ ${blockers} -eq 0 && ${warnings} -eq 0 ]]; then
        echo "║  ${GREEN}${BOLD}All prerequisites met — ready to deploy!${NC}                               ║"
    else
        local summary=""
        [[ ${blockers} -gt 0 ]] && summary="${RED}${blockers} BLOCKER(S)${NC}"
        [[ ${warnings} -gt 0 ]] && {
            [[ -n "${summary}" ]] && summary="${summary}, "
            summary="${summary}${YELLOW}${warnings} WARNING(S)${NC}"
        }
        printf "║  Result: %-60s  ║\n" "${summary}"
    fi
    echo "${BOLD}╚══════════════════════════════════════════════════════════════════════════╝${NC}"

    # Show remediation for failures/warnings
    if [[ ${blockers} -gt 0 || ${warnings} -gt 0 ]]; then
        echo ""
        for i in "${!CHECK_NAMES[@]}"; do
            if [[ "${CHECK_STATUS[$i]}" == "fail" && -n "${REMEDIATION[$i]}" ]]; then
                echo "  ${FAIL} ${BOLD}${CHECK_NAMES[$i]}${NC}"
                echo "     → ${REMEDIATION[$i]}"
                echo ""
            fi
        done
        for i in "${!CHECK_NAMES[@]}"; do
            if [[ "${CHECK_STATUS[$i]}" == "warn" && -n "${REMEDIATION[$i]}" ]]; then
                echo "  ${WARN}${BOLD}${CHECK_NAMES[$i]}${NC}"
                echo "     → ${REMEDIATION[$i]}"
                echo ""
            fi
        done
    fi

    # Return based on blockers (warnings don't block)
    if [[ ${blockers} -gt 0 ]]; then
        echo "  ${RED}${BOLD}Please resolve blocker(s) above and re-run.${NC}"
        echo ""
        return 1
    fi
    return 0
}

# ─── Deployment Actions ───────────────────────────────────────────────────────

deploy() {
    echo ""
    echo "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo "${BOLD}  Deploying Protegrity AI Developer Edition Trial Center${NC}"
    echo "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Build and start containers
    log_info "Building and starting containers..."
    echo ""

    if ! docker compose -f "${PROJECT_ROOT}/docker-compose.yml" up -d --build; then
        die "Docker Compose failed. Check the errors above."
    fi

    echo ""
    log_success "Containers started successfully!"
    echo ""

    # Wait for health
    log_info "Waiting for services to become healthy..."
    local retries=30
    local healthy=false

    for ((i=1; i<=retries; i++)); do
        if curl -sf --max-time 2 "http://localhost:${STREAMLIT_PORT}/_stcore/health" &>/dev/null; then
            healthy=true
            break
        fi
        printf "."
        sleep 2
    done
    echo ""

    if [[ "${healthy}" == "true" ]]; then
        echo ""
        echo "  ${BOLD}╔══════════════════════════════════════════════════════════╗${NC}"
        echo "  ${BOLD}║  ${GREEN}Protegrity AI Developer Edition Trial Center${NC}${BOLD}           ║${NC}"
        echo "  ${BOLD}║                                                          ║${NC}"
        echo "  ${BOLD}║  Trial Center UI: ${GREEN}http://localhost:${STREAMLIT_PORT}${NC}${BOLD}               ║${NC}"
        echo "  ${BOLD}║                                                          ║${NC}"
        echo "  ${BOLD}║  Commands:                                               ║${NC}"
        echo "  ${BOLD}║    Logs:    ${CYAN}./scripts/deploy.sh --logs${NC}${BOLD}                  ║${NC}"
        echo "  ${BOLD}║    Stop:    ${CYAN}./scripts/deploy.sh --clean${NC}${BOLD}                 ║${NC}"
        echo "  ${BOLD}║    Status:  ${CYAN}docker compose ps${NC}${BOLD}                           ║${NC}"
        echo "  ${BOLD}╚══════════════════════════════════════════════════════════╝${NC}"
        echo ""
    else
        log_warn "Trial Center did not become healthy within 60s."
        echo "  Check logs with: ${BOLD}./scripts/deploy.sh --logs${NC}"
        echo ""
    fi

    # Show container status
    docker compose -f "${PROJECT_ROOT}/docker-compose.yml" ps
}

# ─── Clean/Teardown ──────────────────────────────────────────────────────────

do_clean() {
    echo ""
    log_info "Stopping and removing containers..."
    docker compose -f "${PROJECT_ROOT}/docker-compose.yml" down --volumes --remove-orphans 2>/dev/null || true
    log_success "Containers stopped and removed"

    # Optional: remove built images
    read -rp "  Remove built images too? [y/N] " response
    case "${response}" in
        [yY]|[yY][eE][sS])
            docker compose -f "${PROJECT_ROOT}/docker-compose.yml" down --rmi local 2>/dev/null || true
            log_success "Local images removed"
            ;;
    esac

    echo ""
    log_info "Run ${BOLD}./scripts/deploy.sh${NC} to redeploy."
}

# ─── Logs ─────────────────────────────────────────────────────────────────────

do_logs() {
    docker compose -f "${PROJECT_ROOT}/docker-compose.yml" logs -f --tail=100
}

# ─── Usage ────────────────────────────────────────────────────────────────────

show_help() {
    cat <<EOF
${BOLD}Protegrity AI Developer Edition Trial Center — Deployment${NC}

Usage: ./scripts/deploy.sh [OPTION]

Options:
  (none)      Full deployment: prerequisite check → build → launch
  --check     Run prerequisite check only (no action taken)
  --clean     Stop and remove all containers and volumes
  --logs      Tail logs from all containers
  --help      Show this help message

Prerequisites (checked automatically before deployment):
  • Docker >= ${MIN_DOCKER_MAJOR}.${MIN_DOCKER_MINOR}
  • Docker Compose >= ${MIN_COMPOSE_MAJOR}.${MIN_COMPOSE_MINOR}
  • Port ${STREAMLIT_PORT} available
  • Protegrity backends already running and reachable
    (Semantic Guardrail and Classification Service — see docs/GETTING_STARTED.md)
  • .env file with credentials (optional but recommended)

Environment variables:
  TRIAL_CENTER_PORT            UI port (default: 8502)
  SEMANTIC_GUARDRAIL_URL       Backend URL (default: http://host.docker.internal:8581)
  CLASSIFICATION_SERVICE_URL   Backend URL (default: http://host.docker.internal:8580)
  DEV_EDITION_EMAIL            Protegrity account email
  DEV_EDITION_PASSWORD         Protegrity account password
  DEV_EDITION_API_KEY          Protegrity API key

Examples:
  ./scripts/deploy.sh                    # Deploy with default settings
  ./scripts/deploy.sh --check            # Verify prerequisites only
  TRIAL_CENTER_PORT=9000 ./scripts/deploy.sh   # Custom UI port
  ./scripts/deploy.sh --logs             # View container logs
  ./scripts/deploy.sh --clean            # Tear down everything

EOF
}

# ─── Main ─────────────────────────────────────────────────────────────────────

main() {
    cd "${PROJECT_ROOT}"

    case "${1:-}" in
        --help|-h)  show_help; exit 0 ;;
        --clean)    do_clean; exit 0 ;;
        --logs)     do_logs; exit 0 ;;
        --check)
            run_prerequisite_checks
            display_results
            exit $?
            ;;
    esac

    # Full deployment: check first, then deploy
    run_prerequisite_checks

    if ! display_results; then
        exit 1
    fi

    echo ""
    read -rp "  ${BOLD}Proceed with deployment? [Y/n]${NC} " response
    case "${response}" in
        [nN]|[nN][oO]) echo "Aborted."; exit 0 ;;
    esac

    deploy
}

main "$@"
