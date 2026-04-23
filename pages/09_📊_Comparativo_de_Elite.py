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

# Listas de Cadastro (Mantidas para o Menu)
bdrs_elite = ['NVDC34.SA', 'P2LT34.SA', 'ROXO34.SA', 'INBR32.SA', 'M1TA34.SA', 'TSLA34.SA', 'LILY34.SA', 'AMZO34.SA', 'AURA33.SA', 'GOGL34.SA', 'MSFT34.SA', 'MUTC34.SA', 'MELI34.SA', 'C2OI34.SA', 'ORCL34.SA', 'M2ST34.SA', 'A1MD34.SA', 'NFLX34.SA', 'ITLC34.SA', 'AVGO34.SA', 'COCA34.SA', 'JBSS32.SA', 'AAPL34.SA', 'XPBR31.SA', 'STOC34.SA']
ibrx_selecao = ['PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'BBDC4.SA', 'BBAS3.SA', 'B3SA3.SA', 'ABEV3.SA', 'WEGE3.SA', 'AXIA3.SA', 'SUZB3.SA', 'RENT3.SA', 'RADL3.SA', 'EQTL3.SA', 'LREN3.SA', 'PRIO3.SA', 'HAPV3.SA', 'GGBR4.SA', 'VBBR3.SA', 'SBSP3.SA', 'CMIG4.SA', 'CPLE3.SA', 'ENEV3.SA', 'TIMS3.SA', 'TOTS3.SA', 'EGIE3.SA', 'CSAN3.SA', 'ALOS3.SA', 'DIRR3.SA', 'VIVT3.SA', 'KLBN11.SA', 'UGPA3.SA', 'PSSA3.SA', 'CYRE3.SA', 'ASAI3.SA', 'RAIL3.SA', 'ISAE3.SA', 'CSNA3.SA', 'MGLU3.SA', 'EMBJ3.SA', 'TAEE11.SA', 'BBSE3.SA', 'FLRY3.SA', 'MULT3.SA', 'TFCO4.SA', 'LEVE3.SA', 'CPFE3.SA', 'GOAU4.SA', 'MRVE3.SA', 'YDUQ3.SA', 'SMTO3.SA', 'SLCE3.SA', 'CVCB3.SA', 'USIM5.SA', 'BRAP4.SA', 'BRAV3.SA', 'EZTC3.SA', 'PCAR3.SA', 'AUAU3.SA', 'DXCO3.SA', 'CASH3.SA', 'VAMO3.SA', 'AZZA3.SA', 'AURE3.SA', 'BEEF3.SA', 'ECOR3.SA', 'FESA4.SA', 'POMO4.SA', 'CURY3.SA', 'INTB3.SA', 'JHSF3.SA', 'LIGT3.SA', 'LOGG3.SA', 'MDIA3.SA', 'MBRF3.SA', 'NEOE3.SA', 'QUAL3.SA', 'RAPT4.SA', 'ROMI3.SA', 'SANB11.SA', 'SIMH3.SA', 'TEND3.SA', 'VULC3.SA', 'PLPL3.SA', 'CEAB3.SA', 'UNIP6.SA', 'LWSA3.SA', 'BPAC11.SA', 'GMAT3.SA', 'CXSE3.SA', 'ABCB4.SA', 'CSMG3.SA', 'SAPR11.SA', 'GRND3.SA', 'BRAP3.SA', 'LAVV3.SA', 'RANI3.SA', 'ITSA3.SA', 'ALUP11.SA', 'FIQE3.SA', 'COGN3.SA', 'IRBR3.SA', 'SEER3.SA', 'ANIM3.SA', 'JSLG3.SA', 'POSI3.SA', 'MYPK3.SA', 'SOJA3.SA', 'BLAU3.SA', 'PGMN3.SA', 'TUPY3.SA', 'VVEO3.SA', 'MELK3.SA', 'SHUL4.SA', 'BRSR6.SA']

lista_unificada = sorted(list(set([a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)])))

# ==========================================
# 2. INTERFACE DO COMPARADOR
# ==========================================
st.set_page_config(page_title="Comparador de Elite", layout="wide")

