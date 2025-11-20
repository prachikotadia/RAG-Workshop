# RAG Workspace - Complete Technical Interview Reference

## 🎯 PROJECT OVERVIEW

**RAG Workspace** is a full-stack Retrieval-Augmented Generation (RAG) platform built with FastAPI (Python) backend and React (TypeScript) frontend. Users can upload documents (PDFs, text files, markdown, images), have them automatically processed, chunked, embedded, and indexed into a vector store. They can then ask questions via a chat interface, and the system uses RAG to answer based on their uploaded documents with full citation tracking.

**Key Technologies:**
- **Backend**: FastAPI 0.104, Python 3.11+, SQLAlchemy 2.0, PostgreSQL, FAISS
- **Frontend**: React 18, TypeScript 5.2, Vite 5, Tailwind CSS 3.3
- **ML/AI**: OpenAI API (embeddings, LLM, vision), HuggingFace Transformers, BLIP-2, CLIP, Groq API
- **Auth**: JWT (python-jose), bcrypt password hashing
- **Storage**: Local filesystem (per-user directories), optional S3

---

## 📁 COMPLETE FILE STRUCTURE WITH DESCRIPTIONS

### Backend (`/app/`)

#### Core Application Files

**`app/main.py`** (Lines 1-266)
- **Purpose**: FastAPI application entry point and initialization
- **Key Functions**:
  - `create_app()`: Creates and configures FastAPI app
  - Sets up CORS middleware (lines 48-55)
  - Adds RequestIDMiddleware, LoggingMiddleware, TimeoutMiddleware (lines 58-126)
  - Global exception handlers (lines 154-211)
  - Includes routers: auth, documents, chat, admin (lines 245-248)
  - Health check endpoint `/health` (lines 255-259)
- **Critical Details**:
  - CORS configured for localhost:3000, 3001, 5173
  - Timeout middleware: 300s for uploads, 120s for chat, 30s for others
  - All error responses include CORS headers

**`app/config.py`** (Lines 1-73)
- **Purpose**: Centralized configuration using Pydantic BaseSettings
- **Key Settings**:
  - Database: `database_url` (line 18)
  - Security: `jwt_secret_key`, `jwt_algorithm`, `access_token_expire_minutes` (lines 22-24)
  - LLM: `openai_api_key`, `llm_model`, `llm_provider` (lines 27-29, 43)
  - Embeddings: `embeddings_provider`, `embeddings_model`, `huggingface_model` (lines 28, 36-37)
  - Vector Store: `vectorstore_provider`, `vectorstore_base_dir` (lines 32, 50)
  - Storage: `storage_base_dir`, `storage_provider` (lines 44-45)
  - Image Analysis: `enable_caption_model`, `local_caption_model_name` (lines 61-62)
- **Function**: `get_settings()` - Returns cached settings instance (line 70)

#### Database Layer (`/app/db/`)

**`app/db/models.py`** (Lines 1-109)
- **Purpose**: SQLAlchemy ORM models defining database schema
- **Models**:
  - `User` (lines 31-41): id, email, hashed_password, created_at, relationships
  - `RefreshToken` (lines 44-53): id, user_id, token, expires_at, created_at
  - `Document` (lines 56-69): id, user_id, title, original_filename, status (enum), num_chunks, timestamps
  - `DocumentChunk` (lines 72-82): id, document_id, chunk_index, text, token_count, chunk_metadata (JSON)
  - `ChatSession` (lines 85-94): id, user_id, title, created_at
  - `ChatMessage` (lines 97-107): id, session_id, role (enum), content, retrieved_chunks (JSON), created_at
- **Enums**:
  - `DocumentStatus`: UPLOADING, INDEXING, READY, FAILED (lines 18-22)
  - `ChatRole`: USER, ASSISTANT (lines 25-28)
- **Relationships**: All use cascade delete for data cleanup

**`app/db/schemas.py`**
- **Purpose**: Pydantic schemas for API request/response validation
- **Key Schemas**: UserCreate, UserRead, UserLogin, Token, DocumentRead, ChatSessionRead, ChatMessageRead

**`app/db/base.py`**
- **Purpose**: Database connection setup
- **Key Functions**: `get_db()` - FastAPI dependency for database sessions

#### Authentication (`/app/auth/`)

**`app/auth/routes.py`** (Lines 1-246)
- **Purpose**: Authentication API endpoints
- **Endpoints**:
  - `POST /auth/signup` (line 24): Create user account
  - `POST /auth/login` (line 74): Login, returns JWT token
  - `GET /auth/me` (line 127): Get current user profile
  - `PUT /auth/me` (line 184): Update user profile
  - `POST /auth/change-password` (line 208): Change password
  - `DELETE /auth/me` (line 237): Delete account
  - `POST /auth/refresh` (line 146): Refresh access token
