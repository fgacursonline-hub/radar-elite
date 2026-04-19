import streamlit as st

# 1. Configuração da Página (Primeira linha sempre)
st.set_page_config(page_title="Radar Elite", layout="wide", initial_sidebar_state="collapsed")

# 2. Controle de Sessão
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

# 3. Tela de Login (Apenas se não estiver logado)
if not st.session_state['autenticado']:
    # CSS para esconder o menu lateral antes do login
    st.markdown("<style>[data-testid='stSidebar'] {display: none;} [data-testid='stSidebarNav'] {display: none;}</style>", unsafe_allow_html=True)
    
    _, col_login, _ = st.columns([1, 1, 1])
    with col_login:
        st.markdown("<br><br>🎯 Caçadores de Elite<br>", unsafe_allow_html=True)
        usuario = st.text_input("Usuário").lower().strip()
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar no Sistema", use_container_width=True):
            # Verificação simples (adicione seus usuários aqui)
            if usuario == "aluno" and senha == "1234":
                st.session_state['autenticado'] = True
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
    st.stop()

# 4. Conteúdo Pós-Login (Home)
st.title("🎯 Bem-vindo, Caçador!")
st.write("A plataforma está liberada. Escolha uma estratégia no menu lateral à esquerda.")
