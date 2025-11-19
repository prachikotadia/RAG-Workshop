"""Custom exceptions for the application."""


class RAGWorkspaceException(Exception):
    """Base exception for RAG Workspace."""
    pass


class AuthenticationError(RAGWorkspaceException):
    """Authentication failed."""
    pass


class DocumentProcessingError(RAGWorkspaceException):
    """Error processing document."""
    pass


class VectorStoreError(RAGWorkspaceException):
    """Error with vector store operations."""
    pass


class EmbeddingError(RAGWorkspaceException):
    """Error generating embeddings."""
    pass

