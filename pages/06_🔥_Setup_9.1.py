import streamlit as st
from tvDatafeed import TvDatafeed, Interval
import pandas as pd
import pandas_ta as ta
import time
import warnings

warnings.filterwarnings('ignore')

# 1. SEGURANÇA E BLOQUEIO
if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

# 2. CONEXÃO E LISTAS (Padrão de Elite)
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
# Criamos duas colunas: a primeira bem larga (para o título) e a segunda mais estreita (para o botão)
col_titulo, col_botao = st.columns([4, 1])

with col_titulo:
    st.title("🔥 Setup 9.1 (Larry Williams)")

with col_botao:
    # Esse espaço em branco alinha o botão mais para baixo, para ficar na mesma altura do texto do título
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.link_button("📖 Ler Manual", "https://seusite.com/manual_ifr", use_container_width=True)

aba_padrao, aba_avancado, aba_individual, aba_futuros = st.tabs([
    "📡 Radar Clássico (MME9)", "⚙️ Radar Avançado ", "🔬 Raio-X Individual", "📉 Raio-X Futuros"
])

# ==========================================
# ABA 1: RADAR PADRÃO (FAMÍLIA 9.x)
# ==========================================
with aba_padrao:
    st.subheader("📡 Radar Larry Williams (Família 9.x)")
    st.markdown("Identifica reversões (9.1) e pullbacks (9.2, 9.3) a favor da tendência. A saída é sempre conduzida pela virada da média.")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        lista_91 = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"], key="p91_lst")
        periodo_91 = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=3, key="p91_per")
    with c2:
        capital_91 = st.number_input("Capital por Trade (R$):", value=10000.0, step=1000.0, key="p91_cap")
        # CAIXA AZUL ADICIONADA AQUI:
        setup_escolhido = st.selectbox("Escolha a Estratégia:", ["Setup 9.1 (Virada de Média)", "Setup 9.2 (Pullback Curto)", "Setup 9.3 (Pullback Duplo)"], key="p91_setup")
    with c3:
        tempo_91 = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="p91_tmp")

    btn_iniciar_91 = st.button(f"🚀 Iniciar Varredura {setup_escolhido.split()[1]}", type="primary", use_container_width=True, key="p91_btn")

    if btn_iniciar_91:
        ativos_91 = bdrs_elite if lista_91 == "BDRs Elite" else ibrx_selecao if lista_91 == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        
        if tempo_91 == '15m' and periodo_91 not in ['1mo', '3mo']: periodo_91 = '60d'
        elif tempo_91 == '60m' and periodo_91 in ['5y', 'max']: periodo_91 = '2y'

        intervalo_tv = tradutor_intervalo.get(tempo_91, Interval.in_daily)

        ls_armados, ls_abertos, ls_resumo = [], [], []
        p_bar = st.progress(0)
        s_text = st.empty()

        for idx, ativo_raw in enumerate(ativos_91):
            ativo = ativo_raw.replace('.SA', '')
            s_text.text(f"🔍 Analisando {setup_escolhido.split()[1]}: {ativo} ({idx+1}/{len(ativos_91)})")
            p_bar.progress((idx + 1) / len(ativos_91))

            try:
                df_full = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=5000)
                if df_full is None or len(df_full) < 50: continue

                df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                df_full = df_full.dropna()
                
                # --- CÁLCULO DA MME9 ---
                df_full['MME9'] = ta.ema(df_full['Close'], length=9)
                df_full['MME9_Prev1'] = df_full['MME9'].shift(1)
                df_full['MME9_Prev2'] = df_full['MME9'].shift(2)
                df_full = df_full.dropna()

                data_atual = df_full.index[-1]
                if periodo_91 == '1mo': data_corte = data_atual - pd.DateOffset(months=1)
                elif periodo_91 == '3mo': data_corte = data_atual - pd.DateOffset(months=3)
                elif periodo_91 == '6mo': data_corte = data_atual - pd.DateOffset(months=6)
                elif periodo_91 == '1y': data_corte = data_atual - pd.DateOffset(years=1)
                elif periodo_91 == '2y': data_corte = data_atual - pd.DateOffset(years=2)
                elif periodo_91 == '5y': data_corte = data_atual - pd.DateOffset(years=5)
                elif periodo_91 == '60d': data_corte = data_atual - pd.DateOffset(days=60)
                else: data_corte = df_full.index[0]

                df = df_full[df_full.index >= data_corte].copy()
                if len(df) == 0: continue

                trades = []
                em_pos = False
                setup_armado = False
                saida_armada = False
                gatilho_entrada = 0.0
                gatilho_saida = 0.0
                stop_loss = 0.0
                vitorias, derrotas = 0, 0
                
                df_back = df.reset_index()
                col_data = df_back.columns[0]

                # --- MOTOR DE BACKTEST MULTI-SETUP (9.1, 9.2, 9.3) ---
                for i in range(3, len(df_back)):
                    # Lógica Comum da Média
                    mme9_atual = df_back['MME9'].iloc[i]
                    mme9_p1 = df_back['MME9_Prev1'].iloc[i]
                    mme9_p2 = df_back['MME9_Prev2'].iloc[i]

                    media_virou_cima = (mme9_p1 < mme9_p2) and (mme9_atual > mme9_p1)
                    media_virou_baixo = (mme9_p1 > mme9_p2) and (mme9_atual < mme9_p1)
                    media_caindo = mme9_atual < mme9_p1
                    media_subindo = mme9_atual > mme9_p1

                    # Gatilhos Exclusivos do 9.2 e 9.3
                    fechou_abaixo_min_ant = df_back['Close'].iloc[i] < df_back['Low'].iloc[i-1]
                    fechou_abaixo_fech_ant1 = df_back['Close'].iloc[i] < df_back['Close'].iloc[i-1]
                    fechou_abaixo_fech_ant2 = df_back['Close'].iloc[i-1] < df_back['Close'].iloc[i-2]

                    if em_pos:
                        # 1. Verifica Stop Loss Original (Igual para todos)
                        if df_back['Low'].iloc[i] <= stop_loss:
                            d_sai = df_back[col_data].iloc[i]
                            duracao = (d_sai - d_ent).days
                            lucro_rs = capital_91 * ((stop_loss / preco_entrada) - 1)
                            trades.append({'Entrada': d_ent, 'Duração': duracao, 'Lucro (R$)': lucro_rs, 'Situação': 'Stop Acionado ❌'})
                            if lucro_rs > 0: vitorias += 1 
                            else: derrotas += 1
                            em_pos, saida_armada = False, False
                            continue
                        
                        # 2. Verifica Gatilho de Saída (Trailing Stop da MME9)
                        if saida_armada:
                            if df_back['Low'].iloc[i] < gatilho_saida:
                                d_sai = df_back[col_data].iloc[i]
                                duracao = (d_sai - d_ent).days
                                lucro_rs = capital_91 * ((gatilho_saida / preco_entrada) - 1)
                                trades.append({'Entrada': d_ent, 'Duração': duracao, 'Lucro (R$)': lucro_rs, 'Situação': 'Saída Técnica ✅' if lucro_rs > 0 else 'Saída Técnica ❌'})
                                if lucro_rs > 0: vitorias += 1 
                                else: derrotas += 1
                                em_pos, saida_armada = False, False
                                continue
                            elif media_subindo:
                                saida_armada = False

                        # 3. Arma a saída se a MME9 virar para baixo
                        if media_virou_baixo and not saida_armada:
                            saida_armada = True
                            gatilho_saida = df_back['Low'].iloc[i]

                    else:
                        # Fora da Operação: Buscando Entradas
                        if setup_armado:
                            if df_back['High'].iloc[i] > gatilho_entrada:
                                # Rompeu! Entra na operação.
                                em_pos = True
                                setup_armado = False
                                d_ent = df_back[col_data].iloc[i]
                                preco_entrada = max(gatilho_entrada + 0.01, df_back['Open'].iloc[i])
                            else:
                                # Não ativou no candle seguinte. O que fazer?
                                if "9.1" in setup_escolhido:
                                    if media_caindo: setup_armado = False
                                elif "9.2" in setup_escolhido or "9.3" in setup_escolhido:
                                    if media_subindo:
                                        # Ajuste Fino do Palex: Abaixa o gatilho para a nova máxima e sobe o stop para a nova mínima
                                        gatilho_entrada = df_back['High'].iloc[i]
                                        stop_loss = df_back['Low'].iloc[i] - 0.01
                                    else:
                                        setup_armado = False # Média virou pra baixo, desarma tudo

                        # --- ARMAR O SETUP BASEADO NA ESCOLHA ---
                        if "9.1" in setup_escolhido and media_virou_cima:
                            setup_armado = True
                            gatilho_entrada = df_back['High'].iloc[i]
                            stop_loss = df_back['Low'].iloc[i] - 0.01
                        elif "9.2" in setup_escolhido and media_subindo and fechou_abaixo_min_ant:
                            setup_armado = True
                            gatilho_entrada = df_back['High'].iloc[i]
                            stop_loss = df_back['Low'].iloc[i] - 0.01
                        elif "9.3" in setup_escolhido and media_subindo and fechou_abaixo_fech_ant1 and fechou_abaixo_fech_ant2:
                            setup_armado = True
                            gatilho_entrada = df_back['High'].iloc[i]
                            stop_loss = df_back['Low'].iloc[i] - 0.01

                # --- COLETANDO ESTADO ATUAL PARA O PAINEL ---
                if em_pos:
                    resultado_atual = ((df_back['Close'].iloc[-1] / preco_entrada) - 1) * 100
                    ls_abertos.append({
                        'Ativo': ativo, 'Entrada': d_ent.strftime('%d/%m %H:%M') if tempo_91 in ['15m', '60m'] else d_ent.strftime('%d/%m/%Y'),
                        'Dias': (df_back[col_data].iloc[-1] - d_ent).days, 'Preço Entrada': f"R$ {preco_entrada:.2f}",
                        'Cotação Atual': f"R$ {df_back['Close'].iloc[-1]:.2f}",
                        'Status': 'Aguardando Saída ⚠️' if saida_armada else 'Surfando Tendência 🌊',
                        'Resultado Atual': f"+{resultado_atual:.2f}%" if resultado_atual > 0 else f"{resultado_atual:.2f}%"
                    })
                else:
                    # Captura quem armou HOJE para qualquer um dos setups
                    mme9_hj = df_full['MME9'].iloc[-1]
                    mme9_p1_hj = df_full['MME9_Prev1'].iloc[-1]
                    mme9_p2_hj = df_full['MME9_Prev2'].iloc[-1]

                    subindo_hj = mme9_hj > mme9_p1_hj
                    virou_cima_hj = (mme9_p1_hj < mme9_p2_hj) and subindo_hj
                    f_abx_min_hj = df_full['Close'].iloc[-1] < df_full['Low'].iloc[-2]
                    f_abx_f1_hj = df_full['Close'].iloc[-1] < df_full['Close'].iloc[-2]
                    f_abx_f2_hj = df_full['Close'].iloc[-2] < df_full['Close'].iloc[-3]

                    armou_hoje = False
                    if "9.1" in setup_escolhido and virou_cima_hj: armou_hoje = True
                    elif "9.2" in setup_escolhido and subindo_hj and f_abx_min_hj: armou_hoje = True
                    elif "9.3" in setup_escolhido and subindo_hj and f_abx_f1_hj and f_abx_f2_hj: armou_hoje = True

                    if armou_hoje:
                        ls_armados.append({'Ativo': ativo, 'Preço Atual': f"R$ {df_full['Close'].iloc[-1]:.2f}", 'Gatilho Compra (Amanhã)': f"R$ {(df_full['High'].iloc[-1] + 0.01):.2f}", 'Stop Loss': f"R$ {(df_full['Low'].iloc[-1] - 0.01):.2f}"})

                if len(trades) > 0:
                    df_t = pd.DataFrame(trades)
                    taxa_acerto = (vitorias / len(df_t)) * 100
                    ls_resumo.append({
                        'Ativo': ativo, 'Total Trades': len(df_t), 'Acertos': vitorias, 'Stops': derrotas, 'Taxa de Acerto': f"{taxa_acerto:.1f}%", 'Lucro R$': df_t['Lucro (R$)'].sum()
                    })

            except Exception as e: pass
            time.sleep(0.05)

        s_text.empty()
        p_bar.empty()

        # --- EXIBIÇÃO DOS RESULTADOS ---
        st.subheader(f"🔥 Setups {setup_escolhido.split()[1]} Armados Hoje (Compra Amanhã)")
        if len(ls_armados) > 0: st.dataframe(pd.DataFrame(ls_armados), use_container_width=True, hide_index=True)
        else: st.info("Nenhum setup identificado no último candle.")

        st.subheader("🌊 Operações em Andamento (Condução pela MME9)")
        if len(ls_abertos) > 0:
            df_abertos = pd.DataFrame(ls_abertos).sort_values(by='Dias', ascending=False)
            st.dataframe(df_abertos.style.apply(colorir_lucro, axis=1), use_container_width=True, hide_index=True)
        else: st.success("Sua carteira está limpa.")

        st.subheader(f"📊 Top 10 Histórico ({tradutor_periodo_nome.get(periodo_91, periodo_91)})")
        if len(ls_resumo) > 0:
            df_resumo = pd.DataFrame(ls_resumo).sort_values(by='Lucro R$', ascending=False).head(10)
            df_resumo['Lucro R$'] = df_resumo['Lucro R$'].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(df_resumo, use_container_width=True, hide_index=True)
        else: st.warning("Nenhuma operação finalizada.")