- **Dependencies**: Uses `get_current_user` from `app/auth/dependencies.py`

**`app/auth/service.py`**
- **Purpose**: Authentication business logic
- **Key Functions**:
  - `create_user()`: Creates user with bcrypt hashed password
  - `authenticate_user()`: Validates email/password, returns User or None
  - `create_user_access_token()`: Generates JWT token
  - `delete_user_account()`: Deletes user, cleans up vector store and storage files

**`app/auth/jwt.py`**
- **Purpose**: JWT token creation and validation
- **Key Functions**:
  - `create_access_token()`: Creates JWT with user email and ID
  - `decode_access_token()`: Validates and decodes JWT

**`app/auth/dependencies.py`**
- **Purpose**: FastAPI dependencies for authentication
- **Key Function**: `get_current_user()` - Extracts user from JWT token, raises 401 if invalid

#### Document Management (`/app/documents/`)

**`app/documents/routes.py`** (Lines 1-251)
- **Purpose**: Document upload and management API endpoints
- **Endpoints**:
  - `POST /documents/upload` (line 44): Upload one or more files, processes and indexes them
  - `GET /documents` (line 185): List all user documents
  - `GET /documents/{document_id}` (line 204): Get specific document
  - `DELETE /documents/{document_id}` (line 228): Delete document and chunks
- **Validation**: File extension, size (50MB max), MIME type validation before processing

**`app/documents/service.py`** (Lines 1-597)
- **Purpose**: Document ingestion pipeline orchestration
- **Key Functions**:
  - `save_upload_to_disk()` (line 29): Saves file to `storage/user_{user_id}/uploads/` with timestamped filename
  - `create_document_record()` (line 64): Creates Document row with status=UPLOADING
  - `process_and_index_document()` (line 100): **CRITICAL PIPELINE FUNCTION**
    - Flow: Save file → Create record → Set INDEXING → Extract text → Chunk → Create chunks → Embed → Add to vector store → Set READY
    - **GUARANTEES**: Document status is ALWAYS READY or FAILED (never stuck in UPLOADING/INDEXING)
    - Image processing: Uses BLIP-2 for captioning, CLIP for embeddings (lines 187-269)
    - Error handling: All exceptions caught, document marked as FAILED (lines 439-489)
  - `list_user_documents()` (line 492): Returns all documents for user
  - `get_user_document()` (line 511): Gets document by ID, ensures user ownership
  - `delete_user_document()` (line 548): Deletes document, removes from vector store, deletes file

**`app/documents/parsers.py`**
- **Purpose**: Extract text and metadata from files
- **Key Functions**:
  - `extract_text_from_pdf()`: Uses PyPDF2 to extract text
  - `extract_text_from_text_file()`: Reads plain text/markdown
  - `extract_text_from_image()`: Extracts image metadata (dimensions, format, etc.)
  - `extract_text_from_file()`: Router function that calls appropriate parser based on file extension

**`app/documents/chunking.py`**
- **Purpose**: Split text into overlapping chunks
- **Key Function**: `chunk_text()` - Splits text into chunks with max_words and overlap_words

#### RAG Pipeline (`/app/rag/`)

**`app/rag/chain.py`** (Lines 1-693)
- **Purpose**: Core RAG orchestrator - the heart of the system
- **Key Classes**:
  - `LlmClient` (abstract, line 26): Interface for LLM calls
  - `OpenAILlmClient` (line 43): OpenAI API implementation
  - `RagChain` (line 102): Main RAG orchestrator class
- **Key Method**: `RagChain.answer_question()` (line 127)
  - **Flow**:
    1. Embed query using embeddings provider (line 161)
    2. Search vector store for top-k chunks (lines 166-170)
    3. If no chunks but image question, search for image documents and analyze (lines 173-297)
    4. Fetch chunks from database (lines 325-333)
    5. Build context and citations (line 345)
    6. Check for image chunks, perform vision analysis if needed (lines 348-542)
    7. Fetch chat history (line 545)
    8. Build LLM messages (lines 549-553)
    9. Call LLM (line 558)
    10. Return (answer, citations, analysis_info) (line 618)
- **Image Analysis Logic**: 
  - Detects image questions by keywords (lines 359-368)
  - Uses `analyze_image()` for real-time vision analysis (lines 371-455)
  - Falls back to stored analysis in chunks if file not found (lines 527-529)
