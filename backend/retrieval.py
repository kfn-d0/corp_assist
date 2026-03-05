"""
Módulo de Recuperação (Retrieval) busca híbrida combinando vetores (Qdrant) e BM25
Inclui reranking via Crossencoder e filtragem baseada em perfis (RBAC)
"""

import logging
import numpy as np
from rank_bm25 import BM25Okapi
from qdrant_client.http import models

from backend.config import settings
from backend.ingest_pipeline import get_qdrant_client, generate_embeddings_batch
from backend.auth import get_accessible_departments
from backend.graph_engine import query_graph_context

logger = logging.getLogger(__name__)


def vector_search(query: str, top_k: int = None, department_filter: list[str] = None) -> list[dict]:
    """
    Realiza busca por similaridade vetorial no Qdrant com filtragem por departamento
    """
    if top_k is None:
        top_k = settings.top_k

    client = get_qdrant_client()


    query_vector = generate_embeddings_batch([query])[0]


    qdrant_filter = None
    if department_filter:
        qdrant_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="department",
                    match=models.MatchAny(any=department_filter)
                )
            ]
        )


    results = client.search(
        collection_name=settings.qdrant_collection_name,
        query_vector=query_vector,
        query_filter=qdrant_filter,
        limit=top_k * 2,
        with_payload=True,
        with_vectors=False
    )


    formatted = []
    for res in results:
        formatted.append({
            "id": res.id,
            "text": res.payload.get("text", ""),
            "metadata": res.payload,
            "score": res.score,
            "source": "vector",
        })

    return formatted


def bm25_search(query: str, top_k: int = None, department_filter: list[str] = None) -> list[dict]:
    """
    Realiza busca lexical BM25
    Carrega fragmentos do Qdrant (filtrados por departamento) para construir o indice local
    """
    if top_k is None:
        top_k = settings.top_k

    client = get_qdrant_client()


    qdrant_filter = None
    if department_filter:
        qdrant_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="department",
                    match=models.MatchAny(any=department_filter)
                )
            ]
        )


    points, _ = client.scroll(
        collection_name=settings.qdrant_collection_name,
        scroll_filter=qdrant_filter,
        limit=1000,
        with_payload=True
    )

    if not points:
        return []

    corpus = [p.payload.get("text", "") for p in points]
    tokenized_corpus = [doc.lower().split() for doc in corpus]
    tokenized_query = query.lower().split()

    if not tokenized_corpus:
        return []

    bm25 = BM25Okapi(tokenized_corpus)
    scores = bm25.get_scores(tokenized_query)

    top_indices = np.argsort(scores)[::-1][:top_k * 2]

    formatted = []
    for idx in top_indices:
        if scores[idx] > 0:
            p = points[idx]
            formatted.append({
                "id": p.id,
                "text": p.payload.get("text", ""),
                "metadata": p.payload,
                "score": float(scores[idx]),
                "source": "bm25",
            })

    return formatted


def hybrid_search(query: str, top_k: int = None, user_role: str = "public", alpha: float = None) -> list[dict]:
    """
    Combina resultados de vetor e BM25 usando Reciprocal Rank Fusion (RRF)
    """
    if top_k is None:
        top_k = settings.top_k
    if alpha is None:
        alpha = settings.hybrid_alpha

    accessible_depts = get_accessible_departments(user_role)

    vector_results = vector_search(query, top_k=top_k, department_filter=accessible_depts)
    bm25_results = bm25_search(query, top_k=top_k, department_filter=accessible_depts)

    if not vector_results and not bm25_results:
        return []
    if not vector_results:
        return bm25_results[:top_k]
    if not bm25_results:
        return vector_results[:top_k]


    rrf_k = 60
    rrf_scores = {}

    for rank, res in enumerate(vector_results):
        doc_id = res["id"]
        rrf_scores[doc_id] = {"result": res, "score": alpha * (1.0 / (rrf_k + rank + 1))}

    for rank, res in enumerate(bm25_results):
        doc_id = res["id"]
        if doc_id not in rrf_scores:
            rrf_scores[doc_id] = {"result": res, "score": 0.0}
        rrf_scores[doc_id]["score"] += (1 - alpha) * (1.0 / (rrf_k + rank + 1))

    sorted_results = sorted(rrf_scores.values(), key=lambda x: x["score"], reverse=True)

    final_results = []
    for item in sorted_results[:top_k]:
        res = item["result"]
        res["score"] = item["score"]
        res["source"] = "hybrid"
        final_results.append(res)

    return final_results


