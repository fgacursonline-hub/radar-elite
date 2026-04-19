import streamlit as st

# 1. Verifica se o usuário passou pelo login do app.py
if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Acesso negado. Por favor, faça login na página inicial.")
    if st.button("Ir para o Login"):
        st.switch_page("app.py")
    st.stop() # Trava a página aqui!

# 2. Se ele estiver logado, o código abaixo carrega normalmente
st.title("📈 Raio-X de Futuros")
# ... resto do seu código de backtest ...
