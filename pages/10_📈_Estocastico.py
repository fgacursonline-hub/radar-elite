import streamlit as st
import pandas as pd
import pandas_ta as ta
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import warnings
import sys
import os
from datetime import datetime

warnings.filterwarnings('ignore')

# ==========================================
# 1. IMPORTAÇÃO CENTRALIZADA DOS ATIVOS E BUNKER
# ==========================================
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from config_ativos import bdrs_elite, ibrx_selecao
    from motor_dados import puxar_dados_blindados # MODO BUSCA PELO BUNKER AQUI!
except ImportError:
    st.error("❌ Arquivo 'config_ativos.py' ou 'motor_dados.py' não encontrado na raiz do projeto.")
    st.stop()

ativos_para_rastrear = sorted(list(set([a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)])))

# ==========================================
# 2. CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Estocástico Elite", layout="wide", page_icon="📈")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

tradutor_periodo_nome = {
    '1mo': '1 Mês', '3mo': '3 Meses', '6mo': '6 Meses',
    '1y': '1 Ano', '2y': '2 Anos', '5y': '5 Anos',
    'max': 'Máximo', '60d': '60 Dias'
}

st.title("📈 Máquina Quantitativa: Estocástico")
st.markdown("Rastreamento de reversões capturando os cruzamentos nas Zonas de Sobrevenda e Sobrecompra.")

aba_radar, aba_individual = st.tabs(["🌐 Radar Global (Scanner & Top 20)", "🔬 Raio-X Individual (Backtest)"])

# ==========================================
# 3. MOTOR MATEMÁTICO E FUNÇÃO DO GRÁFICO (PLOTLY)
# ==========================================
def calcular_estocastico(df, k=14, d=3, smooth_k=3, sobrecompra=80, sobrevenda=20):
    if df.empty or len(df) < k + smooth_k: return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = df.index.tz_localize(None)
    
    # Cálculo do Estocástico Pleno (Full)
    stoch_df = df.ta.stoch(high='High', low='Low', close='Close', k=k, d=d, smooth_k=smooth_k)
    if stoch_df is None or stoch_df.empty: return pd.DataFrame()
    
    # Captura os nomes dinâmicos das colunas geradas pelo pandas_ta
    col_k = [c for c in stoch_df.columns if 'STOCHk' in c][0]
    col_d = [c for c in stoch_df.columns if 'STOCHd' in c][0]
    
    df['%K'] = stoch_df[col_k]
    df['%D'] = stoch_df[col_d]
    
    # Gatilho de Compra: %K cruza %D para cima, e ambas (ou a %K) estão na zona de Sobrevenda
    cruzamento_alta = (df['%K'].shift(1) <= df['%D'].shift(1)) & (df['%K'] > df['%D'])
    df['Cruzou_Compra'] = cruzamento_alta & (df['%K'] < sobrevenda)
    
    # Gatilho de Venda/Saída (Opcional do indicador): %K cruza %D para baixo na zona de Sobrecompra
    cruzamento_baixa = (df['%K'].shift(1) >= df['%D'].shift(1)) & (df['%K'] < df['%D'])
    df['Cruzou_Venda'] = cruzamento_baixa & (df['%K'] > sobrecompra)
    
    return df.dropna()

def plotar_estocastico_plotly(df, trades_df, mostrar_oscilador):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
    
    # Gráfico de Preços
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Preço"), row=1, col=1)
    
    # Indicador Estocástico
    if mostrar_oscilador and '%K' in df:
        fig.add_trace(go.Scatter(x=df.index, y=df['%K'], name="%K", line=dict(color='#00FFCC', width=1.5)), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['%D'], name="%D", line=dict(color='#FF4D4D', width=1.5, dash='dot')), row=2, col=1)
        fig.add_hline(y=80, line_dash="dash", line_color="gray", row=2, col=1)
        fig.add_hline(y=20, line_dash="dash", line_color="gray", row=2, col=1)

    # Setas de Entrada
    if not trades_df.empty:
        for _, trade in trades_df.iterrows():
            try:
                data_ent = pd.to_datetime(trade['Entrada'], format="%d/%m/%Y")
                if data_ent in df.index:
                    fig.add_annotation(x=data_ent, y=df.loc[data_ent, 'Low'], text="▲ COMPRA", showarrow=True, arrowhead=1, color="green", row=1, col=1)
            except: pass

    fig.update_layout(height=700, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=30, b=10))
    return fig

