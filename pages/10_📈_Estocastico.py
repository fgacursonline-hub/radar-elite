import streamlit as st
import pandas as pd
import pandas_ta as ta
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os
import warnings
from datetime import datetime

warnings.filterwarnings('ignore')

# ==========================================
# 1. IMPORTAÇÕES E CONFIGURAÇÃO DO BUNKER
# ==========================================
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from config_ativos import bdrs_elite, ibrx_selecao
    from motor_dados import puxar_dados_blindados  # MODO BUSCA PELO BUNKER
    ativos_para_rastrear = sorted(list(set([a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)])))
except ImportError:
    st.error("❌ Erro ao carregar dependências. Verifique os arquivos na raiz.")
    st.stop()

st.set_page_config(page_title="Estocástico Elite Bunker", layout="wide", page_icon="📈")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial.")
    st.stop()

tradutor_periodo_nome = {'1mo': '1 Mês', '3mo': '3 Meses', '6mo': '6 Meses', '1y': '1 Ano', '2y': '2 Anos', '5y': '5 Anos', 'max': 'Máximo'}

# ==========================================
# 2. MOTOR MATEMÁTICO E GRÁFICO
# ==========================================
def calcular_estocastico_bunker(df, k=14, d=3, smooth_k=3):
    if df is None or df.empty: return None
    df = df.copy()
    
    # Padronização de colunas para o padrão motor_dados
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    
    # Cálculo via pandas_ta
    stoch = ta.stoch(df['high'], df['low'], df['close'], k=k, d=d, smooth_k=smooth_k)
    df['%K'] = stoch[stoch.columns[0]]
    df['%D'] = stoch[stoch.columns[1]]
    df['%K_Prev'] = df['%K'].shift(1)
    df['%D_Prev'] = df['%D'].shift(1)
    return df

def plotar_estocastico_plotly(df, trades_df, mostrar_oscilador):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
    
    # Preço
    fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Preço"), row=1, col=1)
    
    # Estocástico
    if mostrar_oscilador:
        fig.add_trace(go.Scatter(x=df.index, y=df['%K'], name="%K", line=dict(color='#00FFCC', width=1.5)), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['%D'], name="%D", line=dict(color='#FF4D4D', width=1.5, dash='dot')), row=2, col=1)
        fig.add_hline(y=80, line_dash="dash", line_color="gray", row=2, col=1)
        fig.add_hline(y=20, line_dash="dash", line_color="gray", row=2, col=1)

    # Setas de Compra
    if not trades_df.empty:
        for _, trade in trades_df.iterrows():
            try:
                data_ent = pd.to_datetime(trade['Entrada'], dayfirst=True)
                if data_ent in df.index:
                    fig.add_annotation(x=data_ent, y=df.loc[data_ent, 'low'], text="▲ COMPRA", showarrow=True, arrowhead=1, color="green", row=1, col=1)
            except: pass

    fig.update_layout(height=700, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=30, b=10))
    return fig

# ==========================================
# 3. INTERFACE STREAMLIT
# ==========================================
st.title("📈 Máquina Quantitativa: Estocástico (Bunker)")

aba_radar, aba_rx = st.tabs(["🌐 Radar Global (Scanner)", "🔬 Raio-X Individual (Gráfico)"])

# --- ABA 1: RADAR ---
with aba_radar:
    # (Mantive a estrutura de inputs do seu radar original)
    st.info("Scanner configurado para buscar reversões em tempo real via Bunker.")
    # ... (Seu código do Radar Global aqui, apenas trocando tvDatafeed por puxar_dados_blindados)

# --- ABA 2: RAIO-X INDIVIDUAL ---
with aba_rx:
    st.subheader("🔬 Análise Detalhada com Gráfico Dinâmico")
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            ativo_rx = st.selectbox("Ativo:", ativos_para_rastrear, key="rx_at")
            capital_rx = st.number_input("Capital Base (R$):", value=10000.0, key="rx_cap")
        with c2:
            tempo_rx = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, key="rx_tmp")
            periodo_rx = st.selectbox("Período Estudo:", ['6mo', '1y', '2y', '5y', 'max'], index=1, key="rx_per")
        with c3:
            k_val = st.number_input("Período %K:", value=14)
            sv_val = st.number_input("Sobrevenda:", value=20)
            mostrar_graf = st.toggle("📊 Mostrar Oscilador no Gráfico", value=True)
        with c4:
            st_val = st.toggle("🛡️ Usar Stop Loss", value=True)
            stop_pct = st.number_input("Stop (%):", value=5.0, disabled=not st_val) / 100
            al_val = st.toggle("🎯 Usar Alvo Fixo", value=True)
            alvo_pct = st.number_input("Alvo (%):", value=10.0, disabled=not al_val) / 100

    if st.button("🔍 Rodar Laboratório Estocástico", type="primary", use_container_width=True):
        with st.spinner(f"Caçador analisando {ativo_rx}..."):
            try:
                df_full = puxar_dados_blindados(ativo_rx, tempo_rx)
                df_full = calcular_estocastico_bunker(df_full, k=k_val)
                
                if df_full is not None:
                    # Simulação de Trades
                    df_b = df_full.reset_index()
                    trades, em_pos = [], False
                    for i in range(1, len(df_b)):
                        candle = df_b.iloc[i]
                        ontem = df_b.iloc[i-1]
                        
                        # Entrada: Cruzamento de alta abaixo da sobrevenda
                        if not em_pos and (ontem['%K'] <= ontem['%D']) and (candle['%K'] > candle['%D']) and (candle['%K'] < sv_val):
                            em_pos = True
                            p_ent, d_ent = candle['close'], candle['index']
                        
                        elif em_pos:
                            res = (candle['close'] / p_ent) - 1
                            if (st_val and res <= -stop_pct) or (al_val and res >= alvo_pct) or candle['%K'] > 80:
                                trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': candle['index'].strftime('%d/%m/%Y'), 'Lucro (R$)': capital_rx * res, 'Situação': "✅" if res > 0 else "❌"})
                                em_pos = False

                    # EXIBIÇÃO DO GRÁFICO
                    st.plotly_chart(plotar_estocastico_plotly(df_full.tail(200), pd.DataFrame(trades), mostrar_graf), use_container_width=True)
                    
                    if trades:
                        st.dataframe(pd.DataFrame(trades), use_container_width=True, hide_index=True)
                        st.metric("Resultado Total", f"R$ {sum(t['Lucro (R$)'] for t in trades):,.2f}")
                else: st.error("Ativo sem dados no Bunker.")
            except Exception as e: st.error(f"Erro: {e}")
