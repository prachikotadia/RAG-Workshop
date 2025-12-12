#!/bin/bash
# Auto-restart backend script with health monitoring
# This script will automatically restart the backend if it crashes or becomes unresponsive

set -e

# Ensure only one instance of this script runs
LOCK_FILE="/tmp/rag_workspace_backend_monitor.lock"
if [ -f "$LOCK_FILE" ]; then
    OLD_PID=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
    if [ -n "$OLD_PID" ] && ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "Monitor script is already running (PID: $OLD_PID)"
        exit 0
    else
        rm -f "$LOCK_FILE"
    fi
fi
echo $$ > "$LOCK_FILE"
trap "rm -f $LOCK_FILE; exit" INT TERM EXIT

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

BACKEND_PORT=8000
HEALTH_CHECK_URL="http://127.0.0.1:${BACKEND_PORT}/health"
MAX_RESTART_ATTEMPTS=10
RESTART_DELAY=5
HEALTH_CHECK_INTERVAL=10  # Check every 10 seconds (more aggressive)
UNHEALTHY_THRESHOLD=2  # Restart after 2 consecutive failures (faster recovery)
STUCK_PROCESS_TIMEOUT=5  # Consider process stuck if no response in 5 seconds

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Function to check if backend is healthy
check_backend_health() {
    local response=$(curl -s -w "\n%{http_code}" --max-time $STUCK_PROCESS_TIMEOUT "$HEALTH_CHECK_URL" 2>/dev/null || echo -e "\n000")
    local http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "200" ]; then
        return 0  # Healthy
    else
        return 1  # Unhealthy
    fi
}

# Function to detect and kill stuck processes
detect_and_kill_stuck_processes() {
    local pids=$(lsof -ti:$BACKEND_PORT 2>/dev/null || true)
    if [ -n "$pids" ]; then
        # Process exists on port, but check if it's actually responding
        if ! check_backend_health; then
            warn "Detected stuck process(es) on port $BACKEND_PORT - not responding to health checks"
            # Kill all processes on the port
            echo "$pids" | xargs kill -9 2>/dev/null || true
            sleep 2
            # Double-check and force kill any remaining
            local remaining=$(lsof -ti:$BACKEND_PORT 2>/dev/null || true)
            if [ -n "$remaining" ]; then
                warn "Force killing remaining stuck process(es)"
                echo "$remaining" | xargs kill -9 2>/dev/null || true
                sleep 1
            fi
            # Final check - if still stuck, use pkill
            local still_stuck=$(lsof -ti:$BACKEND_PORT 2>/dev/null || true)
            if [ -n "$still_stuck" ]; then
                warn "Using pkill to force kill all uvicorn processes"
                pkill -9 -f "uvicorn.*8000" 2>/dev/null || true
                sleep 1
            fi
            return 0  # Stuck process killed
        fi
    fi
    return 1  # No stuck process
}

# Function to kill existing backend process
kill_existing_backend() {
    # First check for stuck processes
    detect_and_kill_stuck_processes
    
    # Then kill any remaining processes on the port
    local pid=$(lsof -ti:$BACKEND_PORT 2>/dev/null || true)
    if [ -n "$pid" ]; then
        warn "Killing existing backend process (PID: $pid)"
        kill -9 "$pid" 2>/dev/null || true
        sleep 2
        # Double-check port is clear
        local remaining=$(lsof -ti:$BACKEND_PORT 2>/dev/null || true)
        if [ -n "$remaining" ]; then
            warn "Force killing remaining process (PID: $remaining)"
            kill -9 "$remaining" 2>/dev/null || true
            sleep 1
        fi
    fi
}

# Function to find and activate virtual environment
activate_venv() {
    if [ -d "venv_mac" ]; then
        source venv_mac/bin/activate
        log "Activated macOS virtual environment"
    elif [ -d "venv" ] && [ -d "venv/bin" ]; then
        source venv/bin/activate
        log "Activated virtual environment"
    elif [ -d ".venv" ]; then
        source .venv/bin/activate
        log "Activated virtual environment"
    else
        error "No virtual environment found!"
        error "Please create one with: python3 -m venv venv_mac"
        exit 1
    fi
}

