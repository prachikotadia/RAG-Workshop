"""ChromaDB vector store implementation."""
from typing import List
import logging
from pathlib import Path

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None
    logging.warning("ChromaDB not installed. Install with: pip install chromadb")

from app.config import get_settings
from app.utils.exceptions import VectorStoreError
from app.vectorstore.faiss_store import VectorStoreHit

logger = logging.getLogger(__name__)
settings = get_settings()


class ChromaVectorStore:
    """ChromaDB-based vector store."""
    
    def __init__(self, user_id: int):
        if chromadb is None:
            raise VectorStoreError("ChromaDB not installed")
        
        self.user_id = user_id
        persist_dir = Path(settings.chroma_persist_directory) / f"user_{user_id}"
        persist_dir.mkdir(parents=True, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=str(persist_dir),
            settings=Settings(anonymized_telemetry=False)
        )
        
        self.collection_name = f"user_{user_id}_chunks"
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"user_id": user_id}
        )
    
    def add_vectors(self, chunk_ids: List[int], vectors: List[List[float]]):
        """Add vectors to the collection."""
        if not vectors:
            return
        
        # Prepare IDs and metadata
        ids = [f"chunk_{chunk_id}" for chunk_id in chunk_ids]
        metadatas = [{"chunk_id": chunk_id, "user_id": self.user_id} for chunk_id in chunk_ids]
        
        # Add to collection
        self.collection.add(
            ids=ids,
            embeddings=vectors,
            metadatas=metadatas
        )
        
        logger.info(f"Added {len(chunk_ids)} vectors to ChromaDB collection")
    
    def remove_chunks(self, chunk_ids: List[int]):
        """Remove chunks from the collection."""
        if not chunk_ids:
            return
        
        ids_to_delete = [f"chunk_{chunk_id}" for chunk_id in chunk_ids]
        self.collection.delete(ids=ids_to_delete)
        logger.info(f"Removed {len(chunk_ids)} chunks from ChromaDB collection")
    
    def search(self, query_vector: List[float], k: int = 10) -> List[VectorStoreHit]:
        """Search for similar vectors."""
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=k,
            where={"user_id": self.user_id}
        )
        
        hits = []
        if results["ids"] and len(results["ids"][0]) > 0:
            for i, chunk_id_str in enumerate(results["ids"][0]):
                try:
                    # Extract chunk_id from metadata or ID
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    chunk_id = metadata.get("chunk_id")
                    if not chunk_id:
                        # Fallback: extract from ID
                        chunk_id = int(chunk_id_str.replace("chunk_", ""))
                    
                    score = 1.0 - results["distances"][0][i] if results["distances"] else 0.0
                    hits.append(VectorStoreHit(chunk_id=chunk_id, score=float(score)))
                except (ValueError, KeyError) as e:
                    logger.warning(f"Error parsing ChromaDB result: {e}")
        
        return hits

