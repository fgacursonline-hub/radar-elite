import streamlit as st
import pandas as pd
from datetime import datetime

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA (Deve ser a 1ª linha)
# ==========================================
st.set_page_config(
    page_title="Caçadores de Elite | Quant Dashboard",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. SISTEMA DE AUTENTICAÇÃO
# ==========================================
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>🦅 Caçadores de Elite</h1>", unsafe_allow_html=True)
        st.markdown("<h4 style='text-align: center;'>Terminal Quantitativo</h4>", unsafe_allow_html=True)
        st.divider()
        
        email = st.text_input("Email de Acesso:")
        senha = st.text_input("Senha Única:", type="password")
        
        if st.button("Liberar Motores Quant", type="primary", use_container_width=True):
            # Aqui você pode colocar a sua senha real depois. Por enquanto, aceita qualquer texto para testar.
            if email and senha: 
                st.session_state['autenticado'] = True
                st.rerun()
            else:
                st.error("Preencha as credenciais para acessar a mesa de operações.")
    st.stop()

# ==========================================
# 3. PAINEL CENTRAL (DASHBOARD)
# ==========================================
# Botão de Logout no menu lateral
with st.sidebar:
    st.divider()
    if st.button("Desconectar 🔴", use_container_width=True):
        st.session_state['autenticado'] = False
        st.rerun()

st.title("🎯 Centro de Comando Quantitativo")
st.markdown(f"**Data da Mesa:** {datetime.now().strftime('%d/%m/%Y')} | **Status do Motor:** ONLINE 🟢")
st.divider()

# --- MÉTRICAS GERAIS DA CONTA ---
st.subheader("📊 Visão Geral do Capital")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Capital Alocado", "R$ 45.000,00", "")
m2.metric("Operações Abertas", "4", "")
m3.metric("Risco Exposto", "R$ 900,00", "2.0%")
m4.metric("Resultado Flutuante", "R$ +342,10", "+0.76%")

st.divider()

# --- CONSOLIDADOR DE OPORTUNIDADES E OPERAÇÕES ---
col_esq, col_dir = st.columns(2)

with col_esq:
    st.subheader("🚀 Oportunidades Hoje (Todos os Setups)")
    st.markdown("Sinais armados aguardando gatilho no pregão de hoje.")
    
    # Exemplo de dados (Abaixo vamos conversar sobre como puxar isso de verdade)
    dados_oportunidades = pd.DataFrame([
        {'Ativo': 'PRIO3', 'Estratégia': 'Fibo (61.8%)', 'Gatilho': 'R$ 45.10', 'Alvo': 'R$ 48.00'},
        {'Ativo': 'PETR4', 'Estratégia': 'Harami', 'Gatilho': 'R$ 38.50', 'Alvo': 'R$ 40.00'},
        {'Ativo': 'NVDC34', 'Estratégia': 'Vol. Institucional', 'Gatilho': 'A Mercado', 'Alvo': 'R$ 25.00'}
    ])
    st.dataframe(dados_oportunidades, use_container_width=True, hide_index=True)

with col_dir:
    st.subheader("⏳ Posições Abertas (Carteira)")
    st.markdown("Operações em andamento buscando alvo matemático.")
    
    # Exemplo de dados
    dados_posicoes = pd.DataFrame([
        {'Ativo': 'VALE3', 'Estratégia': 'IFR', 'Dias': 4, 'PM': 'R$ 60.00', 'Atual': 'R$ 61.20', 'Lucro': '+2.00%'},
        {'Ativo': 'MGLU3', 'Estratégia': 'Keltner', 'Dias': 12, 'PM': 'R$ 1.50', 'Atual': 'R$ 1.45', 'Lucro': '-3.33%'}
    ])
    
    def colorir_lucro_home(row):
        val = float(row['Lucro'].replace('%', '').replace('+', ''))
        cor = 'lightgreen' if val > 0 else 'lightcoral' if val < 0 else 'white'
        return [f'color: {cor}'] * len(row)

    st.dataframe(dados_posicoes.style.apply(colorir_lucro_home, axis=1), use_container_width=True, hide_index=True)

st.divider()
st.info("👈 Selecione uma estratégia no menu lateral para iniciar varreduras completas ou backtests individuais.")
