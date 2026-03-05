"""
Frontend Streamlit — Enterprise Knowledge RAG System.
Versão Premium CorpAssist: Design moderno, Material Icons e seletor de tema.
"""

import os
from datetime import datetime

import requests
import streamlit as st


st.set_page_config(
    page_title="CorpAssist — Digital Assistant",
    layout="wide",
    initial_sidebar_state="expanded",
)


if "theme" not in st.session_state:
    st.session_state.theme = "dark"


def inject_theme_css(theme):
    """Injeta CSS baseado no tema selecionado."""
    

    if theme == "dark":
        primary = "#3b82f6"
        bg = "#0f172a"
        surface = "#1e293b"
        text = "#cbd5e1"
        header_text = "#ffffff"
        border = "#1e293b"
        secondary_bg = "#0d1117"
    else:
        primary = "#3b82f6"
        bg = "#f8fafc"
        surface = "#ffffff"
        text = "#334155"
        header_text = "#0f172a"
        border = "#e2e8f0"
        secondary_bg = "#f1f5f9"

    css = f"""
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    
    <style>
        :root {{
            --primary: {primary};
            --bg: {bg};
            --surface: {surface};
            --text: {text};
            --header-text: {header_text};
            --border: {border};
            --secondary-bg: {secondary_bg};
        }}

        /* Reset e Fontes */
        .stApp {{
            background-color: var(--bg);
            color: var(--text);
            font-family: 'Inter', sans-serif;
        }}

        h1, h2, h3, h4, .main-header {{
            color: var(--header-text) !important;
            font-family: 'Inter', sans-serif;
            font-weight: 700;
        }}

        /* Navegação Sidebar */
        [data-testid="stSidebar"] {{
            background-color: var(--surface);
            border-right: 1px solid var(--border);
        }}

        .sidebar-title {{
            font-weight: 800;
            font-size: 1.2rem;
            color: var(--header-text);
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 2rem;
        }}

        /* Cards e Containers */
        .info-card {{
            background: var(--surface);
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid var(--border);
            margin-bottom: 1rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            transition: all 0.2s ease;
        }}
        
        .info-card:hover {{
            border-color: var(--primary);
            transform: translateY(-2px);
        }}

        /* Chat e Mensagens */
        .stChatMessage {{
            background-color: var(--surface) !important;
            border: 1px solid var(--border) !important;
            border-radius: 12px !important;
            padding: 1rem !important;
            margin-bottom: 1rem !important;
        }}
        
        /* Fontes e Citações Side Panel Style */
        .source-card {{
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 0.8rem;
            transition: border-color 0.2s;
        }}
        
        .source-card:hover {{
            border-color: var(--primary);
        }}

        .source-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
        }}

        .source-title {{
            font-weight: 600;
            font-size: 0.85rem;
            color: var(--header-text);
            display: flex;
            align-items: center;
            gap: 5px;
        }}

        .relevance-badge {{
            font-size: 0.7rem;
            background: var(--border);
            padding: 2px 8px;
            border-radius: 4px;
            color: var(--text);
        }}

        .source-excerpt {{
            font-size: 0.8rem;
            color: var(--text);
            opacity: 0.8;
            line-height: 1.5;
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}

        /* Material Icon Helper */
        .mi {{
            font-family: 'Material Icons';
            font-weight: normal;
            font-style: normal;
            display: inline-block;
            line-height: 1;
            text-transform: none;
            letter-spacing: normal;
            word-wrap: normal;
            white-space: nowrap;
            direction: ltr;
            -webkit-font-smoothing: antialiased;
            vertical-align: middle;
        }}

        /* Botões e Inputs */
        .stButton button {{
            border-radius: 8px;
            font-weight: 600;
        }}
        
        .stChatInputContainer {{
            border-radius: 999px !important;
            background: var(--surface) !important;
            border: 1px solid var(--border) !important;
        }}

        /* Forçar cores de texto em elementos Streamlit (Light theme fix) */
        .stApp p, .stApp span, .stApp label, .stApp div {{
            color: var(--text);
        }}

        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp strong, .stApp b {{
            color: var(--header-text) !important;
        }}

        [data-testid="stWidgetLabel"] label, [data-testid="stWidgetLabel"] p {{
            color: var(--header-text) !important;
        }}

        .stRadio label span, .stSelectbox label span, .stTextInput label span {{
            color: var(--header-text) !important;
        }}

        .stRadio div[role="radiogroup"] label p {{
            color: var(--text) !important;
        }}

        .stCaption, [data-testid="stCaptionContainer"] p {{
            color: var(--text) !important;
            opacity: 0.7;
        }}

        .stMarkdown p {{
            color: var(--text);
        }}

        [data-testid="stExpander"] summary span {{
            color: var(--header-text) !important;
        }}

        /* Chat input text */
        .stChatInput textarea {{
            color: var(--header-text) !important;
        }}

        /* Info/Warning/Error boxes */
        .stAlert p {{
            color: inherit !important;
        }}

        /* Material Icon color fix */
        .mi {{
            color: inherit;
        }}

        /* Botões primários: texto branco no tema claro */
        .stButton button {{
            color: #ffffff !important;
            background-color: var(--primary) !important;
            border: none !important;
        }}

        .stButton button:hover {{
            opacity: 0.9;
        }}

        .stFormSubmitButton button {{
            color: #ffffff !important;
            background-color: var(--primary) !important;
            border: none !important;
        }}

        /* Esconde elementos nativos desnecessários */
        #MainMenu, footer {{visibility: hidden;}}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

inject_theme_css(st.session_state.theme)


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

def api_request(method, endpoint, **kwargs):
    """Realiza requisições para o backend API."""
    url = f"{API_BASE_URL}{endpoint}"
    try:
        response = requests.request(method, url, timeout=300, **kwargs)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            st.error("Sessão expirada. Por favor, faça login novamente.")
            return None
        else:
            st.error(f"Erro {response.status_code}: {response.text}")
            return None
    except Exception as e:
        st.error(f"Falha de conexão: {str(e)}")
        return None

def format_timestamp(ts):
    """Formata timestamp ISO para leitura humana."""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return ts


def login_screen():
    """Tela de login estilizada CorpAssist."""
    st.markdown("""
    <div style="text-align:center; padding-top: 100px;">
        <h1 class="main-header"><span class="mi" style="font-size:3rem; color:var(--primary);">dashboard</span> CorpAssist</h1>
        <p style="opacity:0.7;">Autenticação Corporativa</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.container():
        _, mid, _ = st.columns([1, 1.2, 1])
        with mid:
            with st.form("login_form"):
                username = st.text_input("Usuário")
                password = st.text_input("Senha", type="password")
                submit = st.form_submit_button("Entrar no Dashboard", use_container_width=True)
                
                if submit:
                    if not username or not password:
                        st.warning("Credenciais obrigatórias.")
                    else:
                        with st.spinner("Autenticando..."):
                            user = api_request("POST", "/api/login", json={"username": username, "password": password})
                            if user:
                                st.session_state.authenticated = True
                                st.session_state.user = user
                                st.rerun()
            st.caption("Suporte: admin / admin")

