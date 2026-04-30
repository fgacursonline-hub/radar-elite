import streamlit as st
import pandas as pd
import numpy as np
import pandas_ta as ta
from sklearn.neighbors import KNeighborsClassifier
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

b3_symbols = [a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)]
ativos_para_rastrear = sorted(list(set(b3_symbols + list(macro_elite.keys()))))

# ==========================================
# 2. O MOTOR MATEMÁTICO: AI SUPERTREND X PIVOT
# ==========================================
@st.cache_data(show_spinner=False, ttl=300)
def calcular_ai_supertrend_pivot(df, k=6, n_points=48, st_len=10, st_factor=3.5, 
                                 adx_len=14, use_adx=True, pivot_len=14):
    if df is None or len(df) < 150:
        raise ValueError("Histórico muito curto. O motor exige no mínimo 150 candles para treinar a IA.")
        
    df = df.copy()
    df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    if df.index.tz is not None: df.index = df.index.tz_localize(None)
    
    # 1. FILTRO DIRECIONAL: ADX & DMI
    adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=adx_len)
    if adx_df is not None:
        df['ADX'] = adx_df.iloc[:, 0].bfill()
        df['+DI'] = adx_df.iloc[:, 1].bfill()
        df['-DI'] = adx_df.iloc[:, 2].bfill()
    else:
        df['ADX'], df['+DI'], df['-DI'] = 0, 0, 0
    
    df['Long_ADX_Cond'] = (df['ADX'] > 20) & (df['+DI'] > df['-DI']) if use_adx else True
    df['Short_ADX_Cond'] = (df['ADX'] > 20) & (df['-DI'] > df['+DI']) if use_adx else True

    # 2. FUNDAÇÃO: SuperTrend Base (WMA)
    df['WMA_Base'] = ta.wma(df['Close'], length=st_len).bfill().fillna(df['Close'])
    atr = ta.atr(df['High'], df['Low'], df['Close'], length=st_len).bfill().fillna(df['High'] - df['Low'])
    
    st_upper = df['WMA_Base'] + (st_factor * atr)
    st_lower = df['WMA_Base'] - (st_factor * atr)
    
    supertrend = np.zeros(len(df))
    st_direction = np.zeros(len(df))
    
    # Prevenção rigorosa contra NaNs antes de virar numpy array
    up_arr = st_upper.bfill().fillna(df['Close']).values.copy()
    dn_arr = st_lower.bfill().fillna(df['Close']).values.copy()
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
    df['Price_Smoothed'] = ta.wma(df['Close'], length=10).bfill().fillna(df['Close'])
    df['ST_Smoothed'] = ta.wma(df['SuperTrend'], length=80).bfill().fillna(df['SuperTrend'])
    df['Label_Real'] = np.where(df['Price_Smoothed'] > df['ST_Smoothed'], 1, 0)
    
    ai_labels = np.zeros(len(df))
    
    for i in range(n_points, len(df)):
        X_train = df['SuperTrend'].iloc[i-n_points:i].values.reshape(-1, 1)
        y_train = df['Label_Real'].iloc[i-n_points:i].values
        X_test = np.array([[df['SuperTrend'].iloc[i]]])
        
        # Só treina se houver diversidade nos dados, senão copia o estado anterior
        if len(np.unique(y_train)) > 1:
            knn = KNeighborsClassifier(n_neighbors=k, weights='distance')
            try:
                knn.fit(X_train, y_train)
                ai_labels[i] = knn.predict(X_test)[0]
            except: ai_labels[i] = ai_labels[i-1]
        else:
            ai_labels[i] = y_train[0]
            
    df['AI_Label'] = ai_labels 

    # 4. GATILHO FINAL: Pivot Percentile
    lengths = [pivot_len * i for i in range(1, 8)]
    bull_score = np.zeros(len(df))
    bear_score = np.zeros(len(df))
    
    # Reduzindo a exigência de 144 para 50 períodos para evitar destruir dados curtos
    highest_high = df['High'].rolling(50, min_periods=1).quantile(0.75).bfill()
    lowest_low = df['Low'].rolling(50, min_periods=1).quantile(0.25).bfill()
    
    for l in lengths:
        p_high = df['High'].rolling(l, min_periods=1).quantile(0.75).bfill()
        p_low = df['Low'].rolling(l, min_periods=1).quantile(0.25).bfill()
        
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
    
    df.dropna(inplace=True)
    if df.empty:
        raise ValueError("O DataFrame ficou vazio após o processamento matemático.")
        
    return df

# ==========================================
# 3. INTERFACE PRINCIPAL E DASHBOARD
# ==========================================
st.title("🤖 Trend Machine AI (KNN + Pivot)")
st.info("💡 **Inteligência Artificial Algorítmica:** Este robô usa o algoritmo *K-Nearest Neighbors (KNN)* para avaliar os topos e fundos do passado e prever a continuidade da tendência.")

# --- BLOCO DE CALIBRAGEM ---
with st.container(border=True):
    st.markdown("#### ⚙️ Calibragem do Motor Quantitativo")
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.markdown("**Inteligência Artificial (KNN)**")
        p_k = st.number_input("Vizinhos (K):", value=6, step=1)
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
        p_use_adx = st.toggle("Usar Filtro ADX/DMI", value=False, help="Deixado desligado por padrão para facilitar o aparecimento de sinais iniciais.")
        p_adx_len = st.number_input("Período ADX:", value=14, step=1, disabled=not p_use_adx)


