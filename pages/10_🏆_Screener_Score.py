import streamlit as st
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
import warnings
import sys
import os

warnings.filterwarnings('ignore')

# ==========================================
# 1. SEGURANÇA E CONFIGURAÇÃO
# ==========================================
st.set_page_config(page_title="Sniper Confluence Pro", layout="wide", page_icon="🎯")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

# ==========================================
# 2. IMPORTAÇÃO CENTRALIZADA (ATIVOS E MOTOR)
# ==========================================
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from config_ativos import bdrs_elite, ibrx_selecao
except ImportError:
    st.error("❌ Arquivo 'config_ativos.py' não encontrado na raiz do projeto.")
    st.stop()

try:
    from motor_dados import puxar_dados_blindados
except ImportError:
    st.error("❌ Arquivo 'motor_dados.py' não encontrado na raiz do projeto.")
    st.stop()

ativos_para_rastrear = sorted(list(set([a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)])))

def colorir_bias(val):
    if val == "STRONG BULL": return 'color: #00FF00; font-weight: bold'
    if val == "STRONG BEAR": return 'color: #FF0000; font-weight: bold'
    if val == "MILD BULL": return 'color: #90EE90'
    return 'color: #F08080'

# ==========================================
# 3. O MOTOR MATEMÁTICO: TOTALMENTE DINÂMICO
# ==========================================
def calcular_khan_saab_dinamico(df, p_fast, p_slow, ma_type, p_adx, thresh_adx, p_rsi_slow, p_rsi_fast, thresh_rsi, p_vwap, p_vol):
    if df is None or len(df) < max(p_fast, p_slow, p_adx, p_rsi_slow) * 2:
        return None
        
    df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df.index = df.index.tz_localize(None)

    # --- 1. Seleção Dinâmica do Tipo de Média ---
    if ma_type == 'RMA (Welles Wilder)':
        df['MA_Fast'] = ta.rma(df['Close'], length=p_fast)
        df['MA_Slow'] = ta.rma(df['Close'], length=p_slow)
    elif ma_type == 'SMA (Simples)':
        df['MA_Fast'] = ta.sma(df['Close'], length=p_fast)
        df['MA_Slow'] = ta.sma(df['Close'], length=p_slow)
    else: # EMA Padrão
        df['MA_Fast'] = ta.ema(df['Close'], length=p_fast)
        df['MA_Slow'] = ta.ema(df['Close'], length=p_slow)

    # --- 2. Indicadores Flexíveis ---
    df['VWAP_Proxy'] = ta.vwma(df['Close'], df['Volume'], length=p_vwap)
    df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    df['RSI_Slow'] = ta.rsi(df['Close'], length=p_rsi_slow)
    df['RSI_Fast'] = ta.rsi(df['Close'], length=p_rsi_fast)
    
    # MACD (Mantido Clássico 12,26,9, mas você pode parametrizar no futuro se quiser)
    macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
    df['MACD_Line'] = macd.iloc[:, 0]
    df['MACD_Signal'] = macd.iloc[:, 2]
    
    # ADX e DMI
    adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=p_adx)
    df['ADX'] = adx_df.iloc[:, 0]
    df['+DI'] = adx_df.iloc[:, 1]
    df['-DI'] = adx_df.iloc[:, 2]
    
    # Volume Médio
    df['Vol_Avg'] = ta.sma(df['Volume'], length=p_vol)

    # --- 3. SCORE DINÂMICO ---
    b_score = (
        (df['Close'] > df['VWAP_Proxy']).astype(int) +
        (df['RSI_Slow'] > thresh_rsi).astype(int) +
        (df['MACD_Line'] > df['MACD_Signal']).astype(int) +
        (df['MA_Fast'] > df['MA_Slow']).astype(int) +
        ((df['ADX'] > thresh_adx) & (df['Close'] > df['MA_Fast'])).astype(int) +
        ((df['Volume'] > df['Vol_Avg']) & (df['Close'] > df['Open'])).astype(int) +
        (df['RSI_Fast'] > thresh_rsi).astype(int)
    )
    df['Bull_Pct'] = (b_score / 7) * 100

    r_score = (
        (df['Close'] < df['VWAP_Proxy']).astype(int) +
        (df['RSI_Slow'] < thresh_rsi).astype(int) +
        (df['MACD_Line'] < df['MACD_Signal']).astype(int) +
        (df['MA_Fast'] < df['MA_Slow']).astype(int) +
        ((df['ADX'] > thresh_adx) & (df['Close'] < df['MA_Fast'])).astype(int) +
        ((df['Volume'] > df['Vol_Avg']) & (df['Close'] < df['Open'])).astype(int) +
        (df['RSI_Fast'] < thresh_rsi).astype(int)
    )
    df['Bear_Pct'] = (r_score / 7) * 100

    # Viés de Mercado
    conditions = [
        (df['Bull_Pct'] - df['Bear_Pct']) >= 40,
        (df['Bear_Pct'] - df['Bull_Pct']) >= 40,
        df['Bull_Pct'] > df['Bear_Pct']
    ]
    choices = ["STRONG BULL", "STRONG BEAR", "MILD BULL"]
    df['Bias'] = np.select(conditions, choices, default="MILD BEAR")

    # Gatilhos
    df['MA_Fast_Prev'] = df['MA_Fast'].shift(1)
    df['MA_Slow_Prev'] = df['MA_Slow'].shift(1)
    df['Buy_Cross'] = (df['MA_Fast_Prev'] <= df['MA_Slow_Prev']) & (df['MA_Fast'] > df['MA_Slow'])
    df['Sell_Cross'] = (df['MA_Fast_Prev'] >= df['MA_Slow_Prev']) & (df['MA_Fast'] < df['MA_Slow'])

    return df.dropna()

