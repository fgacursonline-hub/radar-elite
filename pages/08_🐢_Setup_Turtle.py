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
st.set_page_config(page_title="Turtle Strategy Elite", layout="wide", page_icon="🐢")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

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

st.title("🐢 Máquina Quantitativa: Turtle Trading System")
st.markdown("O lendário sistema de seguimento de tendência baseado em Canais de Donchian e Volatilidade (ATR).")

aba_radar, aba_individual = st.tabs(["🌐 Radar Global (Scanner & Top 20)", "🔬 Raio-X Individual (Backtest)"])

# ==========================================
# 3. MOTOR MATEMÁTICO (TURTLE + ATR RAIZ)
# ==========================================
def calcular_turtle(df, periodo_donchian=20, mult_atr=2.0):
    if df.empty or len(df) < periodo_donchian + 20: return pd.DataFrame()
    
    # 1. Canais de Donchian (Gatilho)
    df['Donchian_High'] = df['High'].rolling(window=periodo_donchian).max().shift(1)
    df['Donchian_Low'] = df['Low'].rolling(window=periodo_donchian).min().shift(1)
    
    # 2. ATR para o Stop Móvel
    df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=20)
    
    # 3. Lógica de Sinais
    df['Cruzou_Compra'] = (df['Close'] > df['Donchian_High']) & (df['Close'].shift(1) <= df['Donchian_High'])
    df['Cruzou_Venda'] = (df['Close'] < df['Donchian_Low']) & (df['Close'].shift(1) >= df['Donchian_Low'])
    
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
    st.info("🐢 **O Sistema Turtle:** Estratégia de 'Trend Following' agressiva que captura grandes movimentos de mercado. \n\n🟢 **Gatilho de Compra:** Ocorre quando o preço rompe a máxima dos últimos 20 dias (Canal de Donchian Superior). \n\n🔴 **Saída e Condução:** O sistema utiliza a volatilidade do ativo (ATR) para projetar um Stop Móvel. Na compra, o stop sobe à medida que o preço avança, protegendo o lucro e encerrando o trade apenas quando a tendência perde força.")

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
            tempo_grafico_global = st.selectbox("Tempo Gráfico:", ['1d', '1wk'], index=0, format_func=lambda x: {'1d': 'Diário', '1wk': 'Semanal'}[x], key="tmp_global")
        with col_f3:
            periodo_busca_g = st.selectbox("Período de Busca:", options=['1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=2, key="per_busca_g")
        with col_f4:
            capital_trade_global = st.number_input("Capital por Trade (R$):", value=10000.00, step=1000.00, key="cap_global")

        exibir_explicacao_estrategia()

        st.markdown("**2. Calibração e Riscos**")
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            per_donchian_g = st.number_input("Período Donchian:", value=20, step=1, key="don_g")
        with col_p2:
            mult_atr_g = st.number_input("Multiplicador ATR (Stop):", value=2.0, step=0.1, key="atr_g")
        with col_p3:
            usar_alvo_g = st.toggle("🎯 Usar Alvo de % (Opcional)", value=False, key="tg_alvo_g")
            alvo_pct_g = st.number_input("Alvo (%):", value=20.00, step=1.00, key="val_alvo_g", disabled=not usar_alvo_g) / 100.0

    if lista_selecionada == "BDRs Elite": ativos_alvo = bdrs_elite
    elif lista_selecionada == "IBrX Seleção": ativos_alvo = ibrx_selecao
    else: ativos_alvo = bdrs_elite + ibrx_selecao
    ativos_alvo = sorted(list(set([a.replace('.SA', '') for a in ativos_alvo])))

    btn_iniciar_global = st.button("🚀 Iniciar Varredura Turtle (tvDatafeed)", type="primary", use_container_width=True)

    if btn_iniciar_global:
        intervalo_tv = tradutor_intervalo.get(tempo_grafico_global, Interval.in_daily)
        oportunidades, andamento, historico = [], [], []
        p_bar = st.progress(0); s_text = st.empty()
        
        for i, ativo in enumerate(ativos_alvo):
            s_text.text(f"Mapeando Tendências via TV: {ativo} ({i+1}/{len(ativos_alvo)})")
            p_bar.progress((i + 1) / len(ativos_alvo))
            try:
                df_full = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=5000)
                if df_full is None or len(df_full) < 60: continue
                df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                df_full = calcular_turtle(df_full, periodo_donchian=per_donchian_g, mult_atr=mult_atr_g)
                
                data_atual_dt = df_full.index[-1]
                delta = {'1y': 1, '2y': 2, '5y': 5}.get(periodo_busca_g, 10)
                data_corte = data_atual_dt - pd.DateOffset(years=delta) if periodo_busca_g != 'max' else df_full.index[0]
                df = df_full[df_full.index >= data_corte].copy()
                
                trade_aberto = None
                trades_fechados = []
                
                for j in range(len(df)):
                    linha = df.iloc[j]
                    if trade_aberto is None:
                        if linha['Cruzou_Compra']:
                            if j == len(df) - 1:
                                oportunidades.append({"Ativo": ativo, "Preço Atual": linha['Close'], "ATR (20)": f"R$ {linha['ATR']:.2f}"})
                            else:
                                trade_aberto = {'entrada_data': df.index[j], 'entrada_preco': linha['Close'], 'stop_movel': linha['Close'] - (mult_atr_g * linha['ATR'])}
                    else:
                        # Atualiza Stop Móvel (Só sobe)
                        novo_stop = linha['Close'] - (mult_atr_g * linha['ATR'])
                        if novo_stop > trade_aberto['stop_movel']: trade_aberto['stop_movel'] = novo_stop
                        
                        bateu_stop = linha['Low'] <= trade_aberto['stop_movel']
                        bateu_alvo = usar_alvo_g and (linha['High'] >= trade_aberto['entrada_preco'] * (1 + alvo_pct_g))
                        
                        if bateu_stop or bateu_alvo:
                            preco_sai = trade_aberto['stop_movel'] if bateu_stop else trade_aberto['entrada_preco'] * (1 + alvo_pct_g)
                            lucro_rs = capital_trade_global * ((preco_sai / trade_aberto['entrada_preco']) - 1)
                            trades_fechados.append({'lucro_rs': lucro_rs})
                            trade_aberto = None
                
                if trade_aberto:
                    res = (df['Close'].iloc[-1] / trade_aberto['entrada_preco']) - 1
                    andamento.append({"Ativo": ativo, "Entrada": trade_aberto['entrada_data'].strftime("%d/%m/%Y"), "PM": trade_aberto['entrada_preco'], "Cotação": df['Close'].iloc[-1], "Stop Atual": trade_aberto['stop_movel'], "Resultado": res})
                
                if trades_fechados:
                    luc_tot = sum(t['lucro_rs'] for t in trades_fechados)
                    historico.append({"Ativo": ativo, "Trades": len(trades_fechados), "Lucro R$": luc_tot, "Resultado": luc_tot / (capital_trade_global * len(trades_fechados))})
            except: pass
            time.sleep(0.02)
            
        p_bar.empty(); s_text.empty()
        
        st.subheader("🚀 Rompimentos de Donchian Hoje")
        if oportunidades: st.dataframe(pd.DataFrame(oportunidades), use_container_width=True, hide_index=True)
        else: st.info("Nenhum ativo rompeu a máxima de 20 dias hoje.")

        st.subheader("⏳ Surfando Tendências (Operações em Aberto)")
        if andamento:
            df_and = pd.DataFrame(andamento)
            df_and['Stop Atual'] = df_and['Stop Atual'].apply(lambda x: f"R$ {x:.2f}")
            st.dataframe(df_and.style.format({'Resultado': "{:.2%}"}).map(lambda val: f"color: {'#00FFCC' if val > 0 else '#FF4D4D'}; font-weight: bold" if isinstance(val, float) else '', subset=['Resultado']), use_container_width=True, hide_index=True)
        else: st.info("Nenhuma operação Turtle em andamento.")

        st.subheader("🏆 Melhores Resultados Históricos (Tendência)")
        if historico:
            df_hist = pd.DataFrame(historico).sort_values(by="Lucro R$", ascending=False).head(20)
            st.dataframe(df_hist.style.format({'Lucro R$': "R$ {:,.2f}", 'Resultado': "{:.2%}"}), use_container_width=True, hide_index=True)

# ==========================================
# ABA 2: RAIO-X INDIVIDUAL
# ==========================================
with aba_individual:
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            ativo_rx = st.selectbox("Ativo:", ativos_para_rastrear, key="rx_ativo")
            periodo_rx = st.selectbox("Período:", options=['1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=2, key="rx_per")
        with c2:
            capital_rx = st.number_input("Capital Base (R$):", value=10000.00, step=1000.00, key="rx_cap")
            tempo_rx = st.selectbox("Tempo Gráfico:", ['1d', '1wk'], index=0, key="rx_tmp")
        with c3:
            per_donchian_rx = st.number_input("Período Donchian:", value=20, key="don_rx")
            mult_atr_rx = st.number_input("Multiplicador ATR:", value=2.0, key="atr_rx")
        with c4:
            usar_alvo_rx = st.toggle("🎯 Habilitar Alvo", value=False, key="tg_alvo_rx")
            alvo_rx = st.number_input("Alvo (%):", value=20.00, key="rx_alvo", disabled=not usar_alvo_rx)

    exibir_explicacao_estrategia()
    btn_rx = st.button("🔍 Dissecar Tendência Turtle", type="primary", use_container_width=True)
    
    if btn_rx:
        intervalo_tv_rx = tradutor_intervalo.get(tempo_rx, Interval.in_daily)
        with st.spinner(f"Processando {ativo_rx} via tvDatafeed..."):
            try:
                df_full = tv.get_hist(symbol=ativo_rx.replace('.SA', ''), exchange='BMFBOVESPA', interval=intervalo_tv_rx, n_bars=5000)
                if df_full is not None and len(df_full) > 60:
                    df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                    df_full = calcular_turtle(df_full, periodo_donchian=per_donchian_rx, mult_atr=mult_atr_rx)
                    
                    data_atual = df_full.index[-1]
                    delta = {'1y': 1, '2y': 2, '5y': 5}.get(periodo_rx, 10)
                    data_corte = data_atual - pd.DateOffset(years=delta) if periodo_rx != 'max' else df_full.index[0]
                    df_ativo = df_full[df_full.index >= data_corte].copy()
                    
                    trades_fechados, em_pos = [], None
                    for i in range(len(df_ativo)):
                        linha = df_ativo.iloc[i]
                        if em_pos is None:
                            if linha['Cruzou_Compra']:
                                em_pos = {'data': df_ativo.index[i], 'p_ent': linha['Close'], 'stop': linha['Close'] - (mult_atr_rx * linha['ATR'])}
                        else:
                            novo_st = linha['Close'] - (mult_atr_rx * linha['ATR'])
                            if novo_st > em_pos['stop']: em_pos['stop'] = novo_st
                            
                            bateu_st = linha['Low'] <= em_pos['stop']
                            bateu_al = usar_alvo_rx and (linha['High'] >= em_pos['p_ent'] * (1 + (alvo_rx/100)))
                            
                            if bateu_st or bateu_al:
                                p_sai = em_pos['stop'] if bateu_st else em_pos['p_ent'] * (1 + (alvo_rx/100))
                                luc_pct = (p_sai / em_pos['p_ent']) - 1
                                trades_fechados.append({'Entrada': em_pos['data'].strftime('%d/%m/%Y'), 'Saída': df_ativo.index[i].strftime('%d/%m/%Y'), 'Lucro (R$)': capital_rx * luc_pct, 'Situação': "Gain ✅" if luc_pct > 0 else "Loss ❌"})
                                em_pos = None

                    if em_pos: st.info(f"⏳ **{ativo_rx}: Em Tendência** (Posicionado a R$ {em_pos['p_ent']:.2f}. Stop atual: R$ {em_pos['stop']:.2f})")
                    else: st.success(f"✅ **{ativo_rx}: Aguardando Novo Rompimento**")

                    if trades_fechados:
                        df_trades = pd.DataFrame(trades_fechados)
                        st.markdown(f"### 📊 Resultado Consolidado: {ativo_rx}")
                        st.dataframe(df_trades, use_container_width=True, hide_index=True)
                    
                    st.divider()
                    st.markdown(f"### 📈 Gráfico Interativo: {ativo_rx}")
                    renderizar_grafico_tv(f"BMFBOVESPA:{ativo_rx}")
                else: st.error("Dados insuficientes.")
            except Exception as e: st.error(f"Erro: {e}")
# ==========================================
# 1. IMPORTAÇÃO E CONFIGURAÇÃO
# ==========================================
st.set_page_config(page_title="Turtle Strategy Elite", layout="wide", page_icon="🐢")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial.")
    st.stop()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from config_ativos import bdrs_elite, ibrx_selecao
    from motor_dados import puxar_dados_blindados # Usando seu motor padrão
except ImportError:
    st.error("❌ Erro ao carregar dependências.")
    st.stop()

ativos_para_rastrear = sorted(list(set([a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)])))

# ==========================================
# 2. MOTOR MATEMÁTICO TURTLE ELITE
# ==========================================
def calcular_turtle_elite(df, l1=20, l2=55, exit_p=10, mult_atr=2.0):
    if df is None or len(df) < max(l1, l2, exit_p): return None
    df = df.copy()
    
    # Padronização
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]

    # Canais de Donchian (Highs e Lows)
    df['l1_high'] = df['high'].rolling(window=l1).max().shift(1)
    df['l2_high'] = df['high'].rolling(window=l2).max().shift(1)
    df['exit_low'] = df['low'].rolling(window=exit_p).min().shift(1)
    
    # Volatilidade (N)
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=20)
    
    return df

