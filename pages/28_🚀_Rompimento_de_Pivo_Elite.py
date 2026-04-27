import streamlit as st
import pandas as pd
import pandas_ta as ta
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
    st.error("❌ Arquivo 'config_ativos.py' não encontrado.")
    st.stop()

try:
    from motor_dados import puxar_dados_blindados
except ImportError:
    st.error("❌ Arquivo 'motor_dados.py' não encontrado.")
    st.stop()

todos_ativos = sorted(list(set([a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)])))

# ==========================================
# 2. MOTOR MATEMÁTICO: PIVOT BREAKOUT
# ==========================================
def identificar_pivos(df, lb=3):
    """
    Identifica topos e fundos de pivô (Swing High/Low)
    """
    df['Pivot_High'] = df['High'].rolling(window=lb*2+1, center=True).apply(lambda x: x[lb] if all(x[lb] >= i for i in x) else np.nan)
    df['Pivot_Low'] = df['Low'].rolling(window=lb*2+1, center=True).apply(lambda x: x[lb] if all(x[lb] <= i for i in x) else np.nan)
    
    # Preenche para frente para termos a linha de suporte/resistência atual
    df['Last_Pivot_High'] = df['Pivot_High'].ffill()
    df['Last_Pivot_Low'] = df['Pivot_Low'].ffill()
    return df

def calcular_filtros(df, ma_type='SMA', ma_len=50):
    if ma_type == 'SMA':
        df['MA_Filter'] = ta.sma(df['Close'], length=ma_len)
    else:
        df['MA_Filter'] = ta.ema(df['Close'], length=ma_len)
    return df

# ==========================================
# 3. INTERFACE CAÇADORES DE ELITE
# ==========================================
st.set_page_config(page_title="Rompimento de Pivô Elite", layout="wide", page_icon="🚀")
st.title("🚀 Rompimento de Pivô: Trend Follower")
st.markdown("Este scanner busca ativos que romperam a resistência de um topo recente (Pivô de Alta) com o preço blindado por médias de tendência.")

aba_radar, aba_raiox = st.tabs(["📡 Radar de Rompimento", "🔬 Raio-X & Backtest"])

