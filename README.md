# CorpAssist - Digital Assistant

Projeto de Assistente corporativo de Q&A que utiliza RAG avançado com busca híbrida, reranking semântico, cache inteligente e detecção de contradições para consultar documentos internos com precisão e rastreabilidade.

---

<img width="1920" height="906" alt="111111" src="https://github.com/user-attachments/assets/2fabed7f-6cb7-44ca-a5ab-4a38aed2aa65" />
<img width="1920" height="900" alt="222222" src="https://github.com/user-attachments/assets/7a7895d8-74e5-4127-ac9e-de0627a0bde5" />
<img width="1920" height="888" alt="33333333" src="https://github.com/user-attachments/assets/98bd54e3-abed-4576-b4a1-abc1c49ae89c" />
<img width="1920" height="897" alt="4444444444" src="https://github.com/user-attachments/assets/4d17c06d-9bcd-438c-b678-0e7a198f343f" />
<img width="1920" height="876" alt="55555555555" src="https://github.com/user-attachments/assets/e6fdfc69-5545-4c17-9cb7-71e7ee34b0b9" />

---

## Visão Geral

O **CorpAssist** é uma projeto criado para permitir que colaboradores consultem informações em documentos internos (PDF, DOCX, TXT) de forma natural e segura. Utilizando técnicas avançadas de **RAG (Retrieval-Augmented Generation)**, o sistema garante que as respostas sejam baseadas exclusivamente no conteúdo indexado, reduzindo alucinações de modelos de IA e fornecendo citações verificáveis e trecho do texto.

### Diferenciais
- **Privacidade Total**: Execução local via Ollama (Llama 3), sem envio de dados para APIs externas.
- **Busca Híbrida 3.0**: Combina busca vetorial (Qdrant), busca lexical (BM25) e consultas em **Knowledge Graph (Neo4j)**.
- **Cross-Encoder Reranker**: Reordenação inteligente dos resultados usando modelo `ms-marco-MiniLM` para máxima precisão.
- **Trust Score**: Ranking por confiabilidade do documento (PDFs oficiais > notas internas).
- **Cache Semântico**: Queries similares retornam resposta cacheada instantaneamente, sem acionar o LLM.
- **Detecção de Contradição**: Identifica conflitos entre documentos e prioriza a versão mais recente.
- **Knowledge Gap Detection**: Sinaliza quando a pergunta esta fora do escopo dos documentos indexados.
- **Verificacao e Auto-Reparo**: Grader pos-resposta avalia suporte nas fontes. Se parcial, expande a busca e retenta automaticamente.
- **Query Understanding**: Reescrita inteligente de perguntas e **HyDE** (Hypothetical Document Embeddings).
- **Governança RBAC**: Permissões por departamento e autenticação de usuários.
- **Interface Premium**: Design moderno com alternância de temas (Claro/Escuro), Material Icons e layout corporativo. O tema escuro é utilizado por padrão.

---

## Arquitetura do Sistema

O sistema segue um pipeline avançado de RAG:

1.  **Ingestão**: Documentos são processados e fragmentados. Entidades e relações são extraídas para o **Neo4j**, enquanto vetores são salvos no **Qdrant**.
2.  **Processamento de Query**: A pergunta é reescrita pelo LLM e um documento hipotético (HyDE) é gerado.
3.  **Cache Semântico**: Se uma query similar já foi respondida, a resposta cacheada é retornada instantaneamente.
4.  **Recuperação Híbrida**: Busca simultânea no Qdrant (semântica), BM25 (lexical) e Neo4j (relacional).
5.  **Cross-Encoder Reranker**: Os resultados são reordenados por um modelo de reranking para máxima relevância.
6.  **Geração**: O modelo Llama 3 processa o contexto e gera a resposta final fundamentada.

---

## Stack Tecnológica

| Componente | Tecnologia |
|-----------|-----------|
| **LLM** | Ollama (Llama 3) |
| **Embeddings** | nomic-embed-text |
| **Vector DB** | Qdrant |
| **Graph DB** | Neo4j |
| **Busca Lexical** | Rank-BM25 |
| **Backend API** | FastAPI (Python 3.10+) |
| **Frontend UI** | Streamlit (Material Icons + Inter) |
| **Infraestrutura** | Docker & Docker Compose |
 
---
 
## Performance e Requisitos de Hardware

O sistema foi testado e validado em uma configuração de hardware intermediária, apresentando os seguintes comportamentos:

### Benchmarks de Referência
*   **Processador**: AMD Ryzen 5 5500 (6 Cores / 12 Threads)
*   **Memória**: 16GB RAM DDR4 2667MHz
*   **GPU**: AMD Radeon RX 5600 XT (6GB VRAM)
*   **OS**: Windows 10

### Observações de Desempenho
*   **Tempo de Resposta (Inference)**: ~1-3 tokens/segundo (rodando em CPU/GPU AMD via Ollama).
*   **Ingestão de Arquivos**: O processo de GraphRAG (Neo4j) é intensivo. Documentos curtos (2-5 páginas) levam em média 160-240 segundos para indexação completa com extração de relações.
*   **Uso de Memória**: O sistema completo (Docker + Backend + Frontend + Ollama) consome cerca de **10GB a 12GB de RAM** durante o pico de processamento.