# ==========================================
# 3. INTERFACE STREAMLIT
# ==========================================
st.title("🐢 Turtle Strategy: Sistema de Elite")
st.info("Estratégia baseada no experimento original das Tartarugas: Compre força e proteja o capital com volatilidade.")

with st.container(border=True):
    st.markdown("#### ⚙️ Parâmetros do Caçador")
    c1, c2, c3, c4 = st.columns(4)
    p_l1 = c1.number_input("L1 (Curto):", 20)
    p_l2 = c2.number_input("L2 (Longo):", 55)
    p_exit = c3.number_input("Saída (Donchian):", 10)
    p_atr = c4.number_input("Multiplicador ATR:", 2.0)

    st.markdown("#### 🛡️ Filtros Opcionais (Regras de Ouro)")
    f1, f2 = st.columns(2)
    usar_filtro_win = f1.toggle("🚫 Pular L1 se o anterior foi GAIN", value=True, help="Evita entrar em rompimentos falsos logo após uma grande tendência.")
    usar_saida_donchian = f2.toggle("🛑 Usar Saída de 10 dias (Donchian)", value=True, help="Encerra o trade assim que o preço perde a mínima do canal de saída.")

aba_radar, aba_rx = st.tabs(["📡 Radar Global", "🔬 Raio-X de Tendência"])