- **Factory Functions**:
  - `_build_llm_client()` (line 622): Builds LLM client based on `llm_provider` setting
  - `get_llm_client()` (line 675): FastAPI dependency

**`app/rag/prompts.py`** (Lines 1-197)
- **Purpose**: LLM prompt templates and message building
- **Key Content**:
  - `SYSTEM_PROMPT` (line 8): Comprehensive system prompt with image analysis rules, response style guidelines
  - `build_messages()` (line 125): Constructs message array for LLM
    - Structure: system prompt → context message → history messages → current question
    - Handles image analysis context specially (lines 155-178)

**`app/rag/context_builder.py`**
- **Purpose**: Builds context string and citations from retrieved chunks
- **Key Function**: `build_context()` - Combines chunk texts, prioritizes image chunks, creates citation list

**`app/rag/image_analyzer.py`** (Lines 1-700+)
- **Purpose**: Image analysis with fallback chain
- **Key Classes**:
  - `LightweightCaptionModel` (line 32): BLIP-2 captioning model wrapper
  - `SimpleImageAnalyzer` (line 157): Orchestrates fallback chain
- **Key Functions**:
  - `analyze_image()`: Fallback chain: OpenAI Vision → Local BLIP-2 → Metadata
  - `scan_image_comprehensively()`: Comprehensive analysis using BLIP-2 + CLIP
  - `get_blip2_analyzer()`: Returns singleton BLIP-2 analyzer
  - `get_clip_provider()`: Returns singleton CLIP embeddings provider

**`app/rag/vision_analyzer.py`**
- **Purpose**: OpenAI Vision API integration
- **Key Function**: `analyze_image_with_vision()` - Encodes image to base64, calls OpenAI Vision API, extracts structured data

**`app/rag/groq_client.py`**
- **Purpose**: Groq API and local LLM clients
- **Key Classes**: `GroqLlmClient`, `LocalLlmClient` - Both implement `LlmClient` interface

#### Embeddings (`/app/embeddings/`)

**`app/embeddings/provider.py`** (Lines 1-212)
- **Purpose**: Embedding provider abstraction
- **Key Classes**:
  - `EmbeddingsProvider` (abstract, line 16): Interface with `embed_query()` and `embed_documents()`
  - `OpenAIEmbeddingsProvider` (line 46): OpenAI embeddings implementation
- **Key Functions**:
  - `_build_embeddings_provider()` (line 150): Factory function, selects OpenAI or HuggingFace based on config
  - `get_embeddings_provider()` (line 194): FastAPI dependency

**`app/embeddings/huggingface.py`**
- **Purpose**: HuggingFace sentence-transformers implementation
- **Key Class**: `HuggingFaceEmbeddingsProvider` - Uses sentence-transformers library

**`app/embeddings/image_provider.py`**
- **Purpose**: CLIP image embeddings
- **Key Class**: `CLIPImageEmbeddingsProvider` - Generates 512-dim embeddings for images

#### Vector Store (`/app/vectorstore/`)

**`app/vectorstore/faiss_store.py`** (Lines 1-325)
- **Purpose**: FAISS-based vector store with per-user indexes
- **Key Class**: `VectorStore` (line 36)
- **Key Methods**:
  - `add_document_chunks()` (line 70): Adds embeddings to user's FAISS index, maintains chunk_id mapping in `meta.npy`
  - `search()` (line 158): Searches user's index for top-k nearest neighbors, returns `VectorHit(chunk_id, score)`
  - `remove_document_chunks()` (line 220): Rebuilds index without specified chunks
- **Storage**: Per-user indexes at `data/vectorstores/user_{user_id}/index.faiss` and `meta.npy`
- **Index Type**: `faiss.IndexFlatL2` (exact L2 distance search)
- **Factory Functions**:
  - `_build_vector_store()` (line 289): Creates VectorStore instance
  - `get_vector_store()` (line 301): FastAPI dependency

**`app/vectorstore/pinecone_store.py`**
- **Purpose**: Pinecone cloud vector store implementation (alternative to FAISS)

**`app/vectorstore/chroma_store.py`**
- **Purpose**: ChromaDB vector store implementation (alternative to FAISS)

#### Chat System (`/app/chat/`)

**`app/chat/routes.py`** (Lines 1-296)
- **Purpose**: Chat API endpoints
- **Endpoints**:
  - `POST /chat/sessions` (line 43): Create chat session
  - `GET /chat/sessions` (line 64): List all user sessions
  - `GET /chat/sessions/{session_id}` (line 83): Get messages for session
  - `POST /chat/sessions/{session_id}/message` (line 203): **CRITICAL** - Send message, triggers RAG pipeline
  - `DELETE /chat/sessions/{session_id}` (line 179): Delete session
  - `DELETE /chat/sessions/all` (line 158): Delete all chat history
