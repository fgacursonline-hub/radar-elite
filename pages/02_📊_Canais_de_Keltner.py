import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import pandas_ta as ta
import time
import warnings
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
    st.error("❌ Arquivo 'motor_dados.py' não encontrado na raiz do projeto. Crie o Bunker de Dados primeiro.")
    st.stop()

todos_ativos = sorted(list(set([a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)])))

tradutor_periodo_nome = {
    '1mo': '1 Mês', '3mo': '3 Meses', '6mo': '6 Meses',
    '1y': '1 Ano', '2y': '2 Anos', '5y': '5 Anos',
    'max': 'Máximo', '60d': '60 Dias'
}

def colorir_lucro(row):
    if 'Resultado Atual' in row and isinstance(row['Resultado Atual'], str) and row['Resultado Atual'].startswith('+'):
        return ['color: #00FF00; font-weight: bold'] * len(row)
    if 'Situação' in row and isinstance(row['Situação'], str) and 'Gain' in row['Situação']:
        return ['color: #2eeb5c; font-weight: bold'] * len(row)
    return [''] * len(row)

# --- FUNÇÃO DO GRÁFICO (QUE ESTAVA FALTANDO) ---
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
    st.title("📊 Estratégia: Canais de Keltner")

with col_botao:
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.link_button("📖 Ler Manual", "https://seusite.com/manual_ifr", use_container_width=True)

st.info("📊 **Estratégia (Retorno à Média):** O setup foca em comprar o pânico (toque na banda inferior) e vender a euforia (toque na banda superior), aproveitando o conceito de retorno à média. **Atenção:** Keltner brilha em mercados laterais, mas operar contra tendências muito fortes pode gerar falsos rompimentos. É altamente recomendado o uso de filtros de contexto (como MM200, ADX ou divergência de IFR) antes de acionar a compra cega na banda inferior.")

aba_padrao, aba_pm, aba_individual, aba_futuros = st.tabs([
    "📡 Radar (Padrão)", "📡 Radar (PM)", "🔬 Raio-X Individual", "📉 Raio-X Futuros"
])

