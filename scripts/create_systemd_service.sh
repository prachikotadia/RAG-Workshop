#!/bin/bash
# Script to create a systemd service for auto-starting the backend
# Run with: sudo bash scripts/create_systemd_service.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVICE_NAME="rag-workspace-backend"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
USER=$(whoami)

echo "Creating systemd service for RAG Workspace Backend..."
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

# Create service file
cat > /tmp/${SERVICE_NAME}.service << EOF
[Unit]
Description=RAG Workspace Backend API
After=network.target postgresql.service
Requires=network.target

[Service]
Type=simple
User=${USER}
WorkingDirectory=${PROJECT_DIR}
Environment="PATH=${VENV_PATH}/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=${PROJECT_DIR}/.env
ExecStart=${VENV_PATH}/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=${SERVICE_NAME}

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

# Security settings
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# Copy to systemd directory
sudo cp /tmp/${SERVICE_NAME}.service "$SERVICE_FILE"
sudo chmod 644 "$SERVICE_FILE"

echo "Service file created: $SERVICE_FILE"
echo ""
echo "To enable and start the service:"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl enable ${SERVICE_NAME}"
echo "  sudo systemctl start ${SERVICE_NAME}"
echo ""
echo "To check status:"
echo "  sudo systemctl status ${SERVICE_NAME}"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u ${SERVICE_NAME} -f"
