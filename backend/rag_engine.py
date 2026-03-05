"""
RAG Engine — orchestrates retrieval + LLM generation with guardrails.
Generates answers grounded exclusively in the retrieved context,
with verifiable source citations. Includes semantic cache,
answer verification, and auto-repair.
"""

import logging
import time
from datetime import datetime, timezone

import ollama

from backend.config import settings
from backend.retrieval import retrieve
from backend.audit import log_query
from backend.models import QueryResponse, SourceCitation
from backend.query_processing import process_query_for_retrieval
from backend.semantic_cache import get_cached_response, cache_response
from backend.contradiction_detector import detect_contradictions
from backend.answer_verifier import grade_answer

logger = logging.getLogger(__name__)


KNOWLEDGE_GAP_PHRASES = [
    "não consegui encontrar",
    "não encontrei informações",
    "não há informações suficientes",
    "não possuo informações",
    "no relevant documents",
    "não foi possível encontrar",
    "fora do escopo",
]


SYSTEM_PROMPT = """Você é um Assistente de Conhecimento Corporativo. Sua função é responder a perguntas baseando-se EXCLUSIVAMENTE nos documentos de contexto fornecidos.

REGRAS ESTRITAS:
1. Use APENAS as informações presentes no contexto fornecido abaixo.
2. Se a resposta NÃO puder ser encontrada no contexto, ou se o contexto for insuficiente ou vazio, responda EXATAMENTE com: "Não consegui encontrar informações suficientes nos documentos indexados."
3. NÃO invente, não infira e não extrapole informações além do que está explicitamente declarado no contexto.
4. NÃO use nenhum conhecimento externo ou dados de treinamento para responder.
5. NÃO inclua o nome do arquivo, página ou seção no corpo da resposta. Essas informações serão exibidas automaticamente em uma seção separada de "Fontes".
6. Seja preciso e conciso em suas respostas.
7. Se a informação vier de vários documentos, sintetize a resposta de forma direta.
8. Se documentos apresentarem informações CONTRADITÓRIAS, informe ambas as versões de forma neutra.
9. RESPONDA SEMPRE EM PORTUGUÊS DO BRASIL.
10. NÃO USE EMOJIS EM SUAS RESPOSTAS.

FORMATE SUA RESPOSTA COMO:
- Forneça uma resposta clara, direta e bem estruturada.
- Vá direto ao ponto, focando na informação solicitada.
"""


def build_context_prompt(chunks: list[dict]) -> str:
    """Build the context section of the prompt from retrieved chunks."""
    if not chunks:
        return "No relevant documents were found."

    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        doc_name = meta.get("document_name", "Unknown")
        page = meta.get("page", 0)
        section = meta.get("section", "")

        header = f"[Source {i}: {doc_name}, Page {page}"
        if section:
            header += f", Section: {section}"
        header += "]"

        context_parts.append(f"{header}\n{chunk['text']}")

    return "\n\n---\n\n".join(context_parts)


def build_full_prompt(context: str, question: str, graph_context: str = "") -> str:
    """Build the complete user prompt with documents, question, and KG context."""
    prompt = f"CONTEXT (use ONLY this information to answer):\n\n{context}\n"
    if graph_context:
        prompt += f"\n---\n\n{graph_context}\n"
    prompt += f"\n---\n\nQUESTION: {question}\n\nANSWER:"
    return prompt


def _generate_llm_answer(user_prompt: str) -> tuple[str, int]:
    """Chama o LLM e retorna (resposta, tokens_usados)."""
    try:
        response = ollama.chat(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            options={
                "temperature": 0.1,
                "top_p": 0.9,
                "num_predict": 1024,
            },
        )
        answer = response["message"]["content"]
        tokens = response.get("eval_count", 0) + response.get("prompt_eval_count", 0)
        return answer, tokens
    except Exception as e:
        return f"Erro ao gerar resposta: {str(e)}", 0


def _build_citations(chunks: list[dict]) -> list[SourceCitation]:
    """Constrói lista de citações a partir dos chunks."""
    sources = []
    seen_docs = set()
    for chunk in chunks:
        meta = chunk.get("metadata", {})
        doc_name = meta.get("document_name", "Unknown")
        page = meta.get("page", 0)
        doc_key = f"{doc_name}_{page}"

        if doc_key not in seen_docs:
            seen_docs.add(doc_key)
            sources.append(SourceCitation(
                document=doc_name,
                page=page,
                excerpt=chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"],
                relevance_score=round(chunk.get("score", 0.0), 4),
                trust_score=meta.get("trust_score", 0.7),
            ))
    return sources