def exibir_explicacao_estrategia():
    st.info("📈 **A Estratégia (Estocástico Pleno):** Identifica os níveis de sobrecompra e sobrevenda medindo o impulso (velocidade) dos preços. \n\n🟢 **Gatilho de Compra:** Ocorre quando a Linha Rápida (%K) cruza a Linha Lenta (%D) para CIMA, com ambas abaixo da zona de Sobrevenda. O preço estava caindo forte e começou a reagir. \n\n🔴 **Gatilho de Saída (Defesa):** Opcionalmente, o trade encerra quando o indicador atinge a zona de Sobrecompra e cruza para BAIXO, ou ao atingir os limites fixos de stop/alvo.")

# ==========================================
# ABA 1: RADAR GLOBAL (SCANNER + TOP 20)
# ==========================================
with aba_radar:
    with st.container(border=True):
        st.markdown("**1. Setup de Varredura**")
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        with col_f1:
            lista_selecionada = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"])
        with col_f2:
            capital_trade_global = st.number_input("Capital por Trade (R$):", value=10000.00, step=1000.00, key="cap_global")
        with col_f3:
            tempo_grafico_global = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="tmp_global")
        with col_f4:
            periodo_busca_g = st.selectbox("Período de Busca:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=4, key="per_busca_g")

        exibir_explicacao_estrategia()

        st.markdown("**2. Calibração do Estocástico e Zonas de Pressão**")
        col_e1, col_e2, col_e3, col_e4, col_e5 = st.columns(5)
        with col_e1:
            k_g = st.number_input("Período (%K):", value=14, step=1, key="k_g")
        with col_e2:
            d_g = st.number_input("Média (%D):", value=3, step=1, key="d_g")
        with col_e3:
            smooth_g = st.number_input("Suavização:", value=3, step=1, key="smooth_g")
        with col_e4:
            sobrecompra_g = st.number_input("Sobrecompra (>):", value=80, step=5, key="sc_g")
        with col_e5:
            sobrevenda_g = st.number_input("Sobrevenda (<):", value=20, step=5, key="sv_g")

        st.markdown("**3. Gestão de Risco e Saída**")
        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1:
            usar_saida_indicador_g = st.toggle("📈 Sair pelo Indicador (Zona de Sobrecompra)", value=True, key="tg_ind_g")
            st.caption("Fecha operação quando cruzar p/ baixo no teto.")
        with col_r2:
            usar_alvo_g = st.toggle("🎯 Alvo Fixo (Take Profit)", value=False, key="tg_alvo_g")
            alvo_pct_g = st.number_input("Alvo (%):", value=10.00, step=1.00, key="val_alvo_g", disabled=not usar_alvo_g) / 100.0
        with col_r3:
            usar_stop_g = st.toggle("🛡️ Stop Loss", value=True, key="tg_stop_g")
            stop_pct_g = st.number_input("Stop Fixo (%):", value=5.00, step=1.00, key="val_stop_g", disabled=not usar_stop_g) / 100.0

    if lista_selecionada == "BDRs Elite": ativos_alvo = bdrs_elite
    elif lista_selecionada == "IBrX Seleção": ativos_alvo = ibrx_selecao
    else: ativos_alvo = bdrs_elite + ibrx_selecao
    ativos_alvo = sorted(list(set([a.replace('.SA', '') for a in ativos_alvo])))

    btn_iniciar_global = st.button("🚀 Iniciar Varredura do Estocástico (Bunker)", type="primary", use_container_width=True)

    if btn_iniciar_global:
        oportunidades, andamento, historico = [], [], []
        p_bar = st.progress(0)
        s_text = st.empty()
        
        for i, ativo in enumerate(ativos_alvo):
            s_text.text(f"Mapeando Zonas de Reversão via Bunker: {ativo} ({i+1}/{len(ativos_alvo)})")
            p_bar.progress((i + 1) / len(ativos_alvo))
            try:
                # SUBSTITUÍDO: tv.get_hist PELO BUNKER
                df_full = puxar_dados_blindados(ativo, tempo_grafico_global)
                if df_full is None or len(df_full) < (k_g + smooth_g): continue

                df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                df_full = df_full.dropna()
                
                df_full = calcular_estocastico(df_full, k=k_g, d=d_g, smooth_k=smooth_g, sobrecompra=sobrecompra_g, sobrevenda=sobrevenda_g)
                if df_full.empty: continue
                
                data_atual = df_full.index[-1]
                if periodo_busca_g == '1mo': data_corte = data_atual - pd.DateOffset(months=1)
                elif periodo_busca_g == '3mo': data_corte = data_atual - pd.DateOffset(months=3)
                elif periodo_busca_g == '6mo': data_corte = data_atual - pd.DateOffset(months=6)
                elif periodo_busca_g == '1y': data_corte = data_atual - pd.DateOffset(years=1)
                elif periodo_busca_g == '2y': data_corte = data_atual - pd.DateOffset(years=2)
                elif periodo_busca_g == '5y': data_corte = data_atual - pd.DateOffset(years=5)
                else: data_corte = df_full.index[0]
                
                df = df_full[df_full.index >= data_corte].copy()
                if len(df) == 0: continue
                
                trade_aberto = None
                trades_fechados = []
                
                for j in range(len(df)):
                    linha = df.iloc[j]
                    data = df.index[j]
                    
                    if trade_aberto is None:
                        if linha['Cruzou_Compra']:
                            if j == len(df) - 1:
                                oportunidades.append({"Ativo": ativo, "Sinal": "Reversão (Sobrevenda) 🟢", "Preço Atual": linha['Close'], "%K Atual": linha['%K']})
                            else:
                                trade_aberto = {'entrada_data': data, 'entrada_preco': linha['Close'], 'pico': linha['Close'], 'pior_queda': 0.0}
                    else:
                        if linha['High'] > trade_aberto['pico']: trade_aberto['pico'] = linha['High']
                        dd_atual = (linha['Low'] / trade_aberto['pico']) - 1
                        if dd_atual < trade_aberto['pior_queda']: trade_aberto['pior_queda'] = dd_atual
                        
                        bateu_stop = usar_stop_g and (linha['Low'] <= trade_aberto['entrada_preco'] * (1 - stop_pct_g))
                        bateu_alvo = usar_alvo_g and (linha['High'] >= trade_aberto['entrada_preco'] * (1 + alvo_pct_g))
                        sinal_venda = usar_saida_indicador_g and linha['Cruzou_Venda']
                        
                        if bateu_stop or bateu_alvo or sinal_venda:
                            preco_saida = trade_aberto['entrada_preco'] * (1 - stop_pct_g) if bateu_stop else (trade_aberto['entrada_preco'] * (1 + alvo_pct_g) if bateu_alvo else linha['Close'])
                            lucro_rs = capital_trade_global * ((preco_saida / trade_aberto['entrada_preco']) - 1)
                            trades_fechados.append({'lucro_rs': lucro_rs, 'pior_queda': trade_aberto['pior_queda']})
                            trade_aberto = None
                
                if trade_aberto is not None:
                    dias = (datetime.now().date() - trade_aberto['entrada_data'].date()).days
                    resultado = (df['Close'].iloc[-1] / trade_aberto['entrada_preco']) - 1
                    andamento.append({"Ativo": ativo, "Entrada": trade_aberto['entrada_data'].strftime("%d/%m/%Y"), "Dias": dias, "PM": trade_aberto['entrada_preco'], "Cotação Atual": df['Close'].iloc[-1], "%K Atual": df['%K'].iloc[-1], "Resultado Atual": resultado})
                
                if trades_fechados:
                    total_trades = len(trades_fechados)
                    lucro_total = sum(t['lucro_rs'] for t in trades_fechados)
                    pior_dd = min(t['pior_queda'] for t in trades_fechados)
                    investimento = capital_trade_global * total_trades
                    historico.append({"Ativo": ativo, "Trades": total_trades, "Pior Queda": pior_dd, "Investimento": investimento, "Lucro R$": lucro_total, "Resultado": lucro_total / investimento if investimento > 0 else 0})
            except Exception as e: 
                pass
            time.sleep(0.01)
        
        p_bar.empty(); s_text.empty()
        
        st.subheader(f"📈 Oportunidades Hoje (Cruzamento < {sobrevenda_g})")
        if oportunidades:
            df_op = pd.DataFrame(oportunidades)
            df_op['Preço Atual'] = df_op['Preço Atual'].apply(lambda x: f"R$ {x:.2f}")
            df_op['%K Atual'] = df_op['%K Atual'].apply(lambda x: f"{x:.2f}")
            st.dataframe(df_op, use_container_width=True, hide_index=True)
        else: st.info("Nenhum ativo disparou sinal de reversão no pregão atual.")

        st.subheader("⏳ Operações em Andamento (Buscando Sobrecompra)")
        if andamento:
            df_and = pd.DataFrame(andamento)
            df_and['PM'] = df_and['PM'].apply(lambda x: f"R$ {x:.2f}")
            df_and['Cotação Atual'] = df_and['Cotação Atual'].apply(lambda x: f"R$ {x:.2f}")
            df_and['%K Atual'] = df_and['%K Atual'].apply(lambda x: f"{x:.2f}")
            st.dataframe(df_and.style.format({'Resultado Atual': "{:.2%}"}).map(lambda val: f"color: {'#00FFCC' if val > 0 else '#FF4D4D'}; font-weight: bold" if isinstance(val, float) else '', subset=['Resultado Atual']), use_container_width=True, hide_index=True)
        else: st.info("Nenhuma operação em aberto no momento.")

        st.subheader(f"🏆 Top 20 Histórico ({tradutor_periodo_nome.get(periodo_busca_g, periodo_busca_g)})")
        if historico:
            df_hist = pd.DataFrame(historico).sort_values(by="Lucro R$", ascending=False).head(20)
            df_hist['Pior Queda'] = df_hist['Pior Queda'].apply(lambda x: f"{x*100:.2f}%")
            df_hist['Investimento'] = df_hist['Investimento'].apply(lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
            st.dataframe(df_hist.style.format({'Lucro R$': "R$ {:,.2f}", 'Resultado': "{:.2%}"}).map(lambda val: f"color: {'#00FFCC' if val > 0 else '#FF4D4D'}" if isinstance(val, str) else '', subset=['Lucro R$', 'Resultado']), use_container_width=True, hide_index=True)
        else:
            st.warning("Nenhum histórico encontrado com a calibração selecionada.")

# ==========================================
# ABA 2: RAIO-X INDIVIDUAL (O LABORATÓRIO)
# ==========================================
with aba_individual:
    with st.container(border=True):
        st.markdown("**1. Setup e Capital**")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            ativo_rx = st.selectbox("Ativo (Ex: TSLA34):", ativos_para_rastrear, key="rx_ativo")
            periodo_rx = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=4, key="rx_per")
        with c2:
            capital_rx = st.number_input("Capital Base (R$):", value=10000.00, step=1000.00, key="rx_cap")
            tempo_rx = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="rx_tmp")
        with c3:
            usar_saida_indicador_rx = st.toggle("📈 Sair pelo Indicador", value=True, key="tg_ind_rx")
            usar_alvo_rx = st.toggle("🎯 Habilitar Alvo", value=False, key="tg_alvo_rx")
            alvo_rx = st.number_input("Alvo (%):", value=10.00, step=1.00, key="rx_alvo", disabled=not usar_alvo_rx)
            # ADICIONADO: Botão para controlar o gráfico
            mostrar_graf_rx = st.toggle("📊 Mostrar Oscilador no Gráfico", value=True, key="tg_graf_rx")
        with c4:
            st.markdown("<br>", unsafe_allow_html=True)
            usar_stop_rx = st.toggle("🛡️ Habilitar Stop Loss", value=True, key="tg_stop_rx")
            stop_rx = st.number_input("Stop Loss (%):", value=5.00, step=1.00, key="rx_stop", disabled=not usar_stop_rx)
            
        exibir_explicacao_estrategia()
            
        st.markdown("**2. Calibração (Full Stochastic)**")
        col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
        with col_m1: k_rx = st.number_input("Período (%K):", value=14, step=1, key="k_rx")
        with col_m2: d_rx = st.number_input("Média (%D):", value=3, step=1, key="d_rx")
        with col_m3: smooth_rx = st.number_input("Suavização:", value=3, step=1, key="smooth_rx")
        with col_m4: sobrecompra_rx = st.number_input("Sobrecompra:", value=80, step=5, key="sc_rx")
        with col_m5: sobrevenda_rx = st.number_input("Sobrevenda:", value=20, step=5, key="sv_rx")
            
    btn_rx = st.button("🔍 Rodar Laboratório Estocástico", type="primary", use_container_width=True)
    
    if btn_rx:
        with st.spinner(f"Calculando reversões de {ativo_rx} via Bunker..."):
            try:
                # SUBSTITUÍDO: tv.get_hist PELO BUNKER
                df_full = puxar_dados_blindados(ativo_rx, tempo_rx)
                
                if df_full is not None and len(df_full) > (k_rx + smooth_rx):
                    df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                    df_full = df_full.dropna()
                    
                    df_full = calcular_estocastico(df_full, k=k_rx, d=d_rx, smooth_k=smooth_rx, sobrecompra=sobrecompra_rx, sobrevenda=sobrevenda_rx)
                    
                    data_atual = df_full.index[-1]
                    if periodo_rx == '1mo': data_corte = data_atual - pd.DateOffset(months=1)
                    elif periodo_rx == '3mo': data_corte = data_atual - pd.DateOffset(months=3)
                    elif periodo_rx == '6mo': data_corte = data_atual - pd.DateOffset(months=6)
                    elif periodo_rx == '1y': data_corte = data_atual - pd.DateOffset(years=1)
                    elif periodo_rx == '2y': data_corte = data_atual - pd.DateOffset(years=2)
                    elif periodo_rx == '5y': data_corte = data_atual - pd.DateOffset(years=5)
                    else: data_corte = df_full.index[0]
                    
                    df_ativo = df_full[df_full.index >= data_corte].copy()
                    
                    if not df_ativo.empty:
                        alvo_pct = alvo_rx / 100.0
                        stop_pct = stop_rx / 100.0
                        trades_fechados = []
                        em_aberto = None
                        
                        for i in range(len(df_ativo)):
                            linha = df_ativo.iloc[i]
                            data = df_ativo.index[i]
                            
                            if em_aberto is None:
                                if linha['Cruzou_Compra']:
                                    em_aberto = {'entrada_data': data, 'entrada_preco': linha['Close'], 'pico': linha['Close'], 'pior_queda': 0.0}
                            else:
                                if linha['High'] > em_aberto['pico']: em_aberto['pico'] = linha['High']
                                dd = (linha['Low'] / em_aberto['pico']) - 1
                                if dd < em_aberto['pior_queda']: em_aberto['pior_queda'] = dd
                                
                                bateu_stop = usar_stop_rx and (linha['Low'] <= em_aberto['entrada_preco'] * (1 - stop_pct))
                                bateu_alvo = usar_alvo_rx and (linha['High'] >= em_aberto['entrada_preco'] * (1 + alvo_pct))
                                sinal_venda = usar_saida_indicador_rx and linha['Cruzou_Venda']
                                
                                if bateu_stop or bateu_alvo or sinal_venda:
                                    if bateu_stop:
                                        preco_saida = em_aberto['entrada_preco'] * (1 - stop_pct); motivo = "Stop Loss"
                                    elif bateu_alvo:
                                        preco_saida = em_aberto['entrada_preco'] * (1 + alvo_pct); motivo = "Alvo Fixo (Gain)"
                                    else:
                                        preco_saida = linha['Close']; motivo = "Reversão (Sobrecompra)"

                                    lucro_pct = (preco_saida / em_aberto['entrada_preco']) - 1
                                    lucro_rs = capital_rx * lucro_pct
                                    duracao = (data - em_aberto['entrada_data']).days
                                    trades_fechados.append({
                                        'Entrada': em_aberto['entrada_data'].strftime("%d/%m/%Y"), 
                                        'Saída': data.strftime("%d/%m/%Y"), 
                                        'Motivo Saída': motivo, 
                                        'Duração': duracao, 
                                        'Lucro (R$)': lucro_rs, 
                                        'Queda Máx': em_aberto['pior_queda'], 
                                        'Situação': "Gain ✅" if lucro_pct > 0 else "Loss ❌"
                                    })
                                    em_aberto = None

                        if em_aberto is not None:
                            st.info(f"⏳ **{ativo_rx}: Em Operação** (Buscando Sobrecompra | Desde {em_aberto['entrada_data'].strftime('%d/%m/%Y')} a R$ {em_aberto['entrada_preco']:.2f})")
                        else:
                            st.success(f"✅ **{ativo_rx}: Aguardando Novo Sinal na Zona de Sobrevenda (<{sobrevenda_rx})**")

                        st.markdown(f"### 📊 Resultado Consolidado: {ativo_rx}")
                        if trades_fechados:
                            df_trades = pd.DataFrame(trades_fechados)
                            m1, m2, m3, m4 = st.columns(4)
                            m1.metric("Lucro Total", f"R$ {df_trades['Lucro (R$)'].sum():.2f}")
                            m2.metric("Duração Média", f"{df_trades['Duração'].mean():.1f} dias")
                            m3.metric("Operações Fechadas", len(df_trades))
                            m4.metric("Pior Queda", f"{df_trades['Queda Máx'].min()*100:.2f}%")
                            
                            st.markdown("<br>", unsafe_allow_html=True)
                            df_show = df_trades.copy()
                            df_show['Lucro (R$)'] = df_show['Lucro (R$)'].apply(lambda x: f"R$ {x:.2f}")
                            df_show['Queda Máx'] = df_show['Queda Máx'].apply(lambda x: f"{x*100:.2f}%")
                            def colorir_tabela(val):
                                if 'Gain' in str(val) or ('R$' in str(val) and '-' not in str(val) and val != 'R$ 0.00'): return 'color: #00FFCC; font-weight: bold'
                                if 'Loss' in str(val) or ('R$' in str(val) and '-' in str(val)): return 'color: #FF4D4D; font-weight: bold'
                                return ''
                            st.dataframe(df_show.style.map(colorir_tabela), use_container_width=True, hide_index=True)
                        else:
                            st.warning("Nenhuma operação concluída no período com os parâmetros selecionados.")

                        st.divider()
                        st.markdown(f"### 📈 Gráfico Interativo: {ativo_rx}")
                        # SUBSTITUÍDO: renderizar_grafico_tv(f"BMFBOVESPA:{ativo_rx}") PELO PLOTLY
                        corte_grafico = df_ativo.tail(250)
                        df_trades_plot = pd.DataFrame(trades_fechados) if trades_fechados else pd.DataFrame()
                        st.plotly_chart(plotar_estocastico_plotly(corte_grafico, df_trades_plot, mostrar_graf_rx), use_container_width=True)
                        st.info("💡 **Dica:** O gráfico acima já exibe as zonas de sobrevenda e sobrecompra e marca as entradas com setas verdes.")
                        
                    else:
                        st.error("Sem dados suficientes no período de corte.")
                else:
                    st.error("Não foi possível coletar dados do Bunker para este ativo.")
            except Exception as e:
                st.error(f"Erro no processamento via Bunker: {e}")
