import streamlit as st
from tvDatafeed import TvDatafeed, Interval
import streamlit.components.v1 as components
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
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
# 2. CONFIGURAÇÃO DA PÁGINA & TVDATAFEED
# ==========================================
st.set_page_config(page_title="Fura-Teto Elite", layout="wide", page_icon="⬆️")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

# Conexão com o TradingView
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

st.title("⬆️ Máquina Quantitativa: Fura-Teto & Fura-Chão")
st.markdown("O rastreador de Price Action puro. Compre rompimentos de máximas diárias e defenda na perda de mínimas.")

aba_radar, aba_individual = st.tabs(["🌐 Radar Global (Scanner & Top 20)", "🔬 Raio-X Individual (Backtest)"])

# ==========================================
# 3. MOTOR MATEMÁTICO (FURA-TETO)
# ==========================================
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

def exibir_explicacao_estrategia():
    st.info("⬆️ **O Setup (Fura-Teto / Fura-Chão):** Estratégia de Price Action clássica popularizada no Brasil. \n\n🟢 **Gatilho de Compra (Fura-Teto):** Ocorre no momento em que o preço atual ultrapassa a máxima exata do candle anterior (Teto). \n\n🔴 **Gatilho de Venda/Stop (Fura-Chão):** Ocorre quando o preço atual perde a mínima exata do candle anterior (Chão). \n\n⚠️ *Nota Visual:* O TradingView não desenha as escadinhas do Fura-Teto na tela, mas o motor do nosso backtest e radar global calcula os rompimentos matematicamente.")

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
            usar_filtro_mm_g = st.toggle("📈 Filtro Tendência (Preço > MM21)", value=True, key="tg_mm_g")
        with col_f3:
            tempo_grafico_global = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="tmp_global")
        with col_f4:
            periodo_busca_g = st.selectbox("Período de Busca:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=4, key="per_busca_g")

        exibir_explicacao_estrategia()

        st.markdown("**2. Gestão de Risco e Saída**")
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            capital_trade_global = st.number_input("Capital por Trade (R$):", value=10000.00, step=1000.00, key="cap_global")
        with col_p2:
            usar_fura_chao_g = st.toggle("📉 Stop Fura-Chão (Mínima Ant.)", value=True, key="tg_fura_chao_g")
            st.caption("O Stop sobe seguindo a mínima de cada candle.")
        with col_p3:
            usar_alvo_g = st.toggle("🎯 Alvo Fixo (Take Profit)", value=False, key="tg_alvo_g")
            alvo_pct_g = st.number_input("Alvo (%):", value=10.00, step=1.00, key="val_alvo_g", disabled=not usar_alvo_g) / 100.0

    if lista_selecionada == "BDRs Elite": ativos_alvo = bdrs_elite
    elif lista_selecionada == "IBrX Seleção": ativos_alvo = ibrx_selecao
    else: ativos_alvo = bdrs_elite + ibrx_selecao
    ativos_alvo = sorted(list(set([a.replace('.SA', '') for a in ativos_alvo])))

    btn_iniciar_global = st.button("🚀 Iniciar Varredura Fura-Teto (tvDatafeed)", type="primary", use_container_width=True)

    if btn_iniciar_global:
        intervalo_tv = tradutor_intervalo.get(tempo_grafico_global, Interval.in_daily)
        
        oportunidades, andamento, historico = [], [], []
        p_bar = st.progress(0)
        s_text = st.empty()
        
        for i, ativo in enumerate(ativos_alvo):
            s_text.text(f"Mapeando Rompimentos: {ativo} ({i+1}/{len(ativos_alvo)})")
            p_bar.progress((i + 1) / len(ativos_alvo))
            try:
                df_full = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=5000)
                if df_full is None or len(df_full) < 30: continue

                df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                
                # Matemática Fura Teto / Fura Chão
                df_full['Fura_Teto'] = df_full['High'].shift(1)
                df_full['Fura_Chao'] = df_full['Low'].shift(1)
                df_full['MM21'] = ta.sma(df_full['Close'], length=21)
                
                df_full = df_full.dropna()
                
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
                
                df_reset = df.reset_index()
                col_data = df_reset.columns[0]
                
                for j in range(1, len(df_reset)):
                    linha_atual = df_reset.iloc[j]
                    linha_ant = df_reset.iloc[j-1]
                    
                    if trade_aberto is None:
                        # Gatilho Compra: Máxima atual rompeu a máxima anterior
                        rompeu_teto = linha_atual['High'] > linha_atual['Fura_Teto']
                        tendencia_ok = (linha_ant['Close'] > linha_ant['MM21']) if usar_filtro_mm_g else True
                        
                        if rompeu_teto and tendencia_ok:
                            if j == len(df_reset) - 1: # Sinal de Hoje
                                oportunidades.append({"Ativo": ativo, "Sinal": "Rompendo Teto 🚀", "Preço Atual": linha_atual['Close'], "Teto Rompido": linha_atual['Fura_Teto']})
                            else:
                                preco_ent = max(linha_atual['Open'], linha_atual['Fura_Teto'])
                                trade_aberto = {'entrada_data': linha_atual[col_data], 'entrada_preco': preco_ent, 'pior_queda': 0.0}
                    else:
                        dd_atual = (linha_atual['Low'] / trade_aberto['entrada_preco']) - 1
                        if dd_atual < trade_aberto['pior_queda']: trade_aberto['pior_queda'] = dd_atual
                        
                        bateu_stop = usar_fura_chao_g and (linha_atual['Low'] < linha_atual['Fura_Chao'])
                        bateu_alvo = usar_alvo_g and (linha_atual['High'] >= trade_aberto['entrada_preco'] * (1 + alvo_pct_g))
                        
                        if bateu_stop or bateu_alvo:
                            if bateu_stop: preco_saida = min(linha_atual['Open'], linha_atual['Fura_Chao'])
                            else: preco_saida = trade_aberto['entrada_preco'] * (1 + alvo_pct_g)
                            
                            lucro_rs = capital_trade_global * ((preco_saida / trade_aberto['entrada_preco']) - 1)
                            trades_fechados.append({'lucro_rs': lucro_rs, 'pior_queda': trade_aberto['pior_queda']})
                            trade_aberto = None
                
                if trade_aberto is not None:
                    dias = (datetime.now().date() - trade_aberto['entrada_data'].date()).days
                    resultado = (df['Close'].iloc[-1] / trade_aberto['entrada_preco']) - 1
                    chao_atual = df['Fura_Chao'].iloc[-1]
                    andamento.append({"Ativo": ativo, "Entrada": trade_aberto['entrada_data'].strftime("%d/%m/%Y"), "Dias": dias, "PM": trade_aberto['entrada_preco'], "Cotação Atual": df['Close'].iloc[-1], "Stop Fura-Chão": chao_atual, "Resultado Atual": resultado})
                
                if trades_fechados:
                    total_trades = len(trades_fechados)
                    lucro_total = sum(t['lucro_rs'] for t in trades_fechados)
                    pior_dd = min(t['pior_queda'] for t in trades_fechados)
                    investimento = capital_trade_global * total_trades
                    historico.append({"Ativo": ativo, "Trades": total_trades, "Pior Queda": pior_dd, "Investimento": investimento, "Lucro R$": lucro_total, "Resultado": lucro_total / investimento if investimento > 0 else 0})
            except Exception as e: 
                pass
            time.sleep(0.05)
        
        p_bar.empty(); s_text.empty()
        
        st.subheader(f"⬆️ Oportunidades Hoje (Fura-Teto)")
        if oportunidades:
            df_op = pd.DataFrame(oportunidades)
            df_op['Preço Atual'] = df_op['Preço Atual'].apply(lambda x: f"R$ {x:.2f}")
            df_op['Teto Rompido'] = df_op['Teto Rompido'].apply(lambda x: f"R$ {x:.2f}")
            st.dataframe(df_op, use_container_width=True, hide_index=True)
        else: st.info("Nenhum ativo rompeu a máxima anterior no pregão atual.")

        st.subheader("⏳ Operações em Andamento (Conduzindo no Fura-Chão)")
        if andamento:
            df_and = pd.DataFrame(andamento)
            df_and['PM'] = df_and['PM'].apply(lambda x: f"R$ {x:.2f}")
            df_and['Cotação Atual'] = df_and['Cotação Atual'].apply(lambda x: f"R$ {x:.2f}")
            df_and['Stop Fura-Chão'] = df_and['Stop Fura-Chão'].apply(lambda x: f"R$ {x:.2f}")
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
            usar_filtro_mm_rx = st.toggle("📈 Filtro Tendência (> MM21)", value=True, key="tg_mm_rx")
        with c2:
            periodo_rx = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=4, key="rx_per")
            capital_rx = st.number_input("Capital Base (R$):", value=10000.00, step=1000.00, key="rx_cap")
        with c3:
            tempo_rx = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="rx_tmp")
            usar_fura_chao_rx = st.toggle("📉 Conduzir pelo Fura-Chão", value=True, key="tg_fura_chao_rx")
        with c4:
            usar_alvo_rx = st.toggle("🎯 Habilitar Alvo", value=False, key="tg_alvo_rx")
            alvo_rx = st.number_input("Alvo (%):", value=10.00, step=1.00, key="rx_alvo", disabled=not usar_alvo_rx)
            
        exibir_explicacao_estrategia()
            
    btn_rx = st.button("🔍 Rodar Laboratório Fura-Teto", type="primary", use_container_width=True)
    
    if btn_rx:
        intervalo_tv_rx = tradutor_intervalo.get(tempo_rx, Interval.in_daily)
        with st.spinner(f"Calculando rompimentos sucessivos de {ativo_rx} via tvDatafeed..."):
            try:
                df_full = tv.get_hist(symbol=ativo_rx.replace('.SA', ''), exchange='BMFBOVESPA', interval=intervalo_tv_rx, n_bars=5000)
                
                if df_full is not None and len(df_full) > 30:
                    df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                    
                    df_full['Fura_Teto'] = df_full['High'].shift(1)
                    df_full['Fura_Chao'] = df_full['Low'].shift(1)
                    df_full['MM21'] = ta.sma(df_full['Close'], length=21)
                    df_full = df_full.dropna()
                    
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
                        trades_fechados = []
                        em_aberto = None
                        
                        df_reset = df_ativo.reset_index()
                        col_data = df_reset.columns[0]

                        for i in range(1, len(df_reset)):
                            linha_atual = df_reset.iloc[i]
                            linha_ant = df_reset.iloc[i-1]
                            
                            if em_aberto is None:
                                rompeu_teto = linha_atual['High'] > linha_atual['Fura_Teto']
                                tendencia_ok = (linha_ant['Close'] > linha_ant['MM21']) if usar_filtro_mm_rx else True
                                
                                if rompeu_teto and tendencia_ok:
                                    preco_ent = max(linha_atual['Open'], linha_atual['Fura_Teto'])
                                    em_aberto = {'entrada_data': linha_atual[col_data], 'entrada_preco': preco_ent, 'pico': linha_atual['Close'], 'pior_queda': 0.0}
                            else:
                                if linha_atual['High'] > em_aberto['pico']: em_aberto['pico'] = linha_atual['High']
                                dd = (linha_atual['Low'] / em_aberto['pico']) - 1
                                if dd < em_aberto['pior_queda']: em_aberto['pior_queda'] = dd
                                
                                bateu_stop = usar_fura_chao_rx and (linha_atual['Low'] < linha_atual['Fura_Chao'])
                                bateu_alvo = usar_alvo_rx and (linha_atual['High'] >= em_aberto['entrada_preco'] * (1 + alvo_pct))
                                
                                if bateu_stop or bateu_alvo:
                                    if bateu_stop:
                                        preco_saida = min(linha_atual['Open'], linha_atual['Fura_Chao'])
                                        motivo = "Perdeu o Chão"
                                    elif bateu_alvo:
                                        preco_saida = em_aberto['entrada_preco'] * (1 + alvo_pct)
                                        motivo = "Alvo Fixo (Gain)"

                                    lucro_pct = (preco_saida / em_aberto['entrada_preco']) - 1
                                    lucro_rs = capital_rx * lucro_pct
                                    duracao = (linha_atual[col_data] - em_aberto['entrada_data']).days
                                    trades_fechados.append({
                                        'Entrada': em_aberto['entrada_data'].strftime("%d/%m/%Y"), 
                                        'Saída': linha_atual[col_data].strftime("%d/%m/%Y"), 
                                        'Motivo Saída': motivo, 
                                        'Duração': duracao, 
                                        'Lucro (R$)': lucro_rs, 
                                        'Queda Máx': em_aberto['pior_queda'], 
                                        'Situação': "Gain ✅" if lucro_pct > 0 else "Loss ❌"
                                    })
                                    em_aberto = None

                        if em_aberto is not None:
                            chao_atual = df_ativo['Fura_Chao'].iloc[-1]
                            st.info(f"⏳ **{ativo_rx}: Em Operação** (Comprado desde {em_aberto['entrada_data'].strftime('%d/%m/%Y')} a R$ {em_aberto['entrada_preco']:.2f}. Stop atual no Fura-Chão: R$ {chao_atual:.2f})")
                        else:
                            st.success(f"✅ **{ativo_rx}: Aguardando Novo Fura-Teto**")

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
                    st.error("Sem dados suficientes para processar o indicador via tvDatafeed.")
            except Exception as e:
                st.error(f"Falha na coleta de dados: {e}")
