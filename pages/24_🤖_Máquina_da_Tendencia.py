import streamlit as st
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
import warnings
import sys
import os
from tvDatafeed import TvDatafeed, Interval

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

ativos_lista = sorted(list(set([a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)])))

st.set_page_config(page_title="Trend Machine", layout="wide", page_icon="🤖")
if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial.")
    st.stop()

@st.cache_resource
def get_tv_connection(): return TvDatafeed()
tv = get_tv_connection()

dic_per = {'1mo':'1 Mês', '3mo':'3 Meses', '6mo':'6 Meses', '1y':'1 Ano', '2y':'2 Anos', '5y':'5 Anos', 'max':'Máximo'}
dic_int = {'15m':Interval.in_15_minute, '60m':Interval.in_1_hour, '1d':Interval.in_daily, '1wk':Interval.in_weekly}

def cor_lucro(row):
    if 'Resultado Atual' in row and isinstance(row['Resultado Atual'], str) and '+' in row['Resultado Atual']:
        return ['color: #00FF00; font-weight: bold'] * len(row)
    return [''] * len(row)

# ==========================================
# MOTOR MATEMÁTICO PURO (CLONE PINE SCRIPT)
# ==========================================
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

def ind_trend(df, di_len=13, adx_len=8, st_len=10, st_mult=3.0):
    if df is None or len(df) < 50: return None
    df.index = df.index.tz_localize(None)
    
    h, l, c = df['High'].values, df['Low'].values, df['Close'].values
    up, down = np.zeros_like(h), np.zeros_like(l)
    up[1:] = h[1:] - h[:-1]
    down[1:] = l[:-1] - l[1:]
    
    pdm = np.where((up > down) & (up > 0), up, 0.0)
    mdm = np.where((down > up) & (down > 0), down, 0.0)
    
    tr2, tr3 = np.zeros_like(h), np.zeros_like(l)
    tr2[1:] = np.abs(h[1:] - c[:-1])
    tr3[1:] = np.abs(l[1:] - c[:-1])
    tr = np.maximum(h - l, np.maximum(tr2, tr3))
    
    tr_rma = calc_rma(tr, di_len)
    tr_rma = np.where(tr_rma == 0, 1e-10, tr_rma)
    
    pdi = 100 * (calc_rma(pdm, di_len) / tr_rma)
    mdi = 100 * (calc_rma(mdm, di_len) / tr_rma)
    
    s_di = np.where((pdi + mdi) == 0, 1e-10, pdi + mdi)
    dx = 100 * np.abs(pdi - mdi) / s_di
    adx = calc_rma(dx, adx_len)
    
    df['ADX'], df['+DI'], df['-DI'] = adx, pdi, mdi
    st_df = ta.supertrend(df['High'], df['Low'], df['Close'], length=st_len, multiplier=st_mult)
    df['ST_Dir'] = st_df[[col for col in st_df.columns if col.startswith('SUPERTd_')][0]]
    
    df['ADX_Prev'] = df['ADX'].shift(1)
    df['-DI_Prev'] = df['-DI'].shift(1)
    df['+DI_Prev'] = df['+DI'].shift(1)
    return df.dropna()

st.title("🤖 Máquina de Tendência (ADX + SuperTrend)")
aba_padrao, aba_individual, aba_futuros = st.tabs(["📡 Radar Padrão", "🔬 Raio-X Individual", "📉 Raio-X Futuros"])

