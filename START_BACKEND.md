# Starting the Backend

## Quick Start (Recommended)

```bash
bash ensure_backend_running.sh
```

This will:
- ✅ Check if backend is already running
- ✅ Kill any stuck processes automatically
- ✅ Start the monitor if needed
- ✅ Verify backend is healthy

## What the Monitor Does

The backend monitor (`start_backend_auto.sh`) runs continuously and:
- Checks backend health every 10 seconds
- Detects stuck processes (process exists but not responding)
- Automatically kills stuck processes
- Restarts backend if it fails or gets stuck
- Prevents multiple monitor instances

## Manual Commands

```bash
# Check backend status
bash check_backend.sh

# Start backend with monitoring
bash start_backend_auto.sh

# Kill all backend processes (if needed)
lsof -ti:8000 | xargs kill -9
```

## Troubleshooting

If backend keeps timing out:

1. **Check if monitor is running:**
   ```bash
   ps aux | grep start_backend_auto
   ```

2. **Restart monitor:**
   ```bash
   bash ensure_backend_running.sh
   ```

3. **Check logs:**
   ```bash
   tail -f backend_monitor.log
   tail -f backend.log
   ```

4. **Kill stuck processes and restart:**
   ```bash
   lsof -ti:8000 | xargs kill -9
   bash ensure_backend_running.sh
   ```

## Auto-Start on Boot (Optional)

For macOS:
```bash
bash scripts/create_launchd_service.sh
launchctl load ~/Library/LaunchAgents/com.ragworkspace.backend.plist
```

For Linux:
```bash
sudo bash scripts/create_systemd_service.sh
sudo systemctl enable rag-workspace-backend
sudo systemctl start rag-workspace-backend
```
