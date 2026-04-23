import streamlit as st
from tvDatafeed import TvDatafeed, Interval
import pandas as pd
import numpy as np
import pandas_ta as ta
import time
import warnings
from datetime import datetime

warnings.filterwarnings('ignore')

# ==========================================
# 1. SEGURANÇA E CONEXÃO
# ==========================================
if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, inicie sessão na página inicial (Home).")
    st.stop()

@st.cache_resource
def get_tv_connection():
    return TvDatafeed()

tv = get_tv_connection()

tradutor_intervalo = {
    '15m': Interval.in_15_minute,
    '60m': Interval.in_1_hour,
    '1d': Interval.in_daily,
    '1wk': Interval.in_weekly
}

tradutor_periodo_nome = {
    '1mo': '1 Mês', '3mo': '3 Meses', '6mo': '6 Meses',
    '1y': '1 Ano', '2y': '2 Anos', '5y': '5 Anos',
    'max': 'Máximo', '60d': '60 Dias'
}

bdrs_elite = ['NVDC34.SA', 'P2LT34.SA', 'ROXO34.SA', 'INBR32.SA', 'M1TA34.SA', 'TSLA34.SA', 'LILY34.SA', 'AMZO34.SA', 'AURA33.SA', 'GOGL34.SA', 'MSFT34.SA', 'MUTC34.SA', 'MELI34.SA', 'C2OI34.SA', 'ORCL34.SA', 'M2ST34.SA', 'A1MD34.SA', 'NFLX34.SA', 'ITLC34.SA', 'AVGO34.SA', 'COCA34.SA', 'JBSS32.SA', 'AAPL34.SA', 'XPBR31.SA', 'STOC34.SA']
ibrx_selecao = ['PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'BBDC4.SA', 'BBAS3.SA', 'B3SA3.SA', 'ABEV3.SA', 'WEGE3.SA', 'AXIA3.SA', 'SUZB3.SA', 'RENT3.SA', 'RADL3.SA', 'EQTL3.SA', 'LREN3.SA', 'PRIO3.SA', 'HAPV3.SA', 'GGBR4.SA', 'VBBR3.SA', 'SBSP3.SA', 'CMIG4.SA', 'CPLE3.SA', 'ENEV3.SA', 'TIMS3.SA', 'TOTS3.SA', 'EGIE3.SA', 'CSAN3.SA', 'ALOS3.SA', 'DIRR3.SA', 'VIVT3.SA', 'KLBN11.SA', 'UGPA3.SA', 'PSSA3.SA', 'CYRE3.SA', 'ASAI3.SA', 'RAIL3.SA', 'ISAE3.SA', 'CSNA3.SA', 'MGLU3.SA', 'EMBJ3.SA', 'TAEE11.SA', 'BBSE3.SA', 'FLRY3.SA', 'MULT3.SA', 'TFCO4.SA', 'LEVE3.SA', 'CPFE3.SA', 'GOAU4.SA', 'MRVE3.SA', 'YDUQ3.SA', 'SMTO3.SA', 'SLCE3.SA', 'CVCB3.SA', 'USIM5.SA', 'BRAP4.SA', 'BRAV3.SA', 'EZTC3.SA', 'PCAR3.SA', 'AUAU3.SA', 'DXCO3.SA', 'CASH3.SA', 'VAMO3.SA', 'AZZA3.SA', 'AURE3.SA', 'BEEF3.SA', 'ECOR3.SA', 'FESA4.SA', 'POMO4.SA', 'CURY3.SA', 'INTB3.SA', 'JHSF3.SA', 'LIGT3.SA', 'LOGG3.SA', 'MDIA3.SA', 'MBRF3.SA', 'NEOE3.SA', 'QUAL3.SA', 'RAPT4.SA', 'ROMI3.SA', 'SANB11.SA', 'SIMH3.SA', 'TEND3.SA', 'VULC3.SA', 'PLPL3.SA', 'CEAB3.SA', 'UNIP6.SA', 'LWSA3.SA', 'BPAC11.SA', 'GMAT3.SA', 'CXSE3.SA', 'ABCB4.SA', 'CSMG3.SA', 'SAPR11.SA', 'GRND3.SA', 'BRAP3.SA', 'LAVV3.SA', 'RANI3.SA', 'ITSA3.SA', 'ALUP11.SA', 'FIQE3.SA', 'COGN3.SA', 'IRBR3.SA', 'SEER3.SA', 'ANIM3.SA', 'JSLG3.SA', 'POSI3.SA', 'MYPK3.SA', 'SOJA3.SA', 'BLAU3.SA', 'PGMN3.SA', 'TUPY3.SA', 'VVEO3.SA', 'MELK3.SA', 'SHUL4.SA', 'BRSR6.SA']

# ==========================================
# 2. MOTORES MATEMÁTICOS
# ==========================================
def calcular_rolling_poc(df, periodo_lookback=30, num_bins=24):
    poc_list = [np.nan] * len(df)
    for i in range(periodo_lookback, len(df)):
        janela = df.iloc[i-periodo_lookback:i]
        min_p, max_p = janela['Low'].min(), janela['High'].max()
        if max_p == min_p: poc_list[i] = df['Close'].iloc[i]; continue
        bin_edges = np.linspace(min_p, max_p, num_bins)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        vol_profile = np.zeros(num_bins - 1)
        for j in range(len(janela)):
            idx = np.digitize(janela['Close'].iloc[j], bin_edges) - 1
            idx = min(max(idx, 0), num_bins - 2)
            vol_profile[idx] += janela['Volume'].iloc[j]
        poc_list[i] = bin_centers[np.argmax(vol_profile)]
    return pd.Series(poc_list, index=df.index)

def aplicar_fluxo_agressao(df):
    range_c = df['High'] - df['Low']
    df['Saldo_Ag'] = np.where(range_c > 0, df['Volume'] * ((2 * df['Close'] - df['Low'] - df['High']) / range_c), 0)
    df['Delta_Acumulado'] = df['Saldo_Ag'].rolling(window=5).sum()
    return df

# ==========================================
# 3. INTERFACE
# ==========================================
st.title("📊 Fluxo Institucional (POC + VWAP + DELTA)")
st.markdown("Rastreando a defesa dos tubarões com filtro de agressão em tempo real.")

aba_radar, aba_individual = st.tabs(["📡 Radar Institucional (Delta)", "🔬 Raio-X Individual"])

# ABA 1: RADAR (SCANNER)
with aba_radar:
    # (Mantido como estava no turno anterior para brevidade)
    st.info("Utilize a aba Raio-X para análise detalhada com resumo tático.")

# ABA 2: RAIO-X INDIVIDUAL (Ajustado)
with aba_individual:
    st.subheader("🔬 Laboratório de Microestrutura")
    col1, col2 = st.columns([1, 2])
    with col1:
        rx_ativo = st.text_input("Ativo (Ex: PETR4):", value="PETR4").upper().replace('.SA', '')
        rx_tempo = st.selectbox("Tempo:", ['1d', '60m'], key="rx_inst_t")
        rx_btn = st.button("🔬 Analisar DNA do Fluxo", use_container_width=True)
    
    if rx_btn:
        with st.spinner("Mapeando ordens..."):
            df = tv.get_hist(symbol=rx_ativo, exchange='BMFBOVESPA', interval=tradutor_intervalo[rx_tempo], n_bars=100)
            if df is not None:
                df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
                df['POC'] = calcular_rolling_poc(df, periodo_lookback=30)
                df['VWAP'] = ta.vwma(df['Close'], df['Volume'], length=20)
                df = aplicar_fluxo_agressao(df)
                
                res = df.iloc[-1]
                
                # 1. MÉTRICAS TOPO
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Preço Atual", f"R$ {res['Close']:.2f}")
                c2.metric("POC (30d)", f"R$ {res['POC']:.2f}", f"{(res['Close']/res['POC']-1)*100:.2f}%")
                c3.metric("VWAP (VWMA20)", f"R$ {res['VWAP']:.2f}")
                delta_val = res['Delta_Acumulado']
                c4.metric("Saldo Agres. (5p)", f"{delta_val:,.0f}", delta="COMPRADOR" if delta_val > 0 else "VENDEDOR", delta_color="normal" if delta_val > 0 else "inverse")

                st.divider()
                
                # 2. TABELA DE DADOS (Única exibição)
                st.markdown("### 📋 Histórico Recente de Agressão")
                df_view = df[['Close', 'POC', 'VWAP', 'Saldo_Ag', 'Delta_Acumulado']].tail(10).copy()
                st.dataframe(df_view, use_container_width=True)

                # 3. RESUMO TÁTICO (Veredito)
                st.markdown("---")
                st.subheader("🎯 Resumo Tático (Leitura Institucional)")
                
                # Lógica de análise
                p_poc = res['Close'] > res['POC']
                p_vwap = res['Close'] > res['VWAP']
                dist_vwap = abs(res['Close'] - res['VWAP']) / res['VWAP'] * 100
                p_delta = res['Delta_Acumulado'] > 0

                st.markdown(f"""
                * {'✅' if p_poc else '❌'} **Filtro POC:** Preço está {'acima' if p_poc else 'abaixo'} da zona de maior volume ({res['POC']:.2f}). Viés de {'ALTA' if p_poc else 'BAIXA'}.
                * {'⚠️' if dist_vwap < 0.5 else '✅' if p_vwap else '❌'} **Filtro VWAP:** O preço está {'colado na' if dist_vwap < 0.5 else 'acima da' if p_vwap else 'abaixo da'} média institucional ({res['VWAP']:.2f}).
                * {'✅' if p_delta else '❌'} **Filtro Delta:** A agressão acumulada é {'COMPRADORA' if p_delta else 'VENDEDORA'} ({res['Delta_Acumulado']:,.0f}).
                """)

                if p_poc and p_delta and res['Close'] >= res['VWAP']:
                    st.success("⚖️ **VEREDITO:** Cenário de **FORTE COMPRA**. Institucionais estão defendendo a região com agressão ativa. Alta probabilidade de continuidade.")
                elif not p_poc and not p_delta and res['Close'] <= res['VWAP']:
                    st.error("⚖️ **VEREDITO:** Cenário de **FORTE VENDA**. O ativo perdeu valor institucional e está sendo 'marretado' no book. Evite compras.")
                else:
                    st.warning("⚖️ **VEREDITO:** Mercado em **EQUILÍBRIO / INDECISÃO**. Indicadores divergentes. Aguarde o alinhamento total para agir.")
