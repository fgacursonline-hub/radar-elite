import streamlit as st
from tvDatafeed import TvDatafeed, Interval
import streamlit.components.v1 as components
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
import warnings
import sys
import os

warnings.filterwarnings('ignore')

# --- IMPORTAÇÃO CENTRALIZADA DOS ATIVOS ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from config_ativos import bdrs_elite, ibrx_selecao
except ImportError:
    st.error("❌ Arquivo 'config_ativos.py' não encontrado na raiz do projeto.")
    st.stop()

# 1. SEGURANÇA
if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

# 2. CONEXÃO
@st.cache_resource
def get_tv_connection():
    return TvDatafeed()

tv = get_tv_connection()

tradutor_periodo_nome = {'1y': '1 Ano', '2y': '2 Anos', '5y': '5 Anos', 'max': 'Máximo'}
tradutor_intervalo = {'1d': Interval.in_daily, '1wk': Interval.in_weekly}

st.title("🔘 Máquina Quantitativa: Bandas de Bollinger")
st.markdown("Opere a volatilidade: Tendência (Walking up) ou Reversão (FFFD).")

aba_radar, aba_individual = st.tabs(["🌐 Radar Global (Scanner)", "🔬 Raio-X Individual"])

# ==========================================
# 3. MOTOR MATEMÁTICO (BOLLINGER)
# ==========================================
def calcular_bollinger(df, periodo=20, desvio=2.0, estrategia="Andando nas Bandas (Tendência)"):
    if df.empty or len(df) < periodo: return pd.DataFrame()
    
    # Cálculo das Bandas
    bb = ta.bbands(df['Close'], length=periodo, std=desvio)
    df['BB_Upper'] = bb[f'BBU_{periodo}_{desvio}']
    df['BB_Mid'] = bb[f'BBM_{periodo}_{desvio}']
    df['BB_Lower'] = bb[f'BBL_{periodo}_{desvio}']
    
    df['Cruzou_Compra'] = False
    df['Cruzou_Venda'] = False
    
    if "Andando nas Bandas" in estrategia:
        # Compra: Fechou acima da banda superior
        df['Cruzou_Compra'] = (df['Close'] > df['BB_Upper']) & (df['Close'].shift(1) <= df['BB_Upper'].shift(1))
        # Venda: Fechou abaixo da banda inferior (ou da média 20, dependendo do conservadorismo)
        df['Cruzou_Venda'] = (df['Close'] < df['BB_Lower'])
        
    elif "Fechou Fora / Fechou Dentro" in estrategia:
        # Lógica FFFD (Reversão na Banda Inferior)
        # 1. Candle anterior fechou fora (abaixo)
        fechou_fora = df['Close'].shift(1) < df['BB_Lower'].shift(1)
        # 2. Candle atual fechou dentro
        fechou_dentro = df['Close'] > df['BB_Lower']
        # 3. Gatilho: Rompeu a máxima do candle que voltou (Aqui simplificado para o fechamento atual)
        df['Cruzou_Compra'] = fechou_fora & fechou_dentro
        # Venda: Tocou na banda oposta ou média
        df['Cruzou_Venda'] = (df['Close'] >= df['BB_Upper']) | (df['Close'] >= df['BB_Mid'])
        
    return df.dropna()

def renderizar_grafico_tv(symbol):
    html_code = f"""
    <div class="tradingview-widget-container">
      <div id="tv_chart_{symbol.replace(':', '')}" style="height: 600px; width: 100%;"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
      "autosize": true, "symbol": "{symbol}", "interval": "D", "timezone": "America/Sao_Paulo",
      "theme": "dark", "style": "1", "locale": "br", "container_id": "tv_chart_{symbol.replace(':', '')}"
      }});
      </script>
    </div>
    """
    components.html(html_code, height=600)

def explicar_bollinger(est):
    if "Andando" in est:
        st.info("🌊 **Andando nas Bandas (Tendência):** Compra quando o preço fecha ACIMA da banda superior. Indica força e momentum. Saída quando o preço perde a banda inferior.")
    else:
        st.info("🪃 **FFFD (Reversão):** Compra quando o preço fecha abaixo da banda inferior e o candle seguinte volta para DENTRO da banda. Busca o repique até a média ou banda oposta.")