- **Key Endpoint**: `send_message()` (line 207)
  - Creates RagChain instance
  - Calls `handle_user_message()` which runs full RAG pipeline
  - Returns assistant message with citations

**`app/chat/service.py`**
- **Purpose**: Chat business logic
- **Key Functions**:
  - `create_chat_session()`: Creates new ChatSession
  - `handle_user_message()`: Creates user message, runs RAG chain, creates assistant message
  - `list_messages_for_session()`: Gets all messages for a session
  - `delete_chat_session()`: Deletes session and messages

**`app/chat/history.py`**
- **Purpose**: Chat history management
- **Key Function**: `get_recent_messages()` - Fetches recent messages for context, excludes specified message ID

#### Utilities (`/app/utils/`)

**`app/utils/middleware.py`**
- **Purpose**: Custom FastAPI middleware
- **Key Classes**:
  - `RequestIDMiddleware`: Adds unique request ID to each request
  - `LoggingMiddleware`: Logs request/response details

**`app/utils/retry.py`**
- **Purpose**: Retry logic for async and sync operations
- **Key Functions**: `retry_async()`, `retry_sync()` - Retry with exponential backoff

**`app/utils/validation.py`**
- **Purpose**: Input validation utilities
- **Key Functions**: `validate_file_extension()`, `validate_file_size()`, `validate_mime_type()`, `validate_password()`

**`app/utils/exceptions.py`**
- **Purpose**: Custom exception classes
- **Key Class**: `RAGWorkspaceException` - Base exception for application errors

**`app/utils/security.py`**
- **Purpose**: Security utilities (password hashing, etc.)

#### Storage (`/app/storage/`)

**`app/storage/s3_storage.py`**
- **Purpose**: S3 storage implementation (alternative to local filesystem)
- **Key Class**: `S3Storage` - Uses boto3 for S3 operations

#### Telemetry (`/app/telemetry/`)

**`app/telemetry/logging.py`**
- **Purpose**: Application logging configuration
- **Key Function**: `setup_logging()` - Configures Python logging, sets levels, suppresses verbose third-party logs

#### Admin (`/app/admin/`)

**`app/admin/routes.py`**
- **Purpose**: Admin API endpoints (if needed)

---

### Frontend (`/frontend/`)

#### Core Application Files

**`frontend/src/App.tsx`** (Lines 1-87)
- **Purpose**: Main React application component
- **Key Features**:
  - Backend health check on mount (lines 22-40)
  - Shows backend status banner (lines 67-76)
  - Protected routes with `ProtectedRoute` wrapper (line 65)
  - Layout: Navbar + Sidebar + main content area (lines 77-83)
  - Sidebar items: Documents, Chat Assistant (lines 10-13)

**`frontend/src/main.tsx`**
- **Purpose**: React application entry point
- **Key**: Renders App component, sets up React Router

**`frontend/src/router.tsx`**
- **Purpose**: React Router configuration
- **Routes**: `/login`, `/documents`, `/chat`, `/chat/:sessionId`

#### API Client (`/frontend/src/api/`)

**`frontend/src/api/client.ts`** (Lines 1-220)
- **Purpose**: Centralized API client for backend communication
- **Key Class**: `ApiClient`
- **Key Methods**:
  - `request<T>()` (line 23): Core request method, handles JWT tokens, CORS, error handling
  - `get()`, `post()`, `put()`, `delete()`, `patch()`: HTTP method wrappers
  - `postFormData()` (line 156): Special method for file uploads with 6-minute timeout
- **Features**:
  - Auto-injects JWT token from localStorage (line 19)
  - Handles 401 by redirecting to login (lines 79-85)
  - Network/CORS error handling (lines 96-113)
  - Base URL: `http://127.0.0.1:8000` (configurable via `VITE_API_BASE_URL`)

**`frontend/src/api/authApi.ts`**
- **Purpose**: Authentication API endpoints
- **Functions**: `signup()`, `login()`, `getCurrentUser()`, `updateUser()`, `changePassword()`, `deleteAccount()`

**`frontend/src/api/documentApi.ts`**
- **Purpose**: Document API endpoints
- **Functions**: `uploadDocuments()`, `listDocuments()`, `getDocument()`, `deleteDocument()`

