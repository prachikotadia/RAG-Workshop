"""
Advanced RAG features:
- Hybrid search (vector + keyword/BM25)
- Query expansion
- Re-ranking with cross-encoder
- Multi-query retrieval
- Context compression
"""
import logging
from typing import List, Dict, Tuple, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
import re

from app.db import models
from app.vectorstore.faiss_store import VectorHit

logger = logging.getLogger(__name__)


def expand_query(question: str) -> List[str]:
    """
    Expand query with synonyms and variations.
    
    Simple implementation using common synonyms and question variations.
    In production, you could use WordNet, embeddings, or LLM-based expansion.
    
    Args:
        question: Original question
        
    Returns:
        List of expanded query variations
    """
    variations = [question]  # Always include original
    
    question_lower = question.lower()
    
    # Common synonym mappings
    synonyms = {
        "what": ["what is", "what are", "explain", "describe"],
        "how": ["how to", "how does", "how do"],
        "why": ["why is", "why are", "reason", "cause"],
        "when": ["when did", "when does", "when was"],
        "where": ["where is", "where are", "location"],
    }
    
    # Generate variations
    for word, syns in synonyms.items():
        if word in question_lower:
            for syn in syns:
                variation = question_lower.replace(word, syn)
                if variation != question_lower:
                    variations.append(variation)
    
    # Add question word variations
    if question_lower.startswith("what"):
        variations.append(question_lower.replace("what", "explain", 1))
        variations.append(question_lower.replace("what", "describe", 1))
    elif question_lower.startswith("how"):
        variations.append(question_lower.replace("how", "what is the process", 1))
    
    # Remove duplicates and limit
    unique_variations = []
    seen = set()
    for v in variations:
        v_clean = v.strip()
        if v_clean and v_clean not in seen:
            seen.add(v_clean)
            unique_variations.append(v_clean)
    
    return unique_variations[:5]  # Limit to 5 variations


def keyword_search(
    db: Session,
    user_id: int,
    query: str,
    top_k: int = 10
) -> List[Tuple[int, float]]:
    """
    Perform keyword-based search using text matching.
    
    Simple BM25-like scoring using term frequency.
    
    Args:
        db: Database session
        user_id: User ID
        query: Search query
        top_k: Number of results to return
        
    Returns:
        List of (chunk_id, score) tuples
    """
    # Extract keywords from query
    keywords = re.findall(r'\b\w+\b', query.lower())
    if not keywords:
        return []
    
    # Search chunks for keywords
    chunks = (
        db.query(models.DocumentChunk)
        .join(models.Document)
        .filter(models.Document.user_id == user_id)
        .all()
    )
    
    # Score chunks based on keyword matches
    scored_chunks = []
    for chunk in chunks:
        chunk_text_lower = chunk.text.lower()
        score = 0.0
        
        # Count keyword matches (simple TF scoring)
        for keyword in keywords:
            count = chunk_text_lower.count(keyword)
            if count > 0:
                # TF score: log(1 + count) to reduce impact of very frequent terms
                score += (1.0 + count) * 0.5
        
        if score > 0:
            scored_chunks.append((chunk.id, score))
    
    # Sort by score and return top_k
    scored_chunks.sort(key=lambda x: x[1], reverse=True)
    return scored_chunks[:top_k]


