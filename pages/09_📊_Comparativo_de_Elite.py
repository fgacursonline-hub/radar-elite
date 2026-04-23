import streamlit as st
from tvDatafeed import TvDatafeed, Interval
import pandas as pd
import numpy as np
import warnings

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

# Listas de Cadastro
bdrs_elite = ['NVDC34.SA', 'P2LT34.SA', 'ROXO34.SA', 'INBR32.SA', 'M1TA34.SA', 'TSLA34.SA', 'LILY34.SA', 'AMZO34.SA', 'AURA33.SA', 'GOGL34.SA', 'MSFT34.SA', 'MUTC34.SA', 'MELI34.SA', 'C2OI34.SA', 'ORCL34.SA', 'M2ST34.SA', 'A1MD34.SA', 'NFLX34.SA', 'ITLC34.SA', 'AVGO34.SA', 'COCA34.SA', 'JBSS32.SA', 'AAPL34.SA', 'XPBR31.SA', 'STOC34.SA']
ibrx_selecao = ['PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'BBDC4.SA', 'BBAS3.SA', 'B3SA3.SA', 'ABEV3.SA', 'WEGE3.SA', 'AXIA3.SA', 'SUZB3.SA', 'RENT3.SA', 'RADL3.SA', 'EQTL3.SA', 'LREN3.SA', 'PRIO3.SA', 'HAPV3.SA', 'GGBR4.SA', 'VBBR3.SA', 'SBSP3.SA', 'CMIG4.SA', 'CPLE3.SA', 'ENEV3.SA', 'TIMS3.SA', 'TOTS3.SA', 'EGIE3.SA', 'CSAN3.SA', 'ALOS3.SA', 'DIRR3.SA', 'VIVT3.SA', 'KLBN11.SA', 'UGPA3.SA', 'PSSA3.SA', 'CYRE3.SA', 'ASAI3.SA', 'RAIL3.SA', 'ISAE3.SA', 'CSNA3.SA', 'MGLU3.SA', 'EMBJ3.SA', 'TAEE11.SA', 'BBSE3.SA', 'FLRY3.SA', 'MULT3.SA', 'TFCO4.SA', 'LEVE3.SA', 'CPFE3.SA', 'GOAU4.SA', 'MRVE3.SA', 'YDUQ3.SA', 'SMTO3.SA', 'SLCE3.SA', 'CVCB3.SA', 'USIM5.SA', 'BRAP4.SA', 'BRAV3.SA', 'EZTC3.SA', 'PCAR3.SA', 'AUAU3.SA', 'DXCO3.SA', 'CASH3.SA', 'VAMO3.SA', 'AZZA3.SA', 'AURE3.SA', 'BEEF3.SA', 'ECOR3.SA', 'FESA4.SA', 'POMO4.SA', 'CURY3.SA', 'INTB3.SA', 'JHSF3.SA', 'LIGT3.SA', 'LOGG3.SA', 'MDIA3.SA', 'MBRF3.SA', 'NEOE3.SA', 'QUAL3.SA', 'RAPT4.SA', 'ROMI3.SA', 'SANB11.SA', 'SIMH3.SA', 'TEND3.SA', 'VULC3.SA', 'PLPL3.SA', 'CEAB3.SA', 'UNIP6.SA', 'LWSA3.SA', 'BPAC11.SA', 'GMAT3.SA', 'CXSE3.SA', 'ABCB4.SA', 'CSMG3.SA', 'SAPR11.SA', 'GRND3.SA', 'BRAP3.SA', 'LAVV3.SA', 'RANI3.SA', 'ITSA3.SA', 'ALUP11.SA', 'FIQE3.SA', 'COGN3.SA', 'IRBR3.SA', 'SEER3.SA', 'ANIM3.SA', 'JSLG3.SA', 'POSI3.SA', 'MYPK3.SA', 'SOJA3.SA', 'BLAU3.SA', 'PGMN3.SA', 'TUPY3.SA', 'VVEO3.SA', 'MELK3.SA', 'SHUL4.SA', 'BRSR6.SA']

lista_unificada = sorted(list(set([a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)])))

