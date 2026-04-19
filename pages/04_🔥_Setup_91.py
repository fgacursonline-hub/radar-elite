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
st.title("🔥 Setup 9.1 (Larry Williams)")
aba_padrao, aba_avancado, aba_individual, aba_futuros = st.tabs([
    "📡 Radar Clássico (MME9)", "⚙️ Radar Avançado (Opções)", "🔬 Raio-X Individual", "📉 Raio-X Futuros"
])

# ==========================================
# ABA 1: RADAR PADRÃO 9.1 (CLÁSSICO)
# ==========================================
with aba_padrao:
    st.subheader("📡 Radar 9.1 Clássico (MME9)")
    st.markdown("Identifica quando a MME9 vira para cima. A entrada ocorre no rompimento da máxima do candle que fez a média virar. Saída quando a média vira para baixo e perde a mínima.")
    
    cp1, cp2, cp3 = st.columns(3)
    with cp1:
        lista_91 = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"], key="p91_lista")
        ativos_91 = bdrs_elite if lista_91 == "BDRs Elite" else ibrx_selecao if lista_91 == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        periodo_91 = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=3, key="p91_per")
    with cp2:
        capital_91 = st.number_input("Capital por Trade (R$):", value=10000.0, step=1000.0, key="p91_cap")
        st.markdown("<div style='height: 75px;'></div>", unsafe_allow_html=True) 
    with cp3:
        tempo_91 = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="p91_tmp")

    btn_iniciar_91 = st.button("🚀 Iniciar Varredura 9.1", type="primary", use_container_width=True, key="p91_btn")

    if btn_iniciar_91:
        if tempo_91 == '15m' and periodo_91 not in ['1mo', '3mo']: periodo_91 = '60d'
        elif tempo_91 == '60m' and periodo_91 in ['5y', 'max']: periodo_91 = '2y'

        intervalo_tv = tradutor_intervalo.get(tempo_91, Interval.in_daily)

        ls_armados, ls_abertos, ls_resumo = [], [], []
        p_bar = st.progress(0)
        s_text = st.empty()

        for idx, ativo_raw in enumerate(ativos_91):
            ativo = ativo_raw.replace('.SA', '')
            s_text.text(f"🔍 Analisando 9.1 Clássico: {ativo} ({idx+1}/{len(ativos_91)})")
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

                # --- MOTOR DE BACKTEST DO 9.1 ---
                for i in range(2, len(df_back)):
                    # Lógica de Virada da Média
                    media_virou_cima = (df_back['MME9_Prev1'].iloc[i] < df_back['MME9_Prev2'].iloc[i]) and (df_back['MME9'].iloc[i] > df_back['MME9_Prev1'].iloc[i])
                    media_virou_baixo = (df_back['MME9_Prev1'].iloc[i] > df_back['MME9_Prev2'].iloc[i]) and (df_back['MME9'].iloc[i] < df_back['MME9_Prev1'].iloc[i])
                    media_caindo = df_back['MME9'].iloc[i] < df_back['MME9_Prev1'].iloc[i]
                    media_subindo = df_back['MME9'].iloc[i] > df_back['MME9_Prev1'].iloc[i]

                    if em_pos:
                        # 1. Verifica Stop Loss Original
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
                                # A média voltou a subir antes de perder a mínima. Cancela a saída.
                                saida_armada = False

                        # 3. Arma a saída se a MME9 virar para baixo
                        if media_virou_baixo and not saida_armada:
                            saida_armada = True
                            gatilho_saida = df_back['Low'].iloc[i]

                    else:
                        # Fora da Operação: Buscando Entradas
                        if setup_armado:
                            if df_back['High'].iloc[i] > gatilho_entrada:
                                em_pos = True
                                setup_armado = False
                                d_ent = df_back[col_data].iloc[i]
                                # Entra 1 centavo acima da máxima, ou no preço de abertura se abrir em gap de alta
                                preco_entrada = max(gatilho_entrada + 0.01, df_back['Open'].iloc[i])
                                min_price_in_trade = df_back['Low'].iloc[i]
                            elif media_caindo:
                                # Média virou pra baixo antes de ativar. Setup desconfigurado.
                                setup_armado = False

                        # Arma o setup se a MME9 virar para cima
                        if media_virou_cima:
                            setup_armado = True
                            gatilho_entrada = df_back['High'].iloc[i]
                            stop_loss = df_back['Low'].iloc[i] - 0.01 # 1 centavo abaixo da mínima

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
                    # Captura quem armou HOJE
                    media_virou_cima_hoje = (df_full['MME9_Prev1'].iloc[-1] < df_full['MME9_Prev2'].iloc[-1]) and (df_full['MME9'].iloc[-1] > df_full['MME9_Prev1'].iloc[-1])
                    if media_virou_cima_hoje:
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
        st.subheader("🔥 Setups 9.1 Armados Hoje (Compra Amanhã)")
        if len(ls_armados) > 0: st.dataframe(pd.DataFrame(ls_armados), use_container_width=True, hide_index=True)
        else: st.info("Nenhuma MME9 virou para cima no último candle.")

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
# ABA 2: RADAR AVANÇADO 9.1 (OPÇÕES DE CONDUÇÃO)
# ==========================================
with aba_avancado:
    st.subheader("⚙️ Radar 9.1 Avançado (Fundo Anterior & MM9)")
    st.markdown("A entrada continua sendo pela MME9, mas você pode alterar a localização do **Stop Inicial** (para evitar violinadas) e a **Média de Condução**.")
    
    ca1, ca2, ca3 = st.columns(3)
    with ca1:
        lista_91a = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"], key="a91_lista")
        ativos_91a = bdrs_elite if lista_91a == "BDRs Elite" else ibrx_selecao if lista_91a == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        periodo_91a = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=3, key="a91_per")
    with ca2:
        tipo_stop = st.selectbox("Posição do Stop Inicial:", ["Mínima do Candle Referência", "Fundo Anterior (Últimos 5 candles)"], key="a91_stop")
        tipo_conducao = st.selectbox("Média de Condução (Trailing):", ["MME9 (Exponencial)", "MM9 (Aritmética)"], key="a91_cond")
    with ca3:
        capital_91a = st.number_input("Capital por Trade (R$):", value=10000.0, step=1000.0, key="a91_cap")
        tempo_91a = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="a91_tmp")

    btn_iniciar_91a = st.button("🚀 Iniciar Varredura Avançada", type="primary", use_container_width=True, key="a91_btn")

    if btn_iniciar_91a:
        if tempo_91a == '15m' and periodo_91a not in ['1mo', '3mo']: periodo_91a = '60d'
        elif tempo_91a == '60m' and periodo_91a in ['5y', 'max']: periodo_91a = '2y'

        intervalo_tv = tradutor_intervalo.get(tempo_91a, Interval.in_daily)

        ls_armados_a, ls_abertos_a, ls_resumo_a = [], [], []
        p_bar_a = st.progress(0)
        s_text_a = st.empty()

        for idx, ativo_raw in enumerate(ativos_91a):
            ativo = ativo_raw.replace('.SA', '')
            s_text_a.text(f"🔍 Analisando 9.1 Avançado: {ativo} ({idx+1}/{len(ativos_91a)})")
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
                
                # MM9 Aritmética para condução alternativa
                df_full['MM9'] = ta.sma(df_full['Close'], length=9)
                df_full['MM9_Prev1'] = df_full['MM9'].shift(1)
                df_full['MM9_Prev2'] = df_full['MM9'].shift(2)
                
                # Rastreador de Fundo Anterior (Mínima dos últimos 5 candles)
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

                for i in range(2, len(df_back)):
                    # A ENTRADA É SEMPRE PELA MME9
                    mme9_virou_cima = (df_back['MME9_Prev1'].iloc[i] < df_back['MME9_Prev2'].iloc[i]) and (df_back['MME9'].iloc[i] > df_back['MME9_Prev1'].iloc[i])
                    mme9_caindo = df_back['MME9'].iloc[i] < df_back['MME9_Prev1'].iloc[i]

                    # A SAÍDA DEPENDE DA ESCOLHA DO UTILIZADOR
                    if tipo_conducao == "MM9 (Aritmética)":
                        ma_atual = df_back['MM9'].iloc[i]
                        ma_prev1 = df_back['MM9_Prev1'].iloc[i]
                        ma_prev2 = df_back['MM9_Prev2'].iloc[i]
                    else:
                        ma_atual = df_back['MME9'].iloc[i]
                        ma_prev1 = df_back['MME9_Prev1'].iloc[i]
                        ma_prev2 = df_back['MME9_Prev2'].iloc[i]
                        
                    media_saida_virou_baixo = (ma_prev1 > ma_prev2) and (ma_atual < ma_prev1)
                    media_saida_subindo = ma_atual > ma_prev1

                    if em_pos:
                        # 1. Stop Loss Inicial
                        if df_back['Low'].iloc[i] <= stop_loss:
                            d_sai = df_back[col_data].iloc[i]
                            duracao = (d_sai - d_ent).days
                            lucro_rs = capital_91a * ((stop_loss / preco_entrada) - 1)
                            trades.append({'Entrada': d_ent, 'Duração': duracao, 'Lucro (R$)': lucro_rs, 'Situação': 'Stop Acionado ❌'})
                            if lucro_rs > 0: vitorias += 1 else: derrotas += 1
                            em_pos, saida_armada = False, False
                            continue
                        
                        # 2. Gatilho de Saída Técnica (Trailing Stop)
                        if saida_armada:
                            if df_back['Low'].iloc[i] < gatilho_saida:
                                d_sai = df_back[col_data].iloc[i]
                                duracao = (d_sai - d_ent).days
                                lucro_rs = capital_91a * ((gatilho_saida / preco_entrada) - 1)
                                trades.append({'Entrada': d_ent, 'Duração': duracao, 'Lucro (R$)': lucro_rs, 'Situação': 'Saída Técnica ✅' if lucro_rs > 0 else 'Saída Técnica ❌'})
                                if lucro_rs > 0: vitorias += 1 else: derrotas += 1
                                em_pos, saida_armada = False, False
                                continue
                            elif media_saida_subindo:
                                # Se a média voltar a subir antes de perder a mínima, desarma a saída
                                saida_armada = False

                        # 3. Arma a saída se a média de condução escolhida virar para baixo
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
                            elif mme9_caindo:
                                setup_armado = False

                        if mme9_virou_cima:
                            setup_armado = True
                            gatilho_entrada = df_back['High'].iloc[i]
                            # Define o Stop Inicial com base na escolha do utilizador
                            if tipo_stop == "Fundo Anterior (Últimos 5 candles)":
                                stop_loss = df_back['Fundo_5'].iloc[i] - 0.01
                            else:
                                stop_loss = df_back['Low'].iloc[i] - 0.01

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
                    mme9_virou_cima_hoje = (df_full['MME9_Prev1'].iloc[-1] < df_full['MME9_Prev2'].iloc[-1]) and (df_full['MME9'].iloc[-1] > df_full['MME9_Prev1'].iloc[-1])
                    if mme9_virou_cima_hoje:
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
        st.subheader("🔥 Setups 9.1 Armados Hoje (Compra Amanhã)")
        if len(ls_armados_a) > 0: st.dataframe(pd.DataFrame(ls_armados_a), use_container_width=True, hide_index=True)
        else: st.info("Nenhuma MME9 virou para cima no último candle.")

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
with aba_individual: st.info("Em breve: Raio-X Individual do 9.1.")
with aba_futuros: st.info("Em breve: Raio-X Futuros do 9.1.")
