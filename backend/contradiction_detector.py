"""
Módulo de Detecção de Contradição — identifica conflitos entre documentos recuperados.
Usa o LLM para comparar trechos e sinalizar divergências ao usuário.
"""

import logging

import ollama

from backend.config import settings

logger = logging.getLogger(__name__)

CONTRADICTION_PROMPT = """Você é um analista de documentos corporativos. Analise os trechos abaixo e determine se há CONTRADIÇÕES entre eles.

TRECHOS:
{chunks_text}

INSTRUÇÕES:
1. Compare as informações dos trechos acima.
2. Se houver informações CONTRADITÓRIAS (dados conflitantes, números diferentes, regras opostas), responda EXATAMENTE neste formato:
   CONTRADIÇÃO DETECTADA: [descreva brevemente a contradição]. Documento mais recente: [nome do documento mais recente, baseado na data].
3. Se NÃO houver contradições, responda EXATAMENTE: SEM CONTRADIÇÃO
4. Seja objetivo e conciso. Máximo 2 frases.
5. RESPONDA EM PORTUGUÊS DO BRASIL.
6. NÃO USE EMOJIS.
"""


def detect_contradictions(chunks: list[dict]) -> str:
    """
    Analisa chunks recuperados para detectar contradições entre fontes.
    Retorna uma string de aviso se contradições forem encontradas, ou string vazia.
    """
    if len(chunks) < 2:
        return ""


    doc_groups = {}
    for chunk in chunks:
        meta = chunk.get("metadata", {})
        doc_name = meta.get("document_name", "Unknown")
        if doc_name not in doc_groups:
            doc_groups[doc_name] = {
                "text": chunk["text"][:500],
                "timestamp": meta.get("timestamp", ""),
                "version": meta.get("version", 1),
            }


    if len(doc_groups) < 2:
        return ""


    chunks_text = ""
    for doc_name, data in doc_groups.items():
        chunks_text += f"\n--- Documento: {doc_name} (Data: {data['timestamp']}, Versão: {data['version']}) ---\n"
        chunks_text += data["text"] + "\n"

    try:
        response = ollama.chat(
            model=settings.llm_model,
            messages=[
                {"role": "user", "content": CONTRADICTION_PROMPT.format(chunks_text=chunks_text)},
            ],
            options={
                "temperature": 0.0,
                "num_predict": 256,
            },
        )
        result = response["message"]["content"].strip()

        if "SEM CONTRADIÇÃO" in result.upper() or "SEM CONTRADICAO" in result.upper():
            return ""

        if "CONTRADIÇÃO" in result.upper() or "CONTRADICAO" in result.upper():
            logger.info(f"Contradição detectada: {result[:100]}")
            return result

        return ""

    except Exception as e:
        logger.warning(f"Erro na detecção de contradição: {e}")
        return ""
