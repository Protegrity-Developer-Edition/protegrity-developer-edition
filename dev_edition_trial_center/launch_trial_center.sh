#!/usr/bin/env bash

################################################################################
# Trial Center Launcher Script
# 
# Purpose: Launches the Protegrity Developer Edition Trial Center with
#          comprehensive environment validation, service health checks,
#          and graceful error handling. After all prerequisites are
#          validated, it launches the Streamlit UI for interactive use.
#
# Requirements:
#   - Docker Desktop or Docker Engine running
#   - Python 3.11+ with virtual environment
#   - Protegrity Developer Edition services (docker compose)
#   - Streamlit installed in the virtual environment
#
# Environment Variables (optional):
#   - DEV_EDITION_EMAIL: Protegrity account email for reversible protection
#   - DEV_EDITION_PASSWORD: Protegrity account password
#   - DEV_EDITION_API_KEY: API key for protection services
#
# Usage:
#   ./launch_trial_center.sh [--help]
#
# Options:
#   --help      Display this help message
################################################################################

set -euo pipefail  # Exit on error, undefined variable, or pipe failure

# Color codes for enhanced console output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m' # No Color

# Configuration constants
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly VENV_PATH="${PROJECT_ROOT}/.venv"
readonly OUTPUT_DIR="${SCRIPT_DIR}/output"
readonly SAMPLE_PROMPT="${SCRIPT_DIR}/samples/input_test.txt"

# Service endpoints
readonly GUARDRAIL_ENDPOINT="http://localhost:8581"
readonly DISCOVERY_ENDPOINT="http://localhost:8580"

# Exit codes
readonly EXIT_SUCCESS=0
readonly EXIT_DOCKER_ERROR=1
readonly EXIT_VENV_ERROR=2
readonly EXIT_SERVICE_ERROR=3
readonly EXIT_DEPENDENCY_ERROR=4
readonly EXIT_USER_CANCEL=130

################################################################################
# Utility Functions
################################################################################

# Print formatted message with color
print_message() {
    local color="$1"
    local message="$2"
    echo -e "${color}${message}${NC}"
}

# Print error message and exit
error_exit() {
    local message="$1"
    local exit_code="${2:-1}"
    print_message "${RED}" "❌ ERROR: ${message}"
    exit "${exit_code}"
}

# Print success message
print_success() {
    print_message "${GREEN}" "✅ $1"
}

# Print warning message
print_warning() {
    print_message "${YELLOW}" "⚠️  $1"
}

# Print info message
print_info() {
    print_message "${BLUE}" "ℹ️  $1"
}

# Print step header
print_step() {
    print_message "${CYAN}" "▶ $1"
}

# Display help message
show_help() {
    cat << EOF
${GREEN}Protegrity Developer Edition Trial Center Launcher${NC}

${BLUE}DESCRIPTION:${NC}
    Launches the Trial Center pipeline with full environment validation,
    service health checks, and error handling.

${BLUE}USAGE:${NC}
    $0 [OPTIONS]

${BLUE}OPTIONS:${NC}
    --help      Display this help message and exit

${BLUE}EXAMPLES:${NC}
    # Launch Trial Center with prerequisites validation and UI
    $0

${BLUE}ENVIRONMENT VARIABLES:${NC}
    DEV_EDITION_EMAIL       Protegrity account email (optional)
    DEV_EDITION_PASSWORD    Protegrity account password (optional)
    DEV_EDITION_API_KEY     API key for protection services (optional)

    ${YELLOW}Note: Without credentials, the pipeline uses redaction fallback.${NC}

${BLUE}EXIT CODES:${NC}
    0    Success
    1    Docker error
    2    Virtual environment error
    3    Service health check failed
    4    Dependency error
    130  User cancelled

EOF
}

################################################################################
# Validation Functions
################################################################################

# Check if Docker is installed and running
check_docker() {
    print_step "Checking Docker availability..."
    
    if ! command -v docker &> /dev/null; then
        error_exit "Docker is not installed. Please install Docker Desktop." "${EXIT_DOCKER_ERROR}"
    fi
    
    if ! docker info &> /dev/null; then
        error_exit "Docker daemon is not running. Please start Docker Desktop." "${EXIT_DOCKER_ERROR}"
    fi
    
    print_success "Docker is installed and running"
}

