"""
Chat routes for FastAPI.

Phase 7 spec: API endpoints for chat sessions and messages with RAG integration.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from app.db.base import get_db
from app.db import models
from app.db.schemas import ChatSessionRead, ChatMessageRead
from app.auth.dependencies import get_current_user
from app.embeddings.provider import EmbeddingsProvider, get_embeddings_provider
from app.vectorstore.faiss_store import VectorStore, get_vector_store
from app.rag.chain import RagChain, LlmClient, get_llm_client
from app.chat.service import (
    create_chat_session,
    list_chat_sessions_for_user,
    get_chat_session_for_user,
    list_messages_for_session,
    get_all_chat_messages_for_user,
    delete_chat_session,
    delete_all_chat_history_for_user,
    handle_user_message,
)

router = APIRouter()


# Request models
class ChatSessionCreate(BaseModel):
    """Request model for creating a chat session."""
    title: str | None = None


class ChatMessageCreate(BaseModel):
    """Request model for creating a chat message."""
    content: str


@router.post("/sessions", response_model=ChatSessionRead, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Create a new chat session.
    
    Args:
        payload: ChatSessionCreate with optional title
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        ChatSessionRead with created session details
    """
    session = create_chat_session(db, current_user, title=payload.title)
    return ChatSessionRead.model_validate(session)


@router.get("/sessions", response_model=List[ChatSessionRead])
def list_sessions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    List all chat sessions for the current user.
    
    Args:
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        List of ChatSessionRead schemas
    """
    sessions = list_chat_sessions_for_user(db, current_user)
    return [ChatSessionRead.model_validate(s) for s in sessions]


@router.get("/sessions/{session_id}", response_model=List[ChatMessageRead])
def get_session_messages(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Get all messages for a specific chat session.
    
    Args:
        session_id: Chat session ID
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        List of ChatMessageRead schemas
    
    Raises:
        HTTPException: 404 if session not found or not owned by user
    """
    messages = list_messages_for_session(db, current_user, session_id)
    return [ChatMessageRead.model_validate(m) for m in messages]


@router.patch("/sessions/{session_id}/title", response_model=ChatSessionRead)
def update_session_title(
    session_id: int,
    title: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Update the title of a chat session.
    
    Args:
        session_id: Chat session ID
        title: New title for the session
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        Updated ChatSessionRead
    
    Raises:
        HTTPException: 404 if session not found or not owned by user
    """
    from app.chat.service import get_chat_session_for_user
    session = get_chat_session_for_user(db, current_user, session_id)
    session.title = title
    db.commit()
    db.refresh(session)
    return ChatSessionRead.model_validate(session)


@router.get("/messages/all", response_model=List[ChatMessageRead])
def get_all_messages(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Get all chat messages across all sessions for the current user.
    
    This endpoint returns all messages from all chat sessions, ordered chronologically.
    
    Args:
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        List of ChatMessageRead schemas from all sessions
    """
    messages = get_all_chat_messages_for_user(db, current_user)
    return [ChatMessageRead.model_validate(m) for m in messages]


@router.delete("/sessions/all")
def delete_all_chat_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Delete all chat history (sessions and messages) for the current user.
    
    WARNING: This action cannot be undone. All chat sessions and messages will be permanently deleted.
    
    Args:
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        Dictionary with deletion summary
    """
    result = delete_all_chat_history_for_user(db, current_user)
    return result


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Delete a specific chat session and all its messages.
    
    Args:
        session_id: Chat session ID to delete
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        Dictionary with deletion summary
    
    Raises:
        HTTPException: 404 if session not found or not owned by user
    """
    result = delete_chat_session(db, current_user, session_id)
    return result


@router.post(
    "/sessions/{session_id}/message",
    response_model=ChatMessageRead,
)
async def send_message(
    session_id: int,
    payload: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    embeddings_provider: EmbeddingsProvider = Depends(get_embeddings_provider),
    vector_store: VectorStore = Depends(get_vector_store),
    llm_client: LlmClient = Depends(get_llm_client),
):
    """
    Send a message to a chat session and get a RAG-powered response.
    
    This endpoint:
    1. Creates a user message in the session
    2. Runs the RAG pipeline to generate an answer
    3. Creates an assistant message with the answer and citations
    4. Returns the assistant message
    
    Args:
        session_id: Chat session ID
        payload: ChatMessageCreate with message content
        db: Database session
        current_user: Current authenticated user
        embeddings_provider: Embeddings provider instance
        vector_store: Vector store instance
        llm_client: LLM client instance
    
    Returns:
        ChatMessageRead with assistant response and citations
    
    Raises:
        HTTPException: 404 if session not found or not owned by user
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Validate input
    if not payload.content or not payload.content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content cannot be empty"
        )
    
    try:
        # Create RAG chain
        rag_chain = RagChain(
            embeddings_provider=embeddings_provider,
            vector_store=vector_store,
            llm_client=llm_client,
        )
        
        # Handle user message through RAG pipeline
        _, assistant_msg, _ = await handle_user_message(
            db=db,
            user=current_user,
            session_id=session_id,
            question=payload.content.strip(),
            rag_chain=rag_chain,
        )
        
        # Validate response
        if not assistant_msg or not assistant_msg.content:
            logger.error(f"Empty assistant message returned for session {session_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate response"
            )
        
        return ChatMessageRead.model_validate(assistant_msg)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except RuntimeError as e:
        # RuntimeError usually means missing configuration (API keys, etc.)
        logger.error(f"Configuration error in send_message endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Configuration error: {str(e)}. Please check your .env file and ensure API keys are set."
        )
    except Exception as e:
        logger.error(f"Error in send_message endpoint: {e}", exc_info=True)
        error_msg = str(e)
        if len(error_msg) > 200:
            error_msg = error_msg[:200] + "..."
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing message: {error_msg}"
        )
