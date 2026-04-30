import streamlit as st
import pandas as pd
import numpy as np
import pandas_ta as ta
import sys
import os
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. SEGURANÇA E CONFIGURAÇÃO
# ==========================================
st.set_page_config(page_title="Ichimoku TK Elite", layout="wide", page_icon="☁️")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from config_ativos import bdrs_elite, ibrx_selecao, macro_elite
    from motor_dados import puxar_dados_blindados
except ImportError:
    st.error("❌ Erro ao carregar dependências do sistema.")
    st.stop()

ativos_lista = sorted(list(set([a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)] + list(macro_elite.keys()))))

# ==========================================
# 2. O MOTOR MATEMÁTICO ICHIMOKU
# ==========================================
def calcular_ichimoku_tk(df, tenkan=20, kijun=60, senkou=120, displacement=30):
    """
    Motor matemático Ichimoku com períodos customizados para filtragem institucional.
    """
    if df is None or len(df) < senkou: return None
    df = df.copy()
    
    # Cálculos de Ichimoku (High+Low / 2)
    def donchian(len_p):
        return (df['high'].rolling(window=len_p).max() + df['low'].rolling(window=len_p).min()) / 2

    df['Tenkan_sen'] = donchian(tenkan) # Conversion Line
    df['Kijun_sen'] = donchian(kijun)   # Base Line
    
    # EMA 200 como Filtro de Tendência Primária
    df['EMA200'] = ta.ema(df['close'], length=200)
    
    # Senkou Span A e B (A Nuvem)
    df['Senkou_A'] = ((df['Tenkan_sen'] + df['Kijun_sen']) / 2).shift(displacement)
    df['Senkou_B'] = donchian(senkou).shift(displacement)
    
    # --- REGRAS DE ENTRADA E SAÍDA ---
    # TK Cross: Tenkan cruzando Kijun para cima
    df['TK_Cross_Up'] = (df['Tenkan_sen'] > df['Kijun_sen']) & (df['Tenkan_sen'].shift(1) <= df['Kijun_sen'].shift(1))
    df['TK_Cross_Down'] = (df['Tenkan_sen'] < df['Kijun_sen']) & (df['Tenkan_sen'].shift(1) >= df['Kijun_sen'].shift(1))
    
    # Condição de Compra: TK Cross Up + Preço Acima da EMA 200
    df['Entry_Long'] = (df['Tenkan_sen'] > df['Kijun_sen']) & (df['close'] > df['EMA200']) & df['TK_Cross_Up']
    
    # Condição de Saída: TK Cross Down
    df['Exit_Long'] = df['TK_Cross_Down']
    
    return df.dropna(subset=['Tenkan_sen', 'Kijun_sen', 'EMA200'])

# ==========================================
# 3. INTERFACE STREAMLIT
# ==========================================
st.title("☁️ Ichimoku Cloud + EMA 200")
st.markdown("""
Esta estratégia utiliza o **Equilíbrio de Ichimoku** filtrado pela **Média de 200 períodos**. 
O objetivo é capturar o início de grandes tendências quando o momentum de curto prazo (Tenkan) vence o equilíbrio de médio prazo (Kijun).
""")

with st.container(border=True):
    st.markdown("#### ⚙️ Parâmetros da Nuvem")
    c1, c2, c3, c4 = st.columns(4)
    p_tenkan = c1.number_input("Tenkan (Conversão):", 20)
    p_kijun = c2.number_input("Kijun (Base):", 60)
    p_senkou = c3.number_input("Senkou B (Nuvem):", 120)
    p_disp = c4.number_input("Deslocamento:", 30)

aba_radar, aba_test = st.tabs(["📡 Radar de Cruzamento TK", "🔬 Raio-X da Nuvem"])

