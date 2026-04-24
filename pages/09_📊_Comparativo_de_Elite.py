import streamlit as st
from tvDatafeed import TvDatafeed, Interval
import pandas as pd
import numpy as np
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. SEGURANÇA E CONFIGURAÇÃO INICIAL
# ==========================================
st.set_page_config(page_title="Comparador de Elite", layout="wide")

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

# --- MAPEAMENTO DE ELITE (BDR ↔ STOCK) ---
# Lista organizada para facilitar o "duelo" correto
pares_elite = {
    'NVDC34': 'NVDA', 'P2LT34': 'PLTR', 'ROXO34': 'NU', 'INBR32': 'INTR',
    'M1TA34': 'META', 'TSLA34': 'TSLA', 'LILY34': 'LLY', 'AMZO34': 'AMZN',
    'AURA33': 'AUY',  'GOGL34': 'GOOGL','MSFT34': 'MSFT', 'MUTC34': 'MU',
    'MELI34': 'MELI', 'C2OI34': 'COIN', 'ORCL34': 'ORCL', 'M2ST34': 'MA',
    'A1MD34': 'AMD',  'NFLX34': 'NFLX', 'ITLC34': 'INTC', 'AVGO34': 'AVGO',
    'COCA34': 'KO',   'JBSS32': 'JBS',  'AAPL34': 'AAPL', 'XPBR31': 'XP',
    'STOC34': 'STNE'
}

