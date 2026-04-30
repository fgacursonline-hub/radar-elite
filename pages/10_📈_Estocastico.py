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
    from motor_dados import puxar_dados_blindados
    ativos_para_rastrear = sorted(list(set([a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)])))
except ImportError:
    st.error("❌ Erro ao carregar dependências. Verifique os arquivos na raiz.")
    st.stop()

st.set_page_config(page_title="Estocástico Elite Bunker", layout="wide", page_icon="📈")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial.")
    st.stop()

tradutor_periodo_nome = {
    '1mo': '1 Mês', '3mo': '3 Meses', '6mo': '6 Meses',
    '1y': '1 Ano', '2y': '2 Anos', '5y': '5 Anos',
    'max': 'Máximo', '60d': '60 Dias'
}

# ==========================================
# 2. MOTOR MATEMÁTICO E GRÁFICO
# ==========================================
def calcular_estocastico_bunker(df, k=14, d=3, smooth_k=3, sobrecompra=80, sobrevenda=20):
    if df is None or df.empty or len(df) < k + smooth_k: return None
    df = df.copy()
    
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    
    stoch = ta.stoch(df['high'], df['low'], df['close'], k=k, d=d, smooth_k=smooth_k)
    if stoch is None or stoch.empty: return None
    
    df['%K'] = stoch[stoch.columns[0]]
    df['%D'] = stoch[stoch.columns[1]]
    df['%K_Prev'] = df['%K'].shift(1)
    df['%D_Prev'] = df['%D'].shift(1)
    
    df['Cruzou_Compra'] = (df['%K_Prev'] <= df['%D_Prev']) & (df['%K'] > df['%D']) & (df['%K'] < sobrevenda)
    df['Cruzou_Venda'] = (df['%K_Prev'] >= df['%D_Prev']) & (df['%K'] < df['%D']) & (df['%K'] > sobrecompra)
    
    return df.dropna()

def plotar_estocastico_plotly(df, trades_df, mostrar_oscilador):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
    
    fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Preço"), row=1, col=1)
    
    if mostrar_oscilador:
        fig.add_trace(go.Scatter(x=df.index, y=df['%K'], name="%K", line=dict(color='#00FFCC', width=1.5)), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['%D'], name="%D", line=dict(color='#FF4D4D', width=1.5, dash='dot')), row=2, col=1)
        fig.add_hline(y=80, line_dash="dash", line_color="gray", row=2, col=1)
        fig.add_hline(y=20, line_dash="dash", line_color="gray", row=2, col=1)

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
st.markdown("Rastreamento de reversões capturando os cruzamentos nas Zonas de Sobrevenda e Sobrecompra.")

aba_radar, aba_rx = st.tabs(["🌐 Radar Global (Scanner)", "🔬 Raio-X Individual (Gráfico)"])

