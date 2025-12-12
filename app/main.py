# Set thread limits to prevent OpenMP crashes
import os
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')
os.environ.setdefault('NUMEXPR_NUM_THREADS', '1')
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')

from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import logging
import time

from app.telemetry.logging import setup_logging
from app.auth.routes import router as auth_router
from app.documents.routes import router as documents_router
from app.documents import preview_routes, tag_routes
from app.chat.routes import router as chat_router
from app.chat import shared_routes
from app.admin.routes import router as admin_router
from app.admin.gdpr_routes import router as gdpr_router
from app.admin.monitoring_routes import router as monitoring_router
from app.admin.webhook_routes import router as webhook_router
from app.chat.feedback_routes import router as feedback_router
from app.utils.monitoring import PerformanceMonitoringMiddleware
from app.utils.exceptions import RAGWorkspaceException
from app.utils.middleware import RequestIDMiddleware, LoggingMiddleware
from app.utils.rate_limit import RateLimitMiddleware
from app.utils.user_state_middleware import UserStateMiddleware
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def create_app() -> FastAPI:
    # Create FastAPI app with all routes and middleware
    setup_logging()
    app = FastAPI(
        title="Prachi RAG Workspace API",
        version="1.0.0",
        description="""
        End-to-end RAG platform for personal knowledge assistants.
        
        ## Features
        
        * **Document Management**: Upload and index PDFs, text files, and images
        * **RAG Chat**: Ask questions and get answers based on your documents
        * **Advanced RAG**: Hybrid search, query expansion, re-ranking
        * **Analytics**: Usage metrics and insights
        * **Multi-modal**: Support for images, documents, and more
        
        ## Authentication
        
        All endpoints require authentication except `/auth/signup` and `/auth/login`.
        Use the `/auth/login` endpoint to get an access token, then include it in the Authorization header:
        
        ```
        Authorization: Bearer <your_token>
        ```
        """,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS setup - allow frontend to access API
    if settings.environment == "dev":
        # Allow localhost on common dev ports
        cors_origins = []
        for port in range(3000, 3011):
            cors_origins.extend([f"http://127.0.0.1:{port}", f"http://localhost:{port}"])
        for port in range(5173, 5181):
            cors_origins.extend([f"http://127.0.0.1:{port}", f"http://localhost:{port}"])
        for port in [8080, 8081, 8082, 5000, 5001, 4000, 4001]:
            cors_origins.extend([f"http://127.0.0.1:{port}", f"http://localhost:{port}"])
        logger.info(f"CORS configured for dev mode - {len(cors_origins)} origins")
    else:
        cors_origins = [
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:5173",
        ]
        if settings.cors_origins != "*" and settings.cors_origins:
            additional = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
            cors_origins.extend(additional)
        logger.info(f"CORS configured for production")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    
    # Extra CORS handling for dev mode
    if settings.environment == "dev":
        from starlette.middleware.base import BaseHTTPMiddleware as BaseMiddleware
        
        class DevCORSMiddleware(BaseMiddleware):
            # Allow any localhost origin in dev
            async def dispatch(self, request, call_next):
                origin = request.headers.get("origin")
                
                # Allow any localhost or 127.0.0.1 origin in dev mode
                if origin and (origin.startswith("http://localhost:") or 
                              origin.startswith("http://127.0.0.1:") or
                              origin.startswith("https://localhost:") or
                              origin.startswith("https://127.0.0.1:")):
                    response = await call_next(request)
                    # Add CORS headers if not already present
                    if "Access-Control-Allow-Origin" not in response.headers:
                        response.headers["Access-Control-Allow-Origin"] = origin
                        response.headers["Access-Control-Allow-Credentials"] = "true"
                        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
                        response.headers["Access-Control-Allow-Headers"] = "*"
                    return response
                
                return await call_next(request)
        
        app.add_middleware(DevCORSMiddleware)
    
    # Request ID middleware (after CORS)
    app.add_middleware(RequestIDMiddleware)
    
    # User state middleware (extracts user_id from JWT for rate limiting)
    app.add_middleware(UserStateMiddleware)
    
    # Logging middleware
    app.add_middleware(LoggingMiddleware)
    
    # Rate limiting middleware (after logging, before timeout)
    # Configure limits: 60 requests/minute, 1000 requests/hour per user
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=60,
        requests_per_hour=1000
    )
    
    # Performance monitoring middleware
    app.add_middleware(PerformanceMonitoringMiddleware)
    
    # Timeout middleware for long-running requests
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    
    def add_cors_to_timeout_response(response: JSONResponse, request: Request) -> JSONResponse:
        """Add CORS headers to timeout responses."""
        origin = request.headers.get("origin")
        if settings.environment == "dev":
            if origin and any(origin.startswith(f"http://{host}") or origin.startswith(f"https://{host}") 
                           for host in ["localhost", "127.0.0.1"]):
                response.headers["Access-Control-Allow-Origin"] = origin
            else:
                response.headers["Access-Control-Allow-Origin"] = "*"
        elif origin and origin in cors_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response
    
    class TimeoutMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            # Set a longer timeout for upload endpoints only
            if request.url.path.startswith("/documents/upload"):
                # Allow up to 100 seconds for upload (matches processing timeout 90s + buffer)
                import asyncio
                try:
                    response = await asyncio.wait_for(call_next(request), timeout=100.0)
                    return response
                except asyncio.TimeoutError:
                    logger.error(f"Request timeout for {request.url.path}")
                    timeout_response = JSONResponse(
                        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                        content={"detail": "Request timeout after 100 seconds. Document processing exceeded the time limit. The document may still be processing in the background - please refresh to check status."}
                    )
                    return add_cors_to_timeout_response(timeout_response, request)
            elif request.url.path.startswith("/chat/"):
                # Chat endpoints may do image analysis, allow up to 2 minutes
                import asyncio
                try:
                    response = await asyncio.wait_for(call_next(request), timeout=120.0)
                    return response
                except asyncio.TimeoutError:
                    logger.error(f"Request timeout for {request.url.path}")
                    timeout_response = JSONResponse(
                        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                        content={"detail": "Request timeout. Image analysis or processing took too long."}
                    )
                    return add_cors_to_timeout_response(timeout_response, request)
            elif request.url.path.startswith("/auth/"):
                # Auth endpoints (login, signup, etc.) - longer timeout to handle busy backend
                import asyncio
                try:
                    response = await asyncio.wait_for(call_next(request), timeout=60.0)
                    return response
                except asyncio.TimeoutError:
                    logger.error(f"Request timeout for {request.url.path}")
                    timeout_response = JSONResponse(
                        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                        content={"detail": "Request timeout. Backend may be busy. Please try again."}
                    )
                    return add_cors_to_timeout_response(timeout_response, request)
            else:
                # For other endpoints, use shorter timeout (30 seconds)
                import asyncio
                try:
                    response = await asyncio.wait_for(call_next(request), timeout=30.0)
                    return response
                except asyncio.TimeoutError:
                    logger.error(f"Request timeout for {request.url.path}")
                    timeout_response = JSONResponse(
                        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                        content={"detail": "Request timeout. Please try again."}
                    )
                    return add_cors_to_timeout_response(timeout_response, request)
    
    app.add_middleware(TimeoutMiddleware)
    
    # Helper function to add CORS headers to responses
    def add_cors_headers(response: JSONResponse, request: Request) -> JSONResponse:
        """Add CORS headers to a response based on the request origin."""
        origin = request.headers.get("origin")
        if settings.environment == "dev":
            # In dev, always allow localhost origins
            if origin and any(origin.startswith(f"http://{host}") or origin.startswith(f"https://{host}") 
                           for host in ["localhost", "127.0.0.1"]):
                response.headers["Access-Control-Allow-Origin"] = origin
            elif not origin:
                # No origin header, allow all in dev
                response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "*"
        else:
            # In prod, only allow configured origins
            if origin and origin in cors_origins:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
                response.headers["Access-Control-Allow-Headers"] = "*"
        return response

    # Global exception handlers
    # IMPORTANT: HTTPException handler must come before general Exception handler
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTPException and ensure CORS headers are included."""
        logger.warning(f"HTTPException: {exc.status_code} - {exc.detail}")
        response = JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers if hasattr(exc, 'headers') and exc.headers else {}
        )
        # CRITICAL: Always add CORS headers to HTTPException responses
        response = add_cors_headers(response, request)
        logger.info(f"HTTPException response with CORS headers: {response.status_code}")
        return response
    
    @app.exception_handler(RAGWorkspaceException)
    async def rag_exception_handler(request: Request, exc: RAGWorkspaceException):
        logger.error(f"RAG Workspace error: {exc}", exc_info=True)
        response = JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)}
        )
        response = add_cors_headers(response, request)
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle FastAPI request validation errors (422)."""
        errors = exc.errors()
        logger.error(f"❌ Request validation error on {request.method} {request.url.path}: {errors}")
        logger.error(f"Request headers: {dict(request.headers)}")
        logger.error(f"Request content type: {request.headers.get('content-type', 'unknown')}")
        
        # Format error message for better frontend handling
        error_messages = []
        for error in errors:
            loc = " -> ".join(str(x) for x in error.get("loc", []))
            msg = error.get("msg", "Validation error")
            error_type = error.get("type", "unknown")
            error_messages.append(f"{loc}: {msg} (type: {error_type})")
        
        # Return 400 instead of 422 for better frontend compatibility
        response = JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "detail": {
                    "error": "request_validation_failed",
                    "message": "; ".join(error_messages),
                    "errors": errors,
                    "path": request.url.path
                }
            }
        )
        response = add_cors_headers(response, request)
        return response

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
        logger.error(f"Database error: {exc}", exc_info=True)
        response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Database error occurred"}
        )
        response = add_cors_headers(response, request)
        return response

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled error: {exc}", exc_info=True)
        
        # Capture in Sentry
        try:
            from app.utils.sentry_integration import capture_exception
            capture_exception(exc, contexts={"request": {
                "url": str(request.url),
                "method": request.method,
                "headers": dict(request.headers),
            }})
        except Exception:
            pass  # Don't fail if Sentry capture fails
        
        error_detail = str(exc)
        # Truncate very long error messages
        if len(error_detail) > 500:
            error_detail = error_detail[:500] + "..."
        response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"Internal server error: {error_detail}"}
        )
        # Always add CORS headers to all error responses
        response = add_cors_headers(response, request)
        return response

    @app.on_event("startup")
    async def startup_event():
        try:
            from app.utils.sentry_integration import init_sentry
            init_sentry(environment=settings.environment)
        except Exception as e:
            logger.warning(f"Failed to initialize Sentry: {e}")
        
        async def init_db():
            try:
                from app.db.base import engine, Base
                from app.db import models  # noqa: F401
                from app.db.feedback_models import AnswerFeedback  # noqa: F401
                from app.admin.webhooks import Webhook  # noqa: F401
                from app.db.shared_conversation_models import SharedConversation  # noqa: F401
                from app.db.tag_models import Tag, Category  # noqa: F401
                from app.db.saved_search_models import SavedSearch  # noqa: F401
                from app.db.ab_test_models import Experiment, ExperimentResult, ExperimentVariant  # noqa: F401
                from app.db.version_models import DocumentVersion, VersionDiff  # noqa: F401
                from app.db.organization_models import Organization, Workspace, OrganizationMember  # noqa: F401
                
                if settings.environment == "dev":
                    Base.metadata.create_all(bind=engine)
                    logger.info("Database tables initialized")
                else:
                    logger.info("Skipping table creation (use migrations in production)")
            except Exception as e:
                logger.error(f"Error initializing database: {e}")
        
        async def cleanup_stuck_docs():
            # Clean up any documents stuck in INDEXING status on startup
            try:
                from app.db.base import get_db
                from app.documents.service import cleanup_stuck_documents
                db = next(get_db())
                fixed = cleanup_stuck_documents(db, user=None, max_age_minutes=1)
                if fixed > 0:
                    logger.info(f"Cleaned up {fixed} stuck document(s) on startup")
                db.close()
            except Exception as e:
                logger.warning(f"Failed to cleanup stuck documents on startup: {e}")
        
        import asyncio
        asyncio.create_task(init_db())
        asyncio.create_task(cleanup_stuck_docs())

    # Explicit OPTIONS handler for all routes (CORS preflight)
    @app.options("/{full_path:path}")
    async def options_handler(request: Request):
        """Handle CORS preflight requests."""
        return JSONResponse(
            content={},
            headers={
                "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Max-Age": "3600",
            }
        )

    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(documents_router, prefix="/documents", tags=["documents"])
    app.include_router(preview_routes.router, prefix="/documents", tags=["documents"])
    app.include_router(tag_routes.router, prefix="/documents", tags=["documents"])
    app.include_router(chat_router, prefix="/chat", tags=["chat"])
    app.include_router(shared_routes.router, prefix="/chat", tags=["chat"])
    app.include_router(feedback_router, prefix="/chat", tags=["feedback"])
    app.include_router(admin_router, prefix="/admin", tags=["admin"])
    app.include_router(gdpr_router, prefix="/admin", tags=["gdpr"])
    app.include_router(monitoring_router, prefix="/admin", tags=["monitoring"])
    app.include_router(webhook_router, prefix="/admin", tags=["webhooks"])

    @app.get("/")
    async def root(request: Request):
        response = JSONResponse(content={"message": "Prachi RAG Workspace API", "version": "1.0.0"})
        return add_cors_headers(response, request)

    @app.get("/health")
    async def health(request: Request):
        """
        Detailed health check endpoint with dependency status.
        
        Returns:
            - status: Overall health status
            - database: Database connection status
            - vectorstore: Vector store status
            - timestamp: Current server time
        """
        from app.db.base import engine
        from sqlalchemy import text
        
        health_status = {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "dependencies": {}
        }
        
        # Check database
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            health_status["dependencies"]["database"] = {"status": "healthy"}
        except Exception as e:
            health_status["status"] = "degraded"
            health_status["dependencies"]["database"] = {
                "status": "unhealthy",
                "error": str(e)[:100]
            }
        
        # Check vector store
        try:
            from app.vectorstore.faiss_store import get_vector_store
            vector_store = get_vector_store()
            health_status["dependencies"]["vectorstore"] = {"status": "healthy"}
        except Exception as e:
            health_status["status"] = "degraded"
            health_status["dependencies"]["vectorstore"] = {
                "status": "unhealthy",
                "error": str(e)[:100]
            }
        
        # Check embeddings provider
        try:
            from app.embeddings.provider import get_embeddings_provider
            embeddings = get_embeddings_provider()
            health_status["dependencies"]["embeddings"] = {"status": "healthy"}
        except Exception as e:
            health_status["status"] = "degraded"
            health_status["dependencies"]["embeddings"] = {
                "status": "unhealthy",
                "error": str(e)[:100]
            }
        
        status_code = 200 if health_status["status"] == "ok" else 503
        response = JSONResponse(content=health_status, status_code=status_code)
        return add_cors_headers(response, request)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
