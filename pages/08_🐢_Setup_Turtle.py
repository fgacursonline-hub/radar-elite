import streamlit as st
import pandas as pd
import pandas_ta as ta
import numpy as np
import sys
import os
import warnings
from datetime import datetime

warnings.filterwarnings('ignore')

# ==========================================
# 1. IMPORTAÇÃO E CONFIGURAÇÃO
# ==========================================
st.set_page_config(page_title="Turtle Strategy Elite", layout="wide", page_icon="🐢")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial.")
    st.stop()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from config_ativos import bdrs_elite, ibrx_selecao
    from motor_dados import puxar_dados_blindados # Usando seu motor padrão
except ImportError:
    st.error("❌ Erro ao carregar dependências.")
    st.stop()

ativos_para_rastrear = sorted(list(set([a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)])))

# ==========================================
# 2. MOTOR MATEMÁTICO TURTLE ELITE
# ==========================================
def calcular_turtle_elite(df, l1=20, l2=55, exit_p=10, mult_atr=2.0):
    if df is None or len(df) < max(l1, l2, exit_p): return None
    df = df.copy()
    
    # Padronização
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]

    # Canais de Donchian (Highs e Lows)
    df['l1_high'] = df['high'].rolling(window=l1).max().shift(1)
    df['l2_high'] = df['high'].rolling(window=l2).max().shift(1)
    df['exit_low'] = df['low'].rolling(window=exit_p).min().shift(1)
    
    # Volatilidade (N)
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=20)
    
    return df

# ==========================================
# 3. INTERFACE STREAMLIT
# ==========================================
st.title("🐢 Turtle Strategy: Sistema de Elite")
st.info("Estratégia baseada no experimento original das Tartarugas: Compre força e proteja o capital com volatilidade.")

with st.container(border=True):
    st.markdown("#### ⚙️ Parâmetros do Caçador")
    c1, c2, c3, c4 = st.columns(4)
    p_l1 = c1.number_input("L1 (Curto):", 20)
    p_l2 = c2.number_input("L2 (Longo):", 55)
    p_exit = c3.number_input("Saída (Donchian):", 10)
    p_atr = c4.number_input("Multiplicador ATR:", 2.0)

    st.markdown("#### 🛡️ Filtros Opcionais (Regras de Ouro)")
    f1, f2 = st.columns(2)
    usar_filtro_win = f1.toggle("🚫 Pular L1 se o anterior foi GAIN", value=True, help="Evita entrar em rompimentos falsos logo após uma grande tendência.")
    usar_saida_donchian = f2.toggle("🛑 Usar Saída de 10 dias (Donchian)", value=True, help="Encerra o trade assim que o preço perde a mínima do canal de saída.")

aba_radar, aba_rx = st.tabs(["📡 Radar Global", "🔬 Raio-X de Tendência"])

# --- LÓGICA DO RADAR ---
with aba_radar:
    lista_sel = st.selectbox("Lista:", ["BDRs Elite", "IBrX Seleção"])
    tempo_r = st.selectbox("Tempo:", ['1d', '1wk'], index=0)
    
    if st.button("🚀 Iniciar Varredura de Elite", type="primary", use_container_width=True):
        ativos_tr = bdrs_elite if lista_sel == "BDRs Elite" else ibrx_selecao
        ativos_tr = sorted(list(set([a.replace('.SA', '') for a in ativos_tr])))
        
        ls_res = []
        p_bar = st.progress(0)
        
        for idx, ativo in enumerate(ativos_tr):
            p_bar.progress((idx + 1) / len(ativos_tr))
            try:
                df = puxar_dados_blindados(ativo, tempo_r)
                df = calcular_turtle_elite(df, p_l1, p_l2, p_exit, p_atr)
                
                if df is not None:
                    # Lógica simplificada de detecção para o Radar
                    hoje = df.iloc[-1]
                    ontem = df.iloc[-2]
                    
                    status = "🟡 Neutro"
                    # Verifica Rompimentos
                    rompeu_l1 = hoje['close'] > ontem['l1_high']
                    rompeu_l2 = hoje['close'] > ontem['l2_high']
                    
                    if rompeu_l2: status = "🟢 COMPRA (L2 - Forte)"
                    elif rompeu_l1: status = "🟢 COMPRA (L1 - Agressiva)"
                    elif hoje['close'] < ontem['exit_low']: status = "🔴 SAÍDA (Donchian)"
                    elif hoje['close'] > ontem['exit_low'] and hoje['close'] > ontem['l1_high']: status = "📈 Em Tendência"

                    ls_res.append({'Ativo': ativo, 'Preço': f"R$ {hoje['close']:.2f}", 'Status': status, 'ATR': f"{hoje['atr']:.2f}"})
            except: pass
            
        p_bar.empty()
        if ls_res: st.dataframe(pd.DataFrame(ls_res), use_container_width=True, hide_index=True)

# --- LÓGICA DO BACKTEST (COM FILTRO DE GAIN) ---
with aba_rx:
    atv_rx = st.selectbox("Ativo:", ativos_para_rastrear)
    
    if st.button("📊 Analisar Performance Turtle", type="primary", use_container_width=True):
        try:
            df = puxar_dados_blindados(atv_rx, '1d')
            df = calcular_turtle_elite(df, p_l1, p_l2, p_exit, p_atr)
            
            if df is not None:
                trades, em_posicao = [], False
                last_was_win = False # Controlador do filtro
                
                for i in range(1, len(df)):
                    candle = df.iloc[i]
                    ontem = df.iloc[i-1]
                    
                    # Entrada
                    if not em_posicao:
                        pode_l1 = (not usar_filtro_win) or (not last_was_win)
                        rompeu_l1 = candle['close'] > ontem['l1_high']
                        rompeu_l2 = candle['close'] > ontem['l2_high']
                        
                        # Regra: Entra se L2 (independente de win) OU se L1 (se win for falso)
                        if rompeu_l2 or (rompeu_l1 and pode_l1):
                            em_posicao = True
                            p_ent, d_ent = candle['close'], df.index[i]
                            stop_inicial = candle['close'] - (p_atr * candle['atr'])
                    
                    # Saída
                    elif em_posicao:
                        saiu_donchian = usar_saida_donchian and (candle['low'] < ontem['exit_low'])
                        saiu_stop = candle['low'] < stop_inicial
                        
                        if saiu_donchian or saiu_stop:
                            p_sai = ontem['exit_low'] if saiu_donchian else stop_inicial
                            lucro = ((p_sai / p_ent) - 1) * 100
                            trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': df.index[i].strftime('%d/%m/%Y'), 'Retorno (%)': lucro})
                            last_was_win = lucro > 0 # Atualiza para o próximo trade
                            em_posicao = False
                
                if trades:
                    df_res = pd.DataFrame(trades)
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Total Trades", len(df_res))
                    c2.metric("Win Rate", f"{(len(df_res[df_res['Retorno (%)'] > 0])/len(df_res)*100):.1f}%")
                    c3.metric("Resultado Total", f"{df_res['Retorno (%)'].sum():.2f}%")
                    st.dataframe(df_res, use_container_width=True, hide_index=True)
                else: st.warning("Nenhum trade encontrado.")
        except Exception as e: st.error(f"Erro: {e}")
