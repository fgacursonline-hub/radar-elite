import streamlit as st
from tvDatafeed import TvDatafeed, Interval
import pandas as pd
import numpy as np
import warnings
import sys
import os

# Adiciona a pasta principal ao caminho do Python para ele achar o config_ativos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# --- IMPORTAÇÃO CENTRALIZADA ---
from config_ativos import bdrs_elite, ibrx_selecao, pares_elite

warnings.filterwarnings('ignore')

# 1. SEGURANÇA E CONEXÃO
st.set_page_config(page_title="Comparador de Elite", layout="wide")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, inicie sessão na página inicial (Home).")
    st.stop()

@st.cache_resource
def get_tv_connection():
    return TvDatafeed()

tv = get_tv_connection()

tradutor_intervalo = {
    '15m': Interval.in_15_minute, '60m': Interval.in_1_hour,
    '1d': Interval.in_daily, '1wk': Interval.in_weekly
}

# Lista unificada apenas para facilitar menus
lista_b3_pura = sorted(list(set([a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)])))

# 2. INTERFACE
st.title("📊 Comparador de Performance: Prova Real")
tab_geral, tab_inter = st.tabs(["🌎 Comparativo B3", "🇺🇸 Duelo BDR vs Stock + DÓLAR"])

# ABA 1: NACIONAL
with tab_geral:
    st.subheader("⚙️ Configurações B3")
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1: ativos_comp = st.multiselect("Ativos:", options=lista_b3_pura, default=["PETR4", "VALE3"], max_selections=4)
    with c2: tempo_comp = st.selectbox("Tempo:", ['1d', '60m'], key="t_geral")
    with c3: periodo_comp = st.slider("Barras:", 20, 300, 100, key="p_geral")
    
    if st.button("🚀 Gerar Comparativo Nacional", type="primary", use_container_width=True):
        df_final = pd.DataFrame()
        for t in ativos_comp:
            df_at = tv.get_hist(symbol=t, exchange='BMFBOVESPA', interval=tradutor_intervalo[tempo_comp], n_bars=periodo_comp)
            if df_at is not None:
                df_at[t] = ((df_at['close'] / df_at['close'].iloc[0]) - 1) * 100
                if df_final.empty: df_final = df_at[[t]]
                else: df_final = df_final.join(df_at[t], how='inner')
        if not df_final.empty: st.line_chart(df_final)

# ABA 2: INTERNACIONAL COM PROVA REAL E TRADUÇÃO DE DESVIO
with tab_inter:
    st.subheader("⚙️ Duelo BDR vs Stock com Prova Real")
    ci1, ci2, ci3 = st.columns([2, 1, 1])
    with ci1:
        bdr_sel = st.selectbox("Selecione a BDR:", options=sorted(pares_elite.keys()), index=0)
        stock_sel = st.selectbox("Stock correspondente:", options=sorted(set(pares_elite.values())), 
                                index=sorted(set(pares_elite.values())).index(pares_elite[bdr_sel]))
    with ci2: tempo_inter = st.selectbox("Tempo:", ['1d', '60m'], key="t_inter")
    with ci3: periodo_inter = st.slider("Barras:", 20, 300, 100, key="p_inter")

    if st.button("📈 Gerar Análise de Arbitragem", type="primary", use_container_width=True):
        with st.spinner("Sincronizando ativos..."):
            df_bdr = tv.get_hist(symbol=bdr_sel, exchange='BMFBOVESPA', interval=tradutor_intervalo[tempo_inter], n_bars=periodo_inter)
            df_stock = tv.get_hist(symbol=stock_sel, exchange='NYSE', interval=tradutor_intervalo[tempo_inter], n_bars=periodo_inter)
            if df_stock is None: df_stock = tv.get_hist(symbol=stock_sel, exchange='NASDAQ', interval=tradutor_intervalo[tempo_inter], n_bars=periodo_inter)
            df_dolar = tv.get_hist(symbol='USDBRL', exchange='FX_IDC', interval=tradutor_intervalo[tempo_inter], n_bars=periodo_inter)

            if all(v is not None for v in [df_bdr, df_stock, df_dolar]):
                for df in [df_bdr, df_stock, df_dolar]:
                    df.index = pd.to_datetime(df.index).tz_localize(None)
                    if tempo_inter == '1d': df.index = df.index.normalize()

                df_bdr[bdr_sel] = ((df_bdr['close'] / df_bdr['close'].iloc[0]) - 1) * 100
                df_stock[stock_sel] = ((df_stock['close'] / df_stock['close'].iloc[0]) - 1) * 100
                df_dolar['DÓLAR'] = ((df_dolar['close'] / df_dolar['close'].iloc[0]) - 1) * 100

                df_prova = pd.merge(df_bdr[[bdr_sel]], df_stock[[stock_sel]], left_index=True, right_index=True, how='inner')
                df_prova = pd.merge(df_prova, df_dolar[['DÓLAR']], left_index=True, right_index=True, how='inner')

                if not df_prova.empty:
                    st.line_chart(df_prova, use_container_width=True)
                    st.divider()
                    v_bdr, v_stock, v_dolar = df_prova[bdr_sel].iloc[-1], df_prova[stock_sel].iloc[-1], df_prova['DÓLAR'].iloc[-1]
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric(f"Retorno {bdr_sel}", f"{v_bdr:.2f}%")
                    c2.metric(f"Retorno {stock_sel}", f"{v_stock:.2f}%")
                    c3.metric("Variação Dólar", f"{v_dolar:.2f}%")

                    ret_teo = v_stock + v_dolar
                    desvio = v_bdr - ret_teo
                    st.subheader("🔬 Veredito da Arbitragem")
                    if desvio < -1.0:
                        st.warning(f"⚠️ DESVIO DE {desvio:.2f}% DETECTADO")
                        st.markdown(f"**ANÁLISE:** A BDR **{bdr_sel}** está **ATRASADA** em relação à Stock + Dólar.")
                    elif desvio > 1.0:
                        st.error(f"🚨 DESVIO DE +{desvio:.2f}% DETECTADO")
                        st.markdown(f"**ANÁLISE:** A BDR **{bdr_sel}** está **MAIS CARA** que a paridade.")
                    else:
                        st.success(f"✅ EFICIÊNCIA: Desvio de {desvio:.2f}%")
                else:
                    st.error("Erro na sincronização.")
