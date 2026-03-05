"""
Configuration module — loads settings from .env file using Pydantic BaseSettings.
All configurable parameters for the RAG system are centralized here.
"""

import os
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""


    llm_model: str = Field(default="llama3", description="LLM model name for response generation")
    embedding_model: str = Field(default="nomic-embed-text", description="Embedding model for vector generation")


    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection_name: str = "enterprise_docs"


    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"


    chunk_size: int = 1000
    chunk_overlap: int = 150


    top_k: int = 5
    hybrid_alpha: float = 0.5
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"


    cache_collection_name: str = "query_cache"
    cache_similarity_threshold: float = 0.92
    cache_ttl_hours: int = 24


    trust_type_scores: dict = {
        "pdf": 0.9,
        "docx": 0.8,
        "txt": 0.5,
    }
    trust_name_patterns: dict = {
        "policy": 1.0,
        "politica": 1.0,
        "manual": 0.95,
        "regulamento": 0.95,
        "procedimento": 0.9,
        "guia": 0.85,
        "nota": 0.5,
        "rascunho": 0.3,
        "draft": 0.3,
    }


    documents_dir: str = "documents"
    metadata_registry: str = os.path.join("vectorstore", "document_registry.json")
    vectorstore_dir: str = "vectorstore"


    log_dir: str = Field(default="./logs", description="Directory for audit logs")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"
    }


settings = Settings()


os.makedirs(settings.vectorstore_dir, exist_ok=True)
os.makedirs(settings.log_dir, exist_ok=True)
os.makedirs(settings.documents_dir, exist_ok=True)