def logout():
    """Limpa a sessão e desloga."""
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.chat_history = []
    st.rerun()


if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    login_screen()
    st.stop()

current_user = st.session_state.user
user_role = current_user["role"]


with st.sidebar:
    st.markdown("""
    <div class="sidebar-title">
        <span class="mi" style="color:var(--primary);">dashboard</span>
        <span>CorpAssist</span>
    </div>
    """, unsafe_allow_html=True)


    with st.container():
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:12px; padding:10px; background:var(--bg); border-radius:10px; margin-bottom:20px; border:1px solid var(--border);">
            <div style="width:35px; height:35px; background:var(--primary); color:white; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:bold;">
                {current_user['username'][0].upper()}
            </div>
            <div>
                <div style="font-size:0.9rem; font-weight:600; color:var(--header-text);">{current_user['username']}</div>
                <div style="font-size:0.75rem; opacity:0.6;">{current_user['department'].upper()}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)


    theme_choice = st.radio(
        "Aparência",
        ["Claro", "Escuro"],
        index=0 if st.session_state.theme == "light" else 1,
        horizontal=True,
        label_visibility="collapsed"
    )
    new_theme = "light" if theme_choice == "Claro" else "dark"
    if new_theme != st.session_state.theme:
        st.session_state.theme = new_theme
        st.rerun()

    st.markdown("---")


    nav_icons = {
        "Chat": "chat",
        "Upload": "upload_file",
        "Base": "folder",
        "Histórico": "history",
        "Saúde": "monitor_heart"
    }
    if user_role == "admin":
        nav_icons["Usuários"] = "group"

    selected_nav = st.radio(
        "Navegação",
        list(nav_icons.keys()),
        label_visibility="collapsed"
    )
    

    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:10px; color:var(--primary); margin-top:5px; font-weight:600;">
        <span class="mi">{nav_icons[selected_nav]}</span>
        <span>{selected_nav}</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    
    if st.button("Sair do Sistema", use_container_width=True):
        logout()


