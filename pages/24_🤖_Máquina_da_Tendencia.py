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

def cor_luc(row): return ['color: #00FF00; font-weight: bold']*len(row) if '+' in str(row.get('Resultado Atual','')) else ['']*len(row)

# MOTOR MATEMÁTICO: O FRANKENSTEIN DO PROFIT (Com suavização flexível)
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

def ind_trend(df, di_len=13, adx_len=8, adx_sig=8, st_len=10, st_mult=3.0, smooth='rma'):
    if df is None or len(df) < 50: return None
    df.index = df.index.tz_localize(None)
    
    # DI e ADX flexíveis
    dmi = ta.adx(df['High'], df['Low'], df['Close'], length=di_len, lensig=adx_len, mamode=smooth.lower())
    if dmi is None or dmi.empty: return None
    
    df['ADX'] = dmi[[c for c in dmi.columns if c.startswith('ADX')][0]]
    df['+DI'] = dmi[[c for c in dmi.columns if c.startswith('DMP')][0]]
    df['-DI'] = dmi[[c for c in dmi.columns if c.startswith('DMN')][0]]
    
    # Se o Profit usa RMA, SMA, EMA para suavizar a linha ADX, o usuário escolhe
    if smooth.lower() == 'rma': df['ADX'] = calc_rma(df['ADX'], adx_sig)
    elif smooth.lower() == 'sma': df['ADX'] = ta.sma(df['ADX'], adx_sig)
    elif smooth.lower() == 'ema': df['ADX'] = ta.ema(df['ADX'], adx_sig)

    st_df = ta.supertrend(df['High'], df['Low'], df['Close'], length=st_len, multiplier=st_mult)
    df['ST_Dir'] = st_df[[c for c in st_df.columns if 'SUPERTd_' in c][0]]
    
    df['ADX_P'], df['-DI_P'], df['+DI_P'] = df['ADX'].shift(1), df['-DI'].shift(1), df['+DI'].shift(1)
    return df.dropna()

st.title("🤖 Máquina de Tendência (Calibrada p/ Profit)")
st.info("🟢 **Gatilho de Compra:** ADX cruza DI- para cima HOJE, com DI+ > DI- e ST Verde.")
ab1, ab2, ab3 = st.tabs(["📡 Radar", "🔬 Raio-X Individual", "📉 Futuros"])

