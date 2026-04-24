import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# Tenta importar os ativos do seu arquivo de configuração
try:
    from config_ativos import lista_unificada as ativos_para_rastrear
except ImportError:
    # Fallback caso o arquivo não seja encontrado no mesmo diretório
    st.warning("⚠️ Arquivo 'config_ativos.py' não encontrado. Usando lista padrão IBrX/BDRs.")
    ativos_para_rastrear = ['PETR4', 'VALE3', 'ITUB4', 'BBDC4', 'BBAS3', 'MGLU3', 'WEGE3', 'NVDC34', 'AAPL34']

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Radar TPV Elite", layout="wide", page_icon="🎯")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, inicie sessão na página inicial.")
    st.stop()

st.title("🎯 Radar de Agressão TPV (Módulo 6)")
st.markdown("Rastreamento automático de cruzamento do TPV com a Média Móvel de 55 períodos e detecção de divergências.")

# ==========================================
# 2. MOTOR DO RASTREADOR (TPV + MA55)
# ==========================================
def rastrear_sinais_tpv(lista_ativos):
    sinais_encontrados = []
    
    # Barra de progresso para o usuário não ficar no escuro
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, ativo in enumerate(lista_ativos):
        ticker = f"{ativo}.SA" if not ativo.endswith(".SA") else ativo
        status_text.text(f"Analisando fluxo de: {ativo} ({i+1}/{len(lista_ativos)})")
        progress_bar.progress((i + 1) / len(lista_ativos))
        
        try:
            # Puxa 6 meses para garantir que a Média de 55 dias seja calculada corretamente
            df = yf.download(ticker, period="6mo", interval="1d", progress=False)
            
            if df.empty or len(df) < 60:
                continue
                
            # Limpeza do Multi-Index (Padrão de blindagem do YFinance)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # --- MATEMÁTICA DO SLIDE ---
            # 1. Cálculo do TPV (Variação % x Volume) Acumulado
            df['Retorno'] = df['Close'].pct_change()
            df['TPV'] = (df['Volume'] * df['Retorno']).cumsum()
            
            # 2. Média Móvel de 55 Períodos sobre o TPV
            df['TPV_MA55'] = df['TPV'].rolling(window=55).mean()
            
            # Removemos os NaNs gerados pela média móvel
            df.dropna(inplace=True)
            
            if len(df) < 2: continue

            # --- ANÁLISE DE GATILHO (CRUZAMENTO) ---
            tpv_ontem = df['TPV'].iloc[-2]
            ma55_ontem = df['TPV_MA55'].iloc[-2]
            tpv_hoje = df['TPV'].iloc[-1]
            ma55_hoje = df['TPV_MA55'].iloc[-1]
            
            # Condição de Agressão Compradora: Cruzou para CIMA
            cruzou_compra = (tpv_ontem <= ma55_ontem) and (tpv_hoje > ma55_hoje)
            
            # Condição de Agressão Vendedora: Cruzou para BAIXO
            cruzou_venda = (tpv_ontem >= ma55_ontem) and (tpv_hoje < ma55_hoje)
            
            # --- ANÁLISE DE DIVERGÊNCIA (CONFIRMAÇÃO) ---
            # Comparamos os últimos 5 dias para ver a direção da tendência
            tendencia_preco = df['Close'].iloc[-1] - df['Close'].iloc[-5]
            tendencia_tpv = df['TPV'].iloc[-1] - df['TPV'].iloc[-5]
            
            divergencia = "-"
            if tendencia_preco < 0 and tendencia_tpv > 0:
                divergencia = "🚀 ALTA (Preço Cai, TPV Sobe)"
            elif tendencia_preco > 0 and tendencia_tpv < 0:
                divergencia = "🩸 BAIXA (Preço Sobe, TPV Cai)"

            # Adiciona à lista se houver gatilho de entrada ou saída
            if cruzou_compra:
                sinais_encontrados.append({
                    "Ativo": ativo.replace(".SA", ""),
                    "Sinal": "🟢 COMPRA (Cruzou MA55 p/ Cima)",
                    "Preço Atual": f"R$ {df['Close'].iloc[-1]:.2f}",
                    "Divergência 5d": divergencia
                })
            elif cruzou_venda:
                sinais_encontrados.append({
                    "Ativo": ativo.replace(".SA", ""),
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
# 3. INTERFACE DE USUÁRIO
# ==========================================
st.divider()
col1, col2 = st.columns([3, 1], vertical_alignment="bottom")

with col1:
    st.info(f"O radar irá escanear **{len(ativos_para_rastrear)} ativos** buscando as regras exatas de agressão do TPV (Cruzamento da Média de 55).")

with col2:
    btn_rastrear = st.button("🚀 Iniciar Varredura TPV", type="primary", use_container_width=True)

if btn_rastrear:
    with st.spinner("Varrendo o mercado em busca de tubarões..."):
        df_resultados = rastrear_sinais_tpv(ativos_para_rastrear)
        
        if not df_resultados.empty:
            st.success(f"🎯 Foram encontrados {len(df_resultados)} ativos dando condição de entrada/saída hoje!")
            
            # Destaca a tabela com cores nativas do Pandas para facilitar a leitura
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
            * **Sinal de COMPRA + Traço (-):** Rompimento limpo. Significa "Concordância". O preço e o TPV estão subindo juntos. Gatilho clássico.
            * **Sinal de VENDA:** A agressão inverteu. É hora de proteger lucros (acionar stop gain) ou buscar operações de Short (Vendido).
            """)
        else:
            st.warning("Nenhum ativo cruzou a Média Móvel de 55 períodos do TPV no pregão de hoje. Mantenha as posições atuais.")
