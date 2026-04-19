import streamlit as st
from tvDatafeed import TvDatafeed, Interval
import pandas as pd
import pandas_ta as ta
import time
import warnings

warnings.filterwarnings('ignore')

# 1. SEGURANÇA
if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

# 2. CONEXÃO E LISTAS
@st.cache_resource
def get_tv_connection():
    return TvDatafeed()

tv = get_tv_connection()

tradutor_periodo_nome = {
    '1mo': '1 Mês', '3mo': '3 Meses', '6mo': '6 Meses',
    '1y': '1 Ano', '2y': '2 Anos', '5y': '5 Anos',
    'max': 'Máximo', '60d': '60 Dias'
}

tradutor_intervalo = {
    '15m': Interval.in_15_minute,
    '60m': Interval.in_1_hour,
    '1d': Interval.in_daily,
    '1wk': Interval.in_weekly
}

bdrs_elite = [
    'NVDC34.SA', 'P2LT34.SA', 'ROXO34.SA', 'INBR32.SA', 'M1TA34.SA', 'TSLA34.SA',
    'LILY34.SA', 'AMZO34.SA', 'AURA33.SA', 'GOGL34.SA', 'MSFT34.SA', 'MUTC34.SA',
    'MELI34.SA', 'C2OI34.SA', 'ORCL34.SA', 'M2ST34.SA', 'A1MD34.SA', 'NFLX34.SA',
    'ITLC34.SA', 'AVGO34.SA', 'COCA34.SA', 'JBSS32.SA', 'AAPL34.SA', 'XPBR31.SA',
    'STOC34.SA'
]

ibrx_selecao = [
    'PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'BBDC4.SA', 'BBAS3.SA', 'B3SA3.SA', 'ABEV3.SA',
    'WEGE3.SA', 'AXIA3.SA', 'SUZB3.SA', 'RENT3.SA', 'RADL3.SA', 'EQTL3.SA', 'LREN3.SA',
    'PRIO3.SA', 'HAPV3.SA', 'GGBR4.SA', 'VBBR3.SA', 'SBSP3.SA', 'CMIG4.SA', 'CPLE3.SA',
    'ENEV3.SA', 'TIMS3.SA', 'TOTS3.SA', 'EGIE3.SA', 'CSAN3.SA', 'ALOS3.SA', 'DIRR3.SA',
    'VIVT3.SA', 'KLBN11.SA', 'UGPA3.SA', 'PSSA3.SA', 'CYRE3.SA', 'ASAI3.SA', 'RAIL3.SA',
    'ISAE3.SA', 'CSNA3.SA', 'MGLU3.SA', 'EMBJ3.SA', 'TAEE11.SA', 'BBSE3.SA', 'FLRY3.SA',
    'MULT3.SA', 'TFCO4.SA', 'LEVE3.SA', 'CPFE3.SA', 'GOAU4.SA', 'MRVE3.SA', 'YDUQ3.SA',
    'SMTO3.SA', 'SLCE3.SA', 'CVCB3.SA', 'USIM5.SA', 'BRAP4.SA', 'BRAV3.SA', 'EZTC3.SA',
    'PCAR3.SA', 'AUAU3.SA', 'DXCO3.SA', 'CASH3.SA', 'VAMO3.SA', 'AZZA3.SA', 'AURE3.SA',
    'BEEF3.SA', 'ECOR3.SA', 'FESA4.SA', 'POMO4.SA', 'CURY3.SA', 'INTB3.SA', 'JHSF3.SA',
    'LIGT3.SA', 'LOGG3.SA', 'MDIA3.SA', 'MBRF3.SA', 'NEOE3.SA', 'QUAL3.SA', 'RAPT4.SA',
    'ROMI3.SA', 'SANB11.SA', 'SIMH3.SA', 'TEND3.SA', 'VULC3.SA', 'PLPL3.SA', 'CEAB3.SA',
    'UNIP6.SA', 'LWSA3.SA', 'BPAC11.SA', 'GMAT3.SA', 'CXSE3.SA', 'ABCB4.SA', 'CSMG3.SA',
    'SAPR11.SA', 'GRND3.SA', 'BRAP3.SA', 'LAVV3.SA', 'RANI3.SA', 'ITSA3.SA', 'ALUP11.SA',
    'FIQE3.SA', 'COGN3.SA', 'IRBR3.SA', 'SEER3.SA', 'ANIM3.SA', 'JSLG3.SA', 'POSI3.SA',
    'MYPK3.SA', 'SOJA3.SA', 'BLAU3.SA', 'PGMN3.SA', 'TUPY3.SA', 'VVEO3.SA', 'MELK3.SA',
    'SHUL4.SA', 'BRSR6.SA',
]

