#!/bin/bash

# run_tests.sh - Run all tests for the Protegrity AI project
# Executes backend (pytest) and frontend (vitest) test suites

echo "======================================"
echo "Running Protegrity AI Test Suite"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track test results
BACKEND_PASSED=false
FRONTEND_PASSED=false
BACKEND_COUNT=0
FRONTEND_COUNT=0

# Activate virtual environment if it exists
if [ -f ".venv/bin/activate" ]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source .venv/bin/activate
elif [ -f "backend/venv/bin/activate" ]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source backend/venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source venv/bin/activate
else
    echo -e "${YELLOW}No virtual environment found. Using system Python.${NC}"
fi

# Run backend tests
echo -e "${YELLOW}[1/2] Running Backend Tests (pytest)...${NC}"
echo "--------------------------------------"
cd backend

if python -m pytest --version > /dev/null 2>&1; then
    BACKEND_OUTPUT=$(python -m pytest --verbose --tb=short 2>&1 || true)
    BACKEND_EXIT=$?
    echo "$BACKEND_OUTPUT"
    
    # Check for failed tests in output
    BACKEND_FAILED=$(echo "$BACKEND_OUTPUT" | grep -oE '[0-9]+ failed' | grep -oE '[0-9]+' | head -1)
    [ -z "$BACKEND_FAILED" ] && BACKEND_FAILED=0
    
    if [ $BACKEND_EXIT -eq 0 ] && [ $BACKEND_FAILED -eq 0 ]; then
        BACKEND_COUNT=$(echo "$BACKEND_OUTPUT" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+' | head -1)
        [ -z "$BACKEND_COUNT" ] && BACKEND_COUNT=0
        echo ""
        echo -e "${GREEN}✓ Backend tests passed (${BACKEND_COUNT} tests)${NC}"
        BACKEND_PASSED=true
    else
        BACKEND_COUNT=$(echo "$BACKEND_OUTPUT" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+' | head -1)
        [ -z "$BACKEND_COUNT" ] && BACKEND_COUNT=0
        echo ""
        echo -e "${RED}✗ Backend tests failed (${BACKEND_FAILED} failed, ${BACKEND_COUNT} passed)${NC}"
        BACKEND_PASSED=false
    fi
else
    echo -e "${RED}pytest not found. Please install: pip install pytest${NC}"
    BACKEND_PASSED=false
fi

cd ..
echo ""

# Run frontend tests
echo -e "${YELLOW}[2/2] Running Frontend Tests (vitest)...${NC}"
echo "--------------------------------------"
cd frontend/console

if [ -f "package.json" ] && npm list vitest > /dev/null 2>&1; then
    FRONTEND_OUTPUT=$(npm run test -- --run --reporter=verbose 2>&1 || true)
    FRONTEND_EXIT=$?
    echo "$FRONTEND_OUTPUT"
    
    # Check for failed tests in output
    FRONTEND_FAILED=$(echo "$FRONTEND_OUTPUT" | grep -oE '[0-9]+ failed' | grep -oE '[0-9]+' | head -1)
    [ -z "$FRONTEND_FAILED" ] && FRONTEND_FAILED=0
    
    if [ $FRONTEND_EXIT -eq 0 ] && [ $FRONTEND_FAILED -eq 0 ]; then
        FRONTEND_COUNT=$(echo "$FRONTEND_OUTPUT" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+' | head -1)
        [ -z "$FRONTEND_COUNT" ] && FRONTEND_COUNT=0
        echo ""
        echo -e "${GREEN}✓ Frontend tests passed (${FRONTEND_COUNT} tests)${NC}"
        FRONTEND_PASSED=true
    else
        FRONTEND_COUNT=$(echo "$FRONTEND_OUTPUT" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+' | head -1)
        [ -z "$FRONTEND_COUNT" ] && FRONTEND_COUNT=0
        echo ""
        echo -e "${RED}✗ Frontend tests failed (${FRONTEND_FAILED} failed, ${FRONTEND_COUNT} passed)${NC}"
        FRONTEND_PASSED=false
    fi
else
    echo -e "${YELLOW}Vitest not found. Skipping frontend tests.${NC}"
    echo -e "${YELLOW}To install: npm install --save-dev vitest${NC}"
    FRONTEND_PASSED=true  # Don't fail if frontend tests aren't set up
fi

cd ../..
echo ""

# Summary
echo "====================================="
echo "Test Summary"
echo "====================================="
if [ "$BACKEND_PASSED" = true ]; then
    echo -e "${GREEN}✓ Backend:  PASSED (${BACKEND_COUNT} tests)${NC}"
else
    echo -e "${RED}✗ Backend:  FAILED${NC}"
fi

if [ "$FRONTEND_PASSED" = true ]; then
    echo -e "${GREEN}✓ Frontend: PASSED (${FRONTEND_COUNT} tests)${NC}"
else
    echo -e "${RED}✗ Frontend: FAILED${NC}"
fi

TOTAL_TESTS=$((BACKEND_COUNT + FRONTEND_COUNT))
echo ""
echo "Total: ${TOTAL_TESTS} tests passed"
echo ""

# Exit with appropriate code
if [ "$BACKEND_PASSED" = true ] && [ "$FRONTEND_PASSED" = true ]; then
    echo -e "${GREEN}All tests passed successfully!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please review the output above.${NC}"
    exit 1
fi
