import streamlit as st
import streamlit.components.v1 as components
from tvDatafeed import TvDatafeed, Interval
import pandas as pd
import pandas_ta as ta
import time
import warnings
import sys
import os

warnings.filterwarnings('ignore')

# --- IMPORTAÇÃO CENTRALIZADA DOS ATIVOS ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from config_ativos import bdrs_elite, ibrx_selecao
except ImportError:
    st.error("❌ Arquivo 'config_ativos.py' não encontrado na raiz do projeto.")
    st.stop()

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

def colorir_lucro(row):
    if 'Resultado Atual' in row and isinstance(row['Resultado Atual'], str) and row['Resultado Atual'].startswith('+'):
        return ['color: #00FF00; font-weight: bold'] * len(row)
    return [''] * len(row)

# Função para renderizar o Widget Oficial do TradingView
def renderizar_grafico_tv(simbolo_tv, altura=600):
    html_tv = f"""
    <div class="tradingview-widget-container">
      <div id="tradingview_elite"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget(
      {{
      "width": "100%",
      "height": {altura},
      "symbol": "{simbolo_tv}",
      "interval": "D",
      "timezone": "America/Sao_Paulo",
      "theme": "dark",
      "style": "1",
      "locale": "br",
      "enable_publishing": false,
      "allow_symbol_change": true,
      "container_id": "tradingview_elite"
    }}
      );
      </script>
    </div>
    """
    components.html(html_tv, height=altura)

# 3. INTERFACE DE ABAS
col_titulo, col_botao = st.columns([4, 1])

with col_titulo:
    st.title("🔥 Setup 9.x (Larry Williams)")

