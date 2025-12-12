"""
Chat service for managing chat sessions and messages.

Phase 7 spec: Business logic for chat operations including RAG integration.
"""
from datetime import datetime
from typing import List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import logging

from app.db import models
from app.rag.chain import RagChain
from app.chat.history import get_recent_messages_for_session

logger = logging.getLogger(__name__)


def create_chat_session(
    db: Session,
    user: models.User,
    title: str | None = None,
) -> models.ChatSession:
    """
    Create a new chat session for the given user.
    
    Args:
        db: Database session
        user: User model instance
        title: Optional session title (defaults to "New chat")
    
    Returns:
        Created ChatSession model instance
    """
    session = models.ChatSession(
        user_id=user.id,
        title=title or "New chat",
        created_at=datetime.utcnow()
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def list_chat_sessions_for_user(
    db: Session,
    user: models.User,
) -> list[models.ChatSession]:
    """
    Return all chat sessions for the given user, ordered by created_at desc.
    
    Args:
        db: Database session
        user: User model instance
    
    Returns:
        List of ChatSession model instances
    """
    return (
        db.query(models.ChatSession)
        .filter(models.ChatSession.user_id == user.id)
        .order_by(models.ChatSession.created_at.desc())
        .all()
    )


def delete_chat_session(
    db: Session,
    user: models.User,
    session_id: int,
) -> dict:
    """
    Delete a specific chat session and all its messages.
    
    Args:
        db: Database session
        user: User model instance
        session_id: Chat session ID to delete
    
    Returns:
        Dictionary with deletion summary
    
    Raises:
        HTTPException: 404 if session not found or not owned by user
    """
    # Verify session ownership
    session = get_chat_session_for_user(db, user, session_id)
    
    # Delete all messages first (due to foreign key constraints)
    messages_deleted = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id == session.id)
        .delete(synchronize_session=False)
    )
    
    # Delete the session
    db.delete(session)
    db.commit()
    
    return {
        "deleted_session_id": session_id,
        "deleted_messages": messages_deleted,
        "message": f"Successfully deleted session and {messages_deleted} messages"
    }


def get_chat_session_for_user(
    db: Session,
    user: models.User,
    session_id: int,
) -> models.ChatSession:
    """
    Get a chat session by id and ensure it belongs to this user.
    
    Args:
        db: Database session
        user: User model instance
        session_id: Chat session ID to fetch
    
    Returns:
        ChatSession model instance
    
    Raises:
        HTTPException: 404 if session not found or not owned by user
    """
    session = (
        db.query(models.ChatSession)
        .filter(
            models.ChatSession.id == session_id,
            models.ChatSession.user_id == user.id
        )
        .first()
    )
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    return session


def get_all_chat_messages_for_user(
    db: Session,
    user: models.User,
) -> list[models.ChatMessage]:
    """
    Get all chat messages across all sessions for a user.
    
    Args:
        db: Database session
        user: User model instance
    
    Returns:
        List of all ChatMessage model instances, ordered by created_at
    """
    # Get all sessions for the user
    sessions = list_chat_sessions_for_user(db, user)
    session_ids = [s.id for s in sessions]
    
    if not session_ids:
        return []
    
    # Get all messages from all sessions
    messages = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id.in_(session_ids))
        .order_by(models.ChatMessage.created_at.asc())
        .all()
    )
    
    return messages


def list_messages_for_session(
    db: Session,
    user: models.User,
    session_id: int,
) -> list[models.ChatMessage]:
    """
    Return all messages for a session, after verifying user ownership.
    
    Args:
        db: Database session
        user: User model instance
        session_id: Chat session ID
    
    Returns:
        List of ChatMessage model instances, ordered chronologically
    
    Raises:
        HTTPException: 404 if session not found or not owned by user
    """
    # Verify session ownership
    session = get_chat_session_for_user(db, user, session_id)
    
    # Fetch messages
    messages = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id == session.id)
        .order_by(models.ChatMessage.created_at.asc())
        .all()
    )
    
    return messages


def delete_all_chat_history_for_user(
    db: Session,
    user: models.User,
) -> dict:
    """
    Delete all chat history (sessions and messages) for a user.
    
    Args:
        db: Database session
        user: User model instance
    
    Returns:
        Dictionary with deletion summary
    """
    # Get all sessions for the user
    sessions = list_chat_sessions_for_user(db, user)
    session_ids = [s.id for s in sessions]
    
    if not session_ids:
        return {
            "deleted_sessions": 0,
            "deleted_messages": 0,
            "message": "No chat history found"
        }
    
    # Delete all messages first (due to foreign key constraints)
    messages_deleted = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id.in_(session_ids))
        .delete(synchronize_session=False)
    )
    
    # Delete all sessions
    sessions_deleted = (
        db.query(models.ChatSession)
        .filter(models.ChatSession.id.in_(session_ids))
        .delete(synchronize_session=False)
    )
    
    db.commit()
    
    return {
        "deleted_sessions": sessions_deleted,
        "deleted_messages": messages_deleted,
        "message": f"Successfully deleted {sessions_deleted} sessions and {messages_deleted} messages"
    }