# ==========================================
# 4. BARRA LATERAL: O CONTROLE DO QUANT
# ==========================================
with st.sidebar:
    st.header("⚙️ Calibragem Quant")
    st.markdown("Ajuste as engrenagens da sua estratégia.")
    
    st.subheader("1. Médias Móveis")
    ma_tipo = st.selectbox("Tipo de Média:", ['EMA (Exponencial)', 'RMA (Welles Wilder)', 'SMA (Simples)'])
    p_fast = st.number_input("Período Rápido:", value=9, step=1)
    p_slow = st.number_input("Período Lento:", value=21, step=1)
    
    st.subheader("2. Filtros de Força (ADX & RSI)")
    p_adx = st.number_input("Período ADX:", value=14, step=1)
    thresh_adx = st.slider("Corte ADX (Força Mínima):", 15, 50, 25)
    
    p_rsi_slow = st.number_input("Período RSI Padrão:", value=14, step=1)
    p_rsi_fast = st.number_input("Período RSI Rápido:", value=5, step=1)
    thresh_rsi = st.slider("Linha d'água do RSI:", 40, 60, 50)
    
    st.subheader("3. Volume & VWAP")
    p_vol = st.number_input("Média de Volume:", value=20, step=1)
    p_vwap = st.number_input("Período VWAP (Proxy):", value=20, step=1)

# ==========================================
# 5. INTERFACE PRINCIPAL
# ==========================================
st.title("🎯 Sniper Confluence (Pro Edition)")
st.info("💡 **Sistema Dinâmico:** Você está no controle absoluto. Os cálculos de Confluência agora respeitam os parâmetros da Barra Lateral.")

aba_radar, aba_raiox = st.tabs(["📡 Radar de Mercado", "🔬 Raio-X Clínico"])

# --- ABA 1: RADAR ---
with aba_radar:
    c1, c2, c3 = st.columns(3)
    lista_r = c1.selectbox("Lista de Varredura:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"])
    tempo_r = c2.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2)
    score_min = c3.slider("Exigência Mínima (Bull Score %):", 40, 100, 70, 10)

    if st.button("🚀 Iniciar Varredura de Mercado", type="primary", use_container_width=True):
        ativos_tr = bdrs_elite if lista_r == "BDRs Elite" else ibrx_selecao if lista_r == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        ativos_tr = sorted(list(set([a.replace('.SA', '') for a in ativos_tr])))
        
        ls_entradas, ls_fortes = [], []
        p_bar = st.progress(0); s_text = st.empty()

        for idx, ativo in enumerate(ativos_tr):
            s_text.text(f"🎯 Escaneando {ativo} ({idx+1}/{len(ativos_tr)})...")
            p_bar.progress((idx + 1) / len(ativos_tr))
            
            try:
                df = puxar_dados_blindados(ativo, tempo_r)
                if df is None: continue
                # PASSANDO TODOS OS PARÂMETROS DA SIDEBAR
                df = calcular_khan_saab_dinamico(df, p_fast, p_slow, ma_tipo, p_adx, thresh_adx, p_rsi_slow, p_rsi_fast, thresh_rsi, p_vwap, p_vol)
                if df is None: continue
                
                hoje = df.iloc[-1]
                
                if hoje['Buy_Cross'] and hoje['Bull_Pct'] >= score_min:
                    ls_entradas.append({
                        'Ativo': ativo, 'Cotação': f"R$ {hoje['Close']:.2f}",
                        'Bull Score': f"{hoje['Bull_Pct']:.0f}%", 'Bias': hoje['Bias'],
                        'MACD': 'Verde 🟢' if hoje['MACD_Line'] > hoje['MACD_Signal'] else 'Vermelho 🔴',
                        'Volume': 'Alto 🔥' if hoje['Volume'] > hoje['Vol_Avg'] else 'Baixo 🧊'
                    })
                    
                elif hoje['MA_Fast'] > hoje['MA_Slow'] and hoje['Bull_Pct'] >= 85:
                    ls_fortes.append({
                        'Ativo': ativo, 'Cotação': f"R$ {hoje['Close']:.2f}",
                        'Bull Score': f"{hoje['Bull_Pct']:.0f}%", 'Bias': hoje['Bias']
                    })
            except: pass
            time.sleep(0.05)
            
        s_text.empty(); p_bar.empty()
        
        st.subheader(f"🎯 TIROS AUTORIZADOS HOJE (Score >= {score_min}%)")
        if ls_entradas:
            st.dataframe(pd.DataFrame(ls_entradas).style.map(colorir_bias, subset=['Bias']), use_container_width=True, hide_index=True)
        else: st.info("Nenhum ativo alinhou as engrenagens perfeitamente hoje.")
            
        st.subheader("🔥 Top Ativos em Tendência Brutal (Score >= 85%)")
        if ls_fortes:
            st.dataframe(pd.DataFrame(ls_fortes).style.map(colorir_bias, subset=['Bias']), use_container_width=True, hide_index=True)