# ==========================================
# ABA 1: RADAR PADRÃO (KELTNER) COM STOP OPCIONAL
# ==========================================
with aba_padrao:
    st.subheader("📡 Radar Padrão (Entrada na Banda Inferior)")
    st.markdown("O robô faz a entrada no exato momento em que o preço **toca a banda inferior** de Keltner e aguarda o alvo ou stop de proteção.")
    
    cp1, cp2, cp3 = st.columns(3)
    with cp1:
        lista_padrao = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"], key="pk_lista")
        ativos_padrao = bdrs_elite if lista_padrao == "BDRs Elite" else ibrx_selecao if lista_padrao == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        periodo_padrao = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=3, key="pk_per")
    with cp2:
        alvo_padrao = st.number_input("Alvo de Lucro (%):", value=5.0, step=0.5, key="pk_alvo")
        stop_padrao = st.number_input("Stop Loss (%):", value=0.0, step=0.5, help="0.0 ignora o Stop", key="pk_stop")
        keltner_mult = st.number_input("Multiplicador Keltner:", min_value=0.5, max_value=10.0, value=3.0, step=0.1, key="pk_mult")
    with cp3:
        capital_padrao = st.number_input("Capital por Trade (R$):", value=10000.0, step=1000.0, key="pk_cap")
        tempo_padrao = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="pk_tmp")

    btn_iniciar_padrao = st.button("🚀 Iniciar Varredura Padrão", type="primary", use_container_width=True, key="pk_btn")

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
            s_text_p.text(f"🔍 Analisando Keltner (Padrão): {ativo} ({idx+1}/{len(ativos_padrao)})")
            p_bar_p.progress((idx + 1) / len(ativos_padrao))

            try:
                df_full = puxar_dados_blindados(ativo, tempo_grafico=tempo_padrao, barras=5000)
                if df_full is None or len(df_full) < 50: continue

                # --- CÁLCULO DO KELTNER ---
                kc = ta.kc(df_full['High'], df_full['Low'], df_full['Close'], length=20, scalar=keltner_mult)
                if kc is None or kc.empty: continue
                coluna_inferior = [c for c in kc.columns if c.startswith('KCL')][0]
                df_full['Keltner_Inf'] = kc[coluna_inferior]
                df_full = df_full.dropna()

                data_atual = df_full.index[-1]
                offset_map = {'1mo': 1, '3mo': 3, '6mo': 6, '1y': 12, '2y': 24, '5y': 60, '60d': 2}
                data_corte = data_atual - pd.DateOffset(months=offset_map.get(periodo_padrao, 120)) if periodo_padrao != 'max' else df_full.index[0]

                df = df_full[df_full.index >= data_corte].copy()
                if len(df) == 0: continue

                trades, em_pos = [], False
                df_back = df.reset_index()
                col_data = df_back.columns[0]
                vit, der = 0, 0

                for i in range(1, len(df_back)):
                    if em_pos:
                        if df_back['Low'].iloc[i] < min_price_in_trade:
                            min_price_in_trade = df_back['Low'].iloc[i]
                            
                        saiu = False
                        if df_back['High'].iloc[i] >= take_profit:
                            trades.append({'Lucro (R$)': float(capital_padrao) * alvo_dec, 'Drawdown_Raw': ((min_price_in_trade / preco_entrada) - 1) * 100})
                            vit += 1; saiu = True
                        elif stop_padrao > 0 and df_back['Low'].iloc[i] <= stop_price:
                            trades.append({'Lucro (R$)': -(float(capital_padrao) * stop_dec), 'Drawdown_Raw': -stop_padrao})
                            der += 1; saiu = True
                            
                        if saiu: em_pos = False; continue

                    condicao_entrada = df_back['Low'].iloc[i] <= df_back['Keltner_Inf'].iloc[i]
                    if condicao_entrada and not em_pos:
                        em_pos = True
                        d_ent = df_back[col_data].iloc[i]
                        preco_entrada = df_back['Keltner_Inf'].iloc[i] 
                        min_price_in_trade = df_back['Low'].iloc[i]
                        take_profit = preco_entrada * (1 + alvo_dec)
                        stop_price = preco_entrada * (1 - stop_dec)

                if em_pos:
                    res_atual = ((df_back['Close'].iloc[-1] / preco_entrada) - 1) * 100
                    queda_max = ((min_price_in_trade / preco_entrada) - 1) * 100
                    ls_abertos_p.append({
                        'Ativo': ativo, 'Entrada': d_ent.strftime('%d/%m %H:%M') if tempo_padrao in ['15m', '60m'] else d_ent.strftime('%d/%m/%Y'),
                        'Dias': (df_back[col_data].iloc[-1] - d_ent).days, 'PM': f"R$ {preco_entrada:.2f}",
                        'Cotação Atual': f"R$ {df_back['Close'].iloc[-1]:.2f}",
                        'Prej. Máx': f"{queda_max:.2f}%", 'Stop': f"R$ {stop_price:.2f}" if stop_padrao > 0 else "-",
                        'Resultado Atual': f"+{res_atual:.2f}%" if res_atual > 0 else f"{res_atual:.2f}%"
                    })
                else:
                    tem_sinal = df_full['Low'].iloc[-1] <= df_full['Keltner_Inf'].iloc[-1]
                    if tem_sinal: ls_sinais_p.append({'Ativo': ativo, 'Preço Atual': f"R$ {df_full['Close'].iloc[-1]:.2f}", 'Banda Inf': f"R$ {df_full['Keltner_Inf'].iloc[-1]:.2f}"})

                if len(trades) > 0:
                    df_t = pd.DataFrame(trades)
                    lucro_tot = df_t['Lucro (R$)'].sum()
                    invest = float(capital_padrao) * len(df_t)
                    tx_acerto = f"{(vit/len(df_t))*100:.1f}%" if stop_padrao > 0 else "-"
                    ls_resumo_p.append({
                        'Ativo': ativo, 'Trades': len(df_t), 'Taxa Acerto': tx_acerto,
                        'Pior Queda': f"{df_t['Drawdown_Raw'].min():.2f}%", 'Lucro R$': lucro_tot
                    })
            except Exception as e: pass

        s_text_p.empty()
        p_bar_p.empty()

        st.subheader(f"🚀 Oportunidades Hoje (Padrão | Keltner {keltner_mult:.1f})")
        if len(ls_sinais_p) > 0: st.dataframe(pd.DataFrame(ls_sinais_p), use_container_width=True, hide_index=True)
        else: st.info("Nenhum ativo tocou a Banda Inferior na última barra.")

        st.subheader("⏳ Operações em Andamento (Aguardando Alvo)")
        if len(ls_abertos_p) > 0:
            df_abertos = pd.DataFrame(ls_abertos_p).sort_values(by='Dias', ascending=False)
            st.dataframe(df_abertos.style.apply(colorir_lucro, axis=1), use_container_width=True, hide_index=True)
        else: st.success("Sua carteira está limpa.")

        st.subheader(f"📊 Top 10 Histórico ({tradutor_periodo_nome.get(periodo_padrao, periodo_padrao)})")
        if len(ls_resumo_p) > 0:
            df_resumo = pd.DataFrame(ls_resumo_p).sort_values(by='Lucro R$', ascending=False).head(10)
            df_resumo['Lucro R$'] = df_resumo['Lucro R$'].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(df_resumo, use_container_width=True, hide_index=True)
        else: st.warning("Nenhuma operação finalizada.")