# --- ABA 1: RADAR ---
with aba_radar:
    r1, r2 = st.columns(2)
    lista_r = r1.selectbox("Lista:", ["BDRs Elite", "IBrX Seleção", "Cripto/Macros"])
    tempo_r = r2.selectbox("Tempo Gráfico:", ['60m', '1d', '1wk'], index=1)
    
    if st.button("🚀 Escanear Sinais da Nuvem", type="primary", use_container_width=True):
        ativos_tr = bdrs_elite if lista_r == "BDRs Elite" else ibrx_selecao if lista_r == "IBrX Seleção" else list(macro_elite.keys())
        ativos_tr = sorted(list(set([a.replace('.SA', '') for a in ativos_tr])))
        
        ls_res = []
        p_bar = st.progress(0)
        
        for idx, ativo in enumerate(ativos_tr):
            p_bar.progress((idx + 1) / len(ativos_tr))
            try:
                df_cru = puxar_dados_blindados(ativo, tempo_r)
                df = calcular_ichimoku_tk(df_cru, p_tenkan, p_kijun, p_senkou, p_disp)
                if df is not None:
                    hoje = df.iloc[-1]
                    # Verifica se deu entrada ou se está em tendência
                    if hoje['Entry_Long']:
                        status = "🟢 COMPRA (Novo Sinal)"
                    elif hoje['Tenkan_sen'] > hoje['Kijun_sen'] and hoje['close'] > hoje['EMA200']:
                        status = "📈 Tendência de Alta"
                    elif hoje['Tenkan_sen'] < hoje['Kijun_sen']:
                        status = "📉 Tendência de Baixa"
                    else:
                        status = "🟡 Neutro / Consolidação"
                        
                    ls_res.append({
                        'Ativo': ativo, 'Preço': f"R$ {hoje['close']:.2f}",
                        'Status': status, 'Tenkan': f"{hoje['Tenkan_sen']:.2f}", 'Kijun': f"{hoje['Kijun_sen']:.2f}"
                    })
            except: pass
        
        p_bar.empty()
        if ls_res:
            df_final = pd.DataFrame(ls_res)
            st.dataframe(df_final.style.applymap(
                lambda x: 'color: #28a745; font-weight: bold' if 'COMPRA' in str(x) else ('color: #dc3545' if 'Baixa' in str(x) else ''),
                subset=['Status']
            ), use_container_width=True, hide_index=True)

# --- ABA 2: BACKTEST ---
with aba_test:
    c1, c2 = st.columns(2)
    atv_test = c1.selectbox("Selecione o Ativo:", ativos_lista)
    tmp_test = c2.selectbox("Tempo Gráfico:", ['60m', '1d', '1wk'], index=1, key='tk_test')
    
    if st.button("📊 Rodar Backtest Ichimoku", type="primary", use_container_width=True):
        try:
            df_cru = puxar_dados_blindados(atv_test, tmp_test)
            df = calcular_ichimoku_tk(df_cru, p_tenkan, p_kijun, p_senkou, p_disp)
            
            if df is not None:
                trades = []
                em_posicao = False
                
                df_b = df.reset_index()
                col_dt = df_b.columns[0]
                
                for i in range(1, len(df_b)):
                    candle = df_b.iloc[i]
                    if not em_posicao and candle['Entry_Long']:
                        em_posicao = True
                        preco_ent = candle['close']
                        data_ent = candle[col_dt]
                    elif em_posicao and candle['Exit_Long']:
                        lucro = ((candle['close'] / preco_ent) - 1) * 100
                        trades.append({
                            'Entrada': data_ent.strftime('%d/%m/%Y'),
                            'Saída': candle[col_dt].strftime('%d/%m/%Y'),
                            'Retorno (%)': lucro
                        })
                        em_posicao = False
                
                if trades:
                    df_res = pd.DataFrame(trades)
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Total Trades", len(df_res))
                    m2.metric("Win Rate", f"{(len(df_res[df_res['Retorno (%)'] > 0])/len(df_res)*100):.1f}%")
                    m3.metric("Retorno Acumulado", f"{df_res['Retorno (%)'].sum():.2f}%")
                    st.dataframe(df_res, use_container_width=True)
                else:
                    st.warning("Nenhum trade completo encontrado no histórico.")
        except Exception as e:
            st.error(f"Erro: {e}")
