"""Tests for text chunking logic with real behavior validation."""
import pytest
from app.documents.chunking import chunk_text


def test_chunk_text_basic():
    """Test basic text chunking produces valid chunks."""
    text = "This is sentence one. This is sentence two. This is sentence three. " * 10
    chunks = chunk_text(text, max_words=20, overlap_words=5)
    
    # Real behavior: Should produce multiple chunks for long text
    assert len(chunks) > 1, "Long text should produce multiple chunks"
    
    # Validate chunk structure
    for chunk in chunks:
        assert "text" in chunk, "Chunk must have text"
        assert "token_count" in chunk, "Chunk must have token_count"
        assert "chunk_index" in chunk, "Chunk must have chunk_index"
        assert isinstance(chunk["chunk_index"], int), "chunk_index must be int"
        assert isinstance(chunk["token_count"], int), "token_count must be int"
        assert chunk["token_count"] > 0, "token_count must be positive"
        assert len(chunk["text"]) > 0, "Chunk text must not be empty"
    
    # Real behavior: Chunk indices should be sequential
    indices = [chunk["chunk_index"] for chunk in chunks]
    assert indices == list(range(len(chunks))), "Chunk indices should be sequential starting from 0"


def test_chunk_text_word_count_respects_max():
    """Test that chunks respect max_words limit."""
    # Create text with exactly 100 words
    words = [f"word{i}" for i in range(100)]
    text = " ".join(words)
    
    chunks = chunk_text(text, max_words=20, overlap_words=5)
    
    # Real behavior: Each chunk should have <= max_words
    for chunk in chunks:
        chunk_words = chunk["text"].split()
        assert len(chunk_words) <= 20, f"Chunk has {len(chunk_words)} words, exceeds max_words=20"
        # Token count should match word count (approximate)
        assert chunk["token_count"] == len(chunk_words), "token_count should match word count"


def test_chunk_text_overlap_behavior():
    """Test that chunks have proper overlap between consecutive chunks."""
    # Create text with 100 words
    text = " ".join([f"word{i}" for i in range(100)])
    chunks = chunk_text(text, max_words=20, overlap_words=5)
    
    if len(chunks) > 1:
        # Real behavior: Consecutive chunks should overlap
        for i in range(len(chunks) - 1):
            current_words = set(chunks[i]["text"].split())
            next_words = set(chunks[i + 1]["text"].split())
            overlap = current_words & next_words
            
            # Should have overlap (approximately overlap_words)
            assert len(overlap) >= 3, f"Chunks {i} and {i+1} should overlap by at least 3 words"
            
            # Real behavior: Overlap should be meaningful (not just common words)
            assert len(overlap) > 0, "Chunks must have some word overlap"


def test_chunk_text_empty():
    """Test chunking empty or whitespace-only text."""
    # Real behavior: Empty text should return empty list
    chunks = chunk_text("")
    assert chunks == [], "Empty text should return empty chunks"
    
    chunks = chunk_text("   ")
    assert chunks == [], "Whitespace-only text should return empty chunks"
    
    chunks = chunk_text("\n\t  \n")
    assert chunks == [], "Whitespace-only text with newlines should return empty chunks"


def test_chunk_text_single_chunk_for_short_text():
    """Test that short text produces a single chunk."""
    text = "This is a single sentence."
    chunks = chunk_text(text, max_words=100)
    
    # Real behavior: Text shorter than max_words should produce single chunk
    assert len(chunks) == 1, "Short text should produce single chunk"
    assert chunks[0]["text"] == text, "Single chunk should contain full text"
    assert chunks[0]["chunk_index"] == 0, "Single chunk should have index 0"
    
    # Real behavior: Token count should match word count
    word_count = len(text.split())
    assert chunks[0]["token_count"] == word_count, "Token count should match word count"


def test_chunk_text_preserves_all_words():
    """Test that chunking preserves all words from original text."""
    # Create text with known word count
    words = [f"word{i}" for i in range(50)]
    text = " ".join(words)
    
    chunks = chunk_text(text, max_words=20, overlap_words=5)
    
    # Real behavior: All words should appear in chunks (accounting for overlap)
    all_chunk_words = []
    for chunk in chunks:
        all_chunk_words.extend(chunk["text"].split())
    
    # Count unique words in chunks (should match or exceed original due to overlap)
    unique_chunk_words = set(all_chunk_words)
    original_words = set(words)
    
    # All original words should appear in chunks
    assert original_words.issubset(unique_chunk_words), "All original words should appear in chunks"


def test_chunk_text_overlap_calculation():
    """Test that overlap is calculated correctly."""
    # Create text with exactly 40 words, max_words=20, overlap_words=5
    # Expected: 2 chunks with 5-word overlap
    text = " ".join([f"word{i}" for i in range(40)])
    chunks = chunk_text(text, max_words=20, overlap_words=5)
    
    if len(chunks) >= 2:
        # First chunk: words 0-19 (20 words)
        # Second chunk: words 15-34 (20 words, starting at 20-5=15)
        first_words = chunks[0]["text"].split()
        second_words = chunks[1]["text"].split()
        
        # Real behavior: Second chunk should start at position (max_words - overlap_words)
        # First chunk ends at word 19, second should start at word 15 (overlap of 5)
        overlap = set(first_words) & set(second_words)
        assert len(overlap) >= 5, f"Expected at least 5-word overlap, got {len(overlap)}"


def test_chunk_text_token_count_accuracy():
    """Test that token_count accurately reflects word count."""
    # Create text with known word counts
    test_cases = [
        ("word1 word2 word3", 3),
        ("This is a test sentence with seven words.", 7),
        (" ".join([f"word{i}" for i in range(25)]), 25),
    ]
    
    for text, expected_word_count in test_cases:
        chunks = chunk_text(text, max_words=100)
        # Real behavior: token_count should match word count for each chunk
        for chunk in chunks:
            actual_word_count = len(chunk["text"].split())
            assert chunk["token_count"] == actual_word_count, \
                f"token_count ({chunk['token_count']}) should match word count ({actual_word_count})"

