import streamlit as st, pandas as pd, pandas_ta as ta, numpy as np, time
from tvDatafeed import TvDatafeed, Interval
import warnings, sys, os
warnings.filterwarnings('ignore')

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try: from config_ativos import bdrs_elite, ibrx_selecao
except: st.error("Arquivo config_ativos não encontrado."); st.stop()

st.set_page_config(page_title="Trend Machine", layout="wide")
if 'autenticado' not in st.session_state or not st.session_state['autenticado']: st.stop()

@st.cache_resource
def get_tv(): return TvDatafeed()
tv = get_tv()

d_int = {'15m':Interval.in_15_minute, '60m':Interval.in_1_hour, '1d':Interval.in_daily, '1wk':Interval.in_weekly}
lst_atv = sorted(list(set([a.replace('.SA','') for a in (bdrs_elite + ibrx_selecao)])))

def calc_rma(series, length):
    alpha = 1.0 / length
    rma = np.full_like(series, np.nan, dtype=float)
    v_idx = np.where(~np.isnan(series))[0]
    if len(v_idx) == 0 or len(series) < v_idx[0] + length: return rma
    start = v_idx[0]
    rma[start + length - 1] = np.mean(series[start : start + length])
    for i in range(start + length, len(series)):
        rma[i] = rma[i-1] if np.isnan(series[i]) else alpha * series[i] + (1 - alpha) * rma[i-1]
    return rma

def ind_trend(df, d_l, a_l, a_s, s_l, s_m, smt):
    if df is None or len(df) < 50: return None
    df.index = df.index.tz_localize(None)
    # Cálculo DMI
    dmi = ta.adx(df['High'], df['Low'], df['Close'], length=d_l, lensig=a_l, mamode=smt)
    df['+DI'] = dmi[[c for c in dmi.columns if 'DMP' in c][0]]
    df['-DI'] = dmi[[c for c in dmi.columns if 'DMN' in c][0]]
    # Cálculo ADX com Suavização escolhida
    dx = 100 * np.abs(df['+DI'] - df['-DI']) / (df['+DI'] + df['-DI'])
    if smt == 'rma': df['ADX'] = calc_rma(dx, a_s)
    elif smt == 'sma': df['ADX'] = ta.sma(dx, a_s)
    else: df['ADX'] = ta.ema(dx, a_s)
    # SuperTrend
    st_df = ta.supertrend(df['High'], df['Low'], df['Close'], length=s_l, multiplier=s_m)
    df['ST_Dir'] = st_df[[c for c in st_df.columns if 'SUPERTd_' in c][0]]
    df['ADX_P'], df['-DI_P'] = df['ADX'].shift(1), df['-DI'].shift(1)
    return df.dropna()

st.title("🤖 Máquina ProfitPro")
ab1, ab2, ab3 = st.tabs(["📡 Radar", "🔬 Raio-X Individual", "📉 Futuros"])

with ab2: # FOCO NA SUA TELA
    st.subheader("🔬 Calibragem GOGL34 (DI 13, ADX 8,8)")
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        at_x = c1.selectbox("Ativo:", lst_atv, key="v_at")
        cp_x = c1.number_input("Capital R$:", value=10000.0, key="v_cp")
        tm_x = c2.selectbox("Tempo:", ['15m', '60m', '1d', '1wk'], index=2, key="v_tm")
        pr_x = c2.selectbox("Histórico:", ['1y', '2y', '5y', 'max'], index=1, key="v_pr")
        
        # OS CAMPOS QUE FALTAVAM
        di_v = c3.number_input("Período DI (Profit 13):", value=13, key="v_di")
        ad_v = c3.number_input("Período ADX (Profit 8):", value=8, key="v_ad")
        sv_v = c3.number_input("Suavização ADX (Profit 8):", value=8, key="v_sv")
        mt_v = c3.selectbox("Tipo de Média:", ['rma', 'sma', 'ema'], key="v_mt")
        
        sl_v = c4.number_input("ST Período:", value=10, key="v_sl")
        sm_v = c4.number_input("ST Mult:", value=3.0, key="v_sm")
        
    if st.button("🔍 Rodar Análise", type="primary", use_container_width=True):
        with st.spinner('Sincronizando...'):
            df = tv.get_hist(symbol=at_x, exchange='BMFBOVESPA', interval=d_int.get(tm_x), n_bars=5000)
            if df is not None:
                df.rename(columns={'open':'Open','high':'High','low':'Low','close':'Close'}, inplace=True)
                df = ind_trend(df, di_v, ad_v, sv_v, sl_v, sm_v, mt_v)
                df_b = df.reset_index()
                trades, em_pos, vit = [], False, 0
                for i in range(1, len(df_b)):
                    # GATILHO CRUZAMENTO PRETO NO VERMELHO
                    cruzou = (df_b['ADX_P'].iloc[i] <= df_b['-DI_P'].iloc[i]) and (df_b['ADX'].iloc[i] > df_b['-DI'].iloc[i])
                    if not em_pos and cruzou and df_b['+DI'].iloc[i] > df_b['-DI'].iloc[i] and df_b['ST_Dir'].iloc[i] == 1:
                        em_pos, de, pe = True, df_b.iloc[i,0], df_b['Close'].iloc[i]
                    elif em_pos and (df_b['ST_Dir'].iloc[i] == -1 or i == len(df_b)-1):
                        luc = cp_x * ((df_b['Close'].iloc[i]/pe)-1)
                        trades.append({'Entrada': de.strftime('%d/%m/%y'), 'Saída': df_b.iloc[i,0].strftime('%d/%m/%y'), 'Lucro': luc})
                        if luc > 0: vit += 1
                        em_pos = False
                if trades:
                    st.write(pd.DataFrame(trades))
                    st.metric("Taxa de Acerto", f"{(vit/len(trades)*100):.1f}%")

# (As outras abas seguem a mesma lógica simplificada para não travar)