def colorir_lucro(row):
    if 'Resultado Atual' in row and isinstance(row['Resultado Atual'], str) and row['Resultado Atual'].startswith('+'):
        return ['color: #00FF00; font-weight: bold'] * len(row)
    return [''] * len(row)

# 3. INTERFACE DE ABAS
st.title("📊 Estratégia: Canais de Keltner")
aba_padrao, aba_pm, aba_stop, aba_individual, aba_futuros = st.tabs([
    "📡 Radar (Padrão)", "📡 Radar (PM)", "🛡️ Alvo & Stop", "🔬 Raio-X Individual", "📉 Raio-X Futuros"
])

# ==========================================
# ABA 1: RADAR PADRÃO (KELTNER)
# ==========================================
with aba_padrao:
    st.subheader("📡 Radar Padrão (Entrada na Banda Inferior & Alvo Fixo)")
    st.markdown("O robô faz a entrada no exato momento em que o preço **toca a banda inferior** de Keltner e aguarda o alvo.")
    
    cp1, cp2, cp3 = st.columns(3)
    with cp1:
        lista_padrao = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"], key="pk_lista")
        ativos_padrao = bdrs_elite if lista_padrao == "BDRs Elite" else ibrx_selecao if lista_padrao == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        periodo_padrao = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=3, key="pk_per")
    with cp2:
        alvo_padrao = st.number_input("Alvo de Lucro (%):", value=5.0, step=0.5, key="pk_alvo")
        # Campo novo para o multiplicador do Keltner
        keltner_mult = st.number_input("Multiplicador Keltner:", min_value=0.5, max_value=10.0, value=3.0, step=0.1, key="pk_mult")
    with cp3:
        capital_padrao = st.number_input("Capital por Trade (R$):", value=10000.0, step=1000.0, key="pk_cap")
        tempo_padrao = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="pk_tmp")

    btn_iniciar_padrao = st.button("🚀 Iniciar Varredura Padrão", type="primary", use_container_width=True, key="pk_btn")

    if btn_iniciar_padrao:
        if tempo_padrao == '15m' and periodo_padrao not in ['1mo', '3mo']: periodo_padrao = '60d'
        elif tempo_padrao == '60m' and periodo_padrao in ['5y', 'max']: periodo_padrao = '2y'

        intervalo_tv = tradutor_intervalo.get(tempo_padrao, Interval.in_daily)
        alvo_dec = alvo_padrao / 100

        ls_sinais_p, ls_abertos_p, ls_resumo_p = [], [], []
        p_bar_p = st.progress(0)
        s_text_p = st.empty()

        for idx, ativo_raw in enumerate(ativos_padrao):
            ativo = ativo_raw.replace('.SA', '')
            s_text_p.text(f"🔍 Analisando Keltner (Padrão): {ativo} ({idx+1}/{len(ativos_padrao)})")
            p_bar_p.progress((idx + 1) / len(ativos_padrao))

            try:
                df_full = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=5000)
                if df_full is None or len(df_full) < 50: continue

                df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                df_full = df_full.dropna()
                
                # --- CÁLCULO DO KELTNER ---
                # O pandas_ta retorna 3 colunas: Inferior, Base (Média) e Superior
                kc = ta.kc(df_full['High'], df_full['Low'], df_full['Close'], length=20, scalar=keltner_mult)
                if kc is None or kc.empty: continue
                
                # Pegando dinamicamente o nome da coluna da Banda Inferior (KCL)
                coluna_inferior = [c for c in kc.columns if c.startswith('KCL')][0]
                df_full['Keltner_Inf'] = kc[coluna_inferior]
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
                        
                        if df_back['High'].iloc[i] >= take_profit:
                            trades.append({'Lucro (R$)': float(capital_padrao) * alvo_dec, 'Drawdown_Raw': ((min_price_in_trade / preco_entrada) - 1) * 100})
                            em_pos = False
                            continue

                    # CONDIÇÃO DE ENTRADA: Low encosta na Banda Inferior
                    condicao_entrada = df_back['Low'].iloc[i] <= df_back['Keltner_Inf'].iloc[i]
                    
                    if condicao_entrada and not em_pos:
                        em_pos = True
                        d_ent = df_back[col_data].iloc[i]
                        # O preço de entrada é exatamente a banda inferior que foi tocada
                        preco_entrada = df_back['Keltner_Inf'].iloc[i] 
                        min_price_in_trade = df_back['Low'].iloc[i]
                        take_profit = preco_entrada * (1 + alvo_dec)

                if em_pos:
                    resultado_atual = ((df_back['Close'].iloc[-1] / preco_entrada) - 1) * 100
                    queda_max = ((min_price_in_trade / preco_entrada) - 1) * 100
                    ls_abertos_p.append({
                        'Ativo': ativo, 'Entrada': d_ent.strftime('%d/%m %H:%M') if tempo_padrao in ['15m', '60m'] else d_ent.strftime('%d/%m/%Y'),
                        'Dias': (df_back[col_data].iloc[-1] - d_ent).days, 'PM': f"R$ {preco_entrada:.2f}",
                        'Cotação Atual': f"R$ {df_back['Close'].iloc[-1]:.2f}",
                        'Prej. Máx': f"{queda_max:.2f}%",
                        'Resultado Atual': f"+{resultado_atual:.2f}%" if resultado_atual > 0 else f"{resultado_atual:.2f}%"
                    })
                else:
                    # Sinal de Hoje: Tocou na banda na barra mais recente
                    tem_sinal = df_full['Low'].iloc[-1] <= df_full['Keltner_Inf'].iloc[-1]
                    if tem_sinal: ls_sinais_p.append({'Ativo': ativo, 'Preço Atual': f"R$ {df_full['Close'].iloc[-1]:.2f}", 'Banda Inf': f"R$ {df_full['Keltner_Inf'].iloc[-1]:.2f}"})

                if len(trades) > 0:
                    df_t = pd.DataFrame(trades)
                    ls_resumo_p.append({
                        'Ativo': ativo, 'Trades': len(df_t), 'Pior Queda': f"{df_t['Drawdown_Raw'].min():.2f}%", 'Lucro R$': df_t['Lucro (R$)'].sum()
                    })
            except Exception as e: pass
            time.sleep(0.05)

        s_text_p.empty()
        p_bar_p.empty()

        # --- EXIBIÇÃO DOS RESULTADOS ---
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