aba_radar, aba_raiox = st.tabs(["📡 Radar AI de Mercado", "🔬 Backtest de IA (Prova Real)"])

# --- ABA 1: RADAR DE MERCADO ---
with aba_radar:
    r1, r2 = st.columns(2)
    lista_r = r1.selectbox("Lista de Rastreio:", ["BDRs Elite", "IBrX Seleção", "Cripto/Macros", "Todos"])
    tempo_r = r2.selectbox("Tempo Gráfico:", ['60m', '1d', '1wk'], index=1)

    if st.button("🚀 Escanear Mercado com Inteligência Artificial", type="primary", use_container_width=True):
        if lista_r == "BDRs Elite": ativos_tr = bdrs_elite
        elif lista_r == "IBrX Seleção": ativos_tr = ibrx_selecao
        elif lista_r == "Cripto/Macros": ativos_tr = list(macro_elite.keys())
        else: ativos_tr = ativos_para_rastrear
            
        ativos_tr = sorted(list(set([a.replace('.SA', '') for a in ativos_tr])))
        
        ls_compras, ls_vendas = [], []
        p_bar = st.progress(0); s_text = st.empty()

        for idx, ativo in enumerate(ativos_tr):
            s_text.text(f"🤖 Analisando {ativo}...")
            p_bar.progress((idx + 1) / len(ativos_tr))
            
            # MODO DEBUG: Se der erro, ele vai aparecer na tela em vez de sumir silenciosamente
            try:
                df_cru = puxar_dados_blindados(ativo, tempo_r)
                df = calcular_ai_supertrend_pivot(df_cru, p_k, p_pts, p_st_len, p_st_fac, p_adx_len, p_use_adx, p_piv)
                
                hoje = df.iloc[-1]
                if hoje['Entry_Long']:
                    ls_compras.append({'Ativo': ativo, 'Preço (R$)': f"{hoje['Close']:.2f}", 'Score Pivô': f"{hoje['Pivot_Trend_Value']:.1f}"})
                elif hoje['Entry_Short']:
                    ls_vendas.append({'Ativo': ativo, 'Preço (R$)': f"{hoje['Close']:.2f}", 'Score Pivô': f"{hoje['Pivot_Trend_Value']:.1f}"})
            except Exception as e:
                st.error(f"Erro no ativo {ativo}: {e}")
            
        s_text.empty(); p_bar.empty()
        
        c_buy, c_sell = st.columns(2)
        with c_buy:
            st.success("🟢 **SINAIS DE COMPRA**")
            if ls_compras: st.dataframe(pd.DataFrame(ls_compras), use_container_width=True, hide_index=True)
            else: st.write("A IA não autorizou compras.")
            
        with c_sell:
            st.error("🔴 **SINAIS DE VENDA / SHORT**")
            if ls_vendas: st.dataframe(pd.DataFrame(ls_vendas), use_container_width=True, hide_index=True)
            else: st.write("A IA não autorizou vendas.")

# --- ABA 2: BACKTEST INDIVIDUAL ---
with aba_raiox:
    c1, c2 = st.columns(2)
    atv_rx = c1.selectbox("Ativo a Testar na IA:", ativos_para_rastrear)
    tmp_rx = c2.selectbox("Tempo Gráfico (Backtest):", ['60m', '1d', '1wk'], index=1)
    
    if st.button("🔬 Rodar Backtest com a IA", type="primary", use_container_width=True):
        with st.spinner("A IA está processando o histórico..."):
            try:
                df_cru = puxar_dados_blindados(atv_rx, tmp_rx)
                df = calcular_ai_supertrend_pivot(df_cru, p_k, p_pts, p_st_len, p_st_fac, p_adx_len, p_use_adx, p_piv)
                
                trades = []
                em_posicao = False
                tipo_posicao = None  
                preco_ent = 0
                
                df_b = df.reset_index()
                col_dt = df_b.columns[0]
                
                for i in range(1, len(df_b)):
                    candle = df_b.iloc[i]
                    
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
                                'Operação': '🟢 Compra' if tipo_posicao == 'Long' else '🔴 Venda',
                                'Entrada': data_ent.strftime('%d/%m/%Y'),
                                'Saída': candle[col_dt].strftime('%d/%m/%Y'),
                                'Retorno (%)': lucro
                            })
                            em_posicao = False
                
                if trades:
                    df_res = pd.DataFrame(trades)
                    m1, m2, m3 = st.columns(3)
                    acertos = len(df_res[df_res['Retorno (%)'] > 0])
                    m1.metric("Trades Realizados", len(df_res))
                    m2.metric("Win Rate", f"{(acertos/len(df_res)*100):.1f}%")
                    m3.metric("Lucro Acumulado BRUTO", f"{df_res['Retorno (%)'].sum():.2f}%")
                    
                    df_res['Retorno (%)'] = df_res['Retorno (%)'].apply(lambda x: f"{x:.2f}%")
                    st.dataframe(df_res.style.map(lambda v: 'color: #28a745; font-weight: bold' if '-' not in str(v) else 'color: #dc3545; font-weight: bold', subset=['Retorno (%)']), use_container_width=True, hide_index=True)
                else:
                    st.warning("Com essas calibragens, a IA não encontrou nenhum trade finalizado.")
            except Exception as e:
                # O ERRO AGORA APARECE NA TELA PARA VOCÊ LER
                st.error(f"Ocorreu um erro no processamento: {e}")
