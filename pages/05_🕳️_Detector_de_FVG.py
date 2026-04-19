import streamlit as st
import pandas as pd
import pandas_ta as ta
from tvDatafeed import TvDatafeed, Interval
import time

# 1. Configuração da Página
st.set_page_config(page_title="Detector de FVG", layout="wide")

# Inicializa o TradingView
if 'tv' not in st.session_state:
    st.session_state.tv = TvDatafeed()
tv = st.session_state.tv

# --- Cabeçalho ---
col_tit, col_man = st.columns([4, 1])
with col_tit:
    st.title("🕳️ Smart Money: Gaps Institucionais (FVG)")
with col_man:
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.link_button("📖 Manual FVG", "https://seusite.com/manual_fvg", use_container_width=True)

st.divider()

# --- LISTAS DE ATIVOS GLOBAIS ---
bdrs_elite = ['NVDC34', 'P2LT34', 'ROXO34', 'INBR32', 'M1TA34', 'TSLA34', 'LILY34', 'AMZO34', 'AURA33', 'GOGL34', 'MSFT34', 'MUTC34', 'MELI34', 'C2OI34', 'ORCL34', 'M2ST34', 'A1MD34', 'NFLX34', 'ITLC34', 'AVGO34', 'COCA34', 'JBSS32', 'AAPL34', 'XPBR31', 'STOC34']
ibrx_selecao = ['PETR4', 'VALE3', 'ITUB4', 'BBDC4', 'BBAS3', 'B3SA3', 'ABEV3', 'WEGE3', 'AXIA3', 'SUZB3', 'RENT3', 'RADL3', 'EQTL3', 'LREN3', 'PRIO3', 'HAPV3', 'GGBR4', 'VBBR3', 'SBSP3', 'CMIG4', 'CPLE3', 'ENEV3', 'TIMS3', 'TOTS3', 'EGIE3', 'CSAN3', 'ALOS3', 'DIRR3', 'VIVT3', 'KLBN11', 'UGPA3', 'PSSA3', 'CYRE3', 'ASAI3', 'RAIL3', 'ISAE3', 'CSNA3', 'MGLU3', 'EMBJ3', 'TAEE11', 'BBSE3', 'FLRY3', 'MULT3', 'TFCO4', 'LEVE3', 'CPFE3', 'GOAU4', 'MRVE3', 'YDUQ3', 'SMTO3', 'SLCE3', 'CVCB3', 'USIM5', 'BRAP4', 'BRAV3', 'EZTC3', 'PCAR3', 'AUAU3', 'DXCO3', 'CASH3', 'VAMO3', 'AZZA3', 'AURE3', 'BEEF3', 'ECOR3', 'FESA4', 'POMO4', 'CURY3', 'INTB3', 'JHSF3', 'LIGT3', 'LOGG3', 'MDIA3', 'MBRF3', 'NEOE3', 'QUAL3', 'RAPT4', 'ROMI3', 'SANB11', 'SIMH3', 'TEND3', 'VULC3', 'PLPL3', 'CEAB3', 'UNIP6', 'LWSA3', 'BPAC11', 'GMAT3', 'CXSE3', 'ABCB4', 'CSMG3', 'SAPR11', 'GRND3', 'BRAP3', 'LAVV3', 'RANI3', 'ITSA3', 'ALUP11', 'FIQE3', 'COGN3', 'IRBR3', 'SEER3', 'ANIM3', 'JSLG3', 'POSI3', 'MYPK3', 'SOJA3', 'BLAU3', 'PGMN3', 'TUPY3', 'VVEO3', 'MELK3', 'SHUL4', 'BRSR6']

# --- CRIAÇÃO DAS 7 SUB-ABAS ---
aba_individual, aba_radar, aba_backtest, aba_supremo, aba_backtest_supremo, aba_volume, aba_sniper = st.tabs([
    "🔍 Raio-X Individual", "📡 Radar Oportunidades", "📊 Backtest FVG Puro", "🔥 Radar Supremo", "📈 Backtest Supremo", "💎 Volume & VWAP", "🦅 Filtro Sniper"
])

# ==========================================
# ABA 1: RAIO-X INDIVIDUAL
# ==========================================
with aba_individual:
    st.subheader("Análise Detalhada por Ativo")
    c1, c2, c3 = st.columns(3)
    with c1: lupa_ativo = st.text_input("Ativo (Ex: PETR4):", value="PETR4", key="ind_at").upper()
    with c2: lupa_tempo = st.selectbox("Tempo:", ['15m', '60m', '1d', '1wk'], index=2, key="ind_tm")
    with c3: lupa_bars = st.number_input("Velas:", value=300, key="ind_vl")
    if st.button("🔍 Escanear", use_container_width=True):
        try:
            df = tv.get_hist(symbol=lupa_ativo, exchange='BMFBOVESPA', interval={'15m':Interval.in_15_minute,'60m':Interval.in_1_hour,'1d':Interval.in_daily,'1wk':Interval.in_weekly}[lupa_tempo], n_bars=lupa_bars)
            if df is not None:
                df.rename(columns={'high':'High','low':'Low','close':'Close'}, inplace=True)
                pa = df['Close'].iloc[-1]
                gaps = []
                for i in range(2, len(df)):
                    if df['Low'].iloc[i] > df['High'].iloc[i-2]:
                        topo, fundo = df['Low'].iloc[i], df['High'].iloc[i-2]
                        aberto = df['Low'].iloc[i:].min() > fundo
                        gaps.append({'Data': df.index[i].strftime('%d/%m'), 'Tipo': 'Alta 🟢', 'Topo': topo, 'Fundo': fundo, 'Status': "Aberto" if aberto else "Fechado"})
                st.write(f"Preço Atual: R$ {pa:.2f}")
                st.dataframe(pd.DataFrame(gaps).sort_index(ascending=False), use_container_width=True)
        except: st.error("Erro ao carregar ativo.")

