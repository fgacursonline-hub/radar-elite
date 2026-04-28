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

tradutor_periodo = {'1mo': '1 Mês', '3mo': '3 Meses', '6mo': '6 Meses', '1y': '1 Ano', '2y': '2 Anos', '5y': '5 Anos', 'max': 'Máximo'}
tradutor_intervalo = {'15m': Interval.in_15_minute, '60m': Interval.in_1_hour, '1d': Interval.in_daily, '1wk': Interval.in_weekly}

def colorir_lucro(row):
    if 'Resultado Atual' in row and isinstance(row['Resultado Atual'], str) and row['Resultado Atual'].startswith('+'):
        return ['color: #00FF00; font-weight: bold'] * len(row)
    return [''] * len(row)

# ==========================================
# 3. MOTOR MATEMÁTICO: CLONE DO PINE SCRIPT
# ==========================================
def calc_rma(series, length):
    """Cópia exata da função ta.rma() do Pine Script do TradingView"""
    alpha = 1.0 / length
    rma = np.full_like(series, np.nan, dtype=float)
    valid_idx = np.where(~np.isnan(series))[0]
    if len(valid_idx) == 0: return rma
    start = valid_idx[0]
    if len(series) < start + length: return rma
    
    # O segredo do TradingView: começa com Média Simples (SMA)
    rma[start + length - 1] = np.mean(series[start : start + length])
    for i in range(start + length, len(series)):
        if np.isnan(series[i]):
            rma[i] = rma[i-1]
        else:
            rma[i] = alpha * series[i] + (1 - alpha) * rma[i-1]
    return rma

def calcular_indicadores_trend(df, adx_len=14, st_len=10, st_mult=3.0):
    if df is None or len(df) < max(adx_len, st_len) * 2: return None
    df.index = df.index.tz_localize(None)
    
    # 1. ADX e DMI IDÊNTICO ao script do Gu5tavo71
    h, l, c = df['High'].values, df['Low'].values, df['Close'].values
    up = np.zeros_like(h); down = np.zeros_like(l)
    up[1:] = h[1:] - h[:-1]
    down[1:] = l[:-1] - l[1:]
    
    pdm = np.where((up > down) & (up > 0), up, 0.0)
    mdm = np.where((down > up) & (down > 0), down, 0.0)
    
    tr2 = np.zeros_like(h); tr3 = np.zeros_like(l)
    tr2[1:] = np.abs(h[1:] - c[:-1])
    tr3[1:] = np.abs(l[1:] - c[:-1])
    tr = np.maximum(h - l, np.maximum(tr2, tr3))
    
    tr_rma = calc_rma(tr, adx_len)
    tr_rma = np.where(tr_rma == 0, 1e-10, tr_rma) # Evita divisão por zero
    
    pdi = 100 * (calc_rma(pdm, adx_len) / tr_rma)
    mdi = 100 * (calc_rma(mdm, adx_len) / tr_rma)
    
    sum_di = np.where((pdi + mdi) == 0, 1e-10, pdi + mdi)
    dx = 100 * np.abs(pdi - mdi) / sum_di
    adx = calc_rma(dx, adx_len)
    
    df['ADX'], df['+DI'], df['-DI'] = adx, pdi, mdi
    
    # 2. SuperTrend (Mantido com pandas_ta pois é 100% igual)
    st_df = ta.supertrend(df['High'], df['Low'], df['Close'], length=st_len, multiplier=st_mult)
    if st_df is None or st_df.empty: return None
    df['ST_Dir'] = st_df[[col for col in st_df.columns if col.startswith('SUPERTd_')][0]]
    
    # 3. Memórias para o gatilho de cruzamento exato
    df['ADX_Prev'] = df['ADX'].shift(1)
    df['-DI_Prev'] = df['-DI'].shift(1)
    df['+DI_Prev'] = df['+DI'].shift(1)
    return df.dropna()

st.title("🤖 Máquina de Tendência (ADX + SuperTrend)")
st.info("📊 **Estratégia Matemática Pura:** Cópia 1:1 do Pine Script do TradingView. A compra SÓ dispara se **HOJE** o ADX (Preto) fura o DI- (Vermelho) de baixo para cima, com o DI+ (Verde) por cima e o SuperTrend Verde.")

aba_padrao, aba_individual, aba_futuros = st.tabs(["📡 Radar Padrão", "🔬 Raio-X Individual", "📉 Raio-X Futuros"])

