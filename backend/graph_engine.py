"""
Graph Engine — Gerencia a extração de entidades e relações para o Neo4j (GraphRAG).
Permite consultas complexas baseadas em conexões entre documentos.
"""

import json
from typing import List, Dict, Any
from neo4j import GraphDatabase
import ollama

from backend.config import settings


_driver = None

def get_neo4j_driver():
    """Retorna o driver do Neo4j."""
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
    return _driver


GRAPH_EXTRACTION_PROMPT = """
Sua tarefa é extrair ENTIDADES e RELAÇÕES do texto abaixo para construir um Grafo de Conhecimento corporativo.

TEXTO:
{text}

FORMATO DE SAÍDA (JSON APENAS):
{{
    "entities": [
        {{"name": "Nome da Entidade", "type": "Pessoa|Departamento|Projeto|Tecnologia|Documento|Regra"}},
        ...
    ],
    "relationships": [
        {{"source": "Entidade A", "target": "Entidade B", "relation": "TRABALHA_EM|PERTENCE_A|USA|RESPONSAVEL_POR|DEFINE"}},
        ...
    ]
}}

REGRAS:
1. Retorne APENAS o JSON.
2. Seja preciso com nomes próprios.
3. Se não houver relações claras, retorne listas vazias.
"""

def extract_graph_data(text: str) -> Dict[str, Any]:
    """Usa o LLM para extrair triplas (entidade-relação-entidade) do texto."""
    try:
        response = ollama.generate(
            model=settings.llm_model,
            prompt=GRAPH_EXTRACTION_PROMPT.format(text=text),
            format="json",
            options={"temperature": 0.1}
        )
        return json.loads(response["response"])
    except Exception as e:
        print(f"Erro na extração de grafo: {e}")
        return {"entities": [], "relationships": []}


def add_graph_data(doc_name: str, graph_data: Dict[str, Any]):
    """Insere as entidades e relações no Neo4j de forma eficiente (Batch)."""
    try:
        driver = get_neo4j_driver()
        with driver.session() as session:

            session.run("MERGE (d:Document {name: $name})", name=doc_name)


            for entity in graph_data.get("entities", []):
                name = entity.get("name")
                e_type = entity.get("type", "Thing").replace(" ", "_").replace("-", "_")
                e_type = "".join(c for c in e_type if c.isalnum() or c == "_")
                if not e_type or e_type[0].isdigit(): e_type = "Entity_" + e_type
                
                if name:
                    query = f"MERGE (e:{e_type} {{name: $name}}) WITH e MATCH (d:Document {{name: $doc_name}}) MERGE (d)-[:CONTÉM]->(e)"
                    session.run(query, name=name, doc_name=doc_name)


            for rel in graph_data.get("relationships", []):
                source = rel.get("source")
                target = rel.get("target")
                relation = rel.get("relation", "RELATES_TO").replace(" ", "_").upper()
                if source and target:

                    query = f"MATCH (a {{name: $source}}), (b {{name: $target}}) MERGE (a)-[:{relation}]->(b)"
                    session.run(query, source=source, target=target)
    except Exception as e:
        print(f"Aviso: Falha ao inserir dados no Neo4j (GraphRAG): {e}")
    except Exception as e:
        print(f"Aviso: Falha ao inserir dados no Neo4j (GraphRAG): {e}")


def query_graph_context(entities: List[str]) -> str:
    """Busca as conexões das entidades mencionadas para fornecer contexto expandido."""
    if not entities:
        return ""
    
    try:
        driver = get_neo4j_driver()
        context_parts = []
        
        with driver.session() as session:
            for entity in entities:
                result = session.execute_read(
                    lambda tx: tx.run(
                        "MATCH (e {name: $name})-[r]->(neighbor) "
                        "RETURN e.name as source, type(r) as rel, neighbor.name as target "
                        "LIMIT 10",
                        name=entity
                    )
                )
                for record in result:
                    context_parts.append(f"({record['source']}) -[{record['rel']}]-> ({record['target']})")
                    
        if not context_parts:
            return ""
            
        return "Conhecimento Relacional (Grafo):\n" + "\n".join(context_parts)
    except Exception as e:
        print(f"Aviso: Falha ao buscar contexto no Neo4j (GraphRAG): {e}")
        return ""
