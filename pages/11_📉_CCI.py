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
st.set_page_config(page_title="CCI Elite", layout="wide", page_icon="📉")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

# Conexão com o TradingView (Igual ao seu IFR)
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

st.title("📉 Máquina Quantitativa: CCI (TradingView Data)")
st.markdown("Identifique força direcional, reversões e momentum explosivo com dados diretos do TradingView.")

aba_radar, aba_individual = st.tabs(["🌐 Radar Global (Scanner & Top 20)", "🔬 Raio-X Individual (Backtest)"])

# ==========================================
# 3. MOTOR MATEMÁTICO BLINDADO (CCI)
# ==========================================
def calcular_cci(df, periodo=14, limite=100, estrategia="Cruzamento da Linha Zero"):
    if df.empty or len(df) < periodo: return pd.DataFrame()
    
    tp = (df['High'] + df['Low'] + df['Close']) / 3.0
    sma = tp.rolling(window=periodo).mean()
    
    def mad(x):
        return np.mean(np.abs(x - np.mean(x)))
        
    mad_roll = tp.rolling(window=periodo).apply(mad, raw=True)
    mad_roll = mad_roll.replace(0, np.nan) 
    
    df['CCI'] = (tp - sma) / (0.015 * mad_roll)
    df.dropna(subset=['CCI'], inplace=True)
    
    df['Cruzou_Compra'] = False
    df['Cruzou_Venda'] = False
    
    if "Linha Zero" in estrategia or "2" in estrategia:
        df['Cruzou_Compra'] = (df['CCI'].shift(1) <= 0) & (df['CCI'] > 0)
        df['Cruzou_Venda'] = (df['CCI'].shift(1) >= 0) & (df['CCI'] < 0)
        
    elif "Saindo" in estrategia or "1" in estrategia:
        df['Cruzou_Compra'] = (df['CCI'].shift(1) <= -limite) & (df['CCI'] > -limite)
        df['Cruzou_Venda'] = (df['CCI'].shift(1) >= limite) & (df['CCI'] < limite)
        
    elif "Entrando" in estrategia or "3" in estrategia:
        df['Cruzou_Compra'] = (df['CCI'].shift(1) <= limite) & (df['CCI'] > limite)
        df['Cruzou_Venda'] = (df['CCI'].shift(1) >= limite) & (df['CCI'] < limite)
        
    return df

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

