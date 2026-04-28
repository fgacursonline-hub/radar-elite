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

# 1. SEGURANÇA (Verifica se logou no app.py)
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
    st.error("❌ Arquivo 'motor_dados.py' não encontrado na raiz do projeto. Crie o Bunker de Dados primeiro.")
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

# --- FUNÇÃO MESTRA DE ESTILIZAÇÃO VISUAL ---
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
col_titulo, col_botao = st.columns([4, 1])

with col_titulo:
    st.title("📈 Estratégia: IFR")

with col_botao:
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.link_button("📖 Ler Manual", "https://seusite.com/manual_ifr", use_container_width=True)

aba_padrao, aba_pm, aba_individual, aba_futuros, aba_connors = st.tabs([
    "📡 Radar (Padrão)", "📡 Radar (PM)", "🔬 Raio-X Individual", "📉 Raio-X Futuros", "🩸 IFR2 (Connors)"
])

# ==========================================
# ABA 1: RADAR PADRÃO
# ==========================================
with aba_padrao:
    st.subheader("📡 Radar Padrão (Entrada Única & Alvo Fixo)")
    st.info("📊 **A Estratégia Clássica (Rastreador IFR):** Busca exaustão da força vendedora. \n\n🟢 **Gatilho de Compra:** Ocorre quando a linha do IFR mergulha na região de pânico e, em seguida, **cruza de volta para cima do nível configurado**, confirmando que a venda exauriu e o repique começou. \n\n🔴 **Condução (Padrão):** O robô faz apenas uma entrada por sinal e sai estritamente no alvo de lucro fixo percentual ou no Stop Loss (caso configurado).")
    
    cp1, cp2, cp3, cp4 = st.columns(4)
    with cp1:
        lista_padrao = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"], key="p_lista")
        ativos_padrao = bdrs_elite if lista_padrao == "BDRs Elite" else ibrx_selecao if lista_padrao == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        periodo_padrao = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=3, key="p_per")
    with cp2:
        alvo_padrao = st.number_input("Alvo de Lucro (%):", value=5.0, step=0.5, key="p_alvo")
        ifr_padrao = st.number_input("Período do IFR:", min_value=2, max_value=50, value=8, step=1, key="p_ifr")
    with cp3:
        stop_padrao = st.number_input("Stop Loss (%):", value=0.0, step=0.5, help="Deixe 0.0 para ignorar o Stop.", key="p_stop")
        nivel_padrao = st.number_input("Nível IFR (<):", value=25.0, step=1.0, key="p_niv")
    with cp4:
        capital_padrao = st.number_input("Capital por Trade (R$):", value=10000.0, step=1000.0, key="p_cap")
        tempo_padrao = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="p_tmp")

    btn_iniciar_padrao = st.button("🚀 Iniciar Varredura Padrão", type="primary", use_container_width=True, key="p_btn")

    if btn_iniciar_padrao:
        if tempo_padrao == '15m' and periodo_padrao not in ['1mo', '3mo']: periodo_padrao = '60d'
        elif tempo_padrao == '60m' and periodo_padrao in ['5y', 'max']: periodo_padrao = '2y'

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
                if periodo_padrao == '1mo': data_corte = data_atual - pd.DateOffset(months=1)
                elif periodo_padrao == '3mo': data_corte = data_atual - pd.DateOffset(months=3)
                elif periodo_padrao == '6mo': data_corte = data_atual - pd.DateOffset(months=6)
                elif periodo_padrao == '1y': data_corte = data_atual - pd.DateOffset(years=1)
                elif periodo_padrao == '2y': data_corte = data_atual - pd.DateOffset(years=2)
                elif periodo_padrao == '5y': data_corte = data_atual - pd.DateOffset(years=5)
                elif periodo_padrao == '60d': data_corte = data_atual - pd.DateOffset(days=60)
                else: data_corte = df_full.index[0]

                df = df_full[df_full.index >= data_corte].copy()
                if len(df) == 0: continue

                trades, em_pos = [], False
                df_back = df.reset_index()
                col_data = df_back.columns[0]

                for i in range(1, len(df_back)):
                    if em_pos:
                        if df_back['Low'].iloc[i] < min_price_in_trade:
                            min_price_in_trade = df_back['Low'].iloc[i]
                            
                        saiu = False
                        if df_back['High'].iloc[i] >= take_profit:
                            trades.append({'Lucro (R$)': float(capital_padrao) * alvo_dec, 'Drawdown_Raw': ((min_price_in_trade / preco_entrada) - 1) * 100})
                            saiu = True
                        elif stop_padrao > 0 and df_back['Low'].iloc[i] <= stop_price:
                            trades.append({'Lucro (R$)': -(float(capital_padrao) * stop_dec), 'Drawdown_Raw': -stop_padrao})
                            saiu = True
                            
                        if saiu: em_pos = False; continue

                    condicao_entrada = (df_back['IFR_Prev'].iloc[i] < nivel_padrao) and (df_back['IFR'].iloc[i] >= nivel_padrao)
                    if condicao_entrada and not em_pos:
                        em_pos = True
                        d_ent = df_back[col_data].iloc[i]
                        preco_entrada = df_back['Close'].iloc[i]
                        min_price_in_trade = df_back['Low'].iloc[i]
                        take_profit = preco_entrada * (1 + alvo_dec)
                        stop_price = preco_entrada * (1 - stop_dec)

                if em_pos:
                    res_atual = ((df_back['Close'].iloc[-1] / preco_entrada) - 1) * 100
                    q_max = ((min_price_in_trade / preco_entrada) - 1) * 100
                    ls_abertos_p.append({
                        'Ativo': ativo, 'Entrada': d_ent.strftime('%d/%m %H:%M') if tempo_padrao in ['15m', '60m'] else d_ent.strftime('%d/%m/%Y'),
                        'Dias': (df_back[col_data].iloc[-1] - d_ent).days, 'PM': f"R$ {preco_entrada:.2f}",
                        'Cotação Atual': f"R$ {df_back['Close'].iloc[-1]:.2f}",
                        'Prej. Máx': f"{q_max:.2f}%", 'Stop': f"R$ {stop_price:.2f}" if stop_padrao > 0 else "-",
                        'Resultado Atual': f"+{res_atual:.2f}%" if res_atual > 0 else f"{res_atual:.2f}%"
                    })
                else:
                    tem_sinal = (df_full['IFR_Prev'].iloc[-1] < nivel_padrao) and (df_full['IFR'].iloc[-1] >= nivel_padrao)
                    
                    if tem_sinal: 
                        preco_at = df_full['Close'].iloc[-1]
                        ls_sinais_p.append({'Ativo': ativo, 'Preço Atual': f"R$ {preco_at:.2f}"})
                        
                        msg_elite = (
                            f"🎯 *CAÇADORES DE ELITE: IFR*\n\n"
                            f"🚀 *SINAL DE ENTRADA:* `{ativo}`\n"
                            f"💵 *Preço:* R$ {preco_at:.2f}\n"
                            f"⏱️ *Tempo:* {tempo_padrao}"
                        )
                        enviar_alerta_telegram(msg_elite)

                if len(trades) > 0:
                    df_t = pd.DataFrame(trades)
                    lucro_tot = df_t['Lucro (R$)'].sum()
                    invest = float(capital_padrao) * len(df_t)
                    res_pct = (lucro_tot / invest) * 100 if invest > 0 else 0
                    ls_resumo_p.append({
                        'Ativo': ativo, 
                        'Trades': len(df_t), 
                        'Pior Queda': f"{df_t['Drawdown_Raw'].min():.2f}%", 
                        'Investimento': f"R$ {invest:,.2f}", 
                        'Lucro R$': lucro_tot, 
                        'Resultado': f"{res_pct:.2f}%"
                    })
            except: pass

        s_text_p.empty()
        p_bar_p.empty()

        st.subheader(f"🚀 Oportunidades Hoje (Padrão | IFR {ifr_padrao})")
        if len(ls_sinais_p) > 0: 
            st.dataframe(pd.DataFrame(ls_sinais_p), use_container_width=True, hide_index=True)
        else: 
            st.info("Nenhum ativo deu sinal de entrada na última barra.")

        st.subheader("⏳ Operações em Andamento (Aguardando Alvo)")
        if len(ls_abertos_p) > 0:
            df_abertos = pd.DataFrame(ls_abertos_p).sort_values(by='Dias', ascending=False)
            st.dataframe(df_abertos.style.apply(colorir_lucro, axis=1), use_container_width=True, hide_index=True)
        else: 
            st.success("Sua carteira está limpa.")

        st.subheader(f"📊 Top 10 Histórico ({tradutor_periodo_nome.get(periodo_padrao, periodo_padrao)})")
        if len(ls_resumo_p) > 0:
            df_resumo = pd.DataFrame(ls_resumo_p).sort_values(by='Lucro R$', ascending=False).head(10)
            df_resumo['Lucro R$'] = df_resumo['Lucro R$'].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(df_resumo, use_container_width=True, hide_index=True)
        else: 
            st.warning("Nenhuma operação finalizada.")

