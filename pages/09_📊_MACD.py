import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import pandas_ta as ta
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
st.set_page_config(page_title="MACD Elite", layout="wide", page_icon="📊")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

st.title("📊 Máquina Quantitativa: MACD")
st.markdown("Rastreamento de Cruzamentos e Divergências com calibração de parâmetros (MME Rápida, Lenta e Sinal).")

aba_radar, aba_individual = st.tabs(["🌐 Radar Global (Scanner & Top 20)", "🔬 Raio-X Individual (Backtest)"])

# ==========================================
# 3. MOTOR MATEMÁTICO (MACD)
# ==========================================
def calcular_macd(df, fast=12, slow=26, signal=9):
    if df.empty or len(df) < slow + signal: return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = df.index.tz_localize(None)
    
    # Cálculo do MACD usando pandas_ta
    macd_df = df.ta.macd(fast=fast, slow=slow, signal=signal)
    if macd_df is None: return pd.DataFrame()
    
    col_macd = f"MACD_{fast}_{slow}_{signal}"
    col_hist = f"MACDh_{fast}_{slow}_{signal}"
    col_sig = f"MACDs_{fast}_{slow}_{signal}"
    
    df['MACD_Line'] = macd_df[col_macd]
    df['MACD_Signal'] = macd_df[col_sig]
    df['MACD_Hist'] = macd_df[col_hist]
    
    # Lógica 1: Cruzamento Clássico (Linha MACD cruza Sinal para cima)
    df['Cruzou_Compra'] = (df['MACD_Line'].shift(1) <= df['MACD_Signal'].shift(1)) & (df['MACD_Line'] > df['MACD_Signal'])
    df['Cruzou_Venda'] = (df['MACD_Line'].shift(1) >= df['MACD_Signal'].shift(1)) & (df['MACD_Line'] < df['MACD_Signal'])
    
    # Lógica 2: Divergência de Alta (Preço cai nos últimos 5 dias, mas Histograma sobe indicando exaustão da venda)
    tendencia_preco_caindo = df['Close'] < df['Close'].shift(5)
    tendencia_hist_subindo = df['MACD_Hist'] > df['MACD_Hist'].shift(5)
    histograma_ganhando_forca = df['MACD_Hist'] > df['MACD_Hist'].shift(1) # Barra atual maior que a anterior
    
    df['Divergencia_Alta'] = tendencia_preco_caindo & tendencia_hist_subindo & histograma_ganhando_forca & (df['MACD_Hist'] < 0)
    
    return df.dropna()

def renderizar_grafico_tv(symbol):
    html_code = f"""
    <div class="tradingview-widget-container">
      <div id="tv_chart_{symbol.replace(':', '')}" style="height: 600px; width: 100%;"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget(
      {{
      "autosize": true,
      "symbol": "{symbol}",
      "interval": "D",
      "timezone": "America/Sao_Paulo",
      "theme": "dark",
      "style": "1",
      "locale": "br",
      "enable_publishing": false,
      "hide_top_toolbar": false,
      "hide_legend": false,
      "save_image": false,
      "container_id": "tv_chart_{symbol.replace(':', '')}"
    }}
      );
      </script>
    </div>
    """
    components.html(html_code, height=600)

