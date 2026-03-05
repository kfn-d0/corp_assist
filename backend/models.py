"""
Pydantic models — request/response schemas for the FastAPI endpoints.
Defines all data structures used across the RAG system.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DocumentMetadata(BaseModel):
    """Metadata associated with an uploaded document."""
    document_id: str = Field(description="Unique identifier for the document")
    document_name: str = Field(description="Original filename")
    department: str = Field(default="public", description="Department/access scope")
    upload_timestamp: str = Field(description="ISO timestamp of upload")
    total_pages: int = Field(default=0, description="Total pages in document")
    total_chunks: int = Field(default=0, description="Total chunks generated")
    file_type: str = Field(description="File extension (pdf, docx, txt)")
    version: int = Field(default=1, description="Document version number")


class ChunkMetadata(BaseModel):
    """Metadata for an individual text chunk."""
    document_name: str
    document_id: str
    page: int = Field(default=0, description="Page number (0 if not applicable)")
    section: str = Field(default="", description="Section header if detected")
    chunk_index: int = Field(description="Position of chunk in document")
    department: str = Field(default="public")
    timestamp: str = Field(description="Ingestion timestamp")


class QueryRequest(BaseModel):
    """Request body for the /api/query endpoint."""
    question: str = Field(description="User's natural language question")
    user_role: str = Field(default="public", description="User's role for RBAC filtering")
    department_filter: Optional[str] = Field(default=None, description="Optional department filter")
    top_k: Optional[int] = Field(default=None, description="Override default top-k")


class UploadRequest(BaseModel):
    """Metadata sent alongside a file upload."""
    department: str = Field(default="public", description="Department scope for the document")


class SourceCitation(BaseModel):
    """A single source citation in an answer."""
    document: str = Field(description="Source document filename")
    page: int = Field(default=0, description="Page number")
    excerpt: str = Field(description="Relevant text excerpt from the chunk")
    relevance_score: float = Field(default=0.0, description="Retrieval relevance score")
    trust_score: float = Field(default=0.7, description="Document trust/authority score")


class QueryResponse(BaseModel):
    """Response body for the /api/query endpoint."""
    answer: str = Field(description="Generated answer text")
    sources: list[SourceCitation] = Field(default_factory=list, description="Citation list")
    query: str = Field(description="Original question")
    model_used: str = Field(description="LLM model name")
    latency_ms: float = Field(description="Total response latency in milliseconds")
    tokens_used: int = Field(default=0, description="Approximate token count")
    timestamp: str = Field(description="Response timestamp")
    knowledge_gap: bool = Field(default=False, description="True if no relevant documents found")
    contradiction_warning: str = Field(default="", description="Warning if contradictions detected")
    confidence_score: float = Field(default=1.0, description="Answer confidence (0.0-1.0) from verification grader")
    verification_status: str = Field(default="unverified", description="SUPPORTED, PARTIAL, UNSUPPORTED, or unverified")


class IngestResponse(BaseModel):
    """Response body after document ingestion."""
    document_id: str
    document_name: str
    chunk_count: int
    status: str = Field(default="success")
    message: str = Field(default="Document ingested successfully")


class DocumentInfo(BaseModel):
    """Summary info for a single indexed document."""
    document_id: str
    document_name: str
    department: str
    file_type: str
    total_pages: int
    total_chunks: int
    upload_timestamp: str
    version: int


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    ollama_connected: bool
    qdrant_connected: bool
    documents_indexed: int
    llm_model: str
    embedding_model: str


class QueryHistoryItem(BaseModel):
    """A single item from query history."""
    question: str
    answer: str
    user_role: str
    sources_count: int
    latency_ms: float
    model_used: str
    timestamp: str


class LoginRequest(BaseModel):
    """Credentials for login."""
    username: str
    password: str


class UserCreateRequest(BaseModel):
    """Schema for creating a new user."""
    username: str
    password: str
    role: str
    department: str


class UserResponse(BaseModel):
    """Public user info (no password)."""
    username: str
    role: str
    department: str
