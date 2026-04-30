import streamlit as st
import pandas as pd
import numpy as np
import pandas_ta as ta
from sklearn.neighbors import KNeighborsClassifier
import time
import sys
import os
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. SEGURANÇA E CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Trend Machine AI", layout="wide", page_icon="🤖")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

# --- IMPORTANDO SEU BUNKER DE DADOS E ATIVOS ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from config_ativos import bdrs_elite, ibrx_selecao, macro_elite
except ImportError:
    st.error("❌ Arquivo 'config_ativos.py' não encontrado.")
    st.stop()

try:
    from motor_dados import puxar_dados_blindados
except ImportError:
    st.error("❌ Arquivo 'motor_dados.py' não encontrado.")
    st.stop()

# Lista unificada para os testes
b3_symbols = [a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)]
ativos_para_rastrear = sorted(list(set(b3_symbols + list(macro_elite.keys()))))

# ==========================================
# 2. O MOTOR MATEMÁTICO: AI SUPERTREND X PIVOT
# ==========================================
@st.cache_data(show_spinner=False, ttl=300)
def calcular_ai_supertrend_pivot(df, k=6, n_points=48, st_len=10, st_factor=3.5, 
                                 adx_len=14, use_adx=True, pivot_len=14):
    if df is None or len(df) < max(n_points, adx_len, pivot_len * 7) * 2:
        return None
        
    df = df.copy()
    df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    if df.index.tz is not None: df.index = df.index.tz_localize(None)
    
    # 1. FILTRO DIRECIONAL: ADX & DMI
    adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=adx_len)
    df['ADX'] = adx_df.iloc[:, 0]
    df['+DI'] = adx_df.iloc[:, 1]
    df['-DI'] = adx_df.iloc[:, 2]
    
    df['Long_ADX_Cond'] = (df['ADX'] > 20) & (df['+DI'] > df['-DI']) if use_adx else True
    df['Short_ADX_Cond'] = (df['ADX'] > 20) & (df['-DI'] > df['+DI']) if use_adx else True

    # 2. FUNDAÇÃO: SuperTrend Base (WMA)
    df['WMA_Base'] = ta.wma(df['Close'], length=st_len)
    atr = ta.atr(df['High'], df['Low'], df['Close'], length=st_len)
    
    st_upper = df['WMA_Base'] + (st_factor * atr)
    st_lower = df['WMA_Base'] - (st_factor * atr)
    
    supertrend = np.zeros(len(df))
    st_direction = np.zeros(len(df))
    
    up_arr = st_upper.fillna(0).values.copy()
    dn_arr = st_lower.fillna(0).values.copy()
    close_arr = df['Close'].values.copy()
    
    for i in range(1, len(df)):
        prev_st = supertrend[i-1]
        
        curr_up = up_arr[i] if up_arr[i] < up_arr[i-1] or close_arr[i-1] > up_arr[i-1] else up_arr[i-1]
        curr_dn = dn_arr[i] if dn_arr[i] > dn_arr[i-1] or close_arr[i-1] < dn_arr[i-1] else dn_arr[i-1]
        
        if prev_st == up_arr[i-1]:
            st_direction[i] = -1 if close_arr[i] > curr_up else 1
        else:
            st_direction[i] = 1 if close_arr[i] < curr_dn else -1
            
        supertrend[i] = curr_dn if st_direction[i] == -1 else curr_up
        up_arr[i] = curr_up
        dn_arr[i] = curr_dn

    df['SuperTrend'] = supertrend
    df['ST_Direction'] = st_direction 
    
    # 3. INTELIGÊNCIA ARTIFICIAL: KNN
    df['Price_Smoothed'] = ta.wma(df['Close'], length=10)
    df['ST_Smoothed'] = ta.wma(df['SuperTrend'], length=80)
    df['Label_Real'] = np.where(df['Price_Smoothed'] > df['ST_Smoothed'], 1, 0)
    
    ai_labels = np.zeros(len(df))
    
    for i in range(n_points, len(df)):
        X_train = df['SuperTrend'].iloc[i-n_points:i].values.reshape(-1, 1)
        y_train = df['Label_Real'].iloc[i-n_points:i].values
        X_test = np.array([[df['SuperTrend'].iloc[i]]])
        
        knn = KNeighborsClassifier(n_neighbors=k, weights='distance')
        try:
            knn.fit(X_train, y_train)
            ai_labels[i] = knn.predict(X_test)[0]
        except: ai_labels[i] = 0
            
    df['AI_Label'] = ai_labels 

    # 4. GATILHO FINAL: Pivot Percentile
    lengths = [pivot_len * i for i in range(1, 8)]
    bull_score = np.zeros(len(df))
    bear_score = np.zeros(len(df))
    
    highest_high = df['High'].rolling(144).quantile(0.75)
    lowest_low = df['Low'].rolling(144).quantile(0.25)
    
    for l in lengths:
        p_high = df['High'].rolling(l).quantile(0.75)
        p_low = df['Low'].rolling(l).quantile(0.25)
        
        t_bull_high = p_high > highest_high
        t_bull_low = p_low > highest_high
        t_bear_high = p_high < lowest_low
        t_bear_low = p_low < lowest_low
        
        w_bull = (p_low < highest_high) & (p_low > lowest_low)
        w_bear = (p_high > lowest_low) & (p_high < highest_high)
        
        bull_score += t_bull_high.astype(int) + t_bull_low.astype(int) + (0.5 * w_bull.astype(int))
        bear_score += t_bear_high.astype(int) + t_bear_low.astype(int) + (0.5 * w_bear.astype(int))
        
    df['Pivot_Trend_Value'] = bull_score - bear_score
    
    # 5. GATILHOS FINAIS DE ENTRADA E SAÍDA
    df['Entry_Long'] = (df['ST_Direction'] < 0) & (df['AI_Label'] == 1) & df['Long_ADX_Cond'] & (df['Pivot_Trend_Value'] > 0)
    df['Entry_Short'] = (df['ST_Direction'] > 0) & (df['AI_Label'] == 0) & df['Short_ADX_Cond'] & (df['Pivot_Trend_Value'] < 0)
    
    df['Exit_Long'] = ((df['ST_Direction'] == 1) & (df['AI_Label'] == 0)) | (df['Pivot_Trend_Value'] < 0)
    df['Exit_Short'] = ((df['ST_Direction'] == -1) & (df['AI_Label'] == 1)) | (df['Pivot_Trend_Value'] > 0)
    
    return df.dropna()

