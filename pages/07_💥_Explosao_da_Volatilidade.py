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
    st.title("💥 Explosão da Volatilidade")
with col_botao:
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.link_button("📖 Ler Manual", "https://seusite.com/manual_volatilidade", use_container_width=True)

aba_radar, aba_individual = st.tabs(["📡 Scanner de Volatilidade", "🔬 Raio-X Individual"])

# ==========================================
# ABA 1: SCANNER DE COMPRESSÃO DE VOLATILIDADE
# ==========================================
with aba_radar:
    st.subheader("🔍 Scanner de Compressão de Volatilidade")
    st.markdown("Varre o mercado em busca de Molas Comprimidas (NR4/NR7) e Contra-Golpes Táticos. O objetivo é antecipar a ruptura de zonas de acumulação e engolfos direcionais.")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        lista_sel = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"], key="vol_lst")
        tipo_setup = st.selectbox("Estratégia de Elite:", [
            "Mola Comprimida (NR4)", 
            "Mola Mestra (NR7)", 
            "Contra-Golpe Tático"
        ], key="vol_setup")
    with c2:
        tempo_grafico = st.selectbox("Tempo Gráfico:", ['1d', '1wk', '60m', '15m'], index=0, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="vol_tmp")
        tipo_filtro = st.selectbox("Filtro de Compressão (Caixote):", [
            "Bollinger Squeeze (Bandas Estreitas)", 
            "Médias Emboladas (MME9 próxima à MM21)", 
            "Sem Filtro (Sinal Puro)"
        ], key="vol_filtro", disabled=("Contra-Golpe" in tipo_setup)) 
    with c3:
        st.info("💡 **Dica Tática:** O Contra-Golpe exige MM21 inclinada a favor do movimento. A Mola Comprimida prospera na letargia e baixa volatilidade.")
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    nome_botao = tipo_setup.split('(')[0].strip()
    btn_iniciar = st.button(f"🚀 Iniciar Scanner: {nome_botao}", type="primary", use_container_width=True)

    if btn_iniciar:
        ativos_analise = bdrs_elite if lista_sel == "BDRs Elite" else ibrx_selecao if lista_sel == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        intervalo_tv = tradutor_intervalo.get(tempo_grafico, Interval.in_daily)
        
        ls_sinais = []
        p_bar = st.progress(0)
        s_text = st.empty()

        for idx, ativo_raw in enumerate(ativos_analise):
            ativo = ativo_raw.replace('.SA', '')
            s_text.text(f"🔍 Escaneando o campo de batalha: {ativo} ({idx+1}/{len(ativos_analise)})")
            p_bar.progress((idx + 1) / len(ativos_analise))

            try:
                df = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=150)
                if df is None or len(df) < 30: continue

                df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                
                # --- INDICADORES BASE ---
                df['Range'] = df['High'] - df['Low']
                df['MM21'] = ta.sma(df['Close'], length=21)
                df['MME9'] = ta.ema(df['Close'], length=9)
                
                # Mapeamento de Cores dos Candles
                df['Cor'] = 'Verde'
                df.loc[df['Close'] < df['Open'], 'Cor'] = 'Vermelho'
                
                # --- LÓGICA 1: MOLA COMPRIMIDA (NR4) & MOLA MESTRA (NR7) ---
                if "Mola" in tipo_setup:
                    janela = 4 if "NR4" in tipo_setup else 7
                    df[f'Min_Range'] = df['Range'].rolling(window=janela).min()
                    
                    # Filtro Institucional de Caixote
                    mercado_lateral = True
                    if "Bollinger" in tipo_filtro:
                        bb = ta.bbands(df['Close'], length=20, std=2)
                        bb_width = (bb['BBU_20_2.0'] - bb['BBL_20_2.0']) / bb['BBM_20_2.0']
                        mercado_lateral = bb_width.iloc[-1] < bb_width.rolling(20).mean().iloc[-1]
                    elif "Médias" in tipo_filtro:
                        dist = abs(df['MME9'] - df['MM21']) / df['Close'] * 100
                        mercado_lateral = dist.iloc[-1] < 1.5

                    if df['Range'].iloc[-1] == df['Min_Range'].iloc[-1] and mercado_lateral:
                        ls_sinais.append({
                            'Ativo': ativo, 'Sinal': f"💥 {'Mola Comprimida' if janela == 4 else 'Mola Mestra'}", 
                            'Direção': 'Compra/Venda', 'Gatilho Compra': f"R$ {df['High'].iloc[-1]+0.01:.2f}",
                            'Gatilho Venda': f"R$ {df['Low'].iloc[-1]-0.01:.2f}", 'Obs': f"Pressão máxima em {janela} períodos"
                        })

                # --- LÓGICA 2: CONTRA-GOLPE TÁTICO ---
                elif "Contra-Golpe" in tipo_setup:
                    # Direcional da Tendência
                    tendencia_alta = df['MM21'].iloc[-1] > df['MM21'].iloc[-2]
                    tendencia_baixa = df['MM21'].iloc[-1] < df['MM21'].iloc[-2]
                    
                    # Análise do Conjunto (i-2, i-1, i)
                    c0, c1, c2 = df['Cor'].iloc[-3], df['Cor'].iloc[-2], df['Cor'].iloc[-1]
                    
                    # Sinal Tático de Compra: Tendência Alta + Recuo (Vermelho - Verde - Vermelho)
                    if tendencia_alta and c0 == 'Vermelho' and c1 == 'Verde' and c2 == 'Vermelho':
                        max_conjunto = df['High'].iloc[-3:].max()
                        ls_sinais.append({
                            'Ativo': ativo, 'Sinal': '🛡️ Contra-Golpe Tático', 
                            'Direção': 'COMPRA 🟢', 'Gatilho Compra': f"R$ {max_conjunto+0.01:.2f}",
                            'Gatilho Venda': '-', 'Obs': 'Armadilha para Vendidos Armada'
                        })
                    
                    # Sinal Tático de Venda: Tendência Baixa + Respiro (Verde - Vermelho - Verde)
                    elif tendencia_baixa and c0 == 'Verde' and c1 == 'Vermelho' and c2 == 'Verde':
                        min_conjunto = df['Low'].iloc[-3:].min()
                        ls_sinais.append({
                            'Ativo': ativo, 'Sinal': '📉 Contra-Golpe Tático', 
                            'Direção': 'VENDA 🔴', 'Gatilho Compra': '-',
                            'Gatilho Venda': f"R$ {min_conjunto-0.01:.2f}", 'Obs': 'Armadilha para Compradores Armada'
                        })

            except Exception as e: pass
            time.sleep(0.01)

        s_text.empty()
        p_bar.empty()

        # --- EXIBIÇÃO DE RESULTADOS TÁTICOS ---
        st.divider()
        if ls_sinais:
            st.success(f"🎯 Varredura concluída! {len(ls_sinais)} oportunidades táticas detectadas.")
            st.dataframe(pd.DataFrame(ls_sinais), use_container_width=True, hide_index=True)
        else:
            st.warning("O campo de batalha está neutro hoje. Nenhum padrão de explosão ou contra-golpe validado.")

with aba_individual:
    st.info("Aba de Raio-X Individual em desenvolvimento. Próximo passo: Backtest de Alvos Matemáticos.")
