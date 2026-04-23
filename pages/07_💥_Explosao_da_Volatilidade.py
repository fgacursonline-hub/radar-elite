import streamlit as st
from tvDatafeed import TvDatafeed, Interval
import pandas as pd
import pandas_ta as ta
import time
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 0. FUNÇÕES MATEMÁTICAS DE ELITE
# ==========================================
def aplicar_filtro_keltner_bb(df, length=20, mult_kc=1.5, mult_bb=2.0):
    """
    Motor TTM Squeeze traduzido do Pine Script.
    """
    # 1. Linha Central
    df['Basis'] = df['Close'].rolling(window=length).mean()

    # 2. Cálculo do True Range (TR)
    df['prev_close'] = df['Close'].shift(1)
    df['tr1'] = df['High'] - df['Low']
    df['tr2'] = abs(df['High'] - df['prev_close'])
    df['tr3'] = abs(df['Low'] - df['prev_close'])
    df['TR'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)

    # 3. Canais de Keltner
    df['Range_KC'] = df['TR'].rolling(window=length).mean()
    df['KC_Upper'] = df['Basis'] + (df['Range_KC'] * mult_kc)
    df['KC_Lower'] = df['Basis'] - (df['Range_KC'] * mult_kc)

    # 4. Bandas de Bollinger (ddof=0 para igualar ao TradingView)
    df['Stdev'] = df['Close'].rolling(window=length).std(ddof=0)
    df['Dev_BB'] = mult_bb * df['Stdev']
    df['BB_Upper'] = df['Basis'] + df['Dev_BB']
    df['BB_Lower'] = df['Basis'] - df['Dev_BB']

    # 5. Lógica de Explosão (Bollinger rasga o Keltner)
    df['isDanger'] = (df['BB_Lower'] < df['KC_Lower']) | (df['BB_Upper'] > df['KC_Upper'])

    # 6. Gatilho de Início exato
    df['Inicio_Tendencia'] = df['isDanger'] & (~df['isDanger'].shift(1).fillna(False))

    # Limpeza
    df.drop(columns=['prev_close', 'tr1', 'tr2', 'tr3', 'TR', 'Range_KC', 'Stdev', 'Dev_BB'], inplace=True)
    return df

# ==========================================
# 1. SEGURANÇA E CONEXÃO
# ==========================================
if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

@st.cache_resource
def get_tv_connection():
    return TvDatafeed()

tv = get_tv_connection()

