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
# 2. O MOTOR MATEMÁTICO ICHIMOKU (CORRIGIDO)
# ==========================================
def calcular_ichimoku_tk(df, tenkan=20, kijun=60, senkou=120, displacement=30, ema_p=200):
    if df is None or len(df) < max(senkou, ema_p): return None
    df = df.copy()
    
    # PADRONIZAÇÃO DE COLUNAS (Evita erro 'high', 'low', etc.)
    if isinstance(df.columns, pd.MultiIndex): 
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    
    # Garantir que temos as colunas necessárias
    colunas_necessarias = ['open', 'high', 'low', 'close']
    if not all(col in df.columns for col in colunas_necessarias):
        return None

    # Cálculos de Ichimoku
    def donchian(len_p):
        return (df['high'].rolling(window=len_p).max() + df['low'].rolling(window=len_p).min()) / 2

    df['tenkan_sen'] = donchian(tenkan)
    df['kijun_sen'] = donchian(kijun)
    
    # MÉDIA MÓVEL DINÂMICA (Livre para escolha)
    df['ma_filtro'] = ta.ema(df['close'], length=ema_p)
    
    # Senkou Span (Nuvem)
    df['senkou_a'] = ((df['tenkan_sen'] + df['kijun_sen']) / 2).shift(displacement)
    df['senkou_b'] = donchian(senkou).shift(displacement)
    
    # Sinais
    df['tk_cross_up'] = (df['tenkan_sen'] > df['kijun_sen']) & (df['tenkan_sen'].shift(1) <= df['kijun_sen'].shift(1))
    df['tk_cross_down'] = (df['tenkan_sen'] < df['kijun_sen']) & (df['tenkan_sen'].shift(1) >= df['kijun_sen'].shift(1))
    
    # Condição: TK Up + Acima da Média escolhida
    df['entry_long'] = (df['tenkan_sen'] > df['kijun_sen']) & (df['close'] > df['ma_filtro']) & df['tk_cross_up']
    df['exit_long'] = df['tk_cross_down']
    
    return df.dropna(subset=['tenkan_sen', 'kijun_sen', 'ma_filtro'])

# ==========================================
# 3. INTERFACE STREAMLIT
# ==========================================
st.title("☁️ Ichimoku Cloud + Filtro de Média")
st.info("💡 **Dica de Especialista:** O cruzamento Tenkan > Kijun acima da Média Móvel indica que o momentum de curto prazo venceu a resistência de médio prazo em um mercado de tendência definida.")

with st.container(border=True):
    st.markdown("#### ⚙️ Parâmetros da Nuvem e Filtro")
    c1, c2, c3, c4, c5 = st.columns(5)
    p_tenkan = c1.number_input("Tenkan (Conversão):", 20)
    p_kijun = c2.number_input("Kijun (Base):", 60)
    p_senkou = c3.number_input("Senkou B (Nuvem):", 120)
    p_disp = c4.number_input("Deslocamento:", 30)
    # AQUI ESTÁ A MÉDIA LIVRE
    p_ema = c5.number_input("Média Móvel (Filtro):", 200, help="Filtra a direção principal. Sugestões: 200 (Long Term), 50 (Mid Term).")

aba_radar, aba_test = st.tabs(["📡 Radar de Cruzamento TK", "🔬 Raio-X da Nuvem"])

# --- ABA 1: RADAR ---
with aba_radar:
    r1, r2 = st.columns(2)
    lista_r = r1.selectbox("Lista:", ["BDRs Elite", "IBrX Seleção", "Cripto/Macros"])
    tempo_r = r2.selectbox("Tempo Gráfico:", ['60m', '1d', '1wk'], index=1)
    
    if st.button("🚀 Escanear Sinais da Nuvem", type="primary", use_container_width=True):
        if lista_r == "BDRs Elite": ativos_tr = bdrs_elite
        elif lista_r == "IBrX Seleção": ativos_tr = ibrx_selecao
        else: ativos_tr = list(macro_elite.keys())
            
        ativos_tr = sorted(list(set([a.replace('.SA', '') for a in ativos_tr])))
        ls_res = []
        p_bar = st.progress(0)
        
        for idx, ativo in enumerate(ativos_tr):
            p_bar.progress((idx + 1) / len(ativos_tr))
            try:
                df_cru = puxar_dados_blindados(ativo, tempo_r)
                df = calcular_ichimoku_tk(df_cru, p_tenkan, p_kijun, p_senkou, p_disp, p_ema)
                if df is not None:
                    hoje = df.iloc[-1]
                    if hoje['entry_long']: status = "🟢 COMPRA (Novo Sinal)"
                    elif hoje['tenkan_sen'] > hoje['kijun_sen'] and hoje['close'] > hoje['ma_filtro']: status = "📈 Tendência de Alta"
                    elif hoje['tenkan_sen'] < hoje['kijun_sen']: status = "📉 Tendência de Baixa"
                    else: status = "🟡 Neutro"
                        
                    ls_res.append({
                        'Ativo': ativo, 'Preço': f"R$ {hoje['close']:.2f}",
                        'Status': status, f'Média ({p_ema})': f"{hoje['ma_filtro']:.2f}"
                    })
            except: pass
        
        p_bar.empty()
        if ls_res:
            st.dataframe(pd.DataFrame(ls_res), use_container_width=True, hide_index=True)

# --- ABA 2: BACKTEST ---
with aba_test:
    c1, c2 = st.columns(2)
    atv_test = c1.selectbox("Selecione o Ativo:", ativos_lista)
    tmp_test = c2.selectbox("Tempo Gráfico:", ['60m', '1d', '1wk'], index=1, key='tk_test')
    
    if st.button("📊 Rodar Backtest Ichimoku", type="primary", use_container_width=True):
        try:
            df_cru = puxar_dados_blindados(atv_test, tmp_test)
            df = calcular_ichimoku_tk(df_cru, p_tenkan, p_kijun, p_senkou, p_disp, p_ema)
            
            if df is not None:
                trades = []
                em_posicao = False
                for i in range(1, len(df)):
                    candle = df.iloc[i]
                    if not em_posicao and candle['entry_long']:
                        em_posicao = True
                        preco_ent = candle['close']
                        data_ent = df.index[i]
                    elif em_posicao and candle['exit_long']:
                        lucro = ((candle['close'] / preco_ent) - 1) * 100
                        trades.append({'Entrada': data_ent.strftime('%d/%m/%Y'), 'Saída': df.index[i].strftime('%d/%m/%Y'), 'Retorno (%)': lucro})
                        em_posicao = False
                
                if trades:
                    df_res = pd.DataFrame(trades)
                    st.metric("Retorno Acumulado", f"{df_res['Retorno (%)'].sum():.2f}%")
                    st.dataframe(df_res, use_container_width=True, hide_index=True)
                else: st.warning("Nenhum trade encontrado.")
        except Exception as e: st.error(f"Erro no processamento: {e}")
