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
st.set_page_config(page_title="Trend Machine", layout="wide", page_icon="🤖")

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

def colorir_lucro(row):
    if 'Resultado Atual' in row and isinstance(row['Resultado Atual'], str) and row['Resultado Atual'].startswith('+'):
        return ['color: #00FF00; font-weight: bold'] * len(row)
    return [''] * len(row)

# ==========================================
# 3. MOTOR MATEMÁTICO NATIVO TRADINGVIEW
# ==========================================
def rma_tv(series, length):
    """Calcula a Running Moving Average idêntica ao Pine Script do TradingView"""
    return series.ewm(alpha=1/length, min_periods=length, adjust=False).mean()

def calcular_indicadores_trend(df, adx_len=14, st_len=10, st_mult=3.0):
    if df is None or len(df) < max(adx_len, st_len) * 2:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = df.index.tz_localize(None)
    
    # --- CÁLCULO EXATO DO ADX/DMI DO TRADINGVIEW ---
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    up = high - high.shift(1)
    down = low.shift(1) - low
    
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    
    tr_rma = rma_tv(tr, adx_len)
    plus_di_rma = rma_tv(pd.Series(plus_dm, index=df.index), adx_len)
    minus_di_rma = rma_tv(pd.Series(minus_dm, index=df.index), adx_len)
    
    df['+DI'] = 100 * (plus_di_rma / tr_rma)
    df['-DI'] = 100 * (minus_di_rma / tr_rma)
    
    dx = 100 * (df['+DI'] - df['-DI']).abs() / (df['+DI'] + df['-DI'])
    df['ADX'] = rma_tv(dx, adx_len)
    
    # --- CÁLCULO DO SUPERTREND ---
    st_df = ta.supertrend(high, low, close, length=st_len, multiplier=st_mult)
    if st_df is None or st_df.empty: return None
    
    col_st = [c for c in st_df.columns if c.startswith('SUPERT_')][0]
    col_st_dir = [c for c in st_df.columns if c.startswith('SUPERTd_')][0]
    
    df['SuperTrend'] = st_df[col_st]
    df['ST_Dir'] = st_df[col_st_dir] 
    
    # Memórias de ontem para calcular o cruzamento exato
    df['ADX_Prev'] = df['ADX'].shift(1)
    df['-DI_Prev'] = df['-DI'].shift(1)
    df['+DI_Prev'] = df['+DI'].shift(1)
    
    return df.dropna()

st.title("🤖 Máquina de Tendência (ADX + SuperTrend)")
st.info("📊 **Estratégia (Trend Following Extremo):** \n\n🟢 **Gatilho de Compra:** Ocorre SOMENTE no momento em que o ADX (Preto) cruza o DI- (Vermelho) para cima. Para validar, o DI+ tem que estar acima do DI- e o SuperTrend verde. \n🔴 **Defesas:** Você pode montar o seu escudo desativando ou ativando a Saída pela Reversão do SuperTrend, Reversão do DMI, Alvo de Lucro ou Stop Loss fixo.")

aba_padrao, aba_individual, aba_futuros = st.tabs([
    "📡 Radar Padrão", "🔬 Raio-X Individual", "📉 Raio-X Futuros"
])
