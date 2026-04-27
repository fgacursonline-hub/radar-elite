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
st.set_page_config(page_title="Agulhada do Didi Elite", layout="wide", page_icon="🪡")

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

st.title("🪡 Máquina Quantitativa: Agulhada do Didi (Padrão Original)")
st.markdown("O setup direcional mais famoso do Brasil. Exige que as médias passem pelo 'buraco da agulha' antes de explodir.")

aba_radar, aba_individual = st.tabs(["🌐 Radar Global (Scanner & Top 20)", "🔬 Raio-X Individual (Backtest)"])

# ==========================================
# 3. MOTOR MATEMÁTICO (DIDI ORIGINAL - PROFIT)
# ==========================================
def calcular_didi(df, usar_adx=True, limite_adx=20):
    if df.empty or len(df) < 60: return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = df.index.tz_localize(None)
    
    # Médias Móveis Simples
    df['SMA3'] = df['Close'].rolling(window=3).mean()
    df['SMA8'] = df['Close'].rolling(window=8).mean()
    df['SMA20'] = df['Close'].rolling(window=20).mean()
    
    # Filtro ADX (Mede a força da tendência)
    adx_df = df.ta.adx(length=14)
    if adx_df is not None:
        col_adx = [c for c in adx_df.columns if c.startswith('ADX')][0]
        df['ADX'] = adx_df[col_adx]
    else:
        df['ADX'] = 0

    # =========================================================
    # A AGULHADA ORIGINAL (BOLOLÔ + ABERTURA)
    # =========================================================
    
    # 1. O Bololô (Esmagamento): A distância entre a maior e a menor média deve ser minúscula (ex: menor que 1.5%)
    max_ma = df[['SMA3', 'SMA8', 'SMA20']].max(axis=1)
    min_ma = df[['SMA3', 'SMA8', 'SMA20']].min(axis=1)
    df['Esmagamento'] = ((max_ma - min_ma) / df['SMA8']) < 0.015
    
    # Verifica se esse "nó" aconteceu hoje ou nos últimos 3 dias
    teve_bololo = df['Esmagamento'] | df['Esmagamento'].shift(1) | df['Esmagamento'].shift(2) | df['Esmagamento'].shift(3)
    
    # 2. O Alinhamento Perfeito: Média 3 apontada pra cima, Média 8 no meio, Média 20 pra baixo
    alinhamento_alta = (df['SMA3'] > df['SMA8']) & (df['SMA8'] > df['SMA20'])
    
    # 3. O Gatilho: As médias estavam bagunçadas ontem, mas assumiram a formação de alta HOJE
    alinhamento_alta_prev = (df['SMA3'].shift(1) > df['SMA8'].shift(1)) & (df['SMA8'].shift(1) > df['SMA20'].shift(1))
    
    condicao_agulhada = teve_bololo & alinhamento_alta & (~alinhamento_alta_prev)
    
    # Aplica o filtro ADX dinâmico
    if usar_adx:
        df['Cruzou_Compra'] = condicao_agulhada & (df['ADX'] >= limite_adx)
    else:
        df['Cruzou_Compra'] = condicao_agulhada
    
    # Lógica de Saída Clássica (Quando a Média Rápida de 3 fura a de 8 para baixo)
    df['Cruzou_Venda'] = (df['SMA3'] < df['SMA8']) & (df['SMA3'].shift(1) >= df['SMA8'].shift(1))
    
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

def exibir_explicacao_estrategia():
    st.info("🪡 **A Estratégia (Agulhada Padrão Brasil):** A matemática foi programada para agir como no ProfitChart. O robô audita o 'Buraco da Agulha'.\n\n🟢 **Gatilho de Compra:** Primeiro, as 3 médias (3, 8 e 20) precisam se embolar, ficando a menos de 1.5% de distância umas das outras. Em seguida, elas precisam se abrir na ordem exata de alta: **Média 3 > Média 8 > Média 20** (com a Média 8 cortando pelo meio). O filtro ADX (>20) ajuda a evitar agulhadas sem força direcional.\n\n🔴 **Gatilho de Saída (Defesa):** O trade encerra assim que a Média Rápida (3) voltar a cruzar a Média (8) para baixo, indicando perda de fôlego.")

