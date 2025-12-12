"""
Document relationship graph for discovering related content.

Extracts entities and relationships from documents to build a knowledge graph
that helps users discover related content and improves context retrieval.
"""
import logging
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict
import re

logger = logging.getLogger(__name__)

# Try to import spaCy for entity extraction (optional)
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logger.info("spaCy not available, using rule-based entity extraction")

# Global spaCy model (lazy loaded)
_nlp_model = None


def _get_nlp_model():
    """Get or initialize spaCy model for entity extraction."""
    global _nlp_model
    if not SPACY_AVAILABLE:
        return None
    
    if _nlp_model is None:
        try:
            # Try to load English model
            _nlp_model = spacy.load("en_core_web_sm")
            logger.info("spaCy model loaded for entity extraction")
        except OSError:
            logger.warning("spaCy model not found, using rule-based extraction")
            return None
        except Exception as e:
            logger.warning(f"Failed to load spaCy model: {e}, using rule-based extraction")
            return None
    
    return _nlp_model


def _extract_entities_rule_based(text: str) -> List[Tuple[str, str]]:
    """
    Extract entities using rule-based patterns.
    
    Returns:
        List of (entity, type) tuples
    """
    entities = []
    
    # Pattern for capitalized phrases (potential proper nouns)
    capitalized_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
    matches = re.finditer(capitalized_pattern, text)
    for match in matches:
        entity = match.group(1)
        # Filter out common words and short entities
        if len(entity) > 3 and entity not in ['The', 'This', 'That', 'There', 'These', 'Those']:
            entities.append((entity, "PERSON_ORG"))
    
    # Pattern for email addresses
    email_pattern = r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b'
    for match in re.finditer(email_pattern, text):
        entities.append((match.group(1), "EMAIL"))
    
    # Pattern for URLs
    url_pattern = r'https?://[^\s]+'
    for match in re.finditer(url_pattern, text):
        entities.append((match.group(0), "URL"))
    
    # Pattern for dates
    date_pattern = r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b'
    for match in re.finditer(date_pattern, text):
        entities.append((match.group(1), "DATE"))
    
    return entities


def extract_entities(text: str) -> List[Tuple[str, str]]:
    """
    Extract named entities from text.
    
    Args:
        text: Text to extract entities from
    
    Returns:
        List of (entity, entity_type) tuples
    """
    nlp_model = _get_nlp_model()
    
    if nlp_model:
        try:
            doc = nlp_model(text)
            entities = [(ent.text, ent.label_) for ent in doc.ents]
            logger.debug(f"Extracted {len(entities)} entities using spaCy")
            return entities
        except Exception as e:
            logger.warning(f"spaCy entity extraction failed: {e}, using rule-based")
    
    # Fallback to rule-based extraction
    entities = _extract_entities_rule_based(text)
    logger.debug(f"Extracted {len(entities)} entities using rule-based method")
    return entities


def extract_relationships(text: str, entities: List[Tuple[str, str]]) -> List[Tuple[str, str, str]]:
    """
    Extract relationships between entities.
    
    Args:
        text: Text to analyze
        entities: List of extracted entities
    
    Returns:
        List of (entity1, relationship, entity2) tuples
    """
    relationships = []
    entity_texts = [e[0] for e in entities]
    
    # Common relationship patterns
    relationship_patterns = [
        (r'(\w+)\s+(?:is|was|are|were)\s+(?:a|an|the)?\s*(\w+)', "IS_A"),
        (r'(\w+)\s+(?:works?|worked)\s+(?:for|at|with)\s+(\w+)', "WORKS_FOR"),
        (r'(\w+)\s+(?:located|situated)\s+(?:in|at|on)\s+(\w+)', "LOCATED_IN"),
        (r'(\w+)\s+(?:contains?|includes?)\s+(\w+)', "CONTAINS"),
        (r'(\w+)\s+(?:related|connected)\s+(?:to|with)\s+(\w+)', "RELATED_TO"),
    ]
    
    for pattern, rel_type in relationship_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            entity1 = match.group(1)
            entity2 = match.group(2)
            # Check if both are in our entity list
            if any(e.lower() == entity1.lower() for e in entity_texts) and \
               any(e.lower() == entity2.lower() for e in entity_texts):
                relationships.append((entity1, rel_type, entity2))
    
    return relationships


