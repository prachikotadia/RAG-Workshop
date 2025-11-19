"""Tests for RAG chain with mocked components testing real behavior."""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from sqlalchemy.orm import Session
from app.rag.chain import RagChain, LlmClient
from app.embeddings.provider import EmbeddingsProvider
from app.vectorstore.faiss_store import VectorStore, VectorHit
from app.db import models


class MockEmbeddingsProvider(EmbeddingsProvider):
    """Mock embeddings provider for testing."""
    
    def __init__(self, embedding_dim: int = 1536):
        self.embedding_dim = embedding_dim
        self.embed_query_calls = []
        self.embed_documents_calls = []
    
    async def embed_query(self, text: str):
        """Mock query embedding - tracks calls and returns consistent vector."""
        self.embed_query_calls.append(text)
        # Real behavior: Return vector of correct dimension
        return [0.1] * self.embedding_dim
    
    async def embed_documents(self, texts):
        """Mock document embeddings - tracks calls and returns consistent vectors."""
        self.embed_documents_calls.extend(texts)
        # Real behavior: Return one vector per text
        return [[0.1] * self.embedding_dim for _ in texts]


class MockLlmClient(LlmClient):
    """Mock LLM client for testing."""
    
    def __init__(self):
        self.generate_calls = []
        self.response_template = "This is a test response based on the provided context."
    
    async def generate(self, messages):
        """Mock LLM generation - tracks calls and returns contextual response."""
        self.generate_calls.append(messages)
        # Real behavior: Response should reflect context in messages
        context_present = any("context" in str(msg.get("content", "")).lower() for msg in messages)
        if context_present:
            return "Based on the provided context, the answer is X."
        return self.response_template


class MockVectorStore:
    """Mock vector store for testing."""
    
    def __init__(self):
        self.search_calls = []
        self.hits_by_query = {}
    
    def search(self, user_id: int, query_vector: list[float], k: int = 10):
        """Mock vector search - tracks calls and returns configurable hits."""
        self.search_calls.append({
            "user_id": user_id,
            "query_vector": query_vector,
            "k": k
        })
        
        # Real behavior: Return hits sorted by score (lower is better for L2)
        query_key = tuple(query_vector[:5])  # Use first 5 dims as key
        if query_key in self.hits_by_query:
            return self.hits_by_query[query_key]
        
        # Default: Return mock hits
        return [
            VectorHit(chunk_id=1, score=0.95),
            VectorHit(chunk_id=2, score=0.90),
            VectorHit(chunk_id=3, score=0.85),
        ]
    
    def set_hits_for_query(self, query_vector: list[float], hits: list[VectorHit]):
        """Helper to configure hits for a specific query."""
        query_key = tuple(query_vector[:5])
        self.hits_by_query[query_key] = hits


@pytest.fixture
def mock_embeddings():
    """Fixture for mock embeddings provider."""
    return MockEmbeddingsProvider(embedding_dim=1536)


@pytest.fixture
def mock_llm():
    """Fixture for mock LLM client."""
    return MockLlmClient()


@pytest.fixture
def mock_vector_store():
    """Fixture for mock vector store."""
    return MockVectorStore()


@pytest.fixture
def mock_user():
    """Fixture for mock user."""
    user = Mock(spec=models.User)
    user.id = 1
    user.email = "test@example.com"
    return user


@pytest.fixture
def mock_session():
    """Fixture for mock chat session."""
    session = Mock(spec=models.ChatSession)
    session.id = 1
    session.user_id = 1
    return session


@pytest.fixture
def mock_db():
    """Fixture for mock database session."""
    db = Mock(spec=Session)
    return db


@pytest.mark.asyncio
async def test_embeddings_provider_interface(mock_embeddings):
    """Test embeddings provider interface with real behavior."""
    # Real behavior: embed_query should return vector of correct dimension
    query = "What is the meaning of life?"
    query_vec = await mock_embeddings.embed_query(query)
    
    assert len(query_vec) == 1536, "Embedding should have correct dimension"
    assert all(isinstance(x, float) for x in query_vec), "All values should be floats"
    assert all(0 <= x <= 1 for x in query_vec), "Values should be in reasonable range"
    assert len(mock_embeddings.embed_query_calls) == 1, "embed_query should be called once"
    assert mock_embeddings.embed_query_calls[0] == query, "Should track query text"
    
    # Real behavior: embed_documents should handle multiple texts
    texts = ["Document 1", "Document 2", "Document 3"]
    embeddings = await mock_embeddings.embed_documents(texts)
    
    assert len(embeddings) == len(texts), "Should return one embedding per text"
    assert all(len(emb) == 1536 for emb in embeddings), "All embeddings should have correct dimension"


@pytest.mark.asyncio
async def test_llm_client_interface(mock_llm):
    """Test LLM client interface with real behavior."""
    # Real behavior: LLM should process messages and return text
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is 2+2?"}
    ]
    
    response = await mock_llm.generate(messages)
    
    assert isinstance(response, str), "Response should be string"
    assert len(response) > 0, "Response should not be empty"
    assert len(mock_llm.generate_calls) == 1, "generate should be called once"
    assert mock_llm.generate_calls[0] == messages, "Should track messages"