st.title("📊 Comparador de Performance Institucional")
st.markdown("Identifique qual ativo está atraindo mais capital e força relativa no período.")

with st.sidebar:
    st.header("⚙️ Configurações do Duelo")
    ativos_comp = st.multiselect("Selecione até 4 ativos:", options=lista_unificada, default=["PETR4", "VALE3"], max_selections=4)
    tempo_comp = st.selectbox("Tempo Gráfico:", ['1d', '60m'], index=0)
    periodo_comp = st.slider("Janela de Observação (Barras):", 20, 300, 100)
    btn_comp = st.button("📈 Gerar Comparativo", type="primary", use_container_width=True)

if btn_comp:
    if not ativos_comp:
        st.warning("⚠️ Selecione pelo menos um ativo para comparar.")
    else:
        with st.spinner("Sincronizando dados e normalizando retornos..."):
            df_final = pd.DataFrame()
            
            for ticker in ativos_comp:
                try:
                    df_at = tv.get_hist(symbol=ticker, exchange='BMFBOVESPA', interval=tradutor_intervalo[tempo_comp], n_bars=periodo_comp)
                    if df_at is not None:
                        # Normalização: Retorno Acumulado %
                        # Faz com que todos os ativos comecem em 0%
                        inicio = df_at['close'].iloc[0]
                        df_at[ticker] = ((df_at['close'] / inicio) - 1) * 100
                        
                        # Adiciona ao dataframe final usando o index (data)
                        if df_final.empty:
                            df_final = df_at[[ticker]]
                        else:
                            df_final = df_final.join(df_at[ticker], how='inner')
                except Exception as e:
                    st.error(f"❌ Erro ao processar {ticker}")

            if not df_final.empty:
                # Exibição do Gráfico Principal
                st.subheader(f"📈 Desempenho Relativo ({tempo_comp})")
                st.line_chart(df_final, use_container_width=True)
                
                st.divider()

                # Ranking de Performance
                col_rank, col_desc = st.columns([1, 2])
                
                with col_rank:
                    st.markdown("### 🏆 Ranking Final")
                    ult_valores = df_final.iloc[-1].sort_values(ascending=False)
                    for i, (ticker, valor) in enumerate(ult_valores.items(), 1):
                        label = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏅"
                        st.write(f"{label} **{ticker}**: {valor:.2f}%")
                
                with col_desc:
                    st.markdown("### 💡 Insight do Comandante")
                    melhor = ult_valores.index[0]
                    pior = ult_valores.index[-1]
                    distancia = ult_valores.max() - ult_valores.min()
                    
                    st.info(f"""
                    No período analisado, o ativo **{melhor}** lidera a força relativa. 
                    A diferença entre o melhor e o pior desempenho (**{pior}**) é de **{distancia:.2f}%**. 
                    Foque seus estudos de fluxo no ativo que está acima da linha zero e liderando o ranking.
                    """)

# ==========================================
# 3. GLOSSÁRIO TÉCNICO (O MANUAL)
# ==========================================
st.markdown("---")
with st.expander("📖 Manual do Comparador: Como ler este gráfico?", expanded=False):
    st.markdown("""
    Este gráfico utiliza a técnica de **Normalização por Base Zero**. É a mesma lógica usada para comparar o PIB de diferentes países ou a inflação de moedas distintas.

    * **O Ponto Zero:** O lado esquerdo do gráfico (a primeira barra) é sempre o zero. Isso significa que não importa se a ação custa R$ 10 ou R$ 100, todas partem da mesma linha de largada.
    * **Variação Acumulada:** Cada ponto na linha representa o quanto aquele ativo valorizou ou desvalorizou *desde o início do período selecionado*.
    * **Interpretação de Força:** Se a linha de um ativo está acima das outras, ele possui **Força Relativa**. Isso indica que o fluxo comprador institucional está mais denso nesse ativo do que nos demais.
    * **Uso Prático:** Ótimo para decidir qual ação do mesmo setor comprar (ex: comparar bancos entre si) ou para ver se uma BDR está acompanhando o índice lá fora.
    """)
