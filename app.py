# --- SISTEMA DE LOGIN COM MENU OCULTO ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    # CSS para esconder o menu lateral completamente
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {display: none;}
            [data-testid="stSidebarNav"] {display: none;}
        </style>
    """, unsafe_allow_html=True)

    # Centraliza o formulário de login
    _, col_login, _ = st.columns([1, 1, 1])
    
    with col_login:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown("### 🔐 Radar Elite")
        st.caption("Acesso restrito para alunos.")
        
        senha = st.text_input("Senha de acesso:", type="password", placeholder="Digite sua senha...")
        
        if st.button("Acessar Plataforma", use_container_width=True):
            # AJUSTE AQUI: Coloque a sua senha real
            if senha == "SUA_SENHA_AQUI":
                st.session_state['autenticado'] = True
                st.rerun()
            else:
                st.error("Senha incorreta.")
    
    st.stop() # Interrompe aqui. Nada abaixo será lido sem a senha.

# --- TUDO ABAIXO SÓ APARECE APÓS O LOGIN ---
# O menu lateral volta a aparecer automaticamente aqui
st.title("🎯 Bem-vindo ao Radar Elite")
st.markdown("---")
# ... resto do seu código de boas-vindas ...
