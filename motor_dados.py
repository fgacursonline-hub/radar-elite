import streamlit as st
import pandas as pd
import yfinance as yf
from tvDatafeed import TvDatafeed, Interval
import warnings
import time

warnings.filterwarnings('ignore')

# Tenta iniciar a conexão com o TradingView silenciosamente
try:
    tv = TvDatafeed()
except Exception:
    tv = None

# ==========================================
# TRADUTORES DE TEMPO GRÁFICO
# ==========================================
mapa_tv = {
    '15m': Interval.in_15_minute,
    '60m': Interval.in_1_hour,
    '1d': Interval.in_daily,
    '1wk': Interval.in_weekly
}

mapa_yf = {
    '15m': '15m',
    '60m': '60m',
    '1d': '1d',
    '1wk': '1wk'
}

# ==========================================
# O COFRE DE MEMÓRIA (CACHE DE 15 MINUTOS)
# ==========================================
# O parâmetro ttl=900 significa que os dados ficam salvos por 900 segundos (15 min).
# Se 50 alunos clicarem no mesmo ativo nesse período, o robô não vai na internet, ele puxa da RAM instantaneamente.
@st.cache_data(ttl=900, show_spinner=False)
def puxar_dados_blindados(ativo, tempo_grafico='1d', barras=150):
    """
    Tenta puxar do TradingView. Se falhar ou for bloqueado, aciona o Yahoo Finance automaticamente.
    Retorna um DataFrame padronizado.
    """
    df = None
    
    # ----------------------------------------
    # TENTATIVA 1: TRADINGVIEW (TV DATAFEED)
    # ----------------------------------------
    if tv is not None:
        try:
            intervalo_tv = mapa_tv.get(tempo_grafico, Interval.in_daily)
            df_tv = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=barras)
            
            if df_tv is not None and not df_tv.empty:
                df = df_tv.copy()
                df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
                return df
        except Exception:
            pass # Falhou, vai tentar o Plano B

    # ----------------------------------------
    # TENTATIVA 2: PLANO B (YAHOO FINANCE)
    # ----------------------------------------
    if df is None or df.empty:
        try:
            ticker_yf = f"{ativo}.SA"
            intervalo_yf = mapa_yf.get(tempo_grafico, '1d')
            
            # Ajusta o período de download do Yahoo baseado no tempo gráfico
            periodo_yf = "60d" if tempo_grafico in ['15m', '60m'] else "2y"
            
            df_yf = yf.download(ticker_yf, period=periodo_yf, interval=intervalo_yf, progress=False)
            
            if not df_yf.empty:
                # O Yahoo Finance às vezes traz colunas duplas (MultiIndex), vamos limpar:
                if isinstance(df_yf.columns, pd.MultiIndex):
                    df_yf.columns = df_yf.columns.droplevel(1)
                
                df = df_yf.tail(barras).copy()
                return df
        except Exception:
            pass

    # Retorna um DataFrame vazio se tudo der errado, para não quebrar o robô
    return pd.DataFrame()
