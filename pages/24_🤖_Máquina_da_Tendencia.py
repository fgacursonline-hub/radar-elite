import streamlit as st, pandas as pd, pandas_ta as ta, numpy as np, sys, os
import plotly.graph_objects as go
import warnings, traceback

warnings.filterwarnings('ignore')
st.set_page_config(page_title="Máquina Profit V7", layout="wide", page_icon="🛡️")

# --- CORREÇÃO DO CAMINHO DO BUNKER (Apenas 1 nível: '..') ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from bunker import motor_busca
except Exception as e:
    st.error("🚨 Erro Crítico: O arquivo 'bunker.py' não foi encontrado na pasta raiz.")
    st.stop()

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("Por favor, faça login na Home.")
    st.stop()

# --- TRADUTOR DE COLUNAS (O ESCUDO ANTI-ERRO SILENCIOSO) ---
def padronizar_df(df):
    if df is None or df.empty: return None
    df.columns = df.columns.str.lower()
    df.rename(columns={'abertura':'open', 'maxima':'high', 'minima':'low', 'fechamento':'close', 'fech':'close'}, inplace=True)
    return df

# --- MOTOR MATEMÁTICO ---
def calc_rma(series, length):
    alpha = 1.0 / length
    rma = np.full_like(series, np.nan, dtype=float)
    idx = np.where(~np.isnan(series))[0]
    if len(idx) == 0 or len(series) < idx[0] + length: return rma
    start = idx[0]
    rma[start + length - 1] = np.mean(series[start : start + length])
    for i in range(start + length, len(series)):
        rma[i] = rma[i-1] if np.isnan(series[i]) else alpha * series[i] + (1 - alpha) * rma[i-1]
    return rma

def processar_estrategia(df, p_di, p_adx, s_adx, m_adx, p_st, m_st):
    df = padronizar_df(df)
    if df is None or len(df) < 50: return None
    
    # 1. DMI 
    dmi_raw = ta.adx(df['high'], df['low'], df['close'], length=p_di)
    if dmi_raw is None or dmi_raw.empty: return None
    
    df['pDI'] = dmi_raw.iloc[:, 1] 
    df['mDI'] = dmi_raw.iloc[:, 2] 
    
    # 2. ADX 
    dx = 100 * np.abs(df['pDI'] - df['mDI']) / (df['pDI'] + df['mDI'])
    if m_adx == 'rma': df['adx_line'] = calc_rma(dx, s_adx)
    elif m_adx == 'sma': df['adx_line'] = ta.sma(dx, s_adx)
    else: df['adx_line'] = ta.ema(dx, s_adx)
    
    # 3. SuperTrend
    st_df = ta.supertrend(df['high'], df['low'], df['close'], length=p_st, multiplier=m_st)
    df['st_dir'] = st_df.iloc[:, 1]
    df['st_value'] = st_df.iloc[:, 0] 
    
    # Memória
    df['adx_o'] = df['adx_line'].shift(1)
    df['mdi_o'] = df['mDI'].shift(1)
    return df.dropna()

# --- FUNÇÃO DO GRÁFICO INTERATIVO ---
def plotar_grafico(df_b, trades_df):
    fig = go.Figure()
    col_data = df_b.columns[0] 

    # 1. Os Candles
    fig.add_trace(go.Candlestick(
        x=df_b[col_data],
        open=df_b['open'], high=df_b['high'], low=df_b['low'], close=df_b['close'],
        name='Preço'
    ))

    # 2. SuperTrend (Base Branca)
    fig.add_trace(go.Scatter(
        x=df_b[col_data], y=df_b['st_value'], mode='lines',
        name='SuperTrend', line=dict(width=1, color='rgba(255, 255, 255, 0.3)'), hoverinfo='skip'
    ))

    # 3. Colorindo o SuperTrend
    st_verde = df_b.copy()
    st_verde.loc[st_verde['st_dir'] == -1, 'st_value'] = np.nan
    st_vermelho = df_b.copy()
    st_vermelho.loc[st_vermelho['st_dir'] == 1, 'st_value'] = np.nan

    fig.add_trace(go.Scatter(x=st_verde[col_data], y=st_verde['st_value'], mode='lines', line=dict(color='lime', width=3), name='ST Alta'))
    fig.add_trace(go.Scatter(x=st_vermelho[col_data], y=st_vermelho['st_value'], mode='lines', line=dict(color='red', width=3), name='ST Baixa'))

    # 4. Marcando as Entradas
    if not trades_df.empty:
        try:
            entradas_plot = df_b[df_b[col_data].dt.strftime('%d/%m/%Y').isin(trades_df['Entrada'])]
            fig.add_trace(go.Scatter(
                x=entradas_plot[col_data],
                y=entradas_plot['low'] * 0.98,
                mode='markers',
                marker=dict(symbol='triangle-up', size=14, color='cyan', line=dict(width=2, color='white')),
                name='Sinal de Compra'
            ))
        except: pass

    fig.update_layout(
        title='Visão Gráfica: Ação do Preço + SuperTrend + Entradas do Robô',
        yaxis_title='Cotação',
        xaxis_rangeslider_visible=False,
        template='plotly_dark',
        height=600,
        margin=dict(l=20, r=20, t=50, b=20)
    )
    return fig