# --- LÓGICA DO RADAR ---
with aba_radar:
    lista_sel = st.selectbox("Lista:", ["BDRs Elite", "IBrX Seleção"])
    tempo_r = st.selectbox("Tempo:", ['1d', '1wk'], index=0)
    
    if st.button("🚀 Iniciar Varredura de Elite", type="primary", use_container_width=True):
        ativos_tr = bdrs_elite if lista_sel == "BDRs Elite" else ibrx_selecao
        ativos_tr = sorted(list(set([a.replace('.SA', '') for a in ativos_tr])))
        
        ls_res = []
        p_bar = st.progress(0)
        
        for idx, ativo in enumerate(ativos_tr):
            p_bar.progress((idx + 1) / len(ativos_tr))
            try:
                df = puxar_dados_blindados(ativo, tempo_r)
                df = calcular_turtle_elite(df, p_l1, p_l2, p_exit, p_atr)
                
                if df is not None:
                    # Lógica simplificada de detecção para o Radar
                    hoje = df.iloc[-1]
                    ontem = df.iloc[-2]
                    
                    status = "🟡 Neutro"
                    # Verifica Rompimentos
                    rompeu_l1 = hoje['close'] > ontem['l1_high']
                    rompeu_l2 = hoje['close'] > ontem['l2_high']
                    
                    if rompeu_l2: status = "🟢 COMPRA (L2 - Forte)"
                    elif rompeu_l1: status = "🟢 COMPRA (L1 - Agressiva)"
                    elif hoje['close'] < ontem['exit_low']: status = "🔴 SAÍDA (Donchian)"
                    elif hoje['close'] > ontem['exit_low'] and hoje['close'] > ontem['l1_high']: status = "📈 Em Tendência"

                    ls_res.append({'Ativo': ativo, 'Preço': f"R$ {hoje['close']:.2f}", 'Status': status, 'ATR': f"{hoje['atr']:.2f}"})
            except: pass
            
        p_bar.empty()
        if ls_res: st.dataframe(pd.DataFrame(ls_res), use_container_width=True, hide_index=True)

