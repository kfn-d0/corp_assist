"""
Módulo de Verificação de Resposta — avalia se a resposta do LLM está suportada
pelas fontes recuperadas e executa auto-reparo quando necessário.
"""

import logging

import ollama

from backend.config import settings

logger = logging.getLogger(__name__)

GRADER_PROMPT = """Você é um verificador rigoroso de respostas corporativas. Sua tarefa é avaliar se a RESPOSTA está integralmente suportada pelos TRECHOS DE CONTEXTO fornecidos.

RESPOSTA A VERIFICAR:
{answer}

TRECHOS DE CONTEXTO (fontes):
{context}

AVALIE com rigor:
1. Cada afirmação da resposta tem base em algum trecho?
2. Há extrapolação (informação que NÃO está nos trechos)?
3. As citações correspondem ao conteúdo real?

RESPONDA EXATAMENTE neste formato JSON (nada mais):
{{"verdict": "SUPPORTED|PARTIAL|UNSUPPORTED", "confidence": 0.0-1.0, "reason": "explicação breve"}}

Regras:
- SUPPORTED: >= 80% das afirmações estão nos trechos. confidence >= 0.8
- PARTIAL: 40-79% das afirmações estão nos trechos. confidence 0.4-0.79
- UNSUPPORTED: < 40% das afirmações OU resposta inventada. confidence < 0.4
- Se a resposta é "Não encontrei informações", marque SUPPORTED com confidence 1.0 (gap correto).
"""


def grade_answer(answer: str, chunks: list[dict]) -> dict:
    """
    Avalia se a resposta está suportada pelas fontes recuperadas.
    Retorna: {"verdict": str, "confidence": float, "reason": str}
    """
    if not answer or not chunks:
        return {"verdict": "UNSUPPORTED", "confidence": 0.0, "reason": "Sem resposta ou sem fontes."}

    gap_phrases = ["não consegui encontrar", "não encontrei informações"]
    if any(p in answer.lower() for p in gap_phrases):
        return {"verdict": "SUPPORTED", "confidence": 1.0, "reason": "Resposta de gap legítima."}

    context_parts = []
    for i, chunk in enumerate(chunks[:5], 1):
        meta = chunk.get("metadata", {})
        doc = meta.get("document_name", "Doc")
        page = meta.get("page", 0)
        context_parts.append(f"[Trecho {i} - {doc}, Pag.{page}]\n{chunk['text'][:400]}")

    context_text = "\n\n".join(context_parts)

    try:
        response = ollama.chat(
            model=settings.llm_model,
            messages=[
                {"role": "user", "content": GRADER_PROMPT.format(
                    answer=answer[:800],
                    context=context_text,
                )},
            ],
            options={
                "temperature": 0.0,
                "num_predict": 200,
            },
        )
        result_text = response["message"]["content"].strip()

        return _parse_grader_response(result_text)

    except Exception as e:
        logger.warning(f"Erro no grader de verificação: {e}")
        return {"verdict": "SUPPORTED", "confidence": 0.7, "reason": f"Erro no grader: {e}"}


def _parse_grader_response(text: str) -> dict:
    """Parse a resposta do grader (JSON)."""
    import json

    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(text[start:end])
            verdict = data.get("verdict", "SUPPORTED").upper()
            confidence = float(data.get("confidence", 0.7))
            reason = data.get("reason", "")

            if verdict not in ("SUPPORTED", "PARTIAL", "UNSUPPORTED"):
                verdict = "SUPPORTED"
            confidence = max(0.0, min(1.0, confidence))

            return {"verdict": verdict, "confidence": confidence, "reason": reason}
    except (json.JSONDecodeError, ValueError):
        pass

    text_upper = text.upper()
    if "UNSUPPORTED" in text_upper:
        return {"verdict": "UNSUPPORTED", "confidence": 0.3, "reason": text[:100]}
    elif "PARTIAL" in text_upper:
        return {"verdict": "PARTIAL", "confidence": 0.55, "reason": text[:100]}
    else:
        return {"verdict": "SUPPORTED", "confidence": 0.75, "reason": text[:100]}