def exibir_explicacao_estrategia(estrategia):
    if "Linha Zero" in estrategia:
        st.info("🧭 **Direcional:** Compra quando o CCI cruza a Linha Zero para CIMA. Sai da operação se perder a Linha Zero ou bater no Alvo.")
    elif "Saindo" in estrategia:
        st.info("🎣 **Reversão Clássica:** Compra quando o CCI foge da sobrevenda (fura os -100 para CIMA). Sai da operação se bater lá no teto (+100 e cair) ou bater no Alvo.")
    elif "Entrando" in estrategia:
        st.info("🚀 **Momentum Explosivo:** Compra na explosão de força (quando rompe os +100 para CIMA). Sai rápido se perder os +100 para baixo (fim do combustível) ou bater no Alvo.")

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
            estrategia_g = st.selectbox("Estratégia Operacional CCI:", [
                "1 - Saindo dos Extremos (Reversão Clássica)", 
                "2 - Cruzamento da Linha Zero (Direcional)", 
                "3 - Entrando nos Extremos (Momentum/Força)"
            ], key="est_g")
        with col_f3:
            tempo_grafico_global = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="tmp_global")
        with col_f4:
            periodo_busca_g = st.selectbox("Período de Busca:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=4, key="per_busca_g")
            
        exibir_explicacao_estrategia(estrategia_g)

        st.markdown("**2. Calibração e Gestão de Risco**")
        col_p1, col_p2, col_p3, col_p4, col_p5 = st.columns(5)
        with col_p1:
            periodo_g = st.number_input("Período do CCI:", value=14, step=1, key="per_g")
        with col_p2:
            limite_g = st.number_input("Limites (±):", value=100, step=10, key="lim_g")
        with col_p3:
            capital_trade_global = st.number_input("Capital/Trade (R$):", value=10000.00, step=1000.00, key="cap_global")
        with col_p4:
            usar_alvo_g = st.toggle("🎯 Alvo (Take Profit)", value=True, key="tg_alvo_g")
            alvo_pct_g = st.number_input("Alvo (%):", value=8.00, step=0.50, key="val_alvo_g", disabled=not usar_alvo_g) / 100.0
        with col_p5:
            usar_stop_g = st.toggle("🛡️ Stop Loss", value=True, key="tg_stop_g")
            stop_pct_g = st.number_input("Stop (%):", value=4.00, step=0.50, key="val_stop_g", disabled=not usar_stop_g) / 100.0

    if lista_selecionada == "BDRs Elite": ativos_alvo = bdrs_elite
    elif lista_selecionada == "IBrX Seleção": ativos_alvo = ibrx_selecao
    else: ativos_alvo = bdrs_elite + ibrx_selecao
    ativos_alvo = sorted(list(set([a.replace('.SA', '') for a in ativos_alvo])))

    btn_iniciar_global = st.button("🚀 Iniciar Varredura do CCI (tvDatafeed)", type="primary", use_container_width=True)

    if btn_iniciar_global:
        intervalo_tv = tradutor_intervalo.get(tempo_grafico_global, Interval.in_daily)
        
        oportunidades, andamento, historico = [], [], []
        p_bar = st.progress(0)
        s_text = st.empty()
        
        for i, ativo in enumerate(ativos_alvo):
            s_text.text(f"Mapeando Canais via TV: {ativo} ({i+1}/{len(ativos_alvo)})")
            p_bar.progress((i + 1) / len(ativos_alvo))
            try:
                # === A MÁGICA DO TVDATAFEED AQUI ===
                df_full = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=5000)
                if df_full is None or len(df_full) < 50: continue

                df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                df_full = df_full.dropna()
                
                df_full = calcular_cci(df_full, periodo=periodo_g, limite=limite_g, estrategia=estrategia_g)
                if df_full.empty: continue
                
                # Aplica o filtro de data (Período de Busca)
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
                                oportunidades.append({"Ativo": ativo, "Sinal": "Gatilho de Compra 🟢", "Preço Atual": linha['Close'], "CCI Atual": linha['CCI']})
                            else:
                                trade_aberto = {'entrada_data': data, 'entrada_preco': linha['Close'], 'pico': linha['Close'], 'pior_queda': 0.0}
                    else:
                        if linha['High'] > trade_aberto['pico']: trade_aberto['pico'] = linha['High']
                        dd_atual = (linha['Low'] / trade_aberto['pico']) - 1
                        if dd_atual < trade_aberto['pior_queda']: trade_aberto['pior_queda'] = dd_atual
                        
                        bateu_stop = usar_stop_g and (linha['Low'] <= trade_aberto['entrada_preco'] * (1 - stop_pct_g))
                        bateu_alvo = usar_alvo_g and (linha['High'] >= trade_aberto['entrada_preco'] * (1 + alvo_pct_g))
                        sinal_venda = linha['Cruzou_Venda'] 
                        
                        if bateu_stop or bateu_alvo or sinal_venda:
                            preco_saida = trade_aberto['entrada_preco'] * (1 - stop_pct_g) if bateu_stop else (trade_aberto['entrada_preco'] * (1 + alvo_pct_g) if bateu_alvo else linha['Close'])
                            lucro_rs = capital_trade_global * ((preco_saida / trade_aberto['entrada_preco']) - 1)
                            trades_fechados.append({'lucro_rs': lucro_rs, 'pior_queda': trade_aberto['pior_queda']})
                            trade_aberto = None
                
                if trade_aberto is not None:
                    dias = (datetime.now().date() - trade_aberto['entrada_data'].date()).days
                    resultado = (df['Close'].iloc[-1] / trade_aberto['entrada_preco']) - 1
                    andamento.append({"Ativo": ativo, "Entrada": trade_aberto['entrada_data'].strftime('%d/%m/%Y'), "Dias": dias, "PM": trade_aberto['entrada_preco'], "Cotação Atual": df['Close'].iloc[-1], "CCI Atual": df['CCI'].iloc[-1], "Resultado Atual": resultado})
                
                if trades_fechados:
                    total_trades = len(trades_fechados)
                    lucro_total = sum(t['lucro_rs'] for t in trades_fechados)
                    pior_dd = min(t['pior_queda'] for t in trades_fechados)
                    investimento = capital_trade_global * total_trades
                    historico.append({"Ativo": ativo, "Trades": total_trades, "Pior Queda": pior_dd, "Investimento": investimento, "Lucro R$": lucro_total, "Resultado": lucro_total / investimento if investimento > 0 else 0})
            
            except Exception as e: 
                pass
            time.sleep(0.05) # Pausa leve do seu IFR para não engasgar o tvDatafeed
        
        p_bar.empty(); s_text.empty()
        
        st.subheader(f"📉 Oportunidades Hoje ({estrategia_g.split('-')[1].strip()})")
        if oportunidades:
            df_op = pd.DataFrame(oportunidades)
            df_op['Preço Atual'] = df_op['Preço Atual'].apply(lambda x: f"R$ {x:.2f}")
            df_op['CCI Atual'] = df_op['CCI Atual'].apply(lambda x: f"{x:.2f}")
            st.dataframe(df_op, use_container_width=True, hide_index=True)
        else: st.info("Nenhum ativo disparou sinal no pregão atual com a estratégia escolhida.")

        st.subheader("⏳ Operações em Andamento (Aguardando Alvo/Venda)")
        if andamento:
            df_and = pd.DataFrame(andamento)
            df_and['PM'] = df_and['PM'].apply(lambda x: f"R$ {x:.2f}")
            df_and['Cotação Atual'] = df_and['Cotação Atual'].apply(lambda x: f"R$ {x:.2f}")
            df_and['CCI Atual'] = df_and['CCI Atual'].apply(lambda x: f"{x:.2f}")
            st.dataframe(df_and.style.format({'Resultado Atual': "{:.2%}"}).map(lambda val: f"color: {'#00FFCC' if val > 0 else '#FF4D4D'}; font-weight: bold" if isinstance(val, float) else '', subset=['Resultado Atual']), use_container_width=True, hide_index=True)
        else: st.info("Nenhuma operação em aberto no momento.")

        st.subheader(f"🏆 Top 20 Histórico ({tradutor_periodo_nome.get(periodo_busca_g, periodo_busca_g)})")
        if historico:
            df_hist = pd.DataFrame(historico).sort_values(by="Lucro R$", ascending=False).head(20)
            df_hist['Pior Queda'] = df_hist['Pior Queda'].apply(lambda x: f"{x*100:.2f}%")
            df_hist['Investimento'] = df_hist['Investimento'].apply(lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
            st.dataframe(df_hist.style.format({'Lucro R$': "R$ {:,.2f}", 'Resultado': "{:.2%}"}).map(lambda val: f"color: {'#00FFCC' if val > 0 else '#FF4D4D'}" if isinstance(val, str) else '', subset=['Lucro R$', 'Resultado']), use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ Nenhum trade encontrado. O histórico foi baixado via tvDatafeed.")

# ==========================================
# ABA 2: RAIO-X INDIVIDUAL (O LABORATÓRIO)
# ==========================================
with aba_individual:
    with st.container(border=True):
        st.markdown("**1. Setup e Capital**")
        c1, c2, c3 = st.columns(3)
        with c1:
            ativo_rx = st.selectbox("Ativo (Ex: TSLA34):", ativos_para_rastrear, key="rx_ativo")
            estrategia_rx = st.selectbox("Estratégia Operacional CCI:", [
                "1 - Saindo dos Extremos (Reversão Clássica)", 
                "2 - Cruzamento da Linha Zero (Direcional)", 
                "3 - Entrando nos Extremos (Momentum/Força)"
            ], key="est_rx")
        with c2:
            periodo_rx = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=4, key="rx_per")
            capital_rx = st.number_input("Capital Base (R$):", value=10000.00, step=1000.00, key="rx_cap")
        with c3:
            tempo_rx = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="rx_tmp")
            
        exibir_explicacao_estrategia(estrategia_rx)
            
        st.markdown("**2. Calibração e Gestão**")
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1: periodo_cci_rx = st.number_input("Período do CCI:", value=14, step=1, key="per_cci_rx")
        with col_m2: limite_rx = st.number_input("Limites (±):", value=100, step=10, key="lim_rx")
        with col_m3:
            usar_alvo_rx = st.toggle("🎯 Habilitar Alvo", value=True, key="tg_alvo_rx")
            alvo_rx = st.number_input("Alvo (%):", value=8.00, step=0.50, key="rx_alvo", disabled=not usar_alvo_rx)
        with col_m4:
            usar_stop_rx = st.toggle("🛡️ Habilitar Stop Loss", value=True, key="tg_stop_rx")
            stop_rx = st.number_input("Stop Loss (%):", value=4.00, step=0.50, key="rx_stop", disabled=not usar_stop_rx)
            
    btn_rx = st.button("🔍 Rodar Laboratório CCI", type="primary", use_container_width=True)
    
    if btn_rx:
        intervalo_tv_rx = tradutor_intervalo.get(tempo_rx, Interval.in_daily)
        with st.spinner(f"Dissecando as ondas de {ativo_rx} via tvDatafeed..."):
            try:
                df_full = tv.get_hist(symbol=ativo_rx.replace('.SA', ''), exchange='BMFBOVESPA', interval=intervalo_tv_rx, n_bars=5000)
                
                if df_full is not None and len(df_full) > 50:
                    df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                    df_full = df_full.dropna()
                    
                    df_full = calcular_cci(df_full, periodo=periodo_cci_rx, limite=limite_rx, estrategia=estrategia_rx)
                    
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
                                        preco_saida = em_aberto['entrada_preco'] * (1 - stop_pct); motivo = "Stop Loss"
                                    elif bateu_alvo:
                                        preco_saida = em_aberto['entrada_preco'] * (1 + alvo_pct); motivo = "Alvo Fixo (Gain)"
                                    else:
                                        preco_saida = linha['Close']; motivo = "Sinal CCI (Venda)"

                                    lucro_pct = (preco_saida / em_aberto['entrada_preco']) - 1
                                    lucro_rs = capital_rx * lucro_pct
                                    duracao = (data - em_aberto['entrada_data']).days
                                    trades_fechados.append({
                                        'Entrada': em_aberto['entrada_data'].strftime('%d/%m/%Y'), 
                                        'Saída': data.strftime('%d/%m/%Y'), 
                                        'Motivo Saída': motivo, 
                                        'Duração': duracao, 
                                        'Lucro (R$)': lucro_rs, 
                                        'Queda Máx': em_aberto['pior_queda'], 
                                        'Situação': "Gain ✅" if lucro_pct > 0 else "Loss ❌"
                                    })
                                    em_aberto = None

                        if em_aberto is not None:
                            st.info(f"⏳ **{ativo_rx}: Em Operação** (Sinal CCI | Desde {em_aberto['entrada_data'].strftime('%d/%m/%Y')} a R$ {em_aberto['entrada_preco']:.2f})")
                        else:
                            st.success(f"✅ **{ativo_rx}: Aguardando Novo Gatilho CCI**")

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
                        st.info("💡 **Dica:** No gráfico acima, clique em 'Indicadores' e adicione o 'Commodity Channel Index' para visualizar as linhas zero e os limites 100/-100.")
                else:
                    st.error("Sem dados suficientes para calcular o CCI via tvDatafeed.")
            except Exception as e:
                st.error(f"Falha na coleta de dados: {e}")