tradutor_intervalo = {
    '15m': Interval.in_15_minute,
    '60m': Interval.in_1_hour,
    '1d': Interval.in_daily,
    '1wk': Interval.in_weekly
}
tradutor_periodo_nome = {
    '1mo': '1 Mês', '3mo': '3 Meses', '6mo': '6 Meses',
    '1y': '1 Ano', '2y': '2 Anos', '5y': '5 Anos',
    'max': 'Máximo', '60d': '60 Dias'
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

# ==========================================
# 2. INTERFACE E ABAS
# ==========================================
col_titulo, col_botao = st.columns([4, 1])
with col_titulo:
    st.title("💥 Explosão da Volatilidade")
with col_botao:
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.link_button("📖 Ler Manual", "https://seusite.com/manual_volatilidade", use_container_width=True)

aba_radar, aba_ttm, aba_individual = st.tabs(["📡 Scanner Tático", "🧨 Motor TTM Squeeze", "🔬 Raio-X Individual"])

# ==========================================
# ABA 1: SCANNER TÁTICO
# ==========================================
with aba_radar:
    st.subheader("🔍 Scanner de Compressão de Volatilidade")
    st.markdown("Varre o mercado em busca de Molas Comprimidas (NR4/NR7) e Contra-Golpes Táticos.")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        lista_sel = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"], key="vol_lst")
        tipo_setup = st.selectbox("Estratégia de Elite:", ["Mola Comprimida (NR4)", "Mola Mestra (NR7)", "Contra-Golpe Tático"], key="vol_setup")
    with c2:
        tempo_grafico = st.selectbox("Tempo Gráfico:", ['1d', '1wk', '60m', '15m'], index=0, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="vol_tmp")
        tipo_filtro = st.selectbox("Filtro de Compressão (Caixote):", ["Bollinger Squeeze (Bandas Estreitas)", "Médias Emboladas (MME9 próxima à MM21)", "Sem Filtro (Sinal Puro)"], key="vol_filtro", disabled=("Contra-Golpe" in tipo_setup)) 
    with c3:
        st.info("💡 **Dica Tática:** O Contra-Golpe exige MM21 inclinada a favor do movimento. A Mola Comprimida prospera na letargia e baixa volatilidade.")

    nome_botao = tipo_setup.split('(')[0].strip()
    btn_iniciar = st.button(f"🚀 Iniciar Scanner: {nome_botao}", type="primary", use_container_width=True)

    if btn_iniciar:
        ativos_analise = bdrs_elite if lista_sel == "BDRs Elite" else ibrx_selecao if lista_sel == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        intervalo_tv = tradutor_intervalo.get(tempo_grafico, Interval.in_daily)
        
        ls_sinais = []
        p_bar = st.progress(0)
        s_text = st.empty()

        for idx, ativo_raw in enumerate(ativos_analise):
            ativo = ativo_raw.replace('.SA', '')
            s_text.text(f"🔍 Escaneando o campo de batalha: {ativo} ({idx+1}/{len(ativos_analise)})")
            p_bar.progress((idx + 1) / len(ativos_analise))

            try:
                df = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=150)
                if df is None or len(df) < 30: continue

                df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                
                df['Range'] = df['High'] - df['Low']
                df['MM21'] = ta.sma(df['Close'], length=21)
                df['MME9'] = ta.ema(df['Close'], length=9)
                df['Cor'] = 'Verde'
                df.loc[df['Close'] < df['Open'], 'Cor'] = 'Vermelho'
                
                if "Mola" in tipo_setup:
                    janela = 4 if "NR4" in tipo_setup else 7
                    df[f'Min_Range'] = df['Range'].rolling(window=janela).min()
                    
                    mercado_lateral = True
                    if "Bollinger" in tipo_filtro:
                        bb = ta.bbands(df['Close'], length=20, std=2)
                        bb_width = (bb['BBU_20_2.0'] - bb['BBL_20_2.0']) / bb['BBM_20_2.0']
                        mercado_lateral = bb_width.iloc[-1] < bb_width.rolling(20).mean().iloc[-1]
                    elif "Médias" in tipo_filtro:
                        dist = abs(df['MME9'] - df['MM21']) / df['Close'] * 100
                        mercado_lateral = dist.iloc[-1] < 1.5

                    if df['Range'].iloc[-1] == df['Min_Range'].iloc[-1] and mercado_lateral:
                        ls_sinais.append({
                            'Ativo': ativo, 'Sinal': f"💥 {'Mola Comprimida' if janela == 4 else 'Mola Mestra'}", 
                            'Direção': 'Compra/Venda', 'Gatilho Compra': f"R$ {df['High'].iloc[-1]+0.01:.2f}",
                            'Gatilho Venda': f"R$ {df['Low'].iloc[-1]-0.01:.2f}", 'Obs': f"Pressão máxima em {janela} períodos"
                        })

                elif "Contra-Golpe" in tipo_setup:
                    tendencia_alta = df['MM21'].iloc[-1] > df['MM21'].iloc[-2]
                    tendencia_baixa = df['MM21'].iloc[-1] < df['MM21'].iloc[-2]
                    
                    c0, c1, c2 = df['Cor'].iloc[-3], df['Cor'].iloc[-2], df['Cor'].iloc[-1]
                    
                    if tendencia_alta and c0 == 'Vermelho' and c1 == 'Verde' and c2 == 'Vermelho':
                        max_conjunto = df['High'].iloc[-3:].max()
                        ls_sinais.append({
                            'Ativo': ativo, 'Sinal': '🛡️ Contra-Golpe Tático', 
                            'Direção': 'COMPRA 🟢', 'Gatilho Compra': f"R$ {max_conjunto+0.01:.2f}",
                            'Gatilho Venda': '-', 'Obs': 'Armadilha para Vendidos Armada'
                        })
                    
                    elif tendencia_baixa and c0 == 'Verde' and c1 == 'Vermelho' and c2 == 'Verde':
                        min_conjunto = df['Low'].iloc[-3:].min()
                        ls_sinais.append({
                            'Ativo': ativo, 'Sinal': '📉 Contra-Golpe Tático', 
                            'Direção': 'VENDA 🔴', 'Gatilho Compra': '-',
                            'Gatilho Venda': f"R$ {min_conjunto-0.01:.2f}", 'Obs': 'Armadilha para Compradores Armada'
                        })

            except Exception as e: pass
            time.sleep(0.01)

        s_text.empty()
        p_bar.empty()

        st.divider()
        if ls_sinais:
            st.success(f"🎯 Varredura concluída! {len(ls_sinais)} oportunidades táticas detectadas.")
            st.dataframe(pd.DataFrame(ls_sinais), use_container_width=True, hide_index=True)
        else:
            st.warning("O campo de batalha está neutro hoje. Nenhum padrão de explosão ou contra-golpe validado.")

