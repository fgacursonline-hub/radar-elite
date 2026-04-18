import streamlit as st
from tvDatafeed import TvDatafeed, Interval
import pandas as pd
import pandas_ta as ta
import time
import warnings

warnings.filterwarnings('ignore')

# --- CONFIGURAÇÃO DA PÁGINA WEB ---
st.set_page_config(page_title="Caçadores de Elite", layout="wide", page_icon="🎯")

# --- CONTROLE DE ACESSO (LOGIN) ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

alunos_cadastrados = {
    "aluno": "elite123",
    "joao": "senha123",
    "maria": "bolsadevalores",
    "admin": "suasenhaforte"
}

def tela_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.write("")
        st.write("")
        st.write("")
        st.markdown("<h1 style='text-align: center;'>🎯 Caçadores de Elite</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Área Restrita do Radar Quantitativo</p>", unsafe_allow_html=True)
        
        with st.form("form_login"):
            usuario = st.text_input("Usuário").lower().strip()
            senha = st.text_input("Senha", type="password")
            submit = st.form_submit_button("Entrar no Sistema", use_container_width=True)
            
            if submit:
                if usuario in alunos_cadastrados and alunos_cadastrados[usuario] == senha:
                    st.session_state['autenticado'] = True
                    st.rerun()  
                else:
                    st.error("❌ Usuário ou senha incorretos. Tente novamente.")

# --- O CORAÇÃO DO SISTEMA (SÓ RODA SE AUTENTICADO) ---
if not st.session_state['autenticado']:
    tela_login()
