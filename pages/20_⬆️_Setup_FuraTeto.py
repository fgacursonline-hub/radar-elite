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
from datetime import datetime

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

ativos_para_rastrear = sorted(list(set([a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)])))

# ==========================================
# 2. CONFIGURAÇÃO DA PÁGINA & TVDATAFEED
# ==========================================
st.set_page_config(page_title="Fura-Teto Elite", layout="wide", page_icon="⬆️")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

@st.cache_resource
def get_tv_connection():
    return TvDatafeed()

tv = get_tv_connection()

tradutor_periodo_nome = {
    '1mo': '1 Mês', '3mo': '3 Meses', '6mo': '6 Meses',
    '1y': '1 Ano', '2y': '2 Anos', '5y': '5 Anos',
    'max': 'Máximo', '60d': '60 Dias'
}

tradutor_intervalo = {
    '15m': Interval.in_15_minute,
    '60m': Interval.in_1_hour,
    '1d': Interval.in_daily,
    '1wk': Interval.in_weekly
}

st.title("⬆️ Máquina Quantitativa: Fura-Teto & Fura-Chão")

aba_radar, aba_individual = st.tabs(["🌐 Radar Global (Scanner)", "🔬 Raio-X Individual (Backtest)"])

# ==========================================
# 3. FUNÇÕES GLOBAIS
# ==========================================
def renderizar_grafico_tv(symbol):
    html_code = f"""
    <div class="tradingview-widget-container">
      <div id="tv_chart_{symbol.replace(':', '')}" style="height: 500px; width: 100%;"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{"autosize": true, "symbol": "{symbol}", "interval": "D", "theme": "dark", "style": "1", "locale": "br", "container_id": "tv_chart_{symbol.replace(':', '')}"}});
      </script>
    </div>
    """
    components.html(html_code, height=500)

def exibir_explicacao_estrategia():
    st.markdown("<small><b>Fura-Teto:</b> Compra no rompimento da máxima anterior. <b>Fura-Chão:</b> Venda/Stop na perda da mínima anterior.</small>", unsafe_allow_html=True)

# ==========================================
# ABA 1: RADAR GLOBAL (RESTAURADA)
# ==========================================
with aba_radar:
    with st.container(border=True):
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        with col_f1:
            lista_sel = st.selectbox("Lista:", ["BDRs Elite", "IBrX Seleção", "Todos"], key="f_lst")
            cap_g = st.number_input("Capital/Trade:", value=10000.0, key="f_cap")
        with col_f2:
            tempo_g = st.selectbox("Tempo Gráfico:", ['1d', '1wk'], index=0, key="f_tmp")
            periodo_busca_g = st.selectbox("Histórico:", ['1y', '2y', '5y', 'max'], index=1, key="f_per")
        with col_f3:
            usar_mm_g = st.toggle("Filtro MM21", value=True)
            usar_chao_g = st.toggle("Stop Fura-Chão", value=True)
        with col_f4:
            usar_alvo_g = st.toggle("Alvo Fixo (%)", value=False)
            alvo_g = st.number_input("Alvo %:", value=10.0, disabled=not usar_alvo_g)

    if st.button("🚀 Iniciar Varredura Global", type="primary", use_container_width=True):
        ativos = bdrs_elite if lista_sel == "BDRs Elite" else ibrx_selecao if lista_sel == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        intervalo = tradutor_intervalo.get(tempo_g, Interval.in_daily)
        
        oportunidades, historico = [], []
        p_bar = st.progress(0); s_text = st.empty()
        
        for i, ativo_raw in enumerate(ativos):
            ativo = ativo_raw.replace('.SA','')
            s_text.text(f"Varrendo: {ativo}")
            p_bar.progress((i+1)/len(ativos))
            try:
                df = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo, n_bars=3000)
                if df is None: continue
                df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                df['Fura_Teto'] = df['High'].shift(1)
                df['Fura_Chao'] = df['Low'].shift(1)
                df['MM21'] = ta.sma(df['Close'], length=21)
                df = df.dropna()

                # Verifica sinal de hoje
                row = df.iloc[-1]; row_ant = df.iloc[-2]
                if row['High'] > row['Fura_Teto'] and (not usar_mm_g or row_ant['Close'] > row_ant['MM21']):
                    oportunidades.append({"Ativo": ativo, "Preço": row['Close'], "Teto": row['Fura_Teto']})
                
                historico.append({"Ativo": ativo, "Sinais": len(df[df['High'] > df['Fura_Teto']])})
            except: pass
        
        st.subheader("🎯 Oportunidades de Compra Agora")
        if oportunidades: st.dataframe(pd.DataFrame(oportunidades), use_container_width=True, hide_index=True)
        else: st.info("Sem sinais no momento.")