def build_document_graph(
    documents: List[Dict[str, any]],
    chunks: List[Dict[str, any]],
) -> Dict[str, any]:
    """
    Build a knowledge graph from documents and their chunks.
    
    Args:
        documents: List of document dicts with 'id', 'title', 'text'
        chunks: List of chunk dicts with 'document_id', 'text'
    
    Returns:
        Dictionary with entities, relationships, and document connections
    """
    entity_to_docs: Dict[str, Set[int]] = defaultdict(set)
    relationships: List[Tuple[str, str, str, int]] = []  # (entity1, rel, entity2, doc_id)
    doc_entities: Dict[int, Set[str]] = defaultdict(set)
    
    # Process each document
    for doc in documents:
        doc_id = doc.get('id')
        doc_text = doc.get('text', '') or doc.get('title', '')
        
        # Extract entities from document
        entities = extract_entities(doc_text)
        for entity, entity_type in entities:
            entity_to_docs[entity].add(doc_id)
            doc_entities[doc_id].add(entity)
        
        # Extract relationships
        rels = extract_relationships(doc_text, entities)
        for entity1, rel, entity2 in rels:
            relationships.append((entity1, rel, entity2, doc_id))
    
    # Process chunks
    for chunk in chunks:
        doc_id = chunk.get('document_id')
        chunk_text = chunk.get('text', '')
        
        entities = extract_entities(chunk_text)
        for entity, entity_type in entities:
            entity_to_docs[entity].add(doc_id)
            doc_entities[doc_id].add(entity)
    
    # Build document similarity based on shared entities
    doc_similarity: Dict[Tuple[int, int], float] = {}
    doc_ids = list(doc_entities.keys())
    
    for i, doc1_id in enumerate(doc_ids):
        for doc2_id in doc_ids[i+1:]:
            entities1 = doc_entities[doc1_id]
            entities2 = doc_entities[doc2_id]
            
            if entities1 and entities2:
                intersection = len(entities1 & entities2)
                union = len(entities1 | entities2)
                similarity = intersection / union if union > 0 else 0.0
                if similarity > 0.1:  # Only store meaningful similarities
                    doc_similarity[(doc1_id, doc2_id)] = similarity
    
    return {
        "entities": {entity: list(docs) for entity, docs in entity_to_docs.items()},
        "relationships": relationships,
        "document_entities": {doc_id: list(entities) for doc_id, entities in doc_entities.items()},
        "document_similarity": doc_similarity,
    }


def get_related_documents(
    document_id: int,
    graph: Dict[str, any],
    limit: int = 5,
) -> List[Dict[str, any]]:
    """
    Get documents related to a given document based on the knowledge graph.
    
    Args:
        document_id: Document ID to find related documents for
        graph: Knowledge graph from build_document_graph
        limit: Maximum number of related documents to return
    
    Returns:
        List of related document info with similarity scores
    """
    doc_similarity = graph.get("document_similarity", {})
    related = []
    
    for (doc1_id, doc2_id), similarity in doc_similarity.items():
        if doc1_id == document_id:
            related.append({"document_id": doc2_id, "similarity": similarity})
        elif doc2_id == document_id:
            related.append({"document_id": doc1_id, "similarity": similarity})
    
    # Sort by similarity (descending)
    related.sort(key=lambda x: x["similarity"], reverse=True)
    
    return related[:limit]


def get_entity_documents(
    entity: str,
    graph: Dict[str, any],
) -> List[int]:
    """
    Get all documents that mention a specific entity.
    
    Args:
        entity: Entity name to search for
        graph: Knowledge graph from build_document_graph
    
    Returns:
        List of document IDs
    """
    entities = graph.get("entities", {})
    # Case-insensitive search
    entity_lower = entity.lower()
    for ent, doc_ids in entities.items():
        if ent.lower() == entity_lower:
            return list(doc_ids)
    return []
