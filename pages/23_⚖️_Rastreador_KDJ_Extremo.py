import streamlit as st
import pandas as pd
import numpy as np
import time
import warnings
import sys
import os

warnings.filterwarnings('ignore')

# ==========================================
# 1. IMPORTAÇÃO CENTRALIZADA (ATIVOS E MOTOR)
# ==========================================
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from config_ativos import bdrs_elite, ibrx_selecao
except ImportError:
    st.error("❌ Arquivo 'config_ativos.py' não encontrado na raiz do projeto.")
    st.stop()

# 🔥 NOVO: IMPORTANDO O NOSSO MOTOR CENTRAL BLINDADO COM CACHE
try:
    from motor_dados import puxar_dados_blindados
except ImportError:
    st.error("❌ Arquivo 'motor_dados.py' não encontrado na raiz do projeto. Crie o Bunker de Dados primeiro.")
    st.stop()

ativos_para_rastrear = sorted(list(set([a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)])))

# ==========================================
# 2. CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="KDJ Extremo Elite", layout="wide", page_icon="⚖️")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

# ==========================================
# 3. MOTORES MATEMÁTICOS: KDJ + PRICE ACTION
# ==========================================
def calcular_kdj(df, ilong=41, isig=31):
    if df is None or df.empty or len(df) < ilong:
        return None
    
    df['h_max'] = df['High'].rolling(window=ilong).max()
    df['l_min'] = df['Low'].rolling(window=ilong).min()
    
    df['h_l_range'] = df['h_max'] - df['l_min']
    df['h_l_range'] = df['h_l_range'].replace(0, 0.00001)
    
    df['RSV'] = 100 * ((df['Close'] - df['l_min']) / df['h_l_range'])
    
    alpha_suavizacao = 1 / isig
    df['pK'] = df['RSV'].ewm(alpha=alpha_suavizacao, adjust=False).mean()
    df['pD'] = df['pK'].ewm(alpha=alpha_suavizacao, adjust=False).mean()
    
    df['pJ'] = 3 * df['pK'] - 2 * df['pD']
    
    return df

def escanear_reversao_basica(df):
    if df is None or df.empty or len(df) < 5: return []
    
    O, C, H, L = df['Open'], df['Close'], df['High'], df['Low']
    O1, C1, H1, L1 = O.shift(1), C.shift(1), H.shift(1), L.shift(1)
    O2, C2 = O.shift(2), C.shift(2)
    
    body = abs(C - O)
    
    p = []
    if ((C1 < O1) & (C > O) & (C >= O1) & (O <= C1)).iloc[-1]: p.append('Engolfo de Alta')
    if ((C1 < O1) & (C > O) & (C < O1) & (O > C1)).iloc[-1]: p.append('Harami de Alta')
    if (((H - L) > 3 * body) & (((C - L) / (0.001 + H - L)) > 0.6) & (((O - L) / (0.001 + H - L)) > 0.6)).iloc[-1]: p.append('Martelo')
    if ((C2 < O2) & (abs(C1-O1) < (H1-L1)*0.3) & (C > O) & (C > C2)).iloc[-1]: p.append('Estrela da Manhã')
    
    if ((C1 > O1) & (C < O) & (O >= C1) & (C <= O1)).iloc[-1]: p.append('Engolfo de Baixa')
    if ((C1 > O1) & (C < O) & (C > O1) & (O < C1)).iloc[-1]: p.append('Harami de Baixa')
    if (((H - L) > 3 * body) & (((H - C) / (0.001 + H - L)) > 0.6) & (((H - O) / (0.001 + H - L)) > 0.6)).iloc[-1]: p.append('Estrela Cadente')
    if ((C2 > O2) & (abs(C1-O1) < (H1-L1)*0.3) & (C < O) & (C < C2)).iloc[-1]: p.append('Estrela da Noite')
    
    return p

# ==========================================
# 4. INTERFACE CAÇADORES DE ELITE
# ==========================================
st.title("⚖️ Radar KDJ: Caçador de Extremos")
st.markdown("A Linha J multiplicada rastreia matematicamente a zona invisível de pânico institucional (sobrevenda) e euforia irracional (sobrecompra).")

with st.expander("📖 Manual Tático: Pânico, Euforia e Linha J"):
    st.markdown("""
    * **Pânico Absoluto ($J \leq 5$):** O ativo apanhou tanto que o elástico está prestes a arrebentar para baixo. Excelente zona para caçar fundos com Candlesticks de Alta.
    * **Euforia Irracional ($J \geq 95$):** O ativo subiu reto e a ganância dominou o varejo. Zona de perigo máximo. Grandes players estão prestes a despejar ordens de venda.
    """)