with col_botao:
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
        setup_escolhido = st.selectbox("Escolha a Estratégia:", ["Setup 9.1 (Virada de Média)", "Setup 9.2 (Pullback Curto)", "Setup 9.3 (Pullback Duplo)", "Setup 9.4 (Shakeout)"], key="p91_setup")
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
                
                df_full['MME9'] = ta.ema(df_full['Close'], length=9)
                df_full['MME9_Prev1'] = df_full['MME9'].shift(1)
                df_full['MME9_Prev2'] = df_full['MME9'].shift(2)
                df_full['MME9_Prev3'] = df_full['MME9'].shift(3) 
                
                # ADIÇÃO DO FILTRO MM21
                df_full['MM21'] = ta.sma(df_full['Close'], length=21)
                
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

                for i in range(3, len(df_back)):
                    mme9_atual = df_back['MME9'].iloc[i]
                    mme9_p1 = df_back['MME9_Prev1'].iloc[i]
                    mme9_p2 = df_back['MME9_Prev2'].iloc[i]
                    mme9_p3 = df_back['MME9_Prev3'].iloc[i]
                    
                    mm21_atual = df_back['MM21'].iloc[i]
                    close_atual = df_back['Close'].iloc[i]

                    media_virou_cima = (mme9_p1 < mme9_p2) and (mme9_atual > mme9_p1)
                    media_virou_baixo = (mme9_p1 > mme9_p2) and (mme9_atual < mme9_p1)
                    media_caindo = mme9_atual < mme9_p1
                    media_subindo = mme9_atual > mme9_p1

                    fechou_abaixo_min_ant = df_back['Close'].iloc[i] < df_back['Low'].iloc[i-1]
                    fechou_abaixo_fech_ant1 = df_back['Close'].iloc[i] < df_back['Close'].iloc[i-1]
                    fechou_abaixo_fech_ant2 = df_back['Close'].iloc[i-1] < df_back['Close'].iloc[i-2]
                    
                    # 9.4 COM FILTRO DE ELITE
                    mme9_shakeout = (mme9_p2 > mme9_p3) and (mme9_p1 < mme9_p2) and (mme9_atual > mme9_p1)
                    setup_94_compra = mme9_shakeout and (mme9_atual > mm21_atual) and (close_atual > mme9_atual)

                    if em_pos:
                        if df_back['Low'].iloc[i] <= stop_loss:
                            d_sai = df_back[col_data].iloc[i]
                            duracao = (d_sai - d_ent).days
                            lucro_rs = capital_91 * ((stop_loss / preco_entrada) - 1)
                            trades.append({'Entrada': d_ent, 'Duração': duracao, 'Lucro (R$)': lucro_rs, 'Situação': 'Stop Acionado ❌'})
                            if lucro_rs > 0: vitorias += 1 
                            else: derrotas += 1
                            em_pos, saida_armada = False, False
                            continue
                        
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

                        if media_virou_baixo and not saida_armada:
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
                                if "9.1" in setup_escolhido or "9.4" in setup_escolhido:
                                    if media_caindo: setup_armado = False
                                elif "9.2" in setup_escolhido or "9.3" in setup_escolhido:
                                    if media_subindo:
                                        gatilho_entrada = df_back['High'].iloc[i]
                                        stop_loss = df_back['Low'].iloc[i] - 0.01
                                    else:
                                        setup_armado = False

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
                        elif "9.4" in setup_escolhido and setup_94_compra:
                            setup_armado = True
                            gatilho_entrada = df_back['High'].iloc[i]
                            stop_loss = df_back['Low'].iloc[i] - 0.01

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
                    mme9_hj = df_full['MME9'].iloc[-1]
                    mme9_p1_hj = df_full['MME9_Prev1'].iloc[-1]
                    mme9_p2_hj = df_full['MME9_Prev2'].iloc[-1]
                    mme9_p3_hj = df_full['MME9_Prev3'].iloc[-1]
                    
                    mm21_hj = df_full['MM21'].iloc[-1]
                    close_hj = df_full['Close'].iloc[-1]

                    subindo_hj = mme9_hj > mme9_p1_hj
                    virou_cima_hj = (mme9_p1_hj < mme9_p2_hj) and subindo_hj
                    f_abx_min_hj = df_full['Close'].iloc[-1] < df_full['Low'].iloc[-2]
                    f_abx_f1_hj = df_full['Close'].iloc[-1] < df_full['Close'].iloc[-2]
                    f_abx_f2_hj = df_full['Close'].iloc[-2] < df_full['Close'].iloc[-3]
                    
                    # 9.4 HOJE COM FILTRO DE ELITE
                    mme9_shakeout_hj = (mme9_p2_hj > mme9_p3_hj) and (mme9_p1_hj < mme9_p2_hj) and (mme9_hj > mme9_p1_hj)
                    setup_94_compra_hj = mme9_shakeout_hj and (mme9_hj > mm21_hj) and (close_hj > mme9_hj)

                    armou_hoje = False
                    if "9.1" in setup_escolhido and virou_cima_hj: armou_hoje = True
                    elif "9.2" in setup_escolhido and subindo_hj and f_abx_min_hj: armou_hoje = True
                    elif "9.3" in setup_escolhido and subindo_hj and f_abx_f1_hj and f_abx_f2_hj: armou_hoje = True
                    elif "9.4" in setup_escolhido and setup_94_compra_hj: armou_hoje = True

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