# ==========================================
# 3. INTERFACE PRINCIPAL E DASHBOARD
# ==========================================
st.title("🤖 Trend Machine AI (KNN + Pivot)")
st.info("💡 **Inteligência Artificial Algorítmica:** Este robô usa o algoritmo *K-Nearest Neighbors (KNN)* para avaliar os topos e fundos do passado e prever a continuidade da tendência do SuperTrend no presente.")

# --- BLOCO DE CALIBRAGEM ---
with st.container(border=True):
    st.markdown("#### ⚙️ Calibragem do Motor Quantitativo")
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.markdown("**Inteligência Artificial (KNN)**")
        p_k = st.number_input("Vizinhos (K):", value=6, step=1, help="Quantidade de cenários similares do passado para avaliar.")
        p_pts = st.number_input("Massa de Dados (N):", value=48, step=1)
        
    with c2:
        st.markdown("**SuperTrend Base**")
        p_st_len = st.number_input("Período SuperTrend:", value=10, step=1)
        p_st_fac = st.number_input("Fator SuperTrend:", value=3.5, step=0.1)
        
    with c3:
        st.markdown("**Aceleração (Pivôs)**")
        p_piv = st.number_input("Período Pivot Base:", value=14, step=1)
        
    with c4:
        st.markdown("**Filtro Institucional**")
        p_use_adx = st.toggle("Usar Filtro ADX/DMI", value=True)
        p_adx_len = st.number_input("Período ADX:", value=14, step=1, disabled=not p_use_adx)


aba_radar, aba_raiox = st.tabs(["📡 Radar AI de Mercado", "🔬 Backtest de IA (Prova Real)"])

# --- ABA 1: RADAR DE MERCADO ---
with aba_radar:
    r1, r2 = st.columns(2)
    lista_r = r1.selectbox("Lista de Rastreio:", ["BDRs Elite", "IBrX Seleção", "Cripto/Macros", "Todos"])
    tempo_r = r2.selectbox("Tempo Gráfico:", ['60m', '1d', '1wk'], index=1, help="Modelos de IA costumam ser mais assertivos a partir de 60 minutos.")

    if st.button("🚀 Escanear Mercado com Inteligência Artificial", type="primary", use_container_width=True):
        if lista_r == "BDRs Elite": ativos_tr = bdrs_elite
        elif lista_r == "IBrX Seleção": ativos_tr = ibrx_selecao
        elif lista_r == "Cripto/Macros": ativos_tr = list(macro_elite.keys())
        else: ativos_tr = ativos_para_rastrear
            
        ativos_tr = sorted(list(set([a.replace('.SA', '') for a in ativos_tr])))
        
        ls_compras, ls_vendas = [], []
        p_bar = st.progress(0); s_text = st.empty()

        for idx, ativo in enumerate(ativos_tr):
            s_text.text(f"🤖 A Inteligência Artificial está analisando {ativo}...")
            p_bar.progress((idx + 1) / len(ativos_tr))
            try:
                df_cru = puxar_dados_blindados(ativo, tempo_r)
                df = calcular_ai_supertrend_pivot(df_cru, p_k, p_pts, p_st_len, p_st_fac, p_adx_len, p_use_adx, p_piv)
                
                if df is not None:
                    hoje = df.iloc[-1]
                    if hoje['Entry_Long']:
                        ls_compras.append({
                            'Ativo': ativo, 'Preço (R$)': f"{hoje['Close']:.2f}",
                            'Score Pivô': f"{hoje['Pivot_Trend_Value']:.1f}", 'ADX (Força)': f"{hoje['ADX']:.1f}"
                        })
                    elif hoje['Entry_Short']:
                        ls_vendas.append({
                            'Ativo': ativo, 'Preço (R$)': f"{hoje['Close']:.2f}",
                            'Score Pivô': f"{hoje['Pivot_Trend_Value']:.1f}", 'ADX (Força)': f"{hoje['ADX']:.1f}"
                        })
            except: pass
            
        s_text.empty(); p_bar.empty()
        
        c_buy, c_sell = st.columns(2)
        with c_buy:
            st.success("🟢 **SINAIS DE COMPRA (IA CONFIRMOU ALTA)**")
            if ls_compras: st.dataframe(pd.DataFrame(ls_compras), use_container_width=True, hide_index=True)
            else: st.write("A IA não autorizou nenhuma compra hoje.")
            
        with c_sell:
            st.error("🔴 **SINAIS DE VENDA / SHORT (IA CONFIRMOU BAIXA)**")
            if ls_vendas: st.dataframe(pd.DataFrame(ls_vendas), use_container_width=True, hide_index=True)
            else: st.write("A IA não autorizou nenhuma venda hoje.")

