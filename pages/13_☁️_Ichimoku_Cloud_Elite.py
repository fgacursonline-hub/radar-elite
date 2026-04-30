import streamlit as st
import pandas as pd
import numpy as np
import pandas_ta as ta
import sys
import os
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. CONFIGURAÇÃO E LOGIN
# ==========================================
st.set_page_config(page_title="Ichimoku TK Elite", layout="wide", page_icon="☁️")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial.")
    st.stop()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from config_ativos import bdrs_elite, ibrx_selecao, macro_elite
    from motor_dados import puxar_dados_blindados
except ImportError:
    st.error("❌ Erro ao carregar as listas de ativos do Bunker.")
    st.stop()

ativos_lista = sorted(list(set([a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)] + list(macro_elite.keys()))))

# ==========================================
# 2. MOTOR MATEMÁTICO DINÂMICO
# ==========================================
def calcular_ichimoku_tk(df, tenkan=20, kijun=60, senkou=120, displacement=30, ema_p=200):
    if df is None or len(df) < 5: return None
    df = df.copy()
    
    # Padronização de Colunas para evitar erro 'high'
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    
    def donchian(len_p):
        return (df['high'].rolling(window=len_p, min_periods=1).max() + 
                df['low'].rolling(window=len_p, min_periods=1).min()) / 2

    df['tenkan_sen'] = donchian(tenkan)
    df['kijun_sen'] = donchian(kijun)
    
    # CÁLCULO DA MÉDIA COM O VALOR QUE VOCÊ ESCOLHER NA TELA
    ema_series = ta.ema(df['close'], length=ema_p)
    df['ma_filtro'] = ema_series.bfill() if ema_series is not None else df['close']
    
    # Cruzamentos
    df['tk_cross_up'] = (df['tenkan_sen'] > df['kijun_sen']) & (df['tenkan_sen'].shift(1) <= df['kijun_sen'].shift(1))
    df['tk_cross_down'] = (df['tenkan_sen'] < df['kijun_sen']) & (df['tenkan_sen'].shift(1) >= df['kijun_sen'].shift(1))
    
    # Gatilhos
    df['entry_long'] = (df['tenkan_sen'] > df['kijun_sen']) & (df['close'] > df['ma_filtro']) & df['tk_cross_up']
    df['exit_long'] = df['tk_cross_down']
    
    return df

# ==========================================
# 3. INTERFACE (AGORA COM MÉDIA LIBERADA)
# ==========================================
st.title("☁️ Ichimoku Cloud + Filtro Móvel")

with st.container(border=True):
    st.markdown("#### ⚙️ Parâmetros do Setup")
    c1, c2, c3, c4, c5 = st.columns(5)
    p_tenkan = c1.number_input("Tenkan:", value=20, min_value=1)
    p_kijun = c2.number_input("Kijun:", value=60, min_value=1)
    p_senkou = c3.number_input("Senkou B:", value=120, min_value=1)
    p_disp = c4.number_input("Deslocamento:", value=30, min_value=0)
    
    # AQUI ESTÁ A MUDANÇA: min_value=1 permite você descer o quanto quiser!
    p_ema = c5.number_input("Média Filtro:", value=200, min_value=1, step=1)

aba_radar, aba_test = st.tabs(["📡 Radar de Mercado", "🔬 Backtest Individual"])

with aba_radar:
    r1, r2 = st.columns(2)
    lista_r = r1.selectbox("Lista:", ["BDRs Elite", "IBrX Seleção", "Cripto/Macros"])
    tempo_r = r2.selectbox("Tempo Gráfico:", ['60m', '1d', '1wk'], index=1)
    
    if st.button("🚀 Iniciar Escaneamento", type="primary", use_container_width=True):
        ativos_tr = bdrs_elite if lista_r == "BDRs Elite" else ibrx_selecao if lista_r == "IBrX Seleção" else list(macro_elite.keys())
        ativos_tr = sorted(list(set([a.replace('.SA', '') for a in ativos_tr])))
        
        ls_res = []
        p_bar = st.progress(0); s_text = st.empty()
        
        for idx, ativo in enumerate(ativos_tr):
            s_text.text(f"Analisando {ativo}...")
            p_bar.progress((idx + 1) / len(ativos_tr))
            try:
                df_cru = puxar_dados_blindados(ativo, tempo_r)
                df = calcular_ichimoku_tk(df_cru, p_tenkan, p_kijun, p_senkou, p_disp, p_ema)
                
                if df is not None:
                    hoje = df.iloc[-1]
                    if hoje['entry_long']: status = "🟢 COMPRA"
                    elif hoje['tenkan_sen'] > hoje['kijun_sen'] and hoje['close'] > hoje['ma_filtro']: status = "📈 Alta"
                    elif hoje['tenkan_sen'] < hoje['kijun_sen']: status = "📉 Baixa"
                    else: status = "🟡 Neutro"
                        
                    ls_res.append({
                        'Ativo': ativo, 'Preço': f"R$ {hoje['close']:.2f}",
                        'Status': status, f'Média ({p_ema})': f"{hoje['ma_filtro']:.2f}"
                    })
            except: pass
        
        s_text.empty(); p_bar.empty()
        if ls_res:
            st.dataframe(pd.DataFrame(ls_res), use_container_width=True, hide_index=True)

# --- ABA DE BACKTEST RESTAURADA ---
with aba_test:
    t1, t2 = st.columns(2)
    atv_test = t1.selectbox("Selecione o Ativo:", ativos_lista)
    tmp_test = t2.selectbox("Tempo Gráfico:", ['60m', '1d', '1wk'], index=1, key='tk_test_aba')
    
    # O BOTÃO VOLTOU!
    if st.button("📊 Rodar Backtest Individual", type="primary", use_container_width=True):
        with st.spinner("Processando histórico..."):
            try:
                df_cru = puxar_dados_blindados(atv_test, tmp_test)
                df = calcular_ichimoku_tk(df_cru, p_tenkan, p_kijun, p_senkou, p_disp, p_ema)
                
                if df is not None:
                    trades, em_posicao = [], False
                    df_b = df.reset_index()
                    col_dt = df_b.columns[0]
                    
                    for i in range(1, len(df_b)):
                        candle = df_b.iloc[i]
                        if not em_posicao and candle['entry_long']:
                            em_posicao, preco_ent, data_ent = True, candle['close'], candle[col_dt]
                        elif em_posicao and candle['exit_long']:
                            lucro = ((candle['close'] / preco_ent) - 1) * 100
                            trades.append({'Entrada': data_ent.strftime('%d/%m/%Y'), 'Saída': candle[col_dt].strftime('%d/%m/%Y'), 'Retorno (%)': lucro})
                            em_posicao = False
                    
                    if trades:
                        df_res = pd.DataFrame(trades)
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Trades", len(df_res))
                        c2.metric("Win Rate", f"{(len(df_res[df_res['Retorno (%)'] > 0])/len(df_res)*100):.1f}%")
                        c3.metric("Lucro Total", f"{df_res['Retorno (%)'].sum():.2f}%")
                        st.dataframe(df_res, use_container_width=True, hide_index=True)
                    else:
                        st.warning("Nenhum sinal de compra encontrado para este ativo com esses parâmetros.")
            except Exception as e:
                st.error(f"Erro no Raio-X: {e}")