# --- INTERFACE PRINCIPAL ---
st.title("🛡️ MÁQUINA PROFIT V7 (Bunker Corrigido)")

with st.sidebar:
    st.header("⚙️ Calibragem Profit")
    p_di = st.number_input("DI Período (13)", value=13)
    p_adx = st.number_input("ADX Período (8)", value=8)
    s_adx = st.number_input("Suavização ADX (8)", value=8)
    m_adx = st.selectbox("Média ADX:", ['rma', 'sma', 'ema'])
    
    st.header("⚙️ SuperTrend")
    p_st = st.number_input("ST Período:", value=10)
    m_st = st.number_input("ST Multiplicador:", value=3.0)

aba_rx, aba_radar = st.tabs(["🔬 Raio-X com Gráfico", "📡 Varredura Geral"])

with aba_rx:
    c1, c2, c3 = st.columns(3)
    at_escolhido = c1.text_input("Ativo (Ex: GOGL34):", value="GOGL34").upper()
    tf_escolhido = c2.selectbox("Tempo Gráfico:", ['1d', '60m', '15m'], index=0)
    cap_inv = c3.number_input("Capital P/ Trade (R$):", value=10000.0)

    if st.button("🔍 PROCESSAR E DESENHAR GRÁFICO", use_container_width=True, type="primary"):
        with st.spinner("Conectando ao Bunker e renderizando os dados..."):
            try:
                df = motor_busca(at_escolhido, tf_escolhido)
                
                if df is not None and not df.empty:
                    df = processar_estrategia(df, p_di, p_adx, s_adx, m_adx, p_st, m_st)
                    
                    if df is None:
                        st.warning("O motor processou os dados, mas não havia histórico suficiente (mínimo 50 candles).")
                    else:
                        df_b = df.reset_index()
                        col_dt = df_b.columns[0]
                        trades, em_pos = [], False
                        
                        for i in range(1, len(df_b)):
                            cruzou = (df_b['adx_o'].iloc[i] <= df_b['mdi_o'].iloc[i]) and (df_b['adx_line'].iloc[i] > df_b['mDI'].iloc[i])
                            cond_compra = cruzou and (df_b['pDI'].iloc[i] > df_b['mDI'].iloc[i]) and (df_b['st_dir'].iloc[i] == 1)
                            
                            if not em_pos and cond_compra:
                                em_pos, data_e, preco_e = True, df_b[col_dt].iloc[i], df_b['close'].iloc[i]
                            
                            elif em_pos and (df_b['st_dir'].iloc[i] == -1 or i == len(df_b)-1):
                                lucro = cap_inv * ((df_b['close'].iloc[i] / preco_e) - 1)
                                trades.append({
                                    'Entrada': data_e.strftime('%d/%m/%Y'),
                                    'Saída': df_b[col_dt].iloc[i].strftime('%d/%m/%Y'),
                                    'Lucro R$': round(lucro, 2),
                                    'Status': '✅' if lucro > 0 else '❌'
                                })
                                em_pos = False
                        
                        trades_df = pd.DataFrame(trades)
                        
                        # Exibe o Gráfico primeiro
                        corte_visual = df_b.tail(200) # Mostra os últimos 200 candles pra não pesar
                        st.plotly_chart(plotar_grafico(corte_visual, trades_df), use_container_width=True)

                        # Exibe a Tabela
                        if trades:
                            st.dataframe(trades_df, use_container_width=True)
                            total = sum([t['Lucro R$'] for t in trades])
                            st.metric("Resultado Final Estimado", f"R$ {total:,.2f}")
                        else:
                            st.info("O gráfico foi renderizado, mas não houveram cruzamentos do ADX válidos neste período.")
                else:
                    st.error(f"O Bunker não retornou dados para o ativo {at_escolhido}. Verifique o ticker.")
                    
            except Exception as e:
                st.error("🚨 Ocorreu um erro interno. Capture a tela abaixo para diagnosticarmos:")
                st.code(traceback.format_exc())