# ==========================================
# ABA 2: RAIO-X INDIVIDUAL (FONTE PEQUENA)
# ==========================================
with aba_individual:
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            ativo_rx = st.selectbox("Ativo:", ativos_para_rastrear, key="rx_ativo")
            usar_mm_rx = st.toggle("📈 Filtro MM21", value=True)
        with c2:
            periodo_rx = st.selectbox("Período:", options=['1y', '2y', '5y', 'max'], index=1)
            cap_rx = st.number_input("Capital/Trade:", value=10000.0)
        with c3:
            tempo_rx = st.selectbox("Gráfico:", ['1d', '1wk'], index=0)
            usar_chao_rx = st.toggle("📉 Stop Fura-Chão", value=True, key="rx_chao")
        with c4:
            usar_alvo_rx = st.toggle("🎯 Alvo Fixo", value=False, key="rx_alvo_tg")
            alvo_rx = st.number_input("Alvo %:", value=10.0, disabled=not usar_alvo_rx)

    if st.button("🔍 Rodar Laboratório", type="primary", use_container_width=True):
        intervalo = tradutor_intervalo.get(tempo_rx, Interval.in_daily)
        with st.spinner("Analisando..."):
            df_full = tv.get_hist(symbol=ativo_rx.replace('.SA',''), exchange='BMFBOVESPA', interval=intervalo, n_bars=5000)
            if df_full is not None:
                df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                df_full['Fura_Teto'] = df_full['High'].shift(1)
                df_full['Fura_Chao'] = df_full['Low'].shift(1)
                df_full['MM21'] = ta.sma(df_full['Close'], length=21)
                
                delta = {'1y': 1, '2y': 2, '5y': 5}.get(periodo_rx, 10)
                data_corte = df_full.index[-1] - pd.DateOffset(years=delta) if periodo_rx != 'max' else df_full.index[0]
                df = df_full[df_full.index >= data_corte].copy().reset_index()
                
                trades, em_pos = [], None
                for i in range(1, len(df)):
                    row = df.iloc[i]; row_ant = df.iloc[i-1]
                    if em_pos is None:
                        if row['High'] > row['Fura_Teto'] and (not usar_mm_rx or row_ant['Close'] > row_ant['MM21']):
                            p_ent = max(row['Open'], row['Fura_Teto'])
                            em_pos = {'data': row['datetime'], 'preco': p_ent}
                    else:
                        bateu_st = usar_chao_rx and (row['Low'] < row['Fura_Chao'])
                        bateu_al = usar_alvo_rx and (row['High'] >= em_pos['preco'] * (1 + (alvo_rx/100)))
                        if bateu_st or bateu_al:
                            p_sai = min(row['Open'], row['Fura_Chao']) if bateu_st else em_pos['preco'] * (1 + (alvo_rx/100))
                            lucro = cap_rx * ((p_sai / em_pos['preco']) - 1)
                            trades.append({'Entrada': em_pos['data'].strftime('%d/%m/%y'), 'Saída': row['datetime'].strftime('%d/%m/%y'), 'Lucro': lucro})
                            em_pos = None

                if trades:
                    df_t = pd.DataFrame(trades)
                    vits = df_t[df_t['Lucro'] > 0]
                    derrs = df_t[df_t['Lucro'] <= 0]
                    tx = (len(vits)/len(df_t))*100
                    pf = vits['Lucro'].mean() / abs(derrs['Lucro'].mean()) if not derrs.empty else 0
                    
                    # --- RESULTADO EM FONTE PEQUENA ---
                    st.markdown(f"### 📊 Resumo: {ativo_rx}")
                    st.markdown(f"**Lucro:** R$ {df_t['Lucro'].sum():.2f} | **Acerto:** {tx:.1f}% | **Payoff:** {pf:.2f} | **Trades:** {len(df_t)}")
                    
                    st.dataframe(df_t, use_container_width=True, height=250)
                    renderizar_grafico_tv(f"BMFBOVESPA:{ativo_rx}")