# Function to check dependencies
check_dependencies() {
    log "Checking dependencies..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        error "Python 3 is not installed"
        exit 1
    fi
    
    # Check if .env file exists
    if [ ! -f ".env" ]; then
        warn ".env file not found. Creating from .env.example if available..."
        if [ -f ".env.example" ]; then
            cp .env.example .env
            warn "Please edit .env and add your configuration"
        else
            error ".env file is required"
            exit 1
        fi
    fi
    
    # Check if required Python packages are installed
    if ! python3 -c "import fastapi" 2>/dev/null; then
        error "FastAPI is not installed. Please run: pip install -r requirements.txt"
        exit 1
    fi
    
    log "Dependencies check passed"
}

# Function to start backend
start_backend() {
    log "Starting backend server on port $BACKEND_PORT..."
    
    # Kill any existing backend (including stuck processes)
    kill_existing_backend
    
    # Double-check for any stuck processes before starting
    detect_and_kill_stuck_processes
    
    # Activate virtual environment
    activate_venv
    
    # Start uvicorn in background
    nohup uvicorn app.main:app \
        --host 0.0.0.0 \
        --port $BACKEND_PORT \
        --reload \
        > backend.log 2>&1 &
    
    local backend_pid=$!
    log "Backend started with PID: $backend_pid"
    
    # Wait for backend to start
    local wait_time=0
    local max_wait=30
    
    while [ $wait_time -lt $max_wait ]; do
        if check_backend_health; then
            log "Backend is healthy and responding"
            return 0
        fi
        sleep 2
        wait_time=$((wait_time + 2))
    done
    
    error "Backend failed to start within $max_wait seconds"
    return 1
}

# Main monitoring loop
monitor_backend() {
    local restart_count=0
    local unhealthy_count=0
    
    while true; do
        # First check for stuck processes (process exists but not responding)
        if detect_and_kill_stuck_processes; then
            warn "Stuck process detected and killed. Restarting backend..."
            unhealthy_count=$UNHEALTHY_THRESHOLD  # Force restart
        fi
        
        if check_backend_health; then
            unhealthy_count=0
            sleep $HEALTH_CHECK_INTERVAL
        else
            unhealthy_count=$((unhealthy_count + 1))
            warn "Backend health check failed ($unhealthy_count/$UNHEALTHY_THRESHOLD)"
            
            if [ $unhealthy_count -ge $UNHEALTHY_THRESHOLD ]; then
                error "Backend is unhealthy. Restarting..."
                restart_count=$((restart_count + 1))
                
                if [ $restart_count -gt $MAX_RESTART_ATTEMPTS ]; then
                    error "Maximum restart attempts ($MAX_RESTART_ATTEMPTS) reached. Stopping."
                    exit 1
                fi
                
                if start_backend; then
                    log "Backend restarted successfully (attempt $restart_count)"
                    unhealthy_count=0
                    restart_count=0  # Reset on successful restart
                else
                    error "Failed to restart backend (attempt $restart_count/$MAX_RESTART_ATTEMPTS)"
                    sleep $RESTART_DELAY
                fi
            else
                sleep $HEALTH_CHECK_INTERVAL
            fi
        fi
    done
}

# Trap signals for graceful shutdown
trap 'log "Shutting down..."; kill_existing_backend; exit 0' SIGINT SIGTERM

# Main execution
main() {
    log "=========================================="
    log "RAG Workspace Backend Auto-Restart Script"
    log "=========================================="
    
    # Check dependencies
    check_dependencies
    
    # Start backend
    if ! start_backend; then
        error "Failed to start backend. Exiting."
        exit 1
    fi
    
    log "Backend monitoring started"
    log "Health check interval: ${HEALTH_CHECK_INTERVAL}s"
    log "Unhealthy threshold: ${UNHEALTHY_THRESHOLD} consecutive failures"
    log "Press Ctrl+C to stop"
    log "=========================================="
    
    # Start monitoring
    monitor_backend
}

main
