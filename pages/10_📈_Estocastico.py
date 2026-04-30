import streamlit as st
import pandas as pd
import pandas_ta as ta
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. IMPORTAÇÕES DO SISTEMA (CORREÇÃO DO ERRO)
# ==========================================
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from config_ativos import bdrs_elite, ibrx_selecao
    from motor_dados import puxar_dados_blindados # Aqui a correção!
    ativos_para_rastrear = sorted(list(set([a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)])))
except ImportError:
    st.error("❌ Erro ao carregar dependências. Verifique os arquivos na raiz.")
    st.stop()

# Dicionário de tradução para exibição
tradutor_periodo_nome = {'1mo': '1 Mês', '3mo': '3 Meses', '6mo': '6 Meses', '1y': '1 Ano', '2y': '2 Anos', '5y': '5 Anos', 'max': 'Máximo'}

# ==========================================
# 2. FUNÇÕES MATEMÁTICAS E GRÁFICAS
# ==========================================
def calcular_indicadores_estocastico(df, k=14, d=3, smooth=3):
    if df is None: return None
    df = df.copy()
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    
    # Cálculo do Estocástico via pandas_ta
    stoch = ta.stoch(df['high'], df['low'], df['close'], k=k, d=d, smooth_k=smooth)
    df['STOCHk'] = stoch[f'STOCHk_{k}_{d}_{smooth}']
    df['STOCHd'] = stoch[f'STOCHd_{k}_{d}_{smooth}']
    df['STOCHk_Prev'] = df['STOCHk'].shift(1)
    df['STOCHd_Prev'] = df['STOCHd'].shift(1)
    return df

def plotar_grafico_estocastico(df, trades_df, mostrar_stoch=True):
    # Criar subplots: 1 para preço, 1 para Estocástico
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.05, row_heights=[0.7, 0.3])

    # 1. Gráfico de Velas (Candlestick)
    fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], 
                                 low=df['low'], close=df['close'], name="Preço"), row=1, col=1)

    # 2. Indicador Estocástico no subgráfico
    if mostrar_stoch:
        fig.add_trace(go.Scatter(x=df.index, y=df['STOCHk'], name="%K (Rápida)", line=dict(color='#00FFCC', width=1.5)), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['STOCHd'], name="%D (Média)", line=dict(color='#FF4D4D', width=1.5, dash='dot')), row=2, col=1)
        # Linhas de Sobrecompra/Sobrevenda
        fig.add_hline(y=80, line_dash="dash", line_color="gray", opacity=0.5, row=2, col=1)
        fig.add_hline(y=20, line_dash="dash", line_color="gray", opacity=0.5, row=2, col=1)

    # 3. Plotar as Entradas e Saídas no Preço
    if not trades_df.empty:
        # Filtramos apenas os trades que aparecem no recorte do gráfico
        for _, trade in trades_df.iterrows():
            ent_dt = pd.to_datetime(trade['Entrada'])
            if ent_dt in df.index:
                fig.add_annotation(x=ent_dt, y=df.loc[ent_dt, 'low'], text="▲ COMPRA", 
                                   showarrow=True, arrowhead=1, color="green", row=1, col=1)

    fig.update_layout(height=700, template="plotly_dark", showlegend=True, 
                      xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=30, b=10))
    return fig

# ==========================================
# 3. INTERFACE (ABA 2: RAIO-X)
# ==========================================
st.title("📈 Estocástico Elite")

aba_radar, aba_individual = st.tabs(["🌐 Radar de Mercado", "🔬 Raio-X Individual"])

with aba_individual:
    st.subheader("🔬 Análise Detalhada: Oscilador Estocástico")
    with st.container(border=True):
        ci1, ci2, ci3, ci4 = st.columns(4)
        with ci1:
            ativo_rx = st.selectbox("Ativo a Testar:", ativos_para_rastrear, key="st_rx_ativo")
            capital_rx = st.number_input("Capital Base (R$):", value=10000.0, step=1000.0, key="st_rx_cap")
        with ci2:
            tempo_rx = st.selectbox("Tempo Gráfico:", options=['15m', '60m', '1d', '1wk'], index=2, key="st_rx_tmp")
            periodo_rx = st.selectbox("Período de Estudo:", options=['6mo', '1y', '2y', '5y', 'max'], index=1, key="st_rx_per")
        with ci3:
            st.markdown("##### ⚙️ Parâmetros")
            k_len = st.number_input("K (Período):", value=14)
            oversold_rx = st.number_input("Sobrevenda:", value=20)
            overbought_rx = st.number_input("Sobrecompra:", value=80)
            mostrar_subgrafico_st = st.toggle("📊 Mostrar Oscilador", value=True)
        with ci4:
            st.markdown("##### 🛡️ Gestão de Risco")
            usar_alvo_rx = st.toggle("🎯 Alvo Fixo (%)", value=True)
            lupa_alvo = st.number_input("Valor Alvo:", value=10.0, disabled=not usar_alvo_rx)
            usar_saida_ob_rx = st.toggle("📉 Saída em Sobrecompra", value=True)

    if st.button("🔍 Gerar Raio-X do Estocástico", type="primary", use_container_width=True):
        alvo_d = lupa_alvo / 100.0
        try:
            df_full = puxar_dados_blindados(ativo_rx, tempo_rx)
            if df_full is not None and len(df_full) > 50:
                df_full = calcular_indicadores_estocastico(df_full, k_len)
                
                # Recorte de tempo
                df_b = df_full.tail(500).copy().reset_index() # Exemplo de recorte simplificado
                col_dt = df_b.columns[0]
                trades, em_pos, vitorias, derrotas = [], False, 0, 0
                
                # Simulação de trades
                for i in range(1, len(df_b)):
                    # Entrada: Cruzamento de alta abaixo da sobrevenda
                    sinal_entrada = (df_b['STOCHk_Prev'].iloc[i] <= df_b['STOCHd_Prev'].iloc[i]) and \
                                    (df_b['STOCHk'].iloc[i] > df_b['STOCHd'].iloc[i]) and \
                                    (df_b['STOCHk'].iloc[i] < oversold_rx)
                    
                    if not em_pos and sinal_entrada:
                        em_pos = True
                        pos_info = {'d_ent': df_b[col_dt].iloc[i], 'p_ent': df_b['close'].iloc[i]}
                    elif em_pos:
                        lucro_at = (df_b['close'].iloc[i] / pos_info['p_ent']) - 1
                        bateu_alvo = usar_alvo_rx and (lucro_at >= alvo_d)
                        bateu_ob = usar_saida_ob_rx and (df_b['STOCHk'].iloc[i] > overbought_rx)
                        
                        if bateu_alvo or bateu_ob:
                            trades.append({'Entrada': pos_info['d_ent'], 'Saída': df_b[col_dt].iloc[i], 
                                           'Lucro (R$)': capital_rx * lucro_at, 'Situação': "✅ Gain" if lucro_at > 0 else "❌ Loss"})
                            if lucro_at > 0: vitorias += 1
                            else: derrotas += 1
                            em_pos = False

                # Exibição do Gráfico
                st.plotly_chart(plotar_grafico_estocastico(df_full.tail(200), pd.DataFrame(trades)), use_container_width=True)
                
                # Tabela de Resultados
                if trades:
                    st.dataframe(pd.DataFrame(trades), use_container_width=True, hide_index=True)
                    st.metric("Taxa de Acerto", f"{(vitorias/len(trades)*100):.1f}%")
            else:
                st.error("Dados insuficientes.")
        except Exception as e:
            st.error(f"Erro no processamento: {e}")
