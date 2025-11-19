"""
Pydantic compatibility helper for v1/v2 compatibility.
"""
from typing import TypeVar, Type
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)


def from_orm(model_class: Type[T], obj: any) -> T:
    """
    Convert SQLAlchemy ORM object to Pydantic model.
    
    Works with both Pydantic v1 (from_orm) and v2 (model_validate).
    
    Args:
        model_class: Pydantic model class
        obj: SQLAlchemy ORM object
    
    Returns:
        Pydantic model instance
    """
    try:
        # Try Pydantic v2 method first
        return model_class.model_validate(obj)
    except (AttributeError, TypeError):
        # Fall back to Pydantic v1 method
        return model_class.from_orm(obj)