**`frontend/src/api/chatApi.ts`**
- **Purpose**: Chat API endpoints
- **Functions**: `createSession()`, `listSessions()`, `getSessionMessages()`, `sendMessage()`, `deleteSession()`, `deleteAllSessions()`

#### Components (`/frontend/src/components/`)

**Layout Components**:
- `Navbar.tsx`: Top navigation bar with user menu and logout
- `Sidebar.tsx`: Left sidebar with navigation links
- `ProtectedRoute.tsx`: Wrapper that redirects to login if not authenticated

**Auth Components**:
- `LoginForm.tsx`: Login/signup form component

**Document Components**:
- `DocumentUpload.tsx`: File upload component with drag-and-drop
- `DocumentList.tsx`: List of user documents with status indicators
- `DocumentCard.tsx`: Individual document card component

**Chat Components**:
- `ChatInterface.tsx`: Main chat interface with message list and input
- `ChatMessage.tsx`: Individual message component (user/assistant)
- `ChatHistory.tsx`: Sidebar chat history list
- `MessageInput.tsx`: Chat input component

**Common Components**:
- `LoadingSpinner.tsx`: Loading indicator
- `ErrorBanner.tsx`: Error message display
- `ConfirmDialog.tsx`: Confirmation modal for delete actions

#### Pages (`/frontend/src/pages/`)

- `LoginPage.tsx`: Login/signup page
- `DocumentsPage.tsx`: Documents management page
- `ChatPage.tsx`: Chat interface page

#### Hooks (`/frontend/src/hooks/`)

**`frontend/src/hooks/useAuth.ts`**
- **Purpose**: Authentication state management hook
- **Key Features**:
  - Manages user state and JWT token in localStorage
  - `login()`, `signup()`, `logout()` functions
  - `fetchCurrentUser()`: Fetches current user from `/auth/me`
  - Auto-redirects to login on 401

#### Contexts (`/frontend/src/contexts/`)

- `ThemeContext.tsx`: Dark mode theme management

#### Styles (`/frontend/src/styles/`)

- `globals.css`: Global styles, Tailwind directives

---

## 🔄 DATA FLOW AND PIPELINES

### Document Upload Pipeline

1. **User uploads file** → `POST /documents/upload` (`app/documents/routes.py:44`)
2. **Validation** → File extension, size, MIME type checked (`app/documents/routes.py:87-123`)
3. **Processing** → `process_and_index_document()` (`app/documents/service.py:100`)
   - Save file to disk: `storage/user_{user_id}/uploads/` (`service.py:29`)
   - Create Document record with status=UPLOADING (`service.py:64`)
   - Set status=INDEXING (`service.py:158`)
   - Extract text: `extract_text_from_file()` (`app/documents/parsers.py`)
   - **If image**: Process with BLIP-2 + CLIP (`service.py:187-269`)
   - Chunk text: `chunk_text()` (`app/documents/chunking.py`)
   - Create DocumentChunk rows (`service.py:314-339`)
   - Generate embeddings: `embeddings_provider.embed_documents()` (`app/embeddings/provider.py:107`)
   - Add to vector store: `vector_store.add_document_chunks()` (`app/vectorstore/faiss_store.py:70`)
   - Set status=READY (`service.py:408`)
4. **Error Handling**: Any exception → Document marked as FAILED (`service.py:439-489`)

### RAG Query Pipeline

1. **User sends message** → `POST /chat/sessions/{session_id}/message` (`app/chat/routes.py:203`)
2. **Create user message** → `handle_user_message()` (`app/chat/service.py`)
3. **RAG Chain** → `RagChain.answer_question()` (`app/rag/chain.py:127`)
   - **Embed query**: `embeddings_provider.embed_query(question)` (`chain.py:161`)
   - **Search vector store**: `vector_store.search(query_vector, k=10)` (`chain.py:166`)
   - **Fetch chunks**: Query DocumentChunk table with chunk_ids (`chain.py:327`)
   - **Build context**: `build_context(chunks, hits)` (`app/rag/context_builder.py`)
   - **Image analysis** (if applicable): `analyze_image()` (`app/rag/image_analyzer.py`)
   - **Fetch history**: `get_recent_messages(session, limit=10)` (`app/chat/history.py`)
   - **Build messages**: `build_messages(context, history, question)` (`app/rag/prompts.py:125`)
   - **Call LLM**: `llm_client.generate(messages)` (`chain.py:558`)
4. **Create assistant message** → Save to database with citations
5. **Return response** → Frontend displays message with citations

### Image Analysis Pipeline