# ==========================================
# ABA 2: RADAR EM MASSA (PM DINÂMICO)
# ==========================================
with aba_pm:
    st.subheader("📡 Radar PM Dinâmico")
    st.markdown("O robô defende a posição fazendo novos aportes a cada novo sinal de entrada, reduzindo o preço médio.")
    st.info("📊 **Condução por Preço Médio (PM Dinâmico):** Usa o mesmo gatilho clássico do IFR. A grande diferença é a gestão financeira. Se o trade for contra você e o IFR der um **novo sinal de compra**, o robô faz um novo aporte (compra novamente), baixando o seu Preço Médio e recalibrando o Alvo Final mais para baixo. Ideal para quem tem margem e opera ativos sólidos.")
    
    st.markdown("##### ⚙️ Configurações da Varredura")
    cr1, cr2, cr3, cr4 = st.columns(4)
    with cr1:
        lista_pm = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"], key="r1_lista")
        ativos_pm = bdrs_elite if lista_pm == "BDRs Elite" else ibrx_selecao if lista_pm == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        periodo_pm = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=3, key="r1_per")
    with cr2:
        alvo_pm = st.number_input("Alvo (%):", value=3.0, step=0.5, key="r1_alvo")
        ifr_pm = st.number_input("Período do IFR:", min_value=2, max_value=50, value=8, step=1, key="r1_ifr")
    with cr3:
        nivel_pm = st.number_input("Nível IFR (<):", value=25.0, step=1.0, key="r1_niv")
        tempo_pm = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="r1_tmp")
    with cr4:
        capital_pm = st.number_input("Capital por Sinal (R$):", value=10000.0, step=1000.0, key="r1_cap")
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        btn_iniciar_pm = st.button("🚀 Iniciar Varredura PM", type="primary", use_container_width=True, key="r1_btn")

    if btn_iniciar_pm:
        if tempo_pm == '15m' and periodo_pm not in ['1mo', '3mo']: periodo_pm = '60d'
        elif tempo_pm == '60m' and periodo_pm in ['5y', 'max']: periodo_pm = '2y'

        alvo_decimal = alvo_pm / 100

        lista_sinais, lista_abertos, lista_resumo = [], [], []
        progress_bar = st.progress(0)
        status_text = st.empty()

        for idx, ativo_raw in enumerate(ativos_pm):
            ativo = ativo_raw.replace('.SA', '')
            status_text.text(f"🔍 Analisando (PM): {ativo} ({idx+1}/{len(ativos_pm)})")
            progress_bar.progress((idx + 1) / len(ativos_pm))

            try:
                df_full = puxar_dados_blindados(ativo, tempo_grafico=tempo_pm, barras=5000)
                if df_full is None or len(df_full) < 50: continue
                
                df_full['IFR'] = ta.rsi(df_full['Close'], length=ifr_pm)
                df_full['IFR_Prev'] = df_full['IFR'].shift(1)
                df_full = df_full.dropna()

                data_atual = df_full.index[-1]
                if periodo_pm == '1mo': data_corte = data_atual - pd.DateOffset(months=1)
                elif periodo_pm == '3mo': data_corte = data_atual - pd.DateOffset(months=3)
                elif periodo_pm == '6mo': data_corte = data_atual - pd.DateOffset(months=6)
                elif periodo_pm == '1y': data_corte = data_atual - pd.DateOffset(years=1)
                elif periodo_pm == '2y': data_corte = data_atual - pd.DateOffset(years=2)
                elif periodo_pm == '5y': data_corte = data_atual - pd.DateOffset(years=5)
                elif periodo_pm == '60d': data_corte = data_atual - pd.DateOffset(days=60)
                else: data_corte = df_full.index[0]

                df = df_full[df_full.index >= data_corte].copy()
                if len(df) == 0: continue

                trades, em_pos = [], False
                df_back = df.reset_index()
                col_data = df_back.columns[0]

                for i in range(1, len(df_back)):
                    if em_pos:
                        if df_back['Low'].iloc[i] < min_price_in_trade: 
                            min_price_in_trade = df_back['Low'].iloc[i]
                        if df_back['High'].iloc[i] >= take_profit:
                            lucro_rs = capital_total * alvo_decimal
                            trades.append({'Lucro (R$)': lucro_rs, 'Drawdown_Raw': ((min_price_in_trade / preco_entrada_inicial) - 1) * 100})
                            em_pos = False
                            continue 

                    condicao_entrada = (df_back['IFR_Prev'].iloc[i] < nivel_pm) and (df_back['IFR'].iloc[i] >= nivel_pm)
                    if condicao_entrada:
                        if not em_pos:
                            em_pos = True
                            d_ent = df_back[col_data].iloc[i]
                            preco_entrada_inicial = df_back['Close'].iloc[i]
                            min_price_in_trade = df_back['Low'].iloc[i]
                            qtd_pms = 0
                            preco_compra = preco_entrada_inicial
                            capital_total = float(capital_pm)
                            qtd_acoes = capital_total / preco_compra
                            preco_medio = preco_compra
                            take_profit = preco_medio * (1 + alvo_decimal)
                        else:
                            qtd_pms += 1
                            preco_compra = df_back['Close'].iloc[i]
                            capital_total += float(capital_pm)
                            qtd_acoes += float(capital_pm) / preco_compra
                            preco_medio = capital_total / qtd_acoes
                            take_profit = preco_medio * (1 + alvo_decimal)

                if em_pos:
                    queda_maxima = ((min_price_in_trade / preco_entrada_inicial) - 1) * 100
                    resultado_atual = ((df_back['Close'].iloc[-1] / preco_medio) - 1) * 100
                    lista_abertos.append({
                        'Ativo': ativo, 'Entrada': d_ent.strftime('%d/%m %H:%M') if tempo_pm in ['15m', '60m'] else d_ent.strftime('%d/%m/%Y'),
                        'Dias': (df_back[col_data].iloc[-1] - d_ent).days, 'PM': f"R$ {preco_medio:.2f}",
                        'Cotação Atual': f"R$ {df_back['Close'].iloc[-1]:.2f}", 'Prej. Máx': f"{queda_maxima:.2f}%",
                        'Resultado Atual': f"+{resultado_atual:.2f}%" if resultado_atual > 0 else f"{resultado_atual:.2f}%",
                        'Fez PM?': f"Sim ({qtd_pms}x)" if qtd_pms > 0 else 'Não'
                    })
                else:
                    tem_sinal = (df_full['IFR_Prev'].iloc[-1] < nivel_pm) and (df_full['IFR'].iloc[-1] >= nivel_pm)
                    if tem_sinal: lista_sinais.append({'Ativo': ativo, 'Preço Atual': f"R$ {df_full['Close'].iloc[-1]:.2f}"})

                if len(trades) > 0:
                    df_t = pd.DataFrame(trades)
                    lucro_tot = df_t['Lucro (R$)'].sum()
                    invest = float(capital_pm) * len(df_t)
                    res_pct = (lucro_tot / invest) * 100 if invest > 0 else 0
                    lista_resumo.append({
                        'Ativo': ativo, 
                        'Trades': len(df_t), 
                        'Pior Queda': f"{df_t['Drawdown_Raw'].min():.2f}%", 
                        'Investimento': f"R$ {invest:,.2f}", 
                        'Lucro R$': lucro_tot, 
                        'Resultado': f"{res_pct:.2f}%"
                    })

            except Exception as e: pass

        status_text.empty()
        progress_bar.empty()

        st.subheader(f"🚀 Oportunidades Hoje (PM | IFR {ifr_pm})")
        if len(lista_sinais) > 0: st.dataframe(pd.DataFrame(lista_sinais), use_container_width=True, hide_index=True)
        else: st.info("Nenhum ativo deu sinal de entrada na última barra.")

        st.subheader("⏳ Operações em Andamento (PM)")
        if len(lista_abertos) > 0:
            df_abertos = pd.DataFrame(lista_abertos).sort_values(by='Dias', ascending=False)
            st.dataframe(df_abertos.style.apply(colorir_lucro, axis=1), use_container_width=True, hide_index=True)
        else: st.success("Sua carteira está limpa.")

        st.subheader(f"📊 Top 10 Histórico ({tradutor_periodo_nome.get(periodo_pm, periodo_pm)})")
        if len(lista_resumo) > 0:
            df_resumo = pd.DataFrame(lista_resumo).sort_values(by='Lucro R$', ascending=False).head(10)
            df_resumo['Lucro R$'] = df_resumo['Lucro R$'].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(df_resumo, use_container_width=True, hide_index=True)
        else: st.warning("Nenhuma operação finalizada.")

