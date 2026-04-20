import streamlit as st
from tvDatafeed import TvDatafeed, Interval
import pandas as pd
import pandas_ta as ta
import time
import warnings

warnings.filterwarnings('ignore')

# 1. SEGURANÇA (Verifica se logou no app.py)
if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

# 2. CONEXÃO E LISTAS
@st.cache_resource
def get_tv_connection():
    return TvDatafeed()

tv = get_tv_connection()

# --- CONFIGURAÇÃO DO TELEGRAM ---
TOKEN_TELEGRAM = "COLE_AQUI_AQUELE_TOKEN_LONGO"
CHAT_ID_TELEGRAM = "COLE_AQUI_O_NUMERO_DO_ID"

def enviar_alerta_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage"
    payload = {"chat_id": CHAT_ID_TELEGRAM, "text": mensagem}
    try:
        # Manda a mensagem sem travar o restante do código
        import requests
        requests.post(url, json=payload, timeout=5)
    except:
        pass
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
col_titulo, col_botao = st.columns([4, 1])

with col_titulo:
    st.title("📈 Estratégia: IFR")

with col_botao:
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.link_button("📖 Ler Manual", "https://seusite.com/manual_ifr", use_container_width=True)

aba_padrao, aba_pm, aba_stop, aba_individual, aba_futuros = st.tabs([
    "📡 Radar (Padrão)", "📡 Radar (PM)", "🛡️ Alvo & Stop", "🔬 Raio-X Individual", "📉 Raio-X Futuros"
])