# --- LÓGICA DO BACKTEST (COM FILTRO DE GAIN) ---
with aba_rx:
    atv_rx = st.selectbox("Ativo:", ativos_para_rastrear)
    
    if st.button("📊 Analisar Performance Turtle", type="primary", use_container_width=True):
        try:
            df = puxar_dados_blindados(atv_rx, '1d')
            df = calcular_turtle_elite(df, p_l1, p_l2, p_exit, p_atr)
            
            if df is not None:
                trades, em_posicao = [], False
                last_was_win = False # Controlador do filtro
                
                for i in range(1, len(df)):
                    candle = df.iloc[i]
                    ontem = df.iloc[i-1]
                    
                    # Entrada
                    if not em_posicao:
                        pode_l1 = (not usar_filtro_win) or (not last_was_win)
                        rompeu_l1 = candle['close'] > ontem['l1_high']
                        rompeu_l2 = candle['close'] > ontem['l2_high']
                        
                        # Regra: Entra se L2 (independente de win) OU se L1 (se win for falso)
                        if rompeu_l2 or (rompeu_l1 and pode_l1):
                            em_posicao = True
                            p_ent, d_ent = candle['close'], df.index[i]
                            stop_inicial = candle['close'] - (p_atr * candle['atr'])
                    
                    # Saída
                    elif em_posicao:
                        saiu_donchian = usar_saida_donchian and (candle['low'] < ontem['exit_low'])
                        saiu_stop = candle['low'] < stop_inicial
                        
                        if saiu_donchian or saiu_stop:
                            p_sai = ontem['exit_low'] if saiu_donchian else stop_inicial
                            lucro = ((p_sai / p_ent) - 1) * 100
                            trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': df.index[i].strftime('%d/%m/%Y'), 'Retorno (%)': lucro})
                            last_was_win = lucro > 0 # Atualiza para o próximo trade
                            em_posicao = False
                
                if trades:
                    df_res = pd.DataFrame(trades)
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Total Trades", len(df_res))
                    c2.metric("Win Rate", f"{(len(df_res[df_res['Retorno (%)'] > 0])/len(df_res)*100):.1f}%")
                    c3.metric("Resultado Total", f"{df_res['Retorno (%)'].sum():.2f}%")
                    st.dataframe(df_res, use_container_width=True, hide_index=True)
                else: st.warning("Nenhum trade encontrado.")
        except Exception as e: st.error(f"Erro: {e}")
