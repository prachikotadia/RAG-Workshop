# RAG Workspace - Quick Command Reference

## Backend Commands

### Start Backend
```bash
cd /Users/prachi/rag_workspace
source venv_mac/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Or run in background:**
```bash
cd /Users/prachi/rag_workspace
source venv_mac/bin/activate
nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
```

### Kill Backend
```bash
# Kill by port
lsof -ti :8000 | xargs kill -9

# Or kill by process name
pkill -f "uvicorn.*8000"

# Or kill all uvicorn processes
pkill -f uvicorn
```

### Check Backend Status
```bash
curl http://127.0.0.1:8000/health
```

### View Backend Logs (if running in background)
```bash
tail -f /tmp/backend.log
```

---

## Frontend Commands

### Start Frontend
```bash
cd /Users/prachi/rag_workspace/frontend
npm run dev
```

**Or run in background:**
```bash
cd /Users/prachi/rag_workspace/frontend
nohup npm run dev > /tmp/frontend.log 2>&1 &
```

### Kill Frontend
```bash
# Kill by port (usually 3000 or 5173)
lsof -ti :3000 | xargs kill -9
lsof -ti :5173 | xargs kill -9

# Or kill by process name
pkill -f "vite"
pkill -f "npm.*dev"

# Or kill all frontend processes
pkill -f "vite|npm.*frontend"
```

### Check Frontend Status
```bash
curl http://localhost:3000
# or
curl http://localhost:5173
```

### View Frontend Logs (if running in background)
```bash
tail -f /tmp/frontend.log
```

---

## Combined Commands

### Kill Both Backend and Frontend
```bash
pkill -f "uvicorn|vite|npm.*dev"
# Or more specific:
lsof -ti :8000 | xargs kill -9
lsof -ti :3000 | xargs kill -9
lsof -ti :5173 | xargs kill -9
```

### Start Both Backend and Frontend
```bash
# Terminal 1 - Backend
cd /Users/prachi/rag_workspace
source venv_mac/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend
cd /Users/prachi/rag_workspace/frontend
npm run dev
```

### Start Both in Background
```bash
# Backend
cd /Users/prachi/rag_workspace && source venv_mac/bin/activate && nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &

# Frontend
cd /Users/prachi/rag_workspace/frontend && nohup npm run dev > /tmp/frontend.log 2>&1 &
```

### Check What's Running
```bash
# Check processes
ps aux | grep -E "uvicorn|vite|npm.*dev" | grep -v grep

# Check ports
lsof -i :8000 -i :3000 -i :5173
```

---

## Quick Reference

| Action | Command |
|--------|---------|
| **Start Backend** | `cd /Users/prachi/rag_workspace && source venv_mac/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` |
| **Start Frontend** | `cd /Users/prachi/rag_workspace/frontend && npm run dev` |
| **Kill Backend** | `lsof -ti :8000 \| xargs kill -9` |
| **Kill Frontend** | `lsof -ti :3000 \| xargs kill -9` or `lsof -ti :5173 \| xargs kill -9` |
| **Kill Both** | `pkill -f "uvicorn\|vite\|npm.*dev"` |
| **Check Backend** | `curl http://127.0.0.1:8000/health` |
| **View Backend Logs** | `tail -f /tmp/backend.log` |
| **View Frontend Logs** | `tail -f /tmp/frontend.log` |

---

## Notes

- Backend runs on: `http://127.0.0.1:8000`
- Frontend typically runs on: `http://localhost:3000` or `http://localhost:5173` (Vite default)
- Backend API docs: `http://127.0.0.1:8000/docs`
- Make sure virtual environment is activated before starting backend
- Make sure `node_modules` are installed (`npm install`) before starting frontend