# ==========================================
# ABA 1: RADAR PADRÃO
# ==========================================
with aba_padrao:
    st.subheader("📡 Radar Padrão (Entrada Única & Alvo Fixo)")
    
    cp1, cp2, cp3 = st.columns(3)
    with cp1:
        lista_padrao = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"], key="p_lista")
        ativos_padrao = bdrs_elite if lista_padrao == "BDRs Elite" else ibrx_selecao if lista_padrao == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        periodo_padrao = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=3, key="p_per")
    with cp2:
        alvo_padrao = st.number_input("Alvo de Lucro (%):", value=5.0, step=0.5, key="p_alvo")
        ifr_padrao = st.number_input("Período do IFR:", min_value=2, max_value=50, value=8, step=1, key="p_ifr")
    with cp3:
        capital_padrao = st.number_input("Capital por Trade (R$):", value=10000.0, step=1000.0, key="p_cap")
        tempo_padrao = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="p_tmp")

    btn_iniciar_padrao = st.button("🚀 Iniciar Varredura Padrão", type="primary", use_container_width=True, key="p_btn")

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
            s_text_p.text(f"🔍 Analisando (Padrão): {ativo} ({idx+1}/{len(ativos_padrao)})")
            p_bar_p.progress((idx + 1) / len(ativos_padrao))

            try:
                df_full = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=5000)
                if df_full is None or len(df_full) < 50: continue

                df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                df_full = df_full.dropna()
                
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
                        if df_back['High'].iloc[i] >= take_profit:
                            trades.append({'Lucro (R$)': float(capital_padrao) * alvo_dec, 'Drawdown_Raw': ((min_price_in_trade / preco_entrada) - 1) * 100})
                            em_pos = False
                            continue

                    condicao_entrada = (df_back['IFR_Prev'].iloc[i] < 25) and (df_back['IFR'].iloc[i] >= 25)
                    if condicao_entrada and not em_pos:
                        em_pos = True
                        d_ent = df_back[col_data].iloc[i]
                        preco_entrada = df_back['Close'].iloc[i]
                        min_price_in_trade = df_back['Low'].iloc[i]
                        take_profit = preco_entrada * (1 + alvo_dec)

                if em_pos:
                    res_atual = ((df_back['Close'].iloc[-1] / preco_entrada) - 1) * 100
                    q_max = ((min_price_in_trade / preco_entrada) - 1) * 100
                    ls_abertos_p.append({
                        'Ativo': ativo, 'Entrada': d_ent.strftime('%d/%m %H:%M') if tempo_padrao in ['15m', '60m'] else d_ent.strftime('%d/%m/%Y'),
                        'Dias': (df_back[col_data].iloc[-1] - d_ent).days, 'PM': f"R$ {preco_entrada:.2f}",
                        'Cotação Atual': f"R$ {df_back['Close'].iloc[-1]:.2f}",
                        'Prej. Máx': f"{q_max:.2f}%",
                        'Resultado Atual': f"+{res_atual:.2f}%" if res_atual > 0 else f"{res_atual:.2f}%"
                    })
                else:
                    tem_sinal = (df_full['IFR_Prev'].iloc[-1] < 25) and (df_full['IFR'].iloc[-1] >= 25)
                    if tem_sinal: ls_sinais_p.append({'Ativo': ativo, 'Preço Atual': f"R$ {df_full['Close'].iloc[-1]:.2f}"})

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
            time.sleep(0.05)

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
    
    st.markdown("##### ⚙️ Configurações da Varredura")
    cr1, cr2, cr3 = st.columns(3)
    with cr1:
        lista_pm = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"], key="r1_lista")
        ativos_pm = bdrs_elite if lista_pm == "BDRs Elite" else ibrx_selecao if lista_pm == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        periodo_pm = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=3, key="r1_per")
    with cr2:
        alvo_pm = st.number_input("Alvo (%):", value=3.0, step=0.5, key="r1_alvo")
        ifr_pm = st.number_input("Período do IFR:", min_value=2, max_value=50, value=8, step=1, key="r1_ifr")
    with cr3:
        capital_pm = st.number_input("Capital por Sinal (R$):", value=10000.0, step=1000.0, key="r1_cap")
        tempo_pm = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="r1_tmp")
        
    btn_iniciar_pm = st.button("🚀 Iniciar Varredura PM", type="primary", use_container_width=True, key="r1_btn")

    if btn_iniciar_pm:
        if tempo_pm == '15m' and periodo_pm not in ['1mo', '3mo']: periodo_pm = '60d'
        elif tempo_pm == '60m' and periodo_pm in ['5y', 'max']: periodo_pm = '2y'

        intervalo_tv = tradutor_intervalo.get(tempo_pm, Interval.in_daily)
        alvo_decimal = alvo_pm / 100

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

                    condicao_entrada = (df_back['IFR_Prev'].iloc[i] < 25) and (df_back['IFR'].iloc[i] >= 25)
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
                    tem_sinal = (df_full['IFR_Prev'].iloc[-1] < 25) and (df_full['IFR'].iloc[-1] >= 25)
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
            time.sleep(0.05)

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
# ABA 3: RADAR EM MASSA (ALVO & STOP LOSS)
# ==========================================
with aba_stop:
    st.subheader("🛡️ Radar de Risco Definido (Alvo & Stop Loss)")
    st.markdown("Nesta estratégia, o robô faz apenas **uma** entrada por sinal (sem preço médio) e aguarda o atingimento do Alvo ou do Stop de proteção.")
    
    st.markdown("##### ⚙️ Configurações da Varredura")
    cs1, cs2, cs3 = st.columns(3)
    with cs1:
        lista_stop = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"], key="s_lista")
        ativos_stop = bdrs_elite if lista_stop == "BDRs Elite" else ibrx_selecao if lista_stop == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        periodo_stop = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=3, key="s_per")
    with cs2:
        alvo_stop = st.number_input("Alvo de Lucro (%):", value=5.0, step=0.5, key="s_alvo")
        perda_stop = st.number_input("Stop Loss (%):", value=5.0, step=0.5, key="s_perda")
    with cs3:
        capital_stop = st.number_input("Capital por Trade (R$):", value=10000.0, step=1000.0, key="s_cap")
        tempo_stop = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="s_tmp")
        ifr_stop = st.number_input("Período do IFR:", min_value=2, max_value=50, value=8, step=1, key="s_ifr")
    
    btn_iniciar_stop = st.button("🚀 Iniciar Varredura (Alvo & Stop)", type="primary", use_container_width=True, key="s_btn")

    if btn_iniciar_stop:
        if tempo_stop == '15m' and periodo_stop not in ['1mo', '3mo']: periodo_stop = '60d'
        elif tempo_stop == '60m' and periodo_stop in ['5y', 'max']: periodo_stop = '2y'

        intervalo_tv = tradutor_intervalo.get(tempo_stop, Interval.in_daily)
        alvo_dec = alvo_stop / 100
        stop_dec = perda_stop / 100

        ls_sinais, ls_abertos, ls_resumo = [], [], []
        p_bar = st.progress(0)
        s_text = st.empty()

        for idx, ativo_raw in enumerate(ativos_stop):
            ativo = ativo_raw.replace('.SA', '')
            s_text.text(f"🔍 Analisando (Stop): {ativo} ({idx+1}/{len(ativos_stop)})")
            p_bar.progress((idx + 1) / len(ativos_stop))

            try:
                df_full = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=5000)
                if df_full is None or len(df_full) < 50: continue

                df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                df_full = df_full.dropna()
                
                df_full['IFR'] = ta.rsi(df_full['Close'], length=ifr_stop)
                df_full['IFR_Prev'] = df_full['IFR'].shift(1)
                df_full = df_full.dropna()

                data_atual = df_full.index[-1]
                if periodo_stop == '1mo': data_corte = data_atual - pd.DateOffset(months=1)
                elif periodo_stop == '3mo': data_corte = data_atual - pd.DateOffset(months=3)
                elif periodo_stop == '6mo': data_corte = data_atual - pd.DateOffset(months=6)
                elif periodo_stop == '1y': data_corte = data_atual - pd.DateOffset(years=1)
                elif periodo_stop == '2y': data_corte = data_atual - pd.DateOffset(years=2)
                elif periodo_stop == '5y': data_corte = data_atual - pd.DateOffset(years=5)
                elif periodo_stop == '60d': data_corte = data_atual - pd.DateOffset(days=60)
                else: data_corte = df_full.index[0]

                df = df_full[df_full.index >= data_corte].copy()
                if len(df) == 0: continue

                trades = []
                em_pos = False
                df_back = df.reset_index()
                col_data = df_back.columns[0]
                vitorias, derrotas = 0, 0

                for i in range(1, len(df_back)):
                    if em_pos:
                        if df_back['Low'].iloc[i] <= stop_price:
                            trades.append({'Lucro (R$)': - (float(capital_stop) * stop_dec), 'Situação': 'Stop Acionado ❌'})
                            derrotas += 1
                            em_pos = False
                            continue
                        
                        elif df_back['High'].iloc[i] >= take_profit:
                            trades.append({'Lucro (R$)': float(capital_stop) * alvo_dec, 'Situação': 'Gain Atingido ✅'})
                            vitorias += 1
                            em_pos = False
                            continue

                    condicao_entrada = (df_back['IFR_Prev'].iloc[i] < 25) and (df_back['IFR'].iloc[i] >= 25)
                    if condicao_entrada and not em_pos:
                        em_pos = True
                        d_ent = df_back[col_data].iloc[i]
                        preco_entrada = df_back['Close'].iloc[i]
                        take_profit = preco_entrada * (1 + alvo_dec)
                        stop_price = preco_entrada * (1 - stop_dec)

                if em_pos:
                    resultado_atual = ((df_back['Close'].iloc[-1] / preco_entrada) - 1) * 100
                    ls_abertos.append({
                        'Ativo': ativo, 'Entrada': d_ent.strftime('%d/%m %H:%M') if tempo_stop in ['15m', '60m'] else d_ent.strftime('%d/%m/%Y'),
                        'Dias': (df_back[col_data].iloc[-1] - d_ent).days, 'Preço Compra': f"R$ {preco_entrada:.2f}",
                        'Cotação Atual': f"R$ {df_back['Close'].iloc[-1]:.2f}",
                        'Stop Armado': f"R$ {stop_price:.2f}", 'Alvo Armado': f"R$ {take_profit:.2f}",
                        'Resultado Atual': f"+{resultado_atual:.2f}%" if resultado_atual > 0 else f"{resultado_atual:.2f}%"
                    })
                else:
                    tem_sinal = (df_full['IFR_Prev'].iloc[-1] < 25) and (df_full['IFR'].iloc[-1] >= 25)
                    if tem_sinal: ls_sinais.append({'Ativo': ativo, 'Preço Atual': f"R$ {df_full['Close'].iloc[-1]:.2f}"})

                if len(trades) > 0:
                    df_t = pd.DataFrame(trades)
                    taxa_acerto = (vitorias / len(df_t)) * 100
                    lucro_tot = df_t['Lucro (R$)'].sum()
                    invest = float(capital_stop) * len(df_t)
                    res_pct = (lucro_tot / invest) * 100 if invest > 0 else 0
                    ls_resumo.append({
                        'Ativo': ativo, 
                        'Total Trades': len(df_t), 
                        'Acertos ✅': vitorias, 
                        'Stops ❌': derrotas, 
                        'Taxa de Acerto': f"{taxa_acerto:.2f}%", 
                        'Investimento': f"R$ {invest:,.2f}",
                        'Lucro R$': lucro_tot,
                        'Resultado': f"{res_pct:.2f}%"
                    })

            except Exception as e: pass
            time.sleep(0.05)

        s_text.empty()
        p_bar.empty()

        st.subheader(f"🚀 Oportunidades Hoje (Radar Stop | IFR {ifr_stop})")
        if len(ls_sinais) > 0: st.dataframe(pd.DataFrame(ls_sinais), use_container_width=True, hide_index=True)
        else: st.info("Nenhum ativo deu sinal de entrada na última barra.")

        st.subheader("⏳ Operações em Andamento (Vigiando Stop/Alvo)")
        if len(ls_abertos) > 0:
            df_abertos = pd.DataFrame(ls_abertos).sort_values(by='Dias', ascending=False)
            st.dataframe(df_abertos.style.apply(colorir_lucro, axis=1), use_container_width=True, hide_index=True)
        else: st.success("Sua carteira está limpa.")

        st.subheader(f"📊 Top 10 Histórico ({tradutor_periodo_nome.get(periodo_stop, periodo_stop)})")
        if len(ls_resumo) > 0:
            df_resumo = pd.DataFrame(ls_resumo).sort_values(by='Lucro R$', ascending=False).head(10)
            df_resumo['Lucro R$'] = df_resumo['Lucro R$'].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(df_resumo, use_container_width=True, hide_index=True)
        else: st.warning("Nenhuma operação finalizada.")

