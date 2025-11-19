"""Factory functions for creating providers based on configuration."""
from typing import Optional
from app.config import get_settings
from app.embeddings.provider import EmbeddingsProvider
from app.embeddings.huggingface import HuggingFaceEmbeddingsProvider
from app.embeddings.provider import OpenAIEmbeddingsProvider
from app.rag.chain import LlmClient, OpenAILlmClient
from app.rag.groq_client import GroqLlmClient, LocalLlmClient
from app.vectorstore.faiss_store import VectorStore
from app.vectorstore.pinecone_store import PineconeVectorStore
from app.vectorstore.chroma_store import ChromaVectorStore

settings = get_settings()


def create_embeddings_provider() -> Optional[EmbeddingsProvider]:
    """Create embeddings provider based on configuration."""
    if settings.embeddings_provider == "huggingface":
        return HuggingFaceEmbeddingsProvider(
            model_name=settings.huggingface_model,
            cache_dir=settings.huggingface_cache_dir
        )
    elif settings.embeddings_provider == "openai":
        if not settings.openai_api_key:
            return None
        return OpenAIEmbeddingsProvider(
            api_key=settings.openai_api_key,
            model=settings.embeddings_model
        )
    else:
        # Default to OpenAI if available
        if settings.openai_api_key:
            return OpenAIEmbeddingsProvider(
                api_key=settings.openai_api_key,
                model=settings.embeddings_model
            )
        return None


def create_llm_client() -> Optional[LlmClient]:
    """Create LLM client based on configuration."""
    if settings.llm_provider == "groq":
        if not settings.groq_api_key:
            raise ValueError("Groq API key not configured")
        return GroqLlmClient(
            api_key=settings.groq_api_key,
            model=settings.groq_model
        )
    elif settings.llm_provider == "local":
        if not settings.local_llm_base_url:
            raise ValueError("Local LLM base URL not configured")
        return LocalLlmClient(
            base_url=settings.local_llm_base_url,
            model=settings.local_llm_model
        )
    elif settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not configured")
        return OpenAILlmClient(
            api_key=settings.openai_api_key,
            model=settings.llm_model
        )
    else:
        # Default to OpenAI
        if settings.openai_api_key:
            return OpenAILlmClient(
                api_key=settings.openai_api_key,
                model=settings.llm_model
            )
        raise ValueError("No LLM provider configured")


def create_vector_store(user_id: int):
    """Create vector store based on configuration."""
    if settings.vectorstore_provider == "pinecone":
        return PineconeVectorStore(user_id=user_id)
    elif settings.vectorstore_provider == "chroma":
        return ChromaVectorStore(user_id=user_id)
    else:
        # Default to FAISS
        return VectorStore(user_id=user_id)

