"""
Embedding provider abstraction.

Phase 5 spec: Pluggable interface for embedding text (OpenAI, HuggingFace, etc.).
"""
from abc import ABC, abstractmethod
from typing import List
import logging
from functools import lru_cache
from app.config import get_settings
from app.utils.retry import retry_async

logger = logging.getLogger(__name__)


class EmbeddingsProvider(ABC):
    """Abstract base class for embedding providers."""
    
    @abstractmethod
    async def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query string and return a vector.
        
        Args:
            text: Query text to embed
        
        Returns:
            List of floats representing the embedding vector
        """
        pass
    
    @abstractmethod
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed multiple documents and return a list of vectors.
        
        Args:
            texts: List of document texts to embed
        
        Returns:
            List of embedding vectors (each is a list of floats)
        """
        pass


class OpenAIEmbeddingsProvider(EmbeddingsProvider):
    """OpenAI embeddings provider implementation."""
    
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        """
        Initialize OpenAI embeddings provider.
        
        Args:
            api_key: OpenAI API key
            model: Embedding model name (default: text-embedding-3-small)
        """
        self._api_key = api_key
        self._model = model
        self._client = None
    
    def _get_client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self._api_key)
            except ImportError:
                raise ImportError("openai package not installed. Install with: pip install openai")
        return self._client
    
    async def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query string using OpenAI API.
        
        Args:
            text: Query text to embed
        
        Returns:
            Embedding vector as list of floats
        """
        if not text or not text.strip():
            logger.warning("Empty text provided to embed_query")
            # Return zero vector or raise error - for now, raise
            raise ValueError("Cannot embed empty text")
        
        client = self._get_client()
        
        async def _embed():
            import asyncio
            # OpenAI client is synchronous, so we need to run it in executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.embeddings.create(
                    model=self._model,
                    input=text
                )
            )
            return response.data[0].embedding
        
        try:
            return await retry_async(_embed, max_retries=3, exceptions=(Exception,))
        except Exception as e:
            logger.error(f"Error embedding query: {e}")
            raise
    
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed multiple documents using OpenAI API.
        
        Args:
            texts: List of document texts to embed
        
        Returns:
            List of embedding vectors (each is a list of floats)
        """
        if not texts:
            logger.warning("Empty texts list provided to embed_documents")
            return []
        
        # Filter out empty texts
        non_empty_texts = [t for t in texts if t and t.strip()]
        if not non_empty_texts:
            logger.warning("All texts are empty")
            return []
        
        client = self._get_client()
        
        async def _embed():
            import asyncio
            # OpenAI client is synchronous, so we need to run it in executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.embeddings.create(
                    model=self._model,
                    input=non_empty_texts
                )
            )
            return [item.embedding for item in response.data]
        
        try:
            return await retry_async(_embed, max_retries=3, exceptions=(Exception,))
        except Exception as e:
            logger.error(f"Error embedding documents: {e}")
            raise


# DI helpers for FastAPI dependency injection
@lru_cache
def _build_embeddings_provider() -> EmbeddingsProvider:
    """
    Build embeddings provider instance (cached).

    Returns:
        EmbeddingsProvider instance

    Raises:
        RuntimeError: If no embeddings provider is configured
    """
    settings = get_settings()
    
    # Check embeddings_provider setting first
    # If explicitly set to huggingface, use it (even if OpenAI key exists)
    if settings.embeddings_provider == "huggingface":
        try:
            from app.embeddings.huggingface import HuggingFaceEmbeddingsProvider
            return HuggingFaceEmbeddingsProvider(
                model_name=settings.huggingface_model,
                cache_dir=settings.huggingface_cache_dir
            )
        except ImportError as e:
            logger.warning(f"HuggingFace embeddings requested but not available: {e}")
            raise RuntimeError(
                "HuggingFace embeddings requested but sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
    
    # Try OpenAI as fallback
    if settings.openai_api_key:
        return OpenAIEmbeddingsProvider(
            api_key=settings.openai_api_key,
            model=settings.embeddings_model,
        )
    
    # If no provider configured, provide a helpful error message
    raise RuntimeError(
        "No embeddings provider configured. "
        "Please set one of: OPENAI_API_KEY (for OpenAI) or EMBEDDINGS_PROVIDER=huggingface (for HuggingFace). "
        "See .env.example for configuration options."
    )


def get_embeddings_provider() -> EmbeddingsProvider:
    """
    FastAPI dependency to get embeddings provider.
    
    Returns:
        EmbeddingsProvider instance (cached singleton)
    
    Raises:
        HTTPException: If embeddings provider cannot be configured
    """
    try:
        return _build_embeddings_provider()
    except RuntimeError as e:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Embeddings provider configuration error: {str(e)}"
        )

