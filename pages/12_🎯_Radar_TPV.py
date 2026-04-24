import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import warnings
import sys
import os

warnings.filterwarnings('ignore')

# ==========================================
# 1. IMPORTAÇÃO CENTRALIZADA DOS ATIVOS
# ==========================================
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from config_ativos import bdrs_elite, ibrx_selecao
except ImportError:
    st.error("❌ Arquivo 'config_ativos.py' não encontrado na raiz do projeto.")
    st.stop()

# Unificando a lista e removendo os sufixos para padronização no loop
ativos_para_rastrear = sorted(list(set([a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)])))

# ==========================================
# 2. CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Radar TPV Elite", layout="wide", page_icon="🎯")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

st.title("🎯 Radar de Agressão TPV (Módulo 6)")
st.markdown("Rastreamento automático de cruzamento do TPV com a Média Móvel de 55 períodos e detecção de divergências.")

# ==========================================
# 3. MOTOR DO RASTREADOR (TPV + MA55)
# ==========================================
def rastrear_sinais_tpv(lista_ativos):
    sinais_encontrados = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, ativo in enumerate(lista_ativos):
        # Readicionando o sufixo .SA para o Yahoo Finance
        ticker = f"{ativo}.SA"
        status_text.text(f"Analisando fluxo de: {ativo} ({i+1}/{len(lista_ativos)})")
        progress_bar.progress((i + 1) / len(lista_ativos))
        
        try:
            df = yf.download(ticker, period="6mo", interval="1d", progress=False)
            
            if df.empty or len(df) < 60:
                continue
                
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # --- MATEMÁTICA DO TPV ---
            df['Retorno'] = df['Close'].pct_change()
            df['TPV'] = (df['Volume'] * df['Retorno']).cumsum()
            df['TPV_MA55'] = df['TPV'].rolling(window=55).mean()
            
            df.dropna(inplace=True)
            if len(df) < 2: continue

            # --- GATILHO: CRUZAMENTO DE ONTEM PARA HOJE ---
            tpv_ontem = df['TPV'].iloc[-2]
            ma55_ontem = df['TPV_MA55'].iloc[-2]
            tpv_hoje = df['TPV'].iloc[-1]
            ma55_hoje = df['TPV_MA55'].iloc[-1]
            
            cruzou_compra = (tpv_ontem <= ma55_ontem) and (tpv_hoje > ma55_hoje)
            cruzou_venda = (tpv_ontem >= ma55_ontem) and (tpv_hoje < ma55_hoje)
            
            # --- CONFIRMAÇÃO: DIVERGÊNCIA DE 5 DIAS ---
            tendencia_preco = df['Close'].iloc[-1] - df['Close'].iloc[-5]
            tendencia_tpv = df['TPV'].iloc[-1] - df['TPV'].iloc[-5]
            
            divergencia = "-"
            if tendencia_preco < 0 and tendencia_tpv > 0:
                divergencia = "🚀 ALTA (Preço Cai, TPV Sobe)"
            elif tendencia_preco > 0 and tendencia_tpv < 0:
                divergencia = "🩸 BAIXA (Preço Sobe, TPV Cai)"

            if cruzou_compra:
                sinais_encontrados.append({
                    "Ativo": ativo,
                    "Sinal": "🟢 COMPRA (Cruzou MA55 p/ Cima)",
                    "Preço Atual": f"R$ {df['Close'].iloc[-1]:.2f}",
                    "Divergência 5d": divergencia
                })
            elif cruzou_venda:
                sinais_encontrados.append({
                    "Ativo": ativo,
                    "Sinal": "🔴 VENDA (Cruzou MA55 p/ Baixo)",
                    "Preço Atual": f"R$ {df['Close'].iloc[-1]:.2f}",
                    "Divergência 5d": divergencia
                })
                
        except Exception as e:
            continue
            
    progress_bar.empty()
    status_text.empty()
    return pd.DataFrame(sinais_encontrados)

# ==========================================
# 4. INTERFACE DE USUÁRIO
# ==========================================
st.divider()
col1, col2 = st.columns([3, 1], vertical_alignment="bottom")

with col1:
    st.info(f"O radar irá escanear **{len(ativos_para_rastrear)} ativos** do seu arquivo de configuração buscando o cruzamento do TPV com a Média Móvel de 55 períodos.")

with col2:
    btn_rastrear = st.button("🚀 Iniciar Varredura TPV", type="primary", use_container_width=True)

if btn_rastrear:
    with st.spinner("Varrendo o mercado em busca de fluxo institucional..."):
        df_resultados = rastrear_sinais_tpv(ativos_para_rastrear)
        
        if not df_resultados.empty:
            st.success(f"🎯 Foram encontrados {len(df_resultados)} ativos dando condição de entrada/saída hoje!")
            
            def colorir_sinal(val):
                color = '#00FFCC' if 'COMPRA' in str(val) else '#FF4D4D' if 'VENDA' in str(val) else 'white'
                return f'color: {color}; font-weight: bold'
            
            st.dataframe(
                df_resultados.style.map(colorir_sinal, subset=['Sinal']),
                use_container_width=True, 
                hide_index=True
            )
            
            st.markdown("---")
            st.markdown("### 🧠 Tática de Combate (Como operar a tabela)")
            st.markdown("""
            * **Sinal de COMPRA + Divergência de ALTA:** É o setup diamante. O TPV rompeu a média e o volume já vinha acumulando enquanto o preço caía. Mão cheia.
            * **Sinal de COMPRA + Traço (-):** Rompimento limpo (Concordância). O preço e o TPV estão subindo juntos.
            * **Sinal de VENDA:** A agressão inverteu. É hora de proteger lucros ou buscar operações de Short.
            """)
        else:
            st.warning("Nenhum ativo cruzou a Média Móvel de 55 períodos do TPV no pregão de hoje. Mantenha as posições atuais.")
