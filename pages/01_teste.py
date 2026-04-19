import streamlit as st

st.set_page_config(page_title="Página de Teste", layout="wide")

st.title("✅ Sucesso!")
st.write("Se você está lendo isso, a Multipage funcionou.")

if st.button("Voltar para Home"):
    st.switch_page("app.py")
