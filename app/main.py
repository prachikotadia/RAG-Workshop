# CRITICAL: Set thread limits BEFORE importing any PyTorch/ML libraries
# This prevents OpenMP crashes from threading conflicts
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
import logging

from app.telemetry.logging import setup_logging
from app.auth.routes import router as auth_router
from app.documents.routes import router as documents_router
from app.chat.routes import router as chat_router
from app.admin.routes import router as admin_router
from app.utils.exceptions import RAGWorkspaceException
from app.utils.middleware import RequestIDMiddleware, LoggingMiddleware
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    setup_logging()
    app = FastAPI(
        title="Prachi RAG Workspace",
        version="1.0.0",
        description="End-to-end RAG platform for personal knowledge assistants"
    )

    # CORS middleware - MUST be first, before any other middleware
    # In dev mode, allow common localhost/127.0.0.1 origins (comprehensive port list)
    # In production, use configured origins
    if settings.environment == "dev":
        # In dev, allow common localhost and 127.0.0.1 origins with various ports
        # Generate common dev ports (3000-3010, 5173-5180, 8080-8090, etc.)
        cors_origins = []
        # Common Vite/React ports
        for port in range(3000, 3011):  # 3000-3010
            cors_origins.extend([
                f"http://127.0.0.1:{port}",
                f"http://localhost:{port}",
            ])
        # Vite default port range
        for port in range(5173, 5181):  # 5173-5180
            cors_origins.extend([
                f"http://127.0.0.1:{port}",
                f"http://localhost:{port}",
            ])
        # Other common dev ports
        for port in [8080, 8081, 8082, 5000, 5001, 4000, 4001]:
            cors_origins.extend([
                f"http://127.0.0.1:{port}",
                f"http://localhost:{port}",
            ])
        logger.info(f"CORS configured to allow localhost origins on common dev ports (dev mode) - {len(cors_origins)} origins")
    else:
        # In production, use explicit list
        cors_origins = [
            "http://127.0.0.1:3000",  # Frontend default port
            "http://127.0.0.1:3001",
            "http://127.0.0.1:5173",
            "http://localhost:3000",  # Keep for compatibility
            "http://localhost:3001",
            "http://localhost:5173",
        ]
        
        # Add any additional origins from config
        if settings.cors_origins != "*" and settings.cors_origins:
            additional = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
            cors_origins.extend(additional)
        
        logger.info(f"CORS configured with allowed origins: {cors_origins}")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    
    # Additional CORS handler for dev mode - allows any localhost/127.0.0.1 origin
    if settings.environment == "dev":
        from starlette.middleware.base import BaseHTTPMiddleware as BaseMiddleware
        
        class DevCORSMiddleware(BaseMiddleware):
            """Additional CORS middleware for dev mode to allow any localhost/127.0.0.1 origin."""
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
    
    # Logging middleware
    app.add_middleware(LoggingMiddleware)
    
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
                # Allow up to 25 seconds for upload (matches processing timeout + buffer)
                import asyncio
                try:
                    response = await asyncio.wait_for(call_next(request), timeout=25.0)
                    return response
                except asyncio.TimeoutError:
                    logger.error(f"Request timeout for {request.url.path}")
                    timeout_response = JSONResponse(
                        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                        content={"detail": "Request timeout. Document processing exceeded 30 seconds. The document may still be processing in the background - please refresh to check status."}
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
        logger.warning(f"Validation error: {exc.errors()}")
        response = JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors()}
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

    # Startup event - initialize database tables (for dev environment)
    # Run in background to not block startup
    @app.on_event("startup")
    async def startup_event():
        async def init_db():
            try:
                from app.db.base import engine, Base
                # Import all models to ensure they're registered with Base
                from app.db import models  # noqa: F401
                
                # Only create tables in dev environment
                if settings.environment == "dev":
                    Base.metadata.create_all(bind=engine)
                    logger.info("Database tables initialized (dev mode)")
                else:
                    logger.info("Skipping table creation (production mode - use migrations)")
            except Exception as e:
                logger.error(f"Error initializing database: {e}")
        
        # Run in background - don't block startup
        import asyncio
        asyncio.create_task(init_db())

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
    app.include_router(chat_router, prefix="/chat", tags=["chat"])
    app.include_router(admin_router, prefix="/admin", tags=["admin"])

    @app.get("/")
    async def root(request: Request):
        response = JSONResponse(content={"message": "Prachi RAG Workspace API", "version": "1.0.0"})
        return add_cors_headers(response, request)

    @app.get("/health")
    async def health(request: Request):
        """Simple health check endpoint - returns OK if server is running."""
        response = JSONResponse(content={"status": "ok"})
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
