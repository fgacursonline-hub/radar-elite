import streamlit as st
from tvDatafeed import TvDatafeed, Interval
import pandas as pd
import numpy as np
import warnings
import sys
import os

# --- AJUSTE DE CAMINHO PARA ENCONTRAR O CONFIG_ATIVOS ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from config_ativos import bdrs_elite, ibrx_selecao, pares_elite, benchmarks_elite, macro_elite
except ImportError:
    st.error("❌ Arquivo 'config_ativos.py' não encontrado na raiz do projeto.")
    st.stop()

warnings.filterwarnings('ignore')

# ==========================================
# 1. SEGURANÇA E CONEXÃO
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

# --- MAPEAMENTO INTELIGENTE DE BOLSAS (EXCHANGES) ---
b3_symbols = [a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao + benchmarks_elite)]
mapa_exchanges = {sym: 'BMFBOVESPA' for sym in b3_symbols}
mapa_exchanges.update(macro_elite)

lista_geral = sorted(list(mapa_exchanges.keys()))

# ==========================================
# 2. INTERFACE COM ABAS
# ==========================================
st.title("📊 Comparador de Performance Institucional")
st.markdown("Identifique qual ativo está atraindo mais capital e força relativa no período.")

tab_geral, tab_inter = st.tabs(["🌎 Comparativo Global & B3", "🇺🇸 Duelo BDR vs Stock + DÓLAR"])

# ------------------------------------------
# ABA 1: COMPARATIVO NACIONAL E GLOBAL
# ------------------------------------------
with tab_geral:
    st.subheader("⚙️ Configurações do Duelo")
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        ativos_comp = st.multiselect("Selecione até 6 ativos:", options=lista_geral, default=["PETR4", "BRN1!"], max_selections=6)
    with c2:
        tempo_comp = st.selectbox("Tempo Gráfico:", ['1d', '60m'], index=0, key="t_geral")
    with c3:
        periodo_comp = st.slider("Janela de Observação (Barras):", 20, 300, 100, key="p_geral")
        if tempo_comp == '1d':
            st.caption(f"🕒 **Referência:** {periodo_comp} barras ≈ {int(periodo_comp/20)} meses.")
        else:
            st.caption(f"🕒 **Referência:** {periodo_comp} barras ≈ {int(periodo_comp/7)} dias.")

    if st.button("🚀 Gerar Comparativo de Performance", type="primary", use_container_width=True):
        with st.spinner("Analisando e nivelando as cotações..."):
            df_final = pd.DataFrame()
            
            for t in ativos_comp:
                try:
                    bolsa_correta = mapa_exchanges.get(t, 'BMFBOVESPA')
                    df_at = tv.get_hist(symbol=t, exchange=bolsa_correta, interval=tradutor_intervalo[tempo_comp], n_bars=periodo_comp)
                    
                    if df_at is not None and not df_at.empty:
                        # --- O SEGREDO DA SINCRONIA GLOBAL ---
                        # 1. Tira o fuso horário para alinhar o mundo todo
                        df_at.index = pd.to_datetime(df_at.index).tz_localize(None)
                        # 2. No gráfico diário, zera as horas, deixando apenas as datas (ex: 29/04/2026)
                        if tempo_comp == '1d': 
                            df_at.index = df_at.index.normalize()

                        inicio = df_at['close'].iloc[0]
                        df_at[t] = ((df_at['close'] / inicio) - 1) * 100
                        
                        if df_final.empty: 
                            df_final = df_at[[t]]
                        else: 
                            # Usa OUTER join para não perder dados por causa de feriados distintos
                            df_final = df_final.join(df_at[t], how='outer')
                except Exception as e: 
                    pass
            
            if not df_final.empty:
                # Preenche eventuais buracos de feriados repetindo o preço do dia anterior (ffill)
                df_final = df_final.ffill().bfill()
                
                st.line_chart(df_final)
                ult = df_final.iloc[-1].sort_values(ascending=False)
                st.info(f"🏆 Liderança do Período: **{ult.index[0]}** com **{ult.iloc[0]:.2f}%**. Diferença para o último colocado: **{ult.max()-ult.min():.2f}%**.")
            else: 
                st.error("Falha ao buscar dados ou não houve sobreposição de datas compatíveis entre esses ativos.")

    st.markdown("---")
    st.markdown("### 📖 Glossário do Comparador")
    st.markdown("""
    * **Ponto Zero:** A primeira barra à esquerda é a linha de largada unificada (0%). 
    * **Variação %:** Mostra o ganho ou perda real desde o início do gráfico, ignorando moedas ou pontos (tudo é convertido em percentual para ser comparável lado a lado).
    * **Força Relativa:** Ativos com a linha consistentemente acima dos demais são os favoritos do fluxo de capital no momento.
    """)

