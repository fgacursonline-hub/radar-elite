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
      <div id="tv_chart_{symbol.replace(':', '')}" style="height: 600px; width: 100%;"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{"autosize": true, "symbol": "{symbol}", "interval": "D", "theme": "dark", "style": "1", "locale": "br", "container_id": "tv_chart_{symbol.replace(':', '')}"}});
      </script>
    </div>
    """
    components.html(html_code, height=600)

# ==========================================
# ABA 1: RADAR GLOBAL (Omitida para brevidade, manter original)
# ==========================================
# ... (Mantenha o código da aba_radar que já funciona)

# ==========================================
# ABA 2: RAIO-X INDIVIDUAL (COM PAYOFF E TAXA)
# ==========================================
with aba_individual:
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            ativo_rx = st.selectbox("Ativo:", ativos_para_rastrear, key="rx_ativo")
            usar_mm_rx = st.toggle("📈 Filtro Tendência (> MM21)", value=True)
        with c2:
            periodo_rx = st.selectbox("Período:", options=['1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=1)
            cap_rx = st.number_input("Capital/Trade:", value=10000.0)
        with c3:
            tempo_rx = st.selectbox("Tempo Gráfico:", ['1d', '1wk'], index=0)
            usar_chao_rx = st.toggle("📉 Stop Fura-Chão", value=True)
        with c4:
            usar_alvo_rx = st.toggle("🎯 Alvo Fixo", value=False)
            alvo_rx = st.number_input("Alvo (%):", value=10.0, disabled=not usar_alvo_rx)

    if st.button("🔍 Rodar Laboratório Fura-Teto", type="primary", use_container_width=True):
        intervalo = tradutor_intervalo.get(tempo_rx, Interval.in_daily)
        with st.spinner("Dissecando histórico..."):
            try:
                df_full = tv.get_hist(symbol=ativo_rx.replace('.SA',''), exchange='BMFBOVESPA', interval=intervalo, n_bars=5000)
                if df_full is not None:
                    df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                    df_full['Fura_Teto'] = df_full['High'].shift(1)
                    df_full['Fura_Chao'] = df_full['Low'].shift(1)
                    df_full['MM21'] = ta.sma(df_full['Close'], length=21)
                    df_full = df_full.dropna()

                    # Corte temporal
                    delta = {'1y': 1, '2y': 2, '5y': 5}.get(periodo_rx, 10)
                    data_corte = df_full.index[-1] - pd.DateOffset(years=delta) if periodo_rx != 'max' else df_full.index[0]
                    df = df_full[df_full.index >= data_corte].copy().reset_index()
                    
                    trades, em_pos = [], None
                    for i in range(1, len(df)):
                        row = df.iloc[i]; row_ant = df.iloc[i-1]
                        if em_pos is None:
                            if row['High'] > row['Fura_Teto'] and (not usar_mm_rx or row_ant['Close'] > row_ant['MM21']):
                                p_ent = max(row['Open'], row['Fura_Teto'])
                                em_pos = {'data': row['datetime'], 'preco': p_ent, 'pico': row['Close']}
                        else:
                            if row['High'] > em_pos['pico']: em_pos['pico'] = row['High']
                            bateu_st = usar_chao_rx and (row['Low'] < row['Fura_Chao'])
                            bateu_al = usar_alvo_rx and (row['High'] >= em_pos['preco'] * (1 + (alvo_rx/100)))
                            
                            if bateu_st or bateu_al:
                                p_sai = min(row['Open'], row['Fura_Chao']) if bateu_st else em_pos['preco'] * (1 + (alvo_rx/100))
                                luc_rs = cap_rx * ((p_sai / em_pos['preco']) - 1)
                                trades.append({'Entrada': em_pos['data'], 'Saída': row['datetime'], 'Lucro': luc_rs, 'DD': ((row['Low']/em_pos['preco'])-1)*100})
                                em_pos = None

                    if trades:
                        df_t = pd.DataFrame(trades)
                        # --- CÁLCULO DAS MÉTRICAS DE ELITE ---
                        vitorias = df_t[df_t['Lucro'] > 0]
                        derrotas = df_t[df_t['Lucro'] <= 0]
                        tx_acerto = (len(vitorias) / len(df_t)) * 100
                        
                        media_ganho = vitorias['Lucro'].mean() if not vitorias.empty else 0
                        media_perda = abs(derrotas['Lucro'].mean()) if not derrotas.empty else 1
                        payoff = media_ganho / media_perda
                        
                        st.markdown(f"### 📊 Resultado Consolidado: {ativo_rx}")
                        m1, m2, m3, m4, m5 = st.columns(5)
                        m1.metric("Lucro Total", f"R$ {df_t['Lucro'].sum():.2f}")
                        m2.metric("Taxa de Acerto", f"{tx_acerto:.1f}%")
                        m3.metric("Payoff", f"{payoff:.2f}")
                        m4.metric("Trades", len(df_t))
                        m5.metric("Pior Queda", f"{df_t['DD'].min():.2f}%")
                        
                        if payoff < 1 and tx_acerto < 60:
                            st.error(f"🚨 **Alerta:** Este ativo tem Payoff de {payoff:.2f}. A conta não fecha no longo prazo nesta configuração!")
                        elif payoff > 1.5:
                            st.success(f"🎯 **Elite:** Payoff excelente ({payoff:.2f}). Você ganha muito mais do que perde!")

                        st.dataframe(df_t, use_container_width=True)
                        renderizar_grafico_tv(f"BMFBOVESPA:{ativo_rx}")
                    else:
                        st.warning("Nenhuma operação concluída.")
            except Exception as e: st.error(f"Erro: {e}")
