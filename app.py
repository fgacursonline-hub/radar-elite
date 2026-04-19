import streamlit as st

# Configuração da Página (Deve ser a primeira linha de código)
st.set_page_config(page_title="Radar Elite", layout="wide", page_icon="🎯")

# --- SISTEMA DE LOGIN SIMPLIFICADO ---
# (Se você já tem um sistema de login com Session State, mantenha a lógica aqui)
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.title("🔐 Acesso Restrito - Caçadores de Elite")
    senha = st.text_input("Digite sua senha de acesso:", type="password")
    if st.button("Entrar"):
        if senha == "SUA_SENHA_AQUI": # Ajuste para sua senha real
            st.session_state['autenticado'] = True
            st.rerun()
        else:
            st.error("Senha incorreta.")
    st.stop() # Interrompe o código aqui se não estiver logado

# --- PÁGINA DE BOAS-VINDAS (HOME) ---
st.title("🎯 Plataforma Caçadores de Elite")
st.markdown("---")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Bem-vindo, Caçador!")
    st.write("Sua estrutura multipáginas está pronta. Utilize o menu ao lado para navegar.")
    st.info("💡 **Dica:** O Raio-X de Futuros agora está em sua própria página, o que garante mais velocidade no processamento de dados.")

with col2:
    st.image("https://seu-logo-aqui.png", width=200) # Se tiver um link de logo, coloque aqui