with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        lista_sel = st.selectbox("Alvo da Varredura:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"])
        tempo_grafico = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x])
    with col2:
        st.markdown("**Configurações do Gatilho:**")
        exigir_candle = st.toggle("🛡️ Exigir Candlestick de Reversão", value=False)
        
        c_kdj1, c_kdj2 = st.columns(2)
        with c_kdj1: nivel_panico = st.number_input("Nível de Pânico (J <)", value=5.0, step=1.0)
        with c_kdj2: nivel_euforia = st.number_input("Nível de Euforia (J >)", value=95.0, step=1.0)
        
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    btn_iniciar = st.button("⚖️ Iniciar Varredura de Extremos", type="primary", use_container_width=True)

if btn_iniciar:
    ativos_analise = bdrs_elite if lista_sel == "BDRs Elite" else ibrx_selecao if lista_sel == "IBrX Seleção" else bdrs_elite + ibrx_selecao
    ativos_analise = sorted(list(set([a.replace('.SA', '') for a in ativos_analise])))
    
    resultados_panico = []
    resultados_euforia = []
    
    p_bar = st.progress(0)
    s_text = st.empty()

    for idx, ativo in enumerate(ativos_analise):
        s_text.text(f"🔍 Medindo a tensão do elástico: {ativo} ({idx+1}/{len(ativos_analise)})")
        p_bar.progress((idx + 1) / len(ativos_analise))

        try:
            # 🔥 NOVO: CHAMADA ÚNICA PARA O MOTOR CENTRAL BLINDADO!
            # Substituímos toda a lógica de conexão por esta única linha protegida por Cache.
            df = puxar_dados_blindados(ativo, tempo_grafico=tempo_grafico, barras=150)
            
            if df is not None and not df.empty:
                df = calcular_kdj(df)
                if df is None: continue
                
                linha_atual = df.iloc[-1]
                valor_j = linha_atual['pJ']
                
                is_panico = valor_j <= nivel_panico
                is_euforia = valor_j >= nivel_euforia
                
                if is_panico or is_euforia:
                    padroes = escanear_reversao_basica(df)
                    str_padroes = ", ".join(padroes) if padroes else "Nenhum Padrão"
                    
                    if exigir_candle and not padroes:
                        continue 
                    
                    dados = {
                        'Ativo': ativo,
                        'Cotação': f"R$ {linha_atual['Close']:.2f}",
                        'Linha J (Tensão)': f"{valor_j:.1f}",
                        'Status': '🟢 Pânico (Fundo)' if is_panico else '🔴 Euforia (Topo)',
                        'Price Action (Gatilho)': str_padroes,
                        '_J_Raw': valor_j
                    }
                    
                    if is_panico: resultados_panico.append(dados)
                    if is_euforia: resultados_euforia.append(dados)
                    
        except Exception as e: pass
        
        # Atraso só necessário se NÃO estiver lendo da memória. O motor central lida bem com a velocidade agora.
        time.sleep(0.01)

    s_text.empty()
    p_bar.empty()

    st.subheader("🟢 Oportunidades: Faca no Chão (Pânico Institucional)")
    if resultados_panico:
        df_p = pd.DataFrame(resultados_panico).sort_values(by='_J_Raw', ascending=True).drop(columns=['_J_Raw'])
        def colorir_compra(val):
            if isinstance(val, str) and val != "Nenhum Padrão" and "R$" not in val and "🟢" not in val: return 'color: #00FF00; font-weight: bold'
            return ''
        try: styled_p = df_p.style.map(colorir_compra, subset=['Price Action (Gatilho)'])
        except AttributeError: styled_p = df_p.style.applymap(colorir_compra, subset=['Price Action (Gatilho)'])
        st.dataframe(styled_p, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum ativo está sangrando o suficiente para ativar os radares de pânico neste momento.")

    st.subheader("🔴 Perigo: Esticamento Extremo (Euforia do Varejo)")
    if resultados_euforia:
        df_e = pd.DataFrame(resultados_euforia).sort_values(by='_J_Raw', ascending=False).drop(columns=['_J_Raw'])
        def colorir_venda(val):
            if isinstance(val, str) and val != "Nenhum Padrão" and "R$" not in val and "🔴" not in val: return 'color: #FF4D4D; font-weight: bold'
            return ''
        try: styled_e = df_e.style.map(colorir_venda, subset=['Price Action (Gatilho)'])
        except AttributeError: styled_e = df_e.style.applymap(colorir_venda, subset=['Price Action (Gatilho)'])
        st.dataframe(styled_e, use_container_width=True, hide_index=True)
    else:
        st.info("O mercado não apresenta picos de euforia irracional neste momento.")