# --- ABA 2: BACKTEST INDIVIDUAL ---
with aba_raiox:
    c1, c2 = st.columns(2)
    atv_rx = c1.selectbox("Ativo a Testar na IA:", ativos_para_rastrear)
    tmp_rx = c2.selectbox("Tempo Gráfico (Backtest):", ['60m', '1d', '1wk'], index=1)
    
    if st.button("🔬 Rodar Backtest com a IA", type="primary", use_container_width=True):
        with st.spinner("A IA está revivendo o histórico para simular trades..."):
            try:
                df_cru = puxar_dados_blindados(atv_rx, tmp_rx)
                df = calcular_ai_supertrend_pivot(df_cru, p_k, p_pts, p_st_len, p_st_fac, p_adx_len, p_use_adx, p_piv)
                
                if df is not None:
                    trades = []
                    em_posicao = False
                    tipo_posicao = None  # 'Long' ou 'Short'
                    preco_ent = 0
                    
                    df_b = df.reset_index()
                    col_dt = df_b.columns[0]
                    
                    for i in range(1, len(df_b)):
                        candle = df_b.iloc[i]
                        
                        # --- VERIFICA ENTRADAS ---
                        if not em_posicao:
                            if candle['Entry_Long']:
                                em_posicao = True
                                tipo_posicao = 'Long'
                                preco_ent = candle['Close']
                                data_ent = candle[col_dt]
                            elif candle['Entry_Short']:
                                em_posicao = True
                                tipo_posicao = 'Short'
                                preco_ent = candle['Close']
                                data_ent = candle[col_dt]
                                
                        # --- VERIFICA SAÍDAS ---
                        else:
                            saiu = False
                            if tipo_posicao == 'Long' and candle['Exit_Long']:
                                lucro = ((candle['Close'] / preco_ent) - 1) * 100
                                saiu = True
                            elif tipo_posicao == 'Short' and candle['Exit_Short']:
                                lucro = ((preco_ent / candle['Close']) - 1) * 100
                                saiu = True
                                
                            if saiu:
                                trades.append({
                                    'Operação': '🟢 Compra (Long)' if tipo_posicao == 'Long' else '🔴 Venda (Short)',
                                    'Entrada': data_ent.strftime('%d/%m/%Y'),
                                    'Saída': candle[col_dt].strftime('%d/%m/%Y'),
                                    'Retorno (%)': lucro
                                })
                                em_posicao = False
                                tipo_posicao = None
                    
                    if trades:
                        df_res = pd.DataFrame(trades)
                        m1, m2, m3 = st.columns(3)
                        acertos = len(df_res[df_res['Retorno (%)'] > 0])
                        m1.metric("Trades Realizados pela IA", len(df_res))
                        m2.metric("Taxa de Precisão (Win Rate)", f"{(acertos/len(df_res)*100):.1f}%")
                        m3.metric("Lucro Acumulado BRUTO", f"{df_res['Retorno (%)'].sum():.2f}%")
                        
                        df_res['Retorno (%)'] = df_res['Retorno (%)'].apply(lambda x: f"{x:.2f}%")
                        st.dataframe(df_res.style.map(lambda v: 'color: #28a745; font-weight: bold' if '-' not in str(v) else 'color: #dc3545; font-weight: bold', subset=['Retorno (%)']), use_container_width=True, hide_index=True)
                    else:
                        st.warning("Com essas calibragens severas da IA, nenhum trade foi fechado no histórico desse ativo.")
            except Exception as e:
                st.error(f"Erro ao processar: {e}")
