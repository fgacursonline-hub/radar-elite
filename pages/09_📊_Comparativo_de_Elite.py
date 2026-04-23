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

# Listas de Cadastro para facilitar a seleção
bdrs_elite = ['NVDC34', 'P2LT34', 'AAPL34', 'AMZO34', 'GOGL34', 'MSFT34', 'TSLA34', 'NFLX34', 'MELI34']
stocks_correspondentes = ['NVDA', 'PLTR', 'AAPL', 'AMZN', 'GOOGL', 'MSFT', 'TSLA', 'NFLX', 'MELI']
lista_sugestao = sorted(list(set(bdrs_elite + stocks_correspondentes + ['PETR4', 'VALE3', 'ITUB4'])))

# ==========================================
# 2. INTERFACE CENTRALIZADA
# ==========================================
st.set_page_config(page_title="Comparador de Elite", layout="wide")

st.title("📊 Comparador de Performance: BDR vs Stock")
st.markdown("Analise a força relativa entre a BDR (Brasil) e a Ação Original (EUA) para identificar o efeito do Dólar.")

st.divider()
st.subheader("⚙️ Configurações do Duelo Internacional")

c1, c2, c3 = st.columns([2, 1, 1])

with c1:
    # Usei multiselect mas permitindo digitar novos tickers para buscar stocks americanas
    ativos_comp = st.multiselect(
        "Selecione ou digite os tickers (Ex: NVDC34, NVDA):", 
        options=lista_sugestao, 
        default=["NVDC34", "NVDA"], 
        max_selections=4
    )
with c2:
    tempo_comp = st.selectbox("Tempo Gráfico:", ['1d', '60m'], index=0)
with c3:
    periodo_comp = st.slider("Janela de Observação (Barras):", 20, 300, 100)
    if tempo_comp == '1d':
        st.caption(f"🕒 Referência: {periodo_comp} barras ≈ {int(periodo_comp/20)} meses.")
    else:
        st.caption(f"🕒 Referência: {periodo_comp} barras ≈ {int(periodo_comp/7)} dias.")

btn_comp = st.button("🚀 Gerar Comparativo de Performance", type="primary", use_container_width=True)

# ==========================================
# 3. LÓGICA DE BUSCA HÍBRIDA (B3 E NYSE/NASDAQ)
# ==========================================
if btn_comp:
    if not ativos_comp:
        st.warning("⚠️ Selecione os ativos para comparar.")
    else:
        with st.spinner("Buscando dados globais..."):
            df_final = pd.DataFrame()
            
            for ticker in ativos_comp:
                try:
                    # Tenta primeiro na BMFBOVESPA, se falhar ou se for ticker curto, tenta NYSE/NASDAQ
                    if "34" in ticker or len(ticker) == 5: # Geralmente BDRs ou Ações BR
                        exchange = 'BMFBOVESPA'
                    else:
                        exchange = 'NYSE' # Padrão para Stocks, TvDatafeed costuma achar NASDAQ também por aqui
                    
                    df_at = tv.get_hist(symbol=ticker, exchange=exchange, interval=tradutor_intervalo[tempo_comp], n_bars=periodo_comp)
                    
                    # Se não achar na NYSE, tenta na NASDAQ (Segurança)
                    if df_at is None and exchange == 'NYSE':
                        df_at = tv.get_hist(symbol=ticker, exchange='NASDAQ', interval=tradutor_intervalo[tempo_comp], n_bars=periodo_comp)

                    if df_at is not None:
                        inicio = df_at['close'].iloc[0]
                        df_at[ticker] = ((df_at['close'] / inicio) - 1) * 100
                        
                        if df_final.empty:
                            df_final = df_at[[ticker]]
                        else:
                            # Sincroniza as datas (Inner Join) para que o gráfico não fique "quebrado"
                            df_final = df_final.join(df_at[ticker], how='inner')
                except:
                    st.error(f"Não foi possível encontrar dados para {ticker}")

            if not df_final.empty:
                st.markdown("<br>", unsafe_allow_html=True)
                st.subheader(f"📈 Duelo de Performance: {', '.join(ativos_comp)}")
                st.line_chart(df_final, use_container_width=True)
                
                st.divider()

                col_rank, col_insight = st.columns([1, 2])
                with col_rank:
                    st.markdown("### 🏆 Ranking")
                    ult_valores = df_final.iloc[-1].sort_values(ascending=False)
                    for i, (t, v) in enumerate(ult_valores.items(), 1):
                        emoji = "🥇" if i == 1 else "🥈"
                        st.write(f"{emoji} **{t}**: {v:.2f}%")
                
                with col_insight:
                    st.markdown("### 💡 Visão de Comandante")
                    if len(ativos_comp) >= 2:
                        # Lógica para detectar arbitragem/dólar
                        diff = ult_valores.iloc[0] - ult_valores.iloc[1]
                        st.info(f"""
                        A diferença de performance acumulada é de **{abs(diff):.2f}%**.
                        Se a BDR estiver rendendo MUITO mais que a Stock, o motor principal é o **Dólar**.
                        Se ambas andam juntas, o movimento é puramente institucional na empresa.
                        """)

# ==========================================
# 4. MANUAL DO COMPARADOR INTERNACIONAL
# ==========================================
st.markdown("---")
with st.expander("📖 Como operar o duelo BDR vs Stock?", expanded=False):
    st.markdown("""
    Comparar a BDR com a sua Stock original é o melhor jeito de saber se você está comprando uma empresa boa ou apenas apostando na queda do Real.

    * **Sincronização:** O robô ajusta os horários de abertura e fechamento para que o gráfico mostre apenas os momentos em que ambos os mercados estavam ativos.
    * **Arbitragem:** Quando a linha da Stock (Ex: NVDA) sobe e a BDR (Ex: NVDC34) fica parada, existe uma distorção de preço que costuma ser corrigida rapidamente.
    * **Efeito Câmbio:** Em períodos de crise no Brasil, é comum a Stock cair 2% e a BDR subir 1%. Isso acontece porque o Dólar subiu mais do que a ação caiu.
    """)
