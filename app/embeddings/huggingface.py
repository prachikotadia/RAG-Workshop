"""HuggingFace Sentence Transformers embedding provider."""
from typing import List
import logging
from app.embeddings.provider import EmbeddingsProvider
from app.utils.retry import retry_async

logger = logging.getLogger(__name__)


class HuggingFaceEmbeddingsProvider(EmbeddingsProvider):
    """HuggingFace Sentence Transformers embeddings provider."""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2", cache_dir: str = None):
        self.model_name = model_name
        self.cache_dir = cache_dir
        self._model = None
        self._tokenizer = None
    
    def _get_model(self):
        """Lazy initialization of the model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(
                    self.model_name,
                    cache_folder=self.cache_dir
                )
                logger.info(f"Loaded HuggingFace model: {self.model_name}")
            except ImportError:
                raise ImportError(
                    "sentence-transformers not installed. Install with: pip install sentence-transformers"
                )
        return self._model
    
    async def embed_query(self, text: str) -> List[float]:
        """Generate embedding for a query."""
        model = self._get_model()
        
        async def _embed():
            # Run in thread pool since SentenceTransformer is synchronous
            import asyncio
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None,
                lambda: model.encode(text, convert_to_numpy=True).tolist()
            )
            return embedding
        
        return await retry_async(_embed, max_retries=3, exceptions=(Exception,))
    
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple documents."""
        model = self._get_model()
        
        async def _embed():
            # Run in thread pool since SentenceTransformer is synchronous
            import asyncio
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                lambda: model.encode(texts, convert_to_numpy=True).tolist()
            )
            return embeddings
        
        return await retry_async(_embed, max_retries=3, exceptions=(Exception,))

