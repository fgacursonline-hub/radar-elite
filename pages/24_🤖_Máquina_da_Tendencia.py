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
    st.error("❌ Arquivo 'config_ativos.py' não encontrado.")
    st.stop()

ativos_para_rastrear = sorted(list(set([a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)])))

st.set_page_config(page_title="Trend Machine", layout="wide", page_icon="🤖")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

@st.cache_resource
def get_tv_connection(): return TvDatafeed()
tv = get_tv_connection()

tradutor_periodo_nome = {'1mo':'1 Mês', '3mo':'3 Meses', '6mo':'6 Meses', '1y':'1 Ano', '2y':'2 Anos', '5y':'5 Anos', 'max':'Máximo'}
tradutor_intervalo = {'15m':Interval.in_15_minute, '60m':Interval.in_1_hour, '1d':Interval.in_daily, '1wk':Interval.in_weekly}

def colorir_lucro(row):
    if 'Resultado Atual' in row and isinstance(row['Resultado Atual'], str) and row['Resultado Atual'].startswith('+'):
        return ['color: #00FF00; font-weight: bold'] * len(row)
    return [''] * len(row)

# ==========================================
# 3. MOTOR MATEMÁTICO: O FRANKENSTEIN DO PROFIT
# ==========================================
def calcular_indicadores_trend(df, di_len=13, adx_len=8, adx_sig=8, st_len=10, st_mult=3.0):
    if df is None or len(df) < 50: return None
    df.index = df.index.tz_localize(None)

    # 1. Calcula APENAS as linhas DI+ e DI- (Verde e Vermelha)
    dmi_df = ta.adx(df['High'], df['Low'], df['Close'], length=di_len, lensig=di_len)
    if dmi_df is None or dmi_df.empty: return None
    df['+DI'] = dmi_df[[col for col in dmi_df.columns if col.startswith('DMP')][0]]
    df['-DI'] = dmi_df[[col for col in dmi_df.columns if col.startswith('DMN')][0]]

    # 2. Calcula APENAS a linha ADX (Preta) com seus próprios parâmetros
    adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=adx_len, lensig=adx_sig)
    df['ADX'] = adx_df[[col for col in adx_df.columns if col.startswith('ADX')][0]]

    # 3. SuperTrend (Idêntico ao Pine Script)
    st_df = ta.supertrend(df['High'], df['Low'], df['Close'], length=st_len, multiplier=st_mult)
    df['ST_Dir'] = st_df[[col for col in st_df.columns if col.startswith('SUPERTd_')][0]]

    # Memórias para o cruzamento exato
    df['ADX_Prev'] = df['ADX'].shift(1)
    df['-DI_Prev'] = df['-DI'].shift(1)
    
    return df.dropna()

st.title("🤖 Máquina de Tendência (ADX + SuperTrend)")
st.info("📊 **Gatilho de Compra:** Ocorre SE o ADX (Preto) cruzar o DI- (Vermelho) para cima HOJE. Se cruzou, valida se DI+ > DI- e ST é Verde.")

aba_padrao, aba_individual, aba_futuros = st.tabs(["📡 Radar Padrão", "🔬 Raio-X Individual", "📉 Raio-X Futuros"])

