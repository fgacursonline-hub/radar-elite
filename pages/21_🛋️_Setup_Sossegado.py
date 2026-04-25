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
st.set_page_config(page_title="Sossegado Elite", layout="wide", page_icon="🛋️")

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

st.title("🛋️ Máquina Quantitativa: Setup Sossegado (HiLo + WMA)")

aba_radar, aba_individual = st.tabs(["🌐 Radar Global (Scanner)", "🔬 Raio-X Individual (Backtest)"])

# ==========================================
# 3. MOTOR MATEMÁTICO (SOSSEGADO)
# ==========================================
def calcular_sossegado(df, hilo_len=8, wma_len=12, atr_len=10, filtro_atr=True):
    if df.empty or len(df) < max(hilo_len, wma_len, atr_len) + 5: return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = df.index.tz_localize(None)
    
    # 1. Bússola Direcional: Média Móvel Ponderada (WMA)
    df['WMA'] = ta.wma(df['Close'], length=wma_len)
    
    # 2. O Gatilho e Condução: HiLo Activator (Escadinha)
    hilo = ta.hilo(df['High'], df['Low'], df['Close'], length=hilo_len)
    if hilo is None or hilo.empty: return pd.DataFrame()
    
    col_hilo = [c for c in hilo.columns if c.startswith('HILO_')][0]
    col_hilo_long = [c for c in hilo.columns if c.startswith('HILOl_')][0] # Escadinha verde (tendência de alta)
    
    df['HiLo'] = hilo[col_hilo]
    # Se a coluna 'long' não for NaN, a escadinha está embaixo do preço (Tendência de Alta)
    df['Tendencia_Alta'] = ~hilo[col_hilo_long].isna()
    
    # 3. Combustível de Ignição: ATR (Volatilidade)
    df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=atr_len)
    df['ATR_Subindo'] = df['ATR'] > df['ATR'].shift(1)
    
    # Lógica de Compra:
    # A) Escadinha virou para verde (Tendência Alta acabou de nascer)
    virou_alta = df['Tendencia_Alta'] & (~df['Tendencia_Alta'].shift(1).fillna(False))
    # B) Fechamento tem que estar acima da WMA12
    acima_wma = df['Close'] > df['WMA']
    
    condicao_compra = virou_alta & acima_wma
    if filtro_atr:
        condicao_compra = condicao_compra & df['ATR_Subindo']
        
    df['Cruzou_Compra'] = condicao_compra
    
    # Lógica de Saída (Fim do Sossego): Escadinha virou para vermelha
    df['Cruzou_Venda'] = (~df['Tendencia_Alta']) & (df['Tendencia_Alta'].shift(1).fillna(False))
    
    return df.dropna()

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
    st.info("🛋️ **A Estratégia (Setup Sossegado):** Entrar em rompimentos com força e conduzir sem ansiedade. \n\n🟢 **Compra:** A escadinha do HiLo (padrão **8**) vira para baixo do preço confirmando a tendência + O preço fecha acima da Média Ponderada (WMA **12**) + A volatilidade (ATR **10**) está acelerando.\n\n🔴 **Saída / Condução:** Esqueça alvos fixos. Apenas suba o seu Stop Loss diário acompanhando a escadinha do HiLo Activator. O trade acaba automaticamente no dia em que o preço furar a escadinha para baixo.")

# ==========================================
# ABA 1: RADAR GLOBAL (SCANNER)
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
            hilo_len_g = st.number_input("HiLo Activator (Original 8):", value=8, step=1)
            wma_len_g = st.number_input("Média Ponderada WMA:", value=12, step=1)
        with col_f4:
            usar_atr_g = st.toggle("📈 Exigir ATR Subindo (Força)", value=True)
            atr_len_g = st.number_input("Período ATR:", value=10, step=1, disabled=not usar_atr_g)

    exibir_explicacao_estrategia()

    if st.button("🚀 Iniciar Varredura do Sossegado", type="primary", use_container_width=True):
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
                df = calcular_sossegado(df, hilo_len=hilo_len_g, wma_len=wma_len_g, atr_len=atr_len_g, filtro_atr=usar_atr_g)

                # Verifica sinal de hoje
                if not df.empty and df['Cruzou_Compra'].iloc[-1]:
                    oportunidades.append({"Ativo": ativo, "Preço": df['Close'].iloc[-1], "Stop (HiLo)": df['HiLo'].iloc[-1]})
            except: pass
        
        p_bar.empty(); s_text.empty()
        st.subheader("🎯 Gatilhos Armados Hoje")
        if oportunidades: 
            df_op = pd.DataFrame(oportunidades)
            df_op['Preço'] = df_op['Preço'].apply(lambda x: f"R$ {x:.2f}")
            df_op['Stop (HiLo)'] = df_op['Stop (HiLo)'].apply(lambda x: f"R$ {x:.2f}")
            st.dataframe(df_op, use_container_width=True, hide_index=True)
        else: st.info("Sem sinais de ignição no momento.")

