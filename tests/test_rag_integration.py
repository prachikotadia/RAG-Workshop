"""
Integration tests for RAG pipeline end-to-end.
"""
import pytest
from app.rag.chain import RagChain
from app.embeddings.provider import EmbeddingsProvider
from app.vectorstore.faiss_store import VectorStore
from app.rag.groq_client import GroqLlmClient
from app.db import models
from app.config import get_settings


@pytest.fixture
def rag_chain(db_session, test_user):
    """Create a RAG chain for testing."""
    settings = get_settings()
    
    # Use HuggingFace embeddings for testing (no API key needed)
    from app.embeddings.huggingface import HuggingFaceEmbeddingsProvider
    embeddings = HuggingFaceEmbeddingsProvider(
        model_name=settings.huggingface_model,
        cache_dir=settings.huggingface_cache_dir
    )
    
    # Create vector store
    vector_store = VectorStore(base_dir="test_data/vectorstores")
    
    # Create LLM client (use Groq if available, otherwise skip)
    try:
        if settings.groq_api_key:
            llm = GroqLlmClient(api_key=settings.groq_api_key, model=settings.groq_model)
        else:
            pytest.skip("No LLM API key configured")
    except Exception:
        pytest.skip("LLM client not available")
    
    return RagChain(
        embeddings_provider=embeddings,
        vector_store=vector_store,
        llm_client=llm
    )


@pytest.mark.asyncio
async def test_rag_pipeline_end_to_end(db_session, test_user, rag_chain):
    """Test complete RAG pipeline: embed, search, context, LLM."""
    # Create a test document
    from app.documents.service import process_and_index_document
    from pathlib import Path
    import tempfile
    
    # Create a test text file
    test_content = """
    Python is a high-level programming language.
    It is known for its simplicity and readability.
    Python supports multiple programming paradigms.
    """
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(test_content)
        test_file_path = Path(f.name)
    
    try:
        # Process document
        from fastapi import UploadFile
        from io import BytesIO
        
        with open(test_file_path, 'rb') as file:
            content = file.read()
            upload_file = UploadFile(
                filename="test.txt",
                file=BytesIO(content)
            )
            
            # Process and index
            document = await process_and_index_document(
                upload_file=upload_file,
                user=test_user,
                db=db_session,
                embeddings_provider=rag_chain._embeddings,
                vector_store=rag_chain._vector_store
            )
            
            assert document is not None
            assert document.status == models.DocumentStatus.READY
        
        # Create a chat session
        from app.chat.service import create_chat_session
        session = create_chat_session(db_session, test_user, title="Test Session")
        
        # Test RAG query
        answer, citations, analysis_info = await rag_chain.answer_question(
            db=db_session,
            user=test_user,
            session=session,
            question="What is Python?",
            top_k=5
        )
        
        # Assertions
        assert answer is not None
        assert len(answer) > 0
        assert isinstance(citations, list)
        assert len(citations) > 0  # Should have at least one citation
        
        # Verify citation structure
        citation = citations[0]
        assert "document_id" in citation
        assert "document_title" in citation
        assert "chunk_id" in citation
        
    finally:
        # Cleanup
        if test_file_path.exists():
            test_file_path.unlink()


@pytest.mark.asyncio
async def test_rag_with_no_documents(db_session, test_user, rag_chain):
    """Test RAG pipeline when user has no documents."""
    from app.chat.service import create_chat_session
    session = create_chat_session(db_session, test_user, title="Empty Session")
    
    # Query without documents
    answer, citations, analysis_info = await rag_chain.answer_question(
        db=db_session,
        user=test_user,
        session=session,
        question="What is machine learning?",
        top_k=5
    )
    
    # Should still return an answer (from LLM general knowledge)
    assert answer is not None
    assert len(answer) > 0
    # Citations should be empty
    assert len(citations) == 0


@pytest.mark.asyncio
async def test_hybrid_search_integration(db_session, test_user, rag_chain):
    """Test that hybrid search works in RAG pipeline."""
    # This test verifies that advanced RAG features are integrated
    settings = get_settings()
    
    if not settings.enable_hybrid_search:
        pytest.skip("Hybrid search not enabled")
    
    # Create test document with specific keywords
    from pathlib import Path
    import tempfile
    
    test_content = "Machine learning is a subset of artificial intelligence."
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(test_content)
        test_file_path = Path(f.name)
    
    try:
        from fastapi import UploadFile
        from io import BytesIO
        from app.documents.service import process_and_index_document
        
        with open(test_file_path, 'rb') as file:
            content = file.read()
            upload_file = UploadFile(
                filename="ml_test.txt",
                file=BytesIO(content)
            )
            
            document = await process_and_index_document(
                upload_file=upload_file,
                user=test_user,
                db=db_session,
                embeddings_provider=rag_chain._embeddings,
                vector_store=rag_chain._vector_store
            )
        
        # Query using keyword that should match
        from app.chat.service import create_chat_session
        session = create_chat_session(db_session, test_user, title="ML Test")
        
        answer, citations, _ = await rag_chain.answer_question(
            db=db_session,
            user=test_user,
            session=session,
            question="What is machine learning?",
            top_k=5
        )
        
        # Should find the document
        assert len(citations) > 0
        
    finally:
        if test_file_path.exists():
            test_file_path.unlink()

