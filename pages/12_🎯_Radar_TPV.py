import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np
import warnings
import sys
import os
from datetime import datetime

warnings.filterwarnings('ignore')

# ==========================================
# 1. IMPORTAÇÃO CENTRALIZADA DOS ATIVOS
# ==========================================
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from config_ativos import bdrs_elite, ibrx_selecao
except ImportError:
    st.error("❌ Arquivo 'config_ativos.py' não encontrado na raiz do projeto.")
    st.stop()

ativos_para_rastrear = sorted(list(set([a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)])))

# ==========================================
# 2. CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Radar TPV Elite", layout="wide", page_icon="🎯")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

st.title("🎯 Máquina Quantitativa: TPV (Tendência Preço/Volume)")

# Criação das Abas Principais
aba_radar, aba_individual = st.tabs(["🌐 Radar Global (Scanner)", "🔬 Raio-X Individual (Backtest)"])

# ==========================================
# 3. MOTOR MATEMÁTICO (FUNÇÕES)
# ==========================================
def calcular_tpv(df):
    if df.empty or len(df) < 60: return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = df.index.tz_localize(None)
    
    df['Retorno'] = df['Close'].pct_change()
    df['TPV'] = (df['Volume'] * df['Retorno']).cumsum()
    df['TPV_MA55'] = df['TPV'].rolling(window=55).mean()
    df['Cruzou_Compra'] = (df['TPV'].shift(1) <= df['TPV_MA55'].shift(1)) & (df['TPV'] > df['TPV_MA55'])
    df['Cruzou_Venda'] = (df['TPV'].shift(1) >= df['TPV_MA55'].shift(1)) & (df['TPV'] < df['TPV_MA55'])
    return df.dropna()