# ==========================================
# ABA 1: RADAR GLOBAL
# ==========================================
with aba_radar:
    with st.container(border=True):
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            lista_sel = st.selectbox("Lista:", ["BDRs Elite", "IBrX Seleção", "Todos"])
            estrategia_g = st.selectbox("Estratégia:", ["Andando nas Bandas (Tendência)", "Fechou Fora / Fechou Dentro (Reversão)"])
        with col_f2:
            tempo_g = st.selectbox("Tempo:", ["1d", "1wk"], key="tmp_g")
            periodo_busca = st.selectbox("Histórico:", ["1y", "2y", "5y", "max"], index=1)
        with col_f3:
            cap_g = st.number_input("Capital/Trade:", value=10000.0)
            desvio_g = st.number_input("Desvios Padrão:", value=2.0, step=0.1)
            
    explicar_bollinger(estrategia_g)
    
    if st.button("🚀 Varredura de Volatilidade"):
        ativos = bdrs_elite if lista_sel == "BDRs Elite" else ibrx_selecao if lista_sel == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        intervalo = tradutor_intervalo[tempo_g]
        
        oportunidades, historico = [], []
        p_bar = st.progress(0); s_text = st.empty()
        
        for i, ativo_raw in enumerate(ativos):
            ativo = ativo_raw.replace('.SA', '')
            s_text.text(f"Analisando Bandas: {ativo}")
            p_bar.progress((i+1)/len(ativos))
            try:
                df_full = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo, n_bars=3000)
                if df_full is None: continue
                df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                df_full = calcular_bollinger(df_full, desvio=desvio_g, estrategia=estrategia_g)
                
                # Sinais de hoje
                if df_full['Cruzou_Compra'].iloc[-1]:
                    oportunidades.append({"Ativo": ativo, "Preço": df_full['Close'].iloc[-1], "Banda Superior": df_full['BB_Upper'].iloc[-1]})
                
                # Estatística simples (Backtest rápido)
                vitorias = df_full[df_full['Cruzou_Compra']].shape[0] # Exemplo simplificado
                historico.append({"Ativo": ativo, "Sinais no Período": vitorias})
            except: pass
        
        st.subheader("🎯 Oportunidades Identificadas")
        if oportunidades: st.dataframe(pd.DataFrame(oportunidades), use_container_width=True)
        else: st.info("Nenhum sinal no fechamento atual.")
        
        st.subheader("📊 Ranking de Frequência (Top 20)")
        st.dataframe(pd.DataFrame(historico).sort_values(by="Sinais no Período", ascending=False).head(20), use_container_width=True)

# ==========================================
# ABA 2: RAIO-X INDIVIDUAL
# ==========================================
with aba_individual:
    c1, c2 = st.columns(2)
    with c1: 
        ativo_rx = st.selectbox("Ativo:", ativos_para_rastrear)
        est_rx = st.selectbox("Estratégia:", ["Andando nas Bandas (Tendência)", "Fechou Fora / Fechou Dentro (Reversão)"], key="est_rx")
    with c2:
        periodo_rx = st.selectbox("Período:", ["1y", "2y", "5y", "max"], index=1, key="p_rx")
        
    if st.button("🔍 Analisar Ativo"):
        with st.spinner("Buscando dados..."):
            df_rx = tv.get_hist(symbol=ativo_rx.replace('.SA', ''), exchange='BMFBOVESPA', interval=Interval.in_daily, n_bars=3000)
            if df_rx is not None:
                df_rx.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                df_rx = calcular_bollinger(df_rx, estrategia=est_rx)
                
                st.markdown(f"### 📈 Gráfico Interativo: {ativo_rx}")
                renderizar_grafico_tv(f"BMFBOVESPA:{ativo_rx}")
                st.info("💡 No gráfico, adicione o indicador 'Bollinger Bands' para conferir os sinais.")
