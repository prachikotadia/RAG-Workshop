#!/bin/bash
# Comprehensive startup script that checks health and starts all services
# This is the main entry point for starting the RAG Workspace

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}RAG Workspace Startup Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Run health check first
echo -e "${BLUE}Running health checks...${NC}"
if bash scripts/health_check.sh; then
    echo -e "${GREEN}✓ Health checks passed${NC}"
else
    echo -e "${YELLOW}⚠ Health checks completed with warnings${NC}"
fi

echo ""
echo -e "${BLUE}Starting backend with auto-restart...${NC}"
echo ""

# Start backend with auto-restart
exec bash start_backend_auto.sh
