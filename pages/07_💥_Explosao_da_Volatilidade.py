import streamlit as st
from tvDatafeed import TvDatafeed, Interval
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
import warnings
import sys
import os

warnings.filterwarnings('ignore')

# ==========================================
# 1. IMPORTAÇÃO CENTRALIZADA DOS ATIVOS
# ==========================================
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from config_ativos import bdrs_elite, ibrx_selecao
except ImportError:
    st.error("❌ Arquivo 'config_ativos.py' não encontrado na raiz do projeto.")
    st.stop()

ativos_para_rastrear = sorted(list(set([a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)])))

# ==========================================
# 2. CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Squeeze Pro Elite", layout="wide", page_icon="💥")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

@st.cache_resource
def get_tv_connection():
    return TvDatafeed()

tv = get_tv_connection()

tradutor_intervalo = {
    '15m': Interval.in_15_minute,
    '60m': Interval.in_1_hour,
    '1d': Interval.in_daily,
    '1wk': Interval.in_weekly
}

# ==========================================
# 3. MOTOR MATEMÁTICO: TTM SQUEEZE PRO (REPLICAÇÃO EXATA)
# ==========================================
def calcular_squeeze_pro(df, length=20, bb_mult=2.0, kc_high=1.0, kc_mid=1.5, kc_low=2.0):
    try:
        if df.empty or len(df) < length * 2:
            return None
        
        # 1. Bandas de Bollinger
        df['BB_basis'] = ta.sma(df['Close'], length=length)
        df['BB_dev'] = bb_mult * df['Close'].rolling(window=length).std(ddof=0)
        df['BB_upper'] = df['BB_basis'] + df['BB_dev']
        df['BB_lower'] = df['BB_basis'] - df['BB_dev']
        
        # 2. Canais de Keltner (3 Níveis)
        df['TR'] = ta.true_range(df['High'], df['Low'], df['Close'])
        df['KC_basis'] = ta.sma(df['Close'], length=length)
        df['devKC'] = ta.sma(df['TR'], length=length)
        
        df['KC_upper_high'] = df['KC_basis'] + df['devKC'] * kc_high
        df['KC_lower_high'] = df['KC_basis'] - df['devKC'] * kc_high
        
        df['KC_upper_mid'] = df['KC_basis'] + df['devKC'] * kc_mid
        df['KC_lower_mid'] = df['KC_basis'] - df['devKC'] * kc_mid
        
        df['KC_upper_low'] = df['KC_basis'] + df['devKC'] * kc_low
        df['KC_lower_low'] = df['KC_basis'] - df['devKC'] * kc_low
        
        # 3. Condições da "Mola" (Squeeze) - Lógica original do Pine
        df['NoSqz'] = (df['BB_lower'] < df['KC_lower_low']) | (df['BB_upper'] > df['KC_upper_low'])
        df['LowSqz'] = (df['BB_lower'] >= df['KC_lower_low']) | (df['BB_upper'] <= df['KC_upper_low'])
        df['MidSqz'] = (df['BB_lower'] >= df['KC_lower_mid']) | (df['BB_upper'] <= df['KC_upper_mid'])
        df['HighSqz'] = (df['BB_lower'] >= df['KC_lower_high']) | (df['BB_upper'] <= df['KC_upper_high'])
        
        def classificar_mola(row):
            if row['HighSqz']: return '🟠 Extrema (High)'
            elif row['MidSqz']: return '🔴 Média (Mid)'
            elif row['LowSqz']: return '⚫ Leve (Low)'
            else: return '🟢 Mola Solta'
            
        df['Status_Mola'] = df.apply(classificar_mola, axis=1)
        
        # Gatilho de Disparo (Ontem estava comprimido, hoje soltou)
        df['Squeeze_Fired'] = df['NoSqz'] & (~df['NoSqz'].shift(1).fillna(True))
        
        # 4. Oscilador de Momento (Regressão Linear)
        highest_high = df['High'].rolling(window=length).max()
        lowest_low = df['Low'].rolling(window=length).min()
        avg_hl = (highest_high + lowest_low) / 2.0
        sma_close = ta.sma(df['Close'], length=length)
        math_avg = (avg_hl + sma_close) / 2.0
        
        delta = df['Close'] - math_avg
        df['MOM'] = ta.linreg(delta, length=length)
        df['MOM_prev'] = df['MOM'].shift(1)
        
        def classificar_momento(row):
            if pd.isna(row['MOM']) or pd.isna(row['MOM_prev']): return 'Aguardando'
            if row['MOM'] > 0:
                if row['MOM'] > row['MOM_prev']: return '🔵 Alta Acelerando'
                else: return '🟦 Alta Perdendo Força'
            else:
                if row['MOM'] < row['MOM_prev']: return '🔴 Baixa Acelerando'
                else: return '🟨 Baixa Perdendo Força'
                
        df['Cor_Momento'] = df.apply(classificar_momento, axis=1)
        
        return df.dropna().tail(1) # Retorna apenas a foto do último dia
    except Exception as e:
        return None

