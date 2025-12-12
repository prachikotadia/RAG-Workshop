from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List, Dict, Any
import enum
from app.db.models import DocumentStatus, ChatRole


# User schemas
class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    """User read model (Phase 2 spec: UserRead)."""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2


# Alias for Phase 2 spec compatibility
UserRead = UserResponse


# Auth schemas (Phase 3)
class UserLogin(BaseModel):
    """Login request schema."""
    email: EmailStr
    password: str


class Token(BaseModel):
    """JWT access token response (Phase 3 spec)."""
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    """JWT token payload structure (Phase 3 spec)."""
    sub: str | None = None  # email (subject)
    user_id: int | None = None
    exp: int | None = None


# Additional auth schemas (beyond Phase 3)
class TokenData(BaseModel):
    email: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# Document schemas
class DocumentBase(BaseModel):
    title: str
    original_filename: str


class DocumentCreate(DocumentBase):
    pass


class DocumentResponse(DocumentBase):
    """Document read model (Phase 2 spec: DocumentRead)."""
    id: int
    user_id: int
    status: DocumentStatus
    num_chunks: int
    # New optional fields - will be available after migration
    # category_id: Optional[int] = None
    # file_size: Optional[int] = None
    # file_type: Optional[str] = None
    tags: List[Dict[str, Any]] = []  # List of tag objects
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2
    
    @classmethod
    def model_validate(cls, obj):
        """Custom model_validate to include tags."""
        if hasattr(obj, '__dict__'):
            # SQLAlchemy model
            # New fields are commented out until migration
            category_id = None  # getattr(obj, 'category_id', None)
            file_size = None  # getattr(obj, 'file_size', None)
            file_type = None  # getattr(obj, 'file_type', None)
            
            # Safely get tags (relationship might not work if table doesn't exist)
            tags = []
            if hasattr(obj, 'tags'):
                try:
                    tag_list = obj.tags.all() if hasattr(obj.tags, 'all') else obj.tags
                    tags = [
                        {"id": tag.id, "name": tag.name, "color": tag.color}
                        for tag in tag_list
                    ]
                except Exception:
                    # Tags table might not exist yet
                    tags = []
            
            data = {
                "id": obj.id,
                "user_id": obj.user_id,
                "title": obj.title,
                "original_filename": obj.original_filename,
                "status": obj.status,
                "num_chunks": obj.num_chunks,
                "category_id": category_id,
                "file_size": file_size,
                "file_type": file_type,
                "created_at": obj.created_at,
                "updated_at": obj.updated_at,
                "tags": tags,
            }
            return cls(**data)
        else:
            return super().model_validate(obj)


# Alias for Phase 2 spec compatibility
DocumentRead = DocumentResponse


class DocumentChunkResponse(BaseModel):
    id: int
    document_id: int
    chunk_index: int
    text: str
    token_count: int
    metadata: Dict[str, Any]  # Maps to chunk_metadata in model

    class Config:
        from_attributes = True  # Pydantic v2
    
    @classmethod
    def model_validate(cls, obj):
        """Custom model_validate to map chunk_metadata to metadata."""
        if hasattr(obj, '__dict__'):
            # SQLAlchemy model
            data = {
                "id": obj.id,
                "document_id": obj.document_id,
                "chunk_index": obj.chunk_index,
                "text": obj.text,
                "token_count": obj.token_count,
                "metadata": obj.chunk_metadata,  # Map chunk_metadata to metadata
            }
            return cls(**data)
        else:
            # Already a dict or Pydantic model
            return super().model_validate(obj)


# Chat schemas
class ChatSessionBase(BaseModel):
    title: Optional[str] = None


class ChatSessionCreate(ChatSessionBase):
    pass


class ChatSessionResponse(ChatSessionBase):
    """Chat session read model (Phase 2 spec: ChatSessionRead)."""
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2


# Alias for Phase 2 spec compatibility
ChatSessionRead = ChatSessionResponse


class ChatMessageBase(BaseModel):
    content: str


class ChatMessageCreate(ChatMessageBase):
    pass


class ChatMessageResponse(ChatMessageBase):
    """Chat message read model (Phase 2 spec: ChatMessageRead)."""
    id: int
    session_id: int
    role: ChatRole
    retrieved_chunks: List[Dict[str, Any]]
    created_at: datetime
    confidence_score: Optional[float] = None  # Confidence score if available

    class Config:
        from_attributes = True  # Pydantic v2
    
    @classmethod
    def model_validate(cls, obj):
        """Custom model_validate to extract confidence from metadata if stored."""
        if hasattr(obj, '__dict__'):
            # SQLAlchemy model - check if confidence is in retrieved_chunks metadata
            data = {
                "id": obj.id,
                "session_id": obj.session_id,
                "role": obj.role,
                "content": obj.content,
                "retrieved_chunks": obj.retrieved_chunks or [],
                "created_at": obj.created_at,
                "confidence_score": None,  # Will be extracted from metadata if available
            }
            # Try to extract confidence from message metadata (if stored in future)
            return cls(**data)
        else:
            return super().model_validate(obj)


# Alias for Phase 2 spec compatibility
ChatMessageRead = ChatMessageResponse


class ChatResponse(BaseModel):
    answer: str
    citations: List[Dict[str, Any]]


# Pagination schemas
class PaginatedResponse(BaseModel):
    items: List[Any] = []
    total: int = 0
    page: int = 1
    page_size: int = 10
    total_pages: int = 0


# User update schemas
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


# Search schemas
class DocumentSearchRequest(BaseModel):
    query: str
    page: int = 1
    page_size: int = 10


# Export schemas
class ExportFormat(str, enum.Enum):
    JSON = "json"
    CSV = "csv"
    TXT = "txt"