_cross_encoder = None

def _get_cross_encoder():
    """Carrega o Crossencoder uma unica vez (singleton)"""
    global _cross_encoder
    if _cross_encoder is None:
        try:
            from sentence_transformers import CrossEncoder
            logger.info(f"Carregando modelo de reranking: {settings.reranker_model}")
            _cross_encoder = CrossEncoder(settings.reranker_model)
            logger.info("Cross-Encoder carregado com sucesso.")
        except Exception as e:
            logger.warning(f"Falha ao carregar Cross-Encoder: {e}. Usando fallback heurístico.")
            _cross_encoder = "fallback"
    return _cross_encoder


def rerank_results(query: str, results: list[dict], top_k: int = None) -> list[dict]:
    """Reranking usando Crossecoder + Trust Score"""
    if top_k is None:
        top_k = settings.top_k
    if not results:
        return []

    encoder = _get_cross_encoder()

    if encoder == "fallback":
        return _heuristic_rerank(query, results, top_k)

    try:

        pairs = [(query, res["text"]) for res in results]
        scores = encoder.predict(pairs)

        for i, res in enumerate(results):
            ce_score = float(scores[i])
            trust = res.get("metadata", {}).get("trust_score", 0.7)
            semantic = res.get("score", 0.5)

            res["rerank_score"] = (0.5 * ce_score) + (0.2 * trust) + (0.3 * semantic)

        results.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
        return results[:top_k]

    except Exception as e:
        logger.warning(f"Erro no Cross-Encoder reranking: {e}. Usando fallback.")
        return _heuristic_rerank(query, results, top_k)


def _heuristic_rerank(query: str, results: list[dict], top_k: int) -> list[dict]:
    """Fallback: reranking heurístico por sobreposição de palavras + trust"""
    q_terms = set(query.lower().split())

    for res in results:
        text = res["text"].lower()
        t_terms = set(text.split())
        overlap = len(q_terms & t_terms) / max(len(q_terms), 1)
        orig_score = res.get("score", 0.5)
        trust = res.get("metadata", {}).get("trust_score", 0.7)

        res["rerank_score"] = (0.4 * orig_score) + (0.3 * overlap) + (0.3 * trust)

    results.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
    return results[:top_k]


def retrieve(
    query: str,
    user_role: str = "public",
    top_k: int = None,
    use_hybrid: bool = True,
    use_rerank: bool = True,
    use_graph: bool = True,
) -> tuple[list[dict], str]:
    """
    Orquestra a busca: Vetor + BM25 + Grafo
    Retorna (fragmentos_relevantes, contexto_do_grafo)
    """
    if top_k is None:
        top_k = settings.top_k


    graph_context = ""
    if use_graph:

        potential_entities = [w.strip("?,.!") for w in query.split() if (w[0].isupper() or len(w) > 5)]
        graph_context = query_graph_context(potential_entities)


    if use_hybrid:
        results = hybrid_search(query, top_k=top_k * 2, user_role=user_role)
    else:
        depts = get_accessible_departments(user_role)
        results = vector_search(query, top_k=top_k * 2, department_filter=depts)

    if not results:
        return [], graph_context


    if use_rerank:
        results = rerank_results(query, results, top_k=top_k)
    else:
        results = results[:top_k]

    return results, graph_context