# ==========================================
# ABA 3: RAIO-X INDIVIDUAL
# ==========================================
with aba_individual:
    st.subheader("🔬 Raio-X Detalhado: Backtest & Status Atual")
    st.markdown("Veja o histórico de acertos e o status completo se o ativo estiver com operação aberta agora.")
    st.info("📊 **Laboratório do Rastreador de IFR:** Avalie a performance matemática crua da tática de exaustão de venda. Basta inserir o Ticker do ativo e testar as metodologias de manejo de risco para descobrir o que rende mais lucro para esse ativo em específico.")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        lupa_ativo = st.selectbox("Selecione o Ativo:", todos_ativos, index=todos_ativos.index('TSLA34') if 'TSLA34' in todos_ativos else 0, key="l2_ativo")
        lupa_estrategia = st.selectbox("Estratégia:", ["Padrão", "PM Dinâmico"], key="l2_est")
        lupa_periodo = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=3, key="l2_per")
    with col2:
        lupa_alvo = st.number_input("Alvo (%):", value=3.0, step=0.5, key="l2_alvo")
        lupa_stop = st.number_input("Stop Loss (%):", value=5.0, step=0.5, key="l2_stop", help="0.0 = Sem Stop (válido no modo Padrão)") if lupa_estrategia == "Padrão" else 0.0
        lupa_capital = st.number_input("Capital Base (R$):", value=10000.0, step=1000.0, key="l2_cap")
    with col3:
        lupa_tempo = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk', '1mo'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal', '1mo': 'Mensal'}[x], key="l2_tmp")
        lupa_ifr_periodo = st.number_input("Período IFR:", min_value=2, max_value=50, value=8, step=1, key="l2_ifr")
        lupa_niv = st.number_input("Nível IFR (<):", value=25.0, step=1.0, key="l2_niv")
    with col4:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        btn_raiox = st.button("🔍 Rodar Análise Completa", type="primary", use_container_width=True, key="l2_btn")

    if btn_raiox:
        ativo = lupa_ativo
        with st.spinner(f'Calculando dados de {ativo}...'):
            try:
                df_full = puxar_dados_blindados(ativo, tempo_grafico=lupa_tempo, barras=5000)
                
                if df_full is not None and len(df_full) > 50:
                    df_full['IFR'] = ta.rsi(df_full['Close'], length=lupa_ifr_periodo)
                    df_full['IFR_Prev'] = df_full['IFR'].shift(1)
                    df_full = df_full.dropna()

                    data_atual_dt = df_full.index[-1]
                    offset_map = {'1mo': 1, '3mo': 3, '6mo': 6, '1y': 12, '2y': 24, '5y': 60}
                    data_corte = data_atual_dt - pd.DateOffset(months=offset_map.get(lupa_periodo, 120)) if lupa_periodo != 'max' else df_full.index[0]

                    df_back = df_full[df_full.index >= data_corte].copy().reset_index()
                    
                    trades = []
                    em_pos = False
                    posicao_atual = None
                    vitorias, derrotas = 0, 0

                    for i in range(1, len(df_back)):
                        condicao_entrada = (df_back['IFR_Prev'].iloc[i] < lupa_niv) and (df_back['IFR'].iloc[i] >= lupa_niv)

                        if not em_pos:
                            if condicao_entrada:
                                em_pos = True
                                d_ent = df_back.iloc[i, 0]
                                p_ent = df_back['Close'].iloc[i]
                                min_na_op = p_ent
                                cap_total = float(lupa_capital)
                                pm = p_ent
                                posicao_atual = {'Data': d_ent, 'PM': pm, 'Cap': cap_total}
                        else:
                            if df_back['Low'].iloc[i] < min_na_op: min_na_op = df_back['Low'].iloc[i]
                            
                            alvo_p = pm * (1 + (lupa_alvo/100))
                            stop_p = pm * (1 - (lupa_stop/100))
                            
                            saiu = False
                            if df_back['High'].iloc[i] >= alvo_p:
                                lucro = cap_total * (lupa_alvo/100)
                                vitorias += 1; situacao = "Gain ✅"; saiu = True
                            elif lupa_estrategia == "Padrão" and lupa_stop > 0 and df_back['Low'].iloc[i] <= stop_p:
                                lucro = -(cap_total * (lupa_stop/100))
                                derrotas += 1; situacao = "Stop ❌"; saiu = True

                            if saiu:
                                duracao = (df_back.iloc[i, 0] - d_ent).days
                                dd = ((min_na_op / pm) - 1) * 100
                                trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': df_back.iloc[i, 0].strftime('%d/%m/%Y'), 'Duração': duracao, 'Lucro (R$)': lucro, 'Queda Máx': dd, 'Situação': situacao})
                                em_pos = False
                                posicao_atual = None
                            elif lupa_estrategia == "PM Dinâmico" and condicao_entrada:
                                cap_total += float(lupa_capital)
                                pm = (pm + df_back['Close'].iloc[i]) / 2
                                posicao_atual['PM'] = pm
                                posicao_atual['Cap'] = cap_total

                    # --- EXIBIÇÃO: STATUS ATUAL ---
                    st.divider()
                    if em_pos and posicao_atual:
                        st.warning(f"⚠️ **OPERAÇÃO EM CURSO: {ativo} ({lupa_tempo})**")
                        
                        cotacao_atual = df_back['Close'].iloc[-1]
                        hoje = pd.Timestamp.today().normalize()
                        dias_em_op = (hoje - posicao_atual['Data']).days
                        
                        res_pct = ((cotacao_atual / posicao_atual['PM']) - 1) * 100
                        res_rs = posicao_atual['Cap'] * res_pct / 100
                        prej_max = ((min_na_op / posicao_atual['PM']) - 1) * 100

                        c1, c2, c3 = st.columns(3)
                        c1.metric("Data Entrada", posicao_atual['Data'].strftime('%d/%m/%Y'))
                        c2.metric("Dias em Operação", f"{dias_em_op} dias")
                        c3.metric("Cotação Atual", f"R$ {cotacao_atual:.2f}")
                        
                        st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
                        
                        c4, c5, c6 = st.columns(3)
                        c4.metric("Preço Médio (PM)", f"R$ {posicao_atual['PM']:.2f}")
                        c5.metric("Prejuízo Máximo (DD)", f"{prej_max:.2f}%")
                        c6.metric("Resultado Atual", f"{res_pct:.2f}%", delta=f"R$ {res_rs:.2f}")
                        
                    else:
                        st.success(f"✅ **{ativo}: Aguardando Novo Sinal de Entrada**")

                    # --- EXIBIÇÃO: MÉTRICAS DE RESUMO DO HISTÓRICO ---
                    if trades:
                        df_t = pd.DataFrame(trades)
                        st.markdown(f"### 📊 Resultado Consolidado: {ativo}")
                        
                        url_tv_ind = f"https://br.tradingview.com/chart/?symbol=BMFBOVESPA%3A{ativo}"
                        st.markdown(f"<a href='{url_tv_ind}' target='_blank' style='text-decoration: none; font-size: 14px; color: #4da6ff;'>🔗 Abrir no TradingView</a>", unsafe_allow_html=True)
                        
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("Lucro Total", f"R$ {df_t['Lucro (R$)'].sum():,.2f}")
                        m2.metric("Duração Média", f"{df_t['Duração'].mean():.1f} dias")
                        m3.metric("Operações Fechadas", len(df_t))
                        
                        if lupa_estrategia == "Padrão" and lupa_stop > 0:
                            taxa = (vitorias/len(df_t))*100
                            m4.metric("Taxa de Acerto", f"{taxa:.1f}%")
                        else:
                            m4.metric("Pior Queda", f"{df_t['Queda Máx'].min():.2f}%")
                        
                        df_t['Queda Máx'] = df_t['Queda Máx'].map("{:.2f}%".format)
                        
                        st.dataframe(df_t.style.apply(colorir_lucro, axis=1), use_container_width=True, hide_index=True)
                    else:
                        st.info("Nenhuma operação fechada no período de estudo.")
                        
                    # --- GRÁFICO INTERATIVO INSERIDO AQUI ---
                    st.divider()
                    st.markdown(f"### 📈 Gráfico Interativo: {ativo}")
                    renderizar_grafico_tv(f"BMFBOVESPA:{ativo}")
                    
                else:
                    st.error("Ativo não encontrado ou base de dados vazia.")
            except Exception as e:
                st.error(f"Erro no processamento: {e}")