> [!TIP]
> Para máquinas com menos de 16GB de RAM ou sem GPU dedicada, recomenda-se trocar o modelo `llama3` pelo `phi3` ou `gemma:2b` no arquivo `.env` para garantir fluidez.

---

## Guia de Instalação

### Pré-requisitos
1. [Ollama](https://ollama.ai) instalado e rodando.
2. Docker e Docker Compose instalados.

### Configuração Local
1. **Clonar o repositório**:
   ```bash
   cd AI_ENTERPRISE_RAG
   ```

2. **Criar Ambiente Virtual**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

3. **Instalar Dependências**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Variáveis de Ambiente**:
   O sistema já possui um `.env` padrão. Caso precise alterar o host do Ollama, edite este arquivo.

---

## Como Executar no CentOS (VM)

### Passo 1 — Iniciar Docker (Qdrant + Neo4j)

```bash
docker-compose -f docker/docker-compose.yml up -d qdrant neo4j
```

### Passo 2 — Limpar Cache Python (IMPORTANTE antes de cada deploy)

Sempre que sincronizar arquivos `.py` para a VM, execute este script para evitar que Python rode bytecode antigo:

```bash
bash scripts/clear_cache.sh
```

> **Por que isso importa?** Python armazena bytecode compilado em pastas `__pycache__`. Ao copiar arquivos `.py` atualizados para a VM, o Python pode continuar executando o bytecode `.pyc` antigo se ele não for apagado.

### Passo 3 — Iniciar o Backend (FastAPI)

```bash
nohup uvicorn backend.api:app --host 0.0.0.0 --port 8000 > ~/backend.log 2>&1 &
```

### Passo 4 — Iniciar o Frontend (Streamlit)

Em outro terminal (ou usando `&`):

```bash
nohup streamlit run frontend/streamlit_app.py --server.port 8501 > ~/frontend.log 2>&1 &
```

### Passo 5 — Monitorar os Logs

| Objetivo | Comando |
|---|---|
| Ver log do backend | `cat ~/backend.log` |
| Ver log do frontend | `cat ~/frontend.log` |
| Seguir backend em tempo real | `tail -f ~/backend.log` |
| Seguir frontend em tempo real | `tail -f ~/frontend.log` |

---

## Como Executar Localmente (Windows/Mac)

### Via Terminal
1. **Iniciar serviços (Qdrant + Neo4j)**:
   ```bash
   docker-compose -f docker/docker-compose.yml up -d qdrant neo4j
   ```
2. **Limpar cache Python** (PowerShell):
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/clear_cache.ps1
   ```
3. **Iniciar o Backend**:
   ```bash
   uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload
   ```
4. **Iniciar o Frontend** (em outro terminal):
   ```bash
   streamlit run frontend/streamlit_app.py
   ```

### Via Docker (Completo)
```bash
cd docker
docker-compose up --build
```
*Nota: Certifique-se de que o Ollama no host está acessível via `host.docker.internal`.*

---

## Interface do Usuário

O CorpAssist utiliza o design **CorpAssist Style** com as seguintes características:

- **Tema Escuro por Padrão**: O sistema inicia em modo escuro (Deep Navy). O usuário pode alternar para o modo claro pela barra lateral.
- **Material Icons**: Ícones profissionais do Google substituem emojis em toda a interface.
- **Páginas**: Chat, Upload de Documentos, Repositório Corporativo, Histórico de Consultas, Diagnóstico do Sistema e Gestão de Usuários (Admin).
- **Login**: Acesso padrão: `admin` / `admin`.

---

## Controle de Acesso (RBAC)

| Perfil | Permissões | Acesso a Departamentos |
|--------|------------|------------------------|
| **Admin** | Leitura/Escrita/Exclusão | Todos (*) |
| **RH** | Leitura/Escrita | RH + Público |
| **Engenharia** | Leitura/Escrita | Engenharia + Público |
| **Financeiro** | Leitura/Escrita | Financeiro + Público |
| **Público** | Apenas Consulta | Público |

---

## Avaliação de Qualidade (RAGAS)

```bash
python -m evaluation.ragas_eval
```
Métricas: Taxa de Resposta, Cobertura de Fontes, Groundedness e Latência.

---

## Estrutura de Pastas

```
AI_ENTERPRISE_RAG/
├── .streamlit/         # Configuração de tema do Streamlit
├── backend/            # Lógica do servidor, RAG e gestão de dados
├── frontend/           # Interface Streamlit (CorpAssist Style)
├── evaluation/         # Scripts de teste de qualidade
├── documents/          # Repositório de arquivos carregados
├── logs/               # Auditoria diária automatizada
├── docker/             # Configurações de containerização
├── scripts/            # Scripts utilitários (clear_cache, etc.)
├── docs/               # Documentações e guias de execução
└── README.md           # Este guia
```

---

## Segurança e Guardrails

- **Baixa Alucinação**: O assistente responde "Não encontrei informações" se os documentos não contêm a resposta.
- **Isolamento de Dados**: Nenhuma informação é enviada para APIs externas (OpenAI, Anthropic, etc).

---