def hybrid_search(
    db: Session,
    user_id: int,
    query: str,
    vector_hits: List[VectorHit],
    top_k: int = 10,
    alpha: float = 0.7
) -> List[VectorHit]:
    """
    Combine vector search and keyword search using hybrid scoring.
    
    Args:
        db: Database session
        user_id: User ID
        query: Search query
        vector_hits: Results from vector search
        top_k: Number of results to return
        alpha: Weight for vector search (1-alpha for keyword search)
        
    Returns:
        Combined and re-ranked list of VectorHit objects
    """
    if not vector_hits:
        # If no vector hits, fall back to keyword search only
        keyword_results = keyword_search(db, user_id, query, top_k=top_k)
        return [
            VectorHit(chunk_id=chunk_id, score=1.0 - score)
            for chunk_id, score in keyword_results
        ]
    
    # Get keyword search results
    keyword_results = keyword_search(db, user_id, query, top_k=top_k * 2)
    
    # Normalize scores
    vector_scores = {}
    max_vector_score = max((h.score for h in vector_hits), default=1.0)
    for hit in vector_hits:
        # Convert distance to similarity (lower distance = higher similarity)
        normalized_score = 1.0 / (1.0 + hit.score) if hit.score > 0 else 1.0
        vector_scores[hit.chunk_id] = normalized_score
    
    keyword_scores = {}
    max_keyword_score = max((s for _, s in keyword_results), default=1.0)
    for chunk_id, score in keyword_results:
        normalized_score = score / max_keyword_score if max_keyword_score > 0 else 0.0
        keyword_scores[chunk_id] = normalized_score
    
    # Combine scores
    all_chunk_ids = set(vector_scores.keys()) | set(keyword_scores.keys())
    combined_scores = {}
    
    for chunk_id in all_chunk_ids:
        vector_score = vector_scores.get(chunk_id, 0.0)
        keyword_score = keyword_scores.get(chunk_id, 0.0)
        
        # Hybrid score: weighted combination
        hybrid_score = alpha * vector_score + (1 - alpha) * keyword_score
        combined_scores[chunk_id] = hybrid_score
    
    # Convert to VectorHit format and sort
    hybrid_hits = [
        VectorHit(chunk_id=chunk_id, score=1.0 - score)  # Convert similarity back to distance-like
        for chunk_id, score in sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
    ]
    
    return hybrid_hits[:top_k]


def rerank_results(
    query: str,
    chunks: List[models.DocumentChunk],
    hits: List[VectorHit],
    top_k: int = 10
) -> List[VectorHit]:
    """
    Re-rank results using cross-encoder or simple scoring.
    
    Simple implementation using text similarity.
    In production, use a cross-encoder model for better accuracy.
    
    Args:
        query: Original query
        chunks: List of document chunks
        hits: Initial search hits
        top_k: Number of results to return after re-ranking
        
    Returns:
        Re-ranked list of VectorHit objects
    """
    query_lower = query.lower()
    query_words = set(re.findall(r'\b\w+\b', query_lower))
    
    # Create chunk map
    chunk_map = {chunk.id: chunk for chunk in chunks}
    
    # Score each hit
    scored_hits = []
    for hit in hits:
        chunk = chunk_map.get(hit.chunk_id)
        if not chunk:
            continue
        
        chunk_text_lower = chunk.text.lower()
        chunk_words = set(re.findall(r'\b\w+\b', chunk_text_lower))
        
        # Calculate overlap
        overlap = len(query_words & chunk_words)
        total_query_words = len(query_words)
        
        if total_query_words > 0:
            # Jaccard similarity + word overlap
            jaccard = overlap / len(query_words | chunk_words) if (query_words | chunk_words) else 0
            overlap_ratio = overlap / total_query_words
            
            # Combined score
            rerank_score = (jaccard * 0.5 + overlap_ratio * 0.5)
        else:
            rerank_score = 0.0
        
        # Combine with original score (weighted)
        original_score = 1.0 / (1.0 + hit.score) if hit.score > 0 else 1.0
        final_score = 0.6 * rerank_score + 0.4 * original_score
        
        scored_hits.append((hit, final_score))
    
    # Sort by final score
    scored_hits.sort(key=lambda x: x[1], reverse=True)
    
    # Return top_k, converting back to VectorHit format
    return [
        VectorHit(chunk_id=hit.chunk_id, score=1.0 - score)
        for hit, score in scored_hits[:top_k]
    ]


def compress_context(context: str, max_chars: int = 4000) -> str:
    """
    Compress long context by summarizing or truncating intelligently.
    
    Simple implementation: truncate at sentence boundaries.
    In production, use LLM summarization for better compression.
    
    Args:
        context: Original context string
        max_chars: Maximum characters to keep
        
    Returns:
        Compressed context string
    """
    if len(context) <= max_chars:
        return context
    
    # Try to truncate at sentence boundaries
    sentences = re.split(r'([.!?]\s+)', context)
    compressed = ""
    
    for i in range(0, len(sentences), 2):
        sentence = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else "")
        if len(compressed + sentence) <= max_chars:
            compressed += sentence
        else:
            break
    
    if compressed:
        return compressed + "..."
    
    # Fallback: simple truncation
    return context[:max_chars] + "..."


# Note: multi_query_retrieval is now handled directly in chain.py
# This function is kept for reference but not used