if selected_nav == "Chat":
    st.markdown('<h2><span class="mi" style="vertical-align:bottom;">chat</span> Assistente Digital</h2>', unsafe_allow_html=True)
    st.markdown('<p style="opacity:0.7;">Consulta em linguagem natural sobre a base de conhecimento corporativa.</p>', unsafe_allow_html=True)

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []


    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            

            if msg.get("sources"):
                with st.expander("🔍 Fontes Consultadas", expanded=False):
                    for idx, source in enumerate(msg["sources"], 1):
                        st.markdown(f"""
                        <div class="source-card">
                            <div class="source-header">
                                <span class="source-title">
                                    <span class="mi" style="font-size:1rem; color:var(--primary);">description</span> 
                                    <b>{source['document']}</b> (Pág. {source.get('page', 1)})
                                </span>
                                <span class="relevance-badge">Score: {source.get('relevance_score', 0):.2f}</span>
                            </div>
                            <div class="source-excerpt">"{source.get('excerpt', '')}"</div>
                        </div>
                        """, unsafe_allow_html=True)

            if msg.get("latency_ms"):
                st.caption(f"Processado em {msg['latency_ms']:.0f}ms | Modelo: {msg.get('model_used', '')}")


    query = st.chat_input("Como posso ajudar hoje?")

    if query:
        st.session_state.chat_history.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        with st.chat_message("assistant"):
            with st.spinner("Analisando base de documentos..."):
                result = api_request("POST", "/api/query", json={"question": query, "user_role": user_role})

            if result:
                answer = result.get("answer", "Sem resposta.")
                sources = result.get("sources", [])
                
                st.markdown(answer)
                

                if sources:
                    with st.expander("🔍 Fontes Consultadas", expanded=False):
                        for idx, source in enumerate(sources, 1):
                            st.markdown(f"""
                            <div class="source-card">
                                <div class="source-header">
                                    <span class="source-title">
                                        <span class="mi" style="font-size:1rem; color:var(--primary);">description</span> 
                                        <b>{source['document']}</b> (Pág. {source.get('page', 1)})
                                    </span>
                                    <span class="relevance-badge">Score: {source.get('relevance_score', 0):.2f}</span>
                                </div>
                                <div class="source-excerpt">"{source.get('excerpt', '')}"</div>
                            </div>
                            """, unsafe_allow_html=True)

                latency = result.get("latency_ms", 0)
                model = result.get("model_used", "Llama 3")
                st.caption(f"Processado em {latency:.0f}ms | Modelo: {model}")

                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": sources,
                    "latency_ms": latency,
                    "model_used": model,
                })
                st.rerun()
            else:
                st.error("Erro no processamento. Verifique se o servidor está ativo.")