# Check if Python is available
check_python() {
    print_step "Checking Python environment..."
    
    if [[ -d "${VENV_PATH}" ]]; then
        print_success "Virtual environment found at ${VENV_PATH}"
    else
        error_exit "Virtual environment not found at ${VENV_PATH}" "${EXIT_VENV_ERROR}"
    fi
}

# Activate virtual environment
activate_venv() {
    print_step "Activating virtual environment..."
    
    # shellcheck disable=SC1091
    if source "${VENV_PATH}/bin/activate"; then
        print_success "Virtual environment activated"
        print_info "Python: $(python --version)"
    else
        error_exit "Failed to activate virtual environment" "${EXIT_VENV_ERROR}"
    fi
}

# Check environment variables and display warnings
check_environment_variables() {
    print_step "Checking environment variables..."
    
    local has_credentials=false
    local missing_vars=()
    
    if [[ -n "${DEV_EDITION_EMAIL:-}" ]]; then
        print_success "DEV_EDITION_EMAIL is set"
        has_credentials=true
    else
        missing_vars+=("DEV_EDITION_EMAIL")
    fi
    
    if [[ -n "${DEV_EDITION_PASSWORD:-}" ]]; then
        print_success "DEV_EDITION_PASSWORD is set"
        has_credentials=true
    else
        missing_vars+=("DEV_EDITION_PASSWORD")
    fi
    
    if [[ -n "${DEV_EDITION_API_KEY:-}" ]]; then
        print_success "DEV_EDITION_API_KEY is set"
        has_credentials=true
    else
        missing_vars+=("DEV_EDITION_API_KEY")
    fi
    
    if [[ "${has_credentials}" == "false" ]] || [[ ${#missing_vars[@]} -gt 0 ]]; then
        echo
        print_warning "═══════════════════════════════════════════════════════════════"
        print_warning "  CREDENTIALS NOT CONFIGURED"
        print_warning "═══════════════════════════════════════════════════════════════"
        print_warning ""
        if [[ ${#missing_vars[@]} -gt 0 ]]; then
            print_warning "Missing environment variables:"
            for var in "${missing_vars[@]}"; do
                print_warning "  - ${var}"
            done
            print_warning ""
        fi
        print_warning "The Trial Center will use REDACTION FALLBACK mode."
        print_warning "Sensitive data will be masked irreversibly."
        print_warning ""
        print_warning "To enable reversible protection, set these variables:"
        print_warning "  export DEV_EDITION_EMAIL='your-email@domain.com'"
        print_warning "  export DEV_EDITION_PASSWORD='your-password'"
        print_warning "  export DEV_EDITION_API_KEY='your-api-key'"
        print_warning "═══════════════════════════════════════════════════════════════"
        echo
    else
        print_success "All credentials configured - reversible protection available"
    fi
}

# Check if Docker services are already running
check_services_running() {
    local guardrail_running=false
    local discovery_running=false
    
    # Check if containers exist and are running
    if docker ps --filter "name=semantic_guardrail" --filter "status=running" --format "{{.Names}}" | grep -q "semantic_guardrail"; then
        guardrail_running=true
    fi
    
    if docker ps --filter "name=classification_service" --filter "status=running" --format "{{.Names}}" | grep -q "classification_service"; then
        discovery_running=true
    fi
    
    if [[ "${guardrail_running}" == "true" ]] && [[ "${discovery_running}" == "true" ]]; then
        return 0  # Services are running
    else
        return 1  # Services are not running
    fi
}

# Start Docker services with retry logic
start_docker_services() {
    local max_attempts=2
    local attempt=1
    
    # First check if services are already running
    if check_services_running; then
        print_success "Docker services are already running"
        return 0
    fi
    
    print_step "Starting Developer Edition services..."
    
    cd "${PROJECT_ROOT}" || error_exit "Failed to change to project root" "${EXIT_DOCKER_ERROR}"
    
    while [[ ${attempt} -le ${max_attempts} ]]; do
        if [[ ${attempt} -gt 1 ]]; then
            print_warning "Retry attempt ${attempt} of ${max_attempts}..."
            sleep 3
        fi
        
        if docker compose up -d 2>&1; then
            print_success "Docker services started successfully"
            return 0
        else
            print_warning "Attempt ${attempt} failed to start Docker services"
            attempt=$((attempt + 1))
        fi
    done
    
    error_exit "Failed to start Docker services after ${max_attempts} attempts" "${EXIT_DOCKER_ERROR}"
}

# Wait for service to be healthy
wait_for_service() {
    local service_name="$1"
    local endpoint="$2"
    local check_path="$3"
    local max_attempts=30
    local attempt=0
    
    print_step "Waiting for ${service_name} to be ready..."
    
    while [[ ${attempt} -lt ${max_attempts} ]]; do
        # Try the specific check path if provided
        if [[ -n "${check_path}" ]]; then
            # Use curl to check if endpoint responds (any HTTP response means it's alive)
            # Capture HTTP status code
            local http_code
            http_code=$(curl -s -o /dev/null -w "%{http_code}" "${endpoint}${check_path}" 2>/dev/null || echo "000")
            
            # Any valid HTTP response (200-599) means service is up
            if [[ "${http_code}" != "000" ]] && [[ "${http_code}" =~ ^[2-5][0-9][0-9]$ ]]; then
                print_success "${service_name} is ready (HTTP ${http_code})"
                return 0
            fi
        else
            # Fallback to simple connectivity check
            if curl -sf "${endpoint}/health" &> /dev/null || curl -sf "${endpoint}" &> /dev/null; then
                print_success "${service_name} is ready"
                return 0
            fi
        fi
        
        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done
    
    echo
    error_exit "${service_name} did not become ready in time" "${EXIT_SERVICE_ERROR}"
}

# Check if services are healthy and ready
are_services_healthy() {
    local http_code_guardrail
    local http_code_discovery
    
    http_code_guardrail=$(curl -s -o /dev/null -w "%{http_code}" "${GUARDRAIL_ENDPOINT}/docs" 2>/dev/null || echo "000")
    http_code_discovery=$(curl -s -o /dev/null -w "%{http_code}" "${DISCOVERY_ENDPOINT}/pty/data-discovery/v1.0/classify" 2>/dev/null || echo "000")
    
    if [[ "${http_code_guardrail}" != "000" ]] && [[ "${http_code_guardrail}" =~ ^[2-5][0-9][0-9]$ ]] && \
       [[ "${http_code_discovery}" != "000" ]] && [[ "${http_code_discovery}" =~ ^[2-5][0-9][0-9]$ ]]; then
        return 0  # Both services are healthy
    else
        return 1  # At least one service is not healthy
    fi
}

# Check service health
check_services() {
    # First do a quick health check to see if we can skip waiting
    if are_services_healthy; then
        print_success "Services are already healthy and ready"
        return 0
    fi
    
    print_step "Checking service health..."
    
    # Check if containers are running
    local guardrail_status
    local discovery_status
    
    guardrail_status=$(docker ps --filter "name=semantic_guardrail" --format "{{.Status}}" 2>/dev/null || echo "Not running")
    discovery_status=$(docker ps --filter "name=classification_service" --format "{{.Status}}" 2>/dev/null || echo "Not running")
    
    print_info "Semantic Guardrail: ${guardrail_status}"
    print_info "Data Discovery: ${discovery_status}"
    
    # Wait for services to be ready (using their specific API paths)
    # Semantic Guardrail has a /docs endpoint
    wait_for_service "Semantic Guardrail" "${GUARDRAIL_ENDPOINT}" "/docs"
    # Data Discovery uses a different path structure - check the classify endpoint
    wait_for_service "Data Discovery" "${DISCOVERY_ENDPOINT}" "/pty/data-discovery/v1.0/classify"
}

# Create output directory
setup_output_directory() {
    print_step "Setting up output directory..."
    
    if mkdir -p "${OUTPUT_DIR}"; then
        print_success "Output directory ready: ${OUTPUT_DIR}"
    else
        error_exit "Failed to create output directory" "${EXIT_DEPENDENCY_ERROR}"
    fi
}

# Check dependencies
check_dependencies() {
    print_step "Checking Python dependencies..."
    
    # Check if streamlit is installed for UI mode
    if python -c "import streamlit" &> /dev/null; then
        print_success "Streamlit is installed"
    else
        print_warning "Streamlit not installed - UI mode unavailable"
        print_info "Install with: pip install streamlit"
    fi
}

################################################################################
# Launch Functions
################################################################################

# Launch CLI pipeline
launch_cli() {
    print_step "Launching Trial Center CLI pipeline..."
    echo
    
    print_info "═══════════════════════════════════════════════════════════════"
    print_info "  RUNNING TRIAL CENTER PIPELINE"
    print_info "═══════════════════════════════════════════════════════════════"
    print_info "Sample prompt: ${SAMPLE_PROMPT}"
    print_info "Output directory: ${OUTPUT_DIR}"
    print_info "═══════════════════════════════════════════════════════════════"
    echo
    
    cd "${PROJECT_ROOT}" || error_exit "Failed to change to project root" "${EXIT_DEPENDENCY_ERROR}"
    
    if python -m dev_edition_trial_center.run_trial_center \
        "${SAMPLE_PROMPT}" \
        --output-dir "${OUTPUT_DIR}" \
        --verbose; then
        
        echo
        print_success "═══════════════════════════════════════════════════════════════"
        print_success "  PIPELINE COMPLETED SUCCESSFULLY"
        print_success "═══════════════════════════════════════════════════════════════"
        print_success "Sanitized prompt: ${OUTPUT_DIR}/input_test_sanitized.txt"
        print_success "Report: ${OUTPUT_DIR}/input_test_report.json"
        print_success "═══════════════════════════════════════════════════════════════"
    else
        error_exit "Pipeline execution failed" "${EXIT_DEPENDENCY_ERROR}"
    fi
}

# Launch Streamlit UI
launch_ui() {
    print_step "Launching Trial Center UI..."
    echo
    
    if ! python -c "import streamlit" &> /dev/null; then
        error_exit "Streamlit is not installed. Run: pip install streamlit" "${EXIT_DEPENDENCY_ERROR}"
    fi
    
    print_info "═══════════════════════════════════════════════════════════════"
    print_info "  STARTING STREAMLIT WEB INTERFACE"
    print_info "═══════════════════════════════════════════════════════════════"
    print_info "The UI will open in your default browser"
    print_info "Press Ctrl+C to stop the server"
    print_info "═══════════════════════════════════════════════════════════════"
    echo
    
    cd "${PROJECT_ROOT}" || error_exit "Failed to change to project root" "${EXIT_DEPENDENCY_ERROR}"
    
    # Launch Streamlit from project root (same as manual launch)
    streamlit run dev_edition_trial_center/app.py
}

################################################################################
# Cleanup and Signal Handling
################################################################################

# Cleanup function
cleanup() {
    local exit_code=$?
    
    if [[ ${exit_code} -eq ${EXIT_USER_CANCEL} ]]; then
        echo
        print_warning "Operation cancelled by user"
    fi
    
    # Deactivate virtual environment if active
    if [[ -n "${VIRTUAL_ENV:-}" ]]; then
        deactivate 2>/dev/null || true
    fi
    
    exit "${exit_code}"
}

# Trap signals for cleanup
trap cleanup EXIT
trap 'exit ${EXIT_USER_CANCEL}' INT TERM

################################################################################
# Main Execution
################################################################################

main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --help|-h)
                show_help
                exit "${EXIT_SUCCESS}"
                ;;
            *)
                error_exit "Unknown option: $1. Use --help for usage information."
                ;;
        esac
    done
    
    # Print banner
    echo
    print_message "${GREEN}" "╔═══════════════════════════════════════════════════════════════╗"
    print_message "${GREEN}" "║                                                               ║"
    print_message "${GREEN}" "║         PROTEGRITY DEVELOPER EDITION TRIAL CENTER            ║"
    print_message "${GREEN}" "║                                                               ║"
    print_message "${GREEN}" "║           Privacy-Preserving GenAI Pipeline                  ║"
    print_message "${GREEN}" "║                                                               ║"
    print_message "${GREEN}" "╚═══════════════════════════════════════════════════════════════╝"
    echo
    
    # Run validation checks
    check_docker
    check_python
    activate_venv
    check_environment_variables
    start_docker_services
    check_services
    setup_output_directory
    check_dependencies
    
    echo
    print_success "All prerequisites validated successfully!"
    echo
    
    # Always launch the Streamlit UI
    launch_ui
}

# Execute main function
main "$@"
