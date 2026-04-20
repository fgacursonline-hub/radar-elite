import streamlit as st
from tvDatafeed import TvDatafeed, Interval
import pandas as pd
import pandas_ta as ta
import time
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. SEGURANÇA E CONEXÃO
# ==========================================
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

bdrs_elite = [
    'NVDC34.SA', 'P2LT34.SA', 'ROXO34.SA', 'INBR32.SA', 'M1TA34.SA', 'TSLA34.SA',
    'LILY34.SA', 'AMZO34.SA', 'AURA33.SA', 'GOGL34.SA', 'MSFT34.SA', 'MUTC34.SA',
    'MELI34.SA', 'C2OI34.SA', 'ORCL34.SA', 'M2ST34.SA', 'A1MD34.SA', 'NFLX34.SA',
    'ITLC34.SA', 'AVGO34.SA', 'COCA34.SA', 'JBSS32.SA', 'AAPL34.SA', 'XPBR31.SA',
    'STOC34.SA'
]

ibrx_selecao = [
    'PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'BBDC4.SA', 'BBAS3.SA', 'B3SA3.SA', 'ABEV3.SA',
    'WEGE3.SA', 'AXIA3.SA', 'SUZB3.SA', 'RENT3.SA', 'RADL3.SA', 'EQTL3.SA', 'LREN3.SA',
    'PRIO3.SA', 'HAPV3.SA', 'GGBR4.SA', 'VBBR3.SA', 'SBSP3.SA', 'CMIG4.SA', 'CPLE3.SA',
    'ENEV3.SA', 'TIMS3.SA', 'TOTS3.SA', 'EGIE3.SA', 'CSAN3.SA', 'ALOS3.SA', 'DIRR3.SA',
    'VIVT3.SA', 'KLBN11.SA', 'UGPA3.SA', 'PSSA3.SA', 'CYRE3.SA', 'ASAI3.SA', 'RAIL3.SA',
    'ISAE3.SA', 'CSNA3.SA', 'MGLU3.SA', 'EMBJ3.SA', 'TAEE11.SA', 'BBSE3.SA', 'FLRY3.SA',
    'MULT3.SA', 'TFCO4.SA', 'LEVE3.SA', 'CPFE3.SA', 'GOAU4.SA', 'MRVE3.SA', 'YDUQ3.SA',
    'SMTO3.SA', 'SLCE3.SA', 'CVCB3.SA', 'USIM5.SA', 'BRAP4.SA', 'BRAV3.SA', 'EZTC3.SA',
    'PCAR3.SA', 'AUAU3.SA', 'DXCO3.SA', 'CASH3.SA', 'VAMO3.SA', 'AZZA3.SA', 'AURE3.SA',
    'BEEF3.SA', 'ECOR3.SA', 'FESA4.SA', 'POMO4.SA', 'CURY3.SA', 'INTB3.SA', 'JHSF3.SA',
    'LIGT3.SA', 'LOGG3.SA', 'MDIA3.SA', 'MBRF3.SA', 'NEOE3.SA', 'QUAL3.SA', 'RAPT4.SA',
    'ROMI3.SA', 'SANB11.SA', 'SIMH3.SA', 'TEND3.SA', 'VULC3.SA', 'PLPL3.SA', 'CEAB3.SA',
    'UNIP6.SA', 'LWSA3.SA', 'BPAC11.SA', 'GMAT3.SA', 'CXSE3.SA', 'ABCB4.SA', 'CSMG3.SA',
    'SAPR11.SA', 'GRND3.SA', 'BRAP3.SA', 'LAVV3.SA', 'RANI3.SA', 'ITSA3.SA', 'ALUP11.SA',
    'FIQE3.SA', 'COGN3.SA', 'IRBR3.SA', 'SEER3.SA', 'ANIM3.SA', 'JSLG3.SA', 'POSI3.SA',
    'MYPK3.SA', 'SOJA3.SA', 'BLAU3.SA', 'PGMN3.SA', 'TUPY3.SA', 'VVEO3.SA', 'MELK3.SA',
    'SHUL4.SA', 'BRSR6.SA',
]

# ==========================================
# 2. INTERFACE E ABAS
# ==========================================
col_titulo, col_botao = st.columns([4, 1])
with col_titulo:
    st.title("💥 Explosão da Volatilidade (Mola)")
with col_botao:
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.link_button("📖 Ler Manual", "https://seusite.com/manual_mola", use_container_width=True)

aba_radar, aba_individual = st.tabs(["📡 Radar (Setups Armados)", "🔬 Raio-X Individual"])