# ESPAÇO PARA AS PRÓXIMAS ABAS
# ==========================================
# ABA 2: RADAR AVANÇADO (FAMÍLIA 9.x)
# ==========================================
with aba_avancado:
    st.subheader("⚙️ Radar Avançado (Fundo Anterior & MM9)")
    st.markdown("Opere os Setups 9.1, 9.2 ou 9.3 com flexibilidade para alterar a localização do **Stop Inicial** (para evitar violinadas) e a **Média de Condução**.")
    
    ca1, ca2, ca3 = st.columns(3)
    with ca1:
        lista_91a = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"], key="a91_lista")
        periodo_91a = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=3, key="a91_per")
        # --- CAIXA AZUL INSERIDA AQUI PARA EQUILIBRAR O LAYOUT ---
        setup_escolhido_a = st.selectbox("Escolha a Estratégia:", ["Setup 9.1 (Virada de Média)", "Setup 9.2 (Pullback Curto)", "Setup 9.3 (Pullback Duplo)"], key="a91_setup")
    with ca2:
        tipo_stop = st.selectbox("Posição do Stop Inicial:", ["Mínima do Candle Referência", "Fundo Anterior (Últimos 5 candles)"], key="a91_stop")
        tipo_conducao = st.selectbox("Média de Condução (Trailing):", ["MME9 (Exponencial)", "MM9 (Aritmética)"], key="a91_cond")
    with ca3:
        capital_91a = st.number_input("Capital por Trade (R$):", value=10000.0, step=1000.0, key="a91_cap")
        tempo_91a = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="a91_tmp")

    btn_iniciar_91a = st.button(f"🚀 Iniciar Varredura {setup_escolhido_a.split()[1]} Avançada", type="primary", use_container_width=True, key="a91_btn")

    if btn_iniciar_91a:
        ativos_91a = bdrs_elite if lista_91a == "BDRs Elite" else ibrx_selecao if lista_91a == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        
        if tempo_91a == '15m' and periodo_91a not in ['1mo', '3mo']: periodo_91a = '60d'
        elif tempo_91a == '60m' and periodo_91a in ['5y', 'max']: periodo_91a = '2y'

        intervalo_tv = tradutor_intervalo.get(tempo_91a, Interval.in_daily)

        ls_armados_a, ls_abertos_a, ls_resumo_a = [], [], []
        p_bar_a = st.progress(0)
        s_text_a = st.empty()

        for idx, ativo_raw in enumerate(ativos_91a):
            ativo = ativo_raw.replace('.SA', '')
            s_text_a.text(f"🔍 Analisando {setup_escolhido_a.split()[1]} Avançado: {ativo} ({idx+1}/{len(ativos_91a)})")
            p_bar_a.progress((idx + 1) / len(ativos_91a))

            try:
                df_full = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=5000)
                if df_full is None or len(df_full) < 50: continue

                df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                df_full = df_full.dropna()
                
                # --- CÁLCULO DAS MÉDIAS E FUNDOS ---
                df_full['MME9'] = ta.ema(df_full['Close'], length=9)
                df_full['MME9_Prev1'] = df_full['MME9'].shift(1)
                df_full['MME9_Prev2'] = df_full['MME9'].shift(2)
                
                df_full['MM9'] = ta.sma(df_full['Close'], length=9)
                df_full['MM9_Prev1'] = df_full['MM9'].shift(1)
                df_full['MM9_Prev2'] = df_full['MM9'].shift(2)
                
                df_full['Fundo_5'] = df_full['Low'].rolling(window=5).min()
                df_full = df_full.dropna()

                data_atual = df_full.index[-1]
                if periodo_91a == '1mo': data_corte = data_atual - pd.DateOffset(months=1)
                elif periodo_91a == '3mo': data_corte = data_atual - pd.DateOffset(months=3)
                elif periodo_91a == '6mo': data_corte = data_atual - pd.DateOffset(months=6)
                elif periodo_91a == '1y': data_corte = data_atual - pd.DateOffset(years=1)
                elif periodo_91a == '2y': data_corte = data_atual - pd.DateOffset(years=2)
                elif periodo_91a == '5y': data_corte = data_atual - pd.DateOffset(years=5)
                elif periodo_91a == '60d': data_corte = data_atual - pd.DateOffset(days=60)
                else: data_corte = df_full.index[0]

                df = df_full[df_full.index >= data_corte].copy()
                if len(df) == 0: continue

                trades = []
                em_pos = False
                setup_armado = False
                saida_armada = False
                gatilho_entrada = 0.0
                gatilho_saida = 0.0
                stop_loss = 0.0
                vitorias, derrotas = 0, 0
                
                df_back = df.reset_index()
                col_data = df_back.columns[0]

                # --- MOTOR DE BACKTEST MULTI-SETUP (9.1, 9.2, 9.3) COM REGRAS AVANÇADAS ---
                for i in range(3, len(df_back)):
                    # A ENTRADA É SEMPRE PELA MME9 (Regra Clássica)
                    mme9_atual = df_back['MME9'].iloc[i]
                    mme9_p1 = df_back['MME9_Prev1'].iloc[i]
                    mme9_p2 = df_back['MME9_Prev2'].iloc[i]

                    media_virou_cima = (mme9_p1 < mme9_p2) and (mme9_atual > mme9_p1)
                    media_virou_baixo = (mme9_p1 > mme9_p2) and (mme9_atual < mme9_p1)
                    media_caindo = mme9_atual < mme9_p1
                    media_subindo = mme9_atual > mme9_p1

                    fechou_abaixo_min_ant = df_back['Close'].iloc[i] < df_back['Low'].iloc[i-1]
                    fechou_abaixo_fech_ant1 = df_back['Close'].iloc[i] < df_back['Close'].iloc[i-1]
                    fechou_abaixo_fech_ant2 = df_back['Close'].iloc[i-1] < df_back['Close'].iloc[i-2]

                    # A SAÍDA DEPENDE DA ESCOLHA DO USUÁRIO
                    if tipo_conducao == "MM9 (Aritmética)":
                        ma_atual, ma_prev1, ma_prev2 = df_back['MM9'].iloc[i], df_back['MM9_Prev1'].iloc[i], df_back['MM9_Prev2'].iloc[i]
                    else:
                        ma_atual, ma_prev1, ma_prev2 = mme9_atual, mme9_p1, mme9_p2
                        
                    media_saida_virou_baixo = (ma_prev1 > ma_prev2) and (ma_atual < ma_prev1)
                    media_saida_subindo = ma_atual > ma_prev1

                    if em_pos:
                        # 1. Stop Loss Inicial
                        if df_back['Low'].iloc[i] <= stop_loss:
                            d_sai = df_back[col_data].iloc[i]
                            duracao = (d_sai - d_ent).days
                            lucro_rs = capital_91a * ((stop_loss / preco_entrada) - 1)
                            trades.append({'Entrada': d_ent, 'Duração': duracao, 'Lucro (R$)': lucro_rs, 'Situação': 'Stop Acionado ❌'})
                            if lucro_rs > 0: vitorias += 1 
                            else: derrotas += 1
                            em_pos, saida_armada = False, False
                            continue
                        
                        # 2. Gatilho de Saída Técnica (Trailing Stop)
                        if saida_armada:
                            if df_back['Low'].iloc[i] < gatilho_saida:
                                d_sai = df_back[col_data].iloc[i]
                                duracao = (d_sai - d_ent).days
                                lucro_rs = capital_91a * ((gatilho_saida / preco_entrada) - 1)
                                trades.append({'Entrada': d_ent, 'Duração': duracao, 'Lucro (R$)': lucro_rs, 'Situação': 'Saída Técnica ✅' if lucro_rs > 0 else 'Saída Técnica ❌'})
                                if lucro_rs > 0: vitorias += 1 
                                else: derrotas += 1
                                em_pos, saida_armada = False, False
                                continue
                            elif media_saida_subindo:
                                saida_armada = False

                        # 3. Arma a saída se a média de condução virar para baixo
                        if media_saida_virou_baixo and not saida_armada:
                            saida_armada = True
                            gatilho_saida = df_back['Low'].iloc[i]

                    else:
                        # Fora da Posição: Monitorando Entradas
                        if setup_armado:
                            if df_back['High'].iloc[i] > gatilho_entrada:
                                em_pos = True
                                setup_armado = False
                                d_ent = df_back[col_data].iloc[i]
                                preco_entrada = max(gatilho_entrada + 0.01, df_back['Open'].iloc[i])
                            else:
                                if "9.1" in setup_escolhido_a:
                                    if media_caindo: setup_armado = False
                                elif "9.2" in setup_escolhido_a or "9.3" in setup_escolhido_a:
                                    if media_subindo:
                                        gatilho_entrada = df_back['High'].iloc[i]
                                        # Ajuste Fino do Palex: Abaixa a entrada, mas também recalcula o Stop se necessário
                                        stop_loss = df_back['Fundo_5'].iloc[i] - 0.01 if tipo_stop == "Fundo Anterior (Últimos 5 candles)" else df_back['Low'].iloc[i] - 0.01
                                    else:
                                        setup_armado = False

                        # Arma o Setup
                        if "9.1" in setup_escolhido_a and media_virou_cima:
                            setup_armado = True
                            gatilho_entrada = df_back['High'].iloc[i]
                            stop_loss = df_back['Fundo_5'].iloc[i] - 0.01 if tipo_stop == "Fundo Anterior (Últimos 5 candles)" else df_back['Low'].iloc[i] - 0.01
                        elif "9.2" in setup_escolhido_a and media_subindo and fechou_abaixo_min_ant:
                            setup_armado = True
                            gatilho_entrada = df_back['High'].iloc[i]
                            stop_loss = df_back['Fundo_5'].iloc[i] - 0.01 if tipo_stop == "Fundo Anterior (Últimos 5 candles)" else df_back['Low'].iloc[i] - 0.01
                        elif "9.3" in setup_escolhido_a and media_subindo and fechou_abaixo_fech_ant1 and fechou_abaixo_fech_ant2:
                            setup_armado = True
                            gatilho_entrada = df_back['High'].iloc[i]
                            stop_loss = df_back['Fundo_5'].iloc[i] - 0.01 if tipo_stop == "Fundo Anterior (Últimos 5 candles)" else df_back['Low'].iloc[i] - 0.01

                # --- COLETANDO ESTADO ATUAL PARA O PAINEL ---
                if em_pos:
                    resultado_atual = ((df_back['Close'].iloc[-1] / preco_entrada) - 1) * 100
                    ls_abertos_a.append({
                        'Ativo': ativo, 'Entrada': d_ent.strftime('%d/%m %H:%M') if tempo_91a in ['15m', '60m'] else d_ent.strftime('%d/%m/%Y'),
                        'Dias': (df_back[col_data].iloc[-1] - d_ent).days, 'Preço Entrada': f"R$ {preco_entrada:.2f}",
                        'Stop Inicial': f"R$ {stop_loss:.2f}",
                        'Cotação Atual': f"R$ {df_back['Close'].iloc[-1]:.2f}",
                        'Status': 'Aguardando Saída ⚠️' if saida_armada else 'Surfando Tendência 🌊',
                        'Resultado Atual': f"+{resultado_atual:.2f}%" if resultado_atual > 0 else f"{resultado_atual:.2f}%"
                    })
                else:
                    mme9_hj = df_full['MME9'].iloc[-1]
                    mme9_p1_hj = df_full['MME9_Prev1'].iloc[-1]
                    mme9_p2_hj = df_full['MME9_Prev2'].iloc[-1]

                    subindo_hj = mme9_hj > mme9_p1_hj
                    virou_cima_hj = (mme9_p1_hj < mme9_p2_hj) and subindo_hj
                    f_abx_min_hj = df_full['Close'].iloc[-1] < df_full['Low'].iloc[-2]
                    f_abx_f1_hj = df_full['Close'].iloc[-1] < df_full['Close'].iloc[-2]
                    f_abx_f2_hj = df_full['Close'].iloc[-2] < df_full['Close'].iloc[-3]

                    armou_hoje = False
                    if "9.1" in setup_escolhido_a and virou_cima_hj: armou_hoje = True
                    elif "9.2" in setup_escolhido_a and subindo_hj and f_abx_min_hj: armou_hoje = True
                    elif "9.3" in setup_escolhido_a and subindo_hj and f_abx_f1_hj and f_abx_f2_hj: armou_hoje = True

                    if armou_hoje:
                        sl_hoje = df_full['Fundo_5'].iloc[-1] - 0.01 if tipo_stop == "Fundo Anterior (Últimos 5 candles)" else df_full['Low'].iloc[-1] - 0.01
                        ls_armados_a.append({'Ativo': ativo, 'Preço Atual': f"R$ {df_full['Close'].iloc[-1]:.2f}", 'Gatilho Compra': f"R$ {(df_full['High'].iloc[-1] + 0.01):.2f}", 'Stop Indicado': f"R$ {sl_hoje:.2f}"})

                if len(trades) > 0:
                    df_t = pd.DataFrame(trades)
                    taxa_acerto = (vitorias / len(df_t)) * 100
                    ls_resumo_a.append({
                        'Ativo': ativo, 'Total Trades': len(df_t), 'Acertos': vitorias, 'Stops': derrotas, 'Taxa de Acerto': f"{taxa_acerto:.1f}%", 'Lucro R$': df_t['Lucro (R$)'].sum()
                    })

            except Exception as e: pass
            time.sleep(0.05)

        s_text_a.empty()
        p_bar_a.empty()

        # --- EXIBIÇÃO DOS RESULTADOS ---
        st.subheader(f"🔥 Setups {setup_escolhido_a.split()[1]} Armados Hoje (Compra Amanhã)")
        if len(ls_armados_a) > 0: st.dataframe(pd.DataFrame(ls_armados_a), use_container_width=True, hide_index=True)
        else: st.info("Nenhum setup identificado no último candle.")

        st.subheader(f"🌊 Operações em Andamento (Condução pela {tipo_conducao.split()[0]})")
        if len(ls_abertos_a) > 0:
            df_abertos = pd.DataFrame(ls_abertos_a).sort_values(by='Dias', ascending=False)
            st.dataframe(df_abertos.style.apply(colorir_lucro, axis=1), use_container_width=True, hide_index=True)
        else: st.success("Sua carteira está limpa.")

        st.subheader(f"📊 Top 10 Histórico ({tradutor_periodo_nome.get(periodo_91a, periodo_91a)})")
        if len(ls_resumo_a) > 0:
            df_resumo = pd.DataFrame(ls_resumo_a).sort_values(by='Lucro R$', ascending=False).head(10)
            df_resumo['Lucro R$'] = df_resumo['Lucro R$'].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(df_resumo, use_container_width=True, hide_index=True)
        else: st.warning("Nenhuma operação finalizada.")