# === ABA 1: RADAR PADRÃO ===
with ab1:
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        l_tr = c1.selectbox("Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos"], key="a1")
        cap_tr = c1.number_input("Capital (R$):", value=10000.0, step=1000.0, key="c1")
        tmp_tr = c2.selectbox("Tempo:", ['15m', '60m', '1d', '1wk', '1mo'], index=2, key="t1")
        per_tr = c2.selectbox("Histórico:", ['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], index=3, key="p1")
        
        # CAMPOS PROFIT AQUI
        di_g = c3.number_input("DI Per:", value=13, key="di1")
        c_a1, c_a2 = c3.columns(2)
        adx_g = c_a1.number_input("ADX Per:", value=8, key="adx1")
        suav_g = c_a2.selectbox("Suav. ADX:", ['rma', 'sma', 'ema'], key="sv1")
        
        c_s1, c_s2 = c3.columns(2)
        st_l_g = c_s1.number_input("ST Per:", value=10, key="st1")
        st_m_g = c_s2.number_input("ST Mult:", value=3.0, step=0.1, key="stm1")
        
        u_al = c4.toggle("🎯 Alvo Fixo", value=True, key="ua1")
        al_g = c4.number_input("Alvo %:", value=15.0, disabled=not u_al, key="al1")
        u_st = c4.toggle("🛡️ Stop", value=False, key="us1")
        st_g = c4.number_input("Stop %:", value=5.0, disabled=not u_st, key="stp1")
        u_rst = c4.toggle("📉 Saída Rev ST", value=True, key="rst1")
        u_rdm = c4.toggle("📉 Saída Rev DMI", value=False, key="rdm1")

    if st.button("🚀 Iniciar Varredura", type="primary", use_container_width=True):
        lst = bdrs_elite if l_tr=="BDRs Elite" else ibrx_selecao if l_tr=="IBrX Seleção" else bdrs_elite+ibrx_selecao
        lst = sorted(list(set([a.replace('.SA','') for a in lst])))
        sinais, abertos, resumo = [], [], []
        pb = st.progress(0); stx = st.empty()

        for idx, atv in enumerate(lst):
            stx.text(f"🔍 Medindo {atv} ({idx+1}/{len(lst)})")
            pb.progress((idx + 1)/len(lst))
            try:
                df_f = tv.get_hist(symbol=atv, exchange='BMFBOVESPA', interval=d_int.get(tmp_tr), n_bars=5000)
                if df_f is None or len(df_f)<50: continue
                df_f.rename(columns={'open':'Open','high':'High','low':'Low','close':'Close'}, inplace=True)
                df_f = ind_trend(df_f, di_g, adx_g, adx_g, st_l_g, st_m_g, suav_g)
                if df_f is None: continue
                
                dt_c = df_f.index[-1] - pd.DateOffset(months={'1mo':1,'3mo':3,'6mo':6,'1y':12,'2y':24,'5y':60}.get(per_tr,120)) if per_tr != 'max' else df_f.index[0]
                df_b = df_f[df_f.index >= dt_c].copy().reset_index()
                
                trades, em_pos = [], False
                col_dt, alv, stp = df_b.columns[0], al_g/100.0, st_g/100.0

                for i in range(1, len(df_b)):
                    # A REGRA PURA
                    cruz_adx = (df_b['ADX_P'].iloc[i] <= df_b['-DI_P'].iloc[i]) and (df_b['ADX'].iloc[i] > df_b['-DI'].iloc[i])
                    sn_c = cruz_adx and (df_b['+DI'].iloc[i] > df_b['-DI'].iloc[i]) and (df_b['ST_Dir'].iloc[i] == 1)

                    if em_pos:
                        min_p = min(min_p, df_b['Low'].iloc[i])
                        bt_al = u_al and (df_b['High'].iloc[i] >= tk_p)
                        bt_st = u_st and (df_b['Low'].iloc[i] <= st_p)
                        rv_st = u_rst and (df_b['ST_Dir'].iloc[i] == -1)
                        rv_dm = u_rdm and (df_b['+DI'].iloc[i] < df_b['-DI'].iloc[i])
                        
                        if bt_st: trades.append({'L': -(cap_tr*stp), 'D': ((min_p/pe)-1)*100, 'M': 'Stop ❌'}); em_pos=False
                        elif bt_al: trades.append({'L': cap_tr*alv, 'D': ((min_p/pe)-1)*100, 'M': 'Alvo ✅'}); em_pos=False
                        elif rv_st or rv_dm:
                            luc = cap_tr * ((df_b['Close'].iloc[i]/pe)-1)
                            trades.append({'L': luc, 'D': ((min_p/pe)-1)*100, 'M': f"Saída {'ST' if rv_st else 'DMI'} {'✅' if luc>0 else '❌'}"})
                            em_pos=False

                    if sn_c and not em_pos:
                        em_pos, de, pe = True, df_b[col_dt].iloc[i], df_b['Close'].iloc[i]
                        min_p, tk_p, st_p = pe, pe*(1+alv), pe*(1-stp)

                if em_pos:
                    res = ((df_b['Close'].iloc[-1]/pe)-1)*100
                    abertos.append({'Ativo': atv, 'Entrada': de.strftime('%d/%m/%y'), 'Dias': (df_b[col_dt].iloc[-1]-de).days, 'PM': f"R${pe:.2f}", 'Atual': f"R${df_b['Close'].iloc[-1]:.2f}", 'Resultado Atual': f"+{res:.2f}%" if res>0 else f"{res:.2f}%"})
                else:
                    hj = df_f.iloc[-1]
                    if (hj['ADX_P'] <= hj['-DI_P']) and (hj['ADX'] > hj['-DI']) and (hj['+DI'] > hj['-DI']) and (hj['ST_Dir'] == 1):
                        sinais.append({'Ativo': atv, 'Preço': f"R${hj['Close']:.2f}", 'ADX': f"{hj['ADX']:.1f}"})

                if trades:
                    dt = pd.DataFrame(trades)
                    resumo.append({'Ativo': atv, 'Trades': len(dt), 'Pior Queda': f"{dt['D'].min():.2f}%", 'Lucro R$': dt['L'].sum()})
            except: pass
        
        stx.empty(); pb.empty()
        st.subheader("🚀 Sinais Hoje"); st.dataframe(pd.DataFrame(sinais), hide_index=True)
        st.subheader("⏳ Abertos"); st.dataframe(pd.DataFrame(abertos).style.apply(cor_luc, axis=1), hide_index=True)
        st.subheader("📊 Histórico")
        if resumo:
            dr = pd.DataFrame(resumo).sort_values('Lucro R$', ascending=False).head(10)
            dr['Lucro R$'] = dr['Lucro R$'].apply(lambda x: f"R$ {x:,.2f}"); st.dataframe(dr, hide_index=True)

# === ABA 2: RAIO-X INDIVIDUAL ===
with ab2:
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        atv_rx = c1.selectbox("Ativo:", lst_atv, key="a2")
        cap_rx = c1.number_input("Capital R$:", value=10000.0, step=1000.0, key="c2")
        tmp_rx = c2.selectbox("Tempo:", ['15m', '60m', '1d', '1wk', '1mo'], index=2, key="t2")
        per_rx = c2.selectbox("Estudo:", ['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], index=3, key="p2")
        
        # CAMPOS PROFIT AQUI TBM
        di_rx = c3.number_input("DI Per:", value=13, key="di2")
        ca1, ca2 = c3.columns(2)
        adx_rx = ca1.number_input("ADX Per:", value=8, key="adx2")
        suav_rx = ca2.selectbox("Suav. ADX:", ['rma', 'sma', 'ema'], key="sv2")
        
        cs1, cs2 = c3.columns(2)
        st_l_rx = cs1.number_input("ST Per:", value=10, key="st2")
        st_m_rx = cs2.number_input("ST Mult:", value=3.0, step=0.1, key="stm2")
        
        u_al_rx = c4.toggle("🎯 Alvo", value=True, key="ua2")
        al_rx = c4.number_input("Alvo %:", value=15.0, step=0.5, disabled=not u_al_rx, key="al2")
        u_st_rx = c4.toggle("🛡️ Stop", value=False, key="us2")
        st_rx = c4.number_input("Stop %:", value=5.0, step=0.5, disabled=not u_st_rx, key="st_2")
        ur_st_rx = c4.toggle("📉 Saída Rev ST", value=True, key="rst2")
        ur_dm_rx = c4.toggle("📉 Saída Rev DMI", value=False, key="rdm2")

    if st.button("🔍 Gerar Raio-X", type="primary", use_container_width=True, key="brx2"):
        with st.spinner(f'Calculando {atv_rx}...'):
            try:
                df_f = tv.get_hist(symbol=atv_rx, exchange='BITSTAMP' if 'BTC' in atv_rx else 'BMFBOVESPA', interval=d_int.get(tmp_rx), n_bars=5000)
                if df_f is not None and len(df_f)>50:
                    df_f.rename(columns={'open':'Open','high':'High','low':'Low','close':'Close'}, inplace=True)
                    df_f = ind_trend(df_f, di_rx, adx_rx, adx_rx, st_l_rx, st_m_rx, suav_rx)
                    
                    dt_c = df_f.index[-1] - pd.DateOffset(months={'1mo':1,'3mo':3,'6mo':6,'1y':12,'2y':24,'5y':60}.get(per_rx,120)) if per_rx != 'max' else df_f.index[0]
                    df_b = df_f[df_f.index >= dt_c].copy().reset_index()
                    
                    trades, em_pos, vit, col_dt = [], False, 0, df_b.columns[0]
                    alv, stp = al_rx/100.0, st_rx/100.0

                    for i in range(1, len(df_b)):
                        # A REGRA PURA
                        cruz_c = (df_b['ADX_P'].iloc[i] <= df_b['-DI_P'].iloc[i]) and (df_b['ADX'].iloc[i] > df_b['-DI'].iloc[i])
                        sn_c = cruz_c and (df_b['+DI'].iloc[i] > df_b['-DI'].iloc[i]) and (df_b['ST_Dir'].iloc[i] == 1)
                        
                        if not em_pos:
                            if sn_c:
                                em_pos, de, pe = True, df_b[col_dt].iloc[i], df_b['Close'].iloc[i]
                                min_p, tk_p, st_p = pe, pe*(1+alv), pe*(1-stp)
                        else:
                            min_p = min(min_p, df_b['Low'].iloc[i])
                            bt_al = u_al_rx and (df_b['High'].iloc[i] >= tk_p)
                            bt_st = u_st_rx and (df_b['Low'].iloc[i] <= st_p)
                            rv_st = ur_st_rx and (df_b['ST_Dir'].iloc[i] == -1)
                            rv_dm = ur_dm_rx and (df_b['+DI'].iloc[i] < df_b['-DI'].iloc[i])
                            
                            saiu = False
                            if bt_st: luc, sit, saiu = -(cap_rx*stp), "Stop ❌", True
                            elif bt_al: luc, sit, saiu = cap_rx*alv, "Alvo ✅", True; vit+=1
                            elif rv_st or rv_dm:
                                luc = cap_rx * ((df_b['Close'].iloc[i]/pe)-1)
                                sit, saiu = f"Saída {'ST' if rv_st else 'DMI'} {'✅' if luc>0 else '❌'}", True
                                if luc>0: vit+=1

                            if saiu:
                                trades.append({'Entrada': de.strftime('%d/%m/%y'), 'Saída': df_b[col_dt].iloc[i].strftime('%d/%m/%y'), 'Lucro (R$)': luc, 'Queda Máx': f"{((min_p/pe)-1)*100:.2f}%", 'Situação': sit})
                                em_pos = False

                    if em_pos: st.warning(f"⚠️ OPERAÇÃO ATIVA. Entrada: {de.strftime('%d/%m/%y')} | Atual: {((df_b['Close'].iloc[-1]/pe)-1)*100:.2f}%")
                    if trades:
                        dr = pd.DataFrame(trades)
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Lucro", f"R$ {dr['Lucro (R$)'].sum():,.2f}"); c2.metric("Trades", len(dr)); c3.metric("Acerto", f"{(vit/len(dr)*100):.1f}%")
                        st.dataframe(dr.style.apply(cor_luc, axis=1), use_container_width=True, hide_index=True)
            except Exception as e: st.error(f"Erro: {e}")

# === ABA 3: FUTUROS ===
with ab3:
    cf1, cf2, cf3 = st.columns(3)
    f_sel = cf1.selectbox("Ativo:", ["WINFUT (Índice)", "WDOFUT (Dólar)"])
    f_atv = "WIN1!" if "WIN" in f_sel else "WDO1!"
    f_dir = cf1.selectbox("Direção:", ["Ambas", "Apenas Compra", "Apenas Venda"])
    f_tmp = cf1.selectbox("Tempo F:", ['15m', '60m'])
    
    # CAMPOS PROFIT AQUI TBM
    f_di = cf2.number_input("DI Per F:", value=13)
    c_fa1, c_fa2 = cf2.columns(2)
    f_adx = c_fa1.number_input("ADX Per F:", value=8)
    f_suav = c_fa2.selectbox("Suav. ADX F:", ['rma', 'sma', 'ema'])
    
    c_fs1, c_fs2 = cf2.columns(2)
    f_st = c_fs1.number_input("ST Per F:", value=10)
    f_stm = c_fs2.number_input("ST Mult F:", value=3.0, step=0.1)
    
    f_alv = cf3.number_input("Alvo Pts:", value=300 if "WIN" in f_sel else 10, step=50)
    f_cont = cf3.number_input("Contratos:", value=1)
    f_mlt = cf3.number_input("R$/Ponto:", value=0.20 if "WIN" in f_sel else 10.0)
    f_zer = cf3.checkbox("⏰ Zerar Fim Dia", value=True)
    f_sdm = cf3.checkbox("📉 Saída Rev DMI", value=False)

    if st.button("🚀 Gerar Futuros", type="primary", use_container_width=True):
        with st.spinner('Simulando...'):
            try:
                df_f = tv.get_hist(symbol=f_atv, exchange='BMFBOVESPA', interval=d_int.get(f_tmp), n_bars=10000)
                if df_f is not None:
                    df_f.rename(columns={'open':'Open','high':'High','low':'Low','close':'Close'}, inplace=True)
                    df_f = ind_trend(df_f, f_di, f_adx, f_adx, f_st, f_stm, f_suav)
                    trd, p, vit, c_dt = [], 0, 0, df_f.reset_index().columns[0]
                    df_b = df_f.reset_index()

                    for i in range(1, len(df_b)):
                        dt_h, dt_o = df_b[c_dt].iloc[i], df_b[c_dt].iloc[i-1]
                        
                        # Gatilhos
                        c_c = (df_b['ADX_P'].iloc[i] <= df_b['-DI_P'].iloc[i]) and (df_b['ADX'].iloc[i] > df_b['-DI'].iloc[i])
                        sn_c = c_c and (df_b['+DI'].iloc[i] > df_b['-DI'].iloc[i]) and (df_b['ST_Dir'].iloc[i] == 1)
                        
                        c_v = (df_b['ADX_P'].iloc[i] <= df_b['+DI_P'].iloc[i]) and (df_b['ADX'].iloc[i] > df_b['+DI'].iloc[i])
                        sn_v = c_v and (df_b['-DI'].iloc[i] > df_b['+DI'].iloc[i]) and (df_b['ST_Dir'].iloc[i] == -1)

                        if p != 0 and f_zer and dt_h.date() != dt_o.date():
                            pts = (df_b['Close'].iloc[i-1] - pe) if p==1 else (pe - df_b['Close'].iloc[i-1])
                            lc = pts * f_cont * f_mlt
                            trd.append({'E': de.strftime('%d/%m %H:%M'), 'S': dt_o.strftime('%d/%m %H:%M'), 'T': 'Compra' if p==1 else 'Venda', 'P': pts, 'R$': lc, 'St': 'Zerad'})
                            vit += 1 if lc>0 else 0; p = 0

                        if p == 1: 
                            if df_b['High'].iloc[i] >= tk:
                                trd.append({'E': de.strftime('%d/%m %H:%M'), 'S': dt_h.strftime('%d/%m %H:%M'), 'T': 'Compra', 'P': f_alv, 'R$': f_alv*f_cont*f_mlt, 'St': 'Gain ✅'})
                                vit+=1; p=0
                            elif df_b['ST_Dir'].iloc[i] == -1 or (f_sdm and df_b['+DI'].iloc[i] < df_b['-DI'].iloc[i]):
                                pts = df_b['Close'].iloc[i] - pe
                                trd.append({'E': de.strftime('%d/%m %H:%M'), 'S': dt_h.strftime('%d/%m %H:%M'), 'T': 'Compra', 'P': pts, 'R$': pts*f_cont*f_mlt, 'St': 'Rev'})
                                p=0
                        elif p == -1: 
                            if df_b['Low'].iloc[i] <= tk:
                                trd.append({'E': de.strftime('%d/%m %H:%M'), 'S': dt_h.strftime('%d/%m %H:%M'), 'T': 'Venda', 'P': f_alv, 'R$': f_alv*f_cont*f_mlt, 'St': 'Gain ✅'})
                                vit+=1; p=0
                            elif df_b['ST_Dir'].iloc[i] == 1 or (f_sdm and df_b['-DI'].iloc[i] < df_b['+DI'].iloc[i]):
                                pts = pe - df_b['Close'].iloc[i]
                                trd.append({'E': de.strftime('%d/%m %H:%M'), 'S': dt_h.strftime('%d/%m %H:%M'), 'T': 'Venda', 'P': pts, 'R$': pts*f_cont*f_mlt, 'St': 'Rev'})
                                p=0
                        
                        if sn_c and p==0 and f_dir!="Apenas Venda": p, de, pe, tk = 1, dt_h, df_b['Close'].iloc[i], df_b['Close'].iloc[i]+f_alv
                        elif sn_v and p==0 and f_dir!="Apenas Compra": p, -1, dt_h, df_b['Close'].iloc[i], df_b['Close'].iloc[i]-f_alv

                    if trd:
                        dr = pd.DataFrame(trd)
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Lucro", f"R$ {dr['R$'].sum():,.2f}"); c2.metric("Trades", len(dr)); c3.metric("Pontos", f"{dr['P'].sum():.0f}")
                        st.dataframe(dr, use_container_width=True, hide_index=True)
            except Exception as e: st.error(f"Erro: {e}")
