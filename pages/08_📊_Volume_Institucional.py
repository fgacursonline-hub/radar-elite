import streamlit as st
from tvDatafeed import TvDatafeed, Interval
import pandas as pd
import numpy as np
import pandas_ta as ta
import time
import warnings
from datetime import datetime

warnings.filterwarnings('ignore')

# ==========================================
# 1. SEGURANÇA E CONEXÃO
# ==========================================
if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, inicie sessão na página inicial (Home).")
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

bdrs_elite = ['NVDC34.SA', 'P2LT34.SA', 'ROXO34.SA', 'INBR32.SA', 'M1TA34.SA', 'TSLA34.SA', 'LILY34.SA', 'AMZO34.SA', 'AURA33.SA', 'GOGL34.SA', 'MSFT34.SA', 'MUTC34.SA', 'MELI34.SA', 'C2OI34.SA', 'ORCL34.SA', 'M2ST34.SA', 'A1MD34.SA', 'NFLX34.SA', 'ITLC34.SA', 'AVGO34.SA', 'COCA34.SA', 'JBSS32.SA', 'AAPL34.SA', 'XPBR31.SA', 'STOC34.SA']
ibrx_selecao = ['PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'BBDC4.SA', 'BBAS3.SA', 'B3SA3.SA', 'ABEV3.SA', 'WEGE3.SA', 'AXIA3.SA', 'SUZB3.SA', 'RENT3.SA', 'RADL3.SA', 'EQTL3.SA', 'LREN3.SA', 'PRIO3.SA', 'HAPV3.SA', 'GGBR4.SA', 'VBBR3.SA', 'SBSP3.SA', 'CMIG4.SA', 'CPLE3.SA', 'ENEV3.SA', 'TIMS3.SA', 'TOTS3.SA', 'EGIE3.SA', 'CSAN3.SA', 'ALOS3.SA', 'DIRR3.SA', 'VIVT3.SA', 'KLBN11.SA', 'UGPA3.SA', 'PSSA3.SA', 'CYRE3.SA', 'ASAI3.SA', 'RAIL3.SA', 'ISAE3.SA', 'CSNA3.SA', 'MGLU3.SA', 'EMBJ3.SA', 'TAEE11.SA', 'BBSE3.SA', 'FLRY3.SA', 'MULT3.SA', 'TFCO4.SA', 'LEVE3.SA', 'CPFE3.SA', 'GOAU4.SA', 'MRVE3.SA', 'YDUQ3.SA', 'SMTO3.SA', 'SLCE3.SA', 'CVCB3.SA', 'USIM5.SA', 'BRAP4.SA', 'BRAV3.SA', 'EZTC3.SA', 'PCAR3.SA', 'AUAU3.SA', 'DXCO3.SA', 'CASH3.SA', 'VAMO3.SA', 'AZZA3.SA', 'AURE3.SA', 'BEEF3.SA', 'ECOR3.SA', 'FESA4.SA', 'POMO4.SA', 'CURY3.SA', 'INTB3.SA', 'JHSF3.SA', 'LIGT3.SA', 'LOGG3.SA', 'MDIA3.SA', 'MBRF3.SA', 'NEOE3.SA', 'QUAL3.SA', 'RAPT4.SA', 'ROMI3.SA', 'SANB11.SA', 'SIMH3.SA', 'TEND3.SA', 'VULC3.SA', 'PLPL3.SA', 'CEAB3.SA', 'UNIP6.SA', 'LWSA3.SA', 'BPAC11.SA', 'GMAT3.SA', 'CXSE3.SA', 'ABCB4.SA', 'CSMG3.SA', 'SAPR11.SA', 'GRND3.SA', 'BRAP3.SA', 'LAVV3.SA', 'RANI3.SA', 'ITSA3.SA', 'ALUP11.SA', 'FIQE3.SA', 'COGN3.SA', 'IRBR3.SA', 'SEER3.SA', 'ANIM3.SA', 'JSLG3.SA', 'POSI3.SA', 'MYPK3.SA', 'SOJA3.SA', 'BLAU3.SA', 'PGMN3.SA', 'TUPY3.SA', 'VVEO3.SA', 'MELK3.SA', 'SHUL4.SA', 'BRSR6.SA']

# ==========================================
# 2. MOTORES MATEMÁTICOS
# ==========================================
def calcular_rolling_poc(df, periodo_lookback=30, num_bins=24):
    poc_list = [np.nan] * len(df)
    for i in range(periodo_lookback, len(df)):
        janela = df.iloc[i-periodo_lookback:i]
        min_p, max_p = janela['Low'].min(), janela['High'].max()
        if max_p == min_p: poc_list[i] = df['Close'].iloc[i]; continue
        bin_edges = np.linspace(min_p, max_p, num_bins)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        vol_profile = np.zeros(num_bins - 1)
        for j in range(len(janela)):
            idx = np.digitize(janela['Close'].iloc[j], bin_edges) - 1
            idx = min(max(idx, 0), num_bins - 2)
            vol_profile[idx] += janela['Volume'].iloc[j]
        poc_list[i] = bin_centers[np.argmax(vol_profile)]
    return pd.Series(poc_list, index=df.index)

def aplicar_fluxo_e_divergencia(df):
    range_c = df['High'] - df['Low']
    df['Saldo_Ag'] = np.where(range_c > 0, df['Volume'] * ((2 * df['Close'] - df['Low'] - df['High']) / range_c), 0)
    df['Delta_Acumulado'] = df['Saldo_Ag'].rolling(window=5).sum()
    df['Divergência'] = "-"
    df.loc[(df['Close'] < df['Close'].shift(1)) & (df['Delta_Acumulado'] > df['Delta_Acumulado'].shift(1)), 'Divergência'] = "⚠️ ALTA (Absorção)"
    df.loc[(df['Close'] > df['Close'].shift(1)) & (df['Delta_Acumulado'] < df['Delta_Acumulado'].shift(1)), 'Divergência'] = "⚠️ BAIXA (Exaustão)"
    return df

# ==========================================
# 3. INTERFACE PRINCIPAL
# ==========================================
st.title("📊 Fluxo Institucional (POC + VWAP + DELTA)")

aba_radar, aba_individual = st.tabs(["📡 Radar Institucional (Delta)", "🔬 Raio-X Individual"])

# ABA 1: RADAR (SCANNER REATIVADO)
with aba_radar:
    c1, c2, c3 = st.columns(3)
    with c1:
        lista_sel = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos"], key="f_lst")
        tempo_grafico = st.selectbox("Tempo Gráfico:", ['1d', '60m'], index=0, key="f_tmp")
    with c2:
        alvo_pct_rad = st.number_input("Alvo Lucro (%):", value=5.0, step=0.5, key="rad_alvo") / 100
        stop_pct_rad = st.number_input("Stop Loss (%):", value=2.5, step=0.5, key="rad_stop") / 100
    with c3:
        st.info("💡 Scanner de fluxo. Use o Raio-X para ver o Plano de Voo detalhado.")
    
    if st.button("🚀 Iniciar Varredura de Fluxo", type="primary", use_container_width=True):
        ativos = bdrs_elite if lista_sel == "BDRs Elite" else ibrx_selecao if lista_sel == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        ls_armados = []
        p_bar = st.progress(0); s_text = st.empty()

        for idx, ativo_raw in enumerate(ativos):
            ativo = ativo_raw.replace('.SA', '')
            s_text.text(f"🔍 Analisando DNA: {ativo} ({idx+1}/{len(ativos)})")
            p_bar.progress((idx + 1) / len(ativos))
            try:
                df = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=tradutor_intervalo[tempo_grafico], n_bars=150)
                if df is None or len(df) < 50: continue
                df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
                df['POC'] = calcular_rolling_poc(df, periodo_lookback=30)
                df['VWAP'] = ta.vwma(df['Close'], df['Volume'], length=20)
                df = aplicar_fluxo_e_divergencia(df)
                
                res_rad = df.iloc[-1]
                # Lógica de Defesa: Acima da POC + Defesa na VWAP + Delta Positivo
                if res_rad['Close'] > df['POC'].iloc[-2] and res_rad['Low'] <= res_rad['VWAP'] and res_rad['Close'] >= res_rad['VWAP'] and res_rad['Delta_Acumulado'] > 0:
                    ls_armados.append({
                        'Ativo': ativo, 'Sinal': '🔥 DEFESA', 'Preço': f"R$ {res_rad['Close']:.2f}", 'Divergência': res_rad['Divergência']
                    })
            except: pass
        
        s_text.empty(); p_bar.empty()
        if ls_armados:
            st.success(f"🎯 {len(ls_armados)} ativos encontrados com defesa institucional!")
            st.dataframe(pd.DataFrame(ls_armados), use_container_width=True, hide_index=True)
        else: st.warning("Nenhum sinal detectado nas últimas barras.")

    st.markdown("---")
    st.markdown("### 📖 Glossário do Radar: Interpretando os Sinais")
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        st.markdown("""
        **📌 Coluna: Sinal**
        * **🔥 DEFESA:** Alinhamento total. Preço acima da POC, tocou a VWAP e fechou acima dela com Delta Positivo.
        * **Interpretação:** Institucionais defendendo posição na média.
        """)
    with col_l2:
        st.markdown("""
        **📌 Coluna: Divergência**
        * **Traço (-):** Fluxo saudável. Preço e Delta na mesma direção.
        * **⚠️ ALTA (Absorção):** Preço caiu mas o Delta subiu. Alguém "limpou o book" na compra.
        * **⚠️ BAIXA (Exaustão):** Preço subiu mas o Delta caiu. Movimento sem combustível.
        """)

