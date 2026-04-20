import streamlit as st
from tvDatafeed import TvDatafeed, Interval
import pandas as pd
import numpy as np
import pandas_ta as ta
import time
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. SEGURANÇA E CONEXÃO
# ==========================================
# Autenticação via Email para acesso à plataforma de alunos
if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login com seu e-mail na página inicial (Home) para liberar o motor Quant.")
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
    """
    Calcula a POC (Point of Control) rolante.
    Para cada dia, olha o volume passado e encontra o preço de maior interesse institucional.
    """
    poc_list = [np.nan] * len(df)
    
    # Precisamos da coluna de Volume para calcular
    if 'Volume' not in df.columns:
        return pd.Series(poc_list, index=df.index)

    for i in range(periodo_lookback, len(df)):
        janela = df.iloc[i-periodo_lookback:i]
        min_p = janela['Low'].min()
        max_p = janela['High'].max()
        
        if max_p == min_p:
            poc_list[i] = df['Close'].iloc[i]
            continue
            
        # Cria as faixas de preço (bins)
        bin_edges = np.linspace(min_p, max_p, num_bins)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        vol_profile = np.zeros(num_bins - 1)
        
        # Distribui o volume do dia para o bin correspondente
        for j in range(len(janela)):
            idx = np.digitize(janela['Close'].iloc[j], bin_edges) - 1
            idx = min(max(idx, 0), num_bins - 2)
            vol_profile[idx] += janela['Volume'].iloc[j]
            
        # O bin com o maior volume acumulado é a POC
        poc_list[i] = bin_centers[np.argmax(vol_profile)]
        
    return pd.Series(poc_list, index=df.index)

# ==========================================
# 3. INTERFACE E ABAS
# ==========================================
col_titulo, col_botao = st.columns([4, 1])
with col_titulo:
    st.title("📊 Fluxo Institucional (VWAP & Volume)")
with col_botao:
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.link_button("📖 Ler Manual Quant", "https://seusite.com/manual_institucional", use_container_width=True)

st.markdown("Opera na mesma direção dos grandes *players*. Aguarda o preço se estabelecer acima da POC (Suporte Estrutural de Volume) e entra em pullbacks cravados na VWAP (Preço Médio Institucional). O risco/retorno é gerido por variação percentual.")