# ==========================================
# ABA 2: RADAR AVANÇADO (FAMÍLIA 9.x)
# ==========================================
with aba_avancado:
    st.subheader("⚙️ Radar Avançado (Fundo Anterior & MM9)")
    st.markdown("Opere os Setups 9.1, 9.2, 9.3 ou 9.4 com flexibilidade para alterar a localização do **Stop Inicial** (para evitar violinadas) e a **Média de Condução**.")
    
    ca1, ca2, ca3 = st.columns(3)
    with ca1:
        lista_91a = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"], key="a91_lista")
        periodo_91a = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=3, key="a91_per")
        setup_escolhido_a = st.selectbox("Escolha a Estratégia:", ["Setup 9.1 (Virada de Média)", "Setup 9.2 (Pullback Curto)", "Setup 9.3 (Pullback Duplo)", "Setup 9.4 (Shakeout)"], key="a91_setup")
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
                
                df_full['MME9'] = ta.ema(df_full['Close'], length=9)
                df_full['MME9_Prev1'] = df_full['MME9'].shift(1)
                df_full['MME9_Prev2'] = df_full['MME9'].shift(2)
                df_full['MME9_Prev3'] = df_full['MME9'].shift(3)
                
                df_full['MM9'] = ta.sma(df_full['Close'], length=9)
                df_full['MM9_Prev1'] = df_full['MM9'].shift(1)
                df_full['MM9_Prev2'] = df_full['MM9'].shift(2)
                
                # ADIÇÃO DO FILTRO MM21
                df_full['MM21'] = ta.sma(df_full['Close'], length=21)
                
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

                for i in range(3, len(df_back)):
                    mme9_atual = df_back['MME9'].iloc[i]
                    mme9_p1 = df_back['MME9_Prev1'].iloc[i]
                    mme9_p2 = df_back['MME9_Prev2'].iloc[i]
                    mme9_p3 = df_back['MME9_Prev3'].iloc[i]
                    
                    mm21_atual = df_back['MM21'].iloc[i]
                    close_atual = df_back['Close'].iloc[i]

                    media_virou_cima = (mme9_p1 < mme9_p2) and (mme9_atual > mme9_p1)
                    media_virou_baixo = (mme9_p1 > mme9_p2) and (mme9_atual < mme9_p1)
                    media_caindo = mme9_atual < mme9_p1
                    media_subindo = mme9_atual > mme9_p1

                    fechou_abaixo_min_ant = df_back['Close'].iloc[i] < df_back['Low'].iloc[i-1]
                    fechou_abaixo_fech_ant1 = df_back['Close'].iloc[i] < df_back['Close'].iloc[i-1]
                    fechou_abaixo_fech_ant2 = df_back['Close'].iloc[i-1] < df_back['Close'].iloc[i-2]
                    
                    # 9.4 COM FILTRO DE ELITE
                    mme9_shakeout = (mme9_p2 > mme9_p3) and (mme9_p1 < mme9_p2) and (mme9_atual > mme9_p1)
                    setup_94_compra = mme9_shakeout and (mme9_atual > mm21_atual) and (close_atual > mme9_atual)

                    if tipo_conducao == "MM9 (Aritmética)":
                        ma_atual, ma_prev1, ma_prev2 = df_back['MM9'].iloc[i], df_back['MM9_Prev1'].iloc[i], df_back['MM9_Prev2'].iloc[i]
                    else:
                        ma_atual, ma_prev1, ma_prev2 = mme9_atual, mme9_p1, mme9_p2
                        
                    media_saida_virou_baixo = (ma_prev1 > ma_prev2) and (ma_atual < ma_prev1)
                    media_saida_subindo = ma_atual > ma_prev1

                    if em_pos:
                        if df_back['Low'].iloc[i] <= stop_loss:
                            d_sai = df_back[col_data].iloc[i]
                            duracao = (d_sai - d_ent).days
                            lucro_rs = capital_91a * ((stop_loss / preco_entrada) - 1)
                            trades.append({'Entrada': d_ent, 'Duração': duracao, 'Lucro (R$)': lucro_rs, 'Situação': 'Stop Acionado ❌'})
                            if lucro_rs > 0: vitorias += 1 
                            else: derrotas += 1
                            em_pos, saida_armada = False, False
                            continue
                        
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
                                if "9.1" in setup_escolhido_a or "9.4" in setup_escolhido_a:
                                    if media_caindo: setup_armado = False
                                elif "9.2" in setup_escolhido_a or "9.3" in setup_escolhido_a:
                                    if media_subindo:
                                        gatilho_entrada = df_back['High'].iloc[i]
                                        stop_loss = df_back['Fundo_5'].iloc[i] - 0.01 if tipo_stop == "Fundo Anterior (Últimos 5 candles)" else df_back['Low'].iloc[i] - 0.01
                                    else:
                                        setup_armado = False

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
                        elif "9.4" in setup_escolhido_a and setup_94_compra:
                            setup_armado = True
                            gatilho_entrada = df_back['High'].iloc[i]
                            stop_loss = df_back['Fundo_5'].iloc[i] - 0.01 if tipo_stop == "Fundo Anterior (Últimos 5 candles)" else df_back['Low'].iloc[i] - 0.01

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
                    mme9_p3_hj = df_full['MME9_Prev3'].iloc[-1]
                    
                    mm21_hj = df_full['MM21'].iloc[-1]
                    close_hj = df_full['Close'].iloc[-1]

                    subindo_hj = mme9_hj > mme9_p1_hj
                    virou_cima_hj = (mme9_p1_hj < mme9_p2_hj) and subindo_hj
                    f_abx_min_hj = df_full['Close'].iloc[-1] < df_full['Low'].iloc[-2]
                    f_abx_f1_hj = df_full['Close'].iloc[-1] < df_full['Close'].iloc[-2]
                    f_abx_f2_hj = df_full['Close'].iloc[-2] < df_full['Close'].iloc[-3]

                    # 9.4 HOJE COM FILTRO DE ELITE
                    mme9_shakeout_hj = (mme9_p2_hj > mme9_p3_hj) and (mme9_p1_hj < mme9_p2_hj) and (mme9_hj > mme9_p1_hj)
                    setup_94_compra_hj = mme9_shakeout_hj and (mme9_hj > mm21_hj) and (close_hj > mme9_hj)

                    armou_hoje = False
                    if "9.1" in setup_escolhido_a and virou_cima_hj: armou_hoje = True
                    elif "9.2" in setup_escolhido_a and subindo_hj and f_abx_min_hj: armou_hoje = True
                    elif "9.3" in setup_escolhido_a and subindo_hj and f_abx_f1_hj and f_abx_f2_hj: armou_hoje = True
                    elif "9.4" in setup_escolhido_a and setup_94_compra_hj: armou_hoje = True

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
    st.markdown("Faça o teste de estresse de um ativo específico validando as variações de Stop Inicial e Médias de Condução para os setups 9.1, 9.2, 9.3 e 9.4.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        lupa_ativo = st.text_input("Ativo (Ex: TSLA34):", value="TSLA34", key="i91_ativo")
        lupa_stop = st.selectbox("Posição do Stop Inicial:", ["Mínima do Candle", "Fundo Anterior (5 candles)"], key="i91_stop")
        lupa_periodo = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=2, key="i91_per")
    with col2:
        setup_escolhido_i = st.selectbox("Escolha a Estratégia:", ["Setup 9.1 (Virada de Média)", "Setup 9.2 (Pullback Curto)", "Setup 9.3 (Pullback Duplo)", "Setup 9.4 (Shakeout)"], key="i91_setup")
        lupa_cond = st.selectbox("Média de Condução (Trailing):", ["MME9 (Exponencial)", "MM9 (Aritmética)"], key="i91_cond")
        lupa_capital = st.number_input("Capital Base (R$):", value=10000.0, step=1000.0, key="i91_cap")
    with col3:
        lupa_tempo = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="i91_tmp")
        
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
                        
                        df_full['MME9'] = ta.ema(df_full['Close'], length=9)
                        df_full['MME9_Prev1'] = df_full['MME9'].shift(1)
                        df_full['MME9_Prev2'] = df_full['MME9'].shift(2)
                        df_full['MME9_Prev3'] = df_full['MME9'].shift(3)
                        
                        df_full['MM9'] = ta.sma(df_full['Close'], length=9)
                        df_full['MM9_Prev1'] = df_full['MM9'].shift(1)
                        df_full['MM9_Prev2'] = df_full['MM9'].shift(2)
                        
                        # ADIÇÃO DO FILTRO MM21
                        df_full['MM21'] = ta.sma(df_full['Close'], length=21)
                        
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

                        for i in range(3, len(df_back)):
                            mme9_atual = df_back['MME9'].iloc[i]
                            mme9_p1 = df_back['MME9_Prev1'].iloc[i]
                            mme9_p2 = df_back['MME9_Prev2'].iloc[i]
                            mme9_p3 = df_back['MME9_Prev3'].iloc[i]
                            
                            mm21_atual = df_back['MM21'].iloc[i]
                            close_atual = df_back['Close'].iloc[i]
                            
                            mme9_virou_cima = (mme9_p1 < mme9_p2) and (mme9_atual > mme9_p1)
                            mme9_caindo = mme9_atual < mme9_p1
                            mme9_subindo = mme9_atual > mme9_p1

                            fechou_abaixo_min_ant = df_back['Close'].iloc[i] < df_back['Low'].iloc[i-1]
                            fechou_abaixo_fech_ant1 = df_back['Close'].iloc[i] < df_back['Close'].iloc[i-1]
                            fechou_abaixo_fech_ant2 = df_back['Close'].iloc[i-1] < df_back['Close'].iloc[i-2]
                            
                            # 9.4 COM FILTRO DE ELITE
                            mme9_shakeout = (mme9_p2 > mme9_p3) and (mme9_p1 < mme9_p2) and (mme9_atual > mme9_p1)
                            setup_94_compra = mme9_shakeout and (mme9_atual > mm21_atual) and (close_atual > mme9_atual)

                            if lupa_cond == "MM9 (Aritmética)":
                                ma_atual, ma_prev1, ma_prev2 = df_back['MM9'].iloc[i], df_back['MM9_Prev1'].iloc[i], df_back['MM9_Prev2'].iloc[i]
                            else:
                                ma_atual, ma_prev1, ma_prev2 = mme9_atual, mme9_p1, mme9_p2
                                
                            media_saida_virou_baixo = (ma_prev1 > ma_prev2) and (ma_atual < ma_prev1)
                            media_saida_subindo = ma_atual > ma_prev1

                            if em_pos:
                                if df_back['Low'].iloc[i] <= stop_loss:
                                    d_sai = df_back[col_data].iloc[i]
                                    duracao = (d_sai - d_ent).days
                                    lucro_rs = lupa_capital * ((stop_loss / preco_entrada) - 1)
                                    trades.append({'Entrada': d_ent.strftime('%d/%m/%Y %H:%M') if lupa_tempo in ['15m', '60m'] else d_ent.strftime('%d/%m/%Y'), 'Saída': d_sai.strftime('%d/%m/%Y %H:%M') if lupa_tempo in ['15m', '60m'] else d_sai.strftime('%d/%m/%Y'), 'Duração': duracao, 'Lucro (R$)': lucro_rs, 'Situação': 'Stop Inicial ❌'})
                                    derrotas += 1
                                    em_pos, saida_armada = False, False
                                    continue
                                
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
                                        if "9.1" in setup_escolhido_i or "9.4" in setup_escolhido_i:
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
                                elif "9.4" in setup_escolhido_i and setup_94_compra:
                                    setup_armado = True
                                    gatilho_entrada = df_back['High'].iloc[i]
                                    stop_loss = df_back['Fundo_5'].iloc[i] - 0.01 if lupa_stop == "Fundo Anterior (5 candles)" else df_back['Low'].iloc[i] - 0.01

                        st.divider()
                        st.markdown(f"### 📊 Resultado: {ativo} ({setup_escolhido_i.split()[1]})")
                        
                        url_tv_individual = f"https://br.tradingview.com/chart/?symbol=BMFBOVESPA%3A{ativo}"
                        st.markdown(f"<a href='{url_tv_individual}' target='_blank' style='text-decoration: none; font-size: 14px; color: #4da6ff;'>🔗 Abrir no TradingView</a>", unsafe_allow_html=True)
                        
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

                        st.divider()
                        st.markdown(f"### 📈 Gráfico Interativo: {ativo}")
                        renderizar_grafico_tv(f"BMFBOVESPA:{ativo}")

                except Exception as e: st.error(f"Erro: {e}")

