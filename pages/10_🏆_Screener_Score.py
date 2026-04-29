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
st.set_page_config(page_title="Sniper Confluence", layout="wide", page_icon="🎯")

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
# 3. O MOTOR MATEMÁTICO: KHAN SAAB V.02
# ==========================================
def calcular_khan_saab(df):
    if df is None or len(df) < 50:
        return None
        
    df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df.index = df.index.tz_localize(None)

    # Indicadores Base
    df['EMA_9'] = ta.ema(df['Close'], length=9)
    df['EMA_21'] = ta.ema(df['Close'], length=21)
    df['VWAP_Proxy'] = ta.vwma(df['Close'], df['Volume'], length=20) # Proxy VWAP
    df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    df['RSI_14'] = ta.rsi(df['Close'], length=14)
    df['RSI_Fast'] = ta.rsi(df['Close'], length=5) # Proxy para o RSI 5m
    
    # MACD
    macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
    df['MACD_Line'] = macd.iloc[:, 0]
    df['MACD_Signal'] = macd.iloc[:, 2]
    
    # ADX
    adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
    df['ADX'] = adx_df.iloc[:, 0]
    
    # Volume Médio
    df['Vol_Avg'] = ta.sma(df['Volume'], length=20)

    # --- LÓGICA DE SCORE (PONTUAÇÃO DE CONFLUÊNCIA) ---
    b_score = (
        (df['Close'] > df['VWAP_Proxy']).astype(int) +
        (df['RSI_14'] > 50).astype(int) +
        (df['MACD_Line'] > df['MACD_Signal']).astype(int) +
        (df['EMA_9'] > df['EMA_21']).astype(int) +
        ((df['ADX'] > 25) & (df['Close'] > df['EMA_9'])).astype(int) +
        ((df['Volume'] > df['Vol_Avg']) & (df['Close'] > df['Open'])).astype(int) +
        (df['RSI_Fast'] > 50).astype(int)
    )
    df['Bull_Pct'] = (b_score / 7) * 100

    r_score = (
        (df['Close'] < df['VWAP_Proxy']).astype(int) +
        (df['RSI_14'] < 50).astype(int) +
        (df['MACD_Line'] < df['MACD_Signal']).astype(int) +
        (df['EMA_9'] < df['EMA_21']).astype(int) +
        ((df['ADX'] > 25) & (df['Close'] < df['EMA_9'])).astype(int) +
        ((df['Volume'] > df['Vol_Avg']) & (df['Close'] < df['Open'])).astype(int) +
        (df['RSI_Fast'] < 50).astype(int)
    )
    df['Bear_Pct'] = (r_score / 7) * 100

    # Viés de Mercado (Market Bias)
    conditions = [
        (df['Bull_Pct'] - df['Bear_Pct']) >= 40,
        (df['Bear_Pct'] - df['Bull_Pct']) >= 40,
        df['Bull_Pct'] > df['Bear_Pct']
    ]
    choices = ["STRONG BULL", "STRONG BEAR", "MILD BULL"]
    df['Bias'] = np.select(conditions, choices, default="MILD BEAR")

    # Gatilhos Clássicos do KhanSaab
    df['EMA9_Prev'] = df['EMA_9'].shift(1)
    df['EMA21_Prev'] = df['EMA_21'].shift(1)
    df['Buy_Cross'] = (df['EMA9_Prev'] <= df['EMA21_Prev']) & (df['EMA_9'] > df['EMA_21'])
    df['Sell_Cross'] = (df['EMA9_Prev'] >= df['EMA21_Prev']) & (df['EMA_9'] < df['EMA_21'])

    return df.dropna()


# ==========================================
# 4. INTERFACE
# ==========================================
st.title("🎯 Sniper Confluence (KhanSaab V.02)")
st.info("💡 **A Estratégia:** O robô varre dezenas de ativos buscando o cruzamento das EMAs (9 e 21). Porém, ele **só libera o tiro (entrada)** se o 'Bull Score' estiver alto, confirmando confluência com MACD, RSI, ADX e Volume Institucional.")

aba_radar, aba_raiox = st.tabs(["📡 Radar de Confluência", "🔬 Raio-X Individual"])

with aba_radar:
    st.header("Varredura Sniper Institucional")
    c1, c2, c3 = st.columns(3)
    lista_r = c1.selectbox("Lista:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"])
    tempo_r = c2.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2)
    score_min = c3.slider("Confluência Mínima Exigida (Bull Score %):", min_value=40, max_value=100, value=70, step=10)

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
                df = calcular_khan_saab(df)
                if df is None: continue
                
                hoje = df.iloc[-1]
                
                # Regra de Entrada Forte: Cruzou EMA pra cima HOJE + Score Alto
                if hoje['Buy_Cross'] and hoje['Bull_Pct'] >= score_min:
                    ls_entradas.append({
                        'Ativo': ativo, 'Cotação': f"R$ {hoje['Close']:.2f}",
                        'Bull Score': f"{hoje['Bull_Pct']:.0f}%", 'Bias': hoje['Bias'],
                        'MACD': 'Verde 🟢' if hoje['MACD_Line'] > hoje['MACD_Signal'] else 'Vermelho 🔴',
                        'Volume': 'Alto 🔥' if hoje['Volume'] > hoje['Vol_Avg'] else 'Baixo 🧊'
                    })
                    
                # Regra de Operação Correndo: Preço já está acima das médias e Score está estourando
                elif hoje['EMA_9'] > hoje['EMA_21'] and hoje['Bull_Pct'] >= 85:
                    ls_fortes.append({
                        'Ativo': ativo, 'Cotação': f"R$ {hoje['Close']:.2f}",
                        'Bull Score': f"{hoje['Bull_Pct']:.0f}%", 'Bias': hoje['Bias']
                    })
            except: pass
            time.sleep(0.05)
            
        s_text.empty(); p_bar.empty()
        
        st.subheader(f"🎯 TIROS AUTORIZADOS HOJE (Score >= {score_min}%)")
        if ls_entradas:
            # Trocamos applymap por map aqui 👇
            st.dataframe(pd.DataFrame(ls_entradas).style.map(colorir_bias, subset=['Bias']), use_container_width=True, hide_index=True)
        else: st.info("Nenhum ativo alinhou as engrenagens perfeitamente hoje.")
            
        st.subheader("🔥 Top Ativos em Tendência Brutal (Score >= 85%)")
        if ls_fortes:
            # E trocamos applymap por map aqui também 👇
            st.dataframe(pd.DataFrame(ls_fortes).style.map(colorir_bias, subset=['Bias']), use_container_width=True, hide_index=True)

