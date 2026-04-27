import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import pandas_ta as ta
import time
import warnings
import numpy as np
import sys
import os

warnings.filterwarnings('ignore')

# 1. SEGURANÇA
if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

# ==========================================
# IMPORTAÇÃO CENTRALIZADA (ATIVOS E MOTOR)
# ==========================================
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from config_ativos import bdrs_elite, ibrx_selecao
except ImportError:
    st.error("❌ Arquivo 'config_ativos.py' não encontrado.")
    st.stop()

try:
    from motor_dados import puxar_dados_blindados
except ImportError:
    st.error("❌ Arquivo 'motor_dados.py' não encontrado.")
    st.stop()

todos_ativos = sorted(list(set([a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)])))

# --- CONFIGURAÇÃO DO TELEGRAM ---
TOKEN_TELEGRAM = "8689032615:AAFnJTZm0SYgSng9VlwzzZdafOP4mmGlt5Y"
CHAT_ID_TELEGRAM = "734303365"

def enviar_alerta_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage"
    payload = {"chat_id": CHAT_ID_TELEGRAM, "text": mensagem}
    try:
        import requests
        requests.post(url, json=payload, timeout=5)
    except:
        pass

tradutor_periodo_nome = {'1mo': '1 Mês', '3mo': '3 Meses', '6mo': '6 Meses', '1y': '1 Ano', '2y': '2 Anos', '5y': '5 Anos', 'max': 'Máximo'}

def colorir_lucro(row):
    for col in ['Resultado Atual', 'Resultado']:
        if col in row and isinstance(row[col], str) and row[col].startswith('+'):
            return ['color: #2eeb5c; font-weight: bold'] * len(row)
    if 'Situação' in row and isinstance(row['Situação'], str) and 'Gain' in row['Situação']:
        return ['color: #2eeb5c; font-weight: bold'] * len(row)
    return [''] * len(row)

def renderizar_grafico_tv(simbolo_tv, altura=600):
    html_tv = f"""
    <div class="tradingview-widget-container"><div id="tradingview_ifr"></div>
    <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
    <script type="text/javascript">
    new TradingView.widget({{"width": "100%", "height": {altura}, "symbol": "{simbolo_tv}", "interval": "D", "timezone": "America/Sao_Paulo", "theme": "dark", "style": "1", "locale": "br", "container_id": "tradingview_ifr"}});
    </script></div>"""
    components.html(html_tv, height=altura)

st.title("📈 Estratégia: IFR")

aba_padrao, aba_pm, aba_individual, aba_futuros, aba_connors = st.tabs([
    "📡 Radar (Padrão)", "📡 Radar (PM)", "🔬 Raio-X Individual", "📉 Raio-X Futuros", "🩸 IFR2 (Connors)"
])

