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
    st.error("❌ Arquivo 'config_ativos.py' não encontrado na raiz do projeto.")
    st.stop()

try:
    from motor_dados import puxar_dados_blindados
except ImportError:
    st.error("❌ Arquivo 'motor_dados.py' não encontrado na raiz do projeto.")
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

tradutor_periodo_nome = {
    '1mo': '1 Mês', '3mo': '3 Meses', '6mo': '6 Meses',
    '1y': '1 Ano', '2y': '2 Anos', '5y': '5 Anos',
    'max': 'Máximo', '60d': '60 Dias'
}

def colorir_lucro(row):
    for col in ['Resultado Atual', 'Resultado']:
        if col in row and isinstance(row[col], str) and row[col].startswith('+'):
            return ['color: #2eeb5c; font-weight: bold'] * len(row)
    if 'Situação' in row and isinstance(row['Situação'], str) and 'Gain' in row['Situação']:
        return ['color: #2eeb5c; font-weight: bold'] * len(row)
    return [''] * len(row)

def renderizar_grafico_tv(simbolo_tv, altura=600):
    html_tv = f"""
    <div class="tradingview-widget-container">
      <div id="tradingview_ifr"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
      "width": "100%", "height": {altura}, "symbol": "{simbolo_tv}",
      "interval": "D", "timezone": "America/Sao_Paulo", "theme": "dark",
      "style": "1", "locale": "br", "enable_publishing": false,
      "allow_symbol_change": true, "container_id": "tradingview_ifr"
    }});
      </script>
    </div>
    """
    components.html(html_tv, height=altura)

# 3. INTERFACE DE ABAS
st.title("📈 Estratégia: IFR")

# ABA STOP REMOVIDA DAQUI
aba_padrao, aba_pm, aba_individual, aba_futuros, aba_connors = st.tabs([
    "📡 Radar (Padrão)", "📡 Radar (PM)", "🔬 Raio-X Individual", "📉 Raio-X Futuros", "🩸 IFR2 (Connors)"
])