# ==========================================
# ABA 2: MOTOR TTM SQUEEZE
# ==========================================
with aba_ttm:
    st.subheader("🧨 Motor de Explosão: TTM Squeeze")
    st.markdown("O sistema rastreia ativos que estavam em forte consolidação (Bollinger dentro do Keltner) e que **hoje** iniciaram uma explosão direcional de força institucional.")
    
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        ttm_lista = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"], key="ttm_lst")
        ttm_length = st.number_input("Períodos (Keltner e Volatilidade)", value=20, step=1)
    with col_t2:
        ttm_tempo = st.selectbox("Tempo Gráfico:", ['1d', '60m', '15m'], index=0, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário'}[x], key="ttm_tmp")
        ttm_mult_kc = st.number_input("Multiplicador do Canal Keltner", value=1.5, step=0.1)
    with col_t3:
        st.error("🚨 **Sinal de Perigo:** O robô detecta a exata ignição direcional das bandas.")
        ttm_mult_bb = st.number_input("Multiplicador do Bollinger", value=2.0, step=0.1)

    btn_ttm = st.button("🧨 Varrer o Mercado (TTM Squeeze)", type="primary", use_container_width=True)

    if btn_ttm:
        ativos_ttm = bdrs_elite if ttm_lista == "BDRs Elite" else ibrx_selecao if ttm_lista == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        intervalo_tv = tradutor_intervalo.get(ttm_tempo, Interval.in_daily)
        
        sinais_ttm = []
        p_bar_ttm = st.progress(0)
        st_txt_ttm = st.empty()

        for idx, ativo_raw in enumerate(ativos_ttm):
            ativo = ativo_raw.replace('.SA', '')
            st_txt_ttm.text(f"🧨 Analisando compressão: {ativo} ({idx+1}/{len(ativos_ttm)})")
            p_bar_ttm.progress((idx + 1) / len(ativos_ttm))

            try:
                df = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=100)
                if df is None or len(df) < 30: continue
                df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                
                df = aplicar_filtro_keltner_bb(df, length=ttm_length, mult_kc=ttm_mult_kc, mult_bb=ttm_mult_bb)
                
                if df['Inicio_Tendencia'].iloc[-1] == True:
                    # Verifica a direção comparando com a linha central do Keltner
                    is_alta = df['Close'].iloc[-1] > df['Basis'].iloc[-1]
                    
                    direcao = "📈 ALTA" if is_alta else "📉 BAIXA"
                    gatilho_entrada = df['High'].iloc[-1] + 0.01 if is_alta else df['Low'].iloc[-1] - 0.01
                    
                    sinais_ttm.append({
                        'Ativo': ativo,
                        'Alerta': '🚨 IGNICÃO TTM',
                        'Direção': direcao,
                        'Gatilho (Entrada)': f"R$ {gatilho_entrada:.2f}",
                        'Preço Atual': f"R$ {df['Close'].iloc[-1]:.2f}"
                    })
            except Exception as e: pass
            time.sleep(0.01)

        st_txt_ttm.empty()
        p_bar_ttm.empty()

        st.divider()
        if sinais_ttm:
            st.success(f"🔥 Foram detectadas {len(sinais_ttm)} ignições de volatilidade hoje!")
            st.dataframe(pd.DataFrame(sinais_ttm), use_container_width=True, hide_index=True)
        else:
            st.warning("O mercado está calmo. Nenhuma ignição direcional identificada neste momento.")

