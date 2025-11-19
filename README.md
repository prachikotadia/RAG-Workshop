# RAG Workspace

> **A production-ready Retrieval-Augmented Generation (RAG) platform** that enables users to upload documents, index them into a vector store, and interact with an AI assistant that answers questions grounded entirely in their private knowledge base.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.2-blue.svg)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.2-blue.svg)](https://www.typescriptlang.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [API Documentation](#-api-documentation)
- [Project Structure](#-project-structure)
- [Tech Stack](#-tech-stack)
- [Deployment](#-deployment)
- [Contributing](#-contributing)

---

## 🎯 Overview

RAG Workspace is a full-stack application that combines document management, semantic search, and conversational AI. Users can securely upload documents (PDFs, text files, markdown, images), have them automatically processed and indexed, and then ask questions that are answered using only their uploaded content with full citation tracking.

### Use Cases

- **Personal Knowledge Base**: Upload your documents and ask questions about them
- **Research Assistant**: Index research papers and get AI-powered answers
- **Document Q&A**: Quickly find information in large document collections
- **Image Analysis**: Ask questions about uploaded images and GIFs

### Screenshots

![Document Upload Page Screenshot](assets/screenshots/document_page.png)

![Chat Upload Page Screenshot](assets/screenshots/Chat_upload.png)

  
assets/screenshots/Screenshot 2025-11-19 at 8.14.11 AM.png

---

## ✨ Features

### Core Capabilities

- **📄 Multi-format Document Support**: PDF, TXT, MD, and images (JPG, PNG, GIF)
- **🔍 Semantic Vector Search**: FAISS-based similarity search with per-user isolation
- **💬 Conversational AI**: RAG-powered chat with conversation history
- **📸 Image Analysis**: Vision AI for image understanding and Q&A
- **🔐 Secure & Isolated**: JWT authentication with complete user data isolation
- **🎨 Modern UI**: Responsive React frontend with dark mode and glassmorphism design
- **🔌 Provider Flexibility**: Support for OpenAI, Groq, HuggingFace, and local models

### Technical Highlights

- **Per-user Vector Indexes**: Complete data isolation with separate FAISS indexes
- **Citation Tracking**: Every answer includes source document references
- **Multi-model Fallback**: Automatic fallback chain for image analysis
- **Real-time Status Updates**: Document processing status tracking
- **Mobile Responsive**: Fully functional on desktop, tablet, and mobile devices

---

## 🏗️ Architecture

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
│  │  • BLIP-2 Captioning (local)                │       │
│  │  • CLIP Embeddings                          │       │
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

### RAG Pipeline Flow

1. **User Question** → Embed query using OpenAI/HuggingFace
2. **Vector Search** → Search user's FAISS index for top-k similar chunks
3. **Retrieve Context** → Fetch full chunk text with document metadata
4. **Image Analysis** (if applicable) → Analyze images using Vision API or BLIP-2
5. **Build Context** → Combine chunks with citations and image analysis
6. **Generate Answer** → Call LLM (OpenAI/Groq/Local) with context and history
7. **Store & Return** → Save messages and return answer with citations

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **PostgreSQL 15+** (or Docker)
- **OpenAI API Key** (or alternative LLM provider)

### Installation

#### 1. Clone Repository

```bash
git clone https://github.com/prachikotadia/RAG-Workshop.git
cd RAG-Workshop
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
# Edit .env and add your API keys
```

#### 3. Database Setup

**Option A: Docker (Recommended)**
```bash
docker-compose up -d db
```

**Option B: Local PostgreSQL**
```bash
createdb ragworkspace
# Update DATABASE_URL in .env
```

**Initialize Schema:**
```bash
alembic upgrade head
```

#### 4. Frontend Setup

```bash
cd frontend
npm install
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

---

## ⚙️ Configuration

Create a `.env` file in the project root with the following variables:

### Required Variables

```bash
# Database
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/ragworkspace

# Security
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# LLM Provider (at least one required)
OPENAI_API_KEY=sk-...
# OR
GROQ_API_KEY=...
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
```

### Optional Configuration

```bash
# Embeddings
EMBEDDINGS_PROVIDER=openai
EMBEDDINGS_MODEL=text-embedding-3-small

# Vector Store
VECTORSTORE_PROVIDER=faiss
VECTORSTORE_BASE_DIR=data/vectorstores

# Storage
STORAGE_PROVIDER=filesystem
STORAGE_BASE_DIR=storage

# Application
ENVIRONMENT=dev
CORS_ORIGINS=http://localhost:3000
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

## 📁 Project Structure

```
rag_workspace/
├── app/                      # Backend application
│   ├── main.py              # FastAPI app initialization
│   ├── config.py            # Settings management
│   ├── db/                  # Database layer (models, schemas, base)
│   ├── auth/                # Authentication (routes, service, JWT)
│   ├── documents/           # Document management (upload, parse, chunk)
│   ├── embeddings/          # Embedding providers (OpenAI, HuggingFace)
│   ├── vectorstore/         # Vector database (FAISS, Pinecone, Chroma)
│   ├── rag/                 # RAG pipeline (chain, context, prompts)
│   ├── chat/                # Chat system (sessions, messages)
│   ├── storage/             # File storage (filesystem, S3)
│   ├── utils/               # Utilities (middleware, security, retry)
│   └── telemetry/           # Observability (logging)
│
├── frontend/                # React frontend
│   ├── src/
│   │   ├── api/            # API client and endpoints
│   │   ├── components/     # React components (auth, chat, documents, layout)
│   │   ├── pages/          # Page-level components
│   │   ├── hooks/          # Custom React hooks
│   │   ├── contexts/       # React contexts (theme)
│   │   └── styles/         # Global styles
│   └── package.json
│
├── tests/                   # Test suite
├── alembic/                 # Database migrations
├── docker-compose.yml       # Docker services
├── Dockerfile              # Backend container
└── requirements.txt        # Python dependencies
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
| **Migrations** | Alembic | Database schema management |

### Frontend

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Framework** | React 18 | UI library |
| **Language** | TypeScript 5.2 | Type-safe JavaScript |
| **Build Tool** | Vite 5 | Fast dev server & bundler |
| **Routing** | React Router 6 | Client-side routing |
| **Styling** | Tailwind CSS 3.3 | Utility-first CSS |

### Infrastructure

- **Docker** & **Docker Compose** for containerization
- **Alembic** for database migrations
- **pytest** for testing

---

## 🚢 Deployment

### Production Checklist

- [ ] Set `ENVIRONMENT=prod` in `.env`
- [ ] Use strong `JWT_SECRET_KEY` (random, 32+ characters)
- [ ] Configure `CORS_ORIGINS` to specific domains
- [ ] Use HTTPS/TLS for all connections
- [ ] Set up database backups
- [ ] Configure logging aggregation
- [ ] Use managed PostgreSQL (RDS, Cloud SQL, etc.)
- [ ] Set up monitoring and alerting
- [ ] Use Gunicorn with multiple workers
- [ ] Configure reverse proxy (Nginx, Traefik)

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

### Docker Compose

```bash
# Start all services (backend + database)
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down
```

---

## 🔐 Security Features

- **JWT Authentication**: Stateless token-based auth with configurable expiration
- **Password Hashing**: bcrypt with 12 rounds
- **User Isolation**: All queries filtered by user_id, per-user vector indexes
- **Input Validation**: Pydantic schemas for all API inputs
- **CORS Configuration**: Configurable allowed origins
- **File Upload Security**: Extension whitelist, size limits, safe filename generation
- **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries

---

## 🧪 Testing

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

## 📊 Performance Considerations

- **Vector Search**: FAISS IndexFlatL2 for exact search
- **Embedding Batching**: Batch processing for multiple documents
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

Contributions are welcome![Chat Interface Screenshot]Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🙏 Acknowledgments

- **FastAPI** for the excellent web framework
- **FAISS** for efficient vector search
- **OpenAI** for embeddings and LLM APIs
- **React** and **Vite** for the frontend tooling
- **Tailwind CSS** for the utility-first styling

---

## 📞 Support

For issues, questions, or contributions, please open an issue on the [GitHub repository](https://github.com/prachikotadia/RAG-Workshop).

---

**Built with ❤️ using FastAPI, React, and modern AI technologies.**