with aba_raiox:
    st.header("Análise Detalhada (Backtest e Alvos)")
    c1, c2, c3, c4 = st.columns(4)
    atv_rx = c1.selectbox("Ativo a Testar:", ativos_para_rastrear)
    tmp_rx = c2.selectbox("Tempo:", ['15m', '60m', '1d', '1wk'], index=2, key='rx_tmp')
    score_rx = c3.slider("Score Exigido:", 40, 100, 70, 10, key='rx_score')
    mult_atr = c4.number_input("Multiplicador SL/TP (ATR):", value=1.5, step=0.1)
    
    tp_desejado = st.radio("Selecione o Alvo Desejado para Encerrar o Trade:", ["TP 1 (1:1)", "TP 2 (1:2)", "TP 3 (1:3)", "Até Cruzar EMA p/ Baixo (Trailing)"], horizontal=True)

    if st.button("🔬 Processar Backtest Sniper", type="primary", use_container_width=True):
        with st.spinner("Simulando os disparos do Sniper..."):
            try:
                df_full = puxar_dados_blindados(atv_rx, tmp_rx)
                if df_full is not None:
                    df = calcular_khan_saab(df_full)
                    
                    trades = []
                    em_posicao = False
                    
                    df_b = df.tail(1000).reset_index() # Puxa ~4 anos
                    col_dt = df_b.columns[0]
                    
                    for i in range(1, len(df_b)):
                        candle = df_b.iloc[i]
                        
                        if not em_posicao:
                            # ENTRADA: Cruzou pra cima E tem confluência mínima
                            if candle['Buy_Cross'] and candle['Bull_Pct'] >= score_rx:
                                em_posicao = True
                                p_ent = candle['Close']
                                d_ent = candle[col_dt]
                                
                                # Calcula SL e Alvos baseados no ATR do dia
                                risco = candle['ATR'] * mult_atr
                                sl = p_ent - risco
                                tp1 = p_ent + risco
                                tp2 = p_ent + (risco * 2)
                                tp3 = p_ent + (risco * 3)
                        else:
                            bateu_sl = candle['Low'] <= sl
                            bateu_tp1 = "TP 1" in tp_desejado and candle['High'] >= tp1
                            bateu_tp2 = "TP 2" in tp_desejado and candle['High'] >= tp2
                            bateu_tp3 = "TP 3" in tp_desejado and candle['High'] >= tp3
                            virou_tend = "Trailing" in tp_desejado and candle['Sell_Cross']
                            
                            saiu = False
                            motivo = ""
                            
                            if bateu_sl:
                                lucro = ((sl / p_ent) - 1) * 100
                                motivo = "Hit SL ❌"
                                saiu = True
                            elif bateu_tp1:
                                lucro = ((tp1 / p_ent) - 1) * 100
                                motivo = "Hit TP 1 ✅"
                                saiu = True
                            elif bateu_tp2:
                                lucro = ((tp2 / p_ent) - 1) * 100
                                motivo = "Hit TP 2 ✅"
                                saiu = True
                            elif bateu_tp3:
                                lucro = ((tp3 / p_ent) - 1) * 100
                                motivo = "Hit TP 3 ✅"
                                saiu = True
                            elif virou_tend:
                                lucro = ((candle['Close'] / p_ent) - 1) * 100
                                motivo = "Cruzou EMA ❌" if lucro < 0 else "Saída EMA ✅"
                                saiu = True
                                
                            if saiu:
                                trades.append({
                                    'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': candle[col_dt].strftime('%d/%m/%Y'),
                                    'Score Entrada': f"{df_b.iloc[i-1]['Bull_Pct']:.0f}%",
                                    'Retorno (%)': lucro, 'Motivo': motivo
                                })
                                em_posicao = False
                                
                    if trades:
                        df_res = pd.DataFrame(trades)
                        m1, m2, m3 = st.columns(3)
                        acertos = len(df_res[df_res['Retorno (%)'] > 0])
                        m1.metric("Disparos Realizados (Trades)", len(df_res))
                        m2.metric("Taxa de Precisão", f"{(acertos/len(df_res)*100):.1f}%")
                        m3.metric("Lucro Acumulado BRUTO", f"{df_res['Retorno (%)'].sum():.2f}%")
                        
                        df_res['Retorno (%)'] = df_res['Retorno (%)'].apply(lambda x: f"{x:.2f}%")
                        
                        def cor_res(val):
                            if '✅' in str(val): return 'color: #28a745; font-weight: bold'
                            elif '❌' in str(val): return 'color: #dc3545; font-weight: bold'
                            return ''
                            
                        st.dataframe(df_res.style.map(cor_res, subset=['Motivo']), use_container_width=True, hide_index=True)
                    else: st.warning("Com esse nível de confluência exigido, o Sniper não deu nenhum tiro.")
            except Exception as e: st.error(f"Erro: {e}")
