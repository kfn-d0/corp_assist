"""
Módulo de Query Understanding — Reescrita inteligente e HyDE.
Transforma perguntas vagas em consultas ricas para melhorar a recuperação.
"""

import ollama
from backend.config import settings


REWRITE_PROMPT = """
Você é um especialista em reescrita de consultas para sistemas RAG corporativos. 
Sua tarefa é transformar a pergunta curta ou vaga de um usuário em uma consulta detalhada e tecnicamente clara em Português do Brasil.
A consulta reescrita deve ser otimizada para busca em documentos internos de políticas, manuais e engenharia.

REGRAS:
1. Mantenha o idioma original (Português do Brasil).
2. Não adicione saudações ou explicações, retorne APENAS a consulta reescrita.
3. Se a pergunta já for clara, melhore os termos técnicos.
4. Tente prever o que o usuário realmente quer saber (intencionalidade).

Exemplo: "qual regra de ferias?" -> "Qual é a política oficial de concessão, duração e agendamento de férias da empresa?"
Exemplo: "config dns" -> "Quais são as diretrizes de configuração e endereços de servidores DNS internos?"

Pergunta do Usuário: {query}
Consulta Reescrita:
"""

HYDE_PROMPT = """
Sua tarefa é escrever um parágrafo de RESPOSTA HIPOTÉTICA para a pergunta abaixo. 
Este parágrafo será usado para encontrar documentos similares em um banco vetorial. 
Não se preocupe em estar 100% correto sobre fatos reais da empresa, use seu conhecimento geral de padrões corporativos.

Pergunta: {query}
Resposta Hipotética:
"""


def rewrite_query(query: str) -> str:
    """Usa o LLM para reescrever e enriquecer a pergunta do usuário."""
    if len(query.split()) > 10:
        return query

    try:
        response = ollama.generate(
            model=settings.llm_model,
            prompt=REWRITE_PROMPT.format(query=query),
            options={"temperature": 0.2, "top_p": 0.9}
        )
        rewritten = response["response"].strip().replace('"', '')
        return rewritten
    except Exception as e:
        print(f"Erro ao reescrever query: {e}")
        return query


def generate_hyde_response(query: str) -> str:
    """Gera uma resposta hipotética (HyDE) para melhorar o recall vetorial."""
    try:
        response = ollama.generate(
            model=settings.llm_model,
            prompt=HYDE_PROMPT.format(query=query),
            options={"temperature": 0.5}
        )
        return response["response"].strip()
    except Exception as e:
        print(f"Erro ao gerar HyDE: {e}")
        return query


def process_query_for_retrieval(query: str, use_hyde: bool = True) -> str:
    """
    Pipeline principal de Query Understanding:
    1. Reescreve a query.
    2. (Opcional) Adiciona o HyDE para expansão.
    """
    rewritten = rewrite_query(query)
    
    if use_hyde:
        hyde = generate_hyde_response(rewritten)

        return f"Pergunta: {rewritten}\nResposta Provável: {hyde}"
    
    return rewritten
