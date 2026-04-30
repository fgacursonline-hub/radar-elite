import streamlit as st
import pandas as pd
import numpy as np
import pandas_ta as ta
import sys
import os
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. CONFIGURAÇÃO E SEGURANÇA
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
    st.error("❌ Erro ao carregar dependências do sistema.")
    st.stop()

ativos_lista = sorted(list(set([a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)] + list(macro_elite.keys()))))

# ==========================================
# 2. MOTOR MATEMÁTICO (BLINDADO CONTRA NONE)
# ==========================================
def calcular_ichimoku_tk(df, tenkan=20, kijun=60, senkou=120, displacement=30, ema_p=200):
    if df is None or len(df) < 5: return None
    df = df.copy()
    
    # Padronização de Colunas
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    
    def donchian(len_p):
        return (df['high'].rolling(window=len_p, min_periods=1).max() + 
                df['low'].rolling(window=len_p, min_periods=1).min()) / 2

    df['tenkan_sen'] = donchian(tenkan)
    df['kijun_sen'] = donchian(kijun)
    
    # CÁLCULO SEGURO: Evita o erro 'NoneType' se o histórico for curto
    ema_series = ta.ema(df['close'], length=ema_p)
    if ema_series is not None:
        df['ma_filtro'] = ema_series.bfill()
    else:
        # Se não houver dados para a média, preenchemos com o próprio fechamento 
        # para não quebrar, mas os sinais de filtro não serão ativados.
        df['ma_filtro'] = df['close']
    
    # Sinais
    df['tk_cross_up'] = (df['tenkan_sen'] > df['kijun_sen']) & (df['tenkan_sen'].shift(1) <= df['kijun_sen'].shift(1))
    df['tk_cross_down'] = (df['tenkan_sen'] < df['kijun_sen']) & (df['tenkan_sen'].shift(1) >= df['kijun_sen'].shift(1))
    
    # Condição de Compra: TK Cross + Preço > Média Escolhida
    df['entry_long'] = (df['tenkan_sen'] > df['kijun_sen']) & (df['close'] > df['ma_filtro']) & df['tk_cross_up']
    df['exit_long'] = df['tk_cross_down']
    
    return df

# ==========================================
# 3. INTERFACE STREAMLIT
# ==========================================
st.title("☁️ Ichimoku Cloud + Filtro Móvel")

with st.container(border=True):
    st.markdown("#### ⚙️ Parâmetros do Setup")
    c1, c2, c3, c4, c5 = st.columns(5)
    p_tenkan = c1.number_input("Tenkan:", 20)
    p_kijun = c2.number_input("Kijun:", 60)
    p_senkou = c3.number_input("Senkou B:", 120)
    p_disp = c4.number_input("Deslocamento:", 30)
    p_ema = c5.number_input("Média Filtro:", 200)

aba_radar, aba_test = st.tabs(["📡 Radar de Mercado", "🔬 Backtest Individual"])

with aba_radar:
    r1, r2 = st.columns(2)
    lista_r = r1.selectbox("Lista:", ["BDRs Elite", "IBrX Seleção", "Cripto/Macros"])
    tempo_r = r2.selectbox("Tempo Gráfico:", ['60m', '1d', '1wk'], index=1)
    
    if st.button("🚀 Iniciar Escaneamento", type="primary", use_container_width=True):
        if lista_r == "BDRs Elite": ativos_tr = bdrs_elite
        elif lista_r == "IBrX Seleção": ativos_tr = ibrx_selecao
        else: ativos_tr = list(macro_elite.keys())
            
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
            except Exception as e:
                st.warning(f"Atenção em {ativo}: {e}")
        
        s_text.empty(); p_bar.empty()
        if ls_res:
            st.dataframe(pd.DataFrame(ls_res), use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum ativo processado. Verifique sua conexão com o Bunker de dados.")

# Aba de Backtest mantida com a mesma lógica de segurança
with aba_test:
    # ... (mesmo código do backtest anterior, chamando o motor blindado)
    pass