# ==========================================
# ABA 3: RAIO-X DO ATIVO INDIVIDUAL (FAMÍLIA 9.x)
# ==========================================
with aba_individual:
    st.subheader("🔬 Análise Detalhada de Ativo Único (Família 9.x)")
    st.markdown("Faça o teste de estresse de um ativo específico validando as variações de Stop Inicial e Médias de Condução para os setups 9.1, 9.2 e 9.3.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        lupa_ativo = st.text_input("Ativo (Ex: TSLA34):", value="TSLA34", key="i91_ativo")
        lupa_stop = st.selectbox("Posição do Stop Inicial:", ["Mínima do Candle", "Fundo Anterior (5 candles)"], key="i91_stop")
        lupa_periodo = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=2, key="i91_per")
    with col2:
        # --- CAIXA AZUL INSERIDA AQUI ---
        setup_escolhido_i = st.selectbox("Escolha a Estratégia:", ["Setup 9.1 (Virada de Média)", "Setup 9.2 (Pullback Curto)", "Setup 9.3 (Pullback Duplo)"], key="i91_setup")
        lupa_cond = st.selectbox("Média de Condução (Trailing):", ["MME9 (Exponencial)", "MM9 (Aritmética)"], key="i91_cond")
        lupa_capital = st.number_input("Capital Base (R$):", value=10000.0, step=1000.0, key="i91_cap")
    with col3:
        lupa_tempo = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="i91_tmp")
        
    # NOME DO BOTÃO DINÂMICO
    btn_raiox = st.button(f"🔍 Gerar Raio-X {setup_escolhido_i.split()[1]}", type="primary", use_container_width=True, key="i91_btn")

    if btn_raiox:
        ativo_input = lupa_ativo.strip().upper()
        if not ativo_input:
            st.error("Por favor, digite o código de um ativo.")
        else:
            ativo = ativo_input.replace('.SA', '')
            if lupa_tempo == '15m' and lupa_periodo not in ['1mo', '3mo']: lupa_periodo = '60d'
            elif lupa_tempo == '60m' and lupa_periodo in ['5y', 'max']: lupa_periodo = '2y'
            intervalo_tv = tradutor_intervalo.get(lupa_tempo, Interval.in_daily)

            with st.spinner(f'Testando Backtest {setup_escolhido_i.split()[1]} em {ativo}...'):
                try:
                    df_full = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=5000)
                    if df_full is None or len(df_full) < 50:
                        st.error("Dados insuficientes no TradingView para este ativo.")
                    else:
                        df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                        df_full = df_full.dropna()
                        
                        # --- CÁLCULO DAS MÉDIAS E FUNDOS ---
                        df_full['MME9'] = ta.ema(df_full['Close'], length=9)
                        df_full['MME9_Prev1'] = df_full['MME9'].shift(1)
                        df_full['MME9_Prev2'] = df_full['MME9'].shift(2)
                        
                        df_full['MM9'] = ta.sma(df_full['Close'], length=9)
                        df_full['MM9_Prev1'] = df_full['MM9'].shift(1)
                        df_full['MM9_Prev2'] = df_full['MM9'].shift(2)
                        
                        df_full['Fundo_5'] = df_full['Low'].rolling(window=5).min()
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
                        setup_armado = False
                        saida_armada = False
                        gatilho_entrada = 0.0
                        gatilho_saida = 0.0
                        stop_loss = 0.0
                        df_back = df.reset_index()
                        col_data = df_back.columns[0]
                        vitorias, derrotas = 0, 0

                        # Começando do índice 3 para ter margem de candles passados
                        for i in range(3, len(df_back)):
                            mme9_atual = df_back['MME9'].iloc[i]
                            mme9_p1 = df_back['MME9_Prev1'].iloc[i]
                            mme9_p2 = df_back['MME9_Prev2'].iloc[i]
                            
                            mme9_virou_cima = (mme9_p1 < mme9_p2) and (mme9_atual > mme9_p1)
                            mme9_caindo = mme9_atual < mme9_p1
                            mme9_subindo = mme9_atual > mme9_p1

                            fechou_abaixo_min_ant = df_back['Close'].iloc[i] < df_back['Low'].iloc[i-1]
                            fechou_abaixo_fech_ant1 = df_back['Close'].iloc[i] < df_back['Close'].iloc[i-1]
                            fechou_abaixo_fech_ant2 = df_back['Close'].iloc[i-1] < df_back['Close'].iloc[i-2]

                            if lupa_cond == "MM9 (Aritmética)":
                                ma_atual, ma_prev1, ma_prev2 = df_back['MM9'].iloc[i], df_back['MM9_Prev1'].iloc[i], df_back['MM9_Prev2'].iloc[i]
                            else:
                                ma_atual, ma_prev1, ma_prev2 = mme9_atual, mme9_p1, mme9_p2
                                
                            media_saida_virou_baixo = (ma_prev1 > ma_prev2) and (ma_atual < ma_prev1)
                            media_saida_subindo = ma_atual > ma_prev1

                            if em_pos:
                                # 1. Stop Loss Inicial
                                if df_back['Low'].iloc[i] <= stop_loss:
                                    d_sai = df_back[col_data].iloc[i]
                                    duracao = (d_sai - d_ent).days
                                    lucro_rs = lupa_capital * ((stop_loss / preco_entrada) - 1)
                                    trades.append({'Entrada': d_ent.strftime('%d/%m/%Y %H:%M') if lupa_tempo in ['15m', '60m'] else d_ent.strftime('%d/%m/%Y'), 'Saída': d_sai.strftime('%d/%m/%Y %H:%M') if lupa_tempo in ['15m', '60m'] else d_sai.strftime('%d/%m/%Y'), 'Duração': duracao, 'Lucro (R$)': lucro_rs, 'Situação': 'Stop Inicial ❌'})
                                    derrotas += 1
                                    em_pos, saida_armada = False, False
                                    continue
                                
                                # 2. Saída Técnica
                                if saida_armada:
                                    if df_back['Low'].iloc[i] < gatilho_saida:
                                        d_sai = df_back[col_data].iloc[i]
                                        duracao = (d_sai - d_ent).days
                                        lucro_rs = lupa_capital * ((gatilho_saida / preco_entrada) - 1)
                                        trades.append({'Entrada': d_ent.strftime('%d/%m/%Y %H:%M') if lupa_tempo in ['15m', '60m'] else d_ent.strftime('%d/%m/%Y'), 'Saída': d_sai.strftime('%d/%m/%Y %H:%M') if lupa_tempo in ['15m', '60m'] else d_sai.strftime('%d/%m/%Y'), 'Duração': duracao, 'Lucro (R$)': lucro_rs, 'Situação': 'Gain ✅' if lucro_rs > 0 else 'Loss Técnico ❌'})
                                        if lucro_rs > 0: vitorias += 1 
                                        else: derrotas += 1
                                        em_pos, saida_armada = False, False
                                        continue
                                    elif media_saida_subindo:
                                        saida_armada = False

                                # 3. Armar Saída
                                if media_saida_virou_baixo and not saida_armada:
                                    saida_armada = True
                                    gatilho_saida = df_back['Low'].iloc[i]

                            else:
                                if setup_armado:
                                    if df_back['High'].iloc[i] > gatilho_entrada:
                                        em_pos = True
                                        setup_armado = False
                                        d_ent = df_back[col_data].iloc[i]
                                        preco_entrada = max(gatilho_entrada + 0.01, df_back['Open'].iloc[i])
                                    else:
                                        if "9.1" in setup_escolhido_i:
                                            if mme9_caindo: setup_armado = False
                                        elif "9.2" in setup_escolhido_i or "9.3" in setup_escolhido_i:
                                            if mme9_subindo:
                                                gatilho_entrada = df_back['High'].iloc[i]
                                                if lupa_stop == "Fundo Anterior (5 candles)":
                                                    stop_loss = df_back['Fundo_5'].iloc[i] - 0.01
                                                else:
                                                    stop_loss = df_back['Low'].iloc[i] - 0.01
                                            else:
                                                setup_armado = False

                                if "9.1" in setup_escolhido_i and mme9_virou_cima:
                                    setup_armado = True
                                    gatilho_entrada = df_back['High'].iloc[i]
                                    stop_loss = df_back['Fundo_5'].iloc[i] - 0.01 if lupa_stop == "Fundo Anterior (5 candles)" else df_back['Low'].iloc[i] - 0.01
                                elif "9.2" in setup_escolhido_i and mme9_subindo and fechou_abaixo_min_ant:
                                    setup_armado = True
                                    gatilho_entrada = df_back['High'].iloc[i]
                                    stop_loss = df_back['Fundo_5'].iloc[i] - 0.01 if lupa_stop == "Fundo Anterior (5 candles)" else df_back['Low'].iloc[i] - 0.01
                                elif "9.3" in setup_escolhido_i and mme9_subindo and fechou_abaixo_fech_ant1 and fechou_abaixo_fech_ant2:
                                    setup_armado = True
                                    gatilho_entrada = df_back['High'].iloc[i]
                                    stop_loss = df_back['Fundo_5'].iloc[i] - 0.01 if lupa_stop == "Fundo Anterior (5 candles)" else df_back['Low'].iloc[i] - 0.01

                        st.divider()
                        st.markdown(f"### 📊 Resultado: {ativo} ({setup_escolhido_i.split()[1]})")
                        
                        if len(trades) > 0:
                            df_t = pd.DataFrame(trades)
                            mc1, mc2, mc3, mc4 = st.columns(4)
                            mc1.metric("Lucro Total Estimado", f"R$ {df_t['Lucro (R$)'].sum():,.2f}")
                            mc2.metric("Tempo Preso (Médio)", f"{round(df_t['Duração'].mean(), 1)} dias")
                            mc3.metric("Operações Fechadas", f"{len(df_t)}")
                            
                            taxa_acerto = (vitorias / len(df_t)) * 100
                            mc4.metric("Taxa de Acerto", f"{taxa_acerto:.1f}%")
                            
                            st.dataframe(df_t, use_container_width=True, hide_index=True)
                        else:
                            st.warning("Nenhuma operação concluída usando essa configuração neste período.")
                except Exception as e: st.error(f"Erro: {e}")
