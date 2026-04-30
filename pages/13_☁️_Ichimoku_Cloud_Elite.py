import streamlit as st
import pandas as pd
import numpy as np
import pandas_ta as ta
import sys
import os
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. CONFIGURAÇÃO E AMBIENTE
# ==========================================
st.set_page_config(page_title="Ichimoku TK Elite", layout="wide", page_icon="☁️")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial.")
    st.stop()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from config_ativos import bdrs_elite, ibrx_selecao, macro_elite
    from motor_dados import puxar_dados_blindados
    
    # --- A LINHA QUE FALTAVA ESTÁ AQUI ---
    ativos_lista = sorted(list(set([a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)] + list(macro_elite.keys()))))
except ImportError:
    st.error("❌ Erro ao carregar as listas de ativos do Bunker.")
    st.stop()

# ==========================================
# 2. MOTOR MATEMÁTICO ICHIMOKU
# ==========================================
def calcular_ichimoku_tk(df, tenkan=20, kijun=60, senkou=120, displacement=30, ema_p=200):
    if df is None or len(df) < 5: return None
    df = df.copy()
    
    # Padronização de colunas
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    
    def donchian(len_p):
        return (df['high'].rolling(window=len_p, min_periods=1).max() + 
                df['low'].rolling(window=len_p, min_periods=1).min()) / 2

    # Cálculo dos Componentes
    df['tenkan_sen'] = donchian(tenkan)
    df['kijun_sen'] = donchian(kijun)
    
    # Média Móvel como Filtro Institucional
    ema_series = ta.ema(df['close'], length=ema_p)
    df['ma_filtro'] = ema_series.bfill() if ema_series is not None else df['close']
    
    # Lógica de Cruzamento TK (Tenkan x Kijun)
    df['tk_cross_up'] = (df['tenkan_sen'] > df['kijun_sen']) & (df['tenkan_sen'].shift(1) <= df['kijun_sen'].shift(1))
    df['tk_cross_down'] = (df['tenkan_sen'] < df['kijun_sen']) & (df['tenkan_sen'].shift(1) >= df['kijun_sen'].shift(1))
    
    # Gatilho de Entrada
    df['entry_long'] = (df['tenkan_sen'] > df['kijun_sen']) & (df['close'] > df['ma_filtro']) & df['tk_cross_up']
    df['exit_long'] = df['tk_cross_down']
    
    return df

# ==========================================
# 3. INTERFACE VISUAL
# ==========================================
st.title("☁️ Ichimoku Cloud + Filtro Móvel")
st.info("Este setup utiliza o **Ichimoku Kinko Hyo** filtrado por uma Média Móvel para identificar o início de grandes tendências institucionais.")

# Painel de Parâmetros
with st.container(border=True):
    st.markdown("#### ⚙️ Calibragem do Setup")
    c1, c2, c3, c4, c5 = st.columns(5)
    p_tenkan = c1.number_input("Tenkan (Conversão):", 20, min_value=1)
    p_kijun = c2.number_input("Kijun (Base):", 60, min_value=1)
    p_senkou = c3.number_input("Senkou B (Nuvem):", 120, min_value=1)
    p_disp = c4.number_input("Deslocamento:", 30, min_value=0)
    p_ema = c5.number_input("Média de Filtro:", 50, min_value=1) # Sugestão: comece com 50

aba_radar, aba_test = st.tabs(["📡 Radar de Mercado", "🔬 Raio-X Individual"])

# --- ABA: RADAR ---
with aba_radar:
    r1, r2 = st.columns(2)
    lista_r = r1.selectbox("Selecione a Lista:", ["BDRs Elite", "IBrX Seleção", "Cripto/Macros"])
    tempo_r = r2.selectbox("Tempo Gráfico (Radar):", ['60m', '1d', '1wk'], index=1)
    
    if st.button("🚀 Iniciar Escaneamento", type="primary", use_container_width=True):
        if lista_r == "BDRs Elite": ativos_tr = bdrs_elite
        elif lista_r == "IBrX Seleção": ativos_tr = ibrx_selecao
        else: ativos_tr = list(macro_elite.keys())
            
        ativos_tr = sorted(list(set([a.replace('.SA', '') for a in ativos_tr])))
        ls_res = []
        p_bar = st.progress(0); s_text = st.empty()
        
        for idx, ativo in enumerate(ativos_tr):
            s_text.text(f"🤖 Analisando {ativo}...")
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
            
            st.markdown("---")
            with st.expander("📖 Guia de Leitura dos Resultados"):
                st.markdown(f"""
                ### Como ler este Radar?
                Este setup busca o "momentum" perfeito onde o preço vence a média de médio prazo e a tendência institucional.

                * **🟢 COMPRA:** O sinal exato! A linha azul (Tenkan) cruzou a vermelha (Kijun) para cima hoje, e o preço está acima da média de {p_ema}.
                * **📈 Alta:** O ativo já está subindo e o setup autoriza manter a posição.
                * **📉 Baixa:** O momentum virou para baixo. Indica fraqueza no curto prazo.
                * **🟡 Neutro:** O ativo está lateral ou "brigando" com a média de {p_ema}.
                """)

# --- ABA: BACKTEST ---
with aba_test:
    t1, t2 = st.columns(2)
    atv_test = t1.selectbox("Selecione o Ativo para Teste:", ativos_lista)
    tmp_test = t2.selectbox("Tempo Gráfico (Raio-X):", ['60m', '1d', '1wk'], index=1, key='tk_raiox')
    
    if st.button("📊 Rodar Raio-X Individual", type="primary", use_container_width=True):
        with st.spinner("Reconstruindo histórico operacional..."):
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
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Total Trades", len(df_res))
                        m2.metric("Assertividade", f"{(len(df_res[df_res['Retorno (%)'] > 0])/len(df_res)*100):.1f}%")
                        m3.metric("Lucro Total", f"{df_res['Retorno (%)'].sum():.2f}%")
                        st.dataframe(df_res, use_container_width=True, hide_index=True)
                    else:
                        st.warning("Nenhum sinal de compra completo encontrado com esses parâmetros.")
            except Exception as e:
                st.error(f"Erro no processamento: {e}")
