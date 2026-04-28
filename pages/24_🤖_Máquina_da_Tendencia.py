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
    st.error("Erro ao carregar lista de ativos.")
    st.stop()

st.set_page_config(page_title="Trend Master Pro", layout="wide")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.warning("Acesse a Home para logar.")
    st.stop()

@st.cache_resource
def conexao_tv(): return TvDatafeed()
tv = conexao_tv()

# --- FUNÇÕES MATEMÁTICAS ---
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

def calculo_full(df, p_di, p_adx, s_adx, m_adx, p_st, m_st):
    if df is None or len(df) < 50: return None
    df.index = df.index.tz_localize(None)
    
    # 1. DMI (DI+ e DI-)
    dmi_raw = ta.adx(df['high'], df['low'], df['close'], length=p_di)
    df['pDI'] = dmi_raw.iloc[:, 1] # +DI
    df['mDI'] = dmi_raw.iloc[:, 2] # -DI
    
    # 2. ADX Personalizado (Independente do DI)
    dx = 100 * np.abs(df['pDI'] - df['mDI']) / (df['pDI'] + df['mDI'])
    
    if m_adx == 'rma': df['adx_line'] = rma_wilder(dx, s_adx)
    elif m_adx == 'sma': df['adx_line'] = ta.sma(dx, s_adx)
    else: df['adx_line'] = ta.ema(dx, s_adx)
    
    # 3. SuperTrend
    st_df = ta.supertrend(df['high'], df['low'], df['close'], length=p_st, multiplier=m_st)
    df['st_dir'] = st_df.iloc[:, 1]
    
    # Memórias
    df['adx_ontem'] = df['adx_line'].shift(1)
    df['mdi_ontem'] = df['mDI'].shift(1)
    
    return df.dropna()

# --- INTERFACE ---
st.title("🔬 Laboratório de Calibragem (ProfitPro)")

# Abas com nomes novos para forçar atualização
aba_lupa, aba_radar = st.tabs(["🔎 Raio-X Detalhado", "📡 Varredura Geral"])

with aba_lupa:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        at_escolhido = st.selectbox("Escolha o Ativo:", lista_ativos, key="sel_at")
        cap_inv = st.number_input("Capital (R$):", value=10000.0, key="num_cap")
    with c2:
        tf_escolhido = st.selectbox("Tempo Gráfico:", ['1d', '60m', '15m'], key="sel_tf")
        hist_escolhido = st.selectbox("Histórico:", ['1y', '2y', 'max'], key="sel_hi")
    with c3:
        st.write("**Ajustes Profit ADX**")
        p_di = st.number_input("Período DI (13):", value=13, key="num_pdi")
        p_adx = st.number_input("Período ADX (8):", value=8, key="num_padx")
        s_adx = st.number_input("Suavização ADX (8):", value=8, key="num_sadx")
        m_adx = st.selectbox("Tipo Média ADX:", ['rma', 'sma', 'ema'], key="sel_madx")
    with c4:
        st.write("**Ajustes SuperTrend**")
        p_st = st.number_input("ST Período:", value=10, key="num_pst")
        m_st = st.number_input("ST Mult:", value=3.0, key="num_mst")

    if st.button("🚀 EXECUTAR ANÁLISE", use_container_width=True):
        intervalo = Interval.in_daily if tf_escolhido == '1d' else (Interval.in_1_hour if tf_escolhido == '60m' else Interval.in_15_minute)
        df = tv.get_hist(symbol=at_escolhido, exchange='BMFBOVESPA', interval=intervalo, n_bars=3000)
        
        if df is not None:
            df = calculo_full(df, p_di, p_adx, s_adx, m_adx, p_st, m_st)
            df_b = df.reset_index()
            
            trades = []
            em_pos = False
            
            for i in range(1, len(df_b)):
                # GATILHO: Preto cruza Vermelho pra cima
                cruzamento = (df_b['adx_ontem'].iloc[i] <= df_b['mdi_ontem'].iloc[i]) and (df_b['adx_line'].iloc[i] > df_b['mDI'].iloc[i])
                
                # FILTROS
                filtro_di = df_b['pDI'].iloc[i] > df_b['mDI'].iloc[i]
                filtro_st = df_b['st_dir'].iloc[i] == 1
                
                if not em_pos and cruzamento and filtro_di and filtro_st:
                    em_pos = True
                    data_e = df_b.iloc[i, 0]
                    preco_e = df_b['close'].iloc[i]
                
                elif em_pos and (df_b['st_dir'].iloc[i] == -1 or i == len(df_b)-1):
                    lucro = cap_inv * ((df_b['close'].iloc[i] / preco_e) - 1)
                    trades.append({
                        'Entrada': data_e.strftime('%d/%m/%Y'),
                        'Saída': df_b.iloc[i, 0].strftime('%d/%m/%Y'),
                        'Resultado R$': round(lucro, 2),
                        'Status': '✅' if lucro > 0 else '❌'
                    })
                    em_pos = False
            
            if trades:
                st.dataframe(pd.DataFrame(trades), use_container_width=True)
                st.metric("Lucro Total", f"R$ {sum([t['Resultado R$'] for t in trades])}")
            else:
                st.info("Nenhuma entrada encontrada com esses parâmetros.")