# ==========================================
# ABA 2: RADAR OPORTUNIDADES
# ==========================================
with aba_radar:
    st.subheader("Varredura em Massa")
    r1, r2 = st.columns([3, 1])
    with r1: lista_radar = st.selectbox("Lista:", ["BDRs Elite", "IBrX Seleção"], key="rad_lst")
    with r2: tempo_radar = st.selectbox("Tempo:", ['60m', '1d'], index=1, key="rad_tm")
    if st.button("🚀 Iniciar Radar", use_container_width=True):
        ativos = bdrs_elite if "BDRs" in lista_radar else ibrx_selecao
        barra = st.progress(0)
        encontrados = []
        for i, at in enumerate(ativos):
            barra.progress((i+1)/len(ativos), text=f"Lendo {at}...")
            try:
                df = tv.get_hist(symbol=at, exchange='BMFBOVESPA', interval=Interval.in_daily if tempo_radar=='1d' else Interval.in_1_hour, n_bars=100)
                if df is not None:
                    pa = df['close'].iloc[-1]
                    for j in range(2, len(df)):
                        if df['low'].iloc[j] > df['high'].iloc[j-2]:
                            if df['low'].iloc[j:].min() > df['high'].iloc[j-2] and (df['high'].iloc[j-2] <= pa <= df['low'].iloc[j]):
                                encontrados.append({'Ativo': at, 'Sinal': '🟢 COMPRA', 'Cotação': pa, 'Zona': f"{df['high'].iloc[j-2]:.2f}-{df['low'].iloc[j]:.2f}"})
            except: pass
        barra.empty()
        st.dataframe(pd.DataFrame(encontrados), use_container_width=True)

# ==========================================
# ABA 3: BACKTEST FVG PURO
# ==========================================
with aba_backtest:
    st.subheader("📊 Backtest FVG Puro")
    b1, b2, b3, b4 = st.columns(4)
    with b1: bk_at = st.text_input("Ativo:", value="PETR4", key="bk_at").upper()
    with b2: bk_tm = st.selectbox("Tempo:", ['1d', '60m'], key="bk_tm")
    with b3: bk_vl = st.number_input("Velas:", value=1000, key="bk_vl")
    with b4: bk_qt = st.number_input("Qtd:", value=100, key="bk_qt")
    if st.button("⚙️ Rodar Backtest FVG", use_container_width=True):
        df = tv.get_hist(symbol=bk_at, exchange='BMFBOVESPA', interval=Interval.in_daily if bk_tm=='1d' else Interval.in_1_hour, n_bars=bk_vl)
        if df is not None:
            df.rename(columns={'high':'High','low':'Low','close':'Close'}, inplace=True)
            trades = []
            for i in range(2, len(df)-5):
                if df['Low'].iloc[i] > df['High'].iloc[i-2]:
                    ent, sl = df['Low'].iloc[i], df['High'].iloc[i-2]
                    alvo = ent + (2*(ent-sl))
                    for j in range(i+1, len(df)):
                        if df['Low'].iloc[j] <= sl:
                            trades.append({'Resultado':'🔴 LOSS','Fin':(sl-ent)*bk_qt})
                            break
                        elif df['High'].iloc[j] >= alvo:
                            trades.append({'Resultado':'🟢 GAIN','Fin':(alvo-ent)*bk_qt})
                            break
            if trades:
                res = pd.DataFrame(trades)
                st.metric("Resultado Final", f"R$ {res['Fin'].sum():.2f}")
                st.dataframe(res, use_container_width=True)

# ==========================================
# ABA 4: RADAR SUPREMO (9.1 + FVG)
# ==========================================
with aba_supremo:
    st.subheader("🔥 Radar Supremo (9.1 + FVG)")
    if st.button("🚨 Caçar Confluências", use_container_width=True):
        barra = st.progress(0)
        achados = []
        for i, at in enumerate(bdrs_elite + ibrx_selecao):
            barra.progress((i+1)/(len(bdrs_elite)+len(ibrx_selecao)), text=f"Analisando {at}")
            try:
                df = tv.get_hist(symbol=at, exchange='BMFBOVESPA', interval=Interval.in_daily, n_bars=100)
                if df is not None:
                    df.ta.ema(length=9, append=True)
                    if df['EMA_9'].iloc[-3] >= df['EMA_9'].iloc[-2] and df['EMA_9'].iloc[-1] > df['EMA_9'].iloc[-2]:
                        for j in range(2, len(df)-2):
                            if df['low'].iloc[j] > df['high'].iloc[j-2] and df['low'].iloc[j:].min() > df['high'].iloc[j-2]:
                                if min(df['low'].iloc[-1], df['low'].iloc[-2]) <= df['low'].iloc[j]:
                                    achados.append({'Ativo':at, 'Sinal':'9.1 + FVG', 'Entrada':df['high'].iloc[-1], 'Stop':df['high'].iloc[j-2]})
                                    break
            except: pass
        barra.empty()
        st.dataframe(pd.DataFrame(achados), use_container_width=True)