# ==========================================
# ABA 2: RAIO-X INDIVIDUAL (O LABORATÓRIO)
# ==========================================
with aba_individual:
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            ativo_rx = st.selectbox("Ativo:", ativos_para_rastrear, key="rx_ativo_i")
            usar_atr_rx = st.toggle("📈 Exigir ATR Subindo", value=True, key="rx_atr_tg")
        with c2:
            periodo_rx = st.selectbox("Período:", options=['1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=1, key="rx_per_i")
            cap_rx = st.number_input("Capital/Trade:", value=10000.0, key="rx_cap_i")
        with c3:
            tempo_rx = st.selectbox("Gráfico:", ['1d', '1wk'], format_func=lambda x: {'1d': 'Diário', '1wk': 'Semanal'}[x], index=0, key="rx_tmp_i")
            atr_len_rx = st.number_input("Período ATR:", value=10, step=1, disabled=not usar_atr_rx)
        with c4:
            hilo_len_rx = st.number_input("HiLo Activator (Padrão 8):", value=8, step=1)
            wma_len_rx = st.number_input("Média WMA:", value=12, step=1)

    exibir_explicacao_estrategia()

    if st.button("🔍 Rodar Laboratório", type="primary", use_container_width=True, key="rx_btn_i"):
        intervalo_i = tradutor_intervalo.get(tempo_rx, Interval.in_daily)
        with st.spinner("Analisando a paz do sossego..."):
            try:
                df_full = tv.get_hist(symbol=ativo_rx.replace('.SA',''), exchange='BMFBOVESPA', interval=intervalo_i, n_bars=5000)
                if df_full is not None:
                    df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                    df_full = calcular_sossegado(df_full, hilo_len=hilo_len_rx, wma_len=wma_len_rx, atr_len=atr_len_rx, filtro_atr=usar_atr_rx)
                    
                    delta = {'1y': 1, '2y': 2, '5y': 5}.get(periodo_rx, 10)
                    data_corte = df_full.index[-1] - pd.DateOffset(years=delta) if periodo_rx != 'max' else df_full.index[0]
                    df = df_full[df_full.index >= data_corte].copy().reset_index()
                    
                    trades, em_pos = [], None
                    for i in range(1, len(df)):
                        row = df.iloc[i]
                        
                        if em_pos is None:
                            if row['Cruzou_Compra']:
                                em_pos = {'data': row['datetime'], 'preco': row['Close']}
                        else:
                            # Saída do Sossego: HiLo virou para baixo (preço cruzou a escadinha)
                            if row['Cruzou_Venda'] or row['Low'] < row['HiLo']:
                                p_sai = min(row['Open'], row['HiLo']) # Sai no gap ou cravado no HiLo
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
                        lucro_total = df_t['Lucro R$'].sum()
                        
                        st.markdown(f"### 📊 Resumo: {ativo_rx}")
                        
                        # Painel de Resultados Elegante
                        c_res1, c_res2, c_res3, c_res4 = st.columns(4)
                        cor_lucro = '#2eeb5c' if lucro_total > 0 else '#ff4d4d'
                        
                        c_res1.markdown(f"**Lucro Total:**<br><span style='font-size:18px; color:{cor_lucro}'>R$ {lucro_total:.2f}</span>", unsafe_allow_html=True)
                        c_res2.markdown(f"**Taxa de Acerto:**<br><span style='font-size:18px'>{tx:.1f}%</span>", unsafe_allow_html=True)
                        c_res3.markdown(f"**Payoff:**<br><span style='font-size:18px'>{pf:.2f}</span>", unsafe_allow_html=True)
                        c_res4.markdown(f"**Operações Fechadas:**<br><span style='font-size:18px'>{len(df_t)}</span>", unsafe_allow_html=True)
                        
                        st.markdown("<br>", unsafe_allow_html=True)

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
                        
                        st.info("💡 **Dica de Gráfico:** Adicione o 'Gann HiLo Activator' no TradingView para visualizar a escadinha que guiou as saídas desses trades!")
                    else: st.warning("Nenhuma operação concluída neste período com essas configurações.")
            except Exception as e: st.error(f"Erro: {e}")