1. **During Upload** (`app/documents/service.py:187-269`):
   - Extract metadata: `extract_text_from_image()` (`app/documents/parsers.py`)
   - BLIP-2 caption: `blip2.generate_caption()` (`app/rag/image_analyzer.py:66`)
   - BLIP-2 description: `blip2.generate_detailed_description()` (`app/rag/image_analyzer.py`)
   - CLIP embedding: `clip.embed_image()` (`app/embeddings/image_provider.py`)
   - Store as text chunk with metadata

2. **During Chat** (`app/rag/chain.py:371-455`):
   - Detect image question by keywords (`chain.py:359-368`)
   - Find image file path from chunk metadata (`chain.py:383-401`)
   - Call `analyze_image()` which uses fallback chain:
     - **Primary**: OpenAI Vision API (`app/rag/vision_analyzer.py`)
     - **Fallback**: Local BLIP-2 (`app/rag/image_analyzer.py`)
     - **Last resort**: Metadata (`app/rag/image_analyzer.py:163`)

---

## 🗄️ DATABASE SCHEMA

### Tables (from `app/db/models.py`)

**`users`**:
- `id` (Integer, PK)
- `email` (String(255), unique, indexed)
- `hashed_password` (String(255))
- `created_at` (DateTime)

**`documents`**:
- `id` (Integer, PK)
- `user_id` (Integer, FK → users.id)
- `title` (String(255))
- `original_filename` (String(255))
- `status` (Enum: UPLOADING, INDEXING, READY, FAILED)
- `num_chunks` (Integer)
- `created_at`, `updated_at` (DateTime)

**`document_chunks`**:
- `id` (Integer, PK)
- `document_id` (Integer, FK → documents.id)
- `chunk_index` (Integer)
- `text` (Text)
- `token_count` (Integer)
- `metadata` (JSON) - Contains file_type, source_path, etc.

**`chat_sessions`**:
- `id` (Integer, PK)
- `user_id` (Integer, FK → users.id)
- `title` (String(255), nullable)
- `created_at` (DateTime)

**`chat_messages`**:
- `id` (Integer, PK)
- `session_id` (Integer, FK → chat_sessions.id)
- `role` (Enum: USER, ASSISTANT)
- `content` (Text)
- `retrieved_chunks` (JSON) - Array of citation objects
- `created_at` (DateTime)

**`refresh_tokens`**:
- `id` (Integer, PK)
- `user_id` (Integer, FK → users.id)
- `token` (String(512), unique, indexed)
- `expires_at` (DateTime)
- `created_at` (DateTime)

### Relationships

- User → Documents (one-to-many, cascade delete)
- User → ChatSessions (one-to-many, cascade delete)
- Document → DocumentChunks (one-to-many, cascade delete)
- ChatSession → ChatMessages (one-to-many, cascade delete)

---

## 🔌 API ENDPOINTS

### Authentication (`/auth`)

- `POST /auth/signup` - Create account (`app/auth/routes.py:24`)
- `POST /auth/login` - Login, get JWT (`app/auth/routes.py:74`)
- `GET /auth/me` - Get current user (`app/auth/routes.py:127`)
- `PUT /auth/me` - Update profile (`app/auth/routes.py:184`)
- `POST /auth/change-password` - Change password (`app/auth/routes.py:208`)
- `DELETE /auth/me` - Delete account (`app/auth/routes.py:237`)
- `POST /auth/refresh` - Refresh token (`app/auth/routes.py:146`)

### Documents (`/documents`)

- `POST /documents/upload` - Upload files (`app/documents/routes.py:44`)
- `GET /documents` - List documents (`app/documents/routes.py:185`)
- `GET /documents/{id}` - Get document (`app/documents/routes.py:204`)
- `DELETE /documents/{id}` - Delete document (`app/documents/routes.py:228`)

### Chat (`/chat`)

- `POST /chat/sessions` - Create session (`app/chat/routes.py:43`)
- `GET /chat/sessions` - List sessions (`app/chat/routes.py:64`)
- `GET /chat/sessions/{id}` - Get messages (`app/chat/routes.py:83`)
- `POST /chat/sessions/{id}/message` - Send message (RAG) (`app/chat/routes.py:203`)
- `DELETE /chat/sessions/{id}` - Delete session (`app/chat/routes.py:179`)
- `DELETE /chat/sessions/all` - Delete all history (`app/chat/routes.py:158`)

### Health

- `GET /health` - Health check (`app/main.py:255`)

---

## ⚙️ CONFIGURATION

### Environment Variables (`.env`)

**Required**:
- `DATABASE_URL`: PostgreSQL connection string
- `JWT_SECRET_KEY`: Secret for JWT signing
- `OPENAI_API_KEY` or `GROQ_API_KEY`: LLM provider API key