# ==========================================
# ABA 4: RAIO-X FUTUROS
# ==========================================
with aba_futuros:
    st.subheader("📈 Raio-X Mercado Futuro (WIN, WDO, etc)")
    st.markdown("Focado em **15 minutos** para garantir a estabilidade do backtest.")
    st.info("📊 **Laboratório de Futuros (Day Trade/Swing):** Ajuste a agressividade do Índice (WIN) e do Dólar (WDO) no Intraday, focando nas exaustões pontuais de movimento para scalping ou carregamento.")
    
    cf1, cf2, cf3, cf4 = st.columns(4)
    with cf1:
        mapa_futuros = {"WINFUT (Mini Índice)": "WIN1!", "WDOFUT (Mini Dólar)": "WDO1!"}
        fut_selecionado = st.selectbox("Selecione o Ativo:", options=list(mapa_futuros.keys()), key="f_ativo_sel")
        fut_ativo = mapa_futuros[fut_selecionado] 
        fut_estrategia = st.selectbox("Estratégia:", ["Padrão", "PM Dinâmico"], key="f_est")
        fut_periodo = st.selectbox("Período:", options=['3mo', '6mo', '1y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=1, key="f_per")
    with cf2:
        fut_alvo = st.number_input("Alvo (Pontos):", value=300, step=50, key="f_alvo")
        fut_stop = st.number_input("Stop Loss (Pontos):", value=200, step=50, help="0 para ignorar", key="f_stop") if fut_estrategia == "Padrão" else 0 
        fut_contratos = st.number_input("Contratos:", value=1, step=1, key="f_cont")
    with cf3:
        valor_mult_padrao = 0.20 if "WIN" in fut_selecionado else 10.00
        fut_multiplicador = st.number_input("Multiplicador (R$):", value=valor_mult_padrao, step=0.10, format="%.2f", key="f_mult")
        fut_tempo = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d'], index=0, key="f_tmp")
        fut_ifr = st.number_input("Período IFR:", min_value=2, max_value=50, value=8, step=1, key="f_ifr")
    with cf4:
        fut_niv = st.number_input("Nível IFR (<):", value=25.0, step=1.0, key="f_niv")
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        fut_zerar_daytrade = st.checkbox("⏰ Zeragem Automática no Fim do Dia", value=True, key="f_zerar")
        btn_raiox_futuros = st.button("🚀 Gerar Raio-X", type="primary", use_container_width=True, key="f_btn")

    if btn_raiox_futuros:
        with st.spinner(f'Analisando {fut_selecionado}...'):
            try:
                df_full = puxar_dados_blindados(fut_ativo, tempo_grafico=fut_tempo, barras=10000)
                if df_full is not None and len(df_full) > 50:
                    df_full['IFR'] = ta.rsi(df_full['Close'], length=fut_ifr)
                    df_full['IFR_Prev'] = df_full['IFR'].shift(1)
                    df_full = df_full.dropna()

                    data_atual_dt = df_full.index[-1]
                    delta = {'3mo': 3, '6mo': 6, '1y': 12}.get(fut_periodo, 0)
                    data_corte = data_atual_dt - pd.DateOffset(months=delta) if delta > 0 else df_full.index[0]
                    df = df_full[df_full.index >= data_corte].copy()
                    
                    trades, em_pos, vitorias, derrotas = [], False, 0, 0
                    df_back = df.reset_index()
                    col_data = df_back.columns[0]

                    for i in range(1, len(df_back)):
                        d_at = df_back[col_data].iloc[i]
                        d_ant = df_back[col_data].iloc[i-1]
                        
                        if em_pos and fut_zerar_daytrade and d_at.date() != d_ant.date():
                            p_sai = df_back['Close'].iloc[i-1]
                            p_en_c = preco_medio if fut_estrategia == "PM Dinâmico" else preco_entrada
                            qtd_c = contratos_atuais if fut_estrategia == "PM Dinâmico" else fut_contratos
                            luc = (p_sai - p_en_c) * qtd_c * fut_multiplicador
                            trades.append({
                                'Entrada': d_ent.strftime('%d/%m/%Y %H:%M'), 
                                'Saída': d_ant.strftime('%d/%m/%Y %H:%M'), 
                                'Lucro (R$)': luc, 
                                'Situação': 'Zerad. Fim Dia ✅' if luc > 0 else 'Zerad. Fim Dia ❌'
                            })
                            if luc > 0: vitorias += 1
                            else: derrotas += 1
                            em_pos = False

                        cond_ent = (df_back['IFR_Prev'].iloc[i] < fut_niv) and (df_back['IFR'].iloc[i] >= fut_niv)
                        
                        if em_pos:
                            if fut_estrategia == "PM Dinâmico":
                                if df_back['High'].iloc[i] >= take_profit:
                                    luc = fut_alvo * contratos_atuais * fut_multiplicador
                                    trades.append({'Entrada': d_ent.strftime('%d/%m/%Y %H:%M'), 'Saída': d_at.strftime('%d/%m/%Y %H:%M'), 'Lucro (R$)': luc, 'Situação': 'Ganho ✅'})
                                    em_pos, vitorias = False, vitorias + 1
                                    continue
                            else:
                                if fut_stop > 0 and df_back['Low'].iloc[i] <= stop_p:
                                    trades.append({'Entrada': d_ent.strftime('%d/%m/%Y %H:%M'), 'Saída': d_at.strftime('%d/%m/%Y %H:%M'), 'Lucro (R$)': -(fut_stop * fut_contratos * fut_multiplicador), 'Situação': 'Perda ❌'})
                                    em_pos, derrotas = False, derrotas + 1
                                    continue
                                elif df_back['High'].iloc[i] >= take_p:
                                    trades.append({'Entrada': d_ent.strftime('%d/%m/%Y %H:%M'), 'Saída': d_at.strftime('%d/%m/%Y %H:%M'), 'Lucro (R$)': fut_alvo * fut_contratos * fut_multiplicador, 'Situação': 'Ganho ✅'})
                                    em_pos, vitorias = False, vitorias + 1
                                    continue
                        
                        if cond_ent and not em_pos:
                            em_pos, d_ent = True, d_at
                            if fut_estrategia == "PM Dinâmico":
                                preco_medio, contratos_atuais = df_back['Close'].iloc[i], fut_contratos
                                take_profit = preco_medio + fut_alvo
                            else:
                                preco_entrada = df_back['Close'].iloc[i]
                                take_p, stop_p = preco_entrada + fut_alvo, preco_entrada - fut_stop
                        elif cond_ent and em_pos and fut_estrategia == "PM Dinâmico":
                            preco_medio = ((preco_medio * contratos_atuais) + (df_back['Close'].iloc[i] * fut_contratos)) / (contratos_atuais + fut_contratos)
                            contratos_atuais += fut_contratos
                            take_profit = preco_medio + fut_alvo

                    if trades:
                        df_t = pd.DataFrame(trades)
                        st.divider()
                        st.markdown(f"### 📊 Resultado: {fut_selecionado}")
                        st.caption(f"📅 Período: {df.index[0].strftime('%d/%m/%Y')} até {df.index[-1].strftime('%d/%m/%Y')}")
                        
                        l_total = df_t['Lucro (R$)'].sum()
                        vits_df = df_t[df_t['Lucro (R$)'] > 0]
                        derrs_df = df_t[df_t['Lucro (R$)'] <= 0]
                        t_acerto = (len(vits_df) / len(df_t)) * 100
                        
                        m_ganho = vits_df['Lucro (R$)'].mean() if not vits_df.empty else 0
                        m_perda = abs(derrs_df['Lucro (R$)'].mean()) if not derrs_df.empty else 1
                        p_off = m_ganho / m_perda
                        
                        t_critica = (1 / (1 + (p_off if p_off > 0 else 0.01))) * 100
                        margem = t_acerto - t_critica

                        m1, m2, m3, m4, m5 = st.columns(5)
                        m1.metric("Lucro Total", f"R$ {l_total:,.2f}", delta=f"{l_total:,.2f}")
                        m2.metric("Operações", len(df_t))
                        m3.metric("Taxa Acerto", f"{t_acerto:.1f}%")
                        m4.metric("Payoff", f"{p_off:.2f}")
                        m5.metric("V / D", f"{len(vits_df)} / {len(derrs_df)}")
                        
                        if l_total > 0:
                            if p_off > 1:
                                st.success(f"🎯 **Expectativa Real Positiva:** Você está vencendo o mercado! Para cada R$ 1,00 arriscado, ganha R$ {p_off:.2f}. Margem de gordura: {margem:.1f}% acima do crítico.")
                            else:
                                st.info(f"⚖️ **Alerta de Equilíbrio:** Saldo positivo, mas payoff baixo ({p_off:.2f}). Sua alta taxa de acerto é que está salvando a estratégia. Cuidado!")
                        else:
                            st.error(f"🚨 **Expectativa Negativa:** O saldo de R$ {l_total:,.2f} mostra que a conta não fecha. Você precisa acertar mais de {t_critica:.1f}% para este Payoff, ou aumentar seu alvo.")

                        st.dataframe(df_t.style.apply(colorir_lucro, axis=1), use_container_width=True, hide_index=True)
                    else:
                        st.warning("Nenhuma operação encontrada.")
            except Exception as e: st.error(f"Erro: {e}")

# ==========================================
# ABA 6: IFR2 (CONNORS)
# ==========================================
with aba_connors:
    st.subheader("🩸 Máquina de Pânico: IFR2 (Larry Connors)")
    st.markdown("O sistema puro de Reversão à Média. Compra o pânico extremo (faca caindo) e sai no repique.")
    st.info("🩸 **A Estratégia (IFR2 Clássico):** Sistema estatístico de alta precisão desenhado por Larry Connors focado em reversão curta. \n\n🟢 **Gatilho de Compra:** O ativo deve estar em tendência primária de alta (Fechamento acima da Média de 200) para garantir que a queda é apenas um pânico temporário. A entrada ocorre apenas no fechamento do dia se o IFR calibrado em 2 períodos afundar abaixo do gatilho configurado (ex: IFR2 < 25).\n\n🔴 **Alvo / Saída:** O trade é puramente reativo e rápido. A posição é zerada na superação da Máxima dos últimos 2 dias ou no fechamento acima de uma média curta. Não há alvo longo, você só pega o 'repique' de alívio do mercado.")
    
    modo_connors = st.radio("Escolha o Modo Operacional:", ["📡 Radar de Sobrevenda (Varredura B3)", "🔬 Raio-X Individual (Backtest)"], horizontal=True)
    
    if modo_connors == "📡 Radar de Sobrevenda (Varredura B3)":
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            lista_c = st.selectbox("Lista de Ativos:", ["IBrX Seleção", "BDRs Elite", "Todos"], key="c_lst")
            periodo_c = st.selectbox("Período:", ['1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome.get(x, x), index=2, key="c_per")
        with c2:
            gatilho_c = st.number_input("Gatilho Compra (IFR2 <):", value=25.0, step=5.0, max_value=50.0, key="c_gat")
            filtro_c = st.checkbox("Filtro: Preço Acima da MM200", value=True, help="Só compra se a ação estiver em tendência de alta no longo prazo.")
        with c3:
            saida_c = st.selectbox("Regra de Saída (Alvo):", ["Máxima dos Últimos 2 Dias", "Fechamento > MME5"], key="c_sai")
            stop_c = st.selectbox("Stop Loss de Proteção:", ["Sem Stop (Original Connors)", "Máxima Queda (10%)"], key="c_stp")
        with c4:
            capital_c = st.number_input("Capital/Trade (R$):", value=10000.0, step=1000.0, key="c_cap")
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            btn_iniciar_connors = st.button("🚀 Iniciar Varredura IFR2", type="primary", use_container_width=True)

        if btn_iniciar_connors:
            ativos_analise = bdrs_elite if lista_c == "BDRs Elite" else ibrx_selecao if lista_c == "IBrX Seleção" else bdrs_elite + ibrx_selecao
            
            ls_armados, ls_abertos, ls_resumo = [], [], []
            p_bar = st.progress(0); s_text = st.empty()

            for idx, ativo_raw in enumerate(ativos_analise):
                ativo = ativo_raw.replace('.SA', '')
                s_text.text(f"🔍 Caçando sangue em {ativo} ({idx+1}/{len(ativos_analise)})")
                p_bar.progress((idx + 1) / len(ativos_analise))

                try:
                    df_full = puxar_dados_blindados(ativo, tempo_grafico='1d', barras=5000)
                    if df_full is None or len(df_full) < 200: continue

                    df_full['IFR2'] = ta.rsi(df_full['Close'], length=2)
                    df_full['MM200'] = ta.sma(df_full['Close'], length=200)
                    df_full['MME5'] = ta.ema(df_full['Close'], length=5)
                    df_full['Max_2d'] = df_full['High'].rolling(window=2).max().shift(1)
                    df_full = df_full.dropna()

                    if periodo_c == 'max': data_corte = df_full.index[0]
                    else: data_corte = df_full.index[-1] - pd.DateOffset(years=int(periodo_c.replace('y','')))
                    
                    df = df_full[df_full.index >= data_corte].copy().reset_index()
                    col_data = df.columns[0]

                    em_pos, preco_entrada = False, 0.0
                    vitorias, total_trades, lucro_total = 0, 0, 0.0

                    for i in range(1, len(df)):
                        atual = df.iloc[i]
                        if em_pos:
                            fechou_posicao, preco_saida = False, 0.0

                            if saida_c == "Máxima dos Últimos 2 Dias" and atual['High'] >= atual['Max_2d']:
                                preco_saida = max(atual['Max_2d'], atual['Open'])
                                fechou_posicao = True
                            elif saida_c == "Fechamento > MME5" and atual['Close'] > atual['MME5']:
                                preco_saida = atual['Close']
                                fechou_posicao = True
                            
                            queda_atual = (atual['Low'] / preco_entrada) - 1
                            if not fechou_posicao and stop_c == "Máxima Queda (10%)" and queda_atual <= -0.10:
                                preco_saida = preco_entrada * 0.90
                                fechou_posicao = True

                            if fechou_posicao:
                                lucro_rs = capital_c * ((preco_saida / preco_entrada) - 1)
                                lucro_total += lucro_rs
                                total_trades += 1
                                if lucro_rs > 0: vitorias += 1
                                em_pos = False
                        else:
                            sinal_ifr = atual['IFR2'] < gatilho_c
                            sinal_mm200 = atual['Close'] > atual['MM200'] if filtro_c else True
                            if sinal_ifr and sinal_mm200:
                                em_pos, preco_entrada, d_ent = True, atual['Close'], atual[col_data]

                    if em_pos:
                        cot_atual = df['Close'].iloc[-1]
                        res_pct = ((cot_atual / preco_entrada) - 1) * 100
                        alvo_m = "Buscando MME5" if saida_c != "Máxima dos Últimos 2 Dias" else f"R$ {df['Max_2d'].iloc[-1]:.2f}"
                        ls_abertos.append({
                            'Ativo': ativo, 'Dias Sofrendo': (df[col_data].iloc[-1] - d_ent).days,
                            'PM Compra': f"R$ {preco_entrada:.2f}", 'Alvo (Saída)': alvo_m,
                            'Cotação': f"R$ {cot_atual:.2f}", 'Resultado Atual': f"+{res_pct:.2f}%" if res_pct > 0 else f"{res_pct:.2f}%"
                        })
                    else:
                        hoje = df.iloc[-1]
                        if hoje['IFR2'] < gatilho_c and (not filtro_c or hoje['Close'] > hoje['MM200']):
                            ls_armados.append({
                                'Ativo': ativo, 'IFR2': f"{hoje['IFR2']:.1f}", 'Preço (Leilão)': f"R$ {hoje['Close']:.2f}", 'Status': "Sangrando (COMPRA)"
                            })

                    if total_trades > 0:
                        ls_resumo.append({'Ativo': ativo, 'Trades': total_trades, 'Acertos': f"{(vitorias/total_trades)*100:.1f}%", 'Lucro Total R$': lucro_total})
                except: pass

            s_text.empty(); p_bar.empty()
            
            st.divider()
            st.subheader(f"🚀 Oportunidades de Ouro (IFR2 < {gatilho_c})")
            if ls_armados: st.dataframe(pd.DataFrame(ls_armados).sort_values(by='IFR2'), use_container_width=True, hide_index=True)
            else: st.info("O mercado está calmo. Nenhuma ação esticada para baixo hoje.")

            st.subheader(f"⏳ Posições em Aberto (Aguardando Repique)")
            if ls_abertos: st.dataframe(pd.DataFrame(ls_abertos).style.apply(colorir_lucro, axis=1), use_container_width=True, hide_index=True)
            else: st.success("Sua carteira IFR2 está limpa.")

            st.subheader(f"🏆 Top 20 Histórico ({tradutor_periodo_nome.get(periodo_c, periodo_c)})")
            if ls_resumo:
                df_hist = pd.DataFrame(ls_resumo).sort_values(by='Lucro Total R$', ascending=False).head(20)
                df_hist['Lucro Total R$'] = df_hist['Lucro Total R$'].apply(lambda x: f"R$ {x:,.2f}")
                st.dataframe(df_hist, use_container_width=True, hide_index=True)
                
    else:
        col1, col2, col3, col4 = st.columns(4)
        with col1: 
            rx_ativo = st.selectbox("Selecione o Ativo:", todos_ativos, index=todos_ativos.index('PETR4') if 'PETR4' in todos_ativos else 0, key="rxc_atv")
            rx_per = st.selectbox("Período:", ['1y', '2y', '5y', 'max'], index=2, format_func=lambda x: tradutor_periodo_nome.get(x, x), key="rxc_per")
        with col2: 
            rx_gatilho = st.number_input("Gatilho (IFR2 <):", value=25.0, step=5.0, max_value=50.0, key="rxc_gat")
            rx_filtro = st.checkbox("Exigir Preço Acima MM200", value=True, key="rxc_filt")
        with col3: 
            rx_saida = st.selectbox("Saída:", ["Máxima dos Últimos 2 Dias", "Fechamento > MME5"], key="rxc_sai")
            rx_stop = st.selectbox("Stop Loss:", ["Sem Stop (Original)", "Máxima Queda (10%)"], key="rxc_stp")
        with col4: 
            rx_cap = st.number_input("Capital (R$):", value=10000.0, step=1000.0, key="rxc_cap")
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            btn_rx = st.button("🔍 Rodar Backtest IFR2", type="primary", use_container_width=True)

        if btn_rx and rx_ativo:
            with st.spinner(f'Calculando elástico de {rx_ativo}...'):
                try:
                    df_full = puxar_dados_blindados(rx_ativo, tempo_grafico='1d', barras=5000)
                    
                    if df_full is None or len(df_full) < 200: st.error("Dados insuficientes.")
                    else:
                        df_full['IFR2'] = ta.rsi(df_full['Close'], length=2)
                        df_full['MM200'] = ta.sma(df_full['Close'], length=200)
                        df_full['MME5'] = ta.ema(df_full['Close'], length=5)
                        df_full['Max_2d'] = df_full['High'].rolling(window=2).max().shift(1)
                        df_full = df_full.dropna()

                        data_corte = df_full.index[0] if rx_per == 'max' else df_full.index[-1] - pd.DateOffset(years=int(rx_per.replace('y','')))
                        df = df_full[df_full.index >= data_corte].copy().reset_index()
                        col_data = df.columns[0]

                        trades, em_pos, vitorias, derrotas = [], False, 0, 0
                        preco_entrada = 0.0
                        min_na_op = 0.0
                        d_ent = None

                        for i in range(1, len(df)):
                            atual = df.iloc[i]
                            if em_pos:
                                if atual['Low'] < min_na_op: min_na_op = atual['Low']
                                
                                fechou_posicao, preco_saida, motivo = False, 0.0, 'Gain ✅'
                                
                                if rx_saida == "Máxima dos Últimos 2 Dias" and atual['High'] >= atual['Max_2d']:
                                    preco_saida, fechou_posicao = max(atual['Max_2d'], atual['Open']), True
                                elif rx_saida == "Fechamento > MME5" and atual['Close'] > atual['MME5']:
                                    preco_saida, fechou_posicao = atual['Close'], True
                                
                                queda_atual = (atual['Low'] / preco_entrada) - 1
                                if not fechou_posicao and rx_stop == "Máxima Queda (10%)" and queda_atual <= -0.10:
                                    preco_saida, fechou_posicao, motivo = preco_entrada * 0.90, True, 'Stop Queda ❌'

                                if fechou_posicao:
                                    luc_rs = rx_cap * ((preco_saida / preco_entrada) - 1)
                                    if motivo == 'Gain ✅' and luc_rs < 0: motivo = 'Loss Técnico ❌'
                                    
                                    dd = ((min_na_op / preco_entrada) - 1) * 100
                                    
                                    trades.append({
                                        'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': atual[col_data].strftime('%d/%m/%Y'),
                                        'Dias': (atual[col_data] - d_ent).days, 'Lucro (R$)': luc_rs, 'Queda Máx': dd, 'Situação': motivo
                                    })
                                    if luc_rs > 0: vitorias += 1
                                    else: derrotas += 1
                                    em_pos = False
                            else:
                                sinal_ifr = atual['IFR2'] < rx_gatilho
                                sinal_mm200 = atual['Close'] > atual['MM200'] if rx_filtro else True
                                if sinal_ifr and sinal_mm200:
                                    em_pos, preco_entrada, d_ent = True, atual['Close'], atual[col_data]
                                    min_na_op = atual['Low']

                        # --- STATUS ATUAL ---
                        st.divider()
                        if em_pos:
                            st.warning(f"⚠️ **OPERAÇÃO EM CURSO: {rx_ativo}**")
                            cotacao_atual = df['Close'].iloc[-1]
                            hoje = pd.Timestamp.today().normalize()
                            dias_em_op = (hoje - d_ent).days
                            
                            res_pct = ((cotacao_atual / preco_entrada) - 1) * 100
                            res_rs = rx_cap * res_pct / 100
                            prej_max = ((min_na_op / preco_entrada) - 1) * 100
                            
                            alvo_m = "Buscando MME5" if rx_saida != "Máxima dos Últimos 2 Dias" else f"R$ {df['Max_2d'].iloc[-1]:.2f}"

                            c1, c2, c3 = st.columns(3)
                            c1.metric("Data Entrada", d_ent.strftime('%d/%m/%Y'))
                            c2.metric("Dias em Operação", f"{dias_em_op} dias")
                            c3.metric("Cotação Atual", f"R$ {cotacao_atual:.2f}")
                            
                            st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
                            
                            c4, c5, c6 = st.columns(3)
                            c4.metric("Preço Compra", f"R$ {preco_entrada:.2f}")
                            c5.metric("Alvo (Saída)", alvo_m)
                            c6.metric("Resultado Atual", f"{res_pct:.2f}%", delta=f"R$ {res_rs:.2f}")
                        else:
                            st.success(f"✅ **{rx_ativo}: Aguardando Novo Sinal de Entrada**")

                        st.divider()
                        st.markdown(f"### 📊 Resultado IFR2: {rx_ativo}")
                        
                        url_tv_ifr = f"https://br.tradingview.com/chart/?symbol=BMFBOVESPA%3A{rx_ativo}"
                        st.markdown(f"<a href='{url_tv_ifr}' target='_blank' style='text-decoration: none; font-size: 14px; color: #4da6ff;'>🔗 Abrir no TradingView</a>", unsafe_allow_html=True)
                        
                        if trades:
                            df_t = pd.DataFrame(trades)
                            c_m1, c_m2, c_m3, c_m4 = st.columns(4)
                            l_tot = df_t['Lucro (R$)'].sum()
                            tx_acerto = (vitorias/len(df_t))*100
                            
                            m_ganho = df_t[df_t['Lucro (R$)'] > 0]['Lucro (R$)'].mean() if vitorias > 0 else 0
                            m_perda = abs(df_t[df_t['Lucro (R$)'] <= 0]['Lucro (R$)'].mean()) if derrotas > 0 else 1
                            payoff = m_ganho / m_perda
                            
                            c_m1.metric("Lucro Total", f"R$ {l_tot:,.2f}")
                            c_m2.metric("Operações Fechadas", len(df_t))
                            c_m3.metric("Taxa Acerto", f"{tx_acerto:.1f}%")
                            c_m4.metric("Payoff", f"{payoff:.2f}")

                            if tx_acerto > 75.0: st.success("🎯 **Máquina de Vencer:** Taxa de acerto absurdamente alta! O sistema brilha neste ativo.")
                            elif payoff < 0.5: st.warning("⚖️ **Atenção:** Risco/retorno muito baixo. Exige disciplina de ferro no manejo emocional.")

                            df_t['Queda Máx'] = df_t['Queda Máx'].map("{:.2f}%".format)
                            
                            st.dataframe(df_t.style.apply(colorir_lucro, axis=1), use_container_width=True, hide_index=True)
                        else:
                            st.warning("Nenhuma operação concluída usando essa configuração.")
                            
                        # --- GRÁFICO INTERATIVO INSERIDO AQUI ---
                        st.divider()
                        st.markdown(f"### 📈 Gráfico Interativo: {rx_ativo}")
                        renderizar_grafico_tv(f"BMFBOVESPA:{rx_ativo}")
                        
                except Exception as e: st.error(f"Erro ao processar: {e}")