elif selected_nav == "Upload":
    st.markdown('<h2><span class="mi" style="vertical-align:bottom;">upload_file</span> Ingestão de Conhecimento</h2>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    with col1:
        u_file = st.file_uploader("Arraste documentos para indexar", type=["pdf", "docx", "txt"])
    with col2:
        dept = st.selectbox("Departamento Responsável", ["public", "hr", "engineering", "finance", "legal"])

    if u_file:
        st.markdown(f"""
        <div class="info-card">
            <strong>Arquivo Pronto:</strong> {u_file.name}<br>
            <span style="opacity:0.6;">Tamanho: {u_file.size / 1024:.1f} KB</span>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Iniciar Indexação Automática", type="primary", use_container_width=True):
            with st.spinner("Processando (Vetores + Grafo)..."):
                files = {"file": (u_file.name, u_file.getvalue(), u_file.type)}
                data = {"department": dept, "user_role": user_role}
                res = api_request("POST", "/api/upload", files=files, data=data)
            if res:
                st.success("Documento integrado à base de conhecimento.")
                st.balloons()


elif selected_nav == "Base":
    st.markdown('<h2><span class="mi" style="vertical-align:bottom;">folder</span> Repositório Corporativo</h2>', unsafe_allow_html=True)
    
    docs = api_request("GET", f"/api/documents?user_role={user_role}")
    if docs:
        for d in docs:
            st.markdown(f"""
            <div class="info-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <div style="font-weight:700; color:var(--header-text);"><span class="mi">description</span> {d.get('document_name')}</div>
                        <div style="font-size:0.8rem; opacity:0.6;">Indexado em {format_timestamp(d.get('upload_timestamp'))} | Depto: {d.get('department').upper()}</div>
                    </div>
                    <div style="text-align:right;">
                        <span style="font-size:0.8rem; font-weight:700; color:var(--primary);">{d.get('total_chunks')} Chunks</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if user_role == "admin":
                if st.button("Remover do Índice", key=f"del_{d.get('document_id')}"):
                    api_request("DELETE", f"/api/documents/{d.get('document_name')}?user_role={user_role}")
                    st.rerun()
    else:
        st.info("Nenhum arquivo indexado.")


elif selected_nav == "Histórico":
    st.markdown('<h2><span class="mi" style="vertical-align:bottom;">history</span> Logs de Consulta</h2>', unsafe_allow_html=True)
    hist = api_request("GET", "/api/history?limit=30")
    if hist:
        for h in hist:
            with st.expander(f"{format_timestamp(h.get('timestamp'))} — {h.get('question')[:60]}..."):
                st.markdown(f"**Pergunta:** {h.get('question')}")
                st.markdown(f"**Resposta:** {h.get('answer')}")
                st.caption(f"Latência: {h.get('latency_ms', 0):.0f}ms | Perfil: {h.get('user_role')}")
    else:
        st.info("Histórico vazio.")


elif selected_nav == "Saúde":
    st.markdown('<h2><span class="mi" style="vertical-align:bottom;">monitor_heart</span> Diagnóstico do Sistema</h2>', unsafe_allow_html=True)
    health = api_request("GET", "/api/health")
    if health:
        s = health.get("status")
        color = "green" if s == "healthy" else "red"
        st.markdown(f"""
        <div class="info-card" style="border-left:5px solid {color};">
            <h4 style="margin:0;">Status Geral: {s.upper()}</h4>
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"""
            <div class="info-card">
                <strong><span class="mi">psychology</span> IA (Ollama)</strong><br>
                Modelo: {health.get('llm_model')}<br>
                Status: {"Online" if health.get('ollama_connected') else "Offline"}
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="info-card">
                <strong><span class="mi">storage</span> Base Vetorial</strong><br>
                Documentos: {health.get('documents_indexed', 0)}<br>
                Status: {"Online" if health.get('qdrant_connected') else "Offline"}
            </div>
            """, unsafe_allow_html=True)


elif selected_nav == "Usuários":
    st.markdown('<h2><span class="mi" style="vertical-align:bottom;">group</span> Gestão de Acessos</h2>', unsafe_allow_html=True)
    
    with st.expander("Cadastrar Novo Usuário", expanded=False):
        with st.form("add_u"):
            u = st.text_input("Username")
            p = st.text_input("Senha", type="password")
            r = st.selectbox("Perfil", ["admin", "hr", "engineering", "finance", "public"])
            d = st.selectbox("Depto", ["public", "hr", "engineering", "finance"])
            if st.form_submit_button("Salvar Registro"):
                if api_request("POST", f"/api/users?admin_role={user_role}", json={"username":u, "password":p, "role":r, "department":d}):
                    st.success("Usuário criado.")
                    st.rerun()

    users = api_request("GET", f"/api/users?admin_role={user_role}")
    if users:
        for u in users:
            st.markdown(f"""
            <div class="info-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <strong>{u['username']}</strong><br>
                        <span style="font-size:0.8rem; opacity:0.6;">Role: {u['role']} | Depto: {u['department']}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if u['username'] != "admin":
                if st.button("Excluir", key=f"u_del_{u['username']}"):
                    api_request("DELETE", f"/api/users/{u['username']}?admin_role={user_role}")
                    st.rerun()