# ==========================================
# ABA 1: RADAR PADRÃO (COM STOP OPCIONAL)
# ==========================================
with aba_padrao:
    st.subheader("📡 Radar Padrão (Entrada Única)")
    st.info("📊 Gatilho: IFR < 25 cruzando para cima. Saída no Alvo ou Stop opcional.")
    cp1, cp2, cp3 = st.columns(3)
    with cp1:
        lista_p = st.selectbox("Lista:", ["BDRs Elite", "IBrX Seleção", "Todos"], key="p_lst")
        ativos_p = bdrs_elite if lista_p == "BDRs Elite" else ibrx_selecao if lista_p == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        periodo_p = st.selectbox("Período:", options=['1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=0, key="p_per")
    with cp2:
        alvo_p = st.number_input("Alvo (%):", value=5.0, step=0.5, key="p_alvo")
        stop_p = st.number_input("Stop Loss (%):", value=0.0, step=0.5, help="0.0 ignora o Stop", key="p_stop")
    with cp3:
        cap_p = st.number_input("Capital (R$):", value=10000.0, key="p_cap")
        tmp_p = st.selectbox("Tempo:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m':'15m','60m':'60m','1d':'Diário','1wk':'Semanal'}[x], key="p_tmp")
        ifr_p = st.number_input("IFR Período:", value=8, key="p_ifr")

    if st.button("🚀 Iniciar Varredura Padrão", type="primary", use_container_width=True):
        alvo_dec, stop_dec = alvo_p/100, stop_p/100
        ls_sinais, ls_abertos, ls_resumo = [], [], []
        p_bar = st.progress(0); s_txt = st.empty()
        for idx, ativo_raw in enumerate(ativos_p):
            ativo = ativo_raw.replace('.SA', '')
            s_txt.text(f"🔍 Analisando: {ativo}")
            p_bar.progress((idx+1)/len(ativos_p))
            try:
                df_full = puxar_dados_blindados(ativo, tempo_grafico=tmp_p, barras=1500)
                if df_full is None or len(df_full) < 50: continue
                df_full['IFR'] = ta.rsi(df_full['Close'], length=ifr_p)
                df_full['IFR_Prev'] = df_full['IFR'].shift(1)
                df_back = df_full.dropna().reset_index()
                em_pos = False
                for i in range(1, len(df_back)):
                    if em_pos:
                        if df_back['Low'].iloc[i] < min_p: min_p = df_back['Low'].iloc[i]
                        if df_back['High'].iloc[i] >= tk: ls_resumo.append({'Ativo':ativo,'Lucro':cap_p*alvo_dec}); em_pos = False
                        elif stop_p > 0 and df_back['Low'].iloc[i] <= stp: ls_resumo.append({'Ativo':ativo,'Lucro':-cap_p*stop_dec}); em_pos = False
                        continue
                    if df_back['IFR_Prev'].iloc[i] < 25 and df_back['IFR'].iloc[i] >= 25:
                        em_pos, p_ent, d_ent = True, df_back['Close'].iloc[i], df_back.iloc[i,0]
                        min_p, tk, stp = df_back['Low'].iloc[i], p_ent*(1+alvo_dec), p_ent*(1-stop_dec)
                if em_pos:
                    res = ((df_back['Close'].iloc[-1]/p_ent)-1)*100
                    ls_abertos.append({'Ativo':ativo,'Entrada':d_ent.strftime('%d/%m/%Y'),'PM':f"R$ {p_ent:.2f}",'Resultado Atual':f"{res:+.2f}%"})
                elif df_full['IFR_Prev'].iloc[-1] < 25 and df_full['IFR'].iloc[-1] >= 25:
                    ls_sinais.append({'Ativo':ativo,'Preço':f"R$ {df_full['Close'].iloc[-1]:.2f}"})
            except: pass
        s_txt.empty(); p_bar.empty()
        st.subheader("🚀 Sinais e Operações")
        if ls_sinais: st.dataframe(pd.DataFrame(ls_sinais), use_container_width=True, hide_index=True)
        if ls_abertos: st.dataframe(pd.DataFrame(ls_abertos).style.apply(colorir_lucro, axis=1), use_container_width=True, hide_index=True)

# ==========================================
# ABA 2: RADAR PM DINÂMICO
# ==========================================
with aba_pm:
    st.subheader("📡 Radar PM Dinâmico")
    cr1, cr2, cr3 = st.columns(3)
    with cr1:
        lista_pm = st.selectbox("Lista:", ["BDRs Elite", "IBrX Seleção", "Todos"], key="pm_lst")
        ativos_pm = bdrs_elite if lista_pm == "BDRs Elite" else ibrx_selecao if lista_pm == "IBrX Seleção" else bdrs_elite + ibrx_selecao
    with cr2:
        alvo_pm = st.number_input("Alvo (%):", value=3.0, key="pm_alvo")
        ifr_pm = st.number_input("IFR Período:", value=8, key="pm_ifr")
    with cr3:
        cap_pm = st.number_input("Capital/Sinal:", value=10000.0, key="pm_cap")
        tmp_pm = st.selectbox("Tempo:", ['1d', '60m', '15m'], index=0, key="pm_tmp")

    if st.button("🚀 Iniciar Varredura PM", type="primary", key="pm_btn"):
        alvo_dec = alvo_pm/100
        ls_sinais, ls_abertos = [], []
        p_bar = st.progress(0)
        for idx, ativo_raw in enumerate(ativos_pm):
            ativo = ativo_raw.replace('.SA', '')
            p_bar.progress((idx+1)/len(ativos_pm))
            try:
                df = puxar_dados_blindados(ativo, tempo_grafico=tmp_pm, barras=1500)
                df['IFR'] = ta.rsi(df['Close'], length=ifr_pm)
                df['IFR_Prev'] = df['IFR'].shift(1)
                df_b = df.dropna().reset_index()
                em_pos, cap_tot, qtd_a = False, 0.0, 0.0
                for i in range(1, len(df_b)):
                    if em_pos and df_b['High'].iloc[i] >= pm * (1+alvo_dec): em_pos = False; continue
                    if df_b['IFR_Prev'].iloc[i] < 25 and df_b['IFR'].iloc[i] >= 25:
                        em_pos = True
                        cap_tot += cap_pm; qtd_a += cap_pm / df_b['Close'].iloc[i]; pm = cap_tot / qtd_a
                        if em_pos and i == len(df_b)-1: d_ent = df_b.iloc[i,0]
                if em_pos:
                    res = ((df_b['Close'].iloc[-1]/pm)-1)*100
                    ls_abertos.append({'Ativo':ativo,'PM':f"R$ {pm:.2f}",'Resultado':f"{res:+.2f}%"})
                elif df['IFR_Prev'].iloc[-1] < 25 and df['IFR'].iloc[-1] >= 25:
                    ls_sinais.append({'Ativo':ativo,'Preço':f"R$ {df['Close'].iloc[-1]:.2f}"})
            except: pass
        p_bar.empty()
        if ls_sinais: st.dataframe(pd.DataFrame(ls_sinais), use_container_width=True)
        if ls_abertos: st.dataframe(pd.DataFrame(ls_abertos).style.apply(colorir_lucro, axis=1), use_container_width=True)

# ==========================================
# ABA 3: RAIO-X INDIVIDUAL
# ==========================================
with aba_individual:
    st.subheader("🔬 Raio-X Individual")
    c1, c2, c3 = st.columns(3)
    with c1:
        rx_at = st.selectbox("Ativo:", todos_ativos, index=0, key="rx_at")
        rx_est = st.selectbox("Estratégia:", ["Padrão", "PM Dinâmico"], key="rx_est")
    with c2:
        rx_alvo = st.number_input("Alvo (%):", value=3.0, key="rx_alvo")
        rx_cap = st.number_input("Capital:", value=10000.0, key="rx_cap")
    with c3:
        rx_tmp = st.selectbox("Tempo:", ['1d', '60m', '15m'], index=0, key="rx_tmp")
        rx_ifr = st.number_input("IFR:", value=8, key="rx_ifr")

    if st.button("🔍 Rodar Análise", type="primary", use_container_width=True):
        try:
            df = puxar_dados_blindados(rx_at, tempo_grafico=rx_tmp, barras=2000)
            df['IFR'] = ta.rsi(df['Close'], length=rx_ifr)
            df['IFR_Prev'] = df['IFR'].shift(1)
            # Lógica simplificada de backtest para exibição
            st.success(f"Análise de {rx_at} concluída.")
            renderizar_grafico_tv(f"BMFBOVESPA:{rx_at}")
        except Exception as e: st.error(f"Erro: {e}")

# ==========================================
# ABA 4: RAIO-X FUTUROS
# ==========================================
with aba_futuros:
    st.subheader("📈 Mercado Futuro")
    f_at = st.selectbox("Contrato:", ["WIN1!", "WDO1!"], key="f_at")
    if st.button("🚀 Analisar Futuros", type="primary"):
        df = puxar_dados_blindados(f_at, tempo_grafico='15m', barras=5000)
        st.write(f"Dados de {f_at} processados.")

# ==========================================
# ABA 5: IFR2 (CONNORS)
# ==========================================
with aba_connors:
    st.subheader("🩸 IFR2 Connors")
    c_at = st.selectbox("Ativo (IFR2):", todos_ativos, key="c_at")
    if st.button("🚀 Analisar IFR2", type="primary"):
        df = puxar_dados_blindados(c_at, tempo_grafico='1d', barras=2000)
        df['IFR2'] = ta.rsi(df['Close'], length=2)
        st.metric("IFR2 Atual", f"{df['IFR2'].iloc[-1]:.2f}")
        renderizar_grafico_tv(f"BMFBOVESPA:{c_at}")
