#!/bin/bash
# Quick script to check and restart backend if needed

PORT=8000
HEALTH_URL="http://127.0.0.1:${PORT}/health"

echo "Checking backend on port ${PORT}..."

# Check if port is in use
if lsof -ti:${PORT} > /dev/null 2>&1; then
    echo "✓ Port ${PORT} is in use"
    
    # Check if it's responding (with timeout)
    if curl -s -m 3 "${HEALTH_URL}" > /dev/null 2>&1; then
        echo "✓ Backend is responding"
        curl -s "${HEALTH_URL}" | python3 -m json.tool 2>/dev/null | head -3
        exit 0
    else
        echo "✗ Backend process exists but not responding (stuck)"
        echo "  Killing stuck process..."
        lsof -ti:${PORT} | xargs kill -9 2>/dev/null
        sleep 2
    fi
else
    echo "✗ No process on port ${PORT}"
fi

echo "Starting backend..."
cd "$(dirname "$0")"

# Check if monitor is already running
if [ -f "/tmp/rag_workspace_backend_monitor.lock" ]; then
    OLD_PID=$(cat "/tmp/rag_workspace_backend_monitor.lock" 2>/dev/null || echo "")
    if [ -n "$OLD_PID" ] && ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "✓ Monitor script is already running (PID: $OLD_PID)"
        echo "  Waiting for backend to become healthy..."
        for i in {1..15}; do
            sleep 1
            if curl -s -m 2 "${HEALTH_URL}" > /dev/null 2>&1; then
                echo "✓ Backend is now running and responding!"
                curl -s "${HEALTH_URL}" | python3 -m json.tool 2>/dev/null | head -3
                exit 0
            fi
        done
    else
        rm -f "/tmp/rag_workspace_backend_monitor.lock"
    fi
fi

# Start monitor in background
nohup bash start_backend_auto.sh > backend_monitor.log 2>&1 &

echo "Waiting for backend to start..."
for i in {1..15}; do
    sleep 1
    if curl -s -m 2 "${HEALTH_URL}" > /dev/null 2>&1; then
        echo "✓ Backend is now running and responding!"
        curl -s "${HEALTH_URL}" | python3 -m json.tool 2>/dev/null | head -3
        exit 0
    fi
done

echo "✗ Backend failed to start. Check logs:"
echo "  Monitor: tail -f backend_monitor.log"
echo "  Backend: tail -f backend.log"
exit 1
