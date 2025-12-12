# Quick Start Guide

## 🚀 Fastest Way to Start

### 1. Start Backend (Auto-Restart)
```bash
bash ensure_backend_running.sh
```

This script:
- ✅ Checks all dependencies
- ✅ Detects and kills stuck processes automatically
- ✅ Starts backend with aggressive health monitoring (checks every 10s)
- ✅ Automatically restarts on failure or stuck processes
- ✅ Prevents multiple monitor instances
- ✅ Logs to `backend.log` and `backend_monitor.log`

### 2. Start Frontend
```bash
cd frontend
npm run dev
```

### 3. Access Application
- Frontend: http://localhost:3000
- Backend API: http://127.0.0.1:8000
- API Docs: http://127.0.0.1:8000/docs

## 🔧 Alternative Startup Methods

### Method 1: Comprehensive Startup (Recommended)
```bash
# Runs health checks + starts with auto-restart
bash scripts/start_all.sh
```

### Method 2: Standard Backend
```bash
source venv_mac/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Method 3: Health Check First
```bash
# Check everything before starting
bash scripts/health_check.sh
bash start_backend_auto.sh
```

## 🛡️ Production Setup

### macOS: Auto-Start on Boot
```bash
# Create launchd service
bash scripts/create_launchd_service.sh

# Load and start
launchctl load ~/Library/LaunchAgents/com.ragworkspace.backend.plist
launchctl start com.ragworkspace.backend
```

### Linux: Auto-Start on Boot
```bash
# Create systemd service
sudo bash scripts/create_systemd_service.sh

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable rag-workspace-backend
sudo systemctl start rag-workspace-backend
```

## 📊 Monitoring

### Check Backend Status
```bash
curl http://127.0.0.1:8000/health
```

### View Logs
```bash
# Auto-restart script logs
tail -f backend.log

# Systemd (Linux)
sudo journalctl -u rag-workspace-backend -f

# Launchd (macOS)
tail -f backend.log backend.error.log
```

## 🆘 Troubleshooting

### Backend Won't Start
```bash
# Run health check
bash scripts/health_check.sh

# Check logs
tail -f backend.log

# Kill existing process
lsof -ti:8000 | xargs kill -9
```

### Port Already in Use
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Or let auto-restart script handle it
bash start_backend_auto.sh
```

### Database Connection Issues
```bash
# Test connection
source venv_mac/bin/activate
python3 -c "
from app.db.base import engine
from sqlalchemy import text
with engine.connect() as conn:
    conn.execute(text('SELECT 1'))
print('Database OK')
"
```

## 📚 More Information

- **Full Documentation**: [README.md](README.md)
- **Reliability Guide**: [RELIABILITY.md](RELIABILITY.md)
- **API Documentation**: http://127.0.0.1:8000/docs