# ==========================================
# ABA 1: RADAR PADRÃO E ABA 2 JUNTAS (LÓGICA)
# ==========================================
with aba_individual:
    st.subheader("🔬 Análise Detalhada (Aba 2)")
    with st.container(border=True):
        ci1, ci2, ci3, ci4 = st.columns(4)
        with ci1:
            ativo_rx = st.selectbox("Ativo a Testar:", ativos_para_rastrear)
            capital_rx = st.number_input("Capital Base (R$):", value=10000.0, step=1000.0)
        with ci2:
            tempo_rx = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk', '1mo'], index=2)
            periodo_rx = st.selectbox("Período de Estudo:", ['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], index=3)
        with ci3:
            di_len_rx = st.number_input("Período DI (+/-):", min_value=2, value=13)
            c_a1, c_a2 = st.columns(2)
            adx_len_rx = c_a1.number_input("ADX Período:", min_value=2, value=8)
            adx_sig_rx = c_a2.number_input("ADX Suavização:", min_value=2, value=8)
            
            c_s1, c_s2 = st.columns(2)
            st_len_rx = c_s1.number_input("ST Per:", value=10)
            st_mult_rx = c_s2.number_input("ST Mult:", value=3.0, step=0.1)
        with ci4:
            usar_alvo_rx = st.toggle("🎯 Alvo Fixo", value=True)
            lupa_alvo = st.number_input("Alvo (%):", value=15.0, step=0.5, disabled=not usar_alvo_rx)
            usar_stop_rx = st.toggle("🛡️ Stop Fixo", value=False)
            lupa_stop = st.number_input("Stop (%):", value=5.0, step=0.5, disabled=not usar_stop_rx)
            usar_saida_st_rx = st.toggle("📉 Saída Reversão ST", value=True)
            usar_saida_dmi_rx = st.toggle("📉 Saída Reversão DMI", value=False)

    if st.button("🔍 Gerar Raio-X da Máquina", type="primary", use_container_width=True):
        alvo_d, stop_d = lupa_alvo / 100.0, lupa_stop / 100.0

        with st.spinner(f'Calculando matemática para {ativo_rx}...'):
            try:
                exc = 'BITSTAMP' if 'BTC' in ativo_rx else 'BMFBOVESPA'
                df_full = tv.get_hist(symbol=ativo_rx, exchange=exc, interval=tradutor_intervalo.get(tempo_rx), n_bars=5000)
                
                if df_full is not None and len(df_full) > 50:
                    df_full.rename(columns={'open':'Open', 'high':'High', 'low':'Low', 'close':'Close'}, inplace=True)
                    df_full = calcular_indicadores_trend(df_full, di_len_rx, adx_len_rx, adx_sig_rx, st_len_rx, st_mult_rx)
                    
                    data_corte = df_full.index[-1] - pd.DateOffset(months={'1mo':1, '3mo':3, '6mo':6, '1y':12, '2y':24, '5y':60}.get(periodo_rx, 120)) if periodo_rx != 'max' else df_full.index[0]
                    df_b = df_full[df_full.index >= data_corte].copy().reset_index()
                    
                    trades, em_pos, vit, der, pos_atual = [], False, 0, 0, None
                    col_dt = df_b.columns[0]

                    for i in range(1, len(df_b)):
                        # A REGRA EXATA E SIMPLES 
                        cruzou_adx = (df_b['ADX_Prev'].iloc[i] <= df_b['-DI_Prev'].iloc[i]) and (df_b['ADX'].iloc[i] > df_b['-DI'].iloc[i])
                        di_ok = df_b['+DI'].iloc[i] > df_b['-DI'].iloc[i]
                        st_ok = df_b['ST_Dir'].iloc[i] == 1
                        
                        sinal = cruzou_adx and di_ok and st_ok
                        
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
                                lucro, sit, saiu = -(cap * stop_d), "Stop ❌", True; der += 1
                            elif bt_alvo:
                                lucro, sit, saiu = cap * alvo_d, "Alvo ✅", True; vit += 1
                            elif rev_st or rev_dmi:
                                lucro = cap * ((df_b['Close'].iloc[i] / p_ent) - 1)
                                if rev_st: sit = "Saída ST ✅" if lucro > 0 else "Reversão ST ❌"
                                else: sit = "Saída DMI ✅" if lucro > 0 else "Reversão DMI ❌"
                                if lucro > 0: vit += 1 
                                else: der += 1
                                saiu = True

                            if saiu:
                                duracao = (df_b[col_dt].iloc[i] - d_ent).days
                                dd = ((min_na_op / p_ent) - 1) * 100
                                trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': df_b[col_dt].iloc[i].strftime('%d/%m/%Y'), 'Duração': f"{duracao} d", 'Lucro (R$)': lucro, 'Queda Máx': f"{dd:.2f}%", 'Situação': sit})
                                em_pos, pos_atual = False, None

                    if em_pos and pos_atual:
                        st.warning(f"⚠️ OPERAÇÃO EM CURSO: {ativo_rx}")
                        res_pct = ((df_b['Close'].iloc[-1] / pos_atual['PM']) - 1) * 100
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Entrada", pos_atual['Data'].strftime('%d/%m/%Y'))
                        c2.metric("Preço", f"R$ {pos_atual['PM']:.2f}")
                        c3.metric("Atual", f"{res_pct:.2f}%")

                    if trades:
                        df_res = pd.DataFrame(trades)
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Lucro Total", f"R$ {df_res['Lucro (R$)'].sum():,.2f}")
                        m2.metric("Operações", len(df_res))
                        m3.metric("Taxa Acerto", f"{(vit / len(df_res) * 100):.1f}%")
                        st.dataframe(df_res, use_container_width=True, hide_index=True)
                    else: st.info("Nenhum trade finalizado.")
            except Exception as e: st.error(f"Erro: {e}")

# ==========================================
# ABA 3: RAIO-X FUTUROS
# ==========================================
with aba_futuros:
    st.subheader("📉 Raio-X Mercado Futuro")
    cf1, cf2, cf3 = st.columns(3)
    with cf1:
        f_selecionado = st.selectbox("Selecione o Ativo:", ["WINFUT (Mini Índice)", "WDOFUT (Mini Dólar)", "BITCOIN (Cripto)"])
        f_ativo = "WIN1!" if "WIN" in f_selecionado else ("WDO1!" if "WDO" in f_selecionado else "BTCUSD")
        f_dir = st.selectbox("Direção do Trade:", ["Ambas", "Apenas Compra", "Apenas Venda"])
        f_tmp = st.selectbox("Tempo Gráfico F:", ['15m', '60m'])
    with cf2:
        f_di_len = st.number_input("Período DI Fut:", value=13)
        c_f1, c_f2 = st.columns(2)
        f_adx_len = c_f1.number_input("Período ADX Fut:", value=8)
        f_adx_sig = c_f2.number_input("Suav. ADX Fut:", value=8)
        
        c_fs1, c_fs2 = st.columns(2)
        f_st_len = c_fs1.number_input("ST Per Fut:", value=10)
        f_st_mult = c_fs2.number_input("ST Mult Fut:", value=3.0, step=0.1)
    with cf3:
        f_alvo = st.number_input("Alvo (Pontos):", value=300 if "WIN" in f_selecionado else 10, step=50)
        f_contratos = st.number_input("Contratos:", value=1)
        f_multi = st.number_input("R$ por Ponto:", value=0.20 if "WIN" in f_selecionado else 10.0)
        f_zerar = st.checkbox("⏰ Zerar Fim Dia", value=True)
        f_saida_dmi = st.checkbox("📉 Saída Reversão DMI F", value=False)
        btn_fut = st.button("🚀 Gerar Futuros", type="primary", use_container_width=True)

    if btn_fut:
        with st.spinner('Simulando Futuros...'):
            try:
                exc = 'BITSTAMP' if 'BTC' in f_ativo else 'BMFBOVESPA'
                df_full = tv.get_hist(symbol=f_ativo, exchange=exc, interval=tradutor_intervalo.get(f_tmp), n_bars=10000)
                if df_full is not None:
                    df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                    df_full = calcular_indicadores_trend(df_full, f_di_len, f_adx_len, f_adx_sig, f_st_len, f_st_mult)
                    
                    trades, pos, vits = [], 0, 0
                    df_b = df_full.reset_index()
                    col_dt = df_b.columns[0]

                    for i in range(1, len(df_b)):
                        # Lógica Compra
                        c_adx_c = (df_b['ADX_Prev'].iloc[i] <= df_b['-DI_Prev'].iloc[i]) and (df_b['ADX'].iloc[i] > df_b['-DI'].iloc[i])
                        sinal_compra = c_adx_c and (df_b['+DI'].iloc[i] > df_b['-DI'].iloc[i]) and (df_b['ST_Dir'].iloc[i] == 1)
                        
                        # Lógica Venda
                        c_adx_v = (df_b['ADX_Prev'].iloc[i] <= df_b['+DI_Prev'].iloc[i]) and (df_b['ADX'].iloc[i] > df_b['+DI'].iloc[i])
                        sinal_venda = c_adx_v and (df_b['-DI'].iloc[i] > df_b['+DI'].iloc[i]) and (df_b['ST_Dir'].iloc[i] == -1)

                        if pos != 0 and f_zerar and df_b[col_dt].iloc[i].date() != df_b[col_dt].iloc[i-1].date():
                            pts = (df_b['Close'].iloc[i-1] - p_ent) if pos == 1 else (p_ent - df_b['Close'].iloc[i-1])
                            luc = pts * f_contratos * f_multi
                            trades.append({'Entrada': d_ent.strftime('%d/%m %H:%M'), 'Saída': df_b[col_dt].iloc[i-1].strftime('%d/%m %H:%M'), 'Tipo': 'Compra' if pos==1 else 'Venda', 'Pontos': pts, 'Lucro (R$)': luc, 'Status': 'Zerad. Dia'})
                            vits += 1 if luc > 0 else 0; pos = 0

                        if pos == 1: 
                            if df_b['High'].iloc[i] >= take_p:
                                trades.append({'Entrada': d_ent.strftime('%d/%m %H:%M'), 'Saída': df_b[col_dt].iloc[i].strftime('%d/%m %H:%M'), 'Tipo': 'Compra', 'Pontos': f_alvo, 'Lucro (R$)': f_alvo*f_contratos*f_multi, 'Status': 'Gain ✅'})
                                vits += 1; pos = 0
                            elif df_b['ST_Dir'].iloc[i] == -1 or (f_saida_dmi and df_b['+DI'].iloc[i] < df_b['-DI'].iloc[i]):
                                pts = df_b['Close'].iloc[i] - p_ent
                                trades.append({'Entrada': d_ent.strftime('%d/%m %H:%M'), 'Saída': df_b[col_dt].iloc[i].strftime('%d/%m %H:%M'), 'Tipo': 'Compra', 'Pontos': pts, 'Lucro (R$)': pts*f_contratos*f_multi, 'Status': 'Rev.'})
                                pos = 0
                                
                        elif pos == -1: 
                            if df_b['Low'].iloc[i] <= take_p:
                                trades.append({'Entrada': d_ent.strftime('%d/%m %H:%M'), 'Saída': df_b[col_dt].iloc[i].strftime('%d/%m %H:%M'), 'Tipo': 'Venda', 'Pontos': f_alvo, 'Lucro (R$)': f_alvo*f_contratos*f_multi, 'Status': 'Gain ✅'})
                                vits += 1; pos = 0
                            elif df_b['ST_Dir'].iloc[i] == 1 or (f_saida_dmi and df_b['-DI'].iloc[i] < df_b['+DI'].iloc[i]):
                                pts = p_ent - df_b['Close'].iloc[i]
                                trades.append({'Entrada': d_ent.strftime('%d/%m %H:%M'), 'Saída': df_b[col_dt].iloc[i].strftime('%d/%m %H:%M'), 'Tipo': 'Venda', 'Pontos': pts, 'Lucro (R$)': pts*f_contratos*f_multi, 'Status': 'Rev.'})
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
