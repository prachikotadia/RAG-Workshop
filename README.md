# Prachi RAG Workspace

> **A production-ready Retrieval-Augmented Generation (RAG) platform** that enables users to upload documents, index them into a vector store, and interact with an AI assistant that answers questions grounded entirely in their private knowledge base.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.2-blue.svg)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.2-blue.svg)](https://www.typescriptlang.org/)

---

## 🎯 Overview

Prachi RAG Workspace is an end-to-end RAG platform that combines document management, vector search, and conversational AI to create a personal knowledge assistant. Users can securely upload documents (PDFs, text files, markdown, images), have them automatically indexed, and then ask questions that are answered using only their uploaded content with full citation tracking.

### Key Features

- **📄 Multi-format Document Support**: PDF, TXT, MD, and images (JPG, PNG, GIF, etc.)
- **🔍 Intelligent Vector Search**: FAISS-based semantic search with per-user isolation
- **💬 Conversational AI**: RAG-powered chat with conversation history
- **📸 Image Analysis**: Vision AI for image understanding and Q&A
- **🔐 Secure & Isolated**: JWT authentication with complete user data isolation
- **🎨 Modern UI**: Responsive React frontend with dark mode support
- **🔌 Provider Flexibility**: Support for OpenAI, Groq, HuggingFace, and local models

---

## 🏗️ Architecture

The system is built with a modular, scalable architecture:

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                     │
│  • TypeScript + Vite                                    │
│  • Tailwind CSS + Glassmorphism UI                      │
│  • React Router for navigation                          │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP/REST + JWT
┌────────────────────▼────────────────────────────────────┐
│              Backend (FastAPI)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   Auth       │  │  Documents   │  │     Chat     │   │
│  │   Service    │  │   Service    │  │   Service    │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │ 
│         │                 │                  │          │
│         └─────────────────┼──────────────────┘          │
│                           │                             │
│                  ┌────────▼────────┐                    │
│                  │    RAG Chain    │                    │
│                  │   Orchestrator  │                    │
│                  └────────┬────────┘                    │
│                           │                             │
│  ┌────────────────────────┼────────────────────────┐    │
│  │                        │                        │    │
│  ┌──────────┐  ┌──────────▼──────────┐  ┌──────────┐    │
│  │Embeddings│  │   Vector Store      │  │   LLM    │    │
│  │ Provider │  │   (FAISS/Pinecone)  │  │  Client  │    │
│  └──────────┘  └─────────────────────┘  └──────────┘    │
│                                                         │
│  ┌──────────────────────────────────────────────┐       │
│  │         Vision Analyzer (Images)             │       │
│  │  • OpenAI Vision API                         │       │
│  │  • BLIP-2 Captioning (local)                 │       │
│  │  • CLIP Embeddings                           │       │
│  └──────────────────────────────────────────────┘       │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼───────────────────────────────┐
│              Data & Storage Layer                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  PostgreSQL  │  │    FAISS     │  │  Filesystem  │ │
│  │   Database   │  │  Vector Store│  │   Storage    │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└───────────────────────────────────────────────────────┘
```

### Core Components

1. **API & Auth Layer**: FastAPI with JWT authentication, CORS, middleware
2. **RAG Engine**: Embedding → Vector Search → Context Building → LLM Generation
3. **Document Pipeline**: Upload → Parse → Chunk → Embed → Index
4. **Vector Store**: Per-user FAISS indexes with disk persistence
5. **Vision AI**: Multi-model image analysis with fallback chain

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+** (for frontend)
- **PostgreSQL 15+** (or Docker)
- **OpenAI API Key** (or alternative LLM provider)

### Installation

#### 1. Clone Repository

```bash
git clone <repository-url>
cd rag_workspace
```

#### 2. Backend Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your API keys (see Configuration section)
```

#### 3. Database Setup

**Option A: Docker (Recommended)**
```bash
docker-compose up -d db
```

**Option B: Local PostgreSQL**
```bash
# Create database
createdb ragworkspace

# Update DATABASE_URL in .env
# DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/ragworkspace
```

**Initialize Schema:**
```bash
# Using Alembic (recommended)
alembic upgrade head

# Or create tables directly (dev only)
python -c "from app.db.base import engine, Base; from app.db import models; Base.metadata.create_all(bind=engine)"
```

#### 4. Frontend Setup

```bash
cd frontend
npm install

# Configure API URL (optional, defaults to http://127.0.0.1:8000)
# Create frontend/.env if needed:
# VITE_API_BASE_URL=http://127.0.0.1:8000
```

#### 5. Start Services

**Terminal 1 - Backend:**
```bash
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

**Access:**
- Frontend: http://localhost:3000
- Backend API: http://127.0.0.1:8000
- API Docs: http://127.0.0.1:8000/docs

### Docker Deployment

```bash
# Start all services (backend + database)
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down
```

---

## ⚙️ Configuration

Configuration is managed via environment variables. Create a `.env` file in the project root:

### Required Variables

```bash
# Database
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/ragworkspace

# Security
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24 hours

# LLM Provider (at least one required)
OPENAI_API_KEY=sk-...  # For OpenAI embeddings + LLM + vision
# OR
GROQ_API_KEY=...       # For Groq/Llama models
LLM_PROVIDER=openai    # openai, groq, or local
LLM_MODEL=gpt-4o-mini  # OpenAI model name
```

### Optional Configuration

```bash
# Embeddings
EMBEDDINGS_PROVIDER=openai  # openai or huggingface
EMBEDDINGS_MODEL=text-embedding-3-small
HUGGINGFACE_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Vector Store
VECTORSTORE_PROVIDER=faiss  # faiss, pinecone, or chroma
VECTORSTORE_BASE_DIR=data/vectorstores

# Storage
STORAGE_PROVIDER=filesystem  # filesystem or s3
STORAGE_BASE_DIR=storage

# Image Analysis
ENABLE_CAPTION_MODEL=false  # Enable local BLIP-2 (slow on CPU)

# Application
ENVIRONMENT=dev  # dev, staging, or prod
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
MAX_FILE_SIZE_MB=50
```

See `.env.example` for complete configuration options.

---

## 📚 API Documentation

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/signup` | Create new user account |
| `POST` | `/auth/login` | Login and get JWT token |
| `GET` | `/auth/me` | Get current user profile |
| `PUT` | `/auth/me` | Update user profile |
| `POST` | `/auth/change-password` | Change password |
| `DELETE` | `/auth/me` | Delete account |

### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/documents/upload` | Upload documents (PDF, TXT, MD, images) |
| `GET` | `/documents` | List user documents |
| `GET` | `/documents/{id}` | Get document details |
| `DELETE` | `/documents/{id}` | Delete document |

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chat/sessions` | Create chat session |
| `GET` | `/chat/sessions` | List chat sessions |
| `GET` | `/chat/sessions/{id}` | Get session messages |
| `POST` | `/chat/sessions/{id}/message` | Send message (RAG response) |
| `DELETE` | `/chat/sessions/{id}` | Delete session |
| `DELETE` | `/chat/sessions/all` | Delete all chat history |

**Interactive API Documentation**: Visit http://127.0.0.1:8000/docs for Swagger UI.

---

## 🔄 RAG Pipeline Flow

The RAG (Retrieval-Augmented Generation) pipeline processes user questions as follows:

```
User Question
    │
    ▼
1. Embed Query
   • Convert question to embedding vector
   • Provider: OpenAI or HuggingFace
    │
    ▼
2. Vector Search
   • Search user's FAISS index
   • Return top-k similar chunks (default: k=10)
   • Distance metric: L2 (Euclidean)
    │
    ▼
3. Retrieve Chunks
   • Fetch full chunk text from PostgreSQL
   • Filter by user_id (security)
   • Join with Document table for titles
    │
    ▼
4. Build Context
   • Combine chunks with citations
   • Sort by relevance (score)
   • Truncate to max_chars (default: 4000)
   • Special handling for image chunks
    │
    ▼
5. Image Analysis (if image question detected)
   • Detect image-related keywords
   • analyze_image() with fallback chain:
     → OpenAI Vision API (primary)
     → BLIP-2 Captioning (fallback)
     → Metadata extraction (last resort)
   • Enhance context with vision analysis
    │
    ▼
6. Fetch Chat History
   • Get recent messages (last 10)
   • Exclude current question (avoid duplication)
   • Format as message dicts
    │
    ▼
7. Build LLM Messages
   • System prompt (instructions)
   • Context message (retrieved chunks)
   • History messages (conversation)
   • Current user question
    │
    ▼
8. Generate Answer
   • Call LLM (OpenAI/Groq/Local)
   • Temperature: 0.8, top_p: 0.9
   • Return answer text
    │
    ▼
9. Store & Return
   • Save user message
   • Save assistant message with citations
   • Return (answer, citations, analysis_info)
```

---

## 🧪 Testing

Run the test suite:

```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_rag_chain.py

# Run with coverage
pytest --cov=app tests/
```

---

## 🛠️ Tech Stack

### Backend

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Framework** | FastAPI 0.104 | Modern Python web framework |
| **Database** | PostgreSQL 15 | Relational data storage |
| **ORM** | SQLAlchemy 2.0 | Database abstraction |
| **Validation** | Pydantic 2.5 | Data validation & settings |
| **Vector DB** | FAISS | Dense vector search |
| **Embeddings** | OpenAI / HuggingFace | Text embeddings |
| **LLM** | OpenAI / Groq / Local | Language model |
| **Vision** | OpenAI Vision / BLIP-2 | Image analysis |
| **Auth** | JWT (python-jose) | Token-based authentication |
| **Password** | bcrypt (passlib) | Secure password hashing |
| **Migrations** | Alembic | Database schema management |
| **Server** | Uvicorn / Gunicorn | ASGI/WSGI server |

### Frontend

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Framework** | React 18 | UI library |
| **Language** | TypeScript 5.2 | Type-safe JavaScript |
| **Build Tool** | Vite 5 | Fast dev server & bundler |
| **Routing** | React Router 6 | Client-side routing |
| **Styling** | Tailwind CSS 3.3 | Utility-first CSS |
| **State** | React Hooks | Component state management |

### Infrastructure

- **Docker** & **Docker Compose** for containerization
- **Alembic** for database migrations
- **pytest** for testing

---

## 📁 Project Structure

```
rag_workspace/
├── app/                      # Backend application
│   ├── main.py              # FastAPI app initialization
│   ├── config.py            # Settings management
│   │
│   ├── db/                  # Database layer
│   │   ├── base.py          # SQLAlchemy engine & session
│   │   ├── models.py        # SQLAlchemy models
│   │   └── schemas.py       # Pydantic schemas
│   │
│   ├── auth/                # Authentication
│   │   ├── routes.py        # Auth endpoints
│   │   ├── service.py       # Auth business logic
│   │   ├── jwt.py           # JWT token handling
│   │   └── dependencies.py # get_current_user dependency
│   │
│   ├── documents/           # Document management
│   │   ├── routes.py        # Document endpoints
│   │   ├── service.py       # Document processing pipeline
│   │   ├── parsers.py       # PDF/TXT/MD/Image parsing
│   │   └── chunking.py      # Text chunking utilities
│   │
│   ├── embeddings/          # Embedding providers
│   │   ├── provider.py      # Abstract base + OpenAI
│   │   ├── huggingface.py   # HuggingFace provider
│   │   └── image_provider.py # CLIP image embeddings
│   │
│   ├── vectorstore/         # Vector database
│   │   ├── faiss_store.py   # FAISS implementation
│   │   ├── pinecone_store.py # Pinecone (optional)
│   │   └── chroma_store.py  # ChromaDB (optional)
│   │
│   ├── rag/                 # RAG pipeline
│   │   ├── chain.py         # Main RAG orchestrator
│   │   ├── context_builder.py # Context & citation building
│   │   ├── prompts.py       # LLM prompt templates
│   │   ├── image_analyzer.py # Image analysis
│   │   ├── vision_analyzer.py # OpenAI Vision API
│   │   ├── groq_client.py   # Groq/Llama client
│   │   └── hallucination_guard.py # Response validation
│   │
│   ├── chat/                # Chat system
│   │   ├── routes.py        # Chat endpoints
│   │   ├── service.py       # Chat business logic
│   │   └── history.py       # Message history retrieval
│   │
│   ├── storage/             # File storage
│   │   └── s3_storage.py    # AWS S3 storage (optional)
│   │
│   ├── utils/               # Utilities
│   │   ├── middleware.py    # Request ID, logging
│   │   ├── security.py      # Password hashing
│   │   ├── retry.py         # Retry logic
│   │   └── validation.py    # Input validation
│   │
│   └── telemetry/           # Observability
│       └── logging.py       # Logging configuration
│
├── frontend/                # React frontend
│   ├── src/
│   │   ├── api/            # API client and endpoint definitions
│   │   │   ├── client.ts   # HTTP client with JWT handling
│   │   │   ├── auth.ts     # Authentication endpoints
│   │   │   ├── documents.ts # Document endpoints
│   │   │   └── chat.ts     # Chat endpoints
│   │   ├── components/     # React components
│   │   │   ├── auth/      # Login/Signup forms
│   │   │   ├── chat/      # Chat interface components
│   │   │   ├── documents/ # Document management UI
│   │   │   ├── layout/    # Navbar, Sidebar, ThemeToggle
│   │   │   └── common/    # Shared components (modals, spinners)
│   │   ├── pages/          # Page-level components
│   │   │   ├── AuthPage.tsx
│   │   │   ├── DocumentsPage.tsx
│   │   │   ├── ChatPage.tsx
│   │   │   └── NotFoundPage.tsx
│   │   ├── hooks/          # Custom React hooks
│   │   │   └── useAuth.ts  # Authentication state management
│   │   ├── contexts/       # React contexts
│   │   │   └── ThemeContext.tsx # Dark/light theme
│   │   ├── styles/         # Global styles
│   │   │   └── globals.css # Tailwind + custom utilities
│   │   ├── App.tsx         # Main app component
│   │   ├── main.tsx        # Entry point
│   │   └── router.tsx      # Route configuration
│   ├── package.json
│   └── vite.config.ts
│
├── tests/                   # Test suite
│   ├── conftest.py         # Pytest configuration
│   ├── test_auth_flow.py
│   ├── test_chunking.py
│   └── test_rag_chain.py
│
├── alembic/                 # Database migrations
├── data/                    # Vector store data
├── storage/                 # Uploaded files
├── docker-compose.yml       # Docker services
├── Dockerfile              # Backend container
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

---

## 🔐 Security Features

- **JWT Authentication**: Stateless token-based auth with configurable expiration
- **Password Hashing**: bcrypt with 12 rounds (cost factor)
- **User Isolation**: All queries filtered by user_id, per-user vector indexes
- **Input Validation**: Pydantic schemas for all API inputs
- **CORS Configuration**: Configurable allowed origins
- **File Upload Security**: Extension whitelist, size limits, safe filename generation
- **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries

---

## 🎨 Frontend Architecture

### Component Structure

The frontend is built with React 18 and TypeScript, organized into clear layers:

- **API Layer** (`src/api/`): Centralized HTTP client with automatic JWT injection
- **Components** (`src/components/`): Reusable UI components organized by feature
- **Pages** (`src/pages/`): Top-level page components
- **Hooks** (`src/hooks/`): Custom React hooks for state management
- **Contexts** (`src/contexts/`): React contexts for global state (theme)

### State Management

- **Local State**: `useState` for component-level state
- **Global Auth**: `useAuth` hook with localStorage persistence
- **Theme**: `ThemeContext` for dark/light mode
- **No Redux**: Simple state management without external libraries

### API Integration

- **Centralized Client**: `api/client.ts` handles all HTTP requests
- **Automatic Auth**: JWT tokens injected via Authorization header
- **Error Handling**: Automatic 401 redirect to login
- **Type Safety**: TypeScript interfaces for all API responses

### Routing

- **Protected Routes**: `ProtectedRoute` component guards authenticated pages
- **Public Routes**: `/login` accessible without auth
- **Default Redirect**: `/` redirects to `/documents`

### Styling

- **Tailwind CSS** with custom utility classes
- **Dark Mode**: Class-based (`darkMode: 'class'`)
- **Custom Utilities**: `.glass`, `.glass-dark`, `.hover-lift`, `.hover-glow`
- **Responsive**: Mobile-first design with breakpoints

### Frontend Features

- **Responsive Design**: Mobile-first with Tailwind CSS
- **Dark Mode**: Full dark/light theme support
- **Glassmorphism UI**: Modern glass-effect design
- **Real-time Updates**: Document status tracking
- **Chat Interface**: Message history with citations
- **File Upload**: Drag-and-drop with progress
- **Error Handling**: User-friendly error messages
- **Loading States**: Visual feedback for async operations

### Frontend Development

**Available Scripts:**
- `npm run dev` - Start development server (port 3000)
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

**Development Server:**
- Port: 3000 (configurable in `vite.config.ts`)
- HMR: Hot Module Replacement enabled
- Proxy: `/api` requests proxied to backend (port 8000)

**Environment Variables:**
```bash
# frontend/.env (optional)
VITE_API_BASE_URL=http://127.0.0.1:8000
```

**Browser Support:**
- Modern browsers (Chrome, Firefox, Safari, Edge)
- ES2020+ features
- CSS Grid and Flexbox
- LocalStorage for token persistence

---

## 🚢 Deployment

### Production Checklist

- [ ] Set `ENVIRONMENT=prod` in `.env`
- [ ] Use strong `JWT_SECRET_KEY` (random, 32+ characters)
- [ ] Configure `CORS_ORIGINS` to specific domains (not `*`)
- [ ] Use HTTPS/TLS for all connections
- [ ] Set up database backups
- [ ] Configure logging aggregation
- [ ] Use managed PostgreSQL (RDS, Cloud SQL, etc.)
- [ ] Consider managed vector database (Pinecone) for scale
- [ ] Set up monitoring and alerting
- [ ] Use Gunicorn with multiple workers
- [ ] Configure reverse proxy (Nginx, Traefik)
- [ ] Set up CI/CD pipeline

### Docker Production

```bash
# Build image
docker build -t rag-workspace:latest .

# Run with production settings
docker run -d \
  -p 8000:8000 \
  -e ENVIRONMENT=prod \
  -e DATABASE_URL=... \
  -e JWT_SECRET_KEY=... \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/storage:/app/storage \
  rag-workspace:latest
```

---

## 📊 Performance Considerations

- **Vector Search**: FAISS IndexFlatL2 for exact search (O(n*d) complexity)
- **Embedding Batching**: Batch processing for multiple documents
- **Image Processing**: Timeouts configured (60s upload, 30s chat)
- **Database Indexing**: Indexed columns for fast queries
- **Connection Pooling**: SQLAlchemy connection pool
- **Caching**: LLM client and embedding provider singletons

**Scaling Recommendations:**
- Use FAISS IndexIVFFlat for large indexes (>100k vectors)
- Consider Pinecone for managed vector database
- Use S3 for document storage in cloud deployments
- Horizontal scaling with load balancer
- Redis for session/cache storage

---

## 🤝 Contributing

This is a personal project, but contributions are welcome:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

---


## 🙏 Acknowledgments

- **FastAPI** for the excellent web framework
- **FAISS** for efficient vector search
- **OpenAI** for embeddings and LLM APIs
- **React** and **Vite** for the frontend tooling
- **Tailwind CSS** for the utility-first styling

---

## 📞 Support

For issues, questions, or contributions, please open an issue on the repository.