# ------------------------------------------
# ABA 2: DUELO INTERNACIONAL (PROVA REAL)
# ------------------------------------------
with tab_inter:
    st.subheader("⚙️ Duelo BDR vs Stock com Prova Real do Dólar")
    ci1, ci2, ci3 = st.columns([2, 1, 1])
    with ci1:
        bdr_sel = st.selectbox("Selecione a BDR (Brasil):", options=sorted(pares_elite.keys()), index=0)
        stock_options = sorted(set(pares_elite.values()))
        stock_sel = st.selectbox("Stock correspondente (EUA):", options=stock_options, index=stock_options.index(pares_elite[bdr_sel]))
    with ci2:
        tempo_inter = st.selectbox("Tempo Gráfico:", ['1d', '60m'], index=0, key="t_inter")
    with ci3:
        periodo_inter = st.slider("Janela de Observação (Barras):", 20, 300, 100, key="p_inter")
        if tempo_inter == '1d':
            st.caption(f"🕒 **Referência:** {periodo_inter} barras ≈ {int(periodo_inter/20)} meses.")
        else:
            st.caption(f"🕒 **Referência:** {periodo_inter} barras ≈ {int(periodo_inter/7)} dias.")

    if st.button("📈 Gerar Análise de Arbitragem", type="primary", use_container_width=True):
        with st.spinner("Sincronizando mercados globais..."):
            df_bdr = tv.get_hist(symbol=bdr_sel, exchange='BMFBOVESPA', interval=tradutor_intervalo[tempo_inter], n_bars=periodo_inter)
            df_stock = tv.get_hist(symbol=stock_sel, exchange='NYSE', interval=tradutor_intervalo[tempo_inter], n_bars=periodo_inter)
            if df_stock is None: df_stock = tv.get_hist(symbol=stock_sel, exchange='NASDAQ', interval=tradutor_intervalo[tempo_inter], n_bars=periodo_inter)
            df_dolar = tv.get_hist(symbol='USDBRL', exchange='FX_IDC', interval=tradutor_intervalo[tempo_inter], n_bars=periodo_inter)

            if all(v is not None for v in [df_bdr, df_stock, df_dolar]):
                for df in [df_bdr, df_stock, df_dolar]:
                    df.index = pd.to_datetime(df.index).tz_localize(None)
                    if tempo_inter == '1d': df.index = df.index.normalize()

                df_bdr[bdr_sel] = ((df_bdr['close'] / df_bdr['close'].iloc[0]) - 1) * 100
                df_stock[stock_sel] = ((df_stock['close'] / df_stock['close'].iloc[0]) - 1) * 100
                df_dolar['DÓLAR'] = ((df_dolar['close'] / df_dolar['close'].iloc[0]) - 1) * 100

                df_prova = pd.merge(df_bdr[[bdr_sel]], df_stock[[stock_sel]], left_index=True, right_index=True, how='inner')
                df_prova = pd.merge(df_prova, df_dolar[['DÓLAR']], left_index=True, right_index=True, how='inner')

                if not df_prova.empty:
                    st.line_chart(df_prova, use_container_width=True)
                    st.divider()
                    
                    v_bdr, v_stock, v_dolar = df_prova[bdr_sel].iloc[-1], df_prova[stock_sel].iloc[-1], df_prova['DÓLAR'].iloc[-1]
                    c1, c2, c3 = st.columns(3)
                    c1.metric(f"Retorno {bdr_sel}", f"{v_bdr:.2f}%")
                    c2.metric(f"Retorno {stock_sel}", f"{v_stock:.2f}%")
                    c3.metric("Variação Dólar", f"{v_dolar:.2f}%")

                    ret_teo = v_stock + v_dolar
                    desvio = v_bdr - ret_teo
                    
                    st.subheader("🔬 Veredito da Arbitragem")
                    
                    if desvio < -1.0:
                        st.warning(f"⚠️ DESVIO CRÍTICO: {desvio:.2f}%")
                        st.write(f"**Pela soma (Stock + Dólar), sua BDR deveria estar rendendo {ret_teo:.2f}%, mas está em {v_bdr:.2f}%.**")
                        st.markdown(f"**ANÁLISE:** A BDR **{bdr_sel}** está **ATRASADA** (Barata) em relação à paridade internacional.")
                    elif desvio > 1.0:
                        st.error(f"🚨 DESVIO DE +{desvio:.2f}% DETECTADO")
                        st.write(f"**Pela soma (Stock + Dólar), sua BDR deveria estar rendendo {ret_teo:.2f}%, mas está em {v_bdr:.2f}%.**")
                        st.markdown(f"**ANÁLISE:** A BDR **{bdr_sel}** está **MAIS CARA** (Puxada) que a paridade americana.")
                    else:
                        st.success(f"✅ EFICIÊNCIA: Desvio de {desvio:.2f}%")
                        st.write("O mercado está em simetria perfeita. O preço da BDR reflete exatamente a Stock + Câmbio.")
                else: st.error("Sincronização falhou.")

    st.markdown("---")
    st.markdown("### 📖 Glossário da Prova Real")
    st.markdown("""
    * **Retorno Teorico:** É a soma da variação da Stock lá fora com o Dólar aqui.
    * **Arbitragem:** Se o desvio for muito grande, robôs institucionais entrarão para fechar esse "gap".
    * **Atrasada:** Oportunidade de compra; a BDR ainda não reagiu à alta da Stock ou do Dólar.
    """)

# ==========================================
# 3. MANUAL GLOBAL
# ==========================================
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("📖 Manual Completo: Como ler estes gráficos?", expanded=False):
    st.markdown("""
    * **Entendendo as Barras:** 
        * Diário (1d): 20 barras ≈ 1 mês. 
        * Hora (60m): 7 barras ≈ 1 dia.
    * **Base Zero:** Todos começam no mesmo ponto para comparar performance relativa, não preço bruto.
    * **Desvio:** Diferenças acima de 2% entre a BDR e sua Stock original costumam ser corrigidas rapidamente pelo mercado.
    """)
