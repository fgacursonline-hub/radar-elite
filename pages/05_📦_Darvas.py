import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
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
    from motor_dados import puxar_dados_blindados # MODO BUSCA PELO BUNKER AQUI
except ImportError:
    st.error("❌ Arquivo 'config_ativos.py' ou 'motor_dados.py' não encontrado na raiz do projeto.")
    st.stop()

ativos_para_rastrear = sorted(list(set([a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)])))

# ==========================================
# 2. CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Darvas Box Elite", layout="wide", page_icon="📦")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

tradutor_periodo_nome = {
    '1mo': '1 Mês', '3mo': '3 Meses', '6mo': '6 Meses',
    '1y': '1 Ano', '2y': '2 Anos', '5y': '5 Anos',
    'max': 'Máximo', '60d': '60 Dias'
}

st.title("📦 Máquina Quantitativa: Darvas Box")
st.markdown("Trend Following agressivo: Compre rompimentos de máximas e mova o stop pelo fundo das caixas.")

aba_radar, aba_individual = st.tabs(["🌐 Radar Global (Scanner & Top 20)", "🔬 Raio-X Individual (Backtest)"])

# ==========================================
# 3. MOTOR MATEMÁTICO E GRÁFICO (DARVAS BOX)
# ==========================================
def calcular_darvas(df, periodo_caixa=20):
    if df.empty or len(df) < periodo_caixa: return pd.DataFrame()
    
    # A Caixa de Darvas (Mapeamento do Teto e do Piso)
    df['Darvas_Top'] = df['High'].rolling(window=periodo_caixa).max()
    df['Darvas_Bottom'] = df['Low'].rolling(window=periodo_caixa).min()
    
    # Gatilho de Rompimento: Fechamento cruza o Teto da caixa anterior
    df['Cruzou_Compra'] = (df['Close'] > df['Darvas_Top'].shift(1)) & (df['Close'].shift(1) <= df['Darvas_Top'].shift(1))
    
    # Gatilho de Venda/Stop: Perdeu o Piso da caixa anterior
    df['Cruzou_Venda'] = (df['Close'] < df['Darvas_Bottom'].shift(1)) & (df['Close'].shift(1) >= df['Darvas_Bottom'].shift(1))
    
    return df.dropna()

def plotar_darvas_plotly(df, trades_df, mostrar_caixas):
    fig = go.Figure()
    
    # Preço em Candlestick
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Preço"))
    
    # Linhas da Caixa de Darvas (em formato 'step' / 'hv' para ficar com cara de caixa)
    if mostrar_caixas and 'Darvas_Top' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['Darvas_Top'], name="Teto (Darvas)", line=dict(color='#00FFCC', width=1.5, shape='hv')))
        fig.add_trace(go.Scatter(x=df.index, y=df['Darvas_Bottom'], name="Piso (Darvas)", line=dict(color='#FF4D4D', width=1.5, shape='hv')))

    # Setas de Entrada
    if not trades_df.empty:
        for _, trade in trades_df.iterrows():
            try:
                data_ent = pd.to_datetime(trade['Entrada'], format="%d/%m/%Y")
                if data_ent in df.index:
                    fig.add_annotation(x=data_ent, y=df.loc[data_ent, 'Low'], text="▲ COMPRA", showarrow=True, arrowhead=1, color="green", yshift=-10)
            except: pass

    fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=30, b=10))
    return fig