# ==========================================
# ABA 1: RADAR DE COMPRESSÃO (NR4 / NR7)
# ==========================================
with aba_radar:
    st.subheader("📡 Radar de Mola Comprimida")
    st.markdown("Varre o mercado em busca de ativos em congestão que formaram o menor candle dos últimos 4 (NR4) ou 7 (NR7) períodos. Uma mola pronta para disparar.")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        lista_sel = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"], key="lat_lst")
        tipo_setup = st.selectbox("Setup de Volatilidade:", ["NR4 (Mola Clássica)", "NR7 (Mola Estendida)"], key="lat_setup")
    with c2:
        tempo_grafico = st.selectbox("Tempo Gráfico:", ['1d', '1wk', '60m', '15m'], index=0, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="lat_tmp")
        tipo_filtro = st.selectbox("Filtro de Congestão (Caixote):", [
            "Bollinger Squeeze (Bandas Estreitas)", 
            "Médias Emboladas (MME9 próxima a MM21)", 
            "ADX < 25 (Clássico)", 
            "Sem Filtro (Basta ser NR4/NR7)"
        ], key="lat_filtro")
    with c3:
        st.info("💡 **Ação:** Rompendo a máxima, é Compra. Perdendo a mínima, é Venda. O Stop inicial fica no outro extremo da 'Mola'.")
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    btn_iniciar = st.button(f"🚀 Caçar Setups {tipo_setup[:3]} Armados Hoje", type="primary", use_container_width=True)

    if btn_iniciar:
        ativos_analise = bdrs_elite if lista_sel == "BDRs Elite" else ibrx_selecao if lista_sel == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        intervalo_tv = tradutor_intervalo.get(tempo_grafico, Interval.in_daily)
        
        janela_nr = 4 if "NR4" in tipo_setup else 7

        ls_armados = []
        p_bar = st.progress(0)
        s_text = st.empty()

        for idx, ativo_raw in enumerate(ativos_analise):
            ativo = ativo_raw.replace('.SA', '')
            s_text.text(f"🔍 Medindo volatilidade de {ativo} ({idx+1}/{len(ativos_analise)})")
            p_bar.progress((idx + 1) / len(ativos_analise))

            try:
                df = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=150)
                if df is None or len(df) < 30: continue

                df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                
                # --- MATEMÁTICA DA MOLA (NR4/NR7) ---
                df['Range'] = df['High'] - df['Low']
                df[f'Min_Range_{janela_nr}'] = df['Range'].rolling(window=janela_nr).min()
                df['Is_Latinha'] = df['Range'] == df[f'Min_Range_{janela_nr}']
                
                # --- MOTOR DE LEITURA DO CAIXOTE ---
                df['Mercado_Lateral'] = True # Padrão para "Sem Filtro"

                if "ADX" in tipo_filtro:
                    adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
                    if adx_df is not None: df['Mercado_Lateral'] = adx_df['ADX_14'] < 25
                        
                elif "Bollinger" in tipo_filtro:
                    bb = ta.bbands(df['Close'], length=20, std=2)
                    if bb is not None:
                        bb_width = (bb['BBU_20_2.0'] - bb['BBL_20_2.0']) / bb['BBM_20_2.0']
                        bb_width_media = bb_width.rolling(window=20).mean()
                        df['Mercado_Lateral'] = bb_width < bb_width_media
                        
                elif "Médias" in tipo_filtro:
                    mme9 = ta.ema(df['Close'], length=9)
                    mm21 = ta.sma(df['Close'], length=21)
                    if mme9 is not None and mm21 is not None:
                        distancia_pct = abs(mme9 - mm21) / df['Close'] * 100
                        df['Mercado_Lateral'] = distancia_pct < 1.5

                # --- VERIFICA O ÚLTIMO CANDLE FECHADO ---
                ultimo = df.iloc[-1]
                
                if ultimo['Is_Latinha'] and ultimo['Mercado_Lateral']:
                    gatilho_compra = ultimo['High'] + 0.01
                    gatilho_venda = ultimo['Low'] - 0.01
                    
                    ls_armados.append({
                        'Ativo': ativo,
                        'Data Formação': df.index[-1].strftime('%d/%m/%Y'),
                        'Tamanho (R$)': f"R$ {ultimo['Range']:.2f}",
                        'Gatilho COMPRA': f"R$ {gatilho_compra:.2f}",
                        'Gatilho VENDA': f"R$ {gatilho_venda:.2f}",
                        'Fechamento Atual': f"R$ {ultimo['Close']:.2f}"
                    })

            except Exception as e: pass
            time.sleep(0.05)

        s_text.empty()
        p_bar.empty()

        # --- EXIBIÇÃO DOS RESULTADOS ---
        st.divider()
        if len(ls_armados) > 0:
            st.success(f"🎯 Encontramos {len(ls_armados)} 'Molas' validadas pelo filtro de {tipo_filtro.split()[0]}!")
            df_res = pd.DataFrame(ls_armados)
            st.dataframe(df_res, use_container_width=True, hide_index=True)
        else:
            st.warning(f"Nenhuma mola encontrada hoje com as condições do filtro ({tipo_filtro.split()[0]}). O mercado pode estar muito direcional.")

# ==========================================
# ABA 2: RAIO-X INDIVIDUAL (A FAZER)
# ==========================================
with aba_individual:
    st.info("Em breve: Backtest completo para analisar a rentabilidade da mola no passado.")
