from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Phase 2 spec: Pydantic BaseSettings with Config inner class.
    Using pydantic-settings for Pydantic v2 compatibility.
    """
    
    app_name: str = "Prachi RAG Workspace"
    environment: str = "dev"  # "dev" | "staging" | "prod"
    
    # Database
    database_url: str
    # Example: postgresql+psycopg2://user:password@db:5432/rag_db
    
    # Security
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 1 day
    
    # LLM / embeddings
    openai_api_key: Optional[str] = None
    embeddings_model: str = "text-embedding-3-small"
    llm_model: str = "gpt-4o-mini"
    
    # Vector store
    vectorstore_base_dir: str = "data/vectorstores"
    
    # Additional settings (beyond Phase 2 spec)
    refresh_token_expire_days: int = 30
    embeddings_provider: str = "openai"  # openai, huggingface
    huggingface_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    huggingface_cache_dir: Optional[str] = None
    groq_api_key: Optional[str] = None
    groq_model: str = "llama-3.3-70b-versatile"  # Current free model: llama-3.3-70b-versatile, llama-3.1-8b-instant, mixtral-8x7b-32768
    local_llm_base_url: Optional[str] = None
    local_llm_model: Optional[str] = None
    llm_provider: str = "openai"  # openai, groq, local
    storage_base_dir: str = "storage"
    storage_provider: str = "filesystem"  # filesystem, s3
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    s3_bucket_name: Optional[str] = None
    vectorstore_provider: str = "faiss"  # faiss, pinecone, chroma
    pinecone_api_key: Optional[str] = None
    pinecone_environment: Optional[str] = None
    pinecone_index_name: Optional[str] = None
    chroma_persist_directory: str = "data/chroma"
    cors_origins: str = "*"
    max_file_size_mb: int = 50
    allowed_file_extensions: str = ".pdf,.txt,.md,.markdown,.jpg,.jpeg,.png,.gif,.webp,.bmp,.heic,.heif,.tiff,.tif,.svg,.ico"
    # Image analysis
    # NOTE: BLIP captioning model can hang on CPU. Set to True only if you have OPENAI_API_KEY or are willing to risk hangs.
    # For best results, use OPENAI_API_KEY with OpenAI Vision API instead.
    enable_caption_model: bool = False  # Default: false - BLIP hangs on CPU. Set to true only if you have OPENAI_API_KEY or accept risk of hangs
    local_caption_model_name: str = "Salesforce/blip-image-captioning-base"  # HuggingFace model for local captioning
    
    class Config:
        """Pydantic v1-style Config (Phase 2 spec)."""
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