# ==========================================
# ABA 1: RADAR PADRÃO E ABA 2: INDIVIDUAL 
# (As lógicas são idênticas, separadas pela interface)
# ==========================================
with aba_individual:
    st.subheader("🔬 Análise Detalhada de Ativo Único")
    with st.container(border=True):
        ci1, ci2, ci3, ci4 = st.columns(4)
        with ci1:
            ativo_rx = st.selectbox("Ativo a Testar:", ativos_para_rastrear, key="i_tr_ativo")
            capital_rx = st.number_input("Capital Base (R$):", value=10000.0, step=1000.0, key="i_tr_cap")
        with ci2:
            tempo_rx = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk', '1mo'], index=2, key="i_tr_tmp")
            periodo_rx = st.selectbox("Período de Estudo:", ['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], index=3, key="i_tr_per")
        with ci3:
            adx_len = st.number_input("Período ADX:", value=14, key="i_tr_adxlen")
            c_st1, c_st2 = st.columns(2)
            st_len = c_st1.number_input("ST Per:", value=10, key="i_tr_stlen")
            st_mult = c_st2.number_input("ST Mult:", value=3.0, step=0.1, key="i_tr_stmult")
        with ci4:
            usar_alvo_rx = st.toggle("🎯 Alvo Fixo", value=True, key="tg_alvo_rx")
            lupa_alvo = st.number_input("Alvo (%):", value=15.0, step=0.5, disabled=not usar_alvo_rx)
            usar_stop_rx = st.toggle("🛡️ Stop Loss", value=False, key="tg_stop_rx")
            lupa_stop = st.number_input("Stop Loss (%):", value=5.0, step=0.5, disabled=not usar_stop_rx)
            usar_saida_st_rx = st.toggle("📉 Saída Reversão ST", value=True)
            usar_saida_dmi_rx = st.toggle("📉 Saída Reversão DMI", value=False)

    if st.button("🔍 Gerar Raio-X", type="primary", use_container_width=True):
        alvo_d, stop_d = lupa_alvo / 100.0, lupa_stop / 100.0
        with st.spinner(f'Calculando matemática pura de Wilder para {ativo_rx}...'):
            try:
                exc = 'BITSTAMP' if 'BTC' in ativo_rx else 'BMFBOVESPA'
                df_full = tv.get_hist(symbol=ativo_rx, exchange=exc, interval=tradutor_intervalo.get(tempo_rx), n_bars=5000)
                
                if df_full is not None and not df_full.empty:
                    df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                    df_full = calcular_indicadores_trend(df_full, adx_len, st_len, st_mult)
                    
                    if df_full is not None:
                        data_corte = df_full.index[-1] - pd.DateOffset(months={'1mo': 1, '3mo': 3, '6mo': 6, '1y': 12, '2y': 24, '5y': 60}.get(periodo_rx, 120)) if periodo_rx != 'max' else df_full.index[0]
                        df_b = df_full[df_full.index >= data_corte].reset_index()
                        col_dt = df_b.columns[0]
                        trades, em_pos, vit, der, pos_atual = [], False, 0, 0, None

                        for i in range(1, len(df_b)):
                            # --- O GATILHO BLINDADO (Cruzamento Exato + Confirmação) ---
                            cruzou_adx = (df_b['ADX'].iloc[i] > df_b['-DI'].iloc[i]) and (df_b['ADX_Prev'].iloc[i] <= df_b['-DI_Prev'].iloc[i])
                            sinal_compra = cruzou_adx and (df_b['+DI'].iloc[i] > df_b['-DI'].iloc[i]) and (df_b['ST_Dir'].iloc[i] == 1)
                            
                            if not em_pos:
                                if sinal_compra:
                                    em_pos, d_ent, p_ent = True, df_b[col_dt].iloc[i], df_b['Close'].iloc[i]
                                    min_na_op, cap = p_ent, float(capital_rx)
                                    take_p, stop_p = p_ent * (1 + alvo_d), p_ent * (1 - stop_d)
                                    pos_atual = {'Data': d_ent, 'PM': p_ent, 'Cap': cap}
                            else:
                                if df_b['Low'].iloc[i] < min_na_op: min_na_op = df_b['Low'].iloc[i]
                                
                                bt_alvo = usar_alvo_rx and (df_b['High'].iloc[i] >= take_p)
                                bt_stop = usar_stop_rx and (df_b['Low'].iloc[i] <= stop_p)
                                rev_st = usar_saida_st_rx and (df_b['ST_Dir'].iloc[i] == -1)
                                rev_dmi = usar_saida_dmi_rx and (df_b['+DI'].iloc[i] < df_b['-DI'].iloc[i])
                                
                                if bt_stop or bt_alvo or rev_st or rev_dmi:
                                    if bt_stop:
                                        lucro, sit = -(cap * stop_d), "Stop ❌"; der += 1
                                    elif bt_alvo:
                                        lucro, sit = cap * alvo_d, "Alvo ✅"; vit += 1
                                    else:
                                        lucro = cap * ((df_b['Close'].iloc[i] / p_ent) - 1)
                                        if rev_st: sit = "Saída ST ✅" if lucro > 0 else "Reversão ST ❌"
                                        else: sit = "Saída DMI ✅" if lucro > 0 else "Reversão DMI ❌"
                                        vit += 1 if lucro > 0 else 0; der += 1 if lucro <= 0 else 0
                                        
                                    dd = ((min_na_op / p_ent) - 1) * 100
                                    trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': df_b[col_dt].iloc[i].strftime('%d/%m/%Y'), 'Duração': f"{(df_b[col_dt].iloc[i] - d_ent).days} d", 'Lucro (R$)': lucro, 'Queda Máx': f"{dd:.2f}%", 'Situação': sit})
                                    em_pos, pos_atual = False, None

                        if em_pos and pos_atual:
                            st.warning(f"⚠️ **OPERAÇÃO EM CURSO: {ativo_rx}**")
                            cot = df_b['Close'].iloc[-1]
                            res_pct = ((cot / pos_atual['PM']) - 1) * 100
                            c1, c2, c3 = st.columns(3)
                            c1.metric("Entrada", pos_atual['Data'].strftime('%d/%m/%Y'))
                            c2.metric("Preço", f"R$ {pos_atual['PM']:.2f}")
                            c3.metric("Atual", f"{res_pct:.2f}%", delta=f"R$ {pos_atual['Cap'] * res_pct / 100:.2f}")
                        
                        if trades:
                            df_res = pd.DataFrame(trades)
                            st.markdown(f"### 📊 Resultado: {ativo_rx}")
                            m1, m2, m3 = st.columns(3)
                            m1.metric("Lucro Total", f"R$ {df_res['Lucro (R$)'].sum():,.2f}")
                            m2.metric("Operações", len(df_res))
                            m3.metric("Taxa Acerto", f"{(vit/len(df_res)*100):.1f}%")
                            st.dataframe(df_res, use_container_width=True, hide_index=True)
                        else: st.info("Nenhuma operação finalizada.")
            except Exception as e: st.error(f"Erro: {e}")

# ==========================================
# ABA 3: RAIO-X FUTUROS (DAY TRADE / WIN e WDO)
# ==========================================
with aba_futuros:
    st.subheader("📉 Raio-X Mercado Futuro")
    cf1, cf2, cf3 = st.columns(3)
    with cf1:
        f_sel = st.selectbox("Ativo:", ["WINFUT (Mini Índice)", "WDOFUT (Mini Dólar)"])
        f_ativo = "WIN1!" if "WIN" in f_sel else "WDO1!"
        f_dir = st.selectbox("Direção:", ["Ambas", "Apenas Compra", "Apenas Venda"])
    with cf2:
        f_adx_len = st.number_input("Período ADX Futuro:", value=14)
        c_f1, c_f2 = st.columns(2)
        f_st_len = c_f1.number_input("Período ST Futuro:", value=10)
        f_st_mult = c_f2.number_input("Mult ST Futuro:", value=3.0, step=0.1)
    with cf3:
        f_alvo = st.number_input("Alvo (Pontos):", value=300 if "WIN" in f_sel else 10, step=50)
        f_cont = st.number_input("Contratos:", value=1)
        f_multi = st.number_input("R$ por Ponto:", value=0.20 if "WIN" in f_sel else 10.0)
        f_zerar = st.checkbox("⏰ Zerar Fim do Dia", value=True)
        f_sdmi = st.checkbox("📉 Saída Reversão DMI", value=False)
        btn_fut = st.button("🚀 Gerar Futuros", type="primary", use_container_width=True)

    if btn_fut:
        with st.spinner('Processando...'):
            try:
                df_full = tv.get_hist(symbol=f_ativo, exchange='BMFBOVESPA', interval=Interval.in_15_minute, n_bars=10000)
                if df_full is not None:
                    df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                    df_full = calcular_indicadores_trend(df_full, f_adx_len, f_st_len, f_st_mult)
                    
                    if df_full is not None:
                        trades, pos, vits, derrs = [], 0, 0, 0
                        df_b = df_full.reset_index()
                        col_dt = df_b.columns[0]

                        for i in range(1, len(df_b)):
                            d_at, d_ant = df_b[col_dt].iloc[i], df_b[col_dt].iloc[i-1]
                            
                            # COMPRA
                            cruz_compra = (df_b['ADX'].iloc[i] > df_b['-DI'].iloc[i]) and (df_b['ADX_Prev'].iloc[i] <= df_b['-DI_Prev'].iloc[i])
                            sinal_compra = cruz_compra and (df_b['+DI'].iloc[i] > df_b['-DI'].iloc[i]) and (df_b['ST_Dir'].iloc[i] == 1)
                            
                            # VENDA
                            cruz_venda = (df_b['ADX'].iloc[i] > df_b['+DI'].iloc[i]) and (df_b['ADX_Prev'].iloc[i] <= df_b['+DI_Prev'].iloc[i])
                            sinal_venda = cruz_venda and (df_b['-DI'].iloc[i] > df_b['+DI'].iloc[i]) and (df_b['ST_Dir'].iloc[i] == -1)

                            if pos != 0 and f_zerar and d_at.date() != d_ant.date():
                                pts = (df_b['Close'].iloc[i-1] - p_ent) if pos == 1 else (p_ent - df_b['Close'].iloc[i-1])
                                luc = pts * f_cont * f_multi
                                trades.append({'Entrada': d_ent.strftime('%d/%m %H:%M'), 'Saída': d_ant.strftime('%d/%m %H:%M'), 'Tipo': 'Compra 🟢' if pos == 1 else 'Venda 🔴', 'Pontos': pts, 'Lucro (R$)': luc, 'Status': 'Zerad. Fim Dia'})
                                vits += 1 if luc > 0 else 0; pos = 0

                            if pos == 1: 
                                if df_b['High'].iloc[i] >= take_p:
                                    trades.append({'Entrada': d_ent.strftime('%d/%m %H:%M'), 'Saída': d_at.strftime('%d/%m %H:%M'), 'Tipo': 'Compra 🟢', 'Pontos': f_alvo, 'Lucro (R$)': f_alvo * f_cont * f_multi, 'Status': 'Gain ✅'})
                                    vits += 1; pos = 0
                                elif df_b['ST_Dir'].iloc[i] == -1 or (f_sdmi and df_b['+DI'].iloc[i] < df_b['-DI'].iloc[i]):
                                    pts = df_b['Close'].iloc[i] - p_ent
                                    trades.append({'Entrada': d_ent.strftime('%d/%m %H:%M'), 'Saída': d_at.strftime('%d/%m %H:%M'), 'Tipo': 'Compra 🟢', 'Pontos': pts, 'Lucro (R$)': pts * f_cont * f_multi, 'Status': 'Reversão'})
                                    pos = 0
                                    
                            elif pos == -1: 
                                if df_b['Low'].iloc[i] <= take_p:
                                    trades.append({'Entrada': d_ent.strftime('%d/%m %H:%M'), 'Saída': d_at.strftime('%d/%m %H:%M'), 'Tipo': 'Venda 🔴', 'Pontos': f_alvo, 'Lucro (R$)': f_alvo * f_cont * f_multi, 'Status': 'Gain ✅'})
                                    vits += 1; pos = 0
                                elif df_b['ST_Dir'].iloc[i] == 1 or (f_sdmi and df_b['-DI'].iloc[i] < df_b['+DI'].iloc[i]):
                                    pts = p_ent - df_b['Close'].iloc[i]
                                    trades.append({'Entrada': d_ent.strftime('%d/%m %H:%M'), 'Saída': d_at.strftime('%d/%m %H:%M'), 'Tipo': 'Venda 🔴', 'Pontos': pts, 'Lucro (R$)': pts * f_cont * f_multi, 'Status': 'Reversão'})
                                    pos = 0
                            
                            if sinal_compra and pos == 0 and f_dir != "Apenas Venda":
                                pos, d_ent, p_ent = 1, d_at, df_b['Close'].iloc[i]
                                take_p = p_ent + f_alvo
                            elif sinal_venda and pos == 0 and f_dir != "Apenas Compra":
                                pos, d_ent, p_ent = -1, d_at, df_b['Close'].iloc[i]
                                take_p = p_ent - f_alvo

                        if trades:
                            df_res = pd.DataFrame(trades)
                            m1, m2, m3 = st.columns(3)
                            m1.metric("Lucro Total", f"R$ {df_res['Lucro (R$)'].sum():,.2f}")
                            m2.metric("Operações", len(df_res))
                            m3.metric("Saldo Pontos", f"{df_res['Pontos'].sum():.0f}")
                            st.dataframe(df_res, use_container_width=True, hide_index=True)
            except Exception as e: st.error(f"Erro: {e}")