def exibir_explicacao_estrategia():
    st.info("📦 **A Estratégia Darvas Box:** Sistema clássico de Trend Following (Seguidor de Tendência) criado por Nicolas Darvas. \n\n🟢 **Gatilho de Compra:** Ocorre no exato momento em que o preço rompe o Teto (resistência máxima) de uma consolidação. \n\n🔴 **Gatilho de Venda (Defesa):** O Stop Loss padrão da estratégia fica posicionado logo abaixo do Piso da Caixa anterior. O trade só encerra quando esse piso é rompido para baixo (ou se atingir os seus alvos e stops fixos opcionais).")

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
            periodo_caixa_g = st.number_input("Tamanho da Caixa (Dias):", value=20, step=5, key="per_caixa_g")
            st.caption("20 dias = Rompimento Mensal")
        with col_f3:
            tempo_grafico_global = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="tmp_global")
        with col_f4:
            periodo_busca_g = st.selectbox("Período de Busca:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=4, key="per_busca_g")

        exibir_explicacao_estrategia()

        st.markdown("**2. Gestão de Risco e Saída**")
        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        with col_p1:
            capital_trade_global = st.number_input("Capital por Trade (R$):", value=10000.00, step=1000.00, key="cap_global")
        with col_p2:
            usar_stop_darvas_g = st.toggle("📦 Usar Piso da Caixa como Stop (Original)", value=True, key="tg_stop_darvas_g")
            st.caption("O Stop sobe automaticamente.")
        with col_p3:
            usar_alvo_g = st.toggle("🎯 Alvo Fixo (Take Profit)", value=False, key="tg_alvo_g")
            alvo_pct_g = st.number_input("Alvo (%):", value=15.00, step=1.00, key="val_alvo_g", disabled=not usar_alvo_g) / 100.0
        with col_p4:
            usar_stop_fixo_g = st.toggle("🛡️ Stop Fixo (%)", value=False, key="tg_stop_fixo_g")
            stop_pct_g = st.number_input("Stop Fixo (%):", value=5.00, step=1.00, key="val_stop_fixo_g", disabled=not usar_stop_fixo_g) / 100.0

    if lista_selecionada == "BDRs Elite": ativos_alvo = bdrs_elite
    elif lista_selecionada == "IBrX Seleção": ativos_alvo = ibrx_selecao
    else: ativos_alvo = bdrs_elite + ibrx_selecao
    ativos_alvo = sorted(list(set([a.replace('.SA', '') for a in ativos_alvo])))

    btn_iniciar_global = st.button("🚀 Iniciar Varredura Darvas Box (Bunker)", type="primary", use_container_width=True)

    if btn_iniciar_global:
        oportunidades, andamento, historico = [], [], []
        p_bar = st.progress(0)
        s_text = st.empty()
        
        for i, ativo in enumerate(ativos_alvo):
            s_text.text(f"Desenhando Caixas via Bunker: {ativo} ({i+1}/{len(ativos_alvo)})")
            p_bar.progress((i + 1) / len(ativos_alvo))
            try:
                # SUBSTITUÍDO tv.get_hist PELO BUNKER
                df_full = puxar_dados_blindados(ativo, tempo_grafico_global)
                if df_full is None or len(df_full) < 50: continue

                # Padronizando colunas para manter a compatibilidade com a sua lógica original
                if isinstance(df_full.columns, pd.MultiIndex): df_full.columns = df_full.columns.get_level_values(0)
                df_full.columns = [c.capitalize() for c in df_full.columns]
                df_full = df_full.dropna()
                
                df_full = calcular_darvas(df_full, periodo_caixa=periodo_caixa_g)
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
                                oportunidades.append({"Ativo": ativo, "Sinal": "Rompimento do Teto 🚀", "Preço Atual": linha['Close'], "Teto Rompido": linha['Darvas_Top']})
                            else:
                                trade_aberto = {'entrada_data': data, 'entrada_preco': linha['Close'], 'pico': linha['Close'], 'pior_queda': 0.0}
                    else:
                        if linha['High'] > trade_aberto['pico']: trade_aberto['pico'] = linha['High']
                        dd_atual = (linha['Low'] / trade_aberto['pico']) - 1
                        if dd_atual < trade_aberto['pior_queda']: trade_aberto['pior_queda'] = dd_atual
                        
                        # Saídas
                        bateu_stop_fixo = usar_stop_fixo_g and (linha['Low'] <= trade_aberto['entrada_preco'] * (1 - stop_pct_g))
                        bateu_alvo = usar_alvo_g and (linha['High'] >= trade_aberto['entrada_preco'] * (1 + alvo_pct_g))
                        bateu_stop_darvas = usar_stop_darvas_g and linha['Cruzou_Venda']
                        
                        if bateu_stop_fixo or bateu_alvo or bateu_stop_darvas:
                            if bateu_stop_fixo: preco_saida = trade_aberto['entrada_preco'] * (1 - stop_pct_g)
                            elif bateu_alvo: preco_saida = trade_aberto['entrada_preco'] * (1 + alvo_pct_g)
                            else: preco_saida = linha['Close']
                            
                            lucro_rs = capital_trade_global * ((preco_saida / trade_aberto['entrada_preco']) - 1)
                            trades_fechados.append({'lucro_rs': lucro_rs, 'pior_queda': trade_aberto['pior_queda']})
                            trade_aberto = None
                
                if trade_aberto is not None:
                    dias = (datetime.now().date() - trade_aberto['entrada_data'].date()).days
                    resultado = (df['Close'].iloc[-1] / trade_aberto['entrada_preco']) - 1
                    piso_atual = df['Darvas_Bottom'].iloc[-1]
                    andamento.append({"Ativo": ativo, "Entrada": trade_aberto['entrada_data'].strftime("%d/%m/%Y"), "Dias": dias, "PM": trade_aberto['entrada_preco'], "Cotação Atual": df['Close'].iloc[-1], "Stop (Piso)": piso_atual, "Resultado Atual": resultado})
                
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
        
        st.subheader(f"📦 Oportunidades Hoje (Rompimento da Caixa)")
        if oportunidades:
            df_op = pd.DataFrame(oportunidades)
            df_op['Preço Atual'] = df_op['Preço Atual'].apply(lambda x: f"R$ {x:.2f}")
            df_op['Teto Rompido'] = df_op['Teto Rompido'].apply(lambda x: f"R$ {x:.2f}")
            st.dataframe(df_op, use_container_width=True, hide_index=True)
        else: st.info("Nenhum ativo rompeu a caixa de Darvas no pregão atual.")

        st.subheader("⏳ Operações em Andamento (Trend Following Ativo)")
        if andamento:
            df_and = pd.DataFrame(andamento)
            df_and['PM'] = df_and['PM'].apply(lambda x: f"R$ {x:.2f}")
            df_and['Cotação Atual'] = df_and['Cotação Atual'].apply(lambda x: f"R$ {x:.2f}")
            df_and['Stop (Piso)'] = df_and['Stop (Piso)'].apply(lambda x: f"R$ {x:.2f}")
            st.dataframe(df_and.style.format({'Resultado Atual': "{:.2%}"}).map(lambda val: f"color: {'#00FFCC' if val > 0 else '#FF4D4D'}; font-weight: bold" if isinstance(val, float) else '', subset=['Resultado Atual']), use_container_width=True, hide_index=True)
        else: st.info("Nenhuma operação em aberto no momento.")

        st.subheader("🏆 Top 20 Histórico (Ranking Darvas Box)")
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
            periodo_caixa_rx = st.number_input("Tamanho da Caixa (Dias):", value=20, step=5, key="per_caixa_rx")
        with c2:
            periodo_rx = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=4, key="rx_per")
            capital_rx = st.number_input("Capital Base (R$):", value=10000.00, step=1000.00, key="rx_cap")
        with c3:
            tempo_rx = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="rx_tmp")
            usar_stop_darvas_rx = st.toggle("📦 Usar Piso como Stop", value=True, key="tg_stop_darvas_rx")
            # Adicionado Botão do Gráfico aqui para preservar sua estrutura
            mostrar_grafico_rx = st.toggle("📊 Mostrar Caixas no Gráfico", value=True, key="tg_graf_rx")
        with c4:
            usar_alvo_rx = st.toggle("🎯 Alvo Fixo", value=False, key="tg_alvo_rx")
            alvo_rx = st.number_input("Alvo (%):", value=15.00, step=1.00, key="rx_alvo", disabled=not usar_alvo_rx)
            usar_stop_rx = st.toggle("🛡️ Stop Fixo", value=False, key="tg_stop_rx")
            stop_rx = st.number_input("Stop Loss (%):", value=5.00, step=1.00, key="rx_stop", disabled=not usar_stop_rx)
            
        exibir_explicacao_estrategia()
            
    btn_rx = st.button("🔍 Rodar Laboratório Darvas", type="primary", use_container_width=True)
    
    if btn_rx:
        with st.spinner(f"Construindo as Caixas de {ativo_rx} via Bunker..."):
            try:
                # SUBSTITUÍDO tv.get_hist PELO BUNKER
                df_full = puxar_dados_blindados(ativo_rx, tempo_rx)
                
                if df_full is not None and len(df_full) > 50:
                    # Padronizando colunas para manter a compatibilidade com a sua lógica original
                    if isinstance(df_full.columns, pd.MultiIndex): df_full.columns = df_full.columns.get_level_values(0)
                    df_full.columns = [c.capitalize() for c in df_full.columns]
                    df_full = df_full.dropna()
                    
                    df_full = calcular_darvas(df_full, periodo_caixa=periodo_caixa_rx)
                    
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
                                
                                bateu_stop_fixo = usar_stop_rx and (linha['Low'] <= em_aberto['entrada_preco'] * (1 - stop_pct))
                                bateu_alvo = usar_alvo_rx and (linha['High'] >= em_aberto['entrada_preco'] * (1 + alvo_pct))
                                bateu_stop_darvas = usar_stop_darvas_rx and linha['Cruzou_Venda']
                                
                                if bateu_stop_fixo or bateu_alvo or bateu_stop_darvas:
                                    if bateu_stop_fixo:
                                        preco_saida = em_aberto['entrada_preco'] * (1 - stop_pct); motivo = "Stop Fixo"
                                    elif bateu_alvo:
                                        preco_saida = em_aberto['entrada_preco'] * (1 + alvo_pct); motivo = "Alvo (Gain)"
                                    else:
                                        preco_saida = linha['Close']; motivo = "Perdeu o Piso (Darvas)"

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
                            st.info(f"⏳ **{ativo_rx}: Trend Following Ativo** (Desde {em_aberto['entrada_data'].strftime('%d/%m/%Y')} a R$ {em_aberto['entrada_preco']:.2f}. Stop atual no Piso: R$ {df_ativo['Darvas_Bottom'].iloc[-1]:.2f})")
                        else:
                            st.success(f"✅ **{ativo_rx}: Aguardando Novo Rompimento de Caixa**")

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
                        # SUBSTITUÍDO: renderizar_grafico_tv PELO PLOTLY
                        corte_grafico = df_ativo.tail(250)
                        df_trades_plot = pd.DataFrame(trades_fechados) if trades_fechados else pd.DataFrame()
                        st.plotly_chart(plotar_darvas_plotly(corte_grafico, df_trades_plot, mostrar_grafico_rx), use_container_width=True)
                        st.info("💡 **Dica:** O gráfico acima desenha o Teto e o Piso da Caixa de Darvas. O rompimento do teto (linha verde) dispara a entrada.")
                    else:
                        st.error("Sem dados suficientes no período de corte.")
                else:
                    st.error("Não foi possível coletar dados do Bunker para este ativo.")
            except Exception as e:
                st.error(f"Erro no processamento via Bunker: {e}")
