"""
Full-text search with highlighting across document content.

Searches across all document chunks (not just titles) and highlights
matching terms in results for better user experience.
"""
import re
import logging
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.db import models

logger = logging.getLogger(__name__)


def search_documents_fulltext(
    db: Session,
    user_id: int,
    query: str,
    document_id: Optional[int] = None,
    limit: int = 50,
) -> List[Dict[str, any]]:
    """
    Search across all document content with highlighting.
    
    Args:
        db: Database session
        user_id: User ID to filter documents
        query: Search query string
        document_id: Optional document ID to search within
        limit: Maximum number of results
    
    Returns:
        List of search results with highlighted text
    """
    if not query or not query.strip():
        return []
    
    query_terms = query.strip().split()
    if not query_terms:
        return []
    
    # Build search query
    chunk_query = db.query(models.DocumentChunk).join(
        models.Document
    ).filter(
        models.Document.user_id == user_id
    )
    
    # Filter by document if specified
    if document_id:
        chunk_query = chunk_query.filter(
            models.DocumentChunk.document_id == document_id
        )
    
    # Search in chunk text (case-insensitive)
    search_conditions = []
    for term in query_terms:
        search_conditions.append(
            models.DocumentChunk.text.ilike(f'%{term}%')
        )
    
    if search_conditions:
        chunk_query = chunk_query.filter(or_(*search_conditions))
    
    # Get chunks
    chunks = chunk_query.limit(limit).all()
    
    # Build results with highlighting
    results = []
    seen_chunks = set()  # Avoid duplicates
    
    for chunk in chunks:
        # Skip if we've already seen this chunk
        chunk_key = (chunk.document_id, chunk.chunk_index)
        if chunk_key in seen_chunks:
            continue
        seen_chunks.add(chunk_key)
        
        # Highlight matching terms
        highlighted_text = highlight_terms(chunk.text, query_terms)
        
        # Get document info
        document = db.query(models.Document).filter(
            models.Document.id == chunk.document_id
        ).first()
        
        if document:
            results.append({
                "document_id": document.id,
                "document_title": document.title,
                "chunk_id": chunk.id,
                "chunk_index": chunk.chunk_index,
                "text": chunk.text,
                "highlighted_text": highlighted_text,
                "relevance_score": calculate_relevance_score(chunk.text, query_terms),
            })
    
    # Sort by relevance score (descending)
    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    
    return results[:limit]


def highlight_terms(text: str, terms: List[str]) -> str:
    """
    Highlight search terms in text using HTML <mark> tags.
    
    Args:
        text: Text to highlight
        terms: List of search terms
    
    Returns:
        Text with highlighted terms
    """
    if not terms:
        return text
    
    # Create pattern to match any term (case-insensitive, whole word)
    pattern_parts = []
    for term in terms:
        # Escape special regex characters
        escaped_term = re.escape(term)
        # Match whole word (with word boundaries)
        pattern_parts.append(rf'\b{escaped_term}\b')
    
    pattern = '|'.join(pattern_parts)
    
    def highlight_match(match):
        return f'<mark class="bg-yellow-200 dark:bg-yellow-800 px-1 rounded font-medium">{match.group(0)}</mark>'
    
    try:
        highlighted = re.sub(
            pattern,
            highlight_match,
            text,
            flags=re.IGNORECASE
        )
        return highlighted
    except Exception as e:
        logger.warning(f"Highlighting failed: {e}, returning original text")
        return text


def calculate_relevance_score(text: str, terms: List[str]) -> float:
    """
    Calculate relevance score for a text based on search terms.
    
    Args:
        text: Text to score
        terms: List of search terms
    
    Returns:
        Relevance score (0.0 to 1.0)
    """
    if not terms:
        return 0.0
    
    text_lower = text.lower()
    matches = 0
    total_positions = 0
    
    for term in terms:
        term_lower = term.lower()
        # Count occurrences
        count = text_lower.count(term_lower)
        matches += count
        total_positions += len(text_lower)
    
    if total_positions == 0:
        return 0.0
    
    # Calculate score based on term frequency and position
    # Terms at the beginning are more relevant
    position_bonus = 0.0
    for term in terms:
        term_lower = term.lower()
        first_pos = text_lower.find(term_lower)
        if first_pos != -1:
            # Earlier positions get higher bonus
            position_bonus += (1.0 - (first_pos / max(len(text_lower), 1)))
    
    # Combine term frequency and position
    frequency_score = min(matches / len(terms), 1.0)  # Normalize
    position_score = position_bonus / len(terms) if terms else 0.0
    
    # Weighted combination
    relevance = (frequency_score * 0.7) + (position_score * 0.3)
    
    return min(relevance, 1.0)


def search_within_document(
    db: Session,
    user_id: int,
    document_id: int,
    query: str,
    limit: int = 20,
) -> List[Dict[str, any]]:
    """
    Search within a specific document.
    
    Args:
        db: Database session
        user_id: User ID
        document_id: Document ID to search within
        query: Search query
        limit: Maximum results
    
    Returns:
        List of matching chunks with highlighting
    """
    return search_documents_fulltext(
        db=db,
        user_id=user_id,
        query=query,
        document_id=document_id,
        limit=limit,
    )
