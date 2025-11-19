"""
Context builder for RAG.

Phase 6 spec: Build context string and citations from retrieved chunks and FAISS hits.
"""
from typing import List, Dict, Tuple
from sqlalchemy.orm import Session
from app.db import models
from app.vectorstore.faiss_store import VectorHit


def build_context(
    db: Session,
    chunks: List[models.DocumentChunk],
    hits: List[VectorHit],
    max_chars: int = 4000,
) -> Tuple[str, List[Dict]]:
    """
    Given the retrieved document chunks and the raw VectorHit results,
    construct a context string and a list of citation dicts.
    
    Behavior:
    - Join chunks ordered by relevance (using hits scores)
    - For each chunk, include a header like: [doc: <title>, chunk: <chunk_index>]
    - Stop when max_chars is reached
    - Build citations list with document_id, document_title, chunk_id, chunk_index, score
    
    Args:
        db: Database session (to fetch Document titles if needed)
        chunks: List of DocumentChunk objects
        hits: List of VectorHit objects with chunk_id and score
        max_chars: Maximum characters to include in context
    
    Returns:
        Tuple of (context_string, citations_list)
        Citations format:
        [
          {
            "document_id": int,
            "document_title": str,
            "chunk_id": int,
            "chunk_index": int,
            "score": float,
          },
          ...
        ]
    """
    # Create a mapping of chunk_id to hit score
    hit_score_map = {hit.chunk_id: hit.score for hit in hits}
    
    # Create a mapping of chunk_id to chunk
    chunk_map = {chunk.id: chunk for chunk in chunks}
    
    # Filter chunks to only those in hits, and sort by score (most relevant first)
    # Lower score = better for L2 distance, so we sort ascending
    # Only process chunks that were actually retrieved
    chunks_in_hits = [chunk for chunk in chunks if chunk.id in hit_score_map]
    sorted_chunks = sorted(
        chunks_in_hits,
        key=lambda c: hit_score_map.get(c.id, float('inf'))
    )
    
    # Build context and citations
    context_parts = []
    citations = []
    total_chars = 0
    
    for chunk in sorted_chunks:
        # Fetch document for title (if not already loaded)
        if not hasattr(chunk, 'document') or chunk.document is None:
            chunk.document = db.query(models.Document).filter(
                models.Document.id == chunk.document_id
            ).first()
        
        if not chunk.document:
            continue
        
        # Calculate chunk text length (no citation header)
        chunk_text_with_header = chunk.text
        chunk_length = len(chunk_text_with_header)
        
        # Check if adding this chunk would exceed max_chars
        if total_chars + chunk_length > max_chars:
            # Try to add partial chunk if we have space
            remaining_chars = max_chars - total_chars
            if remaining_chars > 50:  # Only add if meaningful amount of text
                partial_text = chunk.text[:remaining_chars] + "..."
                context_parts.append(partial_text)
                # Still add citation for partial chunk (for internal tracking, not shown to user)
                citations.append({
                    "document_id": chunk.document.id,
                    "document_title": chunk.document.title,
                    "chunk_id": chunk.id,
                    "chunk_index": chunk.chunk_index,
                    "score": hit_score_map.get(chunk.id, 0.0),
                })
            break
        
        # For image chunks, prioritize them and ensure full text is included
        # Image chunks contain comprehensive scan data or BLIP-2/CLIP analysis which is critical
        is_image_chunk = (
            chunk.chunk_metadata.get("file_type") == "image" 
            or "COMPREHENSIVE IMAGE SCAN" in chunk.text
            or "BLIP-2 Analysis" in chunk.text
            or "BLIP-2 Caption" in chunk.text
        )
        
        if is_image_chunk:
            # For images, we want the full comprehensive scan/analysis even if it's long
            # Comprehensive scans contain critical details: objects, people, actions, colors, text, etc.
            # Increase max_chars allowance significantly for image chunks to ensure full scan data is included
            is_comprehensive_scan = "COMPREHENSIVE IMAGE SCAN" in chunk.text
            if is_comprehensive_scan:
                # For comprehensive scans, allow even more space - these are critical
                image_max_chars = int(max_chars * 2.0)  # Allow 2x for comprehensive scans
            else:
                image_max_chars = int(max_chars * 1.5)  # Allow 50% more for regular image analysis
            
            if total_chars + chunk_length > image_max_chars:
                # Still try to include as much as possible, prioritizing key sections
                remaining_chars = image_max_chars - total_chars
                if remaining_chars > 200:  # Increased threshold for comprehensive scans
                    # Try to preserve key sections if truncating
                    if is_comprehensive_scan:
                        # For comprehensive scans, try to keep all major sections
                        text = chunk.text
                        # Check if we can fit the key sections
                        key_sections = ["BASIC CAPTION", "DETAILED DESCRIPTION", "DETECTED OBJECTS", 
                                       "PEOPLE INFORMATION", "ACTIONS", "COLOR PALETTE"]
                        preserved_text = ""
                        for section in key_sections:
                            if section in text:
                                section_start = text.find(section)
                                section_end = text.find("\n\n", section_start + 200)  # Get section + some content
                                if section_end == -1:
                                    section_end = min(section_start + 500, len(text))
                                if len(preserved_text) + (section_end - section_start) < remaining_chars:
                                    preserved_text += text[section_start:section_end] + "\n\n"
                        if preserved_text:
                            context_parts.append(preserved_text + "...")
                            total_chars += len(preserved_text)
                        else:
                            partial_text = chunk.text[:remaining_chars] + "..."
                            context_parts.append(partial_text)
                            total_chars += remaining_chars
                    else:
                        partial_text = chunk.text[:remaining_chars] + "..."
                        context_parts.append(partial_text)
                        total_chars += remaining_chars
                else:
                    break
            else:
                # Add full image chunk (comprehensive scan or regular analysis)
                context_parts.append(chunk_text_with_header)
                total_chars += chunk_length
        else:
            # For regular text chunks, use normal logic
            if total_chars + chunk_length > max_chars:
                # Try to add partial chunk if we have space
                remaining_chars = max_chars - total_chars
                if remaining_chars > 50:  # Only add if meaningful amount of text
                    partial_text = chunk.text[:remaining_chars] + "..."
                    context_parts.append(partial_text)
                    total_chars += remaining_chars
                else:
                    break
            else:
                context_parts.append(chunk_text_with_header)
                total_chars += chunk_length
        
        # Add citation (for both image and text chunks)
        citations.append({
            "document_id": chunk.document.id,
            "document_title": chunk.document.title,
            "chunk_id": chunk.id,
            "chunk_index": chunk.chunk_index,
            "score": hit_score_map.get(chunk.id, 0.0),
        })
    
    context = "\n\n".join(context_parts)
    return context, citations