c1, c2, c3, c4 = st.columns(4)
with c1:
    rx_ativo = st.text_input("Ativo Base (Ex: PETR4):", value="PETR4", key="inst_ativo").upper().replace('.SA', '')
    rx_periodo = st.selectbox("Período do Backtest:", options=['6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=1)
with c2:
    rx_tempo = st.selectbox("Tempo Gráfico:", ['60m', '1d', '1wk'], index=1, format_func=lambda x: {'60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x])
    rx_capital = st.number_input("Capital Operado (R$):", value=10000.0, step=1000.0)
with c3:
    st.markdown("**Alvos Percentuais**")
    alvo_pct = st.number_input("Alvo de Lucro (%):", value=5.0, step=0.5, help="Fechamento da operação no lucro.") / 100
with c4:
    st.markdown("**Limites de Perda**")
    stop_pct = st.number_input("Stop Loss (%):", value=2.0, step=0.5, help="Proteção do capital.") / 100

btn_raiox = st.button("🔍 Rodar Motor Institucional", type="primary", use_container_width=True)

if btn_raiox:
    if not rx_ativo:
        st.error("Digite o código de um ativo para analisar o fluxo.")
    else:
        intervalo_tv = tradutor_intervalo.get(rx_tempo, Interval.in_daily)
        with st.spinner(f'Decodificando livro de ofertas e volume de {rx_ativo}...'):
            try:
                df_full = tv.get_hist(symbol=rx_ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=5000)
                if df_full is None or len(df_full) < 100:
                    st.error("Dados de volume insuficientes para calcular a POC.")
                else:
                    df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
                    
                    # --- COMPUTAÇÃO QUANT ---
                    # 1. POC (Point of Control de 30 períodos)
                    df_full['POC'] = calcular_rolling_poc(df_full, periodo_lookback=30)
                    
                    # 2. VWAP Móvel / Institucional (Preço Médio Ponderado por Volume de 20 períodos)
                    df_full['VWAP_Inst'] = ta.vwma(df_full['Close'], df_full['Volume'], length=20)
                    
                    df_full = df_full.dropna()

                    # Corte de Tempo
                    data_atual = df_full.index[-1]
                    if rx_periodo == '6mo': data_corte = data_atual - pd.DateOffset(months=6)
                    elif rx_periodo == '1y': data_corte = data_atual - pd.DateOffset(years=1)
                    elif rx_periodo == '2y': data_corte = data_atual - pd.DateOffset(years=2)
                    elif rx_periodo == '5y': data_corte = data_atual - pd.DateOffset(years=5)
                    else: data_corte = df_full.index[0]

                    df = df_full[df_full.index >= data_corte].copy()
                    df_back = df.reset_index()
                    col_data = df_back.columns[0]

                    trades = []
                    em_pos = False
                    preco_entrada = 0.0
                    stop_loss = 0.0
                    alvo = 0.0
                    d_ent = None
                    vitorias, derrotas = 0, 0

                    # --- BACKTEST DO FLUXO ---
                    for i in range(1, len(df_back)):
                        atual = df_back.iloc[i]
                        ontem = df_back.iloc[i-1]

                        # 1. GESTÃO PERCENTUAL
                        if em_pos:
                            # Verifica Saídas
                            if atual['Low'] <= stop_loss:
                                d_sai = atual[col_data]
                                lucro = rx_capital * ((stop_loss / preco_entrada) - 1)
                                trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': d_sai.strftime('%d/%m/%Y'), 'Lucro (R$)': lucro, 'Resultado': 'Stop Acionado ❌'})
                                derrotas += 1; em_pos = False
                            elif atual['High'] >= alvo:
                                d_sai = atual[col_data]
                                lucro = rx_capital * ((alvo / preco_entrada) - 1)
                                trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': d_sai.strftime('%d/%m/%Y'), 'Lucro (R$)': lucro, 'Resultado': 'Alvo Atingido 🎯'})
                                vitorias += 1; em_pos = False
                            continue

                        # 2. GATILHO INSTITUCIONAL (EMBOSCADA)
                        # Condição Macro: O Ativo precisa estar sendo defendido ACIMA do maior nó de volume (POC)
                        macro_bullish = ontem['Close'] > ontem['POC']
                        
                        # Condição Micro: O preço afunda durante o dia (Low) tocando na VWAP, mas o fechamento (Close) defende e termina acima da VWAP.
                        toque_vwap = atual['Low'] <= atual['VWAP_Inst']
                        defesa_vwap = atual['Close'] >= atual['VWAP_Inst']
                        
                        if macro_bullish and toque_vwap and defesa_vwap and not em_pos:
                            em_pos = True
                            # Compra no fechamento do dia que validou a defesa
                            preco_entrada = atual['Close']
                            d_ent = atual[col_data]
                            
                            # Alvos Matemáticos Baseados na Variação Percentual
                            alvo = preco_entrada * (1 + alvo_pct)
                            stop_loss = preco_entrada * (1 - stop_pct)

                    # --- RESULTADOS ---
                    st.divider()
                    st.markdown(f"### 🛡️ Defesa Institucional: {rx_ativo}")
                    
                    if len(trades) > 0:
                        df_t = pd.DataFrame(trades)
                        
                        l_total = df_t['Lucro (R$)'].sum()
                        t_acerto = (vitorias / len(df_t)) * 100
                        
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("Lucro Extraído", f"R$ {l_total:,.2f}", delta=f"{l_total:,.2f}")
                        m2.metric("Disparos do Robô", len(df_t))
                        m3.metric("Taxa de Precisão", f"{t_acerto:.1f}%")
                        m4.metric("Relação Risco/Retorno", f"1 para {alvo_pct/stop_pct:.1f}")

                        if l_total > 0:
                            st.success("🟢 **Dominância Institucional:** O ativo possui fluxo contínuo e respeita os defensores da VWAP. Sistema validado com sucesso.")
                        else:
                            st.error("🔴 **Falta de Lote:** Ativo errático. O fluxo comprador na VWAP não teve força para deslocar o preço até o alvo percentual na maioria das vezes.")

                        st.dataframe(df_t, use_container_width=True, hide_index=True)
                    else:
                        st.warning("O algoritmo não detectou nenhuma emboscada perfeita de fluxo no período especificado.")
            except Exception as e: st.error(f"Ocorreu um erro no cálculo do volume: {e}")
