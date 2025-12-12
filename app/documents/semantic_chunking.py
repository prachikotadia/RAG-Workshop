"""
Smart semantic chunking that preserves document structure and semantic boundaries.

Uses sentence transformers to find semantic boundaries and chunks at paragraph/section
boundaries rather than fixed sizes. This improves retrieval accuracy by preserving context.
"""
import re
import logging
from typing import List, Dict, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import sentence transformers (optional - falls back to rule-based if unavailable)
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.info("Sentence transformers not available, using rule-based semantic chunking")

# Global model instance (lazy loaded)
_semantic_model = None


def _get_semantic_model():
    """Get or initialize semantic model for boundary detection."""
    global _semantic_model
    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        return None
    
    if _semantic_model is None:
        try:
            # Use a lightweight model for semantic similarity
            _semantic_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Semantic chunking model loaded")
        except Exception as e:
            logger.warning(f"Failed to load semantic model: {e}, using rule-based chunking")
            return None
    
    return _semantic_model


def _detect_paragraphs(text: str) -> List[Tuple[int, int, str]]:
    """
    Detect paragraph boundaries in text.
    
    Returns:
        List of (start_idx, end_idx, paragraph_text) tuples
    """
    paragraphs = []
    # Split by double newlines (paragraph breaks)
    parts = re.split(r'\n\s*\n', text)
    current_pos = 0
    
    for part in parts:
        part = part.strip()
        if not part:
            current_pos += len(part) + 2  # +2 for \n\n
            continue
        
        start_idx = text.find(part, current_pos)
        if start_idx == -1:
            start_idx = current_pos
        
        end_idx = start_idx + len(part)
        paragraphs.append((start_idx, end_idx, part))
        current_pos = end_idx + 2
    
    return paragraphs


def _detect_sections(text: str) -> List[Tuple[int, int, str, int]]:
    """
    Detect section boundaries (headings, numbered sections, etc.).
    
    Returns:
        List of (start_idx, end_idx, section_text, level) tuples
    """
    sections = []
    
    # Pattern for markdown-style headings
    heading_pattern = r'^(#{1,6})\s+(.+)$'
    # Pattern for numbered sections (1., 2., etc.)
    numbered_pattern = r'^(\d+\.)\s+(.+)$'
    # Pattern for ALL CAPS headings
    caps_pattern = r'^([A-Z][A-Z\s]{3,})$'
    
    lines = text.split('\n')
    current_section_start = 0
    current_section_lines = []
    current_level = 0
    
    for i, line in enumerate(lines):
        is_heading = False
        level = 0
        
        # Check for markdown heading
        md_match = re.match(heading_pattern, line.strip())
        if md_match:
            level = len(md_match.group(1))
            is_heading = True
        # Check for numbered section
        elif re.match(numbered_pattern, line.strip()):
            level = 1
            is_heading = True
        # Check for ALL CAPS heading
        elif re.match(caps_pattern, line.strip()) and len(line.strip()) < 100:
            level = 1
            is_heading = True
        
        if is_heading and current_section_lines:
            # Save previous section
            section_text = '\n'.join(current_section_lines)
            if section_text.strip():
                sections.append((
                    current_section_start,
                    current_section_start + len(section_text),
                    section_text,
                    current_level
                ))
            # Start new section
            current_section_start = current_section_start + len(section_text) + 1
            current_section_lines = [line]
            current_level = level
        else:
            current_section_lines.append(line)
    
    # Add final section
    if current_section_lines:
        section_text = '\n'.join(current_section_lines)
        if section_text.strip():
            sections.append((
                current_section_start,
                current_section_start + len(section_text),
                section_text,
                current_level
            ))
    
    return sections


def _calculate_semantic_similarity(text1: str, text2: str) -> float:
    """
    Calculate semantic similarity between two text segments.
    
    Returns:
        Similarity score between 0 and 1
    """
    model = _get_semantic_model()
    if not model:
        # Fallback: use word overlap as similarity measure
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        return intersection / union if union > 0 else 0.0
    
    try:
        embeddings = model.encode([text1, text2])
        # Cosine similarity
        from numpy import dot
        from numpy.linalg import norm
        similarity = dot(embeddings[0], embeddings[1]) / (norm(embeddings[0]) * norm(embeddings[1]))
        return float(similarity)
    except Exception as e:
        logger.warning(f"Semantic similarity calculation failed: {e}, using word overlap")
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        return intersection / union if union > 0 else 0.0


