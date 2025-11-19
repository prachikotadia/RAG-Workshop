"""Hallucination detection and guard for RAG responses."""
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def check_hallucination(
    answer: str,
    citations: List[Dict[str, Any]],
    question: str,
    context: str
) -> tuple[bool, str]:
    """
    Check if the answer might be hallucinated (not grounded in context).
    
    Args:
        answer: Generated answer
        citations: List of citation dictionaries
        question: Original question
        context: Retrieved context
    
    Returns:
        Tuple of (is_hallucinated, warning_message)
    """
    # If no citations, likely hallucination
    if not citations:
        return True, "Answer generated without any document citations"
    
    # Check if answer mentions specific facts not in context
    answer_lower = answer.lower()
    context_lower = context.lower()
    
    # Extract key entities/numbers from answer
    import re
    # Find numbers, dates, names (simple heuristic)
    numbers = re.findall(r'\d+', answer)
    dates = re.findall(r'\d{4}|\d{1,2}/\d{1,2}/\d{2,4}', answer)
    
    # Check if numbers/dates in answer are in context
    missing_facts = []
    for num in numbers[:5]:  # Check first 5 numbers
        if num not in context_lower and len(num) > 2:  # Ignore small numbers
            missing_facts.append(f"number {num}")
    
    for date in dates[:3]:  # Check first 3 dates
        if date not in context_lower:
            missing_facts.append(f"date {date}")
    
    if missing_facts:
        return True, f"Answer contains facts not found in context: {', '.join(missing_facts)}"
    
    # Check answer length vs context coverage
    if len(answer) > len(context) * 2:
        return True, "Answer is significantly longer than provided context"
    
    return False, ""


def add_hallucination_warning(
    answer: str,
    is_hallucinated: bool,
    warning: str
) -> str:
    """
    Add hallucination warning to answer if detected.
    
    Args:
        answer: Original answer
        is_hallucinated: Whether hallucination was detected
        warning: Warning message
    
    Returns:
        Answer with optional warning
    """
    if is_hallucinated:
        warning_text = f"\n\n⚠️ Warning: {warning}. Please verify this information against your documents."
        return answer + warning_text
    return answer

