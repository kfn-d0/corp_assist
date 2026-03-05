"""
Módulo de Cache Semântico — evita recomputação de queries similares
Usa uma coleção dedicada no Qdrant para armazenar embeddings de queries e respostas
"""

import json
import logging
import time
from datetime import datetime, timezone

from qdrant_client.http import models

from backend.config import settings
from backend.ingest_pipeline import get_qdrant_client, generate_embeddings_batch

logger = logging.getLogger(__name__)


VECTOR_DIM = 768


def _ensure_cache_collection():
    """Garante que a coleção de cache existe no Qdrant"""
    client = get_qdrant_client()
    try:
        client.get_collection(settings.cache_collection_name)
    except Exception:
        logger.info(f"Criando coleção de cache: {settings.cache_collection_name}")
        client.create_collection(
            collection_name=settings.cache_collection_name,
            vectors_config=models.VectorParams(
                size=VECTOR_DIM,
                distance=models.Distance.COSINE,
            ),
        )


def get_cached_response(query: str) -> dict | None:
    """
    Busca uma resposta cacheada para uma query similar
    Retorna o payload (answer, sources, model, etc) se similaridade >= threshold
    """
    try:
        client = get_qdrant_client()
        _ensure_cache_collection()

        query_vector = generate_embeddings_batch([query])[0]

        results = client.search(
            collection_name=settings.cache_collection_name,
            query_vector=query_vector,
            limit=1,
            score_threshold=settings.cache_similarity_threshold,
            with_payload=True,
        )

        if results:
            hit = results[0]
            payload = hit.payload


            cached_at = payload.get("cached_at", 0)
            age_hours = (time.time() - cached_at) / 3600
            if age_hours > settings.cache_ttl_hours:
                logger.info(f"Cache expirado (idade: {age_hours:.1f}h). Ignorando.")
                return None

            logger.info(f"Cache HIT (score: {hit.score:.4f}) para query similar.")
            return {
                "answer": payload.get("answer", ""),
                "sources": json.loads(payload.get("sources_json", "[]")),
                "model_used": payload.get("model_used", ""),
                "tokens_used": payload.get("tokens_used", 0),
                "cached": True,
                "cache_score": hit.score,
            }

        return None

    except Exception as e:
        logger.warning(f"Erro ao consultar cache semântico: {e}")
        return None


def cache_response(query: str, answer: str, sources: list, model_used: str, tokens_used: int):
    """Salva a resposta no cache semantico"""
    try:
        client = get_qdrant_client()
        _ensure_cache_collection()

        query_vector = generate_embeddings_batch([query])[0]


        point_id = abs(hash(query)) % (2**63)

        client.upsert(
            collection_name=settings.cache_collection_name,
            points=[
                models.PointStruct(
                    id=point_id,
                    vector=query_vector,
                    payload={
                        "query": query,
                        "answer": answer,
                        "sources_json": json.dumps(sources, ensure_ascii=False),
                        "model_used": model_used,
                        "tokens_used": tokens_used,
                        "cached_at": time.time(),
                        "cached_at_iso": datetime.now(timezone.utc).isoformat(),
                    },
                )
            ],
        )
        logger.info(f"Resposta cacheada para: '{query[:50]}...'")

    except Exception as e:
        logger.warning(f"Erro ao salvar no cache semântico: {e}")