# ==========================================
# ABA 3: RAIO-X INDIVIDUAL
# ==========================================
with aba_individual:
    st.subheader("🔬 Raio-X Individual: Laboratório de Backtest")
    st.markdown("Teste o desempenho histórico da Compressão de Volatilidade e do Contra-Golpe em um ativo específico.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        rx_ativo = st.text_input("Ativo (Ex: M1TA34):", value="M1TA34", key="rx_vol_ativo")
        rx_periodo = st.selectbox("Período do Backtest:", options=['3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=3, key="rx_vol_per")
    with col2:
        rx_setup = st.selectbox("Estratégia de Elite:", ["Mola Comprimida (NR4)", "Mola Mestra (NR7)", "Contra-Golpe Tático"], key="rx_vol_setup")
        rx_filtro = st.selectbox("Filtro de Compressão:", ["Bollinger Squeeze", "Médias Emboladas", "Sem Filtro"], key="rx_vol_filtro", disabled=("Contra-Golpe" in rx_setup))
    with col3:
        rx_tempo = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="rx_vol_tmp")
        rx_capital = st.number_input("Capital por Operação (R$):", value=10000.0, step=1000.0, key="rx_vol_cap")
        
    btn_raiox = st.button(f"🔍 Gerar Raio-X: {rx_setup.split('(')[0].strip()}", type="primary", use_container_width=True)

    if btn_raiox:
        ativo_input = rx_ativo.strip().upper().replace('.SA', '')
        if not ativo_input:
            st.error("Digite o código de um ativo.")
        else:
            intervalo_tv = tradutor_intervalo.get(rx_tempo, Interval.in_daily)
            with st.spinner(f'Processando histórico de {ativo_input}...'):
                try:
                    df_full = tv.get_hist(symbol=ativo_input, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=5000)
                    if df_full is None or len(df_full) < 50:
                        st.error("Dados insuficientes para este ativo.")
                    else:
                        df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                        
                        df_full['Range'] = df_full['High'] - df_full['Low']
                        df_full['MM21'] = ta.sma(df_full['Close'], length=21)
                        df_full['MME9'] = ta.ema(df_full['Close'], length=9)
                        
                        df_full['Cor'] = 'Verde'
                        df_full.loc[df_full['Close'] < df_full['Open'], 'Cor'] = 'Vermelho'
                        
                        bb = ta.bbands(df_full['Close'], length=20, std=2)
                        if bb is not None and not bb.empty:
                            col_u = [c for c in bb.columns if 'BBU' in c][0]
                            col_l = [c for c in bb.columns if 'BBL' in c][0]
                            col_m = [c for c in bb.columns if 'BBM' in c][0]
                            df_full['BB_Width'] = (bb[col_u] - bb[col_l]) / bb[col_m]
                            df_full['BB_Width_Med'] = df_full['BB_Width'].rolling(20).mean()
                        else:
                            df_full['BB_Width'] = 0.0
                            df_full['BB_Width_Med'] = 0.0

                        df_full = df_full.dropna()

                        data_atual = df_full.index[-1]
                        if rx_periodo == '3mo': data_corte = data_atual - pd.DateOffset(months=3)
                        elif rx_periodo == '6mo': data_corte = data_atual - pd.DateOffset(months=6)
                        elif rx_periodo == '1y': data_corte = data_atual - pd.DateOffset(years=1)
                        elif rx_periodo == '2y': data_corte = data_atual - pd.DateOffset(years=2)
                        elif rx_periodo == '5y': data_corte = data_atual - pd.DateOffset(years=5)
                        else: data_corte = df_full.index[0]

                        df = df_full[df_full.index >= data_corte].copy()
                        df_back = df.reset_index()
                        col_data = df_back.columns[0]

                        trades = []
                        em_pos = False
                        direcao = 0
                        preco_entrada = 0.0
                        stop_loss = 0.0
                        alvo = 0.0
                        d_ent = None
                        
                        setup_compra_armado = False
                        setup_venda_armado = False
                        gatilho_compra = 0.0
                        gatilho_venda = 0.0
                        validade_setup = 0
                        sl_pendente_c = 0.0
                        sl_pendente_v = 0.0
                        alvo_pendente_c = 0.0
                        alvo_pendente_v = 0.0

                        vitorias, derrotas = 0, 0

                        for i in range(7, len(df_back)):
                            atual = df_back.iloc[i]
                            ontem = df_back.iloc[i-1]

                            if em_pos:
                                if direcao == 1: 
                                    if atual['Low'] <= stop_loss:
                                        d_sai = atual[col_data]
                                        lucro = rx_capital * ((stop_loss / preco_entrada) - 1)
                                        trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': d_sai.strftime('%d/%m/%Y'), 'Tipo': 'Compra 🟢', 'Lucro (R$)': lucro, 'Situação': 'Stop Acionado ❌'})
                                        derrotas += 1; em_pos = False
                                    elif atual['High'] >= alvo:
                                        d_sai = atual[col_data]
                                        lucro = rx_capital * ((alvo / preco_entrada) - 1)
                                        trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': d_sai.strftime('%d/%m/%Y'), 'Tipo': 'Compra 🟢', 'Lucro (R$)': lucro, 'Situação': 'Alvo Atingido 🎯'})
                                        vitorias += 1; em_pos = False

                                elif direcao == -1: 
                                    if atual['High'] >= stop_loss:
                                        d_sai = atual[col_data]
                                        lucro = rx_capital * ((preco_entrada - stop_loss) / preco_entrada)
                                        trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': d_sai.strftime('%d/%m/%Y'), 'Tipo': 'Venda 🔴', 'Lucro (R$)': lucro, 'Situação': 'Stop Acionado ❌'})
                                        derrotas += 1; em_pos = False
                                    elif atual['Low'] <= alvo:
                                        d_sai = atual[col_data]
                                        lucro = rx_capital * ((preco_entrada - alvo) / preco_entrada)
                                        trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': d_sai.strftime('%d/%m/%Y'), 'Tipo': 'Venda 🔴', 'Lucro (R$)': lucro, 'Situação': 'Alvo Atingido 🎯'})
                                        vitorias += 1; em_pos = False
                                continue 

                            entrou_hoje = False
                            if setup_compra_armado:
                                if atual['High'] > gatilho_compra:
                                    em_pos = True; direcao = 1; entrou_hoje = True
                                    preco_entrada = max(gatilho_compra, atual['Open'])
                                    stop_loss = sl_pendente_c; alvo = alvo_pendente_c
                                    d_ent = atual[col_data]
                                    setup_compra_armado = False; setup_venda_armado = False
                                else:
                                    validade_setup -= 1
                                    if validade_setup <= 0 or atual['Low'] < sl_pendente_c:
                                        setup_compra_armado = False 

                            if not entrou_hoje and setup_venda_armado:
                                if atual['Low'] < gatilho_venda:
                                    em_pos = True; direcao = -1; entrou_hoje = True
                                    preco_entrada = min(gatilho_venda, atual['Open'])
                                    stop_loss = sl_pendente_v; alvo = alvo_pendente_v
                                    d_ent = atual[col_data]
                                    setup_compra_armado = False; setup_venda_armado = False
                                else:
                                    validade_setup -= 1
                                    if validade_setup <= 0 or atual['High'] > sl_pendente_v:
                                        setup_venda_armado = False

                            if not em_pos and not entrou_hoje:
                                if "Mola" in rx_setup:
                                    janela = 4 if "NR4" in rx_setup else 7
                                    min_range_janela = df_back['Range'].iloc[i-janela:i].min() 
                                    
                                    mercado_lateral = True
                                    if "Bollinger" in rx_filtro:
                                        mercado_lateral = ontem['BB_Width'] < ontem['BB_Width_Med']
                                    elif "Médias" in rx_filtro:
                                        mercado_lateral = (abs(ontem['MME9'] - ontem['MM21']) / ontem['Close'] * 100) < 1.5

                                    if ontem['Range'] == min_range_janela and mercado_lateral:
                                        setup_compra_armado = True
                                        setup_venda_armado = True
                                        gatilho_compra = ontem['High'] + 0.01
                                        gatilho_venda = ontem['Low'] - 0.01
                                        sl_pendente_c = ontem['Low'] - 0.01
                                        sl_pendente_v = ontem['High'] + 0.01
                                        amplitude = ontem['Range']
                                        alvo_pendente_c = gatilho_compra + amplitude
                                        alvo_pendente_v = gatilho_venda - amplitude
                                        validade_setup = 1 

                                elif "Contra-Golpe" in rx_setup:
                                    tend_alta = df_back['MM21'].iloc[i-1] > df_back['MM21'].iloc[i-2]
                                    tend_baixa = df_back['MM21'].iloc[i-1] < df_back['MM21'].iloc[i-2]
                                    
                                    c_2, c_1, c_0 = df_back['Cor'].iloc[i-3], df_back['Cor'].iloc[i-2], df_back['Cor'].iloc[i-1]

                                    if tend_alta and c_2 == 'Vermelho' and c_1 == 'Verde' and c_0 == 'Vermelho':
                                        setup_compra_armado = True
                                        max_conj = df_back['High'].iloc[i-3:i].max()
                                        min_conj = df_back['Low'].iloc[i-3:i].min()
                                        gatilho_compra = max_conj + 0.01
                                        sl_pendente_c = min_conj - 0.01
                                        alvo_pendente_c = gatilho_compra + (max_conj - min_conj)
                                        validade_setup = 5 

                                    elif tend_baixa and c_2 == 'Verde' and c_1 == 'Vermelho' and c_0 == 'Verde':
                                        setup_venda_armado = True
                                        max_conj = df_back['High'].iloc[i-3:i].max()
                                        min_conj = df_back['Low'].iloc[i-3:i].min()
                                        gatilho_venda = min_conj - 0.01
                                        sl_pendente_v = max_conj + 0.01
                                        alvo_pendente_v = gatilho_venda - (max_conj - min_conj)
                                        validade_setup = 5

                        st.divider()
                        st.markdown(f"### 📊 Resultado: {ativo_input} ({rx_setup.split('(')[0].strip()})")
                        
                        if len(trades) > 0:
                            df_t = pd.DataFrame(trades)
                            
                            l_total = df_t['Lucro (R$)'].sum()
                            vits_df = df_t[df_t['Lucro (R$)'] > 0]
                            derrs_df = df_t[df_t['Lucro (R$)'] <= 0]
                            t_acerto = (len(vits_df) / len(df_t)) * 100
                            
                            m_ganho = vits_df['Lucro (R$)'].mean() if not vits_df.empty else 0
                            m_perda = abs(derrs_df['Lucro (R$)'].mean()) if not derrs_df.empty else 1
                            p_off = m_ganho / m_perda

                            m1, m2, m3, m4 = st.columns(4)
                            m1.metric("Lucro Acumulado", f"R$ {l_total:,.2f}", delta=f"{l_total:,.2f}")
                            m2.metric("Nº de Operações", len(df_t))
                            m3.metric("Taxa de Acerto", f"{t_acerto:.1f}%")
                            m4.metric("Payoff Média", f"{p_off:.2f}")

                            if l_total > 0:
                                st.success("🟢 **Estratégia Vencedora:** O modelo matemático extraiu dinheiro do mercado neste ativo e período.")
                            else:
                                st.error("🔴 **Estratégia Perdedora:** Cuidado, o ativo apresentou muitos falsos rompimentos machucando a taxa de acerto.")

                            st.dataframe(df_t, use_container_width=True, hide_index=True)
                        else:
                            st.warning("Nenhuma operação ativou e fechou o ciclo completo neste período.")
                except Exception as e: st.error(f"Erro no processamento: {e}")
