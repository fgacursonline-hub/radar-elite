import streamlit as st
import pandas as pd
from tvDatafeed import TvDatafeed, Interval
import time

# 1. Configuração da Página com o novo ícone
st.set_page_config(page_title="Rompimento Mensal", layout="wide", page_icon="⚡")

# Inicializa o TradingView
if 'tv' not in st.session_state:
    st.session_state.tv = TvDatafeed()
tv = st.session_state.tv

# --- Cabeçalho ---
st.title("⚡ Estratégia: Rompimento de Máxima Mensal")
st.markdown("Identifica a força institucional: Ativos que superaram o topo do mês anterior.")
st.divider()

# Listas de Ativos
bdrs_elite = ['NVDC34', 'P2LT34', 'ROXO34', 'INBR32', 'M1TA34', 'TSLA34', 'LILY34', 'AMZO34', 'AURA33', 'GOGL34', 'MSFT34', 'MUTC34', 'MELI34', 'C2OI34', 'ORCL34', 'M2ST34', 'A1MD34', 'NFLX34', 'ITLC34', 'AVGO34', 'COCA34', 'JBSS32', 'AAPL34', 'XPBR31', 'STOC34']
ibrx_selecao = ['PETR4', 'VALE3', 'ITUB4', 'BBDC4', 'BBAS3', 'B3SA3', 'ABEV3', 'WEGE3', 'AXIA3', 'SUZB3', 'RENT3', 'RADL3', 'EQTL3', 'LREN3', 'PRIO3', 'HAPV3', 'GGBR4', 'VBBR3', 'SBSP3', 'CMIG4', 'CPLE3', 'ENEV3', 'TIMS3', 'TOTS3', 'EGIE3', 'CSAN3', 'ALOS3', 'DIRR3', 'VIVT3', 'KLBN11', 'UGPA3', 'PSSA3', 'CYRE3', 'ASAI3', 'RAIL3', 'ISAE3', 'CSNA3', 'MGLU3', 'EMBJ3', 'TAEE11', 'BBSE3', 'FLRY3', 'MULT3', 'TFCO4', 'LEVE3', 'CPFE3', 'GOAU4', 'MRVE3', 'YDUQ3', 'SMTO3', 'SLCE3', 'CVCB3', 'USIM5', 'BRAP4', 'BRAV3', 'EZTC3', 'PCAR3', 'AUAU3', 'DXCO3', 'CASH3', 'VAMO3', 'AZZA3', 'AURE3', 'BEEF3', 'ECOR3', 'FESA4', 'POMO4', 'CURY3', 'INTB3', 'JHSF3', 'LIGT3', 'LOGG3', 'MDIA3', 'MBRF3', 'NEOE3', 'QUAL3', 'RAPT4', 'ROMI3', 'SANB11', 'SIMH3', 'TEND3', 'VULC3', 'PLPL3', 'CEAB3', 'UNIP6', 'LWSA3', 'BPAC11', 'GMAT3', 'CXSE3', 'ABCB4', 'CSMG3', 'SAPR11', 'GRND3', 'BRAP3', 'LAVV3', 'RANI3', 'ITSA3', 'ALUP11', 'FIQE3', 'COGN3', 'IRBR3', 'SEER3', 'ANIM3', 'JSLG3', 'POSI3', 'MYPK3', 'SOJA3', 'BLAU3', 'PGMN3', 'TUPY3', 'VVEO3', 'MELK3', 'SHUL4', 'BRSR6']

# --- Sub-Abas Internas ---
aba_rad_p, aba_rad_pm, aba_alvo_st, aba_raio_x = st.tabs([
    "📡 Radar (Padrão)", "📡 Radar (PM)", "🛡️ Alvo & Stop", "🔬 Raio-X Individual"
])

