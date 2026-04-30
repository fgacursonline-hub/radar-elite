import streamlit as st
import pandas as pd
import numpy as np
import pandas_ta as ta
import sys
import os
import warnings

# ==============================================================================
# ESTRATÉGIA: HEIKEN ASHI + ICHIMOKU KINKO HYO (SISTEMA DE EQUILÍBRIO)
# DESENVOLVIDO PARA: CAÇADORES DE ELITE
# ==============================================================================

warnings.filterwarnings('ignore')

st.set_page_config(page_title="Heiken Ichimoku Elite", layout="wide", page_icon="⛩️")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial.")
    st.stop()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from config_ativos import bdrs_elite, ibrx_selecao, macro_elite
    from motor_dados import puxar_dados_blindados
    ativos_lista = sorted(list(set([a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)] + list(macro_elite.keys()))))
except ImportError:
    st.error("❌ Erro ao carregar dependências do sistema.")
    st.stop()

# ==============================================================================
# 1. MOTOR MATEMÁTICO (LÓGICA DO SET-UP)
# ==============================================================================
def calcular_heiken_ichimoku(df, tenkan=9, kijun=24, senkou_b=51, disp=24):
    if df is None or len(df) < senkou_b + disp: return None
    df = df.copy()
    
    # Padronização de Colunas
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]

    # --- CÁLCULO HEIKEN ASHI (O Filtro de Ruído) ---
    # As velas Heiken Ashi suavizam o preço para mostrar a tendência real.
    ha_df = ta.ha(df['open'], df['high'], df['low'], df['close'])
    df['ha_high'] = ha_df['HA_high']
    df['ha_low'] = ha_df['HA_low']
    df['ha_close'] = ha_df['HA_close']

    # --- CÁLCULO ICHIMOKU (A Estrutura de Equilíbrio) ---
    def donchian(len_p):
        return (df['high'].rolling(window=len_p).max() + df['low'].rolling(window=len_p).min()) / 2

    df['tenkan'] = donchian(tenkan)
    df['kijun'] = donchian(kijun)
    df['senkou_a'] = ((df['tenkan'] + df['kijun']) / 2).shift(disp)
    df['senkou_b'] = donchian(senkou_b).shift(disp)
    
    # Chikou Span: Fechamento atual deslocado para o passado (atraso de momentum)
    df['chikou'] = df['close'].shift(disp)
    
    # Limites da Nuvem (Kumo)
    df['senkou_h'] = df[['senkou_a', 'senkou_b']].max(axis=1)
    df['senkou_l'] = df[['senkou_a', 'senkou_b']].min(axis=1)

    # --- REGRAS DE ENTRADA (O GATILHO) ---
    # 1. Momentum HA: Máxima atual maior que as duas anteriores.
    cond_ha_long = df['ha_high'] > df['ha_high'].rolling(3).max().shift(1)
    # 2. Estrutura: Preço acima da Nuvem e acima do Chikou (momentum passado).
    cond_cloud_long = (df['close'] > df['senkou_h']) & (df['close'] > df['chikou'])
    # 3. Confirmação: Tenkan >= Kijun OU Preço acima da Kijun.
    cond_conf_long = (df['tenkan'] >= df['kijun']) | (df['close'] > df['kijun'])

    df['entry_long'] = cond_ha_long & cond_cloud_long & cond_conf_long

    # --- REGRAS DE SAÍDA (A PROTEÇÃO) ---
    # Saída se a mínima HA cair ou se o preço perder qualquer suporte importante do Ichimoku.
    cond_ha_exit = df['ha_low'] < df['ha_low'].rolling(3).min().shift(1)
    cond_ichimoku_exit = (df['tenkan'] < df['kijun']) | (df['close'] < df['senkou_a']) | (df['close'] < df['kijun'])
    
    df['exit_long'] = cond_ha_exit & cond_ichimoku_exit
    
    return df.dropna(subset=['tenkan', 'kijun', 'senkou_a'])

# ==============================================================================
# 2. INTERFACE E EXPLICAÇÃO
# ==============================================================================
st.title("⛩️ Heiken Ashi + Ichimoku Elite")

