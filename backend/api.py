"""
Aplicação FastAPI — API REST para o Enterprise Knowledge RAG System.
Expõe endpoints para upload de documentos, consultas, gestão de documentos,
autenticação e gerenciamento de usuários.
"""

import os

import traceback
from datetime import datetime, timezone
from typing import List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.models import (
    QueryRequest, QueryResponse, IngestResponse,
    DocumentInfo, HealthResponse, QueryHistoryItem,
    LoginRequest, UserCreateRequest, UserResponse
)
from backend.auth import (
    authenticate_user, list_users, add_user, delete_user,
    can_upload, can_delete, get_accessible_departments,
    get_role_info, ROLES, DEPARTMENTS
)
from backend.ingest_pipeline import (
    ingest_document, get_indexed_documents, delete_document, get_collection
)
from backend.rag_engine import generate_answer, check_ollama_connection
from backend.audit import log_ingestion, log_error, get_query_history


app = FastAPI(
    title="Enterprise Knowledge RAG System",
    description=(
        "Plataforma corporativa de busca semântica e Q&A usando RAG. "
        "Faça upload de documentos (PDF, DOCX, TXT), tire dúvidas e "
        "receba respostas com citações verificáveis."
    ),
    version="1.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/login", response_model=UserResponse, tags=["Auth"])
async def login(credentials: LoginRequest):
    """Autentica o usuário e retorna o perfil."""
    user = authenticate_user(credentials.username, credentials.password)
    if not user:
        raise HTTPException(status_code=401, detail="Usuário ou senha inválidos")
    return user


@app.get("/api/users", response_model=List[UserResponse], tags=["Admin"])
async def get_all_users(admin_role: str = Query("public")):
    """Lista todos os usuários (Acesso: Admin apenas)."""
    if admin_role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado: Apenas administradores podem ver usuários.")
    return list_users()


@app.post("/api/users", response_model=UserResponse, tags=["Admin"])
async def create_user(user_data: UserCreateRequest, admin_role: str = Query("public")):
    """Cria um novo usuário (Acesso: Admin apenas)."""
    if admin_role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado: Apenas administradores podem criar usuários.")
    
    success = add_user(
        username=user_data.username,
        password=user_data.password,
        role=user_data.role,
        department=user_data.department
    )
    if not success:
        raise HTTPException(status_code=400, detail="Usuário já existe ou perfil inválido.")
    
    return UserResponse(
        username=user_data.username,
        role=user_data.role,
        department=user_data.department
    )


@app.delete("/api/users/{username}", tags=["Admin"])
async def remove_user(username: str, admin_role: str = Query("public")):
    """Remove um usuário do sistema (Acesso: Admin apenas)."""
    if admin_role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado: Apenas administradores podem remover usuários.")
    
    success = delete_user(username)
    if not success:
        raise HTTPException(status_code=400, detail="Não foi possível excluir o usuário (usuário inexistente ou protegido).")
    
    return {"status": "success", "message": f"Usuário '{username}' removido com sucesso."}


@app.post("/api/upload", response_model=IngestResponse, tags=["Documents"])
async def upload_document(
    file: UploadFile = File(..., description="Arquivo de documento (PDF, DOCX ou TXT)"),
    department: str = Form(default="public"),
    user_role: str = Form(default="public"),
):
    """Upload e indexação de um documento."""
    if not can_upload(user_role):
        raise HTTPException(
            status_code=403,
            detail=f"O perfil '{user_role}' não tem permissão para fazer upload."
        )

    filename = file.filename or "desconhecido"
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in ("pdf", "docx", "txt"):
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de arquivo não suportado: .{extension}. Esperado: PDF, DOCX, TXT."
        )

    upload_dir = os.path.join("documents", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, filename)

    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        result = ingest_document(
            file_path=file_path,
            document_name=filename,
            department=department,
            file_type=extension,
        )

        log_ingestion(
            document_name=filename,
            department=department,
            chunk_count=result["chunk_count"],
            file_type=extension,
            status=result["status"],
            message=result["message"],
        )

        if result["status"] == "error":
            raise HTTPException(status_code=422, detail=result["message"])

        return IngestResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Falha na ingestão: {str(e)}"
        log_error("upload", error_msg, {"filename": filename, "traceback": traceback.format_exc()})
        raise HTTPException(status_code=500, detail=error_msg)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@app.get("/api/documents", response_model=List[DocumentInfo], tags=["Documents"])
async def list_documents(user_role: str = Query(default="public")):
    """Lista documentos disponíveis para o perfil do usuário."""
    accessible = get_accessible_departments(user_role)
    all_docs = get_indexed_documents()
    filtered = [
        DocumentInfo(**doc)
        for doc in all_docs
        if doc.get("department", "public") in accessible
    ]
    return filtered


@app.delete("/api/documents/{document_name}", tags=["Documents"])
async def remove_document(document_name: str, user_role: str = Query(default="public")):
    """Remove um documento indexado (Acesso: Admin apenas)."""
    if not can_delete(user_role):
        raise HTTPException(status_code=403, detail="Acesso negado para exclusão.")

    try:
        success = delete_document(document_name)
        if success:
            return {"status": "success", "message": f"Documento '{document_name}' removido."}
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha na exclusão: {str(e)}")


@app.post("/api/query", response_model=QueryResponse, tags=["Query"])
async def query_documents(request: QueryRequest):
    """Pergunta ao assistente baseando-se nos documentos."""
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="A pergunta não pode estar vazia.")

    try:
        response = generate_answer(
            question=request.question,
            user_role=request.user_role,
            top_k=request.top_k or settings.top_k,
        )
        return response
    except Exception as e:
        error_msg = f"Falha na consulta: {str(e)}"
        log_error("query", error_msg, {"question": request.question, "traceback": traceback.format_exc()})
        raise HTTPException(status_code=500, detail=error_msg)


@app.get("/api/history", response_model=List[QueryHistoryItem], tags=["Audit"])
async def get_history(limit: int = Query(default=50)):
    """Histórico recente de consultas."""
    history = get_query_history(limit=limit)
    return [QueryHistoryItem(**entry) for entry in history]


@app.get("/api/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Status de saúde do sistema e conexões."""
    ollama_ok = check_ollama_connection()
    qdrant_ok = False
    doc_count = 0
    try:
        from backend.ingest_pipeline import get_qdrant_client
        client = get_qdrant_client()
        # A chamada get_qdrant_client já tenta criar a coleção se não existir
        collection = client.get_collection(settings.qdrant_collection_name)
        qdrant_ok = True
        doc_count = collection.points_count
    except Exception as e:
        logger.warning(f"Qdrant health check error: {e}")
        pass

    return HealthResponse(
        status="healthy" if (ollama_ok and qdrant_ok) else "degraded",
        ollama_connected=ollama_ok,
        qdrant_connected=qdrant_ok,
        documents_indexed=doc_count,
        llm_model=settings.llm_model,
        embedding_model=settings.embedding_model,
    )


@app.get("/api/roles", tags=["System"])
async def list_roles():
    """Lista perfis e permissões."""
    return {role: get_role_info(role) for role in ROLES}


@app.get("/api/departments", tags=["System"])
async def list_departments():
    """Lista departamentos válidos."""
    return {"departments": DEPARTMENTS}


@app.get("/", tags=["System"])
async def root():
    """Endpoint raiz com info básica."""
    return {
        "name": "Enterprise Knowledge RAG System",
        "version": "1.1.0",
        "docs": "/docs",
        "health": "/api/health",
    }