# ==========================================
# 2. INTERFACE CENTRALIZADA
# ==========================================
st.set_page_config(page_title="Comparador de Elite", layout="wide")

st.title("📊 Comparador de Performance Institucional")
st.markdown("Identifique qual ativo está atraindo mais capital e força relativa no período.")

st.divider()
st.subheader("⚙️ Configurações do Duelo")

c1, c2, c3 = st.columns([2, 1, 1])

with c1:
    ativos_comp = st.multiselect("Selecione até 4 ativos:", options=lista_unificada, default=["PETR4", "VALE3"], max_selections=4)
with c2:
    tempo_comp = st.selectbox("Tempo Gráfico:", ['1d', '60m'], index=0)
with c3:
    periodo_comp = st.slider("Janela de Observação (Barras):", 20, 300, 100)
    
    # --- EXPLICAÇÃO DINÂMICA DO TEMPO ---
    if tempo_comp == '1d':
        st.caption(f"🕒 **Referência:** {periodo_comp} barras ≈ {int(periodo_comp/20)} meses de mercado.")
    else:
        st.caption(f"🕒 **Referência:** {periodo_comp} barras ≈ {int(periodo_comp/7)} dias de pregão.")

btn_comp = st.button("🚀 Gerar Comparativo de Performance", type="primary", use_container_width=True)

# ==========================================
# 3. PROCESSAMENTO
# ==========================================
if btn_comp:
    if not ativos_comp:
        st.warning("⚠️ Selecione os ativos para o duelo.")
    else:
        with st.spinner("Sincronizando dados..."):
            df_final = pd.DataFrame()
            for ticker in ativos_comp:
                try:
                    df_at = tv.get_hist(symbol=ticker, exchange='BMFBOVESPA', interval=tradutor_intervalo[tempo_comp], n_bars=periodo_comp)
                    if df_at is not None:
                        inicio = df_at['close'].iloc[0]
                        df_at[ticker] = ((df_at['close'] / inicio) - 1) * 100
                        if df_final.empty: df_final = df_at[[ticker]]
                        else: df_final = df_final.join(df_at[ticker], how='inner')
                except: pass

            if not df_final.empty:
                st.markdown("<br>", unsafe_allow_html=True)
                st.subheader(f"📈 Performance Relativa Acumulada ({tempo_comp})")
                st.line_chart(df_final, use_container_width=True)
                
                st.divider()

                col_rank, col_insight = st.columns([1, 2])
                with col_rank:
                    st.markdown("### 🏆 Ranking do Período")
                    ult_valores = df_final.iloc[-1].sort_values(ascending=False)
                    for i, (ticker, valor) in enumerate(ult_valores.items(), 1):
                        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏅"
                        st.write(f"{emoji} **{ticker}**: {valor:.2f}%")
                
                with col_insight:
                    st.markdown("### 💡 Insight do Comandante")
                    st.info(f"O ativo **{ult_valores.index[0]}** lidera a força relativa. A dispersão entre o primeiro e o último é de **{ult_valores.max() - ult_valores.min():.2f}%**.")

# ==========================================
# 4. MANUAL COMPLETO
# ==========================================
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("📖 Manual do Comparador: Como ler este gráfico?", expanded=False):
    st.markdown(f"""
    Este gráfico utiliza a técnica de **Normalização por Base Zero**.
    
    * **Entendendo as Barras:**
        * No **Gráfico Diário (1d)**: 20 barras ≈ 1 mês | 100 barras ≈ 5 meses | 250 barras ≈ 1 ano.
        * No **Gráfico de 60 min**: 7 barras ≈ 1 dia | 100 barras ≈ 14 dias | 300 barras ≈ 2 meses.
    * **O Ponto Zero:** Todos os ativos começam no 0% na primeira barra à esquerda.
    * **Variação Acumulada:** A linha mostra o ganho/perda real desde o início da janela. Ativos acima do zero com linha ascendente indicam **Acumulação Institucional**.
    """)