# ==========================================
# ABA 1: RADAR GLOBAL (SCANNER + TOP 20)
# ==========================================
with aba_radar:
    with st.container(border=True):
        st.markdown("**1. Parâmetros Operacionais**")
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        with col_f1:
            lista_selecionada = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"])
        with col_f2:
            tempo_grafico_global = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="tmp_global")
        with col_f3:
            periodo_busca_g = st.selectbox("Período de Busca:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=4, key="per_busca_g")
        with col_f4:
            capital_trade_global = st.number_input("Capital por Trade (R$):", value=10000.00, step=1000.00, key="cap_global")
            
        exibir_explicacao_estrategia()

        st.markdown("**2. Calibração (Filtros e Gestão)**")
        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        with col_p1:
            usar_adx_g = st.toggle("📈 Filtro ADX Ativo", value=True, key="tg_adx_g")
            limite_adx_g = st.number_input("Nível ADX (>):", value=20, step=1, key="val_adx_g", disabled=not usar_adx_g)
        with col_p2:
            st.write("")
        with col_p3:
            usar_alvo_g = st.toggle("🎯 Habilitar Alvo", value=True, key="tg_alvo_g")
            alvo_pct_g = st.number_input("Alvo (%):", value=8.00, step=0.50, key="val_alvo_g", disabled=not usar_alvo_g) / 100.0
        with col_p4:
            usar_stop_g = st.toggle("🛡️ Habilitar Stop Loss", value=True, key="tg_stop_g")
            stop_pct_g = st.number_input("Stop (%):", value=4.00, step=0.50, key="val_stop_g", disabled=not usar_stop_g) / 100.0

    if lista_selecionada == "BDRs Elite": ativos_alvo = bdrs_elite
    elif lista_selecionada == "IBrX Seleção": ativos_alvo = ibrx_selecao
    else: ativos_alvo = bdrs_elite + ibrx_selecao
    ativos_alvo = sorted(list(set([a.replace('.SA', '') for a in ativos_alvo])))

    btn_iniciar_global = st.button("🚀 Iniciar Varredura de Agulhadas", type="primary", use_container_width=True)

    if btn_iniciar_global:
        intervalo_tv = tradutor_intervalo.get(tempo_grafico_global, Interval.in_daily)
        
        oportunidades, andamento, historico = [], [], []
        p_bar = st.progress(0)
        s_text = st.empty()
        
        for i, ativo in enumerate(ativos_alvo):
            s_text.text(f"Mapeando Agulhadas: {ativo} ({i+1}/{len(ativos_alvo)})")
            p_bar.progress((i + 1) / len(ativos_alvo))
            try:
                df_full = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=5000)
                if df_full is None or len(df_full) < 60: continue

                df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                df_full = df_full.dropna()
                
                df_full = calcular_didi(df_full, usar_adx=usar_adx_g, limite_adx=limite_adx_g)
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
                                oportunidades.append({"Ativo": ativo, "Preço Atual": linha['Close'], "ADX": linha['ADX']})
                            else:
                                trade_aberto = {'entrada_data': data, 'entrada_preco': linha['Close'], 'pico': linha['Close'], 'pior_queda': 0.0}
                    else:
                        if linha['High'] > trade_aberto['pico']: trade_aberto['pico'] = linha['High']
                        dd_atual = (linha['Low'] / trade_aberto['pico']) - 1
                        if dd_atual < trade_aberto['pior_queda']: trade_aberto['pior_queda'] = dd_atual
                        
                        bateu_stop = usar_stop_g and (linha['Low'] <= trade_aberto['entrada_preco'] * (1 - stop_pct_g))
                        bateu_alvo = usar_alvo_g and (linha['High'] >= trade_aberto['entrada_preco'] * (1 + alvo_pct_g))
                        
                        if bateu_stop or bateu_alvo or linha['Cruzou_Venda']:
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
            except Exception as e: 
                pass
            time.sleep(0.05)
        
        p_bar.empty(); s_text.empty()
        
        st.subheader("🪡 Oportunidades Hoje (Sinal Ativo)")
        if oportunidades:
            df_op = pd.DataFrame(oportunidades)
            df_op['Preço Atual'] = df_op['Preço Atual'].apply(lambda x: f"R$ {x:.2f}")
            df_op['ADX'] = df_op['ADX'].apply(lambda x: f"{x:.1f} (Válido)" if x >= limite_adx_g else f"{x:.1f} (Abaixo)")
            st.dataframe(df_op, use_container_width=True, hide_index=True)
        else: 
            st.info(f"Nenhum ativo disparou Agulhada de Alta {'com ADX > ' + str(limite_adx_g) if usar_adx_g else ''} no pregão atual.")

        st.subheader("⏳ Operações em Andamento (Aguardando Alvo/Venda)")
        if andamento:
            df_and = pd.DataFrame(andamento)
            df_and['PM'] = df_and['PM'].apply(lambda x: f"R$ {x:.2f}")
            df_and['Cotação Atual'] = df_and['Cotação Atual'].apply(lambda x: f"R$ {x:.2f}")
            df_and['Proj. Máx'] = df_and['Proj. Máx'].apply(lambda x: f"{x*100:.2f}%")
            st.dataframe(df_and.style.format({'Resultado Atual': "{:.2%}"}).map(lambda val: f"color: {'#00FFCC' if val > 0 else '#FF4D4D'}; font-weight: bold" if isinstance(val, float) else '', subset=['Resultado Atual']), use_container_width=True, hide_index=True)
        else: st.info("Nenhuma operação em aberto no momento.")

        st.subheader(f"📊 Top 20 Histórico ({tradutor_periodo_nome.get(periodo_busca_g, periodo_busca_g)})")
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
            usar_adx_rx = st.toggle("📈 Filtro ADX Ativo", value=True, key="tg_adx_rx")
            limite_adx_rx = st.number_input("Nível ADX (>):", value=20, step=1, key="val_adx_rx", disabled=not usar_adx_rx)
        with c4:
            usar_alvo_rx = st.toggle("🎯 Habilitar Alvo", value=True, key="tg_alvo_rx")
            alvo_rx = st.number_input("Alvo (%):", value=8.00, step=0.50, key="rx_alvo", disabled=not usar_alvo_rx)
            usar_stop_rx = st.toggle("🛡️ Habilitar Stop Loss", value=True, key="tg_stop_rx")
            stop_rx = st.number_input("Stop Loss (%):", value=4.00, step=0.50, key="rx_stop", disabled=not usar_stop_rx)
            
        exibir_explicacao_estrategia()
            
    btn_rx = st.button("🔍 Dissecando Agulhadas", type="primary", use_container_width=True)
    
    if btn_rx:
        intervalo_tv_rx = tradutor_intervalo.get(tempo_rx, Interval.in_daily)
        with st.spinner(f"Processando Didi Index para {ativo_rx} via tvDatafeed..."):
            try:
                df_full = tv.get_hist(symbol=ativo_rx.replace('.SA', ''), exchange='BMFBOVESPA', interval=intervalo_tv_rx, n_bars=5000)
                
                if df_full is not None and len(df_full) > 60:
                    df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                    df_full = df_full.dropna()
                    
                    df_full = calcular_didi(df_full, usar_adx=usar_adx_rx, limite_adx=limite_adx_rx)
                    
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
                                        motivo = "Perdeu MM8 (Virada)"

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

                        if em_aberto is not None:
                            st.info(f"⏳ **{ativo_rx}: Em Operação** (Posicionado desde {em_aberto['entrada_data'].strftime('%d/%m/%Y')} a R$ {em_aberto['entrada_preco']:.2f})")
                        else:
                            if df_ativo['Cruzou_Compra'].iloc[-1]:
                                st.success(f"🪡 **{ativo_rx}: AGULHADA DE COMPRA ATIVADA HOJE!** (ADX >= {limite_adx_rx if usar_adx_rx else 'Desativado'})")
                            else:
                                st.success(f"✅ **{ativo_rx}: Aguardando Formação da Agulhada**")

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
                            st.warning("Nenhuma Agulhada concluída no período com os parâmetros selecionados.")

                        st.divider()
                        st.markdown(f"### 📈 Gráfico Interativo: {ativo_rx}")
                        renderizar_grafico_tv(f"BMFBOVESPA:{ativo_rx}")
                    else:
                        st.error("Sem dados suficientes no período de corte.")
                else:
                    st.error("Não foi possível coletar dados do TradingView para este ativo.")
            except Exception as e:
                st.error(f"Erro no processamento via tvDatafeed: {e}")