**Optional**:
- `LLM_PROVIDER`: `openai`, `groq`, or `local` (default: `openai`)
- `LLM_MODEL`: Model name (default: `gpt-4o-mini`)
- `EMBEDDINGS_PROVIDER`: `openai` or `huggingface` (default: `openai`)
- `EMBEDDINGS_MODEL`: Embedding model (default: `text-embedding-3-small`)
- `VECTORSTORE_PROVIDER`: `faiss`, `pinecone`, or `chroma` (default: `faiss`)
- `VECTORSTORE_BASE_DIR`: Directory for FAISS indexes (default: `data/vectorstores`)
- `STORAGE_BASE_DIR`: Directory for uploaded files (default: `storage`)
- `ENABLE_CAPTION_MODEL`: Enable local BLIP-2 (default: `false`)
- `CORS_ORIGINS`: Comma-separated origins (default: `*`)

---

## 🐛 COMMON DEBUGGING SCENARIOS

### 1. Document Stuck in INDEXING Status

**Location**: `app/documents/service.py:100-437`
**Issue**: Document status not updating to READY or FAILED
**Solution**: Check error handling in `process_and_index_document()`. All exceptions should mark document as FAILED (lines 439-489). Verify database commits are happening.

### 2. No Chunks Found in Vector Search

**Location**: `app/rag/chain.py:166-170`
**Issue**: `vector_store.search()` returns empty list
**Debug**:
- Check if user has documents: Query `documents` table for `user_id`
- Check if chunks exist: Query `document_chunks` table
- Check if FAISS index exists: `data/vectorstores/user_{user_id}/index.faiss`
- Check embedding dimension mismatch: FAISS index dimension must match embedding dimension

### 3. Image Analysis Not Working

**Location**: `app/rag/image_analyzer.py`
**Issue**: Images not being analyzed during chat
**Debug**:
- Check `OPENAI_API_KEY` is set (for Vision API)
- Check `ENABLE_CAPTION_MODEL=true` (for local BLIP-2)
- Check image file path exists: `storage/user_{user_id}/uploads/{filename}`
- Check image question detection: Keywords in `chain.py:359-368`

### 4. CORS Errors

**Location**: `app/main.py:48-55`
**Issue**: Frontend can't connect to backend
**Solution**: 
- Verify CORS origins include frontend URL (lines 32-44)
- Check `CORS_ORIGINS` environment variable
- Ensure CORS middleware is first (line 48)

### 5. Authentication Failures

**Location**: `app/auth/dependencies.py`
**Issue**: 401 Unauthorized errors
**Debug**:
- Check JWT token in request headers: `Authorization: Bearer {token}`
- Verify `JWT_SECRET_KEY` matches between requests
- Check token expiration: `ACCESS_TOKEN_EXPIRE_MINUTES`
- Verify user exists in database

### 6. Embedding Dimension Mismatch

**Location**: `app/vectorstore/faiss_store.py:114-118`
**Issue**: Error when adding embeddings: "Dimension mismatch"
**Solution**: 
- All embeddings must have same dimension
- OpenAI `text-embedding-3-small`: 1536 dimensions
- HuggingFace `all-MiniLM-L6-v2`: 384 dimensions
- Cannot mix different embedding models for same user

### 7. LLM Not Responding

**Location**: `app/rag/chain.py:558`
**Issue**: LLM call fails or times out
**Debug**:
- Check `OPENAI_API_KEY` or `GROQ_API_KEY` is set
- Check `LLM_PROVIDER` setting matches available API key
- Check timeout middleware: Chat endpoints have 120s timeout (`app/main.py:100-111`)
- Check network connectivity to LLM API

---

## 🔧 HOW TO MAKE CHANGES

### Adding a New File Type Parser

1. **Add parser function** in `app/documents/parsers.py`:
   ```python
   def extract_text_from_newtype(path: Path) -> Tuple[str, Dict[str, Any]]:
       # Parse file, return (text, metadata)
   ```

2. **Add to router** in `extract_text_from_file()` (`parsers.py`):
   ```python
   elif suffix == ".newtype":
       return extract_text_from_newtype(path)
   ```

3. **Update allowed extensions** in `app/config.py:57`:
   ```python
   allowed_file_extensions: str = "...existing...,.newtype"
   ```

### Changing Chunking Strategy

**Location**: `app/documents/chunking.py`
- Modify `chunk_text()` function
- Change `max_words` or `overlap_words` parameters
- Update calls in `app/documents/service.py:304` (text) and `service.py:288` (images)