# ==========================================
# ABA 1: RADAR PADRÃO (AGORA COM STOP OPCIONAL)
# ==========================================
with aba_padrao:
    st.subheader("📡 Radar Padrão (Entrada Única)")
    st.info("📊 Gatilho clássico: IFR mergulha abaixo de 25 e cruza de volta para cima. Saída automática no Alvo ou Stop opcional.")
    
    cp1, cp2, cp3 = st.columns(3)
    with cp1:
        lista_padrao = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"], key="p_lista")
        ativos_padrao = bdrs_elite if lista_padrao == "BDRs Elite" else ibrx_selecao if lista_padrao == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        periodo_padrao = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=3, key="p_per")
    with cp2:
        alvo_padrao = st.number_input("Alvo de Lucro (%):", value=5.0, step=0.5, key="p_alvo")
        # 🔥 NOVO: STOP LOSS OPCIONAL NO RADAR PADRÃO
        stop_padrao = st.number_input("Stop Loss (%):", value=0.0, step=0.5, help="Deixe 0.0 para ignorar o Stop.", key="p_stop")
        ifr_padrao = st.number_input("Período do IFR:", min_value=2, max_value=50, value=8, step=1, key="p_ifr")
    with cp3:
        capital_padrao = st.number_input("Capital por Trade (R$):", value=10000.0, step=1000.0, key="p_cap")
        tempo_padrao = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="p_tmp")

    btn_iniciar_padrao = st.button("🚀 Iniciar Varredura Padrão", type="primary", use_container_width=True, key="p_btn")

    if btn_iniciar_padrao:
        alvo_dec = alvo_padrao / 100
        stop_dec = stop_padrao / 100

        ls_sinais_p, ls_abertos_p, ls_resumo_p = [], [], []
        p_bar_p = st.progress(0)
        s_text_p = st.empty()

        for idx, ativo_raw in enumerate(ativos_padrao):
            ativo = ativo_raw.replace('.SA', '')
            s_text_p.text(f"🔍 Analisando (Padrão): {ativo} ({idx+1}/{len(ativos_padrao)})")
            p_bar_p.progress((idx + 1) / len(ativos_padrao))

            try:
                df_full = puxar_dados_blindados(ativo, tempo_grafico=tempo_padrao, barras=5000)
                if df_full is None or len(df_full) < 50: continue

                df_full['IFR'] = ta.rsi(df_full['Close'], length=ifr_padrao)
                df_full['IFR_Prev'] = df_full['IFR'].shift(1)
                df_full = df_full.dropna()

                data_atual = df_full.index[-1]
                offset_map = {'1mo': 1, '3mo': 3, '6mo': 6, '1y': 12, '2y': 24, '5y': 60, '60d': 2}
                data_corte = data_atual - pd.DateOffset(months=offset_map.get(periodo_padrao, 120)) if periodo_padrao != 'max' else df_full.index[0]

                df = df_full[df_full.index >= data_corte].copy()
                trades, em_pos = [], False
                df_back = df.reset_index()
                col_data = df_back.columns[0]

                for i in range(1, len(df_back)):
                    if em_pos:
                        if df_back['Low'].iloc[i] < min_price_in_trade: min_price_in_trade = df_back['Low'].iloc[i]
                        
                        fechou = False
                        # Saída Gain
                        if df_back['High'].iloc[i] >= take_profit:
                            trades.append({'Lucro (R$)': float(capital_padrao) * alvo_dec, 'Drawdown_Raw': ((min_price_in_trade / preco_entrada) - 1) * 100})
                            fechou = True
                        # Saída Stop (Apenas se stop_padrao > 0)
                        elif stop_padrao > 0 and df_back['Low'].iloc[i] <= stop_price:
                            trades.append({'Lucro (R$)': -(float(capital_padrao) * stop_dec), 'Drawdown_Raw': -stop_padrao})
                            fechou = True
                        
                        if fechou: em_pos = False; continue

                    condicao_entrada = (df_back['IFR_Prev'].iloc[i] < 25) and (df_back['IFR'].iloc[i] >= 25)
                    if condicao_entrada and not em_pos:
                        em_pos, d_ent = True, df_back[col_data].iloc[i]
                        preco_entrada = df_back['Close'].iloc[i]
                        min_price_in_trade = df_back['Low'].iloc[i]
                        take_profit = preco_entrada * (1 + alvo_dec)
                        stop_price = preco_entrada * (1 - stop_dec)

                if em_pos:
                    res_atual = ((df_back['Close'].iloc[-1] / preco_entrada) - 1) * 100
                    q_max = ((min_price_in_trade / preco_entrada) - 1) * 100
                    ls_abertos_p.append({
                        'Ativo': ativo, 'Entrada': d_ent.strftime('%d/%m %H:%M') if tempo_padrao in ['15m', '60m'] else d_ent.strftime('%d/%m/%Y'),
                        'PM Compra': f"R$ {preco_entrada:.2f}",
                        'Alvo': f"R$ {take_profit:.2f}",
                        'Stop': f"R$ {stop_price:.2f}" if stop_padrao > 0 else "Sem Stop",
                        'Resultado Atual': f"+{res_atual:.2f}%" if res_atual > 0 else f"{res_atual:.2f}%"
                    })
                else:
                    hoje = df_full.iloc[-1]
                    if hoje['IFR_Prev'] < 25 and hoje['IFR'] >= 25:
                        ls_sinais_p.append({'Ativo': ativo, 'Preço Atual': f"R$ {hoje['Close']:.2f}"})
                        enviar_alerta_telegram(f"🎯 IFR PADRÃO: Entrada em `{ativo}` a R$ {hoje['Close']:.2f}")

                if len(trades) > 0:
                    df_t = pd.DataFrame(trades)
                    lucro_tot = df_t['Lucro (R$)'].sum()
                    invest = float(capital_padrao) * len(df_t)
                    ls_resumo_p.append({'Ativo': ativo, 'Trades': len(df_t), 'Lucro R$': lucro_tot, 'Resultado': f"{(lucro_tot/invest)*100:.2f}%"})
            except: pass

        s_text_p.empty(); p_bar_p.empty()
        st.subheader("🚀 Oportunidades Hoje")
        if ls_sinais_p: st.dataframe(pd.DataFrame(ls_sinais_p), use_container_width=True, hide_index=True)
        else: st.info("Nenhum sinal detectado.")

        st.subheader("⏳ Operações em Andamento")
        if ls_abertos_p: st.dataframe(pd.DataFrame(ls_abertos_p).style.apply(colorir_lucro, axis=1), use_container_width=True, hide_index=True)
        else: st.success("Carteira limpa.")

        st.subheader("📊 Top 10 Histórico")
        if ls_resumo_p: st.dataframe(pd.DataFrame(ls_resumo_p).sort_values(by='Lucro R$', ascending=False).head(10), use_container_width=True, hide_index=True)

# [OS DEMAIS MÓDULOS (ABA PM, INDIVIDUAL, FUTUROS E CONNORS) PERMANECEM EXATAMENTE IGUAIS AO CÓDIGO ANTERIOR]
# ... (Código continua idêntico abaixo)
