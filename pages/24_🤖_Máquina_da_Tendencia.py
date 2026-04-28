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
# 2. CONFIGURAÇÃO DA PÁGINA E TVDATAFEED
# ==========================================
st.set_page_config(page_title="Trend Machine", layout="wide", page_icon="🤖")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
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

def colorir_lucro(row):
    if 'Resultado Atual' in row and isinstance(row['Resultado Atual'], str) and row['Resultado Atual'].startswith('+'):
        return ['color: #00FF00; font-weight: bold'] * len(row)
    return [''] * len(row)

# ==========================================
# 3. MOTOR MATEMÁTICO PURO (O SIMPLES QUE FUNCIONA)
# ==========================================
def calcular_indicadores_trend(df, adx_len=14, st_len=10, st_mult=3.0):
    if df is None or len(df) < max(adx_len, st_len) * 2:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = df.index.tz_localize(None)

    # 1. ADX e DMI (A Base de Tudo)
    adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=adx_len)
    if adx_df is None or adx_df.empty: return None

    df['ADX'] = adx_df[[col for col in adx_df.columns if col.startswith('ADX')][0]]
    df['+DI'] = adx_df[[col for col in adx_df.columns if col.startswith('DMP')][0]]
    df['-DI'] = adx_df[[col for col in adx_df.columns if col.startswith('DMN')][0]]

    # 2. SuperTrend (Com base no Pine Script)
    st_df = ta.supertrend(df['High'], df['Low'], df['Close'], length=st_len, multiplier=st_mult)
    if st_df is None or st_df.empty: return None

    df['ST_Dir'] = st_df[[col for col in st_df.columns if col.startswith('SUPERTd_')][0]]

    # 3. Criar a "memória de ontem" essencial para ver o cruzamento de linhas
    df['ADX_Prev'] = df['ADX'].shift(1)
    df['-DI_Prev'] = df['-DI'].shift(1)
    df['+DI_Prev'] = df['+DI'].shift(1)

    return df.dropna()

st.title("🤖 Máquina de Tendência (ADX + SuperTrend)")
st.info("📊 **Estratégia Simples:** \n\n🟢 **Gatilho de Compra:** SÓ compra se o ADX (Preto) cruzou o DI- (Vermelho) para cima HOJE. Se cruzou hoje, checa se DI+ está acima de DI- e se SuperTrend é verde.")