# ==========================================
# 1. RADAR (PADRÃO)
# ==========================================
with aba_rad_p:
    st.subheader("📡 Scan de Rompimento Mensal")
    if st.button("🚀 Iniciar Varredura de Mercado", type="primary", use_container_width=True):
        barra = st.progress(0)
        ativos = bdrs_elite + ibrx_selecao
        encontrados = []
        for i, at in enumerate(ativos):
            barra.progress((i+1)/len(ativos), text=f"Lendo {at}...")
            try:
                df = tv.get_hist(symbol=at, exchange='BMFBOVESPA', interval=Interval.in_monthly, n_bars=3)
                if df is not None and len(df) >= 2:
                    df.columns = [c.capitalize() for c in df.columns]
                    max_anterior = df['High'].iloc[-2]
                    preco_atual = df['Close'].iloc[-1]
                    if preco_atual > max_anterior:
                        encontrados.append({
                            'Ativo': at, 'Cotação': f"R$ {preco_atual:.2f}", 
                            'Máxima Anterior': f"R$ {max_anterior:.2f}",
                            'Rompimento': f"{((preco_atual/max_anterior)-1)*100:.2f}%"
                        })
            except: pass
        barra.empty()
        if encontrados: st.dataframe(pd.DataFrame(encontrados), use_container_width=True, hide_index=True)
        else: st.warning("Nenhum rompimento detectado hoje.")

# ==========================================
# 2. RADAR (PM)
# ==========================================
with aba_rad_pm:
    st.subheader("📡 Oportunidades de Preço Médio (Pullback)")
    if st.button("🔍 Buscar Retrações", use_container_width=True):
        barra = st.progress(0)
        ativos = bdrs_elite + ibrx_selecao
        pms = []
        for i, at in enumerate(ativos):
            barra.progress((i+1)/len(ativos))
            try:
                df = tv.get_hist(symbol=at, exchange='BMFBOVESPA', interval=Interval.in_monthly, n_bars=3)
                if df is not None and len(df) >= 2:
                    df.columns = [c.capitalize() for c in df.columns]
                    max_ant = df['High'].iloc[-2]
                    atual = df['Close'].iloc[-1]
                    # Busca ativos próximos à zona rompida para PM (Margem de 2%)
                    if atual >= max_ant * 0.98 and atual <= max_ant * 1.02:
                        pms.append({'Ativo': at, 'Preço Atual': f"R$ {atual:.2f}", 'Suporte Mensal': f"R$ {max_ant:.2f}"})
            except: pass
        barra.empty()
        st.dataframe(pd.DataFrame(pms), use_container_width=True)

# ==========================================
# 3. 🛡️ ALVO & STOP
# ==========================================
with aba_alvo_st:
    st.subheader("🛡️ Calculadora de Objetivo")
    st.info("Estratégia Position: Sem Stop Loss fixo. Alvos longos.")
    c1, c2 = st.columns(2)
    with c1: 
        p_in = st.number_input("Preço de Entrada:", value=25.0)
        perc = st.slider("Alvo de Saída (%)", 5, 100, 20)
    with c2:
        qtd = st.number_input("Quantidade:", value=100)
    
    alvo_fin = p_in * (1 + (perc/100))
    st.metric("🎯 Alvo Final", f"R$ {alvo_fin:.2f}", delta=f"{perc}%")

# ==========================================
# 4. 🔬 RAIO-X INDIVIDUAL
# ==========================================
with aba_raio_x:
    st.subheader("🔬 Análise por Ativo")
    lupa = st.text_input("Ativo:", value="VALE3").upper()
    if st.button("Analisar Gráfico Mensal", use_container_width=True):
        try:
            df = tv.get_hist(symbol=lupa, exchange='BMFBOVESPA', interval=Interval.in_monthly, n_bars=12)
            if df is not None:
                df.columns = [c.capitalize() for c in df.columns]
                max_ant = df['High'].iloc[-2]
                st.write(f"Máxima do mês anterior: **R$ {max_ant:.2f}**")
                st.line_chart(df['Close'])
        except: st.error("Erro ao carregar dados.")