def generate_answer(
    question: str,
    user_role: str = "public",
    top_k: int = None,
) -> QueryResponse:
    """
    Full RAG pipeline with verification & auto-repair:
    0. Semantic Cache
    1. Query Understanding
    2. Retrieve + Contradiction Check
    3. Generate Answer
    4. Verify Answer (grader)
    5. Auto-Repair if PARTIAL (retry once with expanded retrieval)
    6. Return with confidence score
    """
    start_time = time.time()

    if top_k is None:
        top_k = settings.top_k


    cached = get_cached_response(question)
    if cached:
        latency_ms = (time.time() - start_time) * 1000
        logger.info(f"Cache HIT para: '{question[:50]}...' ({latency_ms:.0f}ms)")
        sources = []
        for s in cached.get("sources", []):
            sources.append(SourceCitation(
                document=s.get("document", ""),
                page=s.get("page", 0),
                excerpt=s.get("excerpt", ""),
                relevance_score=s.get("relevance_score", 0),
            ))
        return QueryResponse(
            answer=cached["answer"],
            sources=sources,
            query=question,
            model_used=cached.get("model_used", settings.llm_model) + " (cache)",
            latency_ms=round(latency_ms, 2),
            tokens_used=0,
            timestamp=datetime.now(timezone.utc).isoformat(),
            confidence_score=1.0,
            verification_status="cached",
        )


    processed_query = process_query_for_retrieval(question, use_hyde=True)


    retrieved_chunks, graph_context = retrieve(
        query=processed_query,
        user_role=user_role,
        top_k=top_k,
    )


    contradiction_warning = ""
    if len(retrieved_chunks) >= 2:
        try:
            contradiction_warning = detect_contradictions(retrieved_chunks)
        except Exception as e:
            logger.warning(f"Erro na detecção de contradição: {e}")


    if not retrieved_chunks:
        latency_ms = (time.time() - start_time) * 1000
        return QueryResponse(
            answer="Não consegui encontrar informações suficientes nos documentos indexados.",
            sources=[],
            query=question,
            model_used=settings.llm_model,
            latency_ms=round(latency_ms, 2),
            tokens_used=0,
            timestamp=datetime.now(timezone.utc).isoformat(),
            knowledge_gap=True,
            confidence_score=1.0,
            verification_status="SUPPORTED",
        )


    context_text = build_context_prompt(retrieved_chunks)
    user_prompt = build_full_prompt(context_text, question, graph_context)
    answer, tokens_used = _generate_llm_answer(user_prompt)


    knowledge_gap = False
    answer_lower = answer.lower()
    for phrase in KNOWLEDGE_GAP_PHRASES:
        if phrase in answer_lower:
            knowledge_gap = True
            break


    verification = {"verdict": "unverified", "confidence": 0.7, "reason": ""}
    if not knowledge_gap:
        try:
            verification = grade_answer(answer, retrieved_chunks)
            logger.info(f"Verificação: {verification['verdict']} (confiança: {verification['confidence']:.2f})")
        except Exception as e:
            logger.warning(f"Erro no grader: {e}")


    if verification["verdict"] == "PARTIAL" and verification["confidence"] < 0.8:
        logger.info("Auto-reparo: expandindo retrieval...")
        try:

            expanded_chunks, expanded_graph = retrieve(
                query=processed_query,
                user_role=user_role,
                top_k=top_k * 2,
            )

            if len(expanded_chunks) > len(retrieved_chunks):
                context_text_2 = build_context_prompt(expanded_chunks)
                user_prompt_2 = build_full_prompt(context_text_2, question, expanded_graph or graph_context)
                answer_2, tokens_2 = _generate_llm_answer(user_prompt_2)
                tokens_used += tokens_2


                verification_2 = grade_answer(answer_2, expanded_chunks)
                logger.info(f"Re-verificação: {verification_2['verdict']} (confiança: {verification_2['confidence']:.2f})")

                if verification_2["confidence"] > verification["confidence"]:
                    answer = answer_2
                    retrieved_chunks = expanded_chunks
                    graph_context = expanded_graph or graph_context
                    verification = verification_2
                    logger.info("Auto-reparo: resposta melhorada aceita.")
                else:
                    logger.info("Auto-reparo: resposta original mantida.")

        except Exception as e:
            logger.warning(f"Erro no auto-reparo: {e}")

    elif verification["verdict"] == "UNSUPPORTED":
        knowledge_gap = True
        answer = "Não consegui encontrar informações suficientes nos documentos indexados para responder com confiança."
        verification["confidence"] = 0.0


    if contradiction_warning:
        answer = f"[Aviso: {contradiction_warning}]\n\n{answer}"

    if verification["verdict"] == "PARTIAL" and not knowledge_gap:
        answer += f"\n\n---\n*Nivel de confiança: {verification['confidence']:.0%} — Algumas informações podem necessitar de verificação adicional.*"


    sources = _build_citations(retrieved_chunks)

    latency_ms = (time.time() - start_time) * 1000


    query_response = QueryResponse(
        answer=answer,
        sources=sources,
        query=question,
        model_used=settings.llm_model,
        latency_ms=round(latency_ms, 2),
        tokens_used=tokens_used,
        timestamp=datetime.now(timezone.utc).isoformat(),
        knowledge_gap=knowledge_gap,
        contradiction_warning=contradiction_warning,
        confidence_score=round(verification.get("confidence", 0.7), 2),
        verification_status=verification.get("verdict", "unverified"),
    )


    if verification.get("confidence", 0) >= 0.7 and not knowledge_gap:
        try:
            cache_response(
                query=question,
                answer=answer,
                sources=[s.model_dump() for s in sources],
                model_used=settings.llm_model,
                tokens_used=tokens_used,
            )
        except Exception:
            pass


    try:
        log_query(
            question=question,
            answer=answer,
            user_role=user_role,
            sources=[s.model_dump() for s in sources],
            latency_ms=latency_ms,
            tokens_used=tokens_used,
            model_used=settings.llm_model,
        )
    except Exception:
        pass

    return query_response


def check_ollama_connection() -> bool:
    """Verify that Ollama is running and responsive."""
    try:
        ollama.list()
        return True
    except Exception:
        return False


