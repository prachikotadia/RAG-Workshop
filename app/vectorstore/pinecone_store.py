"""Pinecone vector store implementation."""
from typing import List, Optional
import logging

try:
    import pinecone
    from pinecone import Pinecone, ServerlessSpec
except ImportError:
    pinecone = None
    logging.warning("Pinecone not installed. Install with: pip install pinecone-client")

from app.config import get_settings
from app.utils.exceptions import VectorStoreError
from app.vectorstore.faiss_store import VectorStoreHit

logger = logging.getLogger(__name__)
settings = get_settings()


class PineconeVectorStore:
    """Pinecone-based vector store."""
    
    def __init__(self, user_id: int):
        if pinecone is None:
            raise VectorStoreError("Pinecone not installed")
        
        if not settings.pinecone_api_key:
            raise VectorStoreError("Pinecone API key not configured")
        
        self.user_id = user_id
        self.pc = Pinecone(api_key=settings.pinecone_api_key)
        self.index_name = settings.pinecone_index_name or f"rag-workspace-{user_id}"
        self.dimension = 384  # Default for all-MiniLM-L6-v2, adjust based on model
        self._ensure_index()
    
    def _ensure_index(self):
        """Ensure the index exists."""
        try:
            if self.index_name not in [idx.name for idx in self.pc.list_indexes()]:
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region=settings.pinecone_environment or "us-east-1"
                    )
                )
                logger.info(f"Created Pinecone index: {self.index_name}")
        except Exception as e:
            logger.error(f"Error ensuring Pinecone index: {e}")
            raise VectorStoreError(f"Failed to ensure Pinecone index: {e}")
    
    def add_vectors(self, chunk_ids: List[int], vectors: List[List[float]]):
        """Add vectors to the index."""
        if not vectors:
            return
        
        index = self.pc.Index(self.index_name)
        
        # Prepare vectors with IDs
        vectors_to_upsert = [
            (f"{self.user_id}_{chunk_id}", vector)
            for chunk_id, vector in zip(chunk_ids, vectors)
        ]
        
        # Upsert in batches
        batch_size = 100
        for i in range(0, len(vectors_to_upsert), batch_size):
            batch = vectors_to_upsert[i:i + batch_size]
            index.upsert(vectors=batch)
        
        logger.info(f"Added {len(chunk_ids)} vectors to Pinecone index")
    
    def remove_chunks(self, chunk_ids: List[int]):
        """Remove chunks from the index."""
        if not chunk_ids:
            return
        
        index = self.pc.Index(self.index_name)
        ids_to_delete = [f"{self.user_id}_{chunk_id}" for chunk_id in chunk_ids]
        index.delete(ids=ids_to_delete)
        logger.info(f"Removed {len(chunk_ids)} chunks from Pinecone index")
    
    def search(self, query_vector: List[float], k: int = 10) -> List[VectorStoreHit]:
        """Search for similar vectors."""
        index = self.pc.Index(self.index_name)
        
        # Filter by user_id using metadata
        results = index.query(
            vector=query_vector,
            top_k=k,
            filter={"user_id": {"$eq": self.user_id}},
            include_metadata=True
        )
        
        hits = []
        for match in results.matches:
            # Extract chunk_id from Pinecone ID (format: user_id_chunk_id)
            chunk_id_str = match.id.split("_")[-1]
            try:
                chunk_id = int(chunk_id_str)
                hits.append(VectorStoreHit(chunk_id=chunk_id, score=float(match.score)))
            except ValueError:
                logger.warning(f"Invalid chunk ID format: {match.id}")
        
        return hits