# ==========================================
# ABA 4: RAIO-X FUTUROS (SETUP 9.1 DAY TRADE - COMPRA E VENDA)
# ==========================================
with aba_futuros:
    st.subheader("📈 Raio-X Mercado Futuro (WIN, WDO) - Setup 9.1")
    st.markdown("Teste o poder do *Trend Following* no Day Trade operando nas duas pontas (**Compra e Venda**). Zeragem no Fim do Dia obrigatória.")
    
    cf1, cf2, cf3 = st.columns(3)
    with cf1:
        mapa_futuros = {"WINFUT (Mini Índice)": "WIN1!", "WDOFUT (Mini Dólar)": "WDO1!"}
        fut_selecionado = st.selectbox("Selecione o Ativo:", options=list(mapa_futuros.keys()), key="f91_ativo")
        fut_ativo = mapa_futuros[fut_selecionado] 
        fut_periodo = st.selectbox("Período:", options=['3mo', '6mo', '1y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=1, key="f91_per")
        fut_tempo = st.selectbox("Tempo Gráfico:", ['15m', '60m'], index=0, key="f91_tmp")
    with cf2:
        direcao_fut = st.selectbox("Direção do Trade:", ["Ambas (Compra e Venda)", "Apenas Compra", "Apenas Venda"], key="f91_dir")
        tipo_stop_fut = st.selectbox("Posição do Stop Inicial:", ["Extremo do Candle (Máx/Mín)", "Extremo Anterior (5 candles)"], key="f91_stop")
        tipo_cond_fut = st.selectbox("Média de Condução:", ["MME9 (Exponencial)", "MM9 (Aritmética)"], key="f91_cond")
    with cf3:
        fut_contratos = st.number_input("Contratos Iniciais:", value=1, step=1, key="f91_cont")
        valor_mult_padrao = 0.20 if "WIN" in fut_selecionado else 10.00
        fut_multiplicador = st.number_input("Multiplicador (R$):", value=valor_mult_padrao, step=0.10, format="%.2f", key="f91_mult")
        fut_zerar_daytrade = st.checkbox("⏰ Zeragem Automática no Fim do Dia", value=True, key="f91_zerar")
        st.markdown("<div style='height: 2px;'></div>", unsafe_allow_html=True)
        btn_raiox_futuros = st.button("🚀 Gerar Raio-X Futuros 9.1", type="primary", use_container_width=True, key="f91_btn")

    if btn_raiox_futuros:
        intervalo_tv = tradutor_intervalo.get(fut_tempo, Interval.in_15_minute)
        with st.spinner(f'Testando o motor do 9.1 ({direcao_fut}) em {fut_selecionado}...'):
            try:
                df_full = tv.get_hist(symbol=fut_ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=10000)
                if df_full is not None and len(df_full) > 50:
                    df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                    
                    # --- CÁLCULO DAS MÉDIAS E FUNDOS/TOPOS ---
                    df_full['MME9'] = ta.ema(df_full['Close'], length=9)
                    df_full['MME9_Prev1'] = df_full['MME9'].shift(1)
                    df_full['MME9_Prev2'] = df_full['MME9'].shift(2)
                    
                    df_full['MM9'] = ta.sma(df_full['Close'], length=9)
                    df_full['MM9_Prev1'] = df_full['MM9'].shift(1)
                    df_full['MM9_Prev2'] = df_full['MM9'].shift(2)
                    
                    df_full['Fundo_5'] = df_full['Low'].rolling(window=5).min()
                    df_full['Topo_5'] = df_full['High'].rolling(window=5).max()
                    df_full = df_full.dropna()

                    data_atual_dt = df_full.index[-1]
                    delta = {'3mo': 3, '6mo': 6, '1y': 12}.get(fut_periodo, 0)
                    data_corte = data_atual_dt - pd.DateOffset(months=delta) if delta > 0 else df_full.index[0]
                    df = df_full[df_full.index >= data_corte].copy()
                    
                    trades, vitorias, derrotas = [], 0, 0
                    
                    # Controle de Posição: 0 = Fora, 1 = Comprado, -1 = Vendido
                    posicao = 0 
                    setup_compra, setup_venda, saida_armada = False, False, False
                    gatilho_entrada, gatilho_saida, stop_loss, preco_entrada = 0.0, 0.0, 0.0, 0.0
                    
                    df_back = df.reset_index()
                    col_data = df_back.columns[0]

                    # Ajuste do Tick da B3
                    offset = 5.0 if "WIN" in fut_ativo else 0.5

                    for i in range(2, len(df_back)):
                        d_at = df_back[col_data].iloc[i]
                        d_ant = df_back[col_data].iloc[i-1]
                        
                        mme9_virou_cima = (df_back['MME9_Prev1'].iloc[i] < df_back['MME9_Prev2'].iloc[i]) and (df_back['MME9'].iloc[i] > df_back['MME9_Prev1'].iloc[i])
                        mme9_caindo = df_back['MME9'].iloc[i] < df_back['MME9_Prev1'].iloc[i]

                        mme9_virou_baixo = (df_back['MME9_Prev1'].iloc[i] > df_back['MME9_Prev2'].iloc[i]) and (df_back['MME9'].iloc[i] < df_back['MME9_Prev1'].iloc[i])
                        mme9_subindo = df_back['MME9'].iloc[i] > df_back['MME9_Prev1'].iloc[i]

                        if tipo_cond_fut == "MM9 (Aritmética)":
                            ma_atual, ma_prev1, ma_prev2 = df_back['MM9'].iloc[i], df_back['MM9_Prev1'].iloc[i], df_back['MM9_Prev2'].iloc[i]
                        else:
                            ma_atual, ma_prev1, ma_prev2 = df_back['MME9'].iloc[i], df_back['MME9_Prev1'].iloc[i], df_back['MME9_Prev2'].iloc[i]
                            
                        media_saida_virou_baixo = (ma_prev1 > ma_prev2) and (ma_atual < ma_prev1)
                        media_saida_virou_cima = (ma_prev1 < ma_prev2) and (ma_atual > ma_prev1)
                        media_saida_subindo = ma_atual > ma_prev1
                        media_saida_caindo = ma_atual < ma_prev1

                        # --- ZERAGEM NO FIM DO DIA ---
                        if posicao != 0 and fut_zerar_daytrade and d_at.date() != d_ant.date():
                            p_sai = df_back['Close'].iloc[i-1]
                            luc = (p_sai - preco_entrada) * fut_contratos * fut_multiplicador if posicao == 1 else (preco_entrada - p_sai) * fut_contratos * fut_multiplicador
                            
                            trades.append({
                                'Entrada': d_ent.strftime('%d/%m/%Y %H:%M'), 
                                'Saída': d_ant.strftime('%d/%m/%Y %H:%M'), 
                                'Tipo': 'Compra 🟢' if posicao == 1 else 'Venda 🔴',
                                'Lucro (R$)': luc, 
                                'Situação': 'Zerad. Fim Dia ✅' if luc > 0 else 'Zerad. Fim Dia ❌'
                            })
                            if luc > 0: 
                                vitorias += 1
                            else: 
                                derrotas += 1
                                
                            posicao, setup_compra, setup_venda, saida_armada = 0, False, False, False
                            continue

                        # --- LÓGICA DE OPERAÇÃO ---
                        if posicao == 1: # COMPRADO
                            if df_back['Low'].iloc[i] <= stop_loss:
                                luc = (stop_loss - preco_entrada) * fut_contratos * fut_multiplicador
                                trades.append({'Entrada': d_ent.strftime('%d/%m/%Y %H:%M'), 'Saída': d_at.strftime('%d/%m/%Y %H:%M'), 'Tipo': 'Compra 🟢', 'Lucro (R$)': luc, 'Situação': 'Stop Inicial ❌'})
                                derrotas += 1
                                posicao, saida_armada = 0, False
                                continue
                            
                            if saida_armada:
                                if df_back['Low'].iloc[i] < gatilho_saida:
                                    luc = (gatilho_saida - preco_entrada) * fut_contratos * fut_multiplicador
                                    trades.append({'Entrada': d_ent.strftime('%d/%m/%Y %H:%M'), 'Saída': d_at.strftime('%d/%m/%Y %H:%M'), 'Tipo': 'Compra 🟢', 'Lucro (R$)': luc, 'Situação': 'Saída Técnica ✅' if luc > 0 else 'Saída Técnica ❌'})
                                    if luc > 0: 
                                        vitorias += 1 
                                    else: 
                                        derrotas += 1
                                        
                                    posicao, saida_armada = 0, False
                                    continue
                                elif media_saida_subindo:
                                    saida_armada = False 

                            if media_saida_virou_baixo and not saida_armada:
                                saida_armada = True
                                gatilho_saida = df_back['Low'].iloc[i] - offset

                        elif posicao == -1: # VENDIDO
                            if df_back['High'].iloc[i] >= stop_loss:
                                luc = (preco_entrada - stop_loss) * fut_contratos * fut_multiplicador
                                trades.append({'Entrada': d_ent.strftime('%d/%m/%Y %H:%M'), 'Saída': d_at.strftime('%d/%m/%Y %H:%M'), 'Tipo': 'Venda 🔴', 'Lucro (R$)': luc, 'Situação': 'Stop Inicial ❌'})
                                derrotas += 1
                                posicao, saida_armada = 0, False
                                continue
                            
                            if saida_armada:
                                if df_back['High'].iloc[i] > gatilho_saida:
                                    luc = (preco_entrada - gatilho_saida) * fut_contratos * fut_multiplicador
                                    trades.append({'Entrada': d_ent.strftime('%d/%m/%Y %H:%M'), 'Saída': d_at.strftime('%d/%m/%Y %H:%M'), 'Tipo': 'Venda 🔴', 'Lucro (R$)': luc, 'Situação': 'Saída Técnica ✅' if luc > 0 else 'Saída Técnica ❌'})
                                    if luc > 0: 
                                        vitorias += 1 
                                    else: 
                                        derrotas += 1
                                        
                                    posicao, saida_armada = 0, False
                                    continue
                                elif media_saida_caindo:
                                    saida_armada = False

                            if media_saida_virou_cima and not saida_armada:
                                saida_armada = True
                                gatilho_saida = df_back['High'].iloc[i] + offset

                        else: # FORA DO MERCADO (BUSCANDO ENTRADAS)
                            if setup_compra:
                                if df_back['High'].iloc[i] > gatilho_entrada:
                                    posicao = 1
                                    setup_compra, setup_venda = False, False
                                    d_ent = df_back[col_data].iloc[i]
                                    preco_entrada = max(gatilho_entrada + offset, df_back['Open'].iloc[i])
                                elif mme9_caindo:
                                    setup_compra = False

                            if setup_venda and posicao == 0:
                                if df_back['Low'].iloc[i] < gatilho_entrada:
                                    posicao = -1
                                    setup_compra, setup_venda = False, False
                                    d_ent = df_back[col_data].iloc[i]
                                    preco_entrada = min(gatilho_entrada - offset, df_back['Open'].iloc[i])
                                elif mme9_subindo:
                                    setup_venda = False

                            # ARMA O SETUP (COM TRAVA DE DIREÇÃO)
                            if mme9_virou_cima and posicao == 0 and direcao_fut != "Apenas Venda":
                                setup_compra = True
                                setup_venda = False
                                gatilho_entrada = df_back['High'].iloc[i]
                                stop_loss = df_back['Fundo_5'].iloc[i] - offset if "Extremo Anterior" in tipo_stop_fut else df_back['Low'].iloc[i] - offset
                                
                            elif mme9_virou_baixo and posicao == 0 and direcao_fut != "Apenas Compra":
                                setup_venda = True
                                setup_compra = False
                                gatilho_entrada = df_back['Low'].iloc[i]
                                stop_loss = df_back['Topo_5'].iloc[i] + offset if "Extremo Anterior" in tipo_stop_fut else df_back['High'].iloc[i] + offset

                    # --- PAINEL DE RESULTADOS (DIAGNÓSTICO QUANTI) ---
                    if trades:
                        df_t = pd.DataFrame(trades)
                        st.divider()
                        st.markdown(f"### 📊 Resultado: {fut_selecionado} (9.1 {direcao_fut})")
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
                                st.success(f"🎯 **Expectativa Real Positiva:** O Payoff é o rei do Setup 9.1! Você arrisca 1 para ganhar {p_off:.2f}. Margem de gordura: {margem:.1f}% acima da taxa crítica.")
                            else:
                                st.info(f"⚖️ **Alerta de Risco:** Saldo positivo, mas payoff de {p_off:.2f} é perigoso para seguidores de tendência. A alta taxa de acerto é que está sustentando o sistema.")
                        else:
                            st.error(f"🚨 **Expectativa Negativa:** Saldo de R$ {l_total:,.2f}. O 'Efeito Serrote' machucou o robô. Se o Payoff não cobrir a taxa de erro natural da lateralização intraday, a conta não fecha.")

                        st.dataframe(df_t, use_container_width=True, hide_index=True)
                    else:
                        st.warning("Nenhuma operação concluída usando essa configuração neste período.")
            except Exception as e: st.error(f"Erro: {e}")