# ==========================================
# ABA 1: RADAR GLOBAL (SCANNER + TOP 20)
# ==========================================
with aba_radar:
    with st.container(border=True):
        st.markdown("**1. Parâmetros da Varredura**")
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        with col_f1:
            lista_selecionada = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"])
        with col_f2:
            gatilho_g = st.selectbox("Gatilho Operacional:", ["Tudo (Cruzamento + Divergência)", "Somente Cruzamento", "Somente Divergência"])
        with col_f3:
            capital_trade_global = st.number_input("Capital por Trade (R$):", value=10000.00, step=1000.00, key="cap_global")
        with col_f4:
            tempo_grafico_global = st.selectbox("Tempo Gráfico:", ["1d (Diário)", "1wk (Semanal)"], key="tmp_global")
            int_global = "1d" if "1d" in tempo_grafico_global else "1wk"

        st.markdown("**2. Calibração do MACD e Gestão de Risco**")
        col_p1, col_p2, col_p3, col_p4, col_p5 = st.columns(5)
        with col_p1:
            mme_rapida_g = st.number_input("MME Rápida:", value=12, step=1, key="fast_g")
        with col_p2:
            mme_lenta_g = st.number_input("MME Lenta:", value=26, step=1, key="slow_g")
        with col_p3:
            mme_sinal_g = st.number_input("MME Sinal:", value=9, step=1, key="sig_g")
        with col_p4:
            usar_alvo_g = st.toggle("🎯 Alvo Ativo", value=True, key="tg_alvo_g")
            alvo_pct_g = st.number_input("Alvo (%):", value=8.00, step=0.50, key="val_alvo_g", disabled=not usar_alvo_g) / 100.0
        with col_p5:
            usar_stop_g = st.toggle("🛡️ Stop Ativo", value=True, key="tg_stop_g")
            stop_pct_g = st.number_input("Stop (%):", value=4.00, step=0.50, key="val_stop_g", disabled=not usar_stop_g) / 100.0

    if lista_selecionada == "BDRs Elite": ativos_alvo = bdrs_elite
    elif lista_selecionada == "IBrX Seleção": ativos_alvo = ibrx_selecao
    else: ativos_alvo = bdrs_elite + ibrx_selecao
    ativos_alvo = sorted(list(set([a.replace('.SA', '') for a in ativos_alvo])))

    btn_iniciar_global = st.button("🚀 Iniciar Varredura MACD", type="primary", use_container_width=True)

    if btn_iniciar_global:
        oportunidades, andamento, historico = [], [], []
        p_bar = st.progress(0)
        s_text = st.empty()
        
        for i, ativo in enumerate(ativos_alvo):
            s_text.text(f"Decodificando MACD: {ativo} ({i+1}/{len(ativos_alvo)})")
            p_bar.progress((i + 1) / len(ativos_alvo))
            try:
                df = yf.download(f"{ativo}.SA", period="2y", interval=int_global, progress=False)
                df = calcular_macd(df, fast=mme_rapida_g, slow=mme_lenta_g, signal=mme_sinal_g)
                if df.empty: continue
                
                trade_aberto = None
                trades_fechados = []
                
                for j in range(len(df)):
                    linha = df.iloc[j]
                    data = df.index[j]
                    
                    # Definição do Sinal baseado na escolha do usuário
                    sinal_entrada = False
                    tipo_sinal = ""
                    if gatilho_g == "Somente Cruzamento":
                        sinal_entrada = linha['Cruzou_Compra']
                        tipo_sinal = "Cruzamento 📈"
                    elif gatilho_g == "Somente Divergência":
                        sinal_entrada = linha['Divergencia_Alta']
                        tipo_sinal = "Divergência ⚠️"
                    else: # Tudo
                        if linha['Cruzou_Compra']:
                            sinal_entrada = True; tipo_sinal = "Cruzamento 📈"
                        elif linha['Divergencia_Alta']:
                            sinal_entrada = True; tipo_sinal = "Divergência ⚠️"
                    
                    if trade_aberto is None:
                        if sinal_entrada:
                            if j == len(df) - 1:
                                oportunidades.append({"Ativo": ativo, "Tipo de Sinal": tipo_sinal, "Preço Atual": linha['Close'], "Histograma": linha['MACD_Hist']})
                            else:
                                trade_aberto = {'entrada_data': data, 'entrada_preco': linha['Close'], 'pico': linha['Close'], 'pior_queda': 0.0}
                    else:
                        if linha['High'] > trade_aberto['pico']: trade_aberto['pico'] = linha['High']
                        dd_atual = (linha['Low'] / trade_aberto['pico']) - 1
                        if dd_atual < trade_aberto['pior_queda']: trade_aberto['pior_queda'] = dd_atual
                        
                        bateu_stop = usar_stop_g and (linha['Low'] <= trade_aberto['entrada_preco'] * (1 - stop_pct_g))
                        bateu_alvo = usar_alvo_g and (linha['High'] >= trade_aberto['entrada_preco'] * (1 + alvo_pct_g))
                        sinal_venda = linha['Cruzou_Venda'] # MACD cruzou pra baixo
                        
                        if bateu_stop or bateu_alvo or sinal_venda:
                            preco_saida = trade_aberto['entrada_preco'] * (1 - stop_pct_g) if bateu_stop else (trade_aberto['entrada_preco'] * (1 + alvo_pct_g) if bateu_alvo else linha['Close'])
                            lucro_rs = capital_trade_global * ((preco_saida / trade_aberto['entrada_preco']) - 1)
                            trades_fechados.append({'lucro_rs': lucro_rs, 'pior_queda': trade_aberto['pior_queda']})
                            trade_aberto = None
                
                if trade_aberto is not None:
                    dias = (datetime.now().date() - trade_aberto['entrada_data'].date()).days
                    resultado = (df['Close'].iloc[-1] / trade_aberto['entrada_preco']) - 1
                    andamento.append({"Ativo": ativo, "Entrada": trade_aberto['entrada_data'].strftime("%d/%m/%Y"), "Dias": dias, "PM": trade_aberto['entrada_preco'], "Cotação Atual": df['Close'].iloc[-1], "Proj. Máx": trade_aberto['pior_queda'], "Resultado Atual": resultado})
                
                if trades_fechados:
                    total_trades = len(trades_fechados)
                    lucro_total = sum(t['lucro_rs'] for t in trades_fechados)
                    pior_dd = min(t['pior_queda'] for t in trades_fechados)
                    investimento = capital_trade_global * total_trades
                    historico.append({"Ativo": ativo, "Trades": total_trades, "Pior Queda": pior_dd, "Investimento": investimento, "Lucro R$": lucro_total, "Resultado": lucro_total / investimento if investimento > 0 else 0})
            except: pass
        
        p_bar.empty(); s_text.empty()
        
        st.subheader(f"📊 Oportunidades Hoje ({gatilho_g})")
        if oportunidades:
            df_op = pd.DataFrame(oportunidades)
            df_op['Preço Atual'] = df_op['Preço Atual'].apply(lambda x: f"R$ {x:.2f}")
            df_op['Histograma'] = df_op['Histograma'].apply(lambda x: f"{x:.4f}")
            st.dataframe(df_op, use_container_width=True, hide_index=True)
        else: st.info("Nenhum ativo disparou sinal no pregão atual com os parâmetros escolhidos.")

        st.subheader("⏳ Operações em Andamento (Aguardando Alvo/Venda)")
        if andamento:
            df_and = pd.DataFrame(andamento)
            df_and['PM'] = df_and['PM'].apply(lambda x: f"R$ {x:.2f}")
            df_and['Cotação Atual'] = df_and['Cotação Atual'].apply(lambda x: f"R$ {x:.2f}")
            df_and['Proj. Máx'] = df_and['Proj. Máx'].apply(lambda x: f"{x*100:.2f}%")
            st.dataframe(df_and.style.format({'Resultado Atual': "{:.2%}"}).map(lambda val: f"color: {'#00FFCC' if val > 0 else '#FF4D4D'}; font-weight: bold" if isinstance(val, float) else '', subset=['Resultado Atual']), use_container_width=True, hide_index=True)
        else: st.info("Nenhuma operação em aberto no momento.")

        st.subheader("🏆 Top 20 Histórico (Ranking MACD)")
        if historico:
            df_hist = pd.DataFrame(historico).sort_values(by="Lucro R$", ascending=False).head(20)
            df_hist['Pior Queda'] = df_hist['Pior Queda'].apply(lambda x: f"{x*100:.2f}%")
            df_hist['Investimento'] = df_hist['Investimento'].apply(lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
            st.dataframe(df_hist.style.format({'Lucro R$': "R$ {:,.2f}", 'Resultado': "{:.2%}"}).map(lambda val: f"color: {'#00FFCC' if val > 0 else '#FF4D4D'}" if isinstance(val, str) else '', subset=['Lucro R$', 'Resultado']), use_container_width=True, hide_index=True)

# ==========================================
# ABA 2: RAIO-X INDIVIDUAL (O LABORATÓRIO)
# ==========================================
with aba_individual:
    with st.container(border=True):
        st.markdown("**1. Setup e Capital**")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            ativo_rx = st.selectbox("Ativo (Ex: TSLA34):", ativos_para_rastrear, key="rx_ativo")
            gatilho_rx = st.selectbox("Gatilho Operacional:", ["Tudo (Cruzamento + Divergência)", "Somente Cruzamento", "Somente Divergência"], key="gat_rx")
        with c2:
            periodo_rx = st.selectbox("Período de Estudo:", ["1 Ano", "2 Anos", "5 Anos", "Máximo"], key="rx_per", index=1)
            capital_rx = st.number_input("Capital Base (R$):", value=10000.00, step=1000.00, key="rx_cap")
        with c3:
            tempo_rx = st.selectbox("Tempo Gráfico:", ["1d (Diário)", "1wk (Semanal)"], key="rx_tmp")
            usar_alvo_rx = st.toggle("🎯 Habilitar Alvo", value=True, key="tg_alvo_rx")
            alvo_rx = st.number_input("Alvo (%):", value=8.00, step=0.50, key="rx_alvo", disabled=not usar_alvo_rx)
        with c4:
            st.markdown("<br>", unsafe_allow_html=True) # Espaçador
            usar_stop_rx = st.toggle("🛡️ Habilitar Stop Loss", value=True, key="tg_stop_rx")
            stop_rx = st.number_input("Stop Loss (%):", value=4.00, step=0.50, key="rx_stop", disabled=not usar_stop_rx)
            
        st.markdown("**2. Calibração das Médias Exponenciais (MACD)**")
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            mme_rapida_rx = st.number_input("MME Rápida:", value=12, step=1, key="fast_rx")
        with col_m2:
            mme_lenta_rx = st.number_input("MME Lenta:", value=26, step=1, key="slow_rx")
        with col_m3:
            mme_sinal_rx = st.number_input("MME Sinal:", value=9, step=1, key="sig_rx")
            
    btn_rx = st.button("🔍 Rodar Laboratório MACD", type="primary", use_container_width=True)
    
    if btn_rx:
        with st.spinner(f"Processando matriz MACD para {ativo_rx}..."):
            mapa_per = {"1 Ano": "1y", "2 Anos": "2y", "5 Anos": "5y", "Máximo": "max"}
            df_ativo = yf.download(f"{ativo_rx}.SA", period=mapa_per[periodo_rx], interval="1d" if "1d" in tempo_rx else "1wk", progress=False)
            df_ativo = calcular_macd(df_ativo, fast=mme_rapida_rx, slow=mme_lenta_rx, signal=mme_sinal_rx)
            
            if not df_ativo.empty:
                alvo_pct = alvo_rx / 100.0
                stop_pct = stop_rx / 100.0
                trades_fechados = []
                em_aberto = None
                
                for i in range(len(df_ativo)):
                    linha = df_ativo.iloc[i]
                    data = df_ativo.index[i]
                    
                    sinal_entrada = False
                    tipo_sinal = ""
                    if gatilho_rx == "Somente Cruzamento":
                        sinal_entrada = linha['Cruzou_Compra']; tipo_sinal = "Cruzamento 📈"
                    elif gatilho_rx == "Somente Divergência":
                        sinal_entrada = linha['Divergencia_Alta']; tipo_sinal = "Divergência ⚠️"
                    else:
                        if linha['Cruzou_Compra']: sinal_entrada = True; tipo_sinal = "Cruzamento 📈"
                        elif linha['Divergencia_Alta']: sinal_entrada = True; tipo_sinal = "Divergência ⚠️"
                    
                    if em_aberto is None:
                        if sinal_entrada:
                            em_aberto = {'entrada_data': data, 'entrada_preco': linha['Close'], 'pico': linha['Close'], 'pior_queda': 0.0, 'sinal': tipo_sinal}
                    else:
                        if linha['High'] > em_aberto['pico']: em_aberto['pico'] = linha['High']
                        dd = (linha['Low'] / em_aberto['pico']) - 1
                        if dd < em_aberto['pior_queda']: em_aberto['pior_queda'] = dd
                        
                        bateu_stop = usar_stop_rx and (linha['Low'] <= em_aberto['entrada_preco'] * (1 - stop_pct))
                        bateu_alvo = usar_alvo_rx and (linha['High'] >= em_aberto['entrada_preco'] * (1 + alvo_pct))
                        sinal_venda = linha['Cruzou_Venda']
                        
                        if bateu_stop or bateu_alvo or sinal_venda:
                            if bateu_stop:
                                preco_saida = em_aberto['entrada_preco'] * (1 - stop_pct); motivo = "Stop Loss"
                            elif bateu_alvo:
                                preco_saida = em_aberto['entrada_preco'] * (1 + alvo_pct); motivo = "Alvo (Gain)"
                            else:
                                preco_saida = linha['Close']; motivo = "Cruzou pra Baixo"

                            lucro_pct = (preco_saida / em_aberto['entrada_preco']) - 1
                            lucro_rs = capital_rx * lucro_pct
                            duracao = (data - em_aberto['entrada_data']).days
                            trades_fechados.append({
                                'Entrada': em_aberto['entrada_data'].strftime("%d/%m/%Y"), 
                                'Sinal (In)': em_aberto['sinal'],
                                'Saída': data.strftime("%d/%m/%Y"), 
                                'Motivo Saída': motivo, 
                                'Duração': duracao, 
                                'Lucro (R$)': lucro_rs, 
                                'Queda Máx': em_aberto['pior_queda'], 
                                'Situação': "Gain ✅" if lucro_pct > 0 else "Loss ❌"
                            })
                            em_aberto = None

                if em_aberto is not None:
                    st.info(f"⏳ **{ativo_rx}: Em Operação** (Sinal: {em_aberto['sinal']} | Desde {em_aberto['entrada_data'].strftime('%d/%m/%Y')} a R$ {em_aberto['entrada_preco']:.2f})")
                else:
                    st.success(f"✅ **{ativo_rx}: Aguardando Novo Sinal de Entrada**")

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
                renderizar_grafico_tv(f"BMFBOVESPA:{ativo_rx}")
            else:
                st.error("Sem dados suficientes para processar o MACD.")
