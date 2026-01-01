#!/bin/bash
# Test runner script for AI Agent Framework
# Runs tests using Docker Compose

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default test category
TEST_CATEGORY="${1:-all}"
TEST_ARGS="${2:-}"

# Print header
print_header() {
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================${NC}"
}

# Print info message
print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Print success message
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

# Print error message
print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Print warning message
print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Show usage
show_usage() {
    cat << EOF
${BLUE}AI Agent Framework - Test Runner${NC}

${GREEN}Usage:${NC}
  ./scripts/run_tests.sh [CATEGORY] [PYTEST_ARGS]

${GREEN}Categories:${NC}
  all              Run all tests (default)
  unit             Run unit tests only
  property         Run property-based tests only
  integration      Run integration tests only
  quick            Run quick tests (unit + essential integration)
  slow             Run slow tests
  llm              Run LLM-related tests
  memory           Run memory-related tests
  audit            Run audit-related tests
  guardrails       Run guardrails tests
  tools            Run tool registry tests

${GREEN}Examples:${NC}
  ./scripts/run_tests.sh all
  ./scripts/run_tests.sh property -v
  ./scripts/run_tests.sh integration -k "agent"
  ./scripts/run_tests.sh llm -m "not requires_docker"
  ./scripts/run_tests.sh quick -v --tb=short

${GREEN}Pytest Arguments:${NC}
  Any pytest argument can be passed as the second parameter:
  -v                 Verbose output
  -s                 Show print statements
  --pdb              Drop into debugger on failure
  -k "pattern"       Run tests matching pattern
  -m "marker"        Run tests with specific marker
  --tb=short         Short traceback format
  --cov=shared       Code coverage report
  --html=report.html HTML report

${GREEN}Notes:${NC}
  - Tests run in Docker containers
  - Database and Redis are automatically set up
  - For Ollama tests, the service will be started automatically
  - Press Ctrl+C to stop tests

EOF
}

# Map test category to pytest arguments
get_pytest_args() {
    case "$1" in
        all)
            echo "tests/ -v"
            ;;
        unit)
            echo "tests/unit/ -v"
            ;;
        property)
            echo "tests/properties/ -v"
            ;;
        integration)
            echo "tests/integration/ -v"
            ;;
        quick)
            echo "tests/ -v -m 'not slow and not requires_docker'"
            ;;
        slow)
            echo "tests/ -v -m 'slow'"
            ;;
        llm)
            echo "tests/integration/ -v -k 'llm or ollama'"
            ;;
        memory)
            echo "tests/integration/ -v -k 'memory'"
            ;;
        audit)
            echo "tests/integration/ tests/properties/ -v -k 'audit'"
            ;;
        guardrails)
            echo "tests/integration/ -v -k 'guardrails'"
            ;;
        tools)
            echo "tests/integration/ -v -k 'tool or mcp'"
            ;;
        *)
            echo "tests/ -v"
            ;;
    esac
}

# Main execution
main() {
    # Show help if requested
    if [[ "$TEST_CATEGORY" == "help" || "$TEST_CATEGORY" == "-h" || "$TEST_CATEGORY" == "--help" ]]; then
        show_usage
        exit 0
    fi

    print_header "AI Agent Framework - Test Execution"
    
    # Get pytest arguments
    PYTEST_CMD=$(get_pytest_args "$TEST_CATEGORY")
    
    # Append additional arguments if provided
    if [[ -n "$TEST_ARGS" ]]; then
        PYTEST_CMD="$PYTEST_CMD $TEST_ARGS"
    fi

    print_info "Test Category: $TEST_CATEGORY"
    print_info "Pytest Command: pytest $PYTEST_CMD"
    echo ""

    # Check if Docker is available
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        exit 1
    fi

    # Check if Docker Compose is available
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed or not in PATH"
        exit 1
    fi

    print_info "Checking Docker daemon..."
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker daemon is not running"
        exit 1
    fi
    print_success "Docker is running"
    echo ""

    # Build images if needed
    print_info "Building Docker images..."
    cd "$PROJECT_ROOT"
    docker-compose -f docker-compose.test.yml build --quiet test-runner
    print_success "Images built"
    echo ""

    # Start services and run tests
    print_info "Starting test environment..."
    docker-compose -f docker-compose.test.yml up \
        --abort-on-container-exit \
        --exit-code-from test-runner \
        test-runner postgres-test redis-test ollama-test

    # Capture exit code
    EXIT_CODE=$?

    print_info "Cleaning up..."
    docker-compose -f docker-compose.test.yml down --remove-orphans

    if [ $EXIT_CODE -eq 0 ]; then
        echo ""
        print_success "All tests passed!"
        exit 0
    else
        echo ""
        print_error "Tests failed with exit code $EXIT_CODE"
        exit $EXIT_CODE
    fi
}

# Run main function
main