# ABA 2: RAIO-X INDIVIDUAL
with aba_individual:
    st.subheader("🔬 Laboratório de Microestrutura")
    col1, col2 = st.columns([1, 2])
    with col1:
        rx_ativo = st.text_input("Ativo (Ex: PETR4):", value="PETR4").upper().replace('.SA', '')
        rx_tempo = st.selectbox("Tempo:", ['1d', '60m'], key="rx_inst_t")
        rx_btn = st.button("🔬 Analisar DNA e Divergências", use_container_width=True)
    
    if rx_btn:
        with st.spinner("Descriptografando agressão institucional..."):
            df = tv.get_hist(symbol=rx_ativo, exchange='BMFBOVESPA', interval=tradutor_intervalo[rx_tempo], n_bars=100)
            if df is not None:
                df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
                df['POC'] = calcular_rolling_poc(df, periodo_lookback=30)
                df['VWAP'] = ta.vwma(df['Close'], df['Volume'], length=20)
                df = aplicar_fluxo_e_divergencia(df)
                
                res = df.iloc[-1]
                
                # 1. MÉTRICAS TOPO
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Preço Atual", f"R$ {res['Close']:.2f}")
                c2.metric("POC (30d)", f"R$ {res['POC']:.2f}", f"{(res['Close']/res['POC']-1)*100:.2f}%")
                c3.metric("VWAP (VWMA20)", f"R$ {res['VWAP']:.2f}")
                c4.metric("Saldo Agres. (5p)", f"{res['Delta_Acumulado']:,.0f}", delta="COMPRADOR" if res['Delta_Acumulado'] > 0 else "VENDEDOR")

                st.divider()
                st.markdown("### 📋 Histórico Recente de Agressão")
                df_view = df[['Close', 'POC', 'VWAP', 'Saldo_Ag', 'Delta_Acumulado', 'Divergência']].tail(10).copy()
                st.dataframe(df_view, use_container_width=True)

                # 2. VEREDITO DO CONSULTOR QUANT (RESTAURADO)
                st.markdown("---")
                st.subheader("🎯 Veredito do Consultor Quant")
                
                p_poc = res['Close'] > res['POC']
                p_vwap = res['Close'] > res['VWAP']
                p_delta = res['Delta_Acumulado'] > 0
                diver = res['Divergência']

                if "ALTA" in diver:
                    st.info("🔥 **ABSORÇÃO DE ALTA DETECTADA:** O preço caiu hoje, mas a agressão compradora aumentou!")
                elif "BAIXA" in diver:
                    st.warning("⚠️ **EXAUSTÃO DE COMPRA DETECTADA:** O preço subiu, mas o Delta caiu.")
                else:
                    st.success("✅ **Fluxo em Convergência:** O preço e o Delta estão na mesma direção. Tendência saudável.")

                st.markdown(f"""
                * {'✅' if p_poc else '❌'} **Filtro POC:** Preço {'acima' if p_poc else 'abaixo'} do valor de maior volume (R$ {res['POC']:.2f}).
                * {'✅' if p_vwap else '❌'} **Filtro VWAP:** O preço {'domina' if p_vwap else 'perdeu'} a média de execução institucional (R$ {res['VWAP']:.2f}).
                * {'✅' if p_delta else '❌'} **Filtro Delta:** O saldo acumulado é de **{res['Delta_Acumulado']:,.0f}** ({'POSITIVO' if p_delta else 'NEGATIVO'}).
                """)

                if p_poc and p_delta and p_vwap:
                    veredito = "COMPRA FORTE"
                    st.success(f"⚖️ **VEREDITO FINAL: {veredito}.** Todos os indicadores alinhados. Alta convicção.")
                elif "ALTA" in diver and p_poc:
                    veredito = "COMPRA TÁTICA"
                    st.success(f"⚖️ **VEREDITO FINAL: {veredito}.**")
                elif not p_poc and not p_delta:
                    veredito = "VENDA FORTE"
                    st.error(f"⚖️ **VEREDITO FINAL: {veredito}.**")
                else:
                    veredito = "AGUARDAR"
                    st.warning(f"⚖️ **VEREDITO FINAL: {veredito}.**")

                # 3. PLANO DE VOO OPERACIONAL
                st.markdown("<br>", unsafe_allow_html=True)
                with st.expander("✈️ Plano de Voo Operacional", expanded=True):
                    if veredito == "COMPRA FORTE":
                        st.markdown(f"**Estratégia: Momentum Institucional**")
                        st.write(f"* **Gatilho Agressivo:** Compra a mercado agora (R$ {res['Close']:.2f}).")
                        st.write(f"* **Gatilho Conservador:** Ordem na VWAP (R$ {res['VWAP']:.2f}).")
                        st.write(f"* **Stop Loss:** R$ {min(res['POC'], res['Close']*0.97):.2f}.")
                        st.write(f"* **Alvo 1 (2:1):** R$ {res['Close'] + (res['Close'] - min(res['POC'], res['Close']*0.97))*2:.2f}.")
                    elif veredito == "COMPRA TÁTICA":
                        st.markdown(f"**Estratégia: Absorção**")
                        st.write(f"* **Gatilho Confirmação:** Compra acima da máxima (R$ {df['High'].iloc[-1] + 0.01:.2f}).")
                        st.write(f"* **Stop Loss:** R$ {df['Low'].iloc[-1] - 0.01:.2f} (Mínima de hoje).")
                    elif veredito == "VENDA FORTE":
                        st.markdown(f"**Estratégia: Proteção**")
                        st.write(f"* **Ação:** Sair do ativo ou não entrar. Gatilho de venda em R$ {df['Low'].iloc[-1] - 0.01:.2f}.")
                    else:
                        st.write("Aguardar alinhamento dos filtros na VWAP.")

                # 4. GLOSSÁRIO DE CAMPO
                st.markdown("---")
                st.markdown("### 📖 Glossário de Campo: Legenda do Fluxo Institucional")
                st.markdown("""
                * **datetime:** Quando o candle foi fechado. Sequência indica convicção.
                * **Close:** Último preço negociado.
                * **POC (Point of Control):** Preço com maior volume (Suporte/Ímã).
                * **VWAP (VWMA20):** Preço médio institucional (Linha de Defesa).
                * **Saldo_Ag (Delta):** Agressividade imediata do tubarão.
                * **Delta_Acumulado:** Acumulação ou Distribuição institucional (5 períodos).
                * **Divergência:** Absorção (Alta) ou Exaustão (Baixa).
                """)