# ==========================================
# ABA 1: RADAR GLOBAL (O SCANNER)
# ==========================================
with aba_radar:
    st.markdown("Varredura completa buscando ativos que estão dando entrada agora.")
    
    with st.container(border=True):
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            lista_selecionada = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"])
            capital_trade_global = st.number_input("Capital por Trade (R$):", value=10000.00, step=1000.00, key="cap_global")
        with col_f2:
            usar_alvo_g = st.toggle("🎯 Habilitar Alvo (Take Profit)", value=True, key="tg_alvo_g")
            alvo_pct_g = st.number_input("Alvo (%):", value=5.00, step=0.50, key="val_alvo_g", disabled=not usar_alvo_g) / 100.0
        with col_f3:
            usar_stop_g = st.toggle("🛡️ Habilitar Stop Loss", value=False, key="tg_stop_g")
            stop_pct_g = st.number_input("Stop (%):", value=3.00, step=0.50, key="val_stop_g", disabled=not usar_stop_g) / 100.0
            tempo_grafico_global = st.selectbox("Tempo Gráfico:", ["1d (Diário)", "1wk (Semanal)"], key="tmp_global")
            int_global = "1d" if "1d" in tempo_grafico_global else "1wk"

    if lista_selecionada == "BDRs Elite": ativos_alvo = bdrs_elite
    elif lista_selecionada == "IBrX Seleção": ativos_alvo = ibrx_selecao
    else: ativos_alvo = bdrs_elite + ibrx_selecao
    ativos_alvo = sorted(list(set([a.replace('.SA', '') for a in ativos_alvo])))

    btn_iniciar_global = st.button("🚀 Iniciar Varredura Global", type="primary", use_container_width=True)

    if btn_iniciar_global:
        oportunidades, andamento = [], []
        p_bar = st.progress(0)
        s_text = st.empty()
        
        for i, ativo in enumerate(ativos_alvo):
            s_text.text(f"Varrendo: {ativo} ({i+1}/{len(ativos_alvo)})")
            p_bar.progress((i + 1) / len(ativos_alvo))
            try:
                df = yf.download(f"{ativo}.SA", period="2y", interval=int_global, progress=False)
                df = calcular_tpv(df)
                if df.empty: continue
                
                trade_aberto = None
                for j in range(len(df)):
                    linha = df.iloc[j]
                    data = df.index[j]
                    
                    if trade_aberto is None:
                        if linha['Cruzou_Compra']:
                            if j == len(df) - 1:
                                t_preco = df['Close'].iloc[-1] - df['Close'].iloc[-5]
                                t_tpv = df['TPV'].iloc[-1] - df['TPV'].iloc[-5]
                                div = "🚀 ALTA (Forte)" if (t_preco < 0 and t_tpv > 0) else "-"
                                oportunidades.append({"Ativo": ativo, "Preço Atual": linha['Close'], "Divergência (5p)": div})
                            else:
                                trade_aberto = {'entrada_data': data, 'entrada_preco': linha['Close'], 'pico': linha['Close'], 'pior_queda': 0.0}
                    else:
                        if linha['High'] > trade_aberto['pico']: trade_aberto['pico'] = linha['High']
                        dd_atual = (linha['Low'] / trade_aberto['pico']) - 1
                        if dd_atual < trade_aberto['pior_queda']: trade_aberto['pior_queda'] = dd_atual
                        
                        # Lógica de Saída (Alvo, Stop ou Indicador)
                        bateu_stop = usar_stop_g and (linha['Low'] <= trade_aberto['entrada_preco'] * (1 - stop_pct_g))
                        bateu_alvo = usar_alvo_g and (linha['High'] >= trade_aberto['entrada_preco'] * (1 + alvo_pct_g))
                        
                        if bateu_stop or bateu_alvo or linha['Cruzou_Venda']:
                            trade_aberto = None # Operação encerrada
                
                if trade_aberto is not None:
                    dias = (datetime.now().date() - trade_aberto['entrada_data'].date()).days
                    resultado = (df['Close'].iloc[-1] / trade_aberto['entrada_preco']) - 1
                    andamento.append({"Ativo": ativo, "Entrada": trade_aberto['entrada_data'].strftime("%d/%m/%Y"), "Dias": dias, "PM": trade_aberto['entrada_preco'], "Cotação Atual": df['Close'].iloc[-1], "Proj. Máx": trade_aberto['pior_queda'], "Resultado Atual": resultado})
            except: pass
        
        p_bar.empty(); s_text.empty()
        
        st.subheader("🚀 Oportunidades Hoje (Sinal Ativo)")
        if oportunidades:
            df_op = pd.DataFrame(oportunidades)
            df_op['Preço Atual'] = df_op['Preço Atual'].apply(lambda x: f"R$ {x:.2f}")
            st.dataframe(df_op, use_container_width=True, hide_index=True)
        else: st.info("Nenhum ativo disparou sinal de entrada no pregão atual.")

        st.subheader("⏳ Operações em Andamento (Aguardando Alvo/Venda)")
        if andamento:
            df_and = pd.DataFrame(andamento)
            df_and['PM'] = df_and['PM'].apply(lambda x: f"R$ {x:.2f}")
            df_and['Cotação Atual'] = df_and['Cotação Atual'].apply(lambda x: f"R$ {x:.2f}")
            df_and['Proj. Máx'] = df_and['Proj. Máx'].apply(lambda x: f"{x*100:.2f}%")
            st.dataframe(df_and.style.format({'Resultado Atual': "{:.2%}"}).map(lambda val: f"color: {'#00FFCC' if val > 0 else '#FF4D4D'}; font-weight: bold" if isinstance(val, float) else '', subset=['Resultado Atual']), use_container_width=True, hide_index=True)
        else: st.info("Nenhuma operação em aberto no momento.")

