"""
AI-generated question suggestions for improved UX.
"""
import logging
from typing import List, Optional
from app.rag.groq_client import GroqLlmClient
from app.rag.chain import get_llm_client
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def generate_question_suggestions(
    conversation_history: List[dict],
    last_answer: str,
    max_suggestions: int = 5
) -> List[str]:
    """
    Generate AI-powered question suggestions based on conversation context.
    
    Args:
        conversation_history: List of previous messages in format [{"role": "user/assistant", "content": "..."}]
        last_answer: The most recent assistant answer
        max_suggestions: Maximum number of suggestions to generate
    
    Returns:
        List of suggested questions
    """
    try:
        llm_client = get_llm_client()
        
        # Build context from recent conversation
        recent_context = conversation_history[-6:] if len(conversation_history) > 6 else conversation_history
        context_str = "\n".join([
            f"{msg.get('role', 'user').title()}: {msg.get('content', '')[:200]}"
            for msg in recent_context
        ])
        
        prompt = f"""Based on the following conversation, generate {max_suggestions} relevant follow-up questions that would help the user explore the topic further.

Conversation:
{context_str}

Last Answer:
{last_answer[:500]}

Generate {max_suggestions} concise, specific questions (one per line) that:
1. Build on the information just provided
2. Explore related aspects of the topic
3. Are actionable and specific
4. Would be useful for the user

Format: Just list the questions, one per line, without numbering or bullets."""

        response = await llm_client.generate(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7,
        )
        
        # Parse suggestions
        suggestions = [
            line.strip()
            for line in response.strip().split('\n')
            if line.strip() and len(line.strip()) > 10 and len(line.strip()) < 150
        ]
        
        # Filter and limit
        suggestions = [s for s in suggestions if s.endswith('?') or any(word in s.lower() for word in ['what', 'how', 'why', 'when', 'where', 'who', 'explain', 'describe', 'tell'])]
        suggestions = suggestions[:max_suggestions]
        
        # Fallback if no good suggestions
        if not suggestions:
            suggestions = [
                "Can you provide more details?",
                "What are the key points?",
                "Are there any related topics?",
            ]
        
        logger.info(f"Generated {len(suggestions)} question suggestions")
        return suggestions
        
    except Exception as e:
        logger.error(f"Failed to generate question suggestions: {e}", exc_info=True)
        # Return generic fallback suggestions
        return [
            "Can you tell me more?",
            "What else should I know?",
            "Are there related documents?",
        ][:max_suggestions]


def get_simple_suggestions(last_answer: str) -> List[str]:
    """
    Generate simple keyword-based suggestions without LLM.
    Fallback when LLM is unavailable.
    """
    suggestions = []
    
    # Extract key topics from answer
    answer_lower = last_answer.lower()
    
    if "document" in answer_lower or "file" in answer_lower:
        suggestions.append("What other documents contain similar information?")
    
    if "image" in answer_lower or "picture" in answer_lower:
        suggestions.append("Can you show me similar images?")
    
    if "data" in answer_lower or "information" in answer_lower:
        suggestions.append("Can you provide more details?")
    
    if "process" in answer_lower or "how" in answer_lower:
        suggestions.append("What are the steps involved?")
    
    # Always include generic suggestions
    if len(suggestions) < 3:
        suggestions.extend([
            "What are the key points?",
            "Are there related topics?",
        ])
    
    return suggestions[:5]