def semantic_chunk_text(
    text: str,
    max_chunk_size: int = 500,
    min_chunk_size: int = 100,
    overlap_size: int = 50,
    preserve_structure: bool = True,
) -> List[Dict[str, int | str]]:
    """
    Chunk text using semantic boundaries instead of fixed sizes.
    
    This method:
    1. Detects paragraph and section boundaries
    2. Groups related paragraphs by semantic similarity
    3. Creates chunks that preserve document structure
    4. Ensures chunks are within size limits
    
    Args:
        text: Text to chunk
        max_chunk_size: Maximum words per chunk
        min_chunk_size: Minimum words per chunk (before merging)
        overlap_size: Words to overlap between chunks
        preserve_structure: Whether to preserve paragraph/section boundaries
    
    Returns:
        List of dicts, each with:
        - 'chunk_index': int (0-based index)
        - 'text': str (chunk text)
        - 'token_count': int (approximate word count)
        - 'metadata': dict (chunk metadata including boundaries)
    """
    if not text or not text.strip():
        return []
    
    words = text.split()
    if len(words) <= max_chunk_size:
        # Text is small enough, return as single chunk
        return [{
            "chunk_index": 0,
            "text": text,
            "token_count": len(words),
            "metadata": {"type": "single_chunk", "preserved_structure": True}
        }]
    
    chunks = []
    
    if preserve_structure:
        # Try to use document structure first
        sections = _detect_sections(text)
        paragraphs = _detect_paragraphs(text)
        
        if sections and len(sections) > 1:
            # Use sections as primary boundaries
            logger.debug(f"Using {len(sections)} sections for chunking")
            current_chunk_words = []
            current_chunk_text = []
            chunk_index = 0
            
            for start_idx, end_idx, section_text, level in sections:
                section_words = section_text.split()
                
                # If section fits in current chunk, add it
                if len(current_chunk_words) + len(section_words) <= max_chunk_size:
                    current_chunk_words.extend(section_words)
                    current_chunk_text.append(section_text)
                else:
                    # Save current chunk if it's large enough
                    if len(current_chunk_words) >= min_chunk_size:
                        chunk_text = '\n\n'.join(current_chunk_text)
                        chunks.append({
                            "chunk_index": chunk_index,
                            "text": chunk_text,
                            "token_count": len(current_chunk_words),
                            "metadata": {
                                "type": "section_chunk",
                                "level": level,
                                "preserved_structure": True
                            }
                        })
                        chunk_index += 1
                    
                    # Start new chunk with overlap
                    if overlap_size > 0 and current_chunk_words:
                        overlap_words = current_chunk_words[-overlap_size:]
                        current_chunk_words = overlap_words
                        current_chunk_text = [' '.join(overlap_words)]
                    else:
                        current_chunk_words = []
                        current_chunk_text = []
                    
                    # Add current section
                    current_chunk_words.extend(section_words)
                    current_chunk_text.append(section_text)
            
            # Add final chunk
            if current_chunk_words:
                chunk_text = '\n\n'.join(current_chunk_text)
                chunks.append({
                    "chunk_index": chunk_index,
                    "text": chunk_text,
                    "token_count": len(current_chunk_words),
                    "metadata": {
                        "type": "section_chunk",
                        "preserved_structure": True
                    }
                })
        
        elif paragraphs and len(paragraphs) > 1:
            # Use paragraphs as boundaries
            logger.debug(f"Using {len(paragraphs)} paragraphs for chunking")
            current_chunk_words = []
            current_chunk_text = []
            chunk_index = 0
            
            for start_idx, end_idx, para_text in paragraphs:
                para_words = para_text.split()
                
                # If paragraph fits, add it
                if len(current_chunk_words) + len(para_words) <= max_chunk_size:
                    current_chunk_words.extend(para_words)
                    current_chunk_text.append(para_text)
                else:
                    # Check semantic similarity to decide if we should split
                    if current_chunk_text:
                        last_para = current_chunk_text[-1]
                        similarity = _calculate_semantic_similarity(last_para, para_text)
                        
                        # If similar, try to fit it (allow slight overflow)
                        if similarity > 0.3 and len(current_chunk_words) + len(para_words) <= max_chunk_size * 1.2:
                            current_chunk_words.extend(para_words)
                            current_chunk_text.append(para_text)
                            continue
                    
                    # Save current chunk
                    if len(current_chunk_words) >= min_chunk_size:
                        chunk_text = '\n\n'.join(current_chunk_text)
                        chunks.append({
                            "chunk_index": chunk_index,
                            "text": chunk_text,
                            "token_count": len(current_chunk_words),
                            "metadata": {
                                "type": "paragraph_chunk",
                                "preserved_structure": True
                            }
                        })
                        chunk_index += 1
                    
                    # Start new chunk with overlap
                    if overlap_size > 0 and current_chunk_text:
                        overlap_text = current_chunk_text[-1]
                        overlap_words = overlap_text.split()[-overlap_size:]
                        current_chunk_words = overlap_words
                        current_chunk_text = [' '.join(overlap_words)]
                    else:
                        current_chunk_words = []
                        current_chunk_text = []
                    
                    current_chunk_words.extend(para_words)
                    current_chunk_text.append(para_text)
            
            # Add final chunk
            if current_chunk_words:
                chunk_text = '\n\n'.join(current_chunk_text)
                chunks.append({
                    "chunk_index": chunk_index,
                    "text": chunk_text,
                    "token_count": len(current_chunk_words),
                    "metadata": {
                        "type": "paragraph_chunk",
                        "preserved_structure": True
                    }
                })
    
    # Fallback to sentence-based chunking if structure detection didn't work
    if not chunks:
        logger.debug("Falling back to sentence-based semantic chunking")
        sentences = re.split(r'(?<=[.!?])\s+', text)
        current_chunk_words = []
        current_chunk_text = []
        chunk_index = 0
        
        for i, sentence in enumerate(sentences):
            sentence_words = sentence.split()
            
            if len(current_chunk_words) + len(sentence_words) <= max_chunk_size:
                current_chunk_words.extend(sentence_words)
                current_chunk_text.append(sentence)
            else:
                # Save current chunk
                if len(current_chunk_words) >= min_chunk_size:
                    chunk_text = ' '.join(current_chunk_text)
                    chunks.append({
                        "chunk_index": chunk_index,
                        "text": chunk_text,
                        "token_count": len(current_chunk_words),
                        "metadata": {
                            "type": "sentence_chunk",
                            "preserved_structure": False
                        }
                    })
                    chunk_index += 1
                
                # Start new chunk with overlap
                if overlap_size > 0 and current_chunk_text:
                    overlap_sentences = current_chunk_text[-2:] if len(current_chunk_text) >= 2 else current_chunk_text
                    overlap_words = ' '.join(overlap_sentences).split()[-overlap_size:]
                    current_chunk_words = overlap_words
                    current_chunk_text = [' '.join(overlap_words)]
                else:
                    current_chunk_words = []
                    current_chunk_text = []
                
                current_chunk_words.extend(sentence_words)
                current_chunk_text.append(sentence)
        
        # Add final chunk
        if current_chunk_words:
            chunk_text = ' '.join(current_chunk_text)
            chunks.append({
                "chunk_index": chunk_index,
                "text": chunk_text,
                "token_count": len(current_chunk_words),
                "metadata": {
                    "type": "sentence_chunk",
                    "preserved_structure": False
                }
            })
    
    # Final fallback: word-based chunking (original method)
    if not chunks:
        logger.debug("Falling back to word-based chunking")
        from app.documents.chunking import chunk_text
        return chunk_text(text, max_words=max_chunk_size, overlap_words=overlap_size)
    
    logger.info(f"Created {len(chunks)} semantic chunks (avg size: {sum(c['token_count'] for c in chunks) / len(chunks):.0f} words)")
    return chunks