async def handle_user_message(
    db: Session,
    user: models.User,
    session_id: int,
    question: str,
    rag_chain: RagChain,
) -> Tuple[models.ChatMessage, models.ChatMessage, List[Dict], Dict[str, Any]]:
    """
    Handle a user sending a new question to a chat session.
    
    Steps:
    1. Verify the session belongs to the user
    2. Create and persist a ChatMessage for the user question
    3. Call RagChain.answer_question to get (answer, citations)
    4. Create and persist a ChatMessage for the assistant answer,
       storing citations in retrieved_chunks
    5. Return (user_message, assistant_message, citations)
    
    Args:
        db: Database session
        user: User model instance
        session_id: Chat session ID
        question: User's question string
        rag_chain: RagChain instance for RAG processing
    
    Returns:
        Tuple of (user_message, assistant_message, citations_list, analysis_info)
    
    Raises:
        HTTPException: 404 if session not found or not owned by user
    """
    try:
        # 1. Verify session ownership
        logger.info(f"Handling user message for user {user.id}, session {session_id}")
        session = get_chat_session_for_user(db, user, session_id)
        logger.debug(f"Session {session_id} verified for user {user.id}")
        
        # 2. Create user message
        user_msg = models.ChatMessage(
            session_id=session.id,
            role=models.ChatRole.USER,
            content=question,
            created_at=datetime.utcnow()
        )
        db.add(user_msg)
        db.commit()
        db.refresh(user_msg)
        logger.info(f"Created user message {user_msg.id} for session {session_id}")
        
        # 3. Call RAG chain (exclude the current user message from history to avoid duplication)
        logger.info(f"Calling RAG chain for question: {question[:50]}...")
        try:
            import asyncio
            # Add timeout to RAG chain call to prevent hanging
            answer_text, citations, analysis_info = await asyncio.wait_for(
                rag_chain.answer_question(
                    db=db,
                    user=user,
                    session=session,
                    question=question,
                    top_k=10,
                    exclude_message_id=user_msg.id,  # Exclude current user message from history
                ),
                timeout=50.0  # 50 second timeout for RAG processing
            )
            logger.info(f"RAG chain returned answer ({len(answer_text)} chars) with {len(citations)} citations")
        except asyncio.TimeoutError:
            logger.error(f"RAG chain timed out for question: {question[:50]}...")
            answer_text = "I'm sorry, but processing your question took too long. Please try rephrasing it or asking a simpler question."
            citations = []
            analysis_info = {"confidence_score": 0.0}
        except TimeoutError as te:
            # LLM generation timeout
            logger.error(f"LLM generation timed out: {te}")
            answer_text = "I'm sorry, but generating a response took too long. Please try rephrasing your question or check your API keys."
            citations = []
            analysis_info = {"confidence_score": 0.0}
        except Exception as e:
            logger.error(f"Error in RAG chain: {e}", exc_info=True)
            error_msg = str(e)
            # Truncate very long error messages
            if len(error_msg) > 300:
                error_msg = error_msg[:300] + "..."
            # Provide fallback answer with error details
            answer_text = f"I encountered an error while processing your question: {error_msg}. Please check the backend logs for more details or try again."
            citations = []
            analysis_info = {"confidence_score": 0.0}
        
        # If image analysis was performed, include it in the response
        if analysis_info and analysis_info.get("has_analysis") and analysis_info.get("image_analyses"):
            logger.info(f"Including {len(analysis_info['image_analyses'])} image analyses in response")
            is_comprehensive = analysis_info.get("is_comprehensive_scan", False)
            
            analysis_section = "\n\n" + "="*60 + "\n"
            if is_comprehensive:
                analysis_section += "📸 COMPREHENSIVE IMAGE SCAN DETAILS\n"
                analysis_section += "(All details extracted from image during upload)\n"
            else:
                analysis_section += "📸 IMAGE ANALYSIS (CLIP + BLIP-2)\n"
            analysis_section += "="*60 + "\n\n"
            for img_analysis in analysis_info["image_analyses"]:
                analysis_text = img_analysis.get("analysis_text", "")
                if analysis_text:
                    analysis_section += analysis_text + "\n\n" + "-"*60 + "\n\n"
            answer_text = answer_text + analysis_section
        
        # Ensure answer is not empty
        if not answer_text or not answer_text.strip():
            logger.warning("RAG chain returned empty answer, using fallback")
            answer_text = "I couldn't generate a response. Please try rephrasing your question."
        
        # 4. Create assistant message
        assistant_msg = models.ChatMessage(
            session_id=session.id,
            role=models.ChatRole.ASSISTANT,
            content=answer_text,
            retrieved_chunks=citations,
            created_at=datetime.utcnow()
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)
        logger.info(f"Created assistant message {assistant_msg.id} for session {session_id}")
        
        # Trigger webhook for chat message
        try:
            from app.admin.webhooks import trigger_webhook
            await trigger_webhook(
                db=db,
                user_id=user.id,
                event_type="chat.message",
                payload={
                    "session_id": session.id,
                    "message_id": assistant_msg.id,
                    "question": question,
                    "answer_length": len(answer_text),
                    "citations_count": len(citations),
                    "confidence_score": analysis_info.get("confidence_score") if analysis_info and isinstance(analysis_info, dict) else None,
                }
            )
        except Exception as e:
            logger.warning(f"Failed to trigger webhook for chat message: {e}")
        
        # 5. Auto-generate title if session doesn't have one yet (use first user message)
        if not session.title or session.title == "New chat":
            # Generate a short title from the first user message (max 50 chars)
            title = question[:50].strip()
            if len(question) > 50:
                title += "..."
            session.title = title
            db.commit()
            logger.info(f"Auto-generated title for session {session_id}: {title}")
        
        # 6. Return both messages, citations, and analysis_info
        return (user_msg, assistant_msg, citations, analysis_info)
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 404 for session not found)
        raise
    except Exception as e:
        logger.error(f"Unexpected error in handle_user_message: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat message: {str(e)}"
        )