# ==========================================
# 4. INTERFACE DO CAÇADORES DE ELITE
# ==========================================
st.title("💥 Squeeze PRO: Caçadores de Elite")
st.markdown("O algoritmo rastreia o estrangulamento da volatilidade medindo o embate entre as Bandas de Bollinger e os Canais de Keltner. A Regressão Linear aponta para onde os institucionais vão explodir o preço.")

with st.expander("📖 Manual Tático: Como ler o Squeeze Pro"):
    st.markdown("""
    * **A Mola (Os Pontos):**
        * 🟠 **Extrema:** A panela de pressão vai explodir. Hora de colocar o ativo no radar de curtíssimo prazo.
        * 🔴 **Média / ⚫ Leve:** O mercado está dormindo e acumulando energia.
        * 🟢 **Mola Solta:** A ignição aconteceu. O preço rompeu as correntes.
    * **O Momento (O Histograma):**
        * 🔵 / 🟦 **Azul:** Direção projetada para CIMA.
        * 🔴 / 🟨 **Vermelho/Amarelo:** Direção projetada para BAIXO.
    """)

with st.container(border=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        lista_sel = st.selectbox("Alvo da Varredura:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"])
    with col2:
        tempo_grafico = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'})
    with col3:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        btn_iniciar = st.button("🚀 Iniciar Varredura PRO", type="primary", use_container_width=True)

if btn_iniciar:
    ativos_analise = bdrs_elite if lista_sel == "BDRs Elite" else ibrx_selecao if lista_sel == "IBrX Seleção" else bdrs_elite + ibrx_selecao
    ativos_analise = sorted(list(set([a.replace('.SA', '') for a in ativos_analise])))
    intervalo_tv = tradutor_intervalo.get(tempo_grafico, Interval.in_daily)
    
    resultados_explosao = []
    resultados_compressao = []
    
    p_bar = st.progress(0)
    s_text = st.empty()

    for idx, ativo in enumerate(ativos_analise):
        s_text.text(f"🔍 Medindo pressão institucional: {ativo} ({idx+1}/{len(ativos_analise)})")
        p_bar.progress((idx + 1) / len(ativos_analise))

        try:
            df = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=100)
            if df is not None and not df.empty:
                df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                
                # Aplica o motor do Squeeze Pro
                res = calcular_squeeze_pro(df)
                
                if res is not None and not res.empty:
                    linha = res.iloc[0]
                    dados = {
                        'Ativo': ativo,
                        'Cotação': f"R$ {linha['Close']:.2f}",
                        'Status da Mola': linha['Status_Mola'],
                        'Direção Institucional': linha['Cor_Momento'],
                        '_MOM': linha['MOM'] # Usado para ordenar a força oculta
                    }
                    
                    # Filtra: Ou explodiu hoje, ou está em compressão extrema preste a explodir
                    if linha['Squeeze_Fired']:
                        resultados_explosao.append(dados)
                    elif 'Extrema' in linha['Status_Mola'] or 'Média' in linha['Status_Mola']:
                        resultados_compressao.append(dados)
        except Exception as e: pass
        time.sleep(0.02)

    s_text.empty()
    p_bar.empty()

    # ------------------------------------
    # EXIBIÇÃO: IGNICÕES DE HOJE
    # ------------------------------------
    st.subheader("🔥 Gatilhos Disparados Hoje (Mola Solta)")
    if resultados_explosao:
        df_exp = pd.DataFrame(resultados_explosao).sort_values(by='_MOM', ascending=False).drop(columns=['_MOM'])
        
        def colorir_tabela(val):
            if isinstance(val, str):
                if '🟢' in val: return 'color: #00FF00; font-weight: bold'
                if '🔵' in val: return 'color: #00FFFF; font-weight: bold'
                if '🟦' in val: return 'color: #4169E1'
                if '🔴' in val: return 'color: #FF4D4D; font-weight: bold'
                if '🟨' in val: return 'color: #FFD700'
                if '🟠' in val: return 'color: #FFA500; font-weight: bold'
            return ''
            
        st.dataframe(df_exp.style.map(colorir_tabela, subset=['Status da Mola', 'Direção Institucional']), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma mola foi solta no pregão atual. O mercado está segurando o fôlego.")

    # ------------------------------------
    # EXIBIÇÃO: ALERTAS DE COMPRESSÃO (O RADAR)
    # ------------------------------------
    st.subheader("⚠️ Radar de Pressão: Explosão Iminente")
    if resultados_compressao:
        df_comp = pd.DataFrame(resultados_compressao).sort_values(by='Status da Mola').drop(columns=['_MOM'])
        st.dataframe(df_comp.style.map(colorir_tabela, subset=['Status da Mola', 'Direção Institucional']), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum ativo está em compressão perigosa no momento.")