# ==========================================
# ABA 1: RADAR PADRÃO
# ==========================================
with aba_padrao:
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        lista_tr = c1.selectbox("Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos"], key="a1")
        cap_tr = c1.number_input("Capital (R$):", value=10000.0, step=1000.0, key="c1")
        tmp_tr = c2.selectbox("Tempo:", ['15m', '60m', '1d', '1wk', '1mo'], index=2, key="t1")
        per_tr = c2.selectbox("Histórico:", ['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], index=3, key="p1")
        
        ca1, ca2 = c3.columns(2)
        di_len_g = ca1.number_input("DI Per:", min_value=2, value=13, key="di1")
        adx_len_g = ca2.number_input("ADX Per:", min_value=2, value=8, key="adx1")
        cs1, cs2 = c3.columns(2)
        st_len_g = cs1.number_input("ST Per:", min_value=2, value=10, key="st1")
        st_mult_g = cs2.number_input("ST Mult:", min_value=0.5, value=3.0, step=0.1, key="stm1")
        
        u_alvo_g = c4.toggle("🎯 Alvo Fixo", value=True, key="ua1")
        alvo_g = c4.number_input("Alvo %:", value=15.0, disabled=not u_alvo_g, key="al1")
        u_stop_g = c4.toggle("🛡️ Stop", value=False, key="us1")
        stop_g = c4.number_input("Stop %:", value=5.0, disabled=not u_stop_g, key="st_1")
        u_rst_g = c4.toggle("📉 Saída Rev ST", value=True, key="rst1")
        u_rdm_g = c4.toggle("📉 Saída Rev DMI", value=False, key="rdm1")

    if st.button("🚀 Iniciar Varredura", type="primary", use_container_width=True, key="btn1"):
        lst = bdrs_elite if lista_tr=="BDRs Elite" else ibrx_selecao if lista_tr=="IBrX Seleção" else bdrs_elite+ibrx_selecao
        lst = sorted(list(set([a.replace('.SA','') for a in lst])))
        sinais, abertos, resumo = [], [], []
        pb = st.progress(0); stx = st.empty()

        for idx, ativo in enumerate(lst):
            stx.text(f"🔍 Medindo {ativo} ({idx+1}/{len(lst)})")
            pb.progress((idx + 1) / len(lst))
            try:
                df_f = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=dic_int.get(tmp_tr), n_bars=5000)
                if df_f is None or len(df_f) < 50: continue
                df_f.rename(columns={'open':'Open', 'high':'High', 'low':'Low', 'close':'Close'}, inplace=True)
                df_f = ind_trend(df_f, di_len_g, adx_len_g, st_len_g, st_mult_g)
                if df_f is None: continue
                
                dt_corte = df_f.index[-1] - pd.DateOffset(months=int(per_tr.replace('mo','').replace('y','')) * (1 if 'mo' in per_tr else 12)) if per_tr != 'max' else df_f.index[0]
                df_b = df_f[df_f.index >= dt_corte].copy().reset_index()
                
                trades, em_pos = [], False
                col_dt = df_b.columns[0]
                alv, stp = alvo_g/100.0, stop_g/100.0

                for i in range(1, len(df_b)):
                    cruz_agora = (df_b['ADX_Prev'].iloc[i] <= df_b['-DI_Prev'].iloc[i]) and (df_b['ADX'].iloc[i] > df_b['-DI'].iloc[i])
                    sn_compra = cruz_agora and (df_b['+DI'].iloc[i] > df_b['-DI'].iloc[i]) and (df_b['ST_Dir'].iloc[i] == 1)

                    if em_pos:
                        min_p = min(min_p, df_b['Low'].iloc[i])
                        bt_al = u_alvo_g and (df_b['High'].iloc[i] >= tk_p)
                        bt_st = u_stop_g and (df_b['Low'].iloc[i] <= st_p)
                        rv_st = u_rst_g and (df_b['ST_Dir'].iloc[i] == -1)
                        rv_dm = u_rdm_g and (df_b['+DI'].iloc[i] < df_b['-DI'].iloc[i])
                        
                        if bt_st: trades.append({'Lucro': -(cap_tr*stp), 'DD': ((min_p/pe)-1)*100, 'Motivo': 'Stop ❌'}); em_pos=False
                        elif bt_al: trades.append({'Lucro': cap_tr*alv, 'DD': ((min_p/pe)-1)*100, 'Motivo': 'Alvo ✅'}); em_pos=False
                        elif rv_st or rv_dm:
                            luc = cap_tr * ((df_b['Close'].iloc[i]/pe)-1)
                            mot = 'ST' if rv_st else 'DMI'
                            trades.append({'Lucro': luc, 'DD': ((min_p/pe)-1)*100, 'Motivo': f"Saída {mot} {'✅' if luc>0 else '❌'}"})
                            em_pos=False

                    if sn_compra and not em_pos:
                        em_pos, de, pe = True, df_b[col_dt].iloc[i], df_b['Close'].iloc[i]
                        min_p, tk_p, st_p = pe, pe*(1+alv), pe*(1-stp)

                if em_pos:
                    res = ((df_b['Close'].iloc[-1]/pe)-1)*100
                    dd = ((min_p/pe)-1)*100
                    abertos.append({'Ativo': ativo, 'Entrada': de.strftime('%d/%m/%Y'), 'Dias': (df_b[col_dt].iloc[-1]-de).days, 'PM': f"R${pe:.2f}", 'Cotação Atual': f"R${df_b['Close'].iloc[-1]:.2f}", 'Prej. Máx': f"{dd:.2f}%", 'Resultado Atual': f"+{res:.2f}%" if res>0 else f"{res:.2f}%"})
                else:
                    hj = df_f.iloc[-1]
                    if (hj['ADX_Prev'] <= hj['-DI_Prev']) and (hj['ADX'] > hj['-DI']) and (hj['+DI'] > hj['-DI']) and (hj['ST_Dir'] == 1):
                        sinais.append({'Ativo': ativo, 'Preço': f"R${hj['Close']:.2f}", 'ADX': f"{hj['ADX']:.1f}"})

                if trades:
                    dt = pd.DataFrame(trades)
                    resumo.append({'Ativo': ativo, 'Trades': len(dt), 'Pior Queda': f"{dt['DD'].min():.2f}%", 'Lucro R$': dt['Lucro'].sum()})
            except: pass
        
        stx.empty(); pb.empty()
        st.subheader("🚀 Sinais Hoje"); st.dataframe(pd.DataFrame(sinais), hide_index=True)
        st.subheader("⏳ Abertos"); st.dataframe(pd.DataFrame(abertos).style.apply(cor_lucro, axis=1), hide_index=True)
        st.subheader("📊 Histórico")
        if resumo:
            dr = pd.DataFrame(resumo).sort_values('Lucro R$', ascending=False).head(10)
            dr['Lucro R$'] = dr['Lucro R$'].apply(lambda x: f"R$ {x:,.2f}"); st.dataframe(dr, hide_index=True)

# === ABA 2: RAIO-X INDIVIDUAL ===
with aba_individual:
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            atv_rx = st.selectbox("Ativo a Testar:", ativos_lista, key="a2")
            cap_rx = st.number_input("Capital Base (R$):", value=10000.0, step=1000.0, key="c2")
        with c2:
            tmp_rx = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk', '1mo'], index=2, key="t2")
            per_rx = st.selectbox("Período Estudo:", ['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], index=3, key="p2")
        with c3:
            ca1, ca2 = st.columns(2)
            di_rx = ca1.number_input("DI Per:", min_value=2, value=13, key="di2")
            adx_rx = ca2.number_input("ADX Per:", min_value=2, value=8, key="adx2")
            cs1, cs2 = st.columns(2)
            st_l_rx = cs1.number_input("ST Per:", value=10, key="st2")
            st_m_rx = cs2.number_input("ST Mult:", value=3.0, step=0.1, key="stm2")
        with c4:
            u_alvo_rx = st.toggle("🎯 Alvo Fixo", value=True, key="ua2")
            alvo_rx = st.number_input("Alvo (%):", value=15.0, step=0.5, disabled=not u_alvo_rx, key="al2")
            u_stop_rx = st.toggle("🛡️ Stop Fixo", value=False, key="us2")
            stop_rx = st.number_input("Stop (%):", value=5.0, step=0.5, disabled=not u_stop_rx, key="st_2")
            u_rst_rx = st.toggle("📉 Saída Rev ST", value=True, key="rst2")
            u_rdm_rx = st.toggle("📉 Saída Rev DMI", value=False, key="rdm2")

    if st.button("🔍 Gerar Raio-X", type="primary", use_container_width=True, key="btn2"):
        with st.spinner(f'Calculando {atv_rx}...'):
            try:
                df_f = tv.get_hist(symbol=atv_rx, exchange='BITSTAMP' if 'BTC' in atv_rx else 'BMFBOVESPA', interval=dic_int.get(tmp_rx), n_bars=5000)
                if df_f is not None and len(df_f)>50:
                    df_f.rename(columns={'open':'Open','high':'High','low':'Low','close':'Close'}, inplace=True)
                    df_f = ind_trend(df_f, di_rx, adx_rx, st_l_rx, st_m_rx)
                    
                    dt_corte = df_f.index[-1] - pd.DateOffset(months=int(per_rx.replace('mo','').replace('y','')) * (1 if 'mo' in per_rx else 12)) if per_rx != 'max' else df_f.index[0]
                    df_b = df_f[df_f.index >= dt_corte].copy().reset_index()
                    
                    trades, em_pos, vit, der, col_dt = [], False, 0, 0, df_b.columns[0]
                    alv, stp = alvo_rx/100.0, stop_rx/100.0

                    for i in range(1, len(df_b)):
                        cruz_c = (df_b['ADX_Prev'].iloc[i] <= df_b['-DI_Prev'].iloc[i]) and (df_b['ADX'].iloc[i] > df_b['-DI'].iloc[i])
                        sn_compra = cruz_c and (df_b['+DI'].iloc[i] > df_b['-DI'].iloc[i]) and (df_b['ST_Dir'].iloc[i] == 1)
                        
                        if not em_pos:
                            if sn_compra:
                                em_pos, de, pe = True, df_b[col_dt].iloc[i], df_b['Close'].iloc[i]
                                min_p, tk_p, st_p = pe, pe*(1+alv), pe*(1-stp)
                        else:
                            min_p = min(min_p, df_b['Low'].iloc[i])
                            bt_al = u_alvo_rx and (df_b['High'].iloc[i] >= tk_p)
                            bt_st = u_stop_rx and (df_b['Low'].iloc[i] <= st_p)
                            rv_st = u_rst_rx and (df_b['ST_Dir'].iloc[i] == -1)
                            rv_dm = u_rdm_rx and (df_b['+DI'].iloc[i] < df_b['-DI'].iloc[i])
                            
                            saiu = False
                            if bt_st: luc, sit, saiu = -(cap_rx*stp), "Stop ❌", True; der+=1
                            elif bt_al: luc, sit, saiu = cap_rx*alv, "Alvo ✅", True; vit+=1
                            elif rv_st or rv_dm:
                                luc = cap_rx * ((df_b['Close'].iloc[i]/pe)-1)
                                sit, saiu = f"Saída {'ST' if rv_st else 'DMI'} {'✅' if luc>0 else '❌'}", True
                                vit += 1 if luc>0 else 0; der += 1 if luc<=0 else 0

                            if saiu:
                                dd = ((min_p/pe)-1)*100
                                trades.append({'Entrada': de.strftime('%d/%m/%y'), 'Saída': df_b[col_dt].iloc[i].strftime('%d/%m/%y'), 'Duração': f"{(df_b[col_dt].iloc[i]-de).days}d", 'Lucro': luc, 'Queda Máx': f"{dd:.2f}%", 'Situação': sit})
                                em_pos = False

                    if em_pos:
                        st.warning(f"⚠️ OPERAÇÃO ATIVA. Entrada: {de.strftime('%d/%m/%y')} | PM: R${pe:.2f} | Atual: {((df_b['Close'].iloc[-1]/pe)-1)*100:.2f}%")
                    if trades:
                        dr = pd.DataFrame(trades)
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Lucro Total", f"R$ {dr['Lucro'].sum():,.2f}")
                        m2.metric("Operações", len(dr))
                        m3.metric("Taxa Acerto", f"{(vit/len(dr)*100):.1f}%")
                        dr['Lucro'] = dr['Lucro'].apply(lambda x: f"R$ {x:,.2f}")
                        st.dataframe(dr, use_container_width=True, hide_index=True)
                    else: st.info("Nenhuma operação concluída.")
            except Exception as e: st.error(f"Erro: {e}")

# === ABA 3: FUTUROS ===
with aba_futuros:
    cf1, cf2, cf3 = st.columns(3)
    with cf1:
        f_sel = st.selectbox("Ativo:", ["WINFUT (Índice)", "WDOFUT (Dólar)"])
        f_ativo = "WIN1!" if "WIN" in f_sel else "WDO1!"
        f_dir = st.selectbox("Direção:", ["Ambas", "Apenas Compra", "Apenas Venda"])
        f_tmp = st.selectbox("Tempo Gráfico F:", ['15m', '60m'])
    with cf2:
        c_fa1, c_fa2 = st.columns(2)
        f_di = c_fa1.number_input("DI Per F:", value=13)
        f_adx = c_fa2.number_input("ADX Per F:", value=8)
        c_fs1, c_fs2 = st.columns(2)
        f_st = c_fs1.number_input("ST Per F:", value=10)
        f_stm = c_fs2.number_input("ST Mult F:", value=3.0, step=0.1)
    with cf3:
        f_alv = st.number_input("Alvo (Pts):", value=300 if "WIN" in f_sel else 10, step=50)
        f_cont = st.number_input("Contratos:", value=1)
        f_mlt = st.number_input("R$/Ponto:", value=0.20 if "WIN" in f_sel else 10.0)
        f_zer = st.checkbox("⏰ Zerar Fim Dia", value=True)
        f_sdm = st.checkbox("📉 Saída Rev DMI F", value=False)
        btn_fut = st.button("🚀 Gerar Futuros", type="primary", use_container_width=True)

    if btn_fut:
        with st.spinner('Simulando Futuros...'):
            try:
                df_f = tv.get_hist(symbol=f_ativo, exchange='BMFBOVESPA', interval=dic_int.get(f_tmp), n_bars=10000)
                if df_f is not None:
                    df_f.rename(columns={'open':'Open','high':'High','low':'Low','close':'Close'}, inplace=True)
                    df_f = ind_trend(df_f, f_di, f_adx, f_st, f_stm)
                    trd, pos, vits, col_dt = [], 0, 0, df_f.reset_index().columns[0]
                    df_b = df_f.reset_index()

                    for i in range(1, len(df_b)):
                        dt_h, dt_o = df_b[col_dt].iloc[i], df_b[col_dt].iloc[i-1]
                        
                        # Compra
                        c_c = (df_b['ADX_Prev'].iloc[i] <= df_b['-DI_Prev'].iloc[i]) and (df_b['ADX'].iloc[i] > df_b['-DI'].iloc[i])
                        sn_compra = c_c and (df_b['+DI'].iloc[i] > df_b['-DI'].iloc[i]) and (df_b['ST_Dir'].iloc[i] == 1)
                        # Venda
                        c_v = (df_b['ADX_Prev'].iloc[i] <= df_b['+DI_Prev'].iloc[i]) and (df_b['ADX'].iloc[i] > df_b['+DI'].iloc[i])
                        sn_venda = c_v and (df_b['-DI'].iloc[i] > df_b['+DI'].iloc[i]) and (df_b['ST_Dir'].iloc[i] == -1)

                        if pos != 0 and f_zer and dt_h.date() != dt_o.date():
                            pts = (df_b['Close'].iloc[i-1] - pe) if pos==1 else (pe - df_b['Close'].iloc[i-1])
                            lc = pts * f_cont * f_mlt
                            trd.append({'E': de.strftime('%d/%m %H:%M'), 'S': dt_o.strftime('%d/%m %H:%M'), 'T': 'Compra' if pos==1 else 'Venda', 'Pts': pts, 'R$': lc, 'St': 'Zerad. Dia'})
                            vits += 1 if lc>0 else 0; pos = 0

                        if pos == 1: 
                            if df_b['High'].iloc[i] >= tk:
                                trd.append({'E': de.strftime('%d/%m %H:%M'), 'S': dt_h.strftime('%d/%m %H:%M'), 'T': 'Compra', 'Pts': f_alv, 'R$': f_alv*f_cont*f_mlt, 'St': 'Gain ✅'})
                                vits+=1; pos=0
                            elif df_b['ST_Dir'].iloc[i] == -1 or (f_sdm and df_b['+DI'].iloc[i] < df_b['-DI'].iloc[i]):
                                pts = df_b['Close'].iloc[i] - pe
                                trd.append({'E': de.strftime('%d/%m %H:%M'), 'S': dt_h.strftime('%d/%m %H:%M'), 'T': 'Compra', 'Pts': pts, 'R$': pts*f_cont*f_mlt, 'St': 'Rev.'})
                                pos=0
                        elif pos == -1: 
                            if df_b['Low'].iloc[i] <= tk:
                                trd.append({'E': de.strftime('%d/%m %H:%M'), 'S': dt_h.strftime('%d/%m %H:%M'), 'T': 'Venda', 'Pts': f_alv, 'R$': f_alv*f_cont*f_mlt, 'St': 'Gain ✅'})
                                vits+=1; pos=0
                            elif df_b['ST_Dir'].iloc[i] == 1 or (f_sdm and df_b['-DI'].iloc[i] < df_b['+DI'].iloc[i]):
                                pts = pe - df_b['Close'].iloc[i]
                                trd.append({'E': de.strftime('%d/%m %H:%M'), 'S': dt_h.strftime('%d/%m %H:%M'), 'T': 'Venda', 'Pts': pts, 'R$': pts*f_cont*f_mlt, 'St': 'Rev.'})
                                pos=0
                        
                        if sn_compra and pos==0 and f_dir!="Apenas Venda": pos, de, pe, tk = 1, dt_h, df_b['Close'].iloc[i], df_b['Close'].iloc[i]+f_alv
                        elif sn_venda and pos==0 and f_dir!="Apenas Compra": pos, -1, dt_h, df_b['Close'].iloc[i], df_b['Close'].iloc[i]-f_alv

                    if trd:
                        dr = pd.DataFrame(trd)
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Lucro Líquido", f"R$ {dr['R$'].sum():,.2f}")
                        m2.metric("Operações", len(dr))
                        m3.metric("Pontos", f"{dr['Pts'].sum():.0f}")
                        st.dataframe(dr, use_container_width=True, hide_index=True)
            except Exception as e: st.error(f"Erro: {e}")