# ------------------------------------------
# ABA 1: RADAR EM MASSA
# ------------------------------------------
with aba_radar:
    c1, c2, c3 = st.columns(3)
    with c1:
        lista_sel = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos"], key="brk_lista")
        tempo_grafico = st.selectbox("Tempo Gráfico:", ['1d', '60m', '15m'], index=0, key="brk_tempo")
    with c2:
        pivo_lb = st.number_input("Sensibilidade do Pivô (Lookback):", value=3, min_value=1, help="Maior valor = Pivôs mais fortes e lentos.")
        ma_tipo = st.selectbox("Tipo de Média (Filtro):", ["SMA", "EMA"], index=0)
    with c3:
        ma_periodo = st.number_input("Período da Média:", value=50, min_value=1)
        usar_filtro = st.toggle("🛡️ Somente Acima da Média", value=True)

    btn_escanear = st.button("🚀 Iniciar Varredura de Rompimentos", type="primary", use_container_width=True)

    if btn_escanear:
        ativos = bdrs_elite if lista_sel == "BDRs Elite" else ibrx_selecao if lista_sel == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        ativos = sorted(list(set([a.replace('.SA', '') for a in ativos])))
        
        resultados = []
        p_bar = st.progress(0); s_txt = st.empty()

        for idx, ativo in enumerate(ativos):
            s_txt.text(f"🔍 Caçando rompimentos: {ativo}")
            p_bar.progress((idx + 1) / len(ativos))

            try:
                df = puxar_dados_blindados(ativo, tempo_grafico=tempo_grafico, barras=200)
                if df is None or len(df) < 60: continue
                
                df = identificar_pivos(df, lb=pivo_lb)
                df = calcular_filtros(df, ma_type=ma_tipo, ma_len=ma_periodo)
                
                # Lógica de Rompimento
                hoje = df.iloc[-1]
                ontem = df.iloc[-2]
                
                # 1. O preço fechou acima do último Pivô de Alta?
                rompeu = (hoje['Close'] > hoje['Last_Pivot_High']) and (ontem['Close'] <= ontem['Last_Pivot_High'])
                
                # 2. Filtro de Tendência
                tendencia_ok = hoje['Close'] > hoje['MA_Filter'] if usar_filtro else True
                
                if rompeu and tendencia_ok:
                    resultados.append({
                        'Ativo': ativo,
                        'Preço Atual': f"R$ {hoje['Close']:.2f}",
                        'Resistência Rompida': f"R$ {hoje['Last_Pivot_High']:.2f}",
                        'Suporte (Stop)': f"R$ {hoje['Last_Pivot_Low']:.2f}",
                        'Filtro MA': "✅ OK" if hoje['Close'] > hoje['MA_Filter'] else "❌ ABAIXO"
                    })
            except: pass

        s_txt.empty(); p_bar.empty()

        if resultados:
            st.success(f"🎯 Encontrados {len(resultados)} rompimentos confirmados!")
            st.dataframe(pd.DataFrame(resultados), use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum rompimento de pivô detectado no momento.")

# ------------------------------------------
# ABA 2: RAIO-X INDIVIDUAL
# ------------------------------------------
with aba_raiox:
    st.subheader("🔬 Laboratório de Backtest: Breakout")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        rx_ativo = st.selectbox("Selecione o Ativo:", todos_ativos, index=0)
        rx_tempo = st.selectbox("Tempo Gráfico:", ['1d', '60m', '15m'], index=0, key="rx_brk_tempo")
    with col2:
        rx_lb = st.number_input("Lookback do Pivô:", value=3, key="rx_lb")
        rx_alvo = st.number_input("Alvo Fixo (%):", value=5.0, step=0.5)
    with col3:
        rx_cap = st.number_input("Capital por Operação (R$):", value=10000.0)
        rx_ma = st.number_input("Média de Filtro:", value=50, key="rx_ma")

    if st.button("🔍 Rodar Backtest de Rompimento", type="primary", use_container_width=True):
        with st.spinner(f"Analisando histórico de {rx_ativo}..."):
            try:
                df_full = puxar_dados_blindados(rx_ativo, tempo_grafico=rx_tempo, barras=2000)
                if df_full is None or len(df_full) < 100:
                    st.error("Dados insuficientes.")
                else:
                    df = identificar_pivos(df_full, lb=rx_lb)
                    df = calcular_filtros(df, ma_len=int(rx_ma))
                    df_back = df.dropna().reset_index()
                    
                    trades = []
                    em_pos = False
                    
                    for i in range(1, len(df_back)):
                        linha = df_back.iloc[i]
                        ontem = df_back.iloc[i-1]
                        
                        if em_pos:
                            # Saída 1: Stop no Pivô de Baixa (Trailing Stop)
                            if linha['Low'] <= stop_loss:
                                trades.append({'Entrada': d_ent, 'Saída': linha['index'], 'Tipo': 'Stop ❌', 'Resultado': (stop_loss/p_ent - 1)*100})
                                em_pos = False
                            # Saída 2: Alvo Fixo
                            elif linha['High'] >= alvo_p:
                                trades.append({'Entrada': d_ent, 'Saída': linha['index'], 'Tipo': 'Alvo 🎯', 'Resultado': rx_alvo})
                                em_pos = False
                            continue

                        # Entrada: Rompeu pivo e está acima da média
                        if (linha['Close'] > linha['Last_Pivot_High']) and (ontem['Close'] <= ontem['Last_Pivot_High']) and (linha['Close'] > linha['MA_Filter']):
                            em_pos = True
                            p_ent = linha['Close']
                            d_ent = linha['index']
                            stop_loss = linha['Last_Pivot_Low']
                            alvo_p = p_ent * (1 + rx_alvo/100)

                    if trades:
                        df_t = pd.DataFrame(trades)
                        st.divider()
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Total de Trades", len(df_t))
                        m2.metric("Taxa de Acerto", f"{(len(df_t[df_t['Resultado'] > 0]) / len(df_t))*100:.1f}%")
                        m3.metric("Resultado Acumulado", f"{df_t['Resultado'].sum():+.2f}%")
                        st.dataframe(df_t, use_container_width=True, hide_index=True)
                    else:
                        st.warning("Nenhuma operação disparada no período.")
            except Exception as e: st.error(f"Erro: {e}")
