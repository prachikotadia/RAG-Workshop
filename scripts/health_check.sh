#!/bin/bash
# Comprehensive health check script for RAG Workspace
# Checks all dependencies and services before starting

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ERRORS=0
WARNINGS=0

check() {
    local name="$1"
    local command="$2"
    local required="${3:-true}"
    
    echo -n "Checking $name... "
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        if [ "$required" = "true" ]; then
            echo -e "${RED}✗${NC}"
            ERRORS=$((ERRORS + 1))
            return 1
        else
            echo -e "${YELLOW}⚠${NC} (optional)"
            WARNINGS=$((WARNINGS + 1))
            return 0
        fi
    fi
}

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}RAG Workspace Health Check${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# System checks
echo -e "${BLUE}System Dependencies:${NC}"
check "Python 3" "python3 --version"
check "pip" "pip --version"
check "Node.js" "node --version" false
check "npm" "npm --version" false

# Backend checks
echo ""
echo -e "${BLUE}Backend Dependencies:${NC}"
check "Virtual environment exists" "[ -d 'venv_mac' ] || [ -d 'venv' ] || [ -d '.venv' ]"

if [ -d "venv_mac" ]; then
    VENV_PATH="venv_mac"
elif [ -d "venv" ]; then
    VENV_PATH="venv"
elif [ -d ".venv" ]; then
    VENV_PATH=".venv"
fi

if [ -n "$VENV_PATH" ]; then
    source "$VENV_PATH/bin/activate"
    check "FastAPI installed" "python3 -c 'import fastapi'"
    check "SQLAlchemy installed" "python3 -c 'import sqlalchemy'"
    check "Uvicorn installed" "python3 -c 'import uvicorn'"
    deactivate
fi

# Configuration checks
echo ""
echo -e "${BLUE}Configuration:${NC}"
check ".env file exists" "[ -f '.env' ]"

if [ -f ".env" ]; then
    source .env 2>/dev/null || true
    if [ -z "$DATABASE_URL" ]; then
        echo -e "${YELLOW}⚠ DATABASE_URL not set in .env${NC}"
        WARNINGS=$((WARNINGS + 1))
    else
        echo -e "${GREEN}✓ DATABASE_URL is set${NC}"
    fi
    
    if [ -z "$JWT_SECRET_KEY" ]; then
        echo -e "${YELLOW}⚠ JWT_SECRET_KEY not set in .env${NC}"
        WARNINGS=$((WARNINGS + 1))
    else
        echo -e "${GREEN}✓ JWT_SECRET_KEY is set${NC}"
    fi
fi

# Port checks
echo ""
echo -e "${BLUE}Port Availability:${NC}"
if lsof -ti:8000 > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠ Port 8000 is in use${NC}"
    WARNINGS=$((WARNINGS + 1))
else
    echo -e "${GREEN}✓ Port 8000 is available${NC}"
fi

if lsof -ti:3000 > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠ Port 3000 is in use${NC}"
    WARNINGS=$((WARNINGS + 1))
else
    echo -e "${GREEN}✓ Port 3000 is available${NC}"
fi

# Database connectivity (if DATABASE_URL is set)
if [ -n "$DATABASE_URL" ] && [ -n "$VENV_PATH" ]; then
    echo ""
    echo -e "${BLUE}Database Connectivity:${NC}"
    source "$VENV_PATH/bin/activate"
    if python3 -c "
import os
from sqlalchemy import create_engine, text
try:
    engine = create_engine(os.environ.get('DATABASE_URL', '').replace('postgresql+psycopg2://', 'postgresql://'))
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    print('OK')
except Exception as e:
    print(f'ERROR: {e}')
    exit(1)
" 2>/dev/null | grep -q "OK"; then
        echo -e "${GREEN}✓ Database connection successful${NC}"
    else
        echo -e "${RED}✗ Database connection failed${NC}"
        ERRORS=$((ERRORS + 1))
    fi
    deactivate
fi

# Summary
echo ""
echo -e "${BLUE}========================================${NC}"
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ Checks passed with $WARNINGS warning(s)${NC}"
    exit 0
else
    echo -e "${RED}✗ Health check failed with $ERRORS error(s) and $WARNINGS warning(s)${NC}"
    exit 1
fi
