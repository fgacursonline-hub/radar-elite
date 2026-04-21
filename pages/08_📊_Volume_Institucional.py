import streamlit as st
from tvDatafeed import TvDatafeed, Interval
import pandas as pd
import numpy as np
import pandas_ta as ta
import time
import warnings
from datetime import datetime

warnings.filterwarnings('ignore')

# ==========================================
# 1. SEGURANÇA E CONEXÃO
# ==========================================
if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, inicie sessão na página inicial (Home) para libertar o motor Quant.")
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
    'LILY34.SA', 'AMZO34.SA', 'AURA33.SA', 'GOGL34.SA', 'MSFT34.SA', 'MELI34.SA',
    'AAPL34.SA', 'XPBR31.SA'
]

ibrx_selecao = [
    'PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'BBDC4.SA', 'BBAS3.SA', 'B3SA3.SA', 'ABEV3.SA',
    'WEGE3.SA', 'SUZB3.SA', 'RENT3.SA', 'RADL3.SA', 'EQTL3.SA', 'PRIO3.SA'
]

# ==========================================
# 2. MOTOR MATEMÁTICO: VOLUME PROFILE
# ==========================================
def calcular_rolling_poc(df, periodo_lookback=30, num_bins=24):
    poc_list = [np.nan] * len(df)
    if 'Volume' not in df.columns:
        return pd.Series(poc_list, index=df.index)

    for i in range(periodo_lookback, len(df)):
        janela = df.iloc[i-periodo_lookback:i]
        min_p = janela['Low'].min()
        max_p = janela['High'].max()
        
        if max_p == min_p:
            poc_list[i] = df['Close'].iloc[i]
            continue
            
        bin_edges = np.linspace(min_p, max_p, num_bins)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        vol_profile = np.zeros(num_bins - 1)
        
        for j in range(len(janela)):
            idx = np.digitize(janela['Close'].iloc[j], bin_edges) - 1
            idx = min(max(idx, 0), num_bins - 2)
            vol_profile[idx] += janela['Volume'].iloc[j]
            
        poc_list[i] = bin_centers[np.argmax(vol_profile)]
        
    return pd.Series(poc_list, index=df.index)

# Função para colorir o DataFrame no Streamlit
def colorir_lucro(row):
    try:
        val = float(row['Resultado Atual'].replace('%', '').replace('+', ''))
        cor = 'lightgreen' if val > 0 else 'lightcoral' if val < 0 else 'white'
        return [f'color: {cor}'] * len(row)
    except:
        return [''] * len(row)

# ==========================================
# 3. INTERFACE E ABAS
# ==========================================
col_titulo, col_botao = st.columns([4, 1])
with col_titulo:
    st.title("📊 Fluxo Institucional (VWAP & Volume)")
with col_botao:
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.link_button("📖 Ler Manual Quant", "https://seusite.com/manual_institucional", use_container_width=True)

aba_radar, aba_individual = st.tabs(["📡 Radar Institucional (Ao Vivo)", "🔬 Raio-X Individual"])

