import streamlit as st

# 1. CONFIGURAÇÃO DA PÁGINA (DEVE SER A PRIMEIRA LINHA)
st.set_page_config(
    page_title="Radar Elite", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# 2. SISTEMA DE LOGIN COM MENU OCULTO
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    # CSS para esconder o menu lateral completamente antes do login
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {display: none;}
            [data-testid="stSidebarNav"] {display: none;}
            .stDeployButton {display:none;}
        </style>
    """, unsafe_allow_html=True)

    # Centraliza o formulário de login na tela
    _, col_login, _ = st.columns([1, 1, 1])
    
    with col_login:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown("### 🔐 Radar Elite")
        st.caption("Acesso exclusivo para membros do curso.")
        
        senha = st.text_input("Senha de acesso:", type="password", placeholder="Sua senha...")
        
        if st.button("Acessar Plataforma", use_container_width=True):
            # AJUSTE AQUI: Coloque a sua senha real entre as aspas
            if senha == "1234": 
                st.session_state['autenticado'] = True
                st.rerun()
            else:
                st.error("Senha incorreta. Tente novamente.")
    
    st.stop() # Interrompe a execução aqui se não estiver logado

# 3. CONTEÚDO APÓS LOGIN (A HOME DA PLATAFORMA)
# O menu lateral aparecerá automaticamente agora que o código passou pelo st.stop()
st.title("🎯 Bem-vindo ao Radar Elite")
st.markdown("---")

col_info, col_img = st.columns([2, 1])

with col_info:
    st.subheader("Olá, Caçador!")
    st.markdown("""
    Sua plataforma multipáginas está configurada e protegida.
    
    👈 **Navegue pelo Menu Lateral:** Selecione a estratégia que deseja operar (IFR, Keltner ou Médias). 
    Dentro de cada uma, você encontrará os radares e backtests específicos.
    """)
    
    st.info("💡 **Dica:** Cada estratégia agora carrega de forma independente, o que torna o sistema muito mais rápido.")

with col_img:
    st.write("📡 **Status do Sistema:** Operacional")
    st.caption("Versão 2.0 - 2026")