### Adding a New LLM Provider

1. **Create client class** in `app/rag/` (e.g., `new_provider_client.py`):
   ```python
   class NewProviderLlmClient(LlmClient):
       async def generate(self, messages: List[Dict[str, str]]) -> str:
           # Implementation
   ```

2. **Update factory** in `app/rag/chain.py:622`:
   ```python
   if settings.llm_provider == "newprovider":
       return NewProviderLlmClient(...)
   ```

3. **Add config** in `app/config.py`:
   ```python
   new_provider_api_key: Optional[str] = None
   ```

### Changing Vector Store Provider

1. **Update config** in `app/config.py:50`:
   ```python
   vectorstore_provider: str = "pinecone"  # or "chroma"
   ```

2. **Update factory** in `app/vectorstore/faiss_store.py:301` (or create new factory):
   - Check `vectorstore_provider` setting
   - Return appropriate VectorStore implementation

### Modifying RAG Pipeline

**Location**: `app/rag/chain.py:127` (`RagChain.answer_question()`)
- Steps are numbered 1-9 in comments
- Modify specific step as needed
- Ensure return format: `(answer: str, citations: List[Dict], analysis_info: Dict)`

### Adding New API Endpoint

1. **Add route function** in appropriate router file (`app/{module}/routes.py`)
2. **Add to router** if needed: `router.add_api_route(...)`
3. **Add to frontend API client** (`frontend/src/api/{module}Api.ts`)
4. **Add frontend component** if needed

### Changing Authentication Flow

**Location**: `app/auth/`
- JWT creation: `app/auth/jwt.py`
- Token validation: `app/auth/dependencies.py:get_current_user()`
- Password hashing: `app/auth/service.py` (uses `passlib[bcrypt]`)

---

## 📊 KEY METRICS AND LIMITS

- **Max file size**: 50MB (`app/config.py:56`)
- **Chunk size**: 200 words for text, 500 words for images (`app/documents/service.py:304, 288`)
- **Top-k retrieval**: 10 chunks default (`app/rag/chain.py:133`)
- **Chat history**: Last 10 messages (`app/rag/chain.py:545`)
- **Timeout**: 300s uploads, 120s chat, 30s others (`app/main.py:86, 103, 116`)
- **Embedding dimensions**: OpenAI 1536, HuggingFace 384
- **JWT expiration**: 1440 minutes (24 hours) default (`app/config.py:24`)

---

## 🔐 SECURITY CONSIDERATIONS

- **Password hashing**: bcrypt with 12 rounds (`app/auth/service.py`)
- **JWT tokens**: Signed with `JWT_SECRET_KEY`, validated on every request
- **User isolation**: All queries filtered by `user_id`, per-user FAISS indexes
- **File uploads**: Extension whitelist, size limits, safe filename generation
- **SQL injection**: SQLAlchemy ORM with parameterized queries
- **CORS**: Configurable allowed origins

---

## 🚀 DEPLOYMENT NOTES

- **Database migrations**: Use Alembic (`alembic upgrade head`)
- **Production settings**: Set `ENVIRONMENT=prod` in `.env`
- **Static files**: Frontend built with Vite, served from `frontend/dist/`
- **Backend server**: Use Gunicorn with multiple workers in production
- **Vector store**: FAISS indexes stored on disk, ensure `data/vectorstores/` is persistent
- **File storage**: Ensure `storage/` directory is persistent or use S3

---

## 📝 INTERVIEW TIPS

When asked about:
- **Architecture**: Mention separation of concerns (routes → service → models), dependency injection pattern, per-user data isolation
- **RAG Pipeline**: Explain embedding → search → retrieve → context building → LLM generation flow
- **Error Handling**: Document status guarantees (always READY or FAILED), comprehensive exception handling
- **Scalability**: Per-user indexes allow horizontal scaling, can switch to Pinecone for managed vector DB
- **Image Analysis**: Fallback chain (OpenAI → BLIP-2 → Metadata), stored analysis vs real-time analysis
- **Security**: JWT authentication, user isolation, input validation, SQL injection prevention

**Key Files to Reference**:
- RAG Pipeline: `app/rag/chain.py:127` (`answer_question()`)
- Document Processing: `app/documents/service.py:100` (`process_and_index_document()`)
- Vector Search: `app/vectorstore/faiss_store.py:158` (`search()`)
- Image Analysis: `app/rag/image_analyzer.py` (`analyze_image()`)
- Authentication: `app/auth/dependencies.py` (`get_current_user()`)

---

**END OF TECHNICAL REFERENCE**