# ==========================================
# ABA 4: RAIO-X DO ATIVO INDIVIDUAL
# ==========================================
with aba_individual:
    st.subheader("🔬 Raio-X Detalhado: Backtest & Status Atual")
    st.markdown("Veja o histórico de acertos e o status completo se o ativo estiver com operação aberta agora.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        lupa_ativo = st.text_input("Ativo (Ex: TSLA34):", value="TSLA34", key="l2_ativo")
        lupa_estrategia = st.selectbox("Estratégia:", ["Padrão (Sem PM)", "PM Dinâmico", "Alvo & Stop Loss"], key="l2_est")
        lupa_periodo = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=3, key="l2_per")
    with col2:
        lupa_alvo = st.number_input("Alvo (%):", value=3.0, step=0.5, key="l2_alvo")
        lupa_stop = st.number_input("Stop Loss (%):", value=5.0, step=0.5, key="l2_stop") if lupa_estrategia == "Alvo & Stop Loss" else 0.0
        lupa_capital = st.number_input("Capital Base (R$):", value=10000.0, step=1000.0, key="l2_cap")
    with col3:
        lupa_tempo = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk', '1mo'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal', '1mo': 'Mensal'}[x], key="l2_tmp")
        lupa_ifr_periodo = st.number_input("Período IFR:", min_value=2, max_value=50, value=8, step=1, key="l2_ifr")
        
    btn_raiox = st.button("🔍 Rodar Análise Completa", type="primary", use_container_width=True, key="l2_btn")

    if btn_raiox:
        ativo = lupa_ativo.strip().upper().replace('.SA', '')
        
        mapa_intervalos = {
            '15m': Interval.in_15_minute,
            '60m': Interval.in_1_hour,
            '1d': Interval.in_daily,
            '1wk': Interval.in_weekly,
            '1mo': Interval.in_monthly
        }
        intervalo_tv = mapa_intervalos.get(lupa_tempo, Interval.in_daily)

        with st.spinner(f'Calculando dados de {ativo}...'):
            try:
                df_full = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=5000)
                
                if df_full is not None and len(df_full) > 50:
                    df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
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
                        condicao_entrada = (df_back['IFR_Prev'].iloc[i] < 25) and (df_back['IFR'].iloc[i] >= 25)

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
                            elif lupa_estrategia == "Alvo & Stop Loss" and df_back['Low'].iloc[i] <= stop_p:
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
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("Lucro Total", f"R$ {df_t['Lucro (R$)'].sum():,.2f}")
                        m2.metric("Duração Média", f"{df_t['Duração'].mean():.1f} dias")
                        m3.metric("Operações Fechadas", len(df_t))
                        if lupa_estrategia == "Alvo & Stop Loss":
                            taxa = (vitorias/len(df_t))*100
                            m4.metric("Taxa de Acerto", f"{taxa:.1f}%")
                        else:
                            m4.metric("Pior Queda", f"{df_t['Queda Máx'].min():.2f}%")
                        
                        df_t['Queda Máx'] = df_t['Queda Máx'].map("{:.2f}%".format)
                        st.dataframe(df_t, use_container_width=True, hide_index=True)
                    else:
                        st.info("Nenhuma operação fechada no período de estudo.")
                else:
                    st.error("Ativo não encontrado ou base de dados vazia.")
            except Exception as e:
                st.error(f"Erro no processamento: {e}")