# ==========================================
# ABA 2: RADAR EM MASSA (PM DINÂMICO KELTNER)
# ==========================================
with aba_pm:
    st.subheader("📡 Radar PM Dinâmico por Distância (Keltner)")
    st.markdown("O robô faz a 1ª entrada na Banda Inferior. Os novos aportes só ocorrem se o preço cair a porcentagem estipulada em relação à última compra.")
    
    st.markdown("##### ⚙️ Configurações da Varredura")
    cr1, cr2, cr3 = st.columns(3)
    with cr1:
        lista_pm = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"], key="rk_lista")
        ativos_pm = bdrs_elite if lista_pm == "BDRs Elite" else ibrx_selecao if lista_pm == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        periodo_pm = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=3, key="rk_per")
    with cr2:
        alvo_pm = st.number_input("Alvo de Lucro (%):", value=3.0, step=0.5, key="rk_alvo")
        keltner_mult_pm = st.number_input("Multiplicador Keltner:", min_value=0.5, max_value=10.0, value=3.0, step=0.1, key="rk_mult")
        pm_drop = st.number_input("Queda para novo PM (%):", value=10.0, step=1.0, key="rk_drop")
    with cr3:
        capital_pm = st.number_input("Capital por Sinal (R$):", value=10000.0, step=1000.0, key="rk_cap")
        tempo_pm = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="rk_tmp")
        
    btn_iniciar_pm = st.button("🚀 Iniciar Varredura PM", type="primary", use_container_width=True, key="rk_btn")

    if btn_iniciar_pm:
        if tempo_pm == '15m' and periodo_pm not in ['1mo', '3mo']: periodo_pm = '60d'
        elif tempo_pm == '60m' and periodo_pm in ['5y', 'max']: periodo_pm = '2y'

        alvo_decimal = alvo_pm / 100
        pm_drop_decimal = pm_drop / 100

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

                kc = ta.kc(df_full['High'], df_full['Low'], df_full['Close'], length=20, scalar=keltner_mult_pm)
                if kc is None or kc.empty: continue
                coluna_inferior = [c for c in kc.columns if c.startswith('KCL')][0]
                df_full['Keltner_Inf'] = kc[coluna_inferior]
                df_full = df_full.dropna()

                data_atual = df_full.index[-1]
                offset_map = {'1mo': 1, '3mo': 3, '6mo': 6, '1y': 12, '2y': 24, '5y': 60, '60d': 2}
                data_corte = data_atual - pd.DateOffset(months=offset_map.get(periodo_pm, 120)) if periodo_pm != 'max' else df_full.index[0]

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
                            
                        if df_back['Low'].iloc[i] <= next_pm_price:
                            qtd_pms += 1
                            preco_compra = next_pm_price 
                            capital_total += float(capital_pm)
                            qtd_acoes += float(capital_pm) / preco_compra
                            preco_medio = capital_total / qtd_acoes
                            take_profit = preco_medio * (1 + alvo_decimal)
                            next_pm_price = preco_compra * (1 - pm_drop_decimal)

                    condicao_entrada = df_back['Low'].iloc[i] <= df_back['Keltner_Inf'].iloc[i]
                    if condicao_entrada and not em_pos:
                        em_pos = True
                        d_ent = df_back[col_data].iloc[i]
                        preco_entrada_inicial = df_back['Keltner_Inf'].iloc[i]
                        min_price_in_trade = df_back['Low'].iloc[i]
                        qtd_pms = 0
                        preco_compra = preco_entrada_inicial
                        capital_total = float(capital_pm)
                        qtd_acoes = capital_total / preco_compra
                        preco_medio = preco_compra
                        take_profit = preco_medio * (1 + alvo_decimal)
                        next_pm_price = preco_compra * (1 - pm_drop_decimal)

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
                    tem_sinal = df_full['Low'].iloc[-1] <= df_full['Keltner_Inf'].iloc[-1]
                    if tem_sinal: lista_sinais.append({'Ativo': ativo, 'Preço Atual': f"R$ {df_full['Close'].iloc[-1]:.2f}", 'Banda Inf': f"R$ {df_full['Keltner_Inf'].iloc[-1]:.2f}"})

                if len(trades) > 0:
                    df_t = pd.DataFrame(trades)
                    lista_resumo.append({'Ativo': ativo, 'Trades': len(df_t), 'Pior Queda': f"{df_t['Drawdown_Raw'].min():.2f}%", 'Lucro R$': df_t['Lucro (R$)'].sum()})

            except Exception as e: pass

        status_text.empty()
        progress_bar.empty()

        st.subheader(f"🚀 Oportunidades Hoje (PM | Keltner {keltner_mult_pm:.1f})")
        if len(lista_sinais) > 0: st.dataframe(pd.DataFrame(lista_sinais), use_container_width=True, hide_index=True)
        else: st.info("Nenhum ativo tocou a Banda Inferior na última barra.")

        st.subheader("⏳ Operações em Andamento (Aportes por Distância)")
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
# ABA 3: RAIO-X INDIVIDUAL DO ATIVO (KELTNER)
# ==========================================
with aba_individual:
    st.subheader("🔬 Análise Detalhada de Ativo Único (Keltner)")
    st.markdown("Faça o teste de estresse de um ativo específico testando as estratégias de Keltner.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        lupa_ativo = st.selectbox("Selecione o Ativo:", todos_ativos, index=todos_ativos.index('TSLA34') if 'TSLA34' in todos_ativos else 0, key="l2k_ativo")
        lupa_estrategia = st.selectbox("Estratégia a Testar:", ["Padrão (Sem PM)", "PM Dinâmico"], key="l2k_est")
        lupa_periodo = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=2, key="l2k_per")
    with col2:
        lupa_alvo = st.number_input("Alvo (%):", value=3.0, step=0.5, key="l2k_alvo")
        
        # --- LÓGICA DINÂMICA DA INTERFACE ---
        if lupa_estrategia == "PM Dinâmico":
            lupa_pm_drop = st.number_input("Queda para novo PM (%):", value=10.0, step=1.0, key="l2k_drop")
            lupa_stop = 0.0
        else:
            lupa_stop = st.number_input("Stop Loss (%):", value=5.0, step=0.5, key="l2k_stop", help="0.0 para ignorar") 
            lupa_pm_drop = 10.0
            
        lupa_capital = st.number_input("Capital Base (R$):", value=10000.0, step=1000.0, key="l2k_cap")
    with col3:
        lupa_tempo = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="l2k_tmp")
        lupa_keltner = st.number_input("Multiplicador Keltner:", min_value=0.5, max_value=10.0, value=3.0, step=0.1, key="l2k_mult")
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True) 
        btn_raiox = st.button("🔍 Gerar Raio-X", type="primary", use_container_width=True, key="l2k_btn")

    if btn_raiox:
        ativo = lupa_ativo.strip().upper()
        with st.spinner(f'Testando Backtest ({lupa_estrategia}) em {ativo}...'):
            try:
                df_full = puxar_dados_blindados(ativo, tempo_grafico=lupa_tempo, barras=5000)
                if df_full is None or len(df_full) < 50:
                    st.error("Dados insuficientes no TradingView para este ativo.")
                else:
                    # --- CÁLCULO DO KELTNER ---
                    kc = ta.kc(df_full['High'], df_full['Low'], df_full['Close'], length=20, scalar=lupa_keltner)
                    coluna_inferior = [c for c in kc.columns if c.startswith('KCL')][0]
                    df_full['Keltner_Inf'] = kc[coluna_inferior]
                    df_full = df_full.dropna()

                    data_atual = df_full.index[-1]
                    offset_map = {'1mo': 1, '3mo': 3, '6mo': 6, '1y': 12, '2y': 24, '5y': 60, '60d': 2}
                    data_corte = data_atual - pd.DateOffset(months=offset_map.get(lupa_periodo, 120)) if lupa_periodo != 'max' else df_full.index[0]

                    df = df_full[df_full.index >= data_corte].copy()
                    trades = []
                    em_pos = False
                    alvo_decimal = lupa_alvo / 100
                    stop_decimal = lupa_stop / 100
                    pm_drop_decimal = lupa_pm_drop / 100
                    df_back = df.reset_index()
                    col_data = df_back.columns[0]
                    vitorias, derrotas = 0, 0

                    for i in range(1, len(df_back)):
                        condicao_entrada = df_back['Low'].iloc[i] <= df_back['Keltner_Inf'].iloc[i]

                        if lupa_estrategia == "Padrão (Sem PM)":
                            if em_pos:
                                if df_back['Low'].iloc[i] < min_price_in_trade:
                                    min_price_in_trade = df_back['Low'].iloc[i]
                                
                                saiu = False
                                if df_back['High'].iloc[i] >= take_profit:
                                    d_sai = df_back[col_data].iloc[i]
                                    lucro_rs = float(lupa_capital) * alvo_decimal
                                    trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': d_sai.strftime('%d/%m/%Y'), 'Duração': (d_sai - d_ent).days, 'Lucro (R$)': lucro_rs, 'Queda Máx': f"{((min_price_in_trade / preco_entrada) - 1) * 100:.2f}%", 'Situação': 'Gain ✅'})
                                    vitorias += 1; saiu = True
                                elif lupa_stop > 0 and df_back['Low'].iloc[i] <= stop_price:
                                    d_sai = df_back[col_data].iloc[i]
                                    lucro_rs = - (float(lupa_capital) * stop_decimal)
                                    trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': d_sai.strftime('%d/%m/%Y'), 'Duração': (d_sai - d_ent).days, 'Lucro (R$)': lucro_rs, 'Situação': 'Stop ❌'})
                                    derrotas += 1; saiu = True
                                
                                if saiu: em_pos = False; continue

                            if condicao_entrada and not em_pos:
                                em_pos = True
                                d_ent = df_back[col_data].iloc[i]
                                preco_entrada = df_back['Keltner_Inf'].iloc[i]
                                min_price_in_trade = df_back['Low'].iloc[i]
                                take_profit = preco_entrada * (1 + alvo_decimal)
                                stop_price = preco_entrada * (1 - stop_decimal)

                        elif lupa_estrategia == "PM Dinâmico":
                            if em_pos:
                                if df_back['Low'].iloc[i] < min_price_in_trade: min_price_in_trade = df_back['Low'].iloc[i]
                                
                                if df_back['High'].iloc[i] >= take_profit:
                                    d_sai = df_back[col_data].iloc[i]
                                    lucro_rs = capital_total * alvo_decimal
                                    trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': d_sai.strftime('%d/%m/%Y'), 'Duração': (d_sai - d_ent).days, 'Lucro (R$)': lucro_rs, 'Queda Máx': f"{((min_price_in_trade / preco_entrada_inicial) - 1) * 100:.2f}%", 'Situação': 'Gain ✅'})
                                    vitorias += 1; em_pos = False; continue
                                    
                                if df_back['Low'].iloc[i] <= next_pm_price:
                                    qtd_pms += 1
                                    preco_compra = next_pm_price
                                    capital_total += float(lupa_capital)
                                    qtd_acoes += float(lupa_capital) / preco_compra
                                    preco_medio = capital_total / qtd_acoes
                                    take_profit = preco_medio * (1 + alvo_decimal)
                                    next_pm_price = preco_compra * (1 - pm_drop_decimal)

                            if condicao_entrada and not em_pos:
                                em_pos = True
                                d_ent = df_back[col_data].iloc[i]
                                preco_entrada_inicial = df_back['Keltner_Inf'].iloc[i]
                                min_price_in_trade = df_back['Low'].iloc[i]
                                qtd_pms = 0
                                capital_total = float(lupa_capital)
                                qtd_acoes = capital_total / preco_entrada_inicial
                                preco_medio = preco_entrada_inicial
                                take_profit = preco_medio * (1 + alvo_decimal)
                                next_pm_price = preco_entrada_inicial * (1 - pm_drop_decimal)

                    st.divider()
                    st.markdown(f"### 📊 Resultado: {ativo} ({lupa_estrategia})")
                    
                    if len(trades) > 0:
                        df_t = pd.DataFrame(trades)
                        mc1, mc2, mc3, mc4 = st.columns(4)
                        mc1.metric("Lucro Total Estimado", f"R$ {df_t['Lucro (R$)'].sum():,.2f}")
                        mc2.metric("Tempo Preso (Médio)", f"{round(df_t['Duração'].mean(), 1)} dias")
                        mc3.metric("Operações Fechadas", f"{len(df_t)}")
                        
                        if lupa_estrategia == "Padrão (Sem PM)" and lupa_stop > 0:
                            mc4.metric("Taxa de Acerto", f"{(vitorias / len(df_t)) * 100:.1f}%")
                        else:
                            mc4.metric("Pior Queda", f"{df_t['Queda Máx'].min() if 'Queda Máx' in df_t.columns else 'N/A'}")
                        
                        st.dataframe(df_t.style.apply(colorir_lucro, axis=1), use_container_width=True, hide_index=True)
                    else:
                        st.warning("Nenhuma operação concluída usando essa estratégia neste período.")
                        
                    st.divider()
                    st.markdown(f"### 📈 Gráfico Interativo: {ativo}")
                    renderizar_grafico_tv(f"BMFBOVESPA:{ativo}")
            except Exception as e: st.error(f"Erro: {e}")

