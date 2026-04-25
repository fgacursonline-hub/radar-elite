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
# ABA 1: RADAR GLOBAL
# ==========================================
with aba_radar:
    with st.container(border=True):
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        with col_f1:
            lista_sel = st.selectbox("Lista:", ["BDRs Elite", "IBrX Seleção", "Todos"], key="f_lst_g")
            cap_g = st.number_input("Capital/Trade:", value=10000.0, key="f_cap_g")
        with col_f2:
            tempo_g = st.selectbox("Tempo Gráfico:", ['1d', '1wk'], index=0, format_func=lambda x: {'1d': 'Diário', '1wk': 'Semanal'}[x], key="f_tmp_g")
            periodo_busca_g = st.selectbox("Histórico:", ['1y', '2y', '5y', 'max'], index=1, format_func=lambda x: tradutor_periodo_nome[x], key="f_per_g")
        with col_f3:
            usar_mm_g = st.toggle("Filtro MM21", value=True, key="f_mm_g")
            usar_chao_g = st.toggle("Stop Fura-Chão", value=True, key="f_chao_g")
        with col_f4:
            usar_alvo_g = st.toggle("Alvo Fixo (%)", value=False, key="f_alvo_tg_g")
            alvo_g = st.number_input("Alvo %:", value=10.0, disabled=not usar_alvo_g, key="f_alvo_val_g")

    if st.button("🚀 Iniciar Varredura Global", type="primary", use_container_width=True):
        ativos = bdrs_elite if lista_sel == "BDRs Elite" else ibrx_selecao if lista_sel == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        intervalo = tradutor_intervalo.get(tempo_g, Interval.in_daily)
        
        oportunidades = []
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

                row = df.iloc[-1]; row_ant = df.iloc[-2]
                if row['High'] > row['Fura_Teto'] and (not usar_mm_g or row_ant['Close'] > row_ant['MM21']):
                    oportunidades.append({"Ativo": ativo, "Preço": row['Close'], "Teto": row['Fura_Teto']})
            except: pass
        
        p_bar.empty(); s_text.empty()
        st.subheader("🎯 Oportunidades de Compra Agora")
        if oportunidades: st.dataframe(pd.DataFrame(oportunidades), use_container_width=True, hide_index=True)
        else: st.info("Sem sinais no momento.")

# ==========================================
# ABA 2: RAIO-X INDIVIDUAL
# ==========================================
with aba_individual:
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            ativo_rx = st.selectbox("Ativo:", ativos_para_rastrear, key="rx_ativo_i")
            usar_mm_rx = st.toggle("📈 Filtro MM21", value=True, key="rx_mm_i")
        with c2:
            periodo_rx = st.selectbox("Período:", options=['1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=1, key="rx_per_i")
            cap_rx = st.number_input("Capital/Trade:", value=10000.0, key="rx_cap_i")
        with c3:
            tempo_rx = st.selectbox("Gráfico:", ['1d', '1wk'], format_func=lambda x: {'1d': 'Diário', '1wk': 'Semanal'}[x], index=0, key="rx_tmp_i")
            usar_chao_rx = st.toggle("📉 Stop Fura-Chão", value=True, key="rx_chao_i")
        with c4:
            usar_alvo_rx = st.toggle("🎯 Alvo Fixo", value=False, key="rx_alvo_tg_i")
            alvo_rx_val = st.number_input("Alvo %:", value=10.0, disabled=not usar_alvo_rx, key="rx_alvo_val_i")

    if st.button("🔍 Rodar Laboratório", type="primary", use_container_width=True, key="rx_btn_i"):
        intervalo_i = tradutor_intervalo.get(tempo_rx, Interval.in_daily)
        with st.spinner("Analisando..."):
            try:
                df_full = tv.get_hist(symbol=ativo_rx.replace('.SA',''), exchange='BMFBOVESPA', interval=intervalo_i, n_bars=5000)
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
                            bateu_al = usar_alvo_rx and (row['High'] >= em_pos['preco'] * (1 + (alvo_rx_val/100)))
                            if bateu_st or bateu_al:
                                p_sai = min(row['Open'], row['Fura_Chao']) if bateu_st else em_pos['preco'] * (1 + (alvo_rx_val/100))
                                lucro = cap_rx * ((p_sai / em_pos['preco']) - 1)
                                trades.append({
                                    'Entrada': em_pos['data'].strftime('%d/%m/%y'), 
                                    'Preço Ent.': f"R$ {em_pos['preco']:.2f}",
                                    'Saída': row['datetime'].strftime('%d/%m/%y'), 
                                    'Preço Saída': f"R$ {p_sai:.2f}",
                                    'Lucro R$': lucro
                                })
                                em_pos = None

                    if trades:
                        df_t = pd.DataFrame(trades)
                        vits = df_t[df_t['Lucro R$'] > 0]
                        derrs = df_t[df_t['Lucro R$'] <= 0]
                        tx = (len(vits)/len(df_t))*100
                        pf = vits['Lucro R$'].mean() / abs(derrs['Lucro R$'].mean()) if not derrs.empty else 0
                        
                        st.markdown(f"### 📊 Resumo: {ativo_rx}")
                        st.markdown(f"#### 💰 **Lucro:** R$ {df_t['Lucro R$'].sum():.2f} &nbsp;&nbsp;|&nbsp;&nbsp; 🎯 **Acerto:** {tx:.1f}% &nbsp;&nbsp;|&nbsp;&nbsp; ⚖️ **Payoff:** {pf:.2f} &nbsp;&nbsp;|&nbsp;&nbsp; 🔄 **Trades:** {len(df_t)}")
                        
                        # Formatando o DataFrame para exibir cores
                        df_show = df_t.copy()
                        df_show['Lucro R$'] = df_show['Lucro R$'].apply(lambda x: f"R$ {x:.2f}")
                        
                        def colorir_linha(row):
                            val = str(row['Lucro R$'])
                            if '-' not in val and '0.00' not in val:
                                return ['color: #2eeb5c; font-weight: bold'] * len(row)
                            elif '-' in val:
                                return ['color: #ff4d4d'] * len(row)
                            return [''] * len(row)

                        st.dataframe(df_show.style.apply(colorir_linha, axis=1), use_container_width=True, hide_index=True)
                        renderizar_grafico_tv(f"BMFBOVESPA:{ativo_rx}")
                    else: st.warning("Nenhuma operação concluída neste período com essas configurações.")
            except Exception as e: st.error(f"Erro: {e}")