# ==========================================
# ABA 5: RAIO-X FUTUROS (VERSÃO FINAL)
# ==========================================
with aba_futuros:
    st.subheader("📈 Raio-X Mercado Futuro (WIN, WDO, etc)")
    st.markdown("Focado em **15 minutos** para garantir a estabilidade do backtest.")
    
    cf1, cf2, cf3 = st.columns(3)
    with cf1:
        mapa_futuros = {"WINFUT (Mini Índice)": "WIN1!", "WDOFUT (Mini Dólar)": "WDO1!"}
        fut_selecionado = st.selectbox("Selecione o Ativo:", options=list(mapa_futuros.keys()), key="f_ativo_sel")
        fut_ativo = mapa_futuros[fut_selecionado] 
        fut_estrategia = st.selectbox("Estratégia:", ["Padrão (Sem PM)", "PM Dinâmico", "Alvo & Stop Loss"], key="f_est")
        fut_periodo = st.selectbox("Período:", options=['3mo', '6mo', '1y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=1, key="f_per")
    with cf2:
        fut_alvo = st.number_input("Alvo (Pontos):", value=300, step=50, key="f_alvo")
        if fut_estrategia == "Alvo & Stop Loss":
            fut_stop = st.number_input("Stop Loss (Pontos):", value=200, step=50, key="f_stop")
        else:
            fut_stop = 0 
            st.write("") 
        fut_contratos = st.number_input("Contratos:", value=1, step=1, key="f_cont")
    with cf3:
        valor_mult_padrao = 0.20 if "WIN" in fut_selecionado else 10.00
        fut_multiplicador = st.number_input("Multiplicador (R$):", value=valor_mult_padrao, step=0.10, format="%.2f", key="f_mult")
        fut_tempo = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d'], index=0, key="f_tmp")
        fut_ifr = st.number_input("Período IFR:", min_value=2, max_value=50, value=8, step=1, key="f_ifr")
        
    fut_zerar_daytrade = st.checkbox("⏰ Zeragem Automática no Fim do Dia", value=True, key="f_zerar")
    btn_raiox_futuros = st.button("🚀 Gerar Raio-X", type="primary", use_container_width=True, key="f_btn")

    if btn_raiox_futuros:
        intervalo_tv = tradutor_intervalo.get(fut_tempo, Interval.in_15_minute)
        with st.spinner(f'Analisando {fut_selecionado}...'):
            try:
                df_full = tv.get_hist(symbol=fut_ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=10000)
                if df_full is not None and len(df_full) > 50:
                    df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
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

                        cond_ent = (df_back['IFR_Prev'].iloc[i] < 25) and (df_back['IFR'].iloc[i] >= 25)
                        
                        if em_pos:
                            if fut_estrategia == "PM Dinâmico":
                                if df_back['High'].iloc[i] >= take_profit:
                                    luc = fut_alvo * contratos_atuais * fut_multiplicador
                                    trades.append({'Entrada': d_ent.strftime('%d/%m/%Y %H:%M'), 'Saída': d_at.strftime('%d/%m/%Y %H:%M'), 'Lucro (R$)': luc, 'Situação': 'Ganho ✅'})
                                    em_pos, vitorias = False, vitorias + 1
                                    continue
                            else:
                                if fut_estrategia == "Alvo & Stop Loss" and df_back['Low'].iloc[i] <= stop_p:
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

                    # --- PAINEL DE RESULTADOS (VERSÃO INTELIGENTE) ---
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

                        st.dataframe(df_t, use_container_width=True, hide_index=True)
                    else:
                        st.warning("Nenhuma operação encontrada.")
            except Exception as e: st.error(f"Erro: {e}")