# ==========================================
# ABA 5: BACKTEST SUPREMO
# ==========================================
with aba_backtest_supremo:
    st.subheader("📈 Backtest Supremo")
    if st.button("⚙️ Simular 9.1 + FVG", use_container_width=True):
        df = tv.get_hist(symbol="WEGE3", exchange='BMFBOVESPA', interval=Interval.in_daily, n_bars=1500)
        if df is not None:
            df.ta.ema(length=9, append=True)
            trades = []
            for i in range(15, len(df)-5):
                if df['EMA_9'].iloc[i-2] >= df['EMA_9'].iloc[i-1] and df['EMA_9'].iloc[i] > df['EMA_9'].iloc[i-1]:
                    # Verifica FVG
                    for f in range(2, i):
                        if df['low'].iloc[f] > df['high'].iloc[f-2] and df['low'].iloc[f:i+1].min() > df['high'].iloc[f-2]:
                            if min(df['low'].iloc[i], df['low'].iloc[i-1]) <= df['low'].iloc[f]:
                                ent, sl = df['high'].iloc[i], df['high'].iloc[f-2]
                                alvo = ent + (2*(ent-sl))
                                for j in range(i+1, len(df)):
                                    if df['low'].iloc[j] <= sl: trades.append({'Res':'🔴 LOSS','Fin':(sl-ent)*100}); break
                                    elif df['high'].iloc[j] >= alvo: trades.append({'Res':'🟢 GAIN','Fin':(alvo-ent)*100}); break
            st.dataframe(pd.DataFrame(trades), use_container_width=True)

# ==========================================
# ABA 6: 💎 VOLUME & VWAP
# ==========================================
with aba_volume:
    st.subheader("💎 Volume & VWAP")
    v_at = st.text_input("Ativo Volume:", value="PETR4").upper()
    if st.button("📊 Ver Fluxo", use_container_width=True):
        df = tv.get_hist(symbol=v_at, exchange='BMFBOVESPA', interval=Interval.in_1_hour, n_bars=200)
        if df is not None:
            df['vwap'] = (df['volume'] * (df['high'] + df['low'] + df['close']) / 3).cumsum() / df['volume'].cumsum()
            st.metric("Preço vs VWAP", f"R$ {df['close'].iloc[-1]:.2f}", delta=f"VWAP: {df['vwap'].iloc[-1]:.2f}")

# ==========================================
# ABA 7: 🦅 FILTRO SNIPER (CONFLUÊNCIA TOTAL)
# ==========================================
with aba_sniper:
    st.subheader("🦅 Filtro Sniper")
    if st.button("🦅 Executar Varredura Sniper", type="primary", use_container_width=True):
        barra = st.progress(0)
        snipers = []
        for i, at in enumerate(bdrs_elite + ibrx_selecao):
            barra.progress((i+1)/(len(bdrs_elite)+len(ibrx_selecao)), text=f"Sniper em {at}")
            try:
                df = tv.get_hist(symbol=at, exchange='BMFBOVESPA', interval=Interval.in_daily, n_bars=150)
                if df is not None:
                    df.rename(columns={'high':'High','low':'Low','close':'Close','volume':'Volume'}, inplace=True)
                    df.ta.ema(length=9, append=True)
                    # Condição 9.1 + VWAP + Volume + FVG
                    if (df['EMA_9'].iloc[-2] <= df['EMA_9'].iloc[-3]) and (df['EMA_9'].iloc[-1] > df['EMA_9'].iloc[-2]):
                        vwap = (df['Volume'] * (df['High'] + df['Low'] + df['Close']) / 3).cumsum() / df['Volume'].cumsum()
                        if df['Close'].iloc[-1] > vwap.iloc[-1]:
                            if df['Volume'].iloc[-1] > df['Volume'].rolling(20).mean().iloc[-1]:
                                for j in range(2, len(df)-2):
                                    if df['Low'].iloc[j] > df['High'].iloc[j-2] and df['Low'].iloc[j:].min() > df['High'].iloc[j-2]:
                                        if min(df['Low'].iloc[-1], df['Low'].iloc[-2]) <= df['Low'].iloc[j]:
                                            snipers.append({'Ativo': at, 'Preço': df['Close'].iloc[-1], 'Volume': '✅ ALTO', 'VWAP': '✅ ACIMA'})
                                            break
            except: pass
        barra.empty()
        st.dataframe(pd.DataFrame(snipers), use_container_width=True)