aba_padrao, aba_individual, aba_futuros = st.tabs(["📡 Radar Padrão", "🔬 Raio-X Individual", "📉 Raio-X Futuros"])
# ==========================================
# ABA 1: RADAR PADRÃO
# ==========================================
with aba_padrao:
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            lista_tr = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"], key="tr_lista")
            capital_tr = st.number_input("Capital por Trade (R$):", value=10000.0, step=1000.0, key="tr_cap")
        with c2:
            tempo_tr = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk', '1mo'], index=2, key="tr_tmp")
            periodo_tr = st.selectbox("Histórico:", ['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], index=3, key="tr_per")
        with c3:
            adx_len = st.number_input("Período ADX:", value=14, step=1, key="tr_adx_len")
            c_st1, c_st2 = st.columns(2)
            st_len = c_st1.number_input("ST Período:", value=10, step=1, key="tr_st_len")
            st_mult = c_st2.number_input("ST Mult:", value=3.0, step=0.1, key="tr_st_mult")
        with c4:
            usar_alvo_g = st.toggle("🎯 Alvo Fixo", value=True, key="tg_alvo_g")
            alvo_g = st.number_input("Alvo (%):", value=15.0, step=1.0, disabled=not usar_alvo_g, key="val_alvo_g")
            usar_stop_g = st.toggle("🛡️ Stop Loss", value=False, key="tg_stop_g")
            stop_g = st.number_input("Stop Loss (%):", value=5.0, step=1.0, disabled=not usar_stop_g, key="val_stop_g")
            usar_saida_st_g = st.toggle("📉 Saída Reversão (ST)", value=True, key="tg_st_g")
            usar_saida_dmi_g = st.toggle("📉 Saída Reversão DMI", value=False, key="tg_dmi_g")

    if st.button("🚀 Iniciar Varredura", type="primary", use_container_width=True, key="tr_btn"):
        intervalo_tv = tradutor_intervalo.get(tempo_tr, Interval.in_daily)
        ativos_tr = bdrs_elite if lista_tr == "BDRs Elite" else ibrx_selecao if lista_tr == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        ativos_tr = sorted(list(set([a.replace('.SA', '') for a in ativos_tr])))
        
        ls_sinais, ls_abertos, ls_resumo = [], [], []
        p_bar = st.progress(0); s_text = st.empty()

        for idx, ativo in enumerate(ativos_tr):
            s_text.text(f"🔍 Medindo {ativo} ({idx+1}/{len(ativos_tr)})")
            p_bar.progress((idx + 1) / len(ativos_tr))

            try:
                df_full = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=5000)
                if df_full is None or len(df_full) < 50: continue
                df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                
                df_full = calcular_indicadores_trend(df_full, adx_len, st_len, st_mult)
                if df_full is None: continue

                data_corte = df_full.index[-1] - pd.DateOffset(months={'1mo': 1, '3mo': 3, '6mo': 6, '1y': 12, '2y': 24, '5y': 60}.get(periodo_tr, 120)) if periodo_tr != 'max' else df_full.index[0]
                df_back = df_full[df_full.index >= data_corte].copy().reset_index()
                
                trades, em_pos = [], False
                col_data = df_back.columns[0]
                alvo_d, stop_d = alvo_g / 100.0, stop_g / 100.0

                for i in range(1, len(df_back)):
                    # A REGRA PURA E SIMPLES
                    # Gatilho: ADX Cruzou DI- para cima HOJE?
                    cruzou_agora = (df_back['ADX_Prev'].iloc[i] <= df_back['-DI_Prev'].iloc[i]) and (df_back['ADX'].iloc[i] > df_back['-DI'].iloc[i])
                    
                    # Filtros de Hoje
                    di_verde_por_cima = df_back['+DI'].iloc[i] > df_back['-DI'].iloc[i]
                    st_verde = df_back['ST_Dir'].iloc[i] == 1
                    
                    sinal_compra = cruzou_agora and di_verde_por_cima and st_verde

                    if em_pos:
                        if df_back['Low'].iloc[i] < min_price_in_trade: min_price_in_trade = df_back['Low'].iloc[i]
                        
                        bt_alvo = usar_alvo_g and (df_back['High'].iloc[i] >= take_profit)
                        bt_stop = usar_stop_g and (df_back['Low'].iloc[i] <= stop_price)
                        rev_st = usar_saida_st_g and (df_back['ST_Dir'].iloc[i] == -1)
                        rev_dmi = usar_saida_dmi_g and (df_back['+DI'].iloc[i] < df_back['-DI'].iloc[i])
                        
                        if bt_stop:
                            trades.append({'Lucro': -(float(capital_tr) * stop_d), 'DD': ((min_price_in_trade / p_ent) - 1) * 100, 'Motivo': 'Stop ❌'})
                            em_pos = False; continue
                        elif bt_alvo:
                            trades.append({'Lucro': float(capital_tr) * alvo_d, 'DD': ((min_price_in_trade / p_ent) - 1) * 100, 'Motivo': 'Alvo ✅'})
                            em_pos = False; continue
                        elif rev_st or rev_dmi:
                            lucro = float(capital_tr) * ((df_back['Close'].iloc[i] / p_ent) - 1)
                            motivo = 'Saída ST' if rev_st else 'Saída DMI'
                            trades.append({'Lucro': lucro, 'DD': ((min_price_in_trade / p_ent) - 1) * 100, 'Motivo': f"{motivo} {'✅' if lucro > 0 else '❌'}"})
                            em_pos = False; continue

                    if sinal_compra and not em_pos:
                        em_pos, d_ent, p_ent = True, df_back[col_data].iloc[i], df_back['Close'].iloc[i]
                        min_price_in_trade, take_profit, stop_price = p_ent, p_ent * (1 + alvo_d), p_ent * (1 - stop_d)

                if em_pos:
                    res = ((df_back['Close'].iloc[-1] / p_ent) - 1) * 100
                    dd = ((min_price_in_trade / p_ent) - 1) * 100
                    ls_abertos.append({'Ativo': ativo, 'Entrada': d_ent.strftime('%d/%m/%Y'), 'Dias': (df_back[col_data].iloc[-1] - d_ent).days, 'PM': f"R$ {p_ent:.2f}", 'Atual': f"R$ {df_back['Close'].iloc[-1]:.2f}", 'DD': f"{dd:.2f}%", 'Res': f"+{res:.2f}%" if res > 0 else f"{res:.2f}%"})
                else:
                    hoje = df_full.iloc[-1]
                    hoje_cruzou = (hoje['ADX_Prev'] <= hoje['-DI_Prev']) and (hoje['ADX'] > hoje['-DI'])
                    sinal_hoje = hoje_cruzou and (hoje['+DI'] > hoje['-DI']) and (hoje['ST_Dir'] == 1)
                    if sinal_hoje:
                        ls_sinais.append({'Ativo': ativo, 'Preço': f"R$ {hoje['Close']:.2f}", 'ADX': f"{hoje['ADX']:.1f}"})

                if trades:
                    df_t = pd.DataFrame(trades)
                    ls_resumo.append({'Ativo': ativo, 'Trades': len(df_t), 'Pior Queda': f"{df_t['DD'].min():.2f}%", 'Lucro R$': df_t['Lucro'].sum()})
            except Exception as e: pass
            time.sleep(0.05)

        s_text.empty(); p_bar.empty()
        st.subheader("🚀 Sinais Hoje"); st.dataframe(pd.DataFrame(ls_sinais), hide_index=True)
        st.subheader("⏳ Abertos"); st.dataframe(pd.DataFrame(ls_abertos), hide_index=True)
        st.subheader("📊 Histórico"); st.dataframe(pd.DataFrame(ls_resumo), hide_index=True)
        # ==========================================
# ABA 2: RAIO-X INDIVIDUAL 
# ==========================================
with aba_individual:
    st.subheader("🔬 Análise Detalhada (Aba 2)")
    with st.container(border=True):
        ci1, ci2, ci3, ci4 = st.columns(4)
        with ci1:
            ativo_rx = st.selectbox("Ativo:", ativos_para_rastrear, key="i_tr_ativo")
            capital_rx = st.number_input("Capital (R$):", value=10000.0, step=1000.0, key="i_tr_cap")
        with ci2:
            tempo_rx = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk', '1mo'], index=2, key="i_tr_tmp")
            periodo_rx = st.selectbox("Histórico:", ['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], index=3, key="i_tr_per")
        with ci3:
            lupa_adx_len = st.number_input("Período ADX:", value=14, key="i_tr_adxlen")
            c_rx_st1, c_rx_st2 = st.columns(2)
            lupa_st_len = c_rx_st1.number_input("ST Per:", value=10, key="i_tr_stlen")
            lupa_st_mult = c_rx_st2.number_input("ST Mult:", value=3.0, step=0.1, key="i_tr_stmult")
        with ci4:
            usar_alvo_rx = st.toggle("🎯 Alvo Fixo", value=True, key="tg_alvo_rx")
            lupa_alvo = st.number_input("Alvo (%):", value=15.0, step=0.5, disabled=not usar_alvo_rx, key="i_tr_alvo")
            usar_stop_rx = st.toggle("🛡️ Stop Fixo", value=False, key="tg_stop_rx")
            lupa_stop = st.number_input("Stop (%):", value=5.0, step=0.5, disabled=not usar_stop_rx, key="i_tr_stop")
            usar_saida_st_rx = st.toggle("📉 Saída Reversão ST", value=True, key="tg_st_rx")
            usar_saida_dmi_rx = st.toggle("📉 Saída Reversão DMI", value=False, key="tg_dmi_rx")

    if st.button("🔍 Gerar Raio-X", type="primary", use_container_width=True, key="i_tr_btn"):
        intervalo_tv = tradutor_intervalo.get(tempo_rx, Interval.in_daily)
        alvo_d, stop_d = lupa_alvo / 100.0, lupa_stop / 100.0

        with st.spinner(f'Calculando {ativo_rx}...'):
            try:
                exc = 'BITSTAMP' if 'BTC' in ativo_rx else 'BMFBOVESPA'
                df_full = tv.get_hist(symbol=ativo_rx, exchange=exc, interval=intervalo_tv, n_bars=5000)
                if df_full is not None and len(df_full) > 50:
                    df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                    df_full = calcular_indicadores_trend(df_full, lupa_adx_len, lupa_st_len, lupa_st_mult)
                    
                    data_corte = df_full.index[-1] - pd.DateOffset(months={'1mo': 1, '3mo': 3, '6mo': 6, '1y': 12, '2y': 24, '5y': 60}.get(periodo_rx, 120)) if periodo_rx != 'max' else df_full.index[0]
                    df_b = df_full[df_full.index >= data_corte].copy().reset_index()
                    
                    trades, em_pos, vitorias = [], False, 0
                    col_dt = df_b.columns[0]

                    for i in range(1, len(df_b)):
                        # A REGRA PURA E SIMPLES (Aba 2)
                        cruzou_agora = (df_b['ADX_Prev'].iloc[i] <= df_b['-DI_Prev'].iloc[i]) and (df_b['ADX'].iloc[i] > df_b['-DI'].iloc[i])
                        di_verde_por_cima = df_b['+DI'].iloc[i] > df_b['-DI'].iloc[i]
                        st_verde = df_b['ST_Dir'].iloc[i] == 1
                        
                        sinal = cruzou_agora and di_verde_por_cima and st_verde
                        
                        if not em_pos:
                            if sinal:
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
                            
                            saiu = False
                            if bt_stop:
                                lucro, sit, saiu = -(cap * stop_d), "Stop ❌", True
                            elif bt_alvo:
                                lucro, sit, saiu = cap * alvo_d, "Alvo ✅", True; vitorias += 1
                            elif rev_st or rev_dmi:
                                lucro = cap * ((df_b['Close'].iloc[i] / p_ent) - 1)
                                se_st = "ST" if rev_st else "DMI"
                                sit, saiu = f"Saída {se_st} ✅" if lucro > 0 else f"Reversão {se_st} ❌", True
                                if lucro > 0: vitorias += 1

                            if saiu:
                                duracao = (df_b[col_dt].iloc[i] - d_ent).days
                                dd = ((min_na_op / p_ent) - 1) * 100
                                trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': df_b[col_dt].iloc[i].strftime('%d/%m/%Y'), 'Duração': f"{duracao} d", 'Lucro (R$)': lucro, 'Queda Máx': f"{dd:.2f}%", 'Situação': sit})
                                em_pos, pos_atual = False, None

                    if em_pos and pos_atual:
                        st.warning(f"⚠️ OPERAÇÃO EM CURSO: {ativo_rx}")
                        c1, c2 = st.columns(2)
                        c1.metric("Entrada", pos_atual['Data'].strftime('%d/%m/%Y'))
                        c2.metric("Preço", f"R$ {pos_atual['PM']:.2f}")

                    if trades:
                        df_res = pd.DataFrame(trades)
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Lucro Total", f"R$ {df_res['Lucro (R$)'].sum():,.2f}")
                        m2.metric("Operações", len(df_res))
                        m3.metric("Taxa de Acerto", f"{(vitorias / len(df_res) * 100):.1f}%")
                        st.dataframe(df_res, use_container_width=True, hide_index=True)
            except Exception as e: st.error(f"Erro: {e}")

# ==========================================
# ABA 3: RAIO-X FUTUROS (DAY TRADE / WIN e WDO)
# ==========================================
with aba_futuros:
    st.subheader("📉 Raio-X Mercado Futuro (Aba 3)")
    cf1, cf2, cf3 = st.columns(3)
    with cf1:
        f_ativo = st.selectbox("Ativo:", ["WINFUT (Mini Índice)", "WDOFUT (Mini Dólar)"])
        f_sym = "WIN1!" if "WIN" in f_ativo else "WDO1!"
        f_dir = st.selectbox("Direção:", ["Ambas", "Apenas Compra", "Apenas Venda"])
        f_tmp = st.selectbox("Tempo Gráfico:", ['15m', '60m'])
    with cf2:
        f_adx_len = st.number_input("Período ADX F:", value=14)
        f_st_len = st.number_input("Período ST F:", value=10)
        f_st_mult = st.number_input("Mult ST F:", value=3.0, step=0.1)
    with cf3:
        f_alvo = st.number_input("Alvo Pts:", value=300 if "WIN" in f_sym else 10, step=50)
        f_cont = st.number_input("Contratos:", value=1)
        f_multi = st.number_input("R$ Ponto:", value=0.20 if "WIN" in f_sym else 10.0)
        f_zerar = st.checkbox("⏰ Zerar Fim Dia", value=True)
        f_sdmi = st.checkbox("📉 Saída Reversão DMI Fut", value=False)
        btn_fut = st.button("🚀 Gerar Futuros", type="primary", use_container_width=True)

    if btn_fut:
        intervalo_tv = tradutor_intervalo.get(f_tmp, Interval.in_15_minute)
        with st.spinner('Simulando Futuros...'):
            try:
                df_full = tv.get_hist(symbol=f_sym, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=10000)
                if df_full is not None:
                    df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                    df_full = calcular_indicadores_trend(df_full, f_adx_len, f_st_len, f_st_mult)
                    
                    trades, pos, vits = [], 0, 0
                    df_b = df_full.reset_index()
                    col_dt = df_b.columns[0]

                    for i in range(1, len(df_b)):
                        # A REGRA PURA E SIMPLES (Aba 3)
                        # Compra
                        cruz_compra = (df_b['ADX_Prev'].iloc[i] <= df_b['-DI_Prev'].iloc[i]) and (df_b['ADX'].iloc[i] > df_b['-DI'].iloc[i])
                        di_c_ok = df_b['+DI'].iloc[i] > df_b['-DI'].iloc[i]
                        st_c_ok = df_b['ST_Dir'].iloc[i] == 1
                        sinal_compra = cruz_compra and di_c_ok and st_c_ok
                        
                        # Venda
                        cruz_venda = (df_b['ADX_Prev'].iloc[i] <= df_b['+DI_Prev'].iloc[i]) and (df_b['ADX'].iloc[i] > df_b['+DI'].iloc[i])
                        di_v_ok = df_b['-DI'].iloc[i] > df_b['+DI'].iloc[i]
                        st_v_ok = df_b['ST_Dir'].iloc[i] == -1
                        sinal_venda = cruz_venda and di_v_ok and st_v_ok

                        if pos != 0 and f_zerar and df_b[col_dt].iloc[i].date() != df_b[col_dt].iloc[i-1].date():
                            pts = (df_b['Close'].iloc[i-1] - p_ent) if pos == 1 else (p_ent - df_b['Close'].iloc[i-1])
                            luc = pts * f_cont * f_multi
                            trades.append({'Entrada': d_ent.strftime('%d/%m %H:%M'), 'Saída': df_b[col_dt].iloc[i-1].strftime('%d/%m %H:%M'), 'Tipo': 'Compra' if pos == 1 else 'Venda', 'Pontos': pts, 'Lucro (R$)': luc, 'Status': 'Zerad. Dia'})
                            vits += 1 if luc > 0 else 0; pos = 0

                        if pos == 1: 
                            if df_b['High'].iloc[i] >= take_p:
                                trades.append({'Entrada': d_ent.strftime('%d/%m %H:%M'), 'Saída': df_b[col_dt].iloc[i].strftime('%d/%m %H:%M'), 'Tipo': 'Compra', 'Pontos': f_alvo, 'Lucro (R$)': f_alvo * f_cont * f_multi, 'Status': 'Gain ✅'})
                                vits += 1; pos = 0
                            elif df_b['ST_Dir'].iloc[i] == -1 or (f_sdmi and df_b['+DI'].iloc[i] < df_b['-DI'].iloc[i]):
                                pts = df_b['Close'].iloc[i] - p_ent
                                trades.append({'Entrada': d_ent.strftime('%d/%m %H:%M'), 'Saída': df_b[col_dt].iloc[i].strftime('%d/%m %H:%M'), 'Tipo': 'Compra', 'Pontos': pts, 'Lucro (R$)': pts * f_cont * f_multi, 'Status': 'Rev.'})
                                pos = 0
                                
                        elif pos == -1: 
                            if df_b['Low'].iloc[i] <= take_p:
                                trades.append({'Entrada': d_ent.strftime('%d/%m %H:%M'), 'Saída': df_b[col_dt].iloc[i].strftime('%d/%m %H:%M'), 'Tipo': 'Venda', 'Pontos': f_alvo, 'Lucro (R$)': f_alvo * f_cont * f_multi, 'Status': 'Gain ✅'})
                                vits += 1; pos = 0
                            elif df_b['ST_Dir'].iloc[i] == 1 or (f_sdmi and df_b['-DI'].iloc[i] < df_b['+DI'].iloc[i]):
                                pts = p_ent - df_b['Close'].iloc[i]
                                trades.append({'Entrada': d_ent.strftime('%d/%m %H:%M'), 'Saída': df_b[col_dt].iloc[i].strftime('%d/%m %H:%M'), 'Tipo': 'Venda', 'Pontos': pts, 'Lucro (R$)': pts * f_cont * f_multi, 'Status': 'Rev.'})
                                pos = 0
                        
                        if sinal_compra and pos == 0 and f_dir != "Apenas Venda":
                            pos, d_ent, p_ent = 1, df_b[col_dt].iloc[i], df_b['Close'].iloc[i]
                            take_p = p_ent + f_alvo
                        elif sinal_venda and pos == 0 and f_dir != "Apenas Compra":
                            pos, d_ent, p_ent = -1, df_b[col_dt].iloc[i], df_b['Close'].iloc[i]
                            take_p = p_ent - f_alvo

                    if trades:
                        df_res = pd.DataFrame(trades)
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Lucro Total", f"R$ {df_res['Lucro (R$)'].sum():,.2f}")
                        m2.metric("Operações", len(df_res))
                        m3.metric("Taxa Acerto", f"{(vits/len(df_res)*100):.1f}%")
                        st.dataframe(df_res, use_container_width=True, hide_index=True)
            except Exception as e: st.error(f"Erro: {e}")