# ==========================================
# ABA 2: RAIO-X INDIVIDUAL (O LABORATÓRIO)
# ==========================================
with aba_individual:
    st.markdown("### 🔬 Raio-X Detalhado: Backtest & Status Atual")
    st.markdown("Veja o histórico de acertos e o status completo se o ativo estiver com operação aberta agora.")
    
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            ativo_rx = st.selectbox("Ativo (Ex: TSLA34):", ativos_para_rastrear, key="rx_ativo")
            capital_rx = st.number_input("Capital Base (R$):", value=10000.00, step=1000.00, key="rx_cap")
        with c2:
            usar_alvo_rx = st.toggle("🎯 Habilitar Alvo", value=True, key="tg_alvo_rx")
            alvo_rx = st.number_input("Alvo (%):", value=5.00, step=0.50, key="rx_alvo", disabled=not usar_alvo_rx)
        with c3:
            usar_stop_rx = st.toggle("🛡️ Habilitar Stop Loss", value=False, key="tg_stop_rx")
            stop_rx = st.number_input("Stop Loss (%):", value=3.00, step=0.50, key="rx_stop", disabled=not usar_stop_rx)
            
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            periodo_rx = st.selectbox("Período de Estudo:", ["1 Ano", "2 Anos", "5 Anos", "Máximo"], key="rx_per")
        with col_t2:
            tempo_rx = st.selectbox("Tempo Gráfico:", ["1d (Diário)", "1wk (Semanal)"], key="rx_tmp")
            
    btn_rx = st.button("🔍 Rodar Análise Completa", type="primary", use_container_width=True)
    
    if btn_rx:
        with st.spinner(f"Dissecando o histórico de {ativo_rx}..."):
            mapa_per = {"1 Ano": "1y", "2 Anos": "2y", "5 Anos": "5y", "Máximo": "max"}
            df_ativo = yf.download(f"{ativo_rx}.SA", period=mapa_per[periodo_rx], interval="1d" if "1d" in tempo_rx else "1wk", progress=False)
            df_ativo = calcular_tpv(df_ativo)
            
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
                        
                        # Análise de Saída (Conservadora: testa o stop antes do alvo se ambos baterem no mesmo candle)
                        bateu_stop = usar_stop_rx and (linha['Low'] <= em_aberto['entrada_preco'] * (1 - stop_pct))
                        bateu_alvo = usar_alvo_rx and (linha['High'] >= em_aberto['entrada_preco'] * (1 + alvo_pct))
                        sinal_venda = linha['Cruzou_Venda']
                        
                        if bateu_stop or bateu_alvo or sinal_venda:
                            if bateu_stop:
                                preco_saida = em_aberto['entrada_preco'] * (1 - stop_pct)
                                motivo = "Stop Loss"
                            elif bateu_alvo:
                                preco_saida = em_aberto['entrada_preco'] * (1 + alvo_pct)
                                motivo = "Alvo (Gain)"
                            else:
                                preco_saida = linha['Close']
                                motivo = "Indicador (Virada)"

                            lucro_pct = (preco_saida / em_aberto['entrada_preco']) - 1
                            lucro_rs = capital_rx * lucro_pct
                            duracao = (data - em_aberto['entrada_data']).days
                            
                            trades_fechados.append({
                                'Entrada': em_aberto['entrada_data'].strftime("%d/%m/%Y"),
                                'Saída': data.strftime("%d/%m/%Y"),
                                'Duração': duracao,
                                'Motivo Saída': motivo,
                                'Lucro (R$)': lucro_rs,
                                'Queda Máx': em_aberto['pior_queda'],
                                'Situação': "Gain ✅" if lucro_pct > 0 else "Loss ❌"
                            })
                            em_aberto = None

                # 1. STATUS ATUAL
                if em_aberto is not None:
                    st.info(f"⏳ **{ativo_rx}: Em Operação** (Posicionado desde {em_aberto['entrada_data'].strftime('%d/%m/%Y')} a R$ {em_aberto['entrada_preco']:.2f})")
                else:
                    if df_ativo['Cruzou_Compra'].iloc[-1]:
                        st.success(f"🚀 **{ativo_rx}: SINAL DE COMPRA ATIVADO HOJE!**")
                    else:
                        st.success(f"✅ **{ativo_rx}: Aguardando Novo Sinal de Entrada**")

                st.markdown(f"### 📊 Resultado Consolidado: {ativo_rx}")
                
                # 2. MÉTRICAS ESTATÍSTICAS
                if trades_fechados:
                    df_trades = pd.DataFrame(trades_fechados)
                    lucro_total = df_trades['Lucro (R$)'].sum()
                    duracao_media = df_trades['Duração'].mean()
                    pior_queda_hist = df_trades['Queda Máx'].min()
                    
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Lucro Total", f"R$ {lucro_total:.2f}")
                    m2.metric("Duração Média", f"{duracao_media:.1f} dias")
                    m3.metric("Operações Fechadas", len(df_trades))
                    m4.metric("Pior Queda", f"{pior_queda_hist*100:.2f}%")
                    
                    # 3. TABELA DE HISTÓRICO
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
                    st.warning("Nenhuma operação concluída no período selecionado para este ativo.")

                # 4. GRÁFICO INTERATIVO TRADINGVIEW (CORRIGIDO A ALTURA)
                st.markdown("---")
                st.markdown(f"### 📈 Gráfico Interativo: {ativo_rx}")
                html_tv = f"""
                <div class="tradingview-widget-container" style="height:600px;width:100%">
                  <div class="tradingview-widget-container__widget" style="height:calc(100% - 32px);width:100%"></div>
                  <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
                  {{
                  "autosize": true,
                  "symbol": "BMFBOVESPA:{ativo_rx}",
                  "interval": "D",
                  "timezone": "America/Sao_Paulo",
                  "theme": "dark",
                  "style": "1",
                  "locale": "br",
                  "enable_publishing": false,
                  "hide_top_toolbar": false,
                  "hide_legend": false,
                  "save_image": false,
                  "container_id": "tradingview_rx"
                }}
                  </script>
                </div>
                """
                components.html(html_tv, height=600)
            else:
                st.error("Sem dados suficientes para gerar o backtest deste ativo.")
