"""Admin and statistics endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, extract, and_
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pydantic import BaseModel

from app.db.base import get_db
from app.db import models
from app.auth.dependencies import get_current_user

router = APIRouter()


@router.get("/stats")
async def get_user_stats(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get basic statistics for the current user."""
    # Document stats
    doc_stats = (
        db.query(
            func.count(models.Document.id).label("total_documents"),
            func.sum(models.Document.num_chunks).label("total_chunks"),
            func.sum(func.cast(models.Document.status == models.DocumentStatus.READY, models.Integer)).label("ready_documents")
        )
        .filter(models.Document.user_id == current_user.id)
        .first()
    )
    
    # Session stats
    session_count = (
        db.query(func.count(models.ChatSession.id))
        .filter(models.ChatSession.user_id == current_user.id)
        .scalar()
    )
    
    # Message stats
    message_count = (
        db.query(func.count(models.ChatMessage.id))
        .join(models.ChatSession)
        .filter(models.ChatSession.user_id == current_user.id)
        .scalar()
    )
    
    return {
        "user_id": current_user.id,
        "documents": {
            "total": doc_stats.total_documents or 0,
            "ready": doc_stats.ready_documents or 0,
            "total_chunks": doc_stats.total_chunks or 0
        },
        "chat_sessions": session_count or 0,
        "chat_messages": message_count or 0
    }


@router.get("/analytics/usage")
async def get_usage_analytics(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    days: int = 30
):
    """Get usage analytics: queries per day, popular documents, response times."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Queries per day (user messages)
    daily_queries = (
        db.query(
            func.date(models.ChatMessage.created_at).label("date"),
            func.count(models.ChatMessage.id).label("count")
        )
        .join(models.ChatSession)
        .filter(
            models.ChatSession.user_id == current_user.id,
            models.ChatMessage.role == models.ChatRole.USER,
            models.ChatMessage.created_at >= start_date
        )
        .group_by(func.date(models.ChatMessage.created_at))
        .order_by(func.date(models.ChatMessage.created_at))
        .all()
    )
    
    # Popular documents (most referenced in chat)
    # Get all messages with retrieved chunks
    messages_with_chunks = (
        db.query(models.ChatMessage)
        .join(models.ChatSession)
        .filter(
            models.ChatSession.user_id == current_user.id,
            models.ChatMessage.retrieved_chunks.isnot(None),
            models.ChatMessage.retrieved_chunks != []
        )
        .all()
    )
    
    # Count document references from citations
    doc_reference_count = {}
    for message in messages_with_chunks:
        if message.retrieved_chunks:
            for citation in message.retrieved_chunks:
                if isinstance(citation, dict) and 'document_id' in citation:
                    doc_id = citation['document_id']
                    doc_reference_count[doc_id] = doc_reference_count.get(doc_id, 0) + 1
    
    # Get document details for referenced documents
    if doc_reference_count:
        doc_ids = list(doc_reference_count.keys())
        documents = (
            db.query(models.Document.id, models.Document.title)
            .filter(
                models.Document.user_id == current_user.id,
                models.Document.id.in_(doc_ids)
            )
            .all()
        )
        popular_docs = [
            {
                "document_id": doc.id,
                "title": doc.title,
                "reference_count": doc_reference_count[doc.id]
            }
            for doc in documents
        ]
        popular_docs.sort(key=lambda x: x["reference_count"], reverse=True)
        popular_docs = popular_docs[:10]
    else:
        popular_docs = []
    
    # Format daily queries
    queries_by_day = [
        {"date": str(row.date), "count": row.count}
        for row in daily_queries
    ]
    
    return {
        "queries_by_day": queries_by_day,
        "popular_documents": popular_docs,
        "total_queries": sum(q["count"] for q in queries_by_day),
        "period_days": days
    }


@router.get("/analytics/documents")
async def get_document_insights(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get document insights: most referenced documents, chunk quality metrics."""
    # Most referenced documents - count from citations
    messages_with_chunks = (
        db.query(models.ChatMessage)
        .join(models.ChatSession)
        .filter(
            models.ChatSession.user_id == current_user.id,
            models.ChatMessage.retrieved_chunks.isnot(None),
            models.ChatMessage.retrieved_chunks != []
        )
        .all()
    )
    
    # Count document references
    doc_reference_count = {}
    for message in messages_with_chunks:
        if message.retrieved_chunks:
            for citation in message.retrieved_chunks:
                if isinstance(citation, dict) and 'document_id' in citation:
                    doc_id = citation['document_id']
                    doc_reference_count[doc_id] = doc_reference_count.get(doc_id, 0) + 1
    
    # Get document details
    if doc_reference_count:
        doc_ids = list(doc_reference_count.keys())
        documents = (
            db.query(models.Document.id, models.Document.title, models.Document.num_chunks)
            .filter(
                models.Document.user_id == current_user.id,
                models.Document.id.in_(doc_ids)
            )
            .all()
        )
        most_referenced = [
            {
                "document_id": doc.id,
                "title": doc.title,
                "num_chunks": doc.num_chunks,
                "times_referenced": doc_reference_count[doc.id]
            }
            for doc in documents
        ]
        most_referenced.sort(key=lambda x: x["times_referenced"], reverse=True)
        most_referenced = most_referenced[:10]
    else:
        most_referenced = []
    
    # Chunk quality metrics
    chunk_stats = (
        db.query(
            func.avg(models.DocumentChunk.token_count).label("avg_tokens"),
            func.min(models.DocumentChunk.token_count).label("min_tokens"),
            func.max(models.DocumentChunk.token_count).label("max_tokens"),
            func.count(models.DocumentChunk.id).label("total_chunks")
        )
        .join(models.Document)
        .filter(models.Document.user_id == current_user.id)
        .first()
    )
    
    return {
        "most_referenced_documents": most_referenced,
        "chunk_quality": {
            "average_tokens": float(chunk_stats.avg_tokens or 0),
            "min_tokens": chunk_stats.min_tokens or 0,
            "max_tokens": chunk_stats.max_tokens or 0,
            "total_chunks": chunk_stats.total_chunks or 0
        }
    }


@router.get("/analytics/activity")
async def get_user_activity(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    days: int = 30
):
    """Get user activity: session duration, questions asked, documents uploaded."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Questions asked (user messages)
    questions_asked = (
        db.query(func.count(models.ChatMessage.id))
        .join(models.ChatSession)
        .filter(
            models.ChatSession.user_id == current_user.id,
            models.ChatMessage.role == models.ChatRole.USER,
            models.ChatMessage.created_at >= start_date
        )
        .scalar() or 0
    )
    
    # Documents uploaded
    documents_uploaded = (
        db.query(func.count(models.Document.id))
        .filter(
            models.Document.user_id == current_user.id,
            models.Document.created_at >= start_date
        )
        .scalar() or 0
    )
    
    # Session duration (average)
    sessions = (
        db.query(models.ChatSession)
        .filter(
            models.ChatSession.user_id == current_user.id,
            models.ChatSession.created_at >= start_date
        )
        .all()
    )
    
    session_durations = []
    for session in sessions:
        messages = (
            db.query(models.ChatMessage)
            .filter(models.ChatMessage.session_id == session.id)
            .order_by(models.ChatMessage.created_at)
            .all()
        )
        if len(messages) >= 2:
            duration = (messages[-1].created_at - messages[0].created_at).total_seconds() / 60  # minutes
            session_durations.append(duration)
    
    avg_session_duration = sum(session_durations) / len(session_durations) if session_durations else 0
    
    # Activity by day
    daily_activity = (
        db.query(
            func.date(models.ChatMessage.created_at).label("date"),
            func.count(models.ChatMessage.id).label("messages")
        )
        .join(models.ChatSession)
        .filter(
            models.ChatSession.user_id == current_user.id,
            models.ChatMessage.created_at >= start_date
        )
        .group_by(func.date(models.ChatMessage.created_at))
        .order_by(func.date(models.ChatMessage.created_at))
        .all()
    )
    
    return {
        "questions_asked": questions_asked,
        "documents_uploaded": documents_uploaded,
        "average_session_duration_minutes": round(avg_session_duration, 2),
        "total_sessions": len(sessions),
        "daily_activity": [
            {"date": str(row.date), "messages": row.messages}
            for row in daily_activity
        ],
        "period_days": days
    }


@router.get("/analytics/performance")
async def get_performance_metrics(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    hours: int = 24,
):
    """Get performance metrics: average response time, embedding generation time, query analytics."""
    
    from app.utils.query_analytics import (
        get_query_statistics,
        get_slow_queries,
        get_strategy_comparison,
    )
    
    # Get query statistics
    query_stats = get_query_statistics(user_id=current_user.id, hours=hours)
    slow_queries = get_slow_queries(user_id=current_user.id, hours=hours, threshold_ms=3000.0, limit=10)
    strategy_comparison = get_strategy_comparison(hours=hours)
    
    # Document processing metrics
    documents = (
        db.query(models.Document)
        .filter(
            models.Document.user_id == current_user.id,
            models.Document.status == models.DocumentStatus.READY
        )
        .all()
    )
    
    avg_chunks = (
        db.query(func.avg(models.Document.num_chunks))
        .filter(
            models.Document.user_id == current_user.id,
            models.Document.status == models.DocumentStatus.READY
        )
        .scalar() or 0
    )
    
    total_chunks = (
        db.query(func.sum(models.Document.num_chunks))
        .filter(
            models.Document.user_id == current_user.id,
            models.Document.status == models.DocumentStatus.READY
        )
        .scalar() or 0
    )
    
    return {
        "query_analytics": query_stats,
        "slow_queries": slow_queries,
        "strategy_comparison": strategy_comparison,
        "average_chunks_per_document": round(float(avg_chunks), 2),
        "total_chunks_indexed": total_chunks,
        "total_documents_ready": len(documents),
        "average_response_time_ms": query_stats.get("avg_latency_ms", 0.0),
        "average_embedding_time_ms": 0,  # Would need tracking
    }


@router.post("/documents/bulk-delete", status_code=status.HTTP_204_NO_CONTENT)
async def bulk_delete_documents(
    document_ids: list[int],
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bulk delete multiple documents."""
    documents = (
        db.query(models.Document)
        .filter(
            models.Document.id.in_(document_ids),
            models.Document.user_id == current_user.id
        )
        .all()
    )
    
    if len(documents) != len(document_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Some documents not found or not owned by user"
        )
    
    from app.documents.service import delete_user_document
    from app.vectorstore.faiss_store import get_vector_store
    
    vector_store = get_vector_store()
    for document in documents:
        delete_user_document(db, current_user, document.id, vector_store)
    
    return None