# ==========================================
# ABA 4: RAIO-X FUTUROS (KELTNER COM STOP OPCIONAL)
# ==========================================
with aba_futuros:
    st.subheader("📈 Raio-X Mercado Futuro (WIN, WDO) - Keltner")
    st.markdown("Focado em **15 minutos** para garantir estabilidade do backtest. Entradas ao tocar a Banda Inferior.")
    
    cf1, cf2, cf3 = st.columns(3)
    with cf1:
        mapa_futuros = {"WINFUT (Mini Índice)": "WIN1!", "WDOFUT (Mini Dólar)": "WDO1!"}
        fut_selecionado = st.selectbox("Selecione o Ativo:", options=list(mapa_futuros.keys()), key="f5k_ativo")
        fut_ativo = mapa_futuros[fut_selecionado] 
        fut_estrategia = st.selectbox("Estratégia:", ["Padrão (Sem PM)", "PM Dinâmico"], key="f5k_est")
        fut_periodo = st.selectbox("Período:", options=['3mo', '6mo', '1y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=1, key="f5k_per")
    with cf2:
        fut_alvo = st.number_input("Alvo (Pontos):", value=300, step=50, key="f5k_alvo")
        if fut_estrategia == "Padrão (Sem PM)":
            fut_stop = st.number_input("Stop Loss (Pontos):", value=0, step=50, help="0 para ignorar o Stop Loss", key="f5k_stop")
            fut_pm_drop = 150
        elif fut_estrategia == "PM Dinâmico":
            fut_pm_drop = st.number_input("Queda p/ novo PM (Pontos):", value=150, step=50, key="f5k_drop")
            fut_stop = 0
        fut_contratos = st.number_input("Contratos Iniciais:", value=1, step=1, key="f5k_cont")
    with cf3:
        valor_mult_padrao = 0.20 if "WIN" in fut_selecionado else 10.00
        fut_multiplicador = st.number_input("Multiplicador (R$):", value=valor_mult_padrao, step=0.10, format="%.2f", key="f5k_mult")
        fut_tempo = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d'], index=0, key="f5k_tmp")
        fut_keltner = st.number_input("Multiplicador Keltner:", min_value=0.5, max_value=10.0, value=3.0, step=0.1, key="f5k_kmult")
        
    fut_zerar_daytrade = st.checkbox("⏰ Zeragem Automática no Fim do Dia", value=True, key="f5k_zerar")
    btn_raiox_futuros = st.button("🚀 Gerar Raio-X", type="primary", use_container_width=True, key="f5k_btn")

    if btn_raiox_futuros:
        with st.spinner(f'Analisando {fut_selecionado}...'):
            try:
                df_full = puxar_dados_blindados(fut_ativo, tempo_grafico=fut_tempo, barras=10000)
                if df_full is not None and len(df_full) > 50:
                    kc = ta.kc(df_full['High'], df_full['Low'], df_full['Close'], length=20, scalar=fut_keltner)
                    coluna_inferior = [c for c in kc.columns if c.startswith('KCL')][0]
                    df_full['Keltner_Inf'] = kc[coluna_inferior]
                    df_full = df_full.dropna()

                    delta = {'3mo': 3, '6mo': 6, '1y': 12}.get(fut_periodo, 0)
                    data_corte = df_full.index[-1] - pd.DateOffset(months=delta) if delta > 0 else df_full.index[0]
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

                        cond_ent = df_back['Low'].iloc[i] <= df_back['Keltner_Inf'].iloc[i]
                        
                        if em_pos:
                            if fut_estrategia == "PM Dinâmico":
                                if df_back['High'].iloc[i] >= take_profit:
                                    luc = fut_alvo * contratos_atuais * fut_multiplicador
                                    trades.append({'Entrada': d_ent.strftime('%d/%m/%Y %H:%M'), 'Saída': d_at.strftime('%d/%m/%Y %H:%M'), 'Lucro (R$)': luc, 'Situação': 'Gain ✅'})
                                    em_pos, vitorias = False, vitorias + 1; continue
                                elif df_back['Low'].iloc[i] <= next_pm_price:
                                    preco_compra = next_pm_price
                                    preco_medio = ((preco_medio * contratos_atuais) + (preco_compra * fut_contratos)) / (contratos_atuais + fut_contratos)
                                    contratos_atuais += fut_contratos
                                    take_profit = preco_medio + fut_alvo
                                    next_pm_price = preco_compra - fut_pm_drop
                            else:
                                if fut_stop > 0 and df_back['Low'].iloc[i] <= stop_p:
                                    trades.append({'Entrada': d_ent.strftime('%d/%m/%Y %H:%M'), 'Saída': d_at.strftime('%d/%m/%Y %H:%M'), 'Lucro (R$)': -(fut_stop * fut_contratos * fut_multiplicador), 'Situação': 'Stop ❌'})
                                    em_pos, derrotas = False, derrotas + 1; continue
                                elif df_back['High'].iloc[i] >= take_p:
                                    trades.append({'Entrada': d_ent.strftime('%d/%m/%Y %H:%M'), 'Saída': d_at.strftime('%d/%m/%Y %H:%M'), 'Lucro (R$)': fut_alvo * fut_contratos * fut_multiplicador, 'Situação': 'Gain ✅'})
                                    em_pos, vitorias = False, vitorias + 1; continue
                        
                        if cond_ent and not em_pos:
                            em_pos, d_ent = True, d_at
                            preco_entrada = df_back['Keltner_Inf'].iloc[i]
                            if fut_estrategia == "PM Dinâmico":
                                preco_medio, contratos_atuais = preco_entrada, fut_contratos
                                take_profit = preco_medio + fut_alvo
                                next_pm_price = preco_entrada - fut_pm_drop
                            else:
                                take_p, stop_p = preco_entrada + fut_alvo, preco_entrada - fut_stop

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

                        m1, m2, m3, m4, m5 = st.columns(5)
                        m1.metric("Lucro Total", f"R$ {l_total:,.2f}")
                        m2.metric("Operações", len(df_t))
                        m3.metric("Taxa Acerto", f"{t_acerto:.1f}%")
                        m4.metric("Payoff", f"{p_off:.2f}")
                        m5.metric("V / D", f"{len(vits_df)} / {len(derrs_df)}")
                        
                        st.dataframe(df_t.style.apply(colorir_lucro, axis=1), use_container_width=True, hide_index=True)
                    else: st.warning("Nenhuma operação encontrada.")
            except Exception as e: st.error(f"Erro: {e}")
