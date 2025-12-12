"""
Routes for document tags and categories.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.base import get_db
from app.db import models
from app.db.tag_models import Tag, Category
from app.auth.dependencies import get_current_user
from app.documents.tag_service import (
    get_user_tags,
    get_user_categories,
    create_tag,
    create_category,
    add_tags_to_document,
    remove_tag_from_document,
    set_document_category,
    suggest_tags_from_content,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic schemas
class TagCreate(BaseModel):
    name: str
    color: Optional[str] = None


class TagRead(BaseModel):
    id: int
    name: str
    color: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    color: Optional[str] = None


class CategoryRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    color: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


@router.get("/tags", response_model=List[TagRead])
def list_tags(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get all tags for the current user."""
    tags = get_user_tags(db, current_user.id)
    return [TagRead(id=t.id, name=t.name, color=t.color, created_at=t.created_at.isoformat()) for t in tags]


@router.post("/tags", response_model=TagRead, status_code=status.HTTP_201_CREATED)
def create_tag_endpoint(
    tag_data: TagCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create a new tag."""
    tag = create_tag(db, current_user.id, tag_data.name, tag_data.color)
    return TagRead(id=tag.id, name=tag.name, color=tag.color, created_at=tag.created_at.isoformat())


@router.get("/categories", response_model=List[CategoryRead])
def list_categories(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get all categories for the current user."""
    categories = get_user_categories(db, current_user.id)
    return [
        CategoryRead(
            id=c.id,
            name=c.name,
            description=c.description,
            parent_id=c.parent_id,
            color=c.color,
            created_at=c.created_at.isoformat()
        )
        for c in categories
    ]


@router.post("/categories", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category_endpoint(
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create a new category."""
    category = create_category(
        db,
        current_user.id,
        category_data.name,
        category_data.description,
        category_data.parent_id,
        category_data.color
    )
    return CategoryRead(
        id=category.id,
        name=category.name,
        description=category.description,
        parent_id=category.parent_id,
        color=category.color,
        created_at=category.created_at.isoformat()
    )


@router.post("/documents/{document_id}/tags")
def add_tags(
    document_id: int,
    tag_names: List[str],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Add tags to a document."""
    tags = add_tags_to_document(db, document_id, tag_names, current_user.id)
    return {
        "message": f"Added {len(tags)} tag(s) to document",
        "tags": [{"id": t.id, "name": t.name} for t in tags]
    }


@router.delete("/documents/{document_id}/tags/{tag_id}")
def remove_tag(
    document_id: int,
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Remove a tag from a document."""
    success = remove_tag_from_document(db, document_id, tag_id, current_user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document or tag not found")
    return {"message": "Tag removed from document"}


@router.put("/documents/{document_id}/category")
def set_category(
    document_id: int,
    category_id: Optional[int],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Set the category for a document."""
    success = set_document_category(db, document_id, category_id, current_user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document or category not found")
    return {"message": "Category updated"}


@router.get("/documents/{document_id}/suggest-tags")
def suggest_tags(
    document_id: int,
    max_suggestions: int = 5,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get tag suggestions based on document content."""
    document = db.query(models.Document).filter(
        models.Document.id == document_id,
        models.Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    
    # Get document text from chunks
    chunks = db.query(models.DocumentChunk).filter(
        models.DocumentChunk.document_id == document_id
    ).limit(10).all()  # Use first 10 chunks for suggestions
    
    document_text = " ".join([chunk.text for chunk in chunks])
    
    suggestions = suggest_tags_from_content(db, current_user.id, document_text, max_suggestions)
    
    return {"suggestions": suggestions}


# Saved Searches
from app.db.saved_search_models import SavedSearch
from datetime import datetime


class SavedSearchCreate(BaseModel):
    name: str
    query: Optional[str] = None
    filters: dict = {}


class SavedSearchRead(BaseModel):
    id: int
    name: str
    query: Optional[str] = None
    filters: dict
    created_at: str
    last_used_at: Optional[str] = None
    use_count: int

    class Config:
        from_attributes = True


@router.post("/saved-searches", response_model=SavedSearchRead, status_code=status.HTTP_201_CREATED)
def create_saved_search(
    search_data: SavedSearchCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Save a search query with filters."""
    saved_search = SavedSearch(
        user_id=current_user.id,
        name=search_data.name,
        query=search_data.query,
        filters=search_data.filters,
    )
    db.add(saved_search)
    db.commit()
    db.refresh(saved_search)
    return SavedSearchRead(
        id=saved_search.id,
        name=saved_search.name,
        query=saved_search.query,
        filters=saved_search.filters,
        created_at=saved_search.created_at.isoformat(),
        last_used_at=saved_search.last_used_at.isoformat() if saved_search.last_used_at else None,
        use_count=saved_search.use_count,
    )


@router.get("/saved-searches", response_model=List[SavedSearchRead])
def list_saved_searches(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List all saved searches for the current user."""
    searches = db.query(SavedSearch).filter(
        SavedSearch.user_id == current_user.id
    ).order_by(SavedSearch.last_used_at.desc().nullslast(), SavedSearch.created_at.desc()).all()
    
    return [
        SavedSearchRead(
            id=s.id,
            name=s.name,
            query=s.query,
            filters=s.filters,
            created_at=s.created_at.isoformat(),
            last_used_at=s.last_used_at.isoformat() if s.last_used_at else None,
            use_count=s.use_count,
        )
        for s in searches
    ]


@router.post("/saved-searches/{search_id}/use")
def use_saved_search(
    search_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Mark a saved search as used and increment use count."""
    search = db.query(SavedSearch).filter(
        SavedSearch.id == search_id,
        SavedSearch.user_id == current_user.id
    ).first()
    
    if not search:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved search not found")
    
    search.last_used_at = datetime.utcnow()
    search.use_count += 1
    db.commit()
    
    return {"message": "Search marked as used"}


@router.delete("/saved-searches/{search_id}")
def delete_saved_search(
    search_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Delete a saved search."""
    search = db.query(SavedSearch).filter(
        SavedSearch.id == search_id,
        SavedSearch.user_id == current_user.id
    ).first()
    
    if not search:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved search not found")
    
    db.delete(search)
    db.commit()
    return {"message": "Saved search deleted"}
