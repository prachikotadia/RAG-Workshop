"""
Text chunking utilities.

Phase 4 spec: Word-based chunking with overlap for embedding and retrieval.
"""
from typing import List, Dict


def chunk_text(
    text: str,
    max_words: int = 200,
    overlap_words: int = 50,
) -> List[Dict[str, int | str]]:
    """
    Split text into overlapping word chunks.
    
    Uses a sliding window approach over words with the specified overlap.
    
    Args:
        text: Text to chunk
        max_words: Maximum number of words per chunk
        overlap_words: Number of words to overlap between chunks
    
    Returns:
        List of dicts, each with:
        - 'chunk_index': int (0-based index)
        - 'text': str (chunk text)
        - 'token_count': int (approximate, based on word count)
    """
    if not text or not text.strip():
        return []
    
    # Split text into words
    words = text.split()
    
    if len(words) == 0:
        return []
    
    # If text is shorter than max_words, return single chunk
    if len(words) <= max_words:
        chunk_text = " ".join(words)
        return [{
            "chunk_index": 0,
            "text": chunk_text,
            "token_count": len(words)
        }]
    
    chunks = []
    start_idx = 0
    chunk_index = 0
    
    while start_idx < len(words):
        # Calculate end index for this chunk
        end_idx = min(start_idx + max_words, len(words))
        
        # Extract words for this chunk
        chunk_words = words[start_idx:end_idx]
        chunk_text = " ".join(chunk_words)
        
        # Create chunk dict
        chunks.append({
            "chunk_index": chunk_index,
            "text": chunk_text,
            "token_count": len(chunk_words)  # Approximate token count
        })
        
        # Move start index forward with overlap
        start_idx = start_idx + max_words - overlap_words
        chunk_index += 1
        
        # Prevent infinite loop if overlap is >= max_words
        if overlap_words >= max_words:
            break
    
    return chunks

