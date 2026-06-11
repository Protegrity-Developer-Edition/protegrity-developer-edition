#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# setup_protegrity.sh — Install Protegrity Developer Edition containers
#                       and the Python SDK if they are missing.
#
# Usage:
#   bash scripts/setup_protegrity.sh          # install everything
#   bash scripts/setup_protegrity.sh --check  # check status only
# ──────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CLONE_BASE="${REPO_DIR}/.protegrity-install"

# Auto-create and activate venv if not already in one
VENV_DIR="${REPO_DIR}/.venv"
if [ -z "${VIRTUAL_ENV:-}" ]; then
    if [ ! -d "$VENV_DIR" ] || [ ! -f "$VENV_DIR/bin/activate" ]; then
        rm -rf "$VENV_DIR"
        echo "Creating virtual environment at ${VENV_DIR} …"
        if ! python3 -m venv "$VENV_DIR" 2>/dev/null; then
            # Auto-install python3-venv if missing
            PYVER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
            echo "python3-venv not found — installing …"
            sudo apt-get update -qq 2>/dev/null
            sudo apt-get install -y "python${PYVER}-venv" 2>/dev/null \
                || sudo apt-get install -y python3-venv 2>/dev/null \
                || {
                    echo -e "\033[0;31m✖\033[0m Failed to install python3-venv. Please install manually:"
                    echo "    sudo apt-get install -y python${PYVER}-venv"
                    exit 1
                }
            rm -rf "$VENV_DIR"
            python3 -m venv "$VENV_DIR"
        fi
    fi
    echo "Activating virtual environment …"
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
fi

# Resolve pip command
if command -v pip &>/dev/null; then
    PIP=pip
elif command -v pip3 &>/dev/null; then
    PIP=pip3
elif python3 -m pip --version &>/dev/null; then
    PIP="python3 -m pip"
else
    echo -e "\033[0;31m✖\033[0m pip is not available even inside the venv."
    exit 1
fi

# Install project requirements if not yet done
if [ -f "${REPO_DIR}/config/requirements.txt" ]; then
    if ! python3 -c "import flask" &>/dev/null; then
        echo "Installing project requirements …"
        $PIP install -r "${REPO_DIR}/config/requirements.txt" --quiet
    fi
fi

EDITION_REPO="https://github.com/Protegrity-Developer-Edition/protegrity-developer-edition.git"
PYTHON_REPO="https://github.com/Protegrity-Developer-Edition/protegrity-developer-python.git"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

info()  { echo -e "${GREEN}✔${NC} $*"; }
warn()  { echo -e "${YELLOW}⚠${NC} $*"; }
error() { echo -e "${RED}✖${NC} $*"; }

# ── Checks ────────────────────────────────────────────────────────────

check_docker() {
    if ! command -v docker &>/dev/null; then
        error "Docker is not installed. Please install Docker first."
        echo "  → https://docs.docker.com/get-docker/"
        return 1
    fi
    if ! docker info &>/dev/null; then
        error "Docker daemon is not running. Please start Docker."
        return 1
    fi
    info "Docker is available"
}

check_docker_compose() {
    if docker compose version &>/dev/null 2>&1; then
        COMPOSE_CMD="docker compose"
    elif command -v docker-compose &>/dev/null; then
        COMPOSE_CMD="docker-compose"
    else
        error "Docker Compose is not installed."
        echo "  → https://docs.docker.com/compose/install/"
        return 1
    fi
    info "Docker Compose is available ($COMPOSE_CMD)"
}

check_containers() {
    local running
    running=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -c 'classification_service\|semantic_guardrail\|pattern_provider\|context_provider' || true)
    if [ "$running" -ge 3 ]; then
        info "Protegrity containers are running ($running services)"
        return 0
    else
        warn "Protegrity containers are NOT running ($running/4 services detected)"
        return 1
    fi
}

check_python_sdk() {
    if python3 -c "import protegrity_developer_python" &>/dev/null; then
        local ver
        ver=$($PIP show protegrity-developer-python 2>/dev/null | grep '^Version:' | awk '{print $2}')
        # Verify the SDK has find_and_unprotect (missing in v0.9.0rc6 from PyPI)
        if python3 -c "import protegrity_developer_python; assert hasattr(protegrity_developer_python, 'find_and_unprotect')" 2>/dev/null; then
            info "protegrity-developer-python SDK is installed (v${ver:-unknown})"
            return 0
        else
            warn "protegrity-developer-python v${ver:-unknown} is incomplete (missing find_and_unprotect) — needs upgrade from source"
            return 1
        fi
    else
        warn "protegrity-developer-python SDK is NOT installed"
        return 1
    fi
}

# ── Install functions ─────────────────────────────────────────────────