# Listas de Cadastro para a Aba 1
ibrx_selecao = ['PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'BBDC4.SA', 'BBAS3.SA', 'B3SA3.SA', 'ABEV3.SA', 'WEGE3.SA', 'AXIA3.SA', 'SUZB3.SA', 'RENT3.SA', 'RADL3.SA', 'EQTL3.SA', 'LREN3.SA', 'PRIO3.SA', 'HAPV3.SA', 'GGBR4.SA', 'VBBR3.SA', 'SBSP3.SA', 'CMIG4.SA', 'CPLE3.SA', 'ENEV3.SA', 'TIMS3.SA', 'TOTS3.SA', 'EGIE3.SA', 'CSAN3.SA', 'ALOS3.SA', 'DIRR3.SA', 'VIVT3.SA', 'KLBN11.SA', 'UGPA3.SA', 'PSSA3.SA', 'CYRE3.SA', 'ASAI3.SA', 'RAIL3.SA', 'ISAE3.SA', 'CSNA3.SA', 'MGLU3.SA', 'EMBJ3.SA', 'TAEE11.SA', 'BBSE3.SA', 'FLRY3.SA', 'MULT3.SA', 'TFCO4.SA', 'LEVE3.SA', 'CPFE3.SA', 'GOAU4.SA', 'MRVE3.SA', 'YDUQ3.SA', 'SMTO3.SA', 'SLCE3.SA', 'CVCB3.SA', 'USIM5.SA', 'BRAP4.SA', 'BRAV3.SA', 'EZTC3.SA', 'PCAR3.SA', 'AUAU3.SA', 'DXCO3.SA', 'CASH3.SA', 'VAMO3.SA', 'AZZA3.SA', 'AURE3.SA', 'BEEF3.SA', 'ECOR3.SA', 'FESA4.SA', 'POMO4.SA', 'CURY3.SA', 'INTB3.SA', 'JHSF3.SA', 'LIGT3.SA', 'LOGG3.SA', 'MDIA3.SA', 'MBRF3.SA', 'NEOE3.SA', 'QUAL3.SA', 'RAPT4.SA', 'ROMI3.SA', 'SANB11.SA', 'SIMH3.SA', 'TEND3.SA', 'VULC3.SA', 'PLPL3.SA', 'CEAB3.SA', 'UNIP6.SA', 'LWSA3.SA', 'BPAC11.SA', 'GMAT3.SA', 'CXSE3.SA', 'ABCB4.SA', 'CSMG3.SA', 'SAPR11.SA', 'GRND3.SA', 'BRAP3.SA', 'LAVV3.SA', 'RANI3.SA', 'ITSA3.SA', 'ALUP11.SA', 'FIQE3.SA', 'COGN3.SA', 'IRBR3.SA', 'SEER3.SA', 'ANIM3.SA', 'JSLG3.SA', 'POSI3.SA', 'MYPK3.SA', 'SOJA3.SA', 'BLAU3.SA', 'PGMN3.SA', 'TUPY3.SA', 'VVEO3.SA', 'MELK3.SA', 'SHUL4.SA', 'BRSR6.SA']
lista_b3_pura = sorted(list(set([a.replace('.SA', '') for a in (list(pares_elite.keys()) + ibrx_selecao)])))

# ==========================================
# 2. INTERFACE COM ABAS
# ==========================================
st.title("📊 Comparador de Performance Institucional")
st.markdown("Identifique qual ativo está atraindo mais capital e força relativa no período.")

tab_geral, tab_inter = st.tabs(["🌎 Comparativo Geral (B3)", "🇺🇸 Duelo BDR vs Stock"])

# ------------------------------------------
# ABA 1: COMPARATIVO GERAL (NACIONAL)
# ------------------------------------------
with tab_geral:
    st.subheader("⚙️ Configurações do Duelo B3")
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        ativos_comp = st.multiselect("Selecione até 4 ativos do cadastro:", options=lista_b3_pura, default=["PETR4", "VALE3"], max_selections=4)
    with c2:
        tempo_comp = st.selectbox("Tempo Gráfico:", ['1d', '60m'], index=0, key="t_geral")
    with c3:
        periodo_comp = st.slider("Janela de Observação (Barras):", 20, 300, 100, key="p_geral")
        if tempo_comp == '1d':
            st.caption(f"🕒 **Referência:** {periodo_comp} barras ≈ {int(periodo_comp/20)} meses.")
        else:
            st.caption(f"🕒 **Referência:** {periodo_comp} barras ≈ {int(periodo_comp/7)} dias.")

    btn_comp = st.button("🚀 Gerar Comparativo Nacional", type="primary", use_container_width=True)

    if btn_comp:
        if not ativos_comp:
            st.warning("⚠️ Selecione pelo menos um ativo.")
        else:
            with st.spinner("Analisando rastro do dinheiro..."):
                df_final = pd.DataFrame()
                for t in ativos_comp:
                    try:
                        df_at = tv.get_hist(symbol=t, exchange='BMFBOVESPA', interval=tradutor_intervalo[tempo_comp], n_bars=periodo_comp)
                        if df_at is not None:
                            inicio = df_at['close'].iloc[0]
                            df_at[t] = ((df_at['close'] / inicio) - 1) * 100
                            if df_final.empty: df_final = df_at[[t]]
                            else: df_final = df_final.join(df_at[t], how='inner')
                    except: pass
                
                if not df_final.empty:
                    st.line_chart(df_final)
                    ult = df_final.iloc[-1].sort_values(ascending=False)
                    st.info(f"🏆 Liderança: **{ult.index[0]}** com retorno de **{ult.iloc[0]:.2f}%** no período.")
                else:
                    st.error("Não foi possível carregar os dados para comparação.")

# ------------------------------------------
# ABA 2: DUELO INTERNACIONAL (BDR VS STOCK)
# ------------------------------------------
with tab_inter:
    st.subheader("⚙️ Configurações do Duelo BDR vs Stock")
    ci1, ci2, ci3 = st.columns([2, 1, 1])
    with ci1:
        bdr_input = st.selectbox("Selecione a BDR (Brasil):", options=sorted(pares_elite.keys()), index=0)
        # NOVO: Selectbox preenchida com as Stocks americanas correspondentes
        stock_input = st.selectbox("Selecione a Stock correspondente (EUA):", options=sorted(set(pares_elite.values())), index=sorted(set(pares_elite.values())).index(pares_elite[bdr_input]))
    with ci2:
        tempo_inter = st.selectbox("Tempo Gráfico:", ['1d', '60m'], index=0, key="t_inter")
    with ci3:
        periodo_inter = st.slider("Janela de Observação (Barras):", 20, 300, 100, key="p_inter")
        if tempo_inter == '1d':
            st.caption(f"🕒 **Referência:** {periodo_inter} barras ≈ {int(periodo_inter/20)} meses.")
        else:
            st.caption(f"🕒 **Referência:** {periodo_inter} barras ≈ {int(periodo_inter/7)} dias.")

    btn_inter = st.button("🚀 Gerar Duelo Internacional", type="primary", use_container_width=True)

    if btn_inter:
        with st.spinner(f"Sincronizando mercados (B3 🇧🇷 vs EUA 🇺🇸) para {bdr_input} vs {stock_input}..."):
            df_bdr = tv.get_hist(symbol=bdr_input, exchange='BMFBOVESPA', interval=tradutor_intervalo[tempo_inter], n_bars=periodo_inter)
            
            # Tenta NYSE, depois NASDAQ
            df_stock = tv.get_hist(symbol=stock_input, exchange='NYSE', interval=tradutor_intervalo[tempo_inter], n_bars=periodo_inter)
            if df_stock is None:
                df_stock = tv.get_hist(symbol=stock_input, exchange='NASDAQ', interval=tradutor_intervalo[tempo_inter], n_bars=periodo_inter)

            if df_bdr is not None and df_stock is not None:
                # Sincronização de datas (tz_localize(None) remove o erro de fusos)
                df_bdr.index = pd.to_datetime(df_bdr.index).tz_localize(None)
                df_stock.index = pd.to_datetime(df_stock.index).tz_localize(None)
                
                if tempo_inter == '1d':
                    df_bdr.index = df_bdr.index.normalize()
                    df_stock.index = df_stock.index.normalize()

                df_bdr[bdr_input] = ((df_bdr['close'] / df_bdr['close'].iloc[0]) - 1) * 100
                df_stock[stock_input] = ((df_stock['close'] / df_stock['close'].iloc[0]) - 1) * 100
                
                df_duelo = pd.merge(df_bdr[[bdr_input]], df_stock[[stock_input]], left_index=True, right_index=True, how='inner')

                if not df_duelo.empty:
                    st.markdown(f"### 📈 Performance: {bdr_input} vs {stock_input}")
                    st.line_chart(df_duelo, use_container_width=True)
                    
                    st.divider()
                    
                    c_res1, c_res2 = st.columns(2)
                    with c_res1:
                        v_bdr = df_duelo[bdr_input].iloc[-1]
                        v_stock = df_duelo[stock_input].iloc[-1]
                        st.metric(f"Retorno {bdr_input}", f"{v_bdr:.2f}%")
                        st.metric(f"Retorno {stock_input}", f"{v_stock:.2f}%")
                    with c_res2:
                        diff = v_bdr - v_stock
                        st.markdown("### 💡 Insight de Arbitragem")
                        if abs(diff) > 2:
                            st.warning(f"Desvio de **{abs(diff):.2f}%** detectado!")
                        else:
                            st.success(f"Simetria de **{abs(diff):.2f}%**. Fluxo equilibrado.")
                else:
                    st.error("⚠️ Datas não coincidentes. Tente aumentar a janela para 200 barras.")
            else:
                st.error(f"❌ Erro: Não encontrei dados para '{stock_input}' nos EUA.")

# ==========================================
# 4. MANUAL COMPLETO
# ==========================================
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("📖 Manual do Comparador: Como ler estes dados?", expanded=True):
    st.markdown("""
    * **Entendendo o Tempo:**
        * **1d (Diário):** 20 barras ≈ 1 mês | 100 barras ≈ 5 meses | 250 barras ≈ 1 ano.
        * **60m (Hora):** 7 barras ≈ 1 dia de pregão | 140 barras ≈ 1 mês.
    * **Normalização por Base Zero:** Todos os ativos começam no 0% na primeira barra. Isso permite comparar uma ação de R$ 10 com uma de R$ 100 de forma justa.
    * **Duelo BDR vs Stock:** Se a BDR estiver rendendo muito mais que a Stock, a valorização é puxada pelo Dólar. Se andarem juntas, o movimento é puro institucional na empresa.
    """)