else:
    with st.sidebar:
        if st.button("🚪 Sair do Sistema"):
            st.session_state['autenticado'] = False
            st.rerun()
        st.divider()

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

    st.title("🎯 Plataforma Caçadores de Elite")
    st.markdown("Ferramentas quantitativas para exploração e análise de ativos.")
    
    # CRIANDO AS DUAS ABAS PRINCIPAIS DO SITE
    aba_radar, aba_lupa = st.tabs(["📡 Radar em Massa", "🔬 Raio-X do Ativo"])

    # ==========================================
    # ABA 1: RADAR EM MASSA (CÓDIGO ORIGINAL)
    # ==========================================
    with aba_radar:
        with st.sidebar:
            st.header("⚙️ Filtros do Radar")
            lista_escolhida = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"])
            ativos_selecionados = bdrs_elite if lista_escolhida == "BDRs Elite" else ibrx_selecao if lista_escolhida == "IBrX Seleção" else bdrs_elite + ibrx_selecao
            periodo_selecionado = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=3)
            modo_entrada = st.selectbox("Gatilho de Entrada:", options=['cruzamento', 'toque'], format_func=lambda x: 'Repique (Cruza > 25)' if x == 'cruzamento' else 'Faca Caindo (Toque <= 25)')
            txt_alvo = st.number_input("Alvo (%):", value=3.0, step=0.5)
            txt_pm = st.number_input("Gatilho PM (%):", value=0.0, step=0.5)
            txt_capital = st.number_input("Capital/Trade (R$):", value=10000.0, step=1000.0)
            tempo = st.radio("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x])
            btn_iniciar = st.button("🚀 Iniciar Varredura do Radar", use_container_width=True, type="primary")

        def colorir_lucro(row):
            if isinstance(row['Resultado Atual'], str) and row['Resultado Atual'].startswith('+'):
                return ['color: #00FF00; font-weight: bold'] * len(row)
            return [''] * len(row)

        if btn_iniciar:
            if tempo == '15m' and periodo_selecionado not in ['1mo', '3mo']: periodo_selecionado = '60d'
            elif tempo == '60m' and periodo_selecionado in ['5y', 'max']: periodo_selecionado = '2y'

            intervalo_tv = tradutor_intervalo.get(tempo, Interval.in_daily)
            alvo_decimal = txt_alvo / 100
            gatilho_pm_decimal = txt_pm / 100

            lista_sinais, lista_abertos, lista_resumo = [], [], []
            progress_bar = st.progress(0)
            status_text = st.empty()

            for idx, ativo_raw in enumerate(ativos_selecionados):
                ativo = ativo_raw.replace('.SA', '')
                status_text.text(f"🔍 Analisando: {ativo} ({idx+1}/{len(ativos_selecionados)})")
                progress_bar.progress((idx + 1) / len(ativos_selecionados))

                try:
                    df_full = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=5000)
                    if df_full is None or len(df_full) < 50: continue

                    df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                    df_full = df_full.dropna()
                    df_full['IFR'] = ta.rsi(df_full['Close'], length=8)
                    df_full['IFR_Prev'] = df_full['IFR'].shift(1)
                    df_full = df_full.dropna()

                    data_atual = df_full.index[-1]
                    if periodo_selecionado == '1mo': data_corte = data_atual - pd.DateOffset(months=1)
                    elif periodo_selecionado == '3mo': data_corte = data_atual - pd.DateOffset(months=3)
                    elif periodo_selecionado == '6mo': data_corte = data_atual - pd.DateOffset(months=6)
                    elif periodo_selecionado == '1y': data_corte = data_atual - pd.DateOffset(years=1)
                    elif periodo_selecionado == '2y': data_corte = data_atual - pd.DateOffset(years=2)
                    elif periodo_selecionado == '5y': data_corte = data_atual - pd.DateOffset(years=5)
                    elif periodo_selecionado == '60d': data_corte = data_atual - pd.DateOffset(days=60)
                    else: data_corte = df_full.index[0]

                    df = df_full[df_full.index >= data_corte].copy()
                    if len(df) == 0: continue

                    trades = []
                    em_pos = False
                    df_back = df.reset_index()
                    col_data = df_back.columns[0]

                    for i in range(1, len(df_back)):
                        if not em_pos:
                            condicao_entrada = False
                            if modo_entrada == 'cruzamento' and (df_back['IFR_Prev'].iloc[i] < 25) and (df_back['IFR'].iloc[i] >= 25): condicao_entrada = True
                            elif modo_entrada == 'toque' and df_back['IFR'].iloc[i] <= 25: condicao_entrada = True

                            if condicao_entrada:
                                em_pos = True
                                entrada_original = df_back['Close'].iloc[i]
                                preco_medio = entrada_original
                                d_ent = df_back[col_data].iloc[i]
                                take_profit = preco_medio * (1 + alvo_decimal)
                                min_price_in_trade = entrada_original
                                pm_realizado = False
                                capital_alocado = txt_capital
                        else:
                            if df_back['Low'].iloc[i] < min_price_in_trade: min_price_in_trade = df_back['Low'].iloc[i]

                            if gatilho_pm_decimal < 0 and not pm_realizado:
                                preco_acionamento_pm = entrada_original * (1 + gatilho_pm_decimal)
                                if df_back['Low'].iloc[i] <= preco_acionamento_pm:
                                    pm_realizado = True
                                    preco_medio = (entrada_original + preco_acionamento_pm) / 2
                                    take_profit = preco_medio * (1 + alvo_decimal)
                                    capital_alocado = txt_capital * 2

                            if df_back['High'].iloc[i] >= take_profit:
                                d_sai = df_back[col_data].iloc[i]
                                trades.append({'Lucro (R$)': capital_alocado * alvo_decimal, 'Drawdown_Raw': ((min_price_in_trade / entrada_original) - 1) * 100})
                                em_pos = False

                    if em_pos:
                        queda_maxima = ((min_price_in_trade / entrada_original) - 1) * 100
                        resultado_atual = ((df_back['Close'].iloc[-1] / preco_medio) - 1) * 100
                        lista_abertos.append({
                            'Ativo': ativo, 'Entrada': d_ent.strftime('%d/%m %H:%M') if tempo in ['15m', '60m'] else d_ent.strftime('%d/%m/%Y'),
                            'Dias': (df_back[col_data].iloc[-1] - d_ent).days, 'PM': f"R$ {preco_medio:.2f}",
                            'Cotação Atual': f"R$ {df_back['Close'].iloc[-1]:.2f}", 'Prej. Máx': f"{queda_maxima:.2f}%",
                            'Resultado Atual': f"+{resultado_atual:.2f}%" if resultado_atual > 0 else f"{resultado_atual:.2f}%",
                            'Fez PM?': 'Sim' if pm_realizado else 'Não'
                        })
                    else:
                        tem_sinal = False
                        if modo_entrada == 'cruzamento' and (df_full['IFR_Prev'].iloc[-1] < 25) and (df_full['IFR'].iloc[-1] >= 25): tem_sinal = True
                        elif modo_entrada == 'toque' and df_full['IFR'].iloc[-1] <= 25: tem_sinal = True
                        if tem_sinal: lista_sinais.append({'Ativo': ativo, 'Gatilho': modo_entrada.upper(), 'Preço Atual': f"R$ {df_full['Close'].iloc[-1]:.2f}"})

                    if len(trades) > 0:
                        df_t = pd.DataFrame(trades)
                        lista_resumo.append({'Ativo': ativo, 'Trades': len(df_t), 'Pior Queda': f"{df_t['Drawdown_Raw'].min():.2f}%", 'Lucro R$': df_t['Lucro (R$)'].sum()})

                except Exception as e: pass
                time.sleep(0.1)

            status_text.empty()
            progress_bar.empty()

            st.subheader("🚀 Oportunidades de Entrada Hoje")
            if len(lista_sinais) > 0: st.dataframe(pd.DataFrame(lista_sinais), use_container_width=True, hide_index=True)
            else: st.info("Nenhum ativo deu sinal de entrada na última barra.")

            st.subheader("⏳ Operações em Andamento")
            if len(lista_abertos) > 0:
                df_abertos = pd.DataFrame(lista_abertos).sort_values(by='Dias', ascending=False)
                st.dataframe(df_abertos.style.apply(colorir_lucro, axis=1), use_container_width=True, hide_index=True)
            else: st.success("Sua carteira está limpa. Nenhuma operação em andamento.")

            st.subheader(f"📊 Top 10 Histórico de Lucro ({tradutor_periodo_nome.get(periodo_selecionado, periodo_selecionado)})")
            if len(lista_resumo) > 0:
                df_resumo = pd.DataFrame(lista_resumo).sort_values(by='Lucro R$', ascending=False).head(10)
                df_resumo['Lucro R$'] = df_resumo['Lucro R$'].apply(lambda x: f"R$ {x:,.2f}")
                st.dataframe(df_resumo, use_container_width=True, hide_index=True)
            else: st.warning("Nenhuma operação finalizada no período.")

    # ==========================================
    # ABA 2: RAIO-X DO ATIVO (NOVO CÓDIGO)
    # ==========================================
    with aba_lupa:
        st.subheader("🔬 Análise Detalhada de Ativo Único")
        st.markdown("Digite o código da ação para investigar o histórico completo de testes, verificar drawdowns e ver operação por operação.")
        
        # Usando colunas para organizar os campos do formulário visualmente
        col1, col2, col3 = st.columns(3)
        with col1:
            lupa_ativo = st.text_input("Ativo (Ex: TSLA34):", value="TSLA34")
            lupa_periodo = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=2, key="lupa_per")
        with col2:
            lupa_alvo = st.number_input("Alvo (%):", value=3.0, step=0.5, key="lupa_alvo")
            lupa_pm = st.number_input("Gatilho PM (%):", value=0.0, step=0.5, key="lupa_pm")
        with col3:
            lupa_capital = st.number_input("Capital/Operação (R$):", value=10000.0, step=1000.0, key="lupa_cap")
            lupa_tempo = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="lupa_tmp")
            lupa_gatilho = st.selectbox("Gatilho:", options=['cruzamento', 'toque'], format_func=lambda x: 'Repique' if x == 'cruzamento' else 'Faca Caindo', key="lupa_gat")

        btn_raiox = st.button("🔍 Gerar Raio-X", type="primary", use_container_width=True)

        if btn_raiox:
            ativo_input = lupa_ativo.strip().upper()
            if not ativo_input:
                st.error("Por favor, digite o código de um ativo.")
            else:
                ativo = ativo_input.replace('.SA', '')
                
                # Regras de limite de tempo do TradingView
                if lupa_tempo == '15m' and lupa_periodo not in ['1mo', '3mo']: lupa_periodo = '60d'
                elif lupa_tempo == '60m' and lupa_periodo in ['5y', 'max']: lupa_periodo = '2y'

                intervalo_tv = tradutor_intervalo.get(lupa_tempo, Interval.in_daily)

                with st.spinner(f'Calculando histórico pesado de {ativo}...'):
                    try:
                        df_full = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=5000)

                        if df_full is None or len(df_full) < 50:
                            st.error("Dados insuficientes no TradingView para este ativo.")
                        else:
                            df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                            df_full = df_full.dropna()
                            df_full['IFR'] = ta.rsi(df_full['Close'], length=8)
                            df_full['IFR_Prev'] = df_full['IFR'].shift(1)
                            df_full = df_full.dropna()

                            data_atual = df_full.index[-1]
                            if lupa_periodo == '1mo': data_corte = data_atual - pd.DateOffset(months=1)
                            elif lupa_periodo == '3mo': data_corte = data_atual - pd.DateOffset(months=3)
                            elif lupa_periodo == '6mo': data_corte = data_atual - pd.DateOffset(months=6)
                            elif lupa_periodo == '1y': data_corte = data_atual - pd.DateOffset(years=1)
                            elif lupa_periodo == '2y': data_corte = data_atual - pd.DateOffset(years=2)
                            elif lupa_periodo == '5y': data_corte = data_atual - pd.DateOffset(years=5)
                            elif lupa_periodo == '60d': data_corte = data_atual - pd.DateOffset(days=60)
                            else: data_corte = df_full.index[0]

                            df = df_full[df_full.index >= data_corte].copy()

                            trades = []
                            em_pos = False
                            alvo_decimal = lupa_alvo / 100
                            gatilho_pm_decimal = lupa_pm / 100
                            df_back = df.reset_index()
                            col_data = df_back.columns[0]
                            trade_aberto = None

                            for i in range(1, len(df_back)):
                                if not em_pos:
                                    condicao_entrada = False
                                    if lupa_gatilho == 'cruzamento' and (df_back['IFR_Prev'].iloc[i] < 25) and (df_back['IFR'].iloc[i] >= 25): condicao_entrada = True
                                    elif lupa_gatilho == 'toque' and df_back['IFR'].iloc[i] <= 25: condicao_entrada = True

                                    if condicao_entrada:
                                        em_pos = True
                                        entrada_original = df_back['Close'].iloc[i]
                                        preco_medio = entrada_original
                                        d_ent = df_back[col_data].iloc[i]
                                        take_profit = preco_medio * (1 + alvo_decimal)
                                        min_price_in_trade = entrada_original
                                        pm_realizado = False
                                        capital_alocado = lupa_capital
                                else:
                                    if df_back['Low'].iloc[i] < min_price_in_trade:
                                        min_price_in_trade = df_back['Low'].iloc[i]

                                    if gatilho_pm_decimal < 0 and not pm_realizado:
                                        preco_acionamento_pm = entrada_original * (1 + gatilho_pm_decimal)
                                        if df_back['Low'].iloc[i] <= preco_acionamento_pm:
                                            pm_realizado = True
                                            preco_medio = (entrada_original + preco_acionamento_pm) / 2
                                            take_profit = preco_medio * (1 + alvo_decimal)
                                            capital_alocado = lupa_capital * 2

                                    if df_back['High'].iloc[i] >= take_profit:
                                        d_sai = df_back[col_data].iloc[i]
                                        duracao = (d_sai - d_ent).days
                                        lucro_rs = capital_alocado * alvo_decimal
                                        drawdown_pct = ((min_price_in_trade / entrada_original) - 1) * 100
                                        trades.append({
                                            'Entrada_Raw': d_ent,
                                            'Entrada': d_ent.strftime('%d/%m/%Y %H:%M') if lupa_tempo in ['15m', '60m'] else d_ent.strftime('%d/%m/%Y'),
                                            'Saída': d_sai.strftime('%d/%m/%Y %H:%M') if lupa_tempo in ['15m', '60m'] else d_sai.strftime('%d/%m/%Y'),
                                            'Duração': duracao,
                                            'Lucro (R$)': lucro_rs,
                                            'Drawdown_Raw': drawdown_pct,
                                            'Queda Máx': f"{drawdown_pct:.2f}%",
                                            'Fez PM?': 'Sim' if pm_realizado else 'Não',
                                            'Tipo': 'Day Trade' if duracao == 0 else '-'
                                        })
                                        em_pos = False

                            if em_pos:
                                drawdown_pct_aberto = ((min_price_in_trade / entrada_original) - 1) * 100
                                trade_aberto = {
                                    'Entrada': d_ent.strftime('%d/%m/%Y %H:%M') if lupa_tempo in ['15m', '60m'] else d_ent.strftime('%d/%m/%Y'),
                                    'Duração (dias)': (df_back[col_data].iloc[-1] - d_ent).days,
                                    'Fez PM?': 'Sim' if pm_realizado else 'Não',
                                    'Queda Máx': f"{drawdown_pct_aberto:.2f}%"
                                }

                            # --- EXIBIÇÃO VISUAL DOS RESULTADOS ---
                            st.divider()
                            st.markdown(f"### 📊 Resultado: {ativo}")
                            st.caption(f"Período Analisado: {tradutor_periodo_nome.get(lupa_periodo)} ({df.index[0].strftime('%d/%m/%Y')} até {df.index[-1].strftime('%d/%m/%Y')})")

                            if len(trades) > 0:
                                df_t = pd.DataFrame(trades).sort_values(by='Entrada_Raw', ascending=False)
                                
                                # Painel Executivo (Métricas)
                                mc1, mc2, mc3, mc4 = st.columns(4)
                                mc1.metric("Lucro Total Estimado", f"R$ {df_t['Lucro (R$)'].sum():,.2f}")
                                mc2.metric("Pior Queda", f"{df_t['Drawdown_Raw'].min():.2f}%")
                                mc3.metric("Tempo Preso (Médio)", f"{round(df_t['Duração'].mean(), 1)} dias")
                                mc4.metric("Operações Fechadas", f"{len(df_t)}")
                                
                                # Status Atual e Sinais
                                if trade_aberto:
                                    st.warning(f"⚠️ **Ativo em operação no momento:** Entrada em {trade_aberto['Entrada']} | Calor Máx: {trade_aberto['Queda Máx']} | Duração: {trade_aberto['Duração (dias)']} dias")
                                elif not em_pos:
                                    if lupa_gatilho == 'cruzamento' and (df_full['IFR_Prev'].iloc[-1] < 25) and (df_full['IFR'].iloc[-1] >= 25):
                                        st.success("🚀 SINAL DE ENTRADA DETECTADO AGORA NA ÚLTIMA BARRA!")
                                    elif lupa_gatilho == 'toque' and df_full['IFR'].iloc[-1] <= 25:
                                        st.success("🚀 SINAL DE ENTRADA DETECTADO AGORA NA ÚLTIMA BARRA!")

                                st.markdown("#### 📋 Extrato de Operações (Histórico)")
                                df_view = df_t[['Entrada', 'Saída', 'Duração', 'Queda Máx', 'Fez PM?', 'Tipo']].copy()
                                df_view['Duração'] = df_view['Duração'].astype(str) + " dias"
                                st.dataframe(df_view, use_container_width=True, hide_index=True)

                            else:
                                st.warning("Nenhuma operação foi concluída no histórico usando esses parâmetros.")

                    except Exception as e:
                        st.error(f"Ocorreu um erro ao processar os dados: {e}")