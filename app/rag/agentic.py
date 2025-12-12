"""
Agentic RAG: LLM decides when to search vs answer directly.
"""
import logging
from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.db import models
from app.rag.chain import RagChain

logger = logging.getLogger(__name__)


async def agentic_rag_decision(
    rag_chain: RagChain,
    db: Session,
    user: models.User,
    session: models.ChatSession,
    question: str,
) -> Tuple[str, list, Dict[str, Any], bool]:
    """
    Agentic RAG: Let LLM decide whether to search or answer directly.
    
    Args:
        rag_chain: RAG chain instance
        db: Database session
        user: User model
        session: Chat session
        question: User question
    
    Returns:
        Tuple of (answer, citations, metadata, used_rag)
        used_rag: True if RAG was used, False if direct answer
    """
    from app.chat.history import get_recent_messages
    from app.rag.prompts import build_messages
    
    # Step 1: Ask LLM if it needs to search
    decision_prompt = f"""You are a helpful assistant. A user asked: "{question}"

Do you need to search through the user's documents to answer this question, or can you answer it directly with your general knowledge?

Consider:
- If the question is about specific documents, files, or personal information → SEARCH
- If the question is general knowledge or doesn't require specific documents → DIRECT

Respond with only one word: SEARCH or DIRECT"""

    decision_messages = [
        {"role": "system", "content": "You are a decision-making assistant."},
        {"role": "user", "content": decision_prompt}
    ]
    
    try:
        decision_response = await rag_chain._llm.generate(decision_messages)
        decision = decision_response.strip().upper()
        
        logger.info(f"Agentic RAG decision: {decision} for question: {question[:50]}")
        
        if "SEARCH" in decision or "DOCUMENT" in decision:
            # Use RAG
            answer, citations, analysis_info = await rag_chain.answer_question(
                db=db,
                user=user,
                session=session,
                question=question,
                top_k=10
            )
            analysis_info["agentic_decision"] = "search"
            return answer, citations, analysis_info, True
        else:
            # Answer directly
            history = get_recent_messages(db, session, limit=10)
            messages = build_messages(context="", history=history, question=question)
            answer = await rag_chain._llm.generate(messages)
            
            analysis_info = {
                "agentic_decision": "direct",
                "confidence_score": 0.7,  # Lower confidence for direct answers
            }
            
            return answer, [], analysis_info, False
            
    except Exception as e:
        logger.warning(f"Agentic decision failed: {e}, falling back to RAG")
        # Fallback to RAG
        answer, citations, analysis_info = await rag_chain.answer_question(
            db=db,
            user=user,
            session=session,
            question=question,
            top_k=10
        )
        analysis_info["agentic_decision"] = "fallback_rag"
        return answer, citations, analysis_info, True