with st.expander("📖 METODOLOGIA: Como este setup funciona?"):
    st.markdown("""
    ### 🛡️ O Filtro de Ruído (Heiken Ashi)
    Diferente das velas comuns, as velas **Heiken Ashi** calculam uma média de preços. Isso elimina os "gaps" e as oscilações falsas. 
    O sistema só autoriza a compra quando a **máxima** da vela Heiken Ashi rompe a máxima das duas velas anteriores, confirmando força compradora real.

    ### ☁️ O Equilíbrio (Ichimoku Kinko Hyo)
    O preço deve estar "limpo" para subir. Por isso, exigimos:
    1. **Preço acima da Nuvem (Kumo):** Indica que não há resistências históricas no caminho.
    2. **Chikou Span:** O preço atual deve ser maior que o preço de 24 períodos atrás, confirmando que estamos em um ciclo de expansão.
    3. **Tenkan vs Kijun:** A linha rápida deve estar acima da linha média para garantir o momentum.

    ### 🚨 Saída Rigorosa
    Este setup é projetado para **não devolver lucro**. Se a mínima da Heiken Ashi cair ou se o preço furar a linha Kijun, o robô encerra a posição na hora.
    """)

# Parâmetros
with st.container(border=True):
    st.markdown("#### ⚙️ Ajustes do Caçador")
    c1, c2, c3, c4 = st.columns(4)
    p_tenkan = c1.number_input("Tenkan (Rápida):", 9)
    p_kijun = c2.number_input("Kijun (Média):", 24)
    p_senkou = c3.number_input("Senkou B (Lenta):", 51)
    p_disp = c4.number_input("Deslocamento:", 24)

aba_radar, aba_test = st.tabs(["📡 Radar de Tendência", "🔬 Raio-X Detalhado"])

with aba_radar:
    r1, r2 = st.columns(2)
    lista_r = r1.selectbox("Lista:", ["BDRs Elite", "IBrX Seleção", "Cripto/Macros"])
    tempo_r = r2.selectbox("Tempo Gráfico:", ['60m', '1d', '1wk'], index=1)
    
    if st.button("🚀 Escanear Mercado", type="primary", use_container_width=True):
        ativos_tr = bdrs_elite if lista_r == "BDRs Elite" else ibrx_selecao if lista_r == "IBrX Seleção" else list(macro_elite.keys())
        ativos_tr = sorted(list(set([a.replace('.SA', '') for a in ativos_tr])))
        ls_res = []
        p_bar = st.progress(0)
        
        for idx, ativo in enumerate(ativos_tr):
            p_bar.progress((idx + 1) / len(ativos_tr))
            try:
                df_cru = puxar_dados_blindados(ativo, tempo_r)
                df = calcular_heiken_ichimoku(df_cru, p_tenkan, p_kijun, p_senkou, p_disp)
                if df is not None:
                    hoje = df.iloc[-1]
                    if hoje['entry_long']: status = "🟢 COMPRA CONFIRMADA"
                    elif hoje['close'] > hoje['senkou_h'] and hoje['tenkan'] > hoje['kijun']: status = "📈 Tendência Forte"
                    elif hoje['close'] < hoje['senkou_l']: status = "📉 Baixa Confirmada"
                    else: status = "🟡 Consolidação"
                    
                    ls_res.append({'Ativo': ativo, 'Preço': f"R$ {hoje['close']:.2f}", 'Status': status, 'Nuvem Topo': f"{hoje['senkou_h']:.2f}"})
            except: pass
        
        p_bar.empty()
        if ls_res:
            st.dataframe(pd.DataFrame(ls_res), use_container_width=True, hide_index=True)

with aba_test:
    t1, t2 = st.columns(2)
    atv_test = t1.selectbox("Selecione o Ativo:", ativos_lista)
    tmp_test = t2.selectbox("Tempo Gráfico Teste:", ['60m', '1d', '1wk'], index=1, key='ha_test')
    
    if st.button("📊 Rodar Backtest Heiken-Ichimoku", type="primary", use_container_width=True):
        try:
            df_cru = puxar_dados_blindados(atv_test, tmp_test)
            df = calcular_heiken_ichimoku(df_cru, p_tenkan, p_kijun, p_senkou, p_disp)
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
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Trades", len(df_res))
                    m2.metric("Win Rate", f"{(len(df_res[df_res['Retorno (%)'] > 0])/len(df_res)*100):.1f}%")
                    m3.metric("Lucro Acumulado", f"{df_res['Retorno (%)'].sum():.2f}%")
                    st.dataframe(df_res, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Erro: {e}")
