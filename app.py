import streamlit as st

# 1. CONFIGURAÇÃO INICIAL (FORÇA O MENU LATERAL A EXPANDIR)
st.set_page_config(
    page_title="Radar Elite", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# 2. SISTEMA DE LOGIN (PORTA DE ENTRADA)
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    # Cria colunas para centralizar o campo de senha
    col1, col_centro, col3 = st.columns([1, 1, 1])
    
    with col_centro:
        unsafe_allow_html=True
        st.markdown("### 🔐 Acesso Restrito")
        st.write("Plataforma Caçadores de Elite")
        
        senha = st.text_input("Digite sua senha:", type="password", placeholder="Senha de aluno...")
        
        if st.button("Entrar no Sistema", use_container_width=True):
            # AJUSTE AQUI: Coloque a sua senha real entre as aspas
            if senha == "1234": 
                st.session_state['autenticado'] = True
                st.rerun()
            else:
                st.error("Senha incorreta. Verifique e tente novamente.")
    
    st.stop() # Bloqueia o resto da página se não estiver logado

# 3. O QUE APARECE APÓS O LOGIN (PAINEL PRINCIPAL)
st.title("🎯 Plataforma Caçadores de Elite")
st.markdown("---")

col_info, col_img = st.columns([2, 1])

with col_info:
    st.subheader("Bem-vindo, Caçador!")
    st.markdown("""
    Sua estrutura **Multipage** está ativa! 
    
    👈 **Olhe para o menu ao lado:** Lá você encontrará todas as ferramentas organizadas:
    * **01 Raio-X Futuros:** Backtests de WIN e WDO.
    * **02 Caçador de Elite:** Seus radares e varreduras.
    """)
    
    st.info("💡 Se o menu lateral não aparecer, clique na pequena seta **( > )** no canto superior esquerdo da tela.")

with col_img:
    # Espaço para o seu Logo (Coloque o link da sua imagem se quiser)
    st.write("Versão 2.0 - 2026")