# ESPAÇO PARA AS PRÓXIMAS ABAS
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
        # --- NOVO CAMPO: DISTÂNCIA DO PM ---
        pm_drop = st.number_input("Queda para novo PM (%):", value=10.0, step=1.0, key="rk_drop")
    with cr3:
        capital_pm = st.number_input("Capital por Sinal (R$):", value=10000.0, step=1000.0, key="rk_cap")
        tempo_pm = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="rk_tmp")
        
    btn_iniciar_pm = st.button("🚀 Iniciar Varredura PM", type="primary", use_container_width=True, key="rk_btn")

    if btn_iniciar_pm:
        if tempo_pm == '15m' and periodo_pm not in ['1mo', '3mo']: periodo_pm = '60d'
        elif tempo_pm == '60m' and periodo_pm in ['5y', 'max']: periodo_pm = '2y'

        intervalo_tv = tradutor_intervalo.get(tempo_pm, Interval.in_daily)
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
                df_full = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=5000)
                if df_full is None or len(df_full) < 50: continue

                df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                df_full = df_full.dropna()
                
                # --- CÁLCULO DO KELTNER ---
                kc = ta.kc(df_full['High'], df_full['Low'], df_full['Close'], length=20, scalar=keltner_mult_pm)
                if kc is None or kc.empty: continue
                coluna_inferior = [c for c in kc.columns if c.startswith('KCL')][0]
                df_full['Keltner_Inf'] = kc[coluna_inferior]
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

                trades = []
                em_pos = False
                df_back = df.reset_index()
                col_data = df_back.columns[0]

                for i in range(1, len(df_back)):
                    if em_pos:
                        if df_back['Low'].iloc[i] < min_price_in_trade: 
                            min_price_in_trade = df_back['Low'].iloc[i]
                            
                        # 1. Verifica se atingiu o Alvo
                        if df_back['High'].iloc[i] >= take_profit:
                            lucro_rs = capital_total * alvo_decimal
                            trades.append({'Lucro (R$)': lucro_rs, 'Drawdown_Raw': ((min_price_in_trade / preco_entrada_inicial) - 1) * 100})
                            em_pos = False
                            continue 
                            
                        # 2. Verifica se caiu o suficiente para o novo PM
                        if df_back['Low'].iloc[i] <= next_pm_price:
                            qtd_pms += 1
                            # Assume a compra exatamente no preço do gatilho estipulado
                            preco_compra = next_pm_price 
                            capital_total += float(capital_pm)
                            qtd_acoes += float(capital_pm) / preco_compra
                            preco_medio = capital_total / qtd_acoes
                            # Recalcula alvo e a próxima barreira de queda
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
                        # Define a primeira barreira de queda para o PM (ex: 10% abaixo da entrada)
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
            time.sleep(0.05)

        status_text.empty()
        progress_bar.empty()

        # --- EXIBIÇÃO DOS RESULTADOS ---
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
with aba_stop: st.info("Pronto para receber o código de Alvo & Stop do Keltner.")
with aba_individual: st.info("Pronto para receber o Raio-X Individual do Keltner.")
with aba_futuros: st.info("Pronto para receber o Raio-X Futuros do Keltner.")