# ==========================================
# ABA 1: RADAR (MÚLTIPLOS ATIVOS)
# ==========================================
with aba_radar:
    st.subheader("Radar de Fluxo Institucional")
    st.markdown("Varre a lista de ativos para encontrar quem está tocando a VWAP sendo defendido acima da POC hoje, e mostra as operações que já estão em andamento aguardando o alvo matemático.")
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        lista_sel = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"], key="rad_lst")
        tempo_grafico = st.selectbox("Tempo Gráfico:", ['1d', '60m'], index=0, format_func=lambda x: {'60m': '60 min', '1d': 'Diário'}[x], key="rad_tmp")
    with c2:
        st.markdown("**Alvos Percentuais**")
        alvo_pct_rad = st.number_input("Alvo de Lucro (%):", value=5.0, step=0.5, key="rad_alvo") / 100
    with c3:
        st.markdown("**Limites de Perda**")
        usar_stop_rad = st.checkbox("Utilizar Stop Loss", value=True, key="rad_chk")
        stop_pct_rad = st.number_input("Stop Loss (%):", value=2.0, step=0.5, disabled=not usar_stop_rad, key="rad_stop") / 100
    with c4:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        btn_iniciar_radar = st.button("🚀 Iniciar Varredura de Fluxo", type="primary", use_container_width=True)

    if btn_iniciar_radar:
        ativos_analise = bdrs_elite if lista_sel == "BDRs Elite" else ibrx_selecao if lista_sel == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        intervalo_tv = tradutor_intervalo.get(tempo_grafico, Interval.in_daily)
        
        ls_armados = []
        ls_abertos = []
        
        p_bar = st.progress(0)
        s_text = st.empty()

        for idx, ativo_raw in enumerate(ativos_analise):
            ativo = ativo_raw.replace('.SA', '')
            s_text.text(f"🔍 Lendo fluxo de {ativo} ({idx+1}/{len(ativos_analise)})")
            p_bar.progress((idx + 1) / len(ativos_analise))

            try:
                # Puxa 1 ano de dados para o Radar (suficiente para POC e estar posicionado)
                df_full = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=300)
                if df_full is None or len(df_full) < 50: continue

                df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
                
                df_full['POC'] = calcular_rolling_poc(df_full, periodo_lookback=30)
                df_full['VWAP_Inst'] = ta.vwma(df_full['Close'], df_full['Volume'], length=20)
                df_full = df_full.dropna()

                df_back = df_full.reset_index()
                col_data = df_back.columns[0]

                em_pos = False
                preco_entrada = 0.0
                stop_loss = 0.0
                alvo = 0.0
                min_price_in_trade = 0.0
                d_ent = None

                # Roda o histórico para saber onde estamos HOJE
                for i in range(1, len(df_back)):
                    atual = df_back.iloc[i]
                    ontem = df_back.iloc[i-1]

                    if em_pos:
                        # Regista a pior cotação alcançada enquanto a operação está aberta
                        min_price_in_trade = min(min_price_in_trade, atual['Low'])
                        
                        if usar_stop_rad and atual['Low'] <= stop_loss:
                            em_pos = False
                        elif atual['High'] >= alvo:
                            em_pos = False
                        continue # Se fechou a posição, continua o loop. Se não fechou, também continua.

                    # Lógica de Entrada
                    macro_bullish = ontem['Close'] > ontem['POC']
                    toque_vwap = atual['Low'] <= atual['VWAP_Inst']
                    defesa_vwap = atual['Close'] >= atual['VWAP_Inst']
                    
                    if macro_bullish and toque_vwap and defesa_vwap and not em_pos:
                        em_pos = True
                        preco_entrada = atual['Close']
                        min_price_in_trade = atual['Close'] # Reinicia o marcador de queda no ponto de entrada
                        d_ent = atual[col_data]
                        alvo = preco_entrada * (1 + alvo_pct_rad)
                        stop_loss = preco_entrada * (1 - stop_pct_rad)

                # FORA DO LOOP: Avalia o estado no momento atual (último candle)
                if em_pos:
                    # Operação está em andamento!
                    cotacao_atual = df_back['Close'].iloc[-1]
                    res_pct = (cotacao_atual / preco_entrada) - 1
                    dias_aberto = (df_back[col_data].iloc[-1] - d_ent).days
                    queda_max = (min_price_in_trade / preco_entrada) - 1
                    
                    ls_abertos.append({
                        'Ativo': ativo,
                        'Entrada': d_ent.strftime('%d/%m/%Y'),
                        'Dias': dias_aberto,
                        'PM (Entrada)': f"R$ {preco_entrada:.2f}",
                        'Cotação Atual': f"R$ {cotacao_atual:.2f}",
                        'Queda Máx': f"{queda_max*100:.2f}%",
                        'Alvo Programado': f"R$ {alvo:.2f}",
                        'Resultado Atual': f"+{res_pct*100:.2f}%" if res_pct > 0 else f"{res_pct*100:.2f}%"
                    })
                else:
                    # Não está em operação. O setup armou HOJE?
                    atual = df_back.iloc[-1]
                    ontem = df_back.iloc[-2]
                    
                    macro_bullish = ontem['Close'] > ontem['POC']
                    toque_vwap = atual['Low'] <= atual['VWAP_Inst']
                    defesa_vwap = atual['Close'] >= atual['VWAP_Inst']
                    
                    if macro_bullish and toque_vwap and defesa_vwap:
                        ls_armados.append({
                            'Ativo': ativo,
                            'Sinal': 'Defesa VWAP + POC',
                            'Gatilho Compra': f"R$ {atual['Close']:.2f} (A Mercado)",
                            'Alvo': f"R$ {atual['Close'] * (1 + alvo_pct_rad):.2f}",
                            'Stop': f"R$ {atual['Close'] * (1 - stop_pct_rad):.2f}" if usar_stop_rad else "Sem Stop"
                        })

            except Exception as e: pass
            time.sleep(0.01)

        s_text.empty()
        p_bar.empty()

        # --- EXIBIÇÃO ---
        st.subheader(f"🚀 Oportunidades Hoje (Fluxo Institucional | Alvo {alvo_pct_rad*100:.1f}%)")
        if ls_armados:
            st.dataframe(pd.DataFrame(ls_armados), use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum ativo deu sinal de entrada na última barra baseando-se no fluxo.")

        st.subheader("⏳ Operações em Andamento (Aguardando Alvo)")
        if ls_abertos:
            df_abertos = pd.DataFrame(ls_abertos).sort_values(by='Dias', ascending=False)
            st.dataframe(df_abertos.style.apply(colorir_lucro, axis=1), use_container_width=True, hide_index=True)
        else:
            st.info("A carteira de Fluxo Institucional está vazia no momento.")

# ==========================================
# ABA 2: RAIO-X INDIVIDUAL (BACKTEST)
# ==========================================
with aba_individual:
    st.subheader("🔬 Raio-X Individual: Laboratório de Fluxo")
    
    cr1, cr2, cr3, cr4 = st.columns(4)
    with cr1:
        rx_ativo = st.text_input("Ativo Base (Ex: PETR4):", value="PETR4", key="rx_inst_ativo").upper().replace('.SA', '')
        rx_periodo = st.selectbox("Período de Estudo:", options=['6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=1, key="rx_inst_per")
    with cr2:
        rx_tempo = st.selectbox("Tempo Gráfico:", ['60m', '1d', '1wk'], index=1, format_func=lambda x: {'60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="rx_inst_tmp")
        rx_capital = st.number_input("Capital Operado (R$):", value=10000.0, step=1000.0, key="rx_inst_cap")
    with cr3:
        st.markdown("**Alvos Percentuais**")
        alvo_pct = st.number_input("Alvo de Lucro (%):", value=5.0, step=0.5, key="rx_inst_alvo") / 100
    with cr4:
        st.markdown("**Limites de Perda**")
        usar_stop = st.checkbox("Utilizar Stop Loss", value=True, key="rx_inst_chk")
        stop_pct = st.number_input("Stop Loss (%):", value=2.0, step=0.5, disabled=not usar_stop, key="rx_inst_stop") / 100

    btn_raiox = st.button("🔍 Rodar Análise Completa", type="primary", use_container_width=True, key="rx_inst_btn")

    if btn_raiox:
        if not rx_ativo: st.error("Digite o código de um ativo.")
        else:
            intervalo_tv = tradutor_intervalo.get(rx_tempo, Interval.in_daily)
            with st.spinner(f'A descodificar o livro de ofertas de {rx_ativo}...'):
                try:
                    df_full = tv.get_hist(symbol=rx_ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=5000)
                    if df_full is None or len(df_full) < 100: st.error("Dados de volume insuficientes.")
                    else:
                        df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
                        
                        df_full['POC'] = calcular_rolling_poc(df_full, periodo_lookback=30)
                        df_full['VWAP_Inst'] = ta.vwma(df_full['Close'], df_full['Volume'], length=20)
                        df_full = df_full.dropna()

                        data_atual = df_full.index[-1]
                        if rx_periodo == '6mo': data_corte = data_atual - pd.DateOffset(months=6)
                        elif rx_periodo == '1y': data_corte = data_atual - pd.DateOffset(years=1)
                        elif rx_periodo == '2y': data_corte = data_atual - pd.DateOffset(years=2)
                        elif rx_periodo == '5y': data_corte = data_atual - pd.DateOffset(years=5)
                        else: data_corte = df_full.index[0]

                        df = df_full[df_full.index >= data_corte].copy()
                        df_back = df.reset_index()
                        col_data = df_back.columns[0]

                        trades, em_pos = [], False
                        preco_entrada, stop_loss, alvo = 0.0, 0.0, 0.0
                        min_price_in_trade = 0.0
                        d_ent, vitorias, derrotas = None, 0, 0

                        for i in range(1, len(df_back)):
                            atual = df_back.iloc[i]
                            ontem = df_back.iloc[i-1]

                            if em_pos:
                                # Regista o pior preço alcançado durante o trade
                                min_price_in_trade = min(min_price_in_trade, atual['Low'])
                                
                                if usar_stop and atual['Low'] <= stop_loss:
                                    d_sai = atual[col_data]
                                    lucro = rx_capital * ((stop_loss / preco_entrada) - 1)
                                    dias_op = (d_sai - d_ent).days
                                    queda_max = (min_price_in_trade / preco_entrada) - 1
                                    trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': d_sai.strftime('%d/%m/%Y'), 'Duração': dias_op, 'Lucro (R$)': lucro, 'Queda Máx': queda_max, 'Situação': 'Stop ❌'})
                                    derrotas += 1; em_pos = False
                                elif atual['High'] >= alvo:
                                    d_sai = atual[col_data]
                                    lucro = rx_capital * ((alvo / preco_entrada) - 1)
                                    dias_op = (d_sai - d_ent).days
                                    queda_max = (min_price_in_trade / preco_entrada) - 1
                                    trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': d_sai.strftime('%d/%m/%Y'), 'Duração': dias_op, 'Lucro (R$)': lucro, 'Queda Máx': queda_max, 'Situação': 'Gain ✅'})
                                    vitorias += 1; em_pos = False
                                continue

                            macro_bullish = ontem['Close'] > ontem['POC']
                            toque_vwap = atual['Low'] <= atual['VWAP_Inst']
                            defesa_vwap = atual['Close'] >= atual['VWAP_Inst']
                            
                            if macro_bullish and toque_vwap and defesa_vwap and not em_pos:
                                em_pos = True
                                preco_entrada = atual['Close']
                                min_price_in_trade = atual['Close'] # Inicia a medição de queda
                                d_ent = atual[col_data]
                                alvo = preco_entrada * (1 + alvo_pct)
                                stop_loss = preco_entrada * (1 - stop_pct)

                        st.divider()
                        
                        # --- BARRA DE ESTADO (NOVA) ---
                        if em_pos:
                            st.warning(f"⏳ **{rx_ativo}: Em Operação (Aguardando Alvo)**")
                        else:
                            st.success(f"✅ **{rx_ativo}: Aguardando Novo Sinal de Entrada**")
                            
                        st.markdown(f"### 📊 Resultado Consolidado: {rx_ativo}")
                        
                        if len(trades) > 0:
                            df_t = pd.DataFrame(trades)
                            
                            l_total = df_t['Lucro (R$)'].sum()
                            media_dias = df_t['Duração'].mean()
                            pior_queda = df_t['Queda Máx'].min() # Pega o valor mais negativo
                            
                            # Formatação para exibição na tabela
                            df_t['Queda Máx'] = df_t['Queda Máx'].apply(lambda x: f"{x*100:.2f}%")
                            
                            # --- MÉTRICAS ALINHADAS COM A IMAGEM ---
                            m1, m2, m3, m4 = st.columns(4)
                            m1.metric("Lucro Total", f"R$ {l_total:,.2f}")
                            m2.metric("Duração Média", f"{media_dias:.1f} dias")
                            m3.metric("Operações Fechadas", len(df_t))
                            m4.metric("Pior Queda", f"{pior_queda*100:.2f}%")

                            st.dataframe(df_t, use_container_width=True, hide_index=True)
                        else:
                            st.info("O algoritmo não detetou entradas finalizadas no período especificado.")
                except Exception as e: st.error(f"Erro: {e}")
