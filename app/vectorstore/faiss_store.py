"""
FAISS-based vector store implementation.

Phase 5 spec: Per-user FAISS index with disk persistence and search capabilities.
"""
try:
    import faiss
    import numpy as np
    FAISS_AVAILABLE = True
except ImportError:
    faiss = None
    np = None
    FAISS_AVAILABLE = False

from pathlib import Path
from typing import List, NamedTuple
import logging
from functools import lru_cache

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class VectorHit(NamedTuple):
    """Represents a search hit from the vector store."""
    chunk_id: int
    score: float  # distance (L2) or similarity


# Backward compatibility alias
VectorStoreHit = VectorHit


class VectorStore:
    """FAISS-based vector store with per-user indexes."""
    
    def __init__(self, base_dir: str):
        """
        Initialize vector store with base directory.
        
        Args:
            base_dir: Base directory for storing indexes
        
        Raises:
            ImportError: If FAISS is not installed
        """
        if not FAISS_AVAILABLE:
            raise ImportError(
                "FAISS is not installed. Install with: pip install faiss-cpu or faiss-gpu"
            )
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_user_dir(self, user_id: int) -> Path:
        """Get directory for a specific user's index."""
        user_dir = self._base_dir / f"user_{user_id}"
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir
    
    def _get_index_path(self, user_id: int) -> Path:
        """Get path to FAISS index file for a user."""
        return self._get_user_dir(user_id) / "index.faiss"
    
    def _get_meta_path(self, user_id: int) -> Path:
        """Get path to metadata (mapping) file for a user."""
        return self._get_user_dir(user_id) / "meta.npy"
    
    def add_document_chunks(
        self,
        user_id: int,
        document_id: int,
        embeddings: List[List[float]],
        chunk_ids: List[int],
    ) -> None:
        """
        Add chunk embeddings for a document to the user's FAISS index.
        
        If the index exists, load it and append; otherwise, create a new one.
        Maintains a mapping from FAISS row to chunk_id using a NumPy array.
        
        Args:
            user_id: User ID
            document_id: Document ID (for logging)
            embeddings: List of embedding vectors (each is a list of floats)
            chunk_ids: List of chunk IDs corresponding to embeddings
        
        Raises:
            ImportError: If FAISS is not installed
        """
        if not FAISS_AVAILABLE:
            raise ImportError("FAISS is not installed. Install with: pip install faiss-cpu or faiss-gpu")
        if not embeddings or not chunk_ids:
            logger.warning(f"Empty embeddings or chunk_ids for document {document_id}")
            return
        
        if len(embeddings) != len(chunk_ids):
            raise ValueError(f"Mismatch: {len(embeddings)} embeddings but {len(chunk_ids)} chunk_ids")
        
        # Convert embeddings to numpy array
        emb_array = np.array(embeddings, dtype=np.float32)
        dimension = emb_array.shape[1]
        
        index_path = self._get_index_path(user_id)
        meta_path = self._get_meta_path(user_id)
        
        if index_path.exists() and meta_path.exists():
            # Load existing index and mapping
            try:
                index = faiss.read_index(str(index_path))
                existing_dimension = index.d
                
                if existing_dimension != dimension:
                    raise ValueError(
                        f"Dimension mismatch: existing index has {existing_dimension}, "
                        f"new embeddings have {dimension}"
                    )
                
                # Load existing mapping
                mapping_array = np.load(meta_path)
                mapping_chunk_ids = mapping_array.tolist()
                
                # Append new embeddings
                index.add(emb_array)
                
                # Extend mapping with new chunk_ids
                mapping_chunk_ids.extend(chunk_ids)
                
                # Save updated index and mapping
                faiss.write_index(index, str(index_path))
                np.save(meta_path, np.array(mapping_chunk_ids, dtype=np.int64))
                
                logger.info(
                    f"Added {len(chunk_ids)} vectors to existing index for user {user_id}, "
                    f"document {document_id}"
                )
            except Exception as e:
                logger.error(f"Error loading/updating index for user {user_id}: {e}")
                raise
        else:
            # Create new index
            index = faiss.IndexFlatL2(dimension)
            index.add(emb_array)
            
            # Create new mapping
            mapping_array = np.array(chunk_ids, dtype=np.int64)
            
            # Save index and mapping
            faiss.write_index(index, str(index_path))
            np.save(meta_path, mapping_array)
            
            logger.info(
                f"Created new index for user {user_id} with {len(chunk_ids)} vectors "
                f"for document {document_id}"
            )
    
    def search(
        self,
        user_id: int,
        query_vector: List[float],
        k: int = 10,
    ) -> List[VectorHit]:
        """
        Search the user's FAISS index for top-k nearest neighbors.
        
        Args:
            user_id: User ID
            query_vector: Query embedding vector
            k: Number of results to return
        
        Returns:
            List of VectorHit(chunk_id, score) results.
            If no index exists for the user, returns empty list.
        
        Raises:
            ImportError: If FAISS is not installed
        """
        if not FAISS_AVAILABLE:
            raise ImportError("FAISS is not installed. Install with: pip install faiss-cpu or faiss-gpu")
        index_path = self._get_index_path(user_id)
        meta_path = self._get_meta_path(user_id)
        
        if not index_path.exists() or not meta_path.exists():
            logger.debug(f"No index found for user {user_id}")
            return []
        
        try:
            # Load index and mapping
            index = faiss.read_index(str(index_path))
            mapping_array = np.load(meta_path)
            mapping_chunk_ids = mapping_array.tolist()
            
            if index.ntotal == 0:
                return []
            
            # Convert query vector to numpy array
            query_array = np.array([query_vector], dtype=np.float32)
            
            # Search
            k = min(k, index.ntotal)
            distances, indices = index.search(query_array, k)
            
            # Convert to VectorHit results
            hits = []
            for distance, idx in zip(distances[0], indices[0]):
                if idx == -1:  # FAISS returns -1 for empty slots
                    continue
                if idx < len(mapping_chunk_ids):
                    chunk_id = int(mapping_chunk_ids[idx])
                    # For L2 distance, lower is better (more similar)
                    # We keep it as distance, but you could convert to similarity: 1 / (1 + distance)
                    hits.append(VectorHit(chunk_id=chunk_id, score=float(distance)))
            
            return hits
        except Exception as e:
            logger.error(f"Error searching index for user {user_id}: {e}")
            return []
    
    def remove_document_chunks(
        self,
        user_id: int,
        document_chunk_ids: List[int]
    ) -> None:
        """
        Remove all entries for the given chunk IDs from the user's index.
        
        Implementation rebuilds the index without those entries.
        
        Args:
            user_id: User ID
            document_chunk_ids: List of chunk IDs to remove
        """
        if not document_chunk_ids:
            return
        
        index_path = self._get_index_path(user_id)
        meta_path = self._get_meta_path(user_id)
        
        if not index_path.exists() or not meta_path.exists():
            logger.debug(f"No index found for user {user_id} to remove chunks from")
            return
        
        try:
            # Load existing index and mapping
            index = faiss.read_index(str(index_path))
            mapping_array = np.load(meta_path)
            mapping_chunk_ids = mapping_array.tolist()
            
            # Filter out chunks to remove
            chunk_ids_to_remove = set(document_chunk_ids)
            filtered_vectors = []
            filtered_chunk_ids = []
            
            for faiss_idx, chunk_id in enumerate(mapping_chunk_ids):
                if chunk_id not in chunk_ids_to_remove:
                    # Reconstruct vector from index
                    vector = index.reconstruct(faiss_idx)
                    filtered_vectors.append(vector)
                    filtered_chunk_ids.append(chunk_id)
            
            if not filtered_vectors:
                # Empty index - delete files
                index_path.unlink()
                meta_path.unlink()
                logger.info(f"Removed all vectors for user {user_id}, deleted index")
                return
            
            # Rebuild index
            dimension = index.d
            new_index = faiss.IndexFlatL2(dimension)
            vectors_array = np.array(filtered_vectors, dtype=np.float32)
            new_index.add(vectors_array)
            
            # Save updated index and mapping
            faiss.write_index(new_index, str(index_path))
            np.save(meta_path, np.array(filtered_chunk_ids, dtype=np.int64))
            
            logger.info(
                f"Removed {len(document_chunk_ids)} chunks from index for user {user_id}, "
                f"remaining: {len(filtered_chunk_ids)}"
            )
        except Exception as e:
            logger.error(f"Error removing chunks from index for user {user_id}: {e}")
            raise


# DI helpers for FastAPI dependency injection
@lru_cache
def _build_vector_store() -> VectorStore:
    """
    Build vector store instance (cached).
    
    Returns:
        VectorStore instance
    """
    settings = get_settings()
    return VectorStore(base_dir=settings.vectorstore_base_dir)


def get_vector_store() -> VectorStore:
    """
    FastAPI dependency to get vector store.
    
    Returns:
        VectorStore instance (cached singleton)
    
    Raises:
        HTTPException: If FAISS is not installed or vector store cannot be created
    """
    try:
        return _build_vector_store()
    except ImportError as e:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector store error: {str(e)}. Please install FAISS with: pip install faiss-cpu"
        )
    except Exception as e:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector store configuration error: {str(e)}"
        )