# ==========================================
# ABA 4: RAIO-X FUTUROS (DAY TRADE MULTI-SETUP)
# ==========================================
with aba_futuros:
    st.subheader("📈 Raio-X Mercado Futuro (WIN, WDO) - Família 9.x")
    st.markdown("Teste o poder do *Trend Following* no Day Trade operando nas duas pontas (**Compra e Venda**). Zeragem no Fim do Dia obrigatória.")
    
    cf1, cf2, cf3 = st.columns(3)
    with cf1:
        mapa_futuros = {"WINFUT (Mini Índice)": "WIN1!", "WDOFUT (Mini Dólar)": "WDO1!"}
        fut_selecionado = st.selectbox("Selecione o Ativo:", options=list(mapa_futuros.keys()), key="f91_ativo")
        fut_ativo = mapa_futuros[fut_selecionado] 
        fut_periodo = st.selectbox("Período:", options=['3mo', '6mo', '1y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=1, key="f91_per")
        fut_tempo = st.selectbox("Tempo Gráfico:", ['15m', '60m'], index=0, key="f91_tmp")
    with cf2:
        setup_escolhido_f = st.selectbox("Escolha a Estratégia:", ["Setup 9.1 (Virada de Média)", "Setup 9.2 (Pullback Curto)", "Setup 9.3 (Pullback Duplo)", "Setup 9.4 (Shakeout)"], key="f91_setup")
        direcao_fut = st.selectbox("Direção do Trade:", ["Ambas (Compra e Venda)", "Apenas Compra", "Apenas Venda"], key="f91_dir")
        tipo_stop_fut = st.selectbox("Posição do Stop Inicial:", ["Extremo do Candle (Máx/Mín)", "Extremo Anterior (5 candles)"], key="f91_stop")
        tipo_cond_fut = st.selectbox("Média de Condução:", ["MME9 (Exponencial)", "MM9 (Aritmética)"], key="f91_cond")
    with cf3:
        fut_contratos = st.number_input("Contratos Iniciais:", value=1, step=1, key="f91_cont")
        valor_mult_padrao = 0.20 if "WIN" in fut_selecionado else 10.00
        fut_multiplicador = st.number_input("Multiplicador (R$):", value=valor_mult_padrao, step=0.10, format="%.2f", key="f91_mult")
        fut_zerar_daytrade = st.checkbox("⏰ Zeragem Automática no Fim do Dia", value=True, key="f91_zerar")
        st.markdown("<div style='height: 2px;'></div>", unsafe_allow_html=True)
        
        btn_raiox_futuros = st.button(f"🚀 Gerar Raio-X Futuros {setup_escolhido_f.split()[1]}", type="primary", use_container_width=True, key="f91_btn")

    if btn_raiox_futuros:
        intervalo_tv = tradutor_intervalo.get(fut_tempo, Interval.in_15_minute)
        with st.spinner(f'Testando o motor do {setup_escolhido_f.split()[1]} ({direcao_fut}) em {fut_selecionado}...'):
            try:
                df_full = tv.get_hist(symbol=fut_ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=10000)
                if df_full is not None and len(df_full) > 50:
                    df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                    
                    df_full['MME9'] = ta.ema(df_full['Close'], length=9)
                    df_full['MME9_Prev1'] = df_full['MME9'].shift(1)
                    df_full['MME9_Prev2'] = df_full['MME9'].shift(2)
                    df_full['MME9_Prev3'] = df_full['MME9'].shift(3)
                    
                    df_full['MM9'] = ta.sma(df_full['Close'], length=9)
                    df_full['MM9_Prev1'] = df_full['MM9'].shift(1)
                    df_full['MM9_Prev2'] = df_full['MM9'].shift(2)
                    
                    # ADIÇÃO DO FILTRO MM21 PARA FUTUROS
                    df_full['MM21'] = ta.sma(df_full['Close'], length=21)
                    
                    df_full['Fundo_5'] = df_full['Low'].rolling(window=5).min()
                    df_full['Topo_5'] = df_full['High'].rolling(window=5).max()
                    df_full = df_full.dropna()

                    data_atual_dt = df_full.index[-1]
                    delta = {'3mo': 3, '6mo': 6, '1y': 12}.get(fut_periodo, 0)
                    data_corte = data_atual_dt - pd.DateOffset(months=delta) if delta > 0 else df_full.index[0]
                    df = df_full[df_full.index >= data_corte].copy()
                    
                    trades, vitorias, derrotas = [], 0, 0
                    
                    posicao = 0 
                    setup_compra, setup_venda, saida_armada = False, False, False
                    gatilho_entrada, gatilho_saida, stop_loss, preco_entrada = 0.0, 0.0, 0.0, 0.0
                    
                    df_back = df.reset_index()
                    col_data = df_back.columns[0]
                    offset = 5.0 if "WIN" in fut_ativo else 0.5

                    for i in range(3, len(df_back)):
                        d_at = df_back[col_data].iloc[i]
                        d_ant = df_back[col_data].iloc[i-1]
                        
                        mme9_atual = df_back['MME9'].iloc[i]
                        mme9_p1 = df_back['MME9_Prev1'].iloc[i]
                        mme9_p2 = df_back['MME9_Prev2'].iloc[i]
                        mme9_p3 = df_back['MME9_Prev3'].iloc[i]
                        
                        mm21_atual = df_back['MM21'].iloc[i]
                        close_atual = df_back['Close'].iloc[i]

                        mme9_virou_cima = (mme9_p1 < mme9_p2) and (mme9_atual > mme9_p1)
                        mme9_caindo = mme9_atual < mme9_p1
                        mme9_virou_baixo = (mme9_p1 > mme9_p2) and (mme9_atual < mme9_p1)
                        mme9_subindo = mme9_atual > mme9_p1
                        
                        # 9.4 COM FILTRO DE ELITE PARA COMPRA E VENDA
                        mme9_shakeout_compra = (mme9_p2 > mme9_p3) and (mme9_p1 < mme9_p2) and (mme9_atual > mme9_p1)
                        setup_94_compra = mme9_shakeout_compra and (mme9_atual > mm21_atual) and (close_atual > mme9_atual)
                        
                        mme9_shakeout_venda = (mme9_p2 < mme9_p3) and (mme9_p1 > mme9_p2) and (mme9_atual < mme9_p1)
                        setup_94_venda = mme9_shakeout_venda and (mme9_atual < mm21_atual) and (close_atual < mme9_atual)

                        fechou_abaixo_min_ant = df_back['Close'].iloc[i] < df_back['Low'].iloc[i-1]
                        fechou_abaixo_fech_ant1 = df_back['Close'].iloc[i] < df_back['Close'].iloc[i-1]
                        fechou_abaixo_fech_ant2 = df_back['Close'].iloc[i-1] < df_back['Close'].iloc[i-2]

                        fechou_acima_max_ant = df_back['Close'].iloc[i] > df_back['High'].iloc[i-1]
                        fechou_acima_fech_ant1 = df_back['Close'].iloc[i] > df_back['Close'].iloc[i-1]
                        fechou_acima_fech_ant2 = df_back['Close'].iloc[i-1] > df_back['Close'].iloc[i-2]

                        if tipo_cond_fut == "MM9 (Aritmética)":
                            ma_atual, ma_prev1, ma_prev2 = df_back['MM9'].iloc[i], df_back['MM9_Prev1'].iloc[i], df_back['MM9_Prev2'].iloc[i]
                        else:
                            ma_atual, ma_prev1, ma_prev2 = mme9_atual, mme9_p1, mme9_p2
                            
                        media_saida_virou_baixo = (ma_prev1 > ma_prev2) and (ma_atual < ma_prev1)
                        media_saida_virou_cima = (ma_prev1 < ma_prev2) and (ma_atual > ma_prev1)
                        media_saida_subindo = ma_atual > ma_prev1
                        media_saida_caindo = ma_atual < ma_prev1

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
                            if luc > 0: vitorias += 1
                            else: derrotas += 1
                                
                            posicao, setup_compra, setup_venda, saida_armada = 0, False, False, False
                            continue

                        if posicao == 1: 
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
                                    if luc > 0: vitorias += 1 
                                    else: derrotas += 1
                                    
                                    posicao, saida_armada = 0, False
                                    continue
                                elif media_saida_subindo:
                                    saida_armada = False 

                            if media_saida_virou_baixo and not saida_armada:
                                saida_armada = True
                                gatilho_saida = df_back['Low'].iloc[i] - offset

                        elif posicao == -1: 
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
                                    if luc > 0: vitorias += 1 
                                    else: derrotas += 1
                                    
                                    posicao, saida_armada = 0, False
                                    continue
                                elif media_saida_caindo:
                                    saida_armada = False

                            if media_saida_virou_cima and not saida_armada:
                                saida_armada = True
                                gatilho_saida = df_back['High'].iloc[i] + offset

                        else: 
                            if setup_compra:
                                if df_back['High'].iloc[i] > gatilho_entrada:
                                    posicao = 1
                                    setup_compra, setup_venda = False, False
                                    d_ent = df_back[col_data].iloc[i]
                                    preco_entrada = max(gatilho_entrada + offset, df_back['Open'].iloc[i])
                                else:
                                    if "9.1" in setup_escolhido_f or "9.4" in setup_escolhido_f:
                                        if mme9_caindo: setup_compra = False
                                    elif "9.2" in setup_escolhido_f or "9.3" in setup_escolhido_f:
                                        if mme9_subindo:
                                            gatilho_entrada = df_back['High'].iloc[i]
                                            stop_loss = df_back['Fundo_5'].iloc[i] - offset if "Extremo Anterior" in tipo_stop_fut else df_back['Low'].iloc[i] - offset
                                        else:
                                            setup_compra = False

                            if setup_venda and posicao == 0:
                                if df_back['Low'].iloc[i] < gatilho_entrada:
                                    posicao = -1
                                    setup_compra, setup_venda = False, False
                                    d_ent = df_back[col_data].iloc[i]
                                    preco_entrada = min(gatilho_entrada - offset, df_back['Open'].iloc[i])
                                else:
                                    if "9.1" in setup_escolhido_f or "9.4" in setup_escolhido_f:
                                        if mme9_subindo: setup_venda = False
                                    elif "9.2" in setup_escolhido_f or "9.3" in setup_escolhido_f:
                                        if mme9_caindo:
                                            gatilho_entrada = df_back['Low'].iloc[i]
                                            stop_loss = df_back['Topo_5'].iloc[i] + offset if "Extremo Anterior" in tipo_stop_fut else df_back['High'].iloc[i] + offset
                                        else:
                                            setup_venda = False

                            if posicao == 0:
                                armar_compra = False
                                if "9.1" in setup_escolhido_f and mme9_virou_cima: armar_compra = True
                                elif "9.2" in setup_escolhido_f and mme9_subindo and fechou_abaixo_min_ant: armar_compra = True
                                elif "9.3" in setup_escolhido_f and mme9_subindo and fechou_abaixo_fech_ant1 and fechou_abaixo_fech_ant2: armar_compra = True
                                elif "9.4" in setup_escolhido_f and setup_94_compra: armar_compra = True
                                
                                if armar_compra and direcao_fut != "Apenas Venda":
                                    setup_compra = True
                                    setup_venda = False
                                    gatilho_entrada = df_back['High'].iloc[i]
                                    stop_loss = df_back['Fundo_5'].iloc[i] - offset if "Extremo Anterior" in tipo_stop_fut else df_back['Low'].iloc[i] - offset
                                    
                                armar_venda = False
                                if "9.1" in setup_escolhido_f and mme9_virou_baixo: armar_venda = True
                                elif "9.2" in setup_escolhido_f and mme9_caindo and fechou_acima_max_ant: armar_venda = True
                                elif "9.3" in setup_escolhido_f and mme9_caindo and fechou_acima_fech_ant1 and fechou_acima_fech_ant2: armar_venda = True
                                elif "9.4" in setup_escolhido_f and setup_94_venda: armar_venda = True
                                
                                if armar_venda and direcao_fut != "Apenas Compra":
                                    setup_venda = True
                                    setup_compra = False
                                    gatilho_entrada = df_back['Low'].iloc[i]
                                    stop_loss = df_back['Topo_5'].iloc[i] + offset if "Extremo Anterior" in tipo_stop_fut else df_back['High'].iloc[i] + offset

                    if trades:
                        df_t = pd.DataFrame(trades)
                        st.divider()
                        st.markdown(f"### 📊 Resultado: {fut_selecionado} ({setup_escolhido_f.split()[1]} - {direcao_fut})")
                        st.caption(f"📅 Período: {df.index[0].strftime('%d/%m/%Y')} até {df.index[-1].strftime('%d/%m/%Y')}")
                        
                        url_fut_individual = f"https://br.tradingview.com/chart/?symbol=BMFBOVESPA%3A{fut_ativo.replace('!', '%21')}"
                        st.markdown(f"<a href='{url_fut_individual}' target='_blank' style='text-decoration: none; font-size: 14px; color: #4da6ff;'>🔗 Abrir no TradingView</a>", unsafe_allow_html=True)
                        
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
                                st.success(f"🎯 **Expectativa Real Positiva:** O Payoff é o rei da família 9.x! Você arrisca 1 para ganhar {p_off:.2f}. Margem de gordura: {margem:.1f}% acima da taxa crítica.")
                            else:
                                st.info(f"⚖️ **Alerta de Risco:** Saldo positivo, mas payoff de {p_off:.2f} é perigoso para seguidores de tendência. A alta taxa de acerto é que está sustentando o sistema.")
                        else:
                            st.error(f"🚨 **Expectativa Negativa:** Saldo de R$ {l_total:,.2f}. O 'Efeito Serrote' ou falsos rompimentos machucaram o robô. Se o Payoff não cobrir a taxa de erro natural, a conta não fecha.")

                        st.dataframe(df_t, use_container_width=True, hide_index=True)
                        
                        st.divider()
                        st.markdown(f"### 📈 Gráfico Interativo: {fut_selecionado}")
                        renderizar_grafico_tv(f"BMFBOVESPA:{fut_ativo.replace('!', '')}")
                        
                    else:
                        st.warning("Nenhuma operação concluída usando essa configuração neste período.")
            except Exception as e: st.error(f"Erro: {e}")