@pytest.mark.asyncio
async def test_vector_store_interface(mock_vector_store):
    """Test vector store interface with real behavior."""
    # Real behavior: search should return hits sorted by score
    query_vector = [0.1] * 1536
    hits = mock_vector_store.search(user_id=1, query_vector=query_vector, k=5)
    
    assert len(hits) > 0, "Should return hits"
    assert all(isinstance(hit, VectorHit) for hit in hits), "All hits should be VectorHit"
    assert all(hasattr(hit, 'chunk_id') for hit in hits), "Hits should have chunk_id"
    assert all(hasattr(hit, 'score') for hit in hits), "Hits should have score"
    
    # Real behavior: Hits should be sorted by score (lower is better for L2)
    scores = [hit.score for hit in hits]
    assert scores == sorted(scores), "Hits should be sorted by score (ascending)"
    
    # Verify search was called
    assert len(mock_vector_store.search_calls) == 1, "search should be called once"
    assert mock_vector_store.search_calls[0]["user_id"] == 1, "Should track user_id"
    assert mock_vector_store.search_calls[0]["k"] == 5, "Should track k parameter"


@pytest.mark.asyncio
async def test_rag_chain_initialization(mock_embeddings, mock_vector_store, mock_llm):
    """Test RAG chain initialization with real behavior."""
    # Real behavior: RagChain should initialize with all required components
    rag_chain = RagChain(
        embeddings_provider=mock_embeddings,
        vector_store=mock_vector_store,
        llm_client=mock_llm,
    )
    
    assert rag_chain._embeddings is mock_embeddings, "Should store embeddings provider"
    assert rag_chain._vector_store is mock_vector_store, "Should store vector store"
    assert rag_chain._llm is mock_llm, "Should store LLM client"


@pytest.mark.asyncio
async def test_rag_chain_no_hits_behavior(mock_embeddings, mock_vector_store, mock_llm, mock_db, mock_user, mock_session):
    """Test RAG chain behavior when no hits are found."""
    # Real behavior: Should return helpful message when no chunks found
    mock_vector_store.set_hits_for_query([0.1] * 1536, [])
    
    rag_chain = RagChain(
        embeddings_provider=mock_embeddings,
        vector_store=mock_vector_store,
        llm_client=mock_llm,
    )
    
    question = "What is the capital of France?"
    answer, citations = await rag_chain.answer_question(
        db=mock_db,
        user=mock_user,
        session=mock_session,
        question=question,
        top_k=10
    )
    
    # Real behavior: Should return informative message
    assert isinstance(answer, str), "Answer should be string"
    assert len(answer) > 0, "Answer should not be empty"
    assert "couldn't find" in answer.lower() or "no relevant" in answer.lower(), \
        "Should indicate no relevant information found"
    assert citations == [], "Citations should be empty when no hits"
    
    # Verify embeddings were called
    assert len(mock_embeddings.embed_query_calls) == 1, "Should call embed_query"
    assert mock_embeddings.embed_query_calls[0] == question, "Should embed the question"
    
    # Verify vector store was called
    assert len(mock_vector_store.search_calls) == 1, "Should call vector store search"


@pytest.mark.asyncio
async def test_rag_chain_with_hits_flow(mock_embeddings, mock_vector_store, mock_llm, mock_db, mock_user, mock_session):
    """Test RAG chain complete flow with hits."""
    # Setup: Create mock chunks in database
    mock_chunk1 = Mock(spec=models.DocumentChunk)
    mock_chunk1.id = 1
    mock_chunk1.text = "Paris is the capital of France."
    mock_chunk1.document_id = 1
    mock_chunk1.document = Mock(spec=models.Document)
    mock_chunk1.document.id = 1
    mock_chunk1.document.title = "Geography Facts"
    mock_chunk1.document.user_id = 1
    
    mock_chunk2 = Mock(spec=models.DocumentChunk)
    mock_chunk2.id = 2
    mock_chunk2.text = "France is a country in Europe."
    mock_chunk2.document_id = 1
    mock_chunk2.document = mock_chunk1.document
    
    # Mock database query
    mock_db.query.return_value.filter.return_value.join.return_value.filter.return_value.all.return_value = [
        mock_chunk1, mock_chunk2
    ]
    
    # Setup vector store hits
    query_vector = [0.1] * 1536
    hits = [
        VectorHit(chunk_id=1, score=0.85),
        VectorHit(chunk_id=2, score=0.90),
    ]
    mock_vector_store.set_hits_for_query(query_vector, hits)
    
    rag_chain = RagChain(
        embeddings_provider=mock_embeddings,
        vector_store=mock_vector_store,
        llm_client=mock_llm,
    )
    
    question = "What is the capital of France?"
    answer, citations = await rag_chain.answer_question(
        db=mock_db,
        user=mock_user,
        session=mock_session,
        question=question,
        top_k=10
    )
    
    # Real behavior: Should return answer and citations
    assert isinstance(answer, str), "Answer should be string"
    assert len(answer) > 0, "Answer should not be empty"
    assert isinstance(citations, list), "Citations should be list"
    assert len(citations) > 0, "Should have citations when chunks found"
    
    # Verify citations structure
    for citation in citations:
        assert "document_id" in citation, "Citation should have document_id"
        assert "document_title" in citation, "Citation should have document_title"
        assert "chunk_id" in citation, "Citation should have chunk_id"
        assert "score" in citation, "Citation should have score"
    
    # Verify all components were called
    assert len(mock_embeddings.embed_query_calls) == 1, "Should call embed_query"
    assert len(mock_vector_store.search_calls) == 1, "Should call vector store search"
    assert len(mock_llm.generate_calls) == 1, "Should call LLM generate"
    
    # Verify LLM received context
    llm_messages = mock_llm.generate_calls[0]
    assert len(llm_messages) > 0, "LLM should receive messages"
    # Check that context is included
    context_found = any("context" in str(msg.get("content", "")).lower() or 
                       "paris" in str(msg.get("content", "")).lower() 
                       for msg in llm_messages)
    assert context_found, "LLM messages should include context from chunks"