# --- ABA 2: RAIO-X E ESTADO CLÍNICO ---
with aba_raiox:
    c1, c2, c3 = st.columns([1.5, 1, 1])
    atv_rx = c1.selectbox("Ativo a Testar:", ativos_para_rastrear)
    tmp_rx = c2.selectbox("Tempo:", ['15m', '60m', '1d', '1wk'], index=2, key='rx_tmp')
    mult_atr = c3.number_input("Multiplicador SL/TP (ATR):", value=1.5, step=0.1)

    if st.button("🔬 Diagnóstico Completo", type="primary", use_container_width=True):
        with st.spinner("Realizando ressonância magnética do ativo..."):
            try:
                df_full = puxar_dados_blindados(atv_rx, tmp_rx)
                if df_full is not None:
                    # Roda o motor com as configs do usuário
                    df = calcular_khan_saab_dinamico(df_full, p_fast, p_slow, ma_tipo, p_adx, thresh_adx, p_rsi_slow, p_rsi_fast, thresh_rsi, p_vwap, p_vol)
                    
                    if df is not None:
                        hoje = df.iloc[-1]
                        
                        # ==================================================
                        # O NOVO DASHBOARD: ESTADO CLÍNICO DO ATIVO HOJE
                        # ==================================================
                        st.markdown(f"### 🩺 Estado Clínico: {atv_rx} (Hoje)")
                        
                        # Criando uma tabela organizada para os indicadores
                        dados_clinicos = [
                            {"Indicador": "Preço x VWAP", "Valor Exato": f"Preço: R${hoje['Close']:.2f} | VWAP: R${hoje['VWAP_Proxy']:.2f}", "Status": "🟢 Acima (Bull)" if hoje['Close'] > hoje['VWAP_Proxy'] else "🔴 Abaixo (Bear)"},
                            {"Indicador": f"Média Rápida x Lenta ({p_fast}/{p_slow})", "Valor Exato": f"Ráp: R${hoje['MA_Fast']:.2f} | Len: R${hoje['MA_Slow']:.2f}", "Status": "🟢 Comprado (Bull)" if hoje['MA_Fast'] > hoje['MA_Slow'] else "🔴 Vendido (Bear)"},
                            {"Indicador": f"RSI Principal ({p_rsi_slow})", "Valor Exato": f"{hoje['RSI_Slow']:.1f}", "Status": "🟢 Alta" if hoje['RSI_Slow'] > thresh_rsi else "🔴 Baixa"},
                            {"Indicador": f"RSI Rápido ({p_rsi_fast})", "Valor Exato": f"{hoje['RSI_Fast']:.1f}", "Status": "🟢 Alta" if hoje['RSI_Fast'] > thresh_rsi else "🔴 Baixa"},
                            {"Indicador": "MACD (Linha x Sinal)", "Valor Exato": f"Lin: {hoje['MACD_Line']:.2f} | Sin: {hoje['MACD_Signal']:.2f}", "Status": "🟢 Comprado" if hoje['MACD_Line'] > hoje['MACD_Signal'] else "🔴 Vendido"},
                            {"Indicador": f"DMI (+DI x -DI)", "Valor Exato": f"+DI: {hoje['+DI']:.1f} | -DI: {hoje['-DI']:.1f}", "Status": "🟢 +DI Acima" if hoje['+DI'] > hoje['-DI'] else "🔴 -DI Acima"},
                            {"Indicador": f"Força ADX ({p_adx})", "Valor Exato": f"{hoje['ADX']:.1f}", "Status": f"🔥 Forte (> {thresh_adx})" if hoje['ADX'] > thresh_adx else f"🧊 Fraco (< {thresh_adx})"},
                            {"Indicador": "Volume x Média", "Valor Exato": f"Vol: {hoje['Volume']:.0f}", "Status": "🟢 Acima da Média" if hoje['Volume'] > hoje['Vol_Avg'] else "⚪ Normal/Baixo"}
                        ]
                        
                        df_clinico = pd.DataFrame(dados_clinicos)
                        
                        def cor_status(val):
                            if '🟢' in str(val) or '🔥' in str(val): return 'color: #28a745; font-weight: bold'
                            elif '🔴' in str(val): return 'color: #dc3545; font-weight: bold'
                            return 'color: #6c757d'
                            
                        st.dataframe(df_clinico.style.map(cor_status, subset=['Status']), use_container_width=True, hide_index=True)
                        
                        st.markdown(f"**Veredito Final de Confluência:** {hoje['Bull_Pct']:.0f}% Bull Score | Viés: **{hoje['Bias']}**")
                        st.divider()

                        # ==================================================
                        # BACKTEST TRADICIONAL
                        # ==================================================
                        st.markdown("### 📊 Backtest Histórico de Tiros")
                        trades = []
                        em_posicao = False
                        
                        df_b = df.tail(1000).reset_index()
                        col_dt = df_b.columns[0]
                        
                        for i in range(1, len(df_b)):
                            candle = df_b.iloc[i]
                            
                            if not em_posicao:
                                # Entrada (Usa o score mínimo de 70% fixo para o backtest de qualidade)
                                if candle['Buy_Cross'] and candle['Bull_Pct'] >= 70:
                                    em_posicao = True
                                    p_ent = candle['Close']
                                    d_ent = candle[col_dt]
                                    risco = candle['ATR'] * mult_atr
                                    sl = p_ent - risco
                                    tp_alvo = p_ent + (risco * 2) # Assume Alvo Padrão 1:2 no Backtest Rápido
                            else:
                                se_bateu_sl = candle['Low'] <= sl
                                se_bateu_tp = candle['High'] >= tp_alvo
                                virou_tend = candle['Sell_Cross']
                                
                                saiu = False
                                motivo = ""
                                
                                if se_bateu_sl:
                                    lucro = ((sl / p_ent) - 1) * 100
                                    motivo = "Hit SL ❌"
                                    saiu = True
                                elif se_bateu_tp:
                                    lucro = ((tp_alvo / p_ent) - 1) * 100
                                    motivo = "Hit Alvo 1:2 ✅"
                                    saiu = True
                                elif virou_tend:
                                    lucro = ((candle['Close'] / p_ent) - 1) * 100
                                    motivo = "Cruzou P/ Baixo ❌" if lucro < 0 else "Saída Cruzamento ✅"
                                    saiu = True
                                    
                                if saiu:
                                    trades.append({
                                        'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': candle[col_dt].strftime('%d/%m/%Y'),
                                        'Retorno (%)': lucro, 'Motivo': motivo
                                    })
                                    em_posicao = False
                                    
                        if trades:
                            df_res = pd.DataFrame(trades)
                            m1, m2, m3 = st.columns(3)
                            acertos = len(df_res[df_res['Retorno (%)'] > 0])
                            m1.metric("Disparos Realizados (Trades)", len(df_res))
                            m2.metric("Taxa de Precisão (Win Rate)", f"{(acertos/len(df_res)*100):.1f}%")
                            m3.metric("Lucro Acumulado BRUTO", f"{df_res['Retorno (%)'].sum():.2f}%")
                            
                            df_res['Retorno (%)'] = df_res['Retorno (%)'].apply(lambda x: f"{x:.2f}%")
                            st.dataframe(df_res.style.map(lambda v: 'color: #28a745; font-weight: bold' if '✅' in str(v) else 'color: #dc3545; font-weight: bold' if '❌' in str(v) else '', subset=['Motivo']), use_container_width=True, hide_index=True)
                        else: st.warning("Com esse nível de confluência, não houve tiros fechados no histórico.")
            except Exception as e: st.error(f"Erro: {e}")
