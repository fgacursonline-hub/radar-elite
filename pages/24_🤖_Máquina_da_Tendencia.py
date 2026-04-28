import streamlit as st, pandas as pd, pandas_ta as ta, numpy as np, sys, os
from datetime import datetime
import warnings

# Importação do Motor de Busca Central
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from bunker import motor_busca # Aqui está o nosso motor central

warnings.filterwarnings('ignore')

# Configuração da Página
st.set_page_config(page_title="Máquina Profit V4", layout="wide", page_icon="🛡️")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("Por favor, faça login na Home.")
    st.stop()

# --- MOTOR MATEMÁTICO DE PRECISÃO ---
def calc_rma(series, length):
    alpha = 1.0 / length
    rma = np.full_like(series, np.nan, dtype=float)
    idx = np.where(~np.isnan(series))[0]
    if len(idx) == 0 or len(series) < idx[0] + length: return rma
    start = idx[0]
    rma[start + length - 1] = np.mean(series[start : start + length])
    for i in range(start + length, len(series)):
        rma[i] = rma[i-1] if np.isnan(series[i]) else alpha * series[i] + (1 - alpha) * rma[i-1]
    return rma

def processar_estrategia(df, p_di, p_adx, s_adx, m_adx, p_st, m_st):
    if df is None or len(df) < 50: return None
    
    # 1. DMI (DI+ e DI-) - Calibragem Profit
    dmi_raw = ta.adx(df['high'], df['low'], df['close'], length=p_di)
    df['pDI'] = dmi_raw.iloc[:, 1] 
    df['mDI'] = dmi_raw.iloc[:, 2] 
    
    # 2. ADX com Suavização Independente (Ex: 8, 8)
    dx = 100 * np.abs(df['pDI'] - df['mDI']) / (df['pDI'] + df['mDI'])
    if m_adx == 'rma': df['adx_line'] = calc_rma(dx, s_adx)
    elif m_adx == 'sma': df['adx_line'] = ta.sma(dx, s_adx)
    else: df['adx_line'] = ta.ema(dx, s_adx)
    
    # 3. SuperTrend do Pine
    st_df = ta.supertrend(df['high'], df['low'], df['close'], length=p_st, multiplier=m_st)
    df['st_dir'] = st_df.iloc[:, 1]
    
    # Memória para Cruzamento
    df['adx_o'] = df['adx_line'].shift(1)
    df['mdi_o'] = df['mDI'].shift(1)
    return df.dropna()

# --- INTERFACE ---
st.title("🛡️ MÁQUINA PROFIT V4 (Powered by BUNKER)")
st.markdown("---")

# Barra Lateral de Parâmetros (Para não poluir o visual)
with st.sidebar:
    st.header("⚙️ Calibragem Profit")
    p_di = st.number_input("DI Período (Profit: 13)", value=13)
    p_adx = st.number_input("ADX Período (Profit: 8)", value=8)
    s_adx = st.number_input("Suavização ADX (Profit: 8)", value=8)
    m_adx = st.selectbox("Média ADX:", ['rma', 'sma', 'ema'])
    
    st.header("⚙️ SuperTrend")
    p_st = st.number_input("ST Período:", value=10)
    m_st = st.number_input("ST Multiplicador:", value=3.0)

# Abas de Operação
aba_rx, aba_radar = st.tabs(["🔬 Raio-X Bunker", "📡 Radar de Tendência"])

with aba_rx:
    c1, c2, c3 = st.columns(3)
    at_escolhido = c1.text_input("Ativo (Ex: GOGL34):", value="GOGL34").upper()
    tf_escolhido = c2.selectbox("Tempo:", ['1d', '60m', '15m'], index=0)
    cap_inv = c3.number_input("Capital (R$):", value=10000.0)

    if st.button("🔍 EXECUTAR VIA BUNKER", use_container_width=True, type="primary"):
        with st.spinner("Bunker buscando dados..."):
            # Chamada do Motor de Busca unificado
            df = motor_busca(at_escolhido, tf_escolhido)
            
            if df is not None:
                df = processar_estrategia(df, p_di, p_adx, s_adx, m_adx, p_st, m_st)
                df_b = df.reset_index()
                
                trades = []
                em_pos = False
                
                for i in range(1, len(df_b)):
                    # REGRA: Preto cruzou Vermelho pra cima?
                    cruzou = (df_b['adx_o'].iloc[i] <= df_b['mdi_o'].iloc[i]) and (df_b['adx_line'].iloc[i] > df_b['mDI'].iloc[i])
                    cond_compra = cruzou and (df_b['pDI'].iloc[i] > df_b['mDI'].iloc[i]) and (df_b['st_dir'].iloc[i] == 1)
                    
                    if not em_pos and cond_compra:
                        em_pos = True
                        data_e, preco_e = df_b.iloc[i, 0], df_b['close'].iloc[i]
                    
                    elif em_pos and (df_b['st_dir'].iloc[i] == -1 or i == len(df_b)-1):
                        lucro = cap_inv * ((df_b['close'].iloc[i] / preco_e) - 1)
                        trades.append({
                            'Entrada': data_e.strftime('%d/%m/%Y'),
                            'Saída': df_b.iloc[i, 0].strftime('%d/%m/%Y'),
                            'Lucro R$': round(lucro, 2),
                            'Status': '✅' if lucro > 0 else '❌'
                        })
                        em_pos = False
                
                if trades:
                    st.dataframe(pd.DataFrame(trades), use_container_width=True)
                    total = sum([t['Lucro R$'] for t in trades])
                    st.metric("Resultado Final", f"R$ {total:,.2f}", delta=f"{((total/cap_inv)*100):.2f}%")
                else:
                    st.warning("Nenhum sinal detectado com esta calibragem.")