# ==========================================
# ABA 1: RADAR GLOBAL (SCANNER)
# ==========================================
with aba_radar:
    with st.container(border=True):
        st.markdown("**1. Setup de Varredura**")
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        with col_f1: lista_selecionada = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos"])
        with col_f2: capital_trade_global = st.number_input("Capital por Trade (R$):", value=10000.00, step=1000.00, key="cap_g")
        with col_f3: tempo_grafico_global = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, key="tmp_g")
        with col_f4: periodo_busca_g = st.selectbox("Período de Busca:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], index=4, format_func=lambda x: tradutor_periodo_nome[x], key="per_g")

        st.markdown("**2. Calibração do Estocástico e Zonas de Pressão**")
        col_e1, col_e2, col_e3, col_e4, col_e5 = st.columns(5)
        with col_e1: k_g = st.number_input("Período (%K):", value=14, step=1, key="k_g")
        with col_e2: d_g = st.number_input("Média (%D):", value=3, step=1, key="d_g")
        with col_e3: smooth_g = st.number_input("Suavização:", value=3, step=1, key="sm_g")
        with col_e4: sobrecompra_g = st.number_input("Sobrecompra (>):", value=80, step=5, key="sc_g")
        with col_e5: sobrevenda_g = st.number_input("Sobrevenda (<):", value=20, step=5, key="sv_g")

        st.markdown("**3. Gestão de Risco e Saída**")
        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1: usar_saida_indicador_g = st.toggle("📈 Sair pelo Indicador", value=True, key="tg_ind_g")
        with col_r2:
            usar_alvo_g = st.toggle("🎯 Alvo Fixo", value=False, key="tg_alvo_g")
            alvo_pct_g = st.number_input("Alvo (%):", value=10.00, disabled=not usar_alvo_g, key="v_alvo_g") / 100.0
        with col_r3:
            usar_stop_g = st.toggle("🛡️ Stop Loss", value=True, key="tg_stop_g")
            stop_pct_g = st.number_input("Stop Fixo (%):", value=5.00, disabled=not usar_stop_g, key="v_stop_g") / 100.0

    if lista_selecionada == "BDRs Elite": ativos_alvo = bdrs_elite
    elif lista_selecionada == "IBrX Seleção": ativos_alvo = ibrx_selecao
    else: ativos_alvo = bdrs_elite + ibrx_selecao
    ativos_alvo = sorted(list(set([a.replace('.SA', '') for a in ativos_alvo])))

    if st.button("🚀 Iniciar Varredura Rápida (Bunker)", type="primary", use_container_width=True):
        oportunidades, andamento, historico = [], [], []
        p_bar = st.progress(0); s_text = st.empty()
        
        for i, ativo in enumerate(ativos_alvo):
            s_text.text(f"Caçando reversões: {ativo} ({i+1}/{len(ativos_alvo)})")
            p_bar.progress((i + 1) / len(ativos_alvo))
            try:
                df_full = puxar_dados_blindados(ativo, tempo_grafico_global)
                df_full = calcular_estocastico_bunker(df_full, k=k_g, d=d_g, smooth_k=smooth_g, sobrecompra=sobrecompra_g, sobrevenda=sobrevenda_g)
                
                if df_full is not None and not df_full.empty:
                    # Filtro de data
                    data_corte = df_full.index[-1] - pd.DateOffset(months={'1mo':1, '3mo':3, '6mo':6, '1y':12, '2y':24, '5y':60}.get(periodo_busca_g, 120)) if periodo_busca_g != 'max' else df_full.index[0]
                    df = df_full[df_full.index >= data_corte].copy()
                    
                    trade_aberto, trades_fechados = None, []
                    
                    for j in range(len(df)):
                        linha = df.iloc[j]
                        if trade_aberto is None:
                            if linha['Cruzou_Compra']:
                                if j == len(df) - 1:
                                    oportunidades.append({"Ativo": ativo, "Preço Atual": linha['close'], "%K Atual": linha['%K']})
                                else:
                                    trade_aberto = {'d_ent': df.index[j], 'p_ent': linha['close'], 'pico': linha['close'], 'pior_dd': 0.0}
                        else:
                            if linha['high'] > trade_aberto['pico']: trade_aberto['pico'] = linha['high']
                            dd_atual = (linha['low'] / trade_aberto['pico']) - 1
                            if dd_atual < trade_aberto['pior_dd']: trade_aberto['pior_dd'] = dd_atual
                            
                            b_stop = usar_stop_g and (linha['low'] <= trade_aberto['p_ent'] * (1 - stop_pct_g))
                            b_alvo = usar_alvo_g and (linha['high'] >= trade_aberto['p_ent'] * (1 + alvo_pct_g))
                            s_venda = usar_saida_indicador_g and linha['Cruzou_Venda']
                            
                            if b_stop or b_alvo or s_venda:
                                p_sai = trade_aberto['p_ent']*(1-stop_pct_g) if b_stop else (trade_aberto['p_ent']*(1+alvo_pct_g) if b_alvo else linha['close'])
                                lucro_rs = capital_trade_global * ((p_sai / trade_aberto['p_ent']) - 1)
                                trades_fechados.append({'lucro_rs': lucro_rs, 'pior_dd': trade_aberto['pior_dd']})
                                trade_aberto = None
                                
                    if trade_aberto:
                        res = (df['close'].iloc[-1] / trade_aberto['p_ent']) - 1
                        andamento.append({"Ativo": ativo, "Entrada": trade_aberto['d_ent'].strftime("%d/%m/%Y"), "PM": trade_aberto['p_ent'], "Cotação": df['close'].iloc[-1], "Resultado": res})
                    
                    if trades_fechados:
                        lucro_tot = sum(t['lucro_rs'] for t in trades_fechados)
                        historico.append({"Ativo": ativo, "Trades": len(trades_fechados), "Pior Queda": min(t['pior_dd'] for t in trades_fechados), "Lucro R$": lucro_tot})
            except: pass
            
        p_bar.empty(); s_text.empty()
        
        st.subheader("🚀 Oportunidades Hoje (Sinal Ativo)")
        if oportunidades: st.dataframe(pd.DataFrame(oportunidades), use_container_width=True, hide_index=True)
        else: st.info("Nenhum ativo disparou sinal de compra hoje.")
        
        st.subheader("🏆 Top 20 Histórico")
        if historico:
            df_hist = pd.DataFrame(historico).sort_values(by="Lucro R$", ascending=False).head(20)
            df_hist['Lucro R$'] = df_hist['Lucro R$'].apply(lambda x: f"R$ {x:,.2f}")
            df_hist['Pior Queda'] = df_hist['Pior Queda'].apply(lambda x: f"{x*100:.2f}%")
            st.dataframe(df_hist, use_container_width=True, hide_index=True)

# ==========================================
# ABA 2: RAIO-X INDIVIDUAL (GRÁFICO)
# ==========================================
with aba_rx:
    st.subheader("🔬 Análise Detalhada com Gráfico Dinâmico")
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            ativo_rx = st.selectbox("Ativo:", ativos_para_rastrear, key="rx_at")
            capital_rx = st.number_input("Capital Base (R$):", value=10000.0, key="rx_cap")
        with c2:
            tempo_rx = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, key="rx_tmp")
            periodo_rx = st.selectbox("Período Estudo:", ['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], index=3, format_func=lambda x: tradutor_periodo_nome[x], key="rx_per")
        with c3:
            k_val = st.number_input("Período %K:", value=14, key="rx_k")
            d_val = st.number_input("Média %D:", value=3, key="rx_d")
            sv_val = st.number_input("Sobrevenda:", value=20, key="rx_sv")
            sc_val = st.number_input("Sobrecompra:", value=80, key="rx_sc")
            mostrar_graf = st.toggle("📊 Mostrar Oscilador", value=True)
        with c4:
            st_val = st.toggle("🛡️ Stop Loss Fixo", value=True, key="rx_tg_st")
            stop_pct = st.number_input("Stop (%):", value=5.0, disabled=not st_val, key="rx_v_st") / 100
            al_val = st.toggle("🎯 Alvo Fixo", value=False, key="rx_tg_al")
            alvo_pct = st.number_input("Alvo (%):", value=10.0, disabled=not al_val, key="rx_v_al") / 100
            saida_ind = st.toggle("📈 Sair na Sobrecompra", value=True, key="rx_tg_ind")

    if st.button("🔍 Rodar Laboratório Estocástico", type="primary", use_container_width=True):
        with st.spinner(f"Processando gráficos para {ativo_rx}..."):
            try:
                df_full = puxar_dados_blindados(ativo_rx, tempo_rx)
                df_full = calcular_estocastico_bunker(df_full, k=k_val, d=d_val, sobrecompra=sc_val, sobrevenda=sv_val)
                
                if df_full is not None and not df_full.empty:
                    data_corte = df_full.index[-1] - pd.DateOffset(months={'1mo':1, '3mo':3, '6mo':6, '1y':12, '2y':24, '5y':60}.get(periodo_rx, 120)) if periodo_rx != 'max' else df_full.index[0]
                    df_b = df_full[df_full.index >= data_corte].copy().reset_index()
                    col_dt = df_b.columns[0]
                    
                    trades, em_pos = [], False
                    for i in range(1, len(df_b)):
                        candle = df_b.iloc[i]
                        
                        if not em_pos and candle['Cruzou_Compra']:
                            em_pos = True
                            p_ent, d_ent = candle['close'], candle[col_dt]
                        
                        elif em_pos:
                            res = (candle['close'] / p_ent) - 1
                            b_st = st_val and (res <= -stop_pct)
                            b_al = al_val and (res >= alvo_pct)
                            b_ind = saida_ind and candle['Cruzou_Venda']
                            
                            if b_st or b_al or b_ind:
                                situacao = "❌ Stop" if b_st else ("✅ Alvo" if b_al else "🎯 Saída Ind.")
                                trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': candle[col_dt].strftime('%d/%m/%Y'), 'Lucro (R$)': capital_rx * res, 'Situação': situacao})
                                em_pos = False

                    st.plotly_chart(plotar_estocastico_plotly(df_full.tail(250), pd.DataFrame(trades), mostrar_graf), use_container_width=True)
                    
                    if trades:
                        df_res = pd.DataFrame(trades)
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Total Trades", len(df_res))
                        c2.metric("Assertividade", f"{(len(df_res[df_res['Lucro (R$)'] > 0]) / len(df_res) * 100):.1f}%")
                        c3.metric("Resultado Bruto", f"R$ {df_res['Lucro (R$)'].sum():,.2f}")
                        
                        def colorir(val):
                            if '✅' in str(val) or '🎯' in str(val): return 'color: #00FFCC; font-weight: bold'
                            if '❌' in str(val): return 'color: #FF4D4D; font-weight: bold'
                            return ''
                        st.dataframe(df_res.style.map(colorir, subset=['Situação']), use_container_width=True, hide_index=True)
                    else: st.warning("Nenhum trade fechado no período.")
                else: st.error("Dados insuficientes no Bunker.")
            except Exception as e: st.error(f"Erro: {e}")
