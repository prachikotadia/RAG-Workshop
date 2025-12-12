#!/bin/bash
# Script to create a launchd service for macOS auto-starting the backend
# Run with: bash scripts/create_launchd_service.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVICE_NAME="com.ragworkspace.backend"
PLIST_FILE="$HOME/Library/LaunchAgents/${SERVICE_NAME}.plist"

echo "Creating launchd service for RAG Workspace Backend (macOS)..."
echo ""

# Detect virtual environment
if [ -d "$PROJECT_DIR/venv_mac" ]; then
    VENV_PATH="$PROJECT_DIR/venv_mac"
elif [ -d "$PROJECT_DIR/venv" ]; then
    VENV_PATH="$PROJECT_DIR/venv"
elif [ -d "$PROJECT_DIR/.venv" ]; then
    VENV_PATH="$PROJECT_DIR/.venv"
else
    echo "Error: No virtual environment found!"
    exit 1
fi

# Create LaunchAgents directory if it doesn't exist
mkdir -p "$HOME/Library/LaunchAgents"

# Create plist file
cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${SERVICE_NAME}</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>${VENV_PATH}/bin/uvicorn</string>
        <string>app.main:app</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>8000</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>${PROJECT_DIR}</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>${VENV_PATH}/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
    
    <key>StandardOutPath</key>
    <string>${PROJECT_DIR}/backend.log</string>
    
    <key>StandardErrorPath</key>
    <string>${PROJECT_DIR}/backend.error.log</string>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    
    <key>ThrottleInterval</key>
    <integer>10</integer>
    
    <key>ProcessType</key>
    <string>Background</string>
</dict>
</plist>
EOF

chmod 644 "$PLIST_FILE"

echo "Service file created: $PLIST_FILE"
echo ""
echo "To load and start the service:"
echo "  launchctl load $PLIST_FILE"
echo "  launchctl start ${SERVICE_NAME}"
echo ""
echo "To check status:"
echo "  launchctl list | grep ${SERVICE_NAME}"
echo ""
echo "To stop the service:"
echo "  launchctl stop ${SERVICE_NAME}"
echo ""
echo "To unload the service:"
echo "  launchctl unload $PLIST_FILE"