install_docker() {
    echo ""
    echo "━━━ Installing Docker & Docker Compose ━━━"

    if ! command -v curl &>/dev/null; then
        sudo apt-get update -qq 2>/dev/null
        sudo apt-get install -y curl 2>/dev/null
    fi

    echo "Installing Docker via get.docker.com …"
    curl -fsSL https://get.docker.com | sudo sh

    # Add current user to docker group so sudo is not needed
    sudo usermod -aG docker "$USER"

    # Activate the new group in current shell (avoids logout/login)
    if command -v newgrp &>/dev/null; then
        echo "Activating docker group …"
        sg docker -c "docker info" &>/dev/null || true
    fi

    # Verify installation
    if docker --version &>/dev/null; then
        info "Docker installed: $(docker --version)"
    else
        error "Docker installation failed"
        return 1
    fi

    if docker compose version &>/dev/null 2>&1; then
        COMPOSE_CMD="docker compose"
        info "Docker Compose installed: $(docker compose version)"
    else
        error "Docker Compose not available after Docker install"
        return 1
    fi
}

install_containers() {
    echo ""
    echo "━━━ Installing Protegrity Developer Edition containers ━━━"
    mkdir -p "$CLONE_BASE"
    local edition_dir="$CLONE_BASE/protegrity-developer-edition"

    if [ -d "$edition_dir/.git" ]; then
        info "Repository already cloned — pulling latest…"
        git -C "$edition_dir" pull --quiet
    else
        echo "Cloning $EDITION_REPO …"
        git clone --quiet "$EDITION_REPO" "$edition_dir"
    fi

    echo "Starting containers with docker compose (this may take a while on first run)…"
    cd "$edition_dir"
    $COMPOSE_CMD up -d
    cd "$REPO_DIR"

    echo ""
    # Wait briefly for containers to start
    echo "Waiting for containers to start…"
    sleep 10
    if check_containers; then
        info "Protegrity containers started successfully"
    else
        warn "Containers may still be starting — check with: docker ps"
    fi
}

install_python_sdk() {
    echo ""
    echo "━━━ Installing Protegrity Python SDK ━━━"
    echo "Installing from PyPI: $PIP install protegrity-developer-python …"

    if $PIP install protegrity-developer-python 2>/dev/null; then
        # Check if we got the full SDK (v1.1.0+) or a limited fallback version
        if python3 -c "import protegrity_developer_python; assert hasattr(protegrity_developer_python, 'find_and_unprotect')" 2>/dev/null; then
            info "protegrity-developer-python installed from PyPI (full SDK)"
            return 0
        else
            warn "PyPI installed a limited SDK version — upgrading from source…"
        fi
    else
        warn "PyPI install failed — building from source…"
    fi

    # Build from source with relaxed Python version requirement
    mkdir -p "$CLONE_BASE"
    local python_dir="$CLONE_BASE/protegrity-developer-python"

    if [ -d "$python_dir/.git" ]; then
        info "Repository already cloned — pulling latest…"
        git -C "$python_dir" pull --quiet
    else
        echo "Cloning $PYTHON_REPO …"
        git clone --quiet "$PYTHON_REPO" "$python_dir"
    fi

    cd "$python_dir"

    $PIP install -r requirements.txt 2>/dev/null || true
    $PIP install . --no-deps --force-reinstall
    cd "$REPO_DIR"

    if python3 -c "import protegrity_developer_python; assert hasattr(protegrity_developer_python, 'find_and_unprotect')" 2>/dev/null; then
        info "Python SDK installed successfully from source (full SDK)"
    elif check_python_sdk; then
        warn "Python SDK installed but find_and_unprotect not available"
    else
        error "Python SDK installation failed"
        return 1
    fi
}

# ── Main ──────────────────────────────────────────────────────────────

main() {
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║   Protegrity Developer Edition — Setup                  ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo ""

    local check_only=false
    if [[ "${1:-}" == "--check" ]]; then
        check_only=true
    fi

    # Status checks
    local containers_ok=true sdk_ok=true docker_ok=true

    check_docker      || docker_ok=false
    check_docker_compose || docker_ok=false
    check_containers  || containers_ok=false
    check_python_sdk  || sdk_ok=false

    echo ""

    if $containers_ok && $sdk_ok; then
        info "Everything is installed and running ✓"
        return 0
    fi

    if $check_only; then
        echo ""
        echo "Run without --check to install missing components."
        return 1
    fi

    # Install missing components
    if ! $containers_ok; then
        if ! $docker_ok; then
            install_docker
            docker_ok=true
        fi
        install_containers
    fi

    if ! $sdk_ok; then
        install_python_sdk
    fi

    echo ""
    echo "━━━ Summary ━━━"
    check_containers || true
    check_python_sdk || true
    echo ""
    info "Setup complete. You can verify with: bash scripts/setup_protegrity.sh --check"
}

main "$@"
