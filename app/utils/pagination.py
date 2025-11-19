"""Pagination utilities."""
from typing import List, TypeVar, Generic
from sqlalchemy.orm import Query
from math import ceil

T = TypeVar('T')


def paginate_query(query: Query, page: int = 1, page_size: int = 10) -> tuple[List[T], int]:
    """
    Paginate a SQLAlchemy query.
    
    Args:
        query: SQLAlchemy query object
        page: Page number (1-indexed)
        page_size: Number of items per page
    
    Returns:
        Tuple of (items, total_count)
    """
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 10
    if page_size > 100:
        page_size = 100  # Max page size
    
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return items, total


def calculate_total_pages(total: int, page_size: int) -> int:
    """Calculate total number of pages."""
    return ceil(total / page_size) if total > 0 else 0

