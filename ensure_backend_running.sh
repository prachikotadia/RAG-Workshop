#!/bin/bash
# Ensure backend is always running - kills stuck processes and starts monitor

cd "$(dirname "$0")"

PORT=8000
HEALTH_URL="http://127.0.0.1:${PORT}/health"
LOCK_FILE="/tmp/rag_workspace_backend_monitor.lock"

echo "Ensuring backend is running..."

# Check if monitor is already running
if [ -f "$LOCK_FILE" ]; then
    OLD_PID=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
    if [ -n "$OLD_PID" ] && ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "✓ Monitor is already running (PID: $OLD_PID)"
        
        # Check if backend is actually responding
        if curl -s -m 3 "$HEALTH_URL" > /dev/null 2>&1; then
            echo "✓ Backend is healthy"
            exit 0
        else
            echo "⚠ Backend not responding, but monitor is running"
            echo "  Monitor will auto-restart backend soon"
            exit 0
        fi
    else
        rm -f "$LOCK_FILE"
    fi
fi

# Check for stuck processes
if lsof -ti:$PORT > /dev/null 2>&1; then
    if ! curl -s -m 3 "$HEALTH_URL" > /dev/null 2>&1; then
        echo "⚠ Detected stuck backend process"
        echo "  Killing stuck process..."
        lsof -ti:$PORT | xargs kill -9 2>/dev/null
        sleep 2
    fi
fi

# Start monitor in background and detach
echo "Starting backend monitor..."
nohup bash start_backend_auto.sh >> backend_monitor.log 2>&1 &
MONITOR_PID=$!
echo "Monitor started with PID: $MONITOR_PID"

echo "Waiting for backend to start..."
for i in {1..20}; do
    sleep 1
    if curl -s -m 2 "$HEALTH_URL" > /dev/null 2>&1; then
        echo "✓ Backend is now running and healthy!"
        exit 0
    fi
done

echo "⚠ Backend is starting (may take a bit longer)"
echo "  Monitor is running and will ensure backend stays healthy"
echo "  Check status: tail -f backend_monitor.log"
exit 0
