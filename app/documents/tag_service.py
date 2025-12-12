"""
Service for document tagging and auto-suggestion.
"""
import logging
import re
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct

from app.db import models
from app.db.tag_models import Tag, Category, document_tags

logger = logging.getLogger(__name__)


def suggest_tags_from_content(db: Session, user_id: int, document_text: str, max_suggestions: int = 5) -> List[str]:
    """
    Auto-suggest tags based on document content using keyword extraction.
    
    Args:
        db: Database session
        user_id: User ID
        document_text: Document text content
        max_suggestions: Maximum number of suggestions
    
    Returns:
        List of suggested tag names
    """
    try:
        # Extract keywords (simple approach: common words, technical terms)
        # In production, you might use NLP libraries like spaCy or NLTK
        words = re.findall(r'\b[a-zA-Z]{4,}\b', document_text.lower())
        
        # Count word frequencies
        word_freq: Dict[str, int] = {}
        for word in words:
            if len(word) >= 4:  # Only words with 4+ characters
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get top keywords (excluding common stop words)
        stop_words = {'this', 'that', 'with', 'from', 'have', 'been', 'will', 'would', 'could', 'should',
                     'there', 'their', 'these', 'those', 'which', 'where', 'when', 'what', 'about'}
        
        keywords = [
            word for word, freq in sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
            if word not in stop_words and freq >= 2
        ][:max_suggestions * 2]  # Get more candidates
        
        # Check which keywords already exist as tags for this user
        existing_tags = {}
        if db:
            existing_tags = {tag.name.lower(): tag.name for tag in 
                             db.query(Tag).filter(Tag.user_id == user_id).all()}
        
        # Suggest existing tags that match keywords, or new keywords
        suggestions = []
        for keyword in keywords[:max_suggestions]:
            keyword_lower = keyword.lower()
            if keyword_lower in existing_tags:
                suggestions.append(existing_tags[keyword_lower])
            else:
                # Capitalize first letter
                suggestions.append(keyword.capitalize())
        
        return suggestions[:max_suggestions]
        
    except Exception as e:
        logger.error(f"Error suggesting tags: {e}", exc_info=True)
        return []


def get_user_tags(db: Session, user_id: int) -> List[Tag]:
    """Get all tags for a user."""
    return db.query(Tag).filter(Tag.user_id == user_id).order_by(Tag.name).all()


def get_user_categories(db: Session, user_id: int) -> List[Category]:
    """Get all categories for a user (flat list, can be organized hierarchically in frontend)."""
    return db.query(Category).filter(Category.user_id == user_id).order_by(Category.name).all()


def create_tag(db: Session, user_id: int, name: str, color: Optional[str] = None) -> Tag:
    """Create a new tag for a user."""
    # Check if tag already exists
    existing = db.query(Tag).filter(
        Tag.user_id == user_id,
        func.lower(Tag.name) == name.lower()
    ).first()
    
    if existing:
        return existing
    
    tag = Tag(user_id=user_id, name=name.strip(), color=color)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def create_category(db: Session, user_id: int, name: str, description: Optional[str] = None,
                   parent_id: Optional[int] = None, color: Optional[str] = None) -> Category:
    """Create a new category for a user."""
    category = Category(
        user_id=user_id,
        name=name.strip(),
        description=description,
        parent_id=parent_id,
        color=color
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def add_tags_to_document(db: Session, document_id: int, tag_names: List[str], user_id: int) -> List[Tag]:
    """Add tags to a document. Creates tags if they don't exist."""
    document = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not document or document.user_id != user_id:
        return []
    
    tags = []
    for tag_name in tag_names:
        tag = create_tag(db, user_id, tag_name)
        # Check if tags relationship exists before using it
        if hasattr(document, 'tags'):
            if tag not in document.tags:
                document.tags.append(tag)
        tags.append(tag)
    
    db.commit()
    return tags


def remove_tag_from_document(db: Session, document_id: int, tag_id: int, user_id: int) -> bool:
    """Remove a tag from a document."""
    document = db.query(models.Document).filter(
        models.Document.id == document_id,
        models.Document.user_id == user_id
    ).first()
    
    if not document:
        return False
    
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    # Check if tags relationship exists before using it
    if tag and hasattr(document, 'tags') and tag in document.tags:
        document.tags.remove(tag)
        db.commit()
        return True
    
    return False


def set_document_category(db: Session, document_id: int, category_id: Optional[int], user_id: int) -> bool:
    """Set the category for a document."""
    document = db.query(models.Document).filter(
        models.Document.id == document_id,
        models.Document.user_id == user_id
    ).first()
    
    if not document:
        return False
    
    if category_id:
        category = db.query(Category).filter(
            Category.id == category_id,
            Category.user_id == user_id
        ).first()
        if not category:
            return False
        document.category_id = category_id
    else:
        document.category_id = None
    
    db.commit()
    return True
