"""
Confidence scoring for RAG answers.
"""
import logging
from typing import List, Dict, Tuple, Any
from app.vectorstore.faiss_store import VectorHit

logger = logging.getLogger(__name__)


def calculate_confidence_score(
    hits: List[VectorHit],
    citations: List[Dict],
    answer: str,
    question: str
) -> float:
    """
    Calculate confidence score for a RAG answer.
    
    Factors:
    - Vector similarity scores (higher = more confident)
    - Number of relevant chunks (more = more confident)
    - Citation quality (more citations = more confident)
    - Answer length (too short or too long = less confident)
    
    Args:
        hits: Vector search hits
        citations: Citation list
        answer: Generated answer
        question: Original question
    
    Returns:
        Confidence score between 0.0 and 1.0
    """
    if not hits or not citations:
        return 0.3  # Low confidence if no sources
    
    # Factor 1: Average similarity score (normalized)
    # Lower distance = higher similarity = higher confidence
    avg_similarity = 0.0
    if hits:
        # Convert distances to similarities (inverse relationship)
        similarities = [1.0 / (1.0 + hit.score) if hit.score > 0 else 1.0 for hit in hits]
        avg_similarity = sum(similarities) / len(similarities)
    
    # Factor 2: Number of citations (more = better, but diminishing returns)
    citation_count_score = min(len(citations) / 5.0, 1.0)  # Cap at 5 citations
    
    # Factor 3: Answer quality (length check)
    answer_length = len(answer)
    ideal_length = 100  # Ideal answer length
    length_score = 1.0 - abs(answer_length - ideal_length) / (ideal_length * 2)
    length_score = max(0.0, min(1.0, length_score))
    
    # Factor 4: Citation scores (if available)
    citation_score = 0.0
    if citations:
        citation_scores = [c.get('score', 0.0) for c in citations if isinstance(c, dict)]
        if citation_scores:
            citation_score = sum(citation_scores) / len(citation_scores)
    
    # Weighted combination
    confidence = (
        avg_similarity * 0.4 +  # 40% weight on similarity
        citation_count_score * 0.2 +  # 20% on citation count
        length_score * 0.2 +  # 20% on answer length
        citation_score * 0.2  # 20% on citation quality
    )
    
    # Ensure between 0 and 1
    confidence = max(0.0, min(1.0, confidence))
    
    return round(confidence, 2)


def fact_check_answer(
    answer: str,
    citations: List[Dict],
    chunks: List
) -> Dict[str, Any]:
    """
    Fact-check an answer against its sources.
    
    Args:
        answer: Generated answer
        citations: Citation list
        chunks: Document chunks used
    
    Returns:
        Dictionary with fact-check results
    """
    # Simple fact-checking: verify key claims are in sources
    # In production, use more sophisticated NLP
    
    answer_lower = answer.lower()
    verified_claims = []
    unverified_claims = []
    
    # Extract key phrases from answer (simple approach)
    # In production, use NER or keyphrase extraction
    key_phrases = []
    sentences = answer.split('.')
    for sentence in sentences[:5]:  # Check first 5 sentences
        words = sentence.split()
        if len(words) > 3:
            # Take important phrases (nouns, verbs)
            key_phrases.append(sentence.strip())
    
    # Check if phrases appear in source chunks
    chunk_texts = [chunk.text.lower() for chunk in chunks]
    all_chunk_text = ' '.join(chunk_texts)
    
    for phrase in key_phrases:
        phrase_lower = phrase.lower()
        # Simple substring matching (in production, use semantic similarity)
        if phrase_lower in all_chunk_text:
            verified_claims.append(phrase)
        else:
            unverified_claims.append(phrase)
    
    verification_ratio = len(verified_claims) / len(key_phrases) if key_phrases else 1.0
    
    return {
        "verified_claims": verified_claims,
        "unverified_claims": unverified_claims,
        "verification_ratio": round(verification_ratio, 2),
        "total_claims": len(key_phrases),
        "verified_count": len(verified_claims),
    }

