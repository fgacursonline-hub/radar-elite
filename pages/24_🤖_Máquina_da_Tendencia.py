import streamlit as st, pandas as pd, pandas_ta as ta, numpy as np
from tvDatafeed import TvDatafeed, Interval
import warnings, sys, os

warnings.filterwarnings('ignore')

# Configuração de Caminhos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from config_ativos import bdrs_elite, ibrx_selecao
    lista_ativos = sorted(list(set([a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)])))
except:
    lista_ativos = ["GOGL34", "AAPL34", "TSLA34", "PETR4", "VALE3"]

st.set_page_config(page_title="Máquina Profit V3", layout="wide")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("Por favor, faça login na Home.")
    st.stop()

@st.cache_resource
def conexao_tv(): return TvDatafeed()
tv = conexao_tv()

def rma_wilder(series, length):
    alpha = 1.0 / length
    rma = np.full_like(series, np.nan, dtype=float)
    idx = np.where(~np.isnan(series))[0]
    if len(idx) == 0: return rma
    start = idx[0]
    rma[start + length - 1] = np.mean(series[start : start + length])
    for i in range(start + length, len(series)):
        rma[i] = rma[i-1] if np.isnan(series[i]) else alpha * series[i] + (1 - alpha) * rma[i-1]
    return rma

def calculo_v3(df, p_di, p_adx, s_adx, m_adx, p_st, m_st):
    if df is None or len(df) < 50: return None
    df.index = df.index.tz_localize(None)
    
    # 1. DMI (DI+ e DI-) usando Período DI (Ex: 13)
    dmi_raw = ta.adx(df['high'], df['low'], df['close'], length=p_di)
    df['pDI'] = dmi_raw.iloc[:, 1] 
    df['mDI'] = dmi_raw.iloc[:, 2] 
    
    # 2. ADX usando Período e Suavização (Ex: 8, 8)
    dx = 100 * np.abs(df['pDI'] - df['mDI']) / (df['pDI'] + df['mDI'])
    if m_adx == 'rma': df['adx_line'] = rma_wilder(dx, s_adx)
    elif m_adx == 'sma': df['adx_line'] = ta.sma(dx, s_adx)
    else: df['adx_line'] = ta.ema(dx, s_adx)
    
    # 3. SuperTrend
    st_df = ta.supertrend(df['high'], df['low'], df['close'], length=p_st, multiplier=m_st)
    df['st_dir'] = st_df.iloc[:, 1]
    
    df['adx_o'] = df['adx_line'].shift(1)
    df['mdi_o'] = df['mDI'].shift(1)
    return df.dropna()

# --- INTERFACE FORÇADA V3 ---
st.title("🔬 MÁQUINA PROFIT V3 (Sincronização Total)")
st.markdown("---")

c1, c2, c3, c4 = st.columns([1.5, 1, 2, 1.5])

with c1:
    at_v3 = st.selectbox("Ativo:", lista_ativos, key="at_v3")
    cp_v3 = st.number_input("Capital (R$):", value=10000.0, key="cp_v3")
    tf_v3 = st.selectbox("Tempo:", ['1d', '60m', '15m'], key="tf_v3")

with c2:
    st.write("**Parâmetros DI**")
    p_di_v3 = st.number_input("DI Período (13):", value=13, key="p_di_v3")

with c3:
    st.write("**Parâmetros ADX (Preto)**")
    col_a, col_b, col_c = st.columns(3)
    p_adx_v3 = col_a.number_input("ADX Per (8):", value=8, key="p_adx_v3")
    s_adx_v3 = col_b.number_input("Suaviz. (8):", value=8, key="s_adx_v3")
    m_adx_v3 = col_c.selectbox("Média:", ['rma', 'sma', 'ema'], key="m_adx_v3")

with c4:
    st.write("**Parâmetros SuperTrend**")
    p_st_v3 = st.number_input("ST Per:", value=10, key="p_st_v3")
    m_st_v3 = st.number_input("ST Mult:", value=3.0, key="m_st_v3")

if st.button("🚀 EXECUTAR ANÁLISE PROFIT V3", use_container_width=True, type="primary"):
    intervalo = Interval.in_daily if tf_v3 == '1d' else (Interval.in_1_hour if tf_v3 == '60m' else Interval.in_15_minute)
    with st.spinner("Puxando dados e batendo cálculos..."):
        df = tv.get_hist(symbol=at_v3, exchange='BMFBOVESPA', interval=intervalo, n_bars=3000)
        
        if df is not None:
            df = calculo_v3(df, p_di_v3, p_adx_v3, s_adx_v3, m_adx_v3, p_st_v3, m_st_v3)
            df_b = df.reset_index()
            
            trades = []
            em_pos = False
            
            for i in range(1, len(df_b)):
                # GATILHO EXATO: Preto cruza Vermelho de baixo pra cima
                cruzou = (df_b['adx_o'].iloc[i] <= df_b['mdi_o'].iloc[i]) and (df_b['adx_line'].iloc[i] > df_b['mDI'].iloc[i])
                ok_di = df_b['pDI'].iloc[i] > df_b['mDI'].iloc[i]
                ok_st = df_b['st_dir'].iloc[i] == 1
                
                if not em_pos and cruzou and ok_di and ok_st:
                    em_pos = True
                    data_e, preco_e = df_b.iloc[i, 0], df_b['close'].iloc[i]
                
                elif em_pos and (df_b['st_dir'].iloc[i] == -1 or i == len(df_b)-1):
                    lucro = cp_v3 * ((df_b['close'].iloc[i] / preco_e) - 1)
                    trades.append({
                        'Entrada': data_e.strftime('%d/%m/%Y'),
                        'Saída': df_b.iloc[i, 0].strftime('%d/%m/%Y'),
                        'R$': round(lucro, 2),
                        'Status': '✅' if lucro > 0 else '❌'
                    })
                    em_pos = False
            
            if trades:
                st.success(f"Análise Concluída para {at_v3}")
                st.dataframe(pd.DataFrame(trades), use_container_width=True)
                total = sum([t['R$'] for t in trades])
                st.metric("Resultado Consolidado", f"R$ {total:,.2f}")
            else:
                st.info("Nenhum cruzamento de ADX encontrado no período.")
