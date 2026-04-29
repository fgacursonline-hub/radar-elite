import streamlit as st
from tvDatafeed import TvDatafeed, Interval
import pandas as pd
import numpy as np
import warnings
import sys
import os

# --- AJUSTE DE CAMINHO PARA ENCONTRAR O CONFIG E O MOTOR ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from config_ativos import bdrs_elite, ibrx_selecao, pares_elite, benchmarks_elite, macro_elite
except ImportError:
    st.error("❌ Arquivo 'config_ativos.py' não encontrado na raiz do projeto.")
    st.stop()

try:
    from motor_dados import puxar_dados_blindados
except ImportError:
    st.error("❌ Arquivo 'motor_dados.py' não encontrado.")
    st.stop()

warnings.filterwarnings('ignore')

# ==========================================
# 1. SEGURANÇA E CONEXÃO GERAL
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
# 2. FUNÇÕES HÍBRIDAS E DE LIMPEZA
# ==========================================
def buscar_dados_hibrido(simbolo, tempo, periodo):
    """
    Tenta o motor cego da B3. Se falhar (ativo gringo), usa conexão internacional.
    """
    bolsa = mapa_exchanges.get(simbolo, 'BMFBOVESPA')
    
    # Tratamento especial para Dólar e Stocks no Duelo Internacional
    if simbolo == 'USDBRL': bolsa = 'FX_IDC'
    elif simbolo in pares_elite.values(): bolsa = 'NYSE'
        
    # 1. Tenta usar o motor_dados blindado
    try:
        df_cru = puxar_dados_blindados(simbolo, tempo)
        if df_cru is not None and not df_cru.empty:
            return df_cru
    except:
        pass
        
    # 2. Se falhou (Gringo ou erro), vai na conexão direta
    try:
        intervalo_tv = tradutor_intervalo.get(tempo, Interval.in_daily)
        df_cru = tv.get_hist(symbol=simbolo, exchange=bolsa, interval=intervalo_tv, n_bars=periodo + 20)
        
        # Se for NYSE e falhar, tenta NASDAQ
        if df_cru is None and bolsa == 'NYSE':
            df_cru = tv.get_hist(symbol=simbolo, exchange='NASDAQ', interval=intervalo_tv, n_bars=periodo + 20)
            
        return df_cru
    except:
        return None

def processar_ativo_comparador(df, simbolo, tempo, periodo):
    """Limpa fuso horário, normaliza nomes e resolve problemas de feriado."""
    if df is None or df.empty:
        return None
    
    df.columns = [c.capitalize() for c in df.columns]
    if 'Close' not in df.columns:
        return None
        
    df = df.tail(periodo).copy()
    
    # Remove fuso horário para bater as datas do Brasil com o Exterior
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
        
    # No gráfico diário, apaga a hora pra cruzar perfeito (ex: 29/04/2026)
    if tempo == '1d': 
        df.index = df.index.normalize()
        
    df = df[~df.index.duplicated(keep='last')]
    return df

# ==========================================
# 3. INTERFACE COM ABAS
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
        ativos_comp = st.multiselect("Selecione até 6 ativos:", options=lista_geral, default=["IBOV", "EWZ"], max_selections=6)
    with c2:
        tempo_comp = st.selectbox("Tempo Gráfico:", ['1d', '60m', '15m'], index=0, key="t_geral")
    with c3:
        periodo_comp = st.slider("Janela de Observação (Barras):", 20, 500, 100, key="p_geral")
        if tempo_comp == '1d':
            st.caption(f"🕒 **Referência:** {periodo_comp} barras ≈ {int(periodo_comp/20)} meses.")
        else:
            st.caption(f"🕒 **Referência:** {periodo_comp} barras ≈ {int(periodo_comp/7)} dias.")

    if st.button("🚀 Gerar Comparativo de Performance", type="primary", use_container_width=True):
        if len(ativos_comp) < 2:
            st.warning("⚠️ Selecione pelo menos 2 ativos para fazer uma comparação justa.")
        else:
            with st.spinner("Analisando e nivelando as cotações..."):
                df_final = pd.DataFrame()
                sucessos = []
                falhas = []
                
                for t in ativos_comp:
                    df_at_cru = buscar_dados_hibrido(t, tempo_comp, periodo_comp)
                    df_at = processar_ativo_comparador(df_at_cru, t, tempo_comp, periodo_comp)
                    
                    if df_at is not None and not df_at.empty:
                        # Ponto zero percentual
                        inicio = df_at['Close'].dropna().iloc[0]
                        df_at[t] = ((df_at['Close'] / inicio) - 1) * 100
                        
                        if df_final.empty: 
                            df_final = df_at[[t]]
                        else: 
                            # OUTER JOIN junta as duas linhas mesmo com feriados desencontrados
                            df_final = df_final.join(df_at[[t]], how='outer')
                        sucessos.append(t)
                    else:
                        falhas.append(t)
                
                if falhas:
                    st.warning(f"⚠️ Não foi possível conectar aos seguintes ativos: **{', '.join(falhas)}**. Eles foram removidos do gráfico.")

                if not df_final.empty and len(sucessos) > 0:
                    # FFILL preenche o "buraco" de um feriado brasileiro copiando o preço de ontem
                    df_final = df_final.ffill().fillna(0)
                    
                    st.line_chart(df_final)
                    
                    if len(df_final.columns) > 1:
                        ult = df_final.iloc[-1].sort_values(ascending=False)
                        st.info(f"🏆 Liderança do Período: **{ult.index[0]}** com **{ult.iloc[0]:.2f}%**. Diferença para o último colocado: **{ult.max()-ult.min():.2f}%**.")
                else: 
                    st.error("Falha ao montar o gráfico. Nenhum dado compatível foi encontrado.")

    st.markdown("---")
    st.markdown("### 📖 Glossário do Comparador")
    st.markdown("""
    * **Ponto Zero:** A primeira barra à esquerda é a linha de largada unificada (0%). 
    * **Variação %:** Mostra o ganho ou perda real desde o início do gráfico.
    * **Preenchimento Automático:** Se um ativo for feriado e outro não (ex: B3 vs Ouro Global), a linha do ativo parado continua reta até o mercado reabrir.
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
        tempo_inter = st.selectbox("Tempo Gráfico:", ['1d', '60m', '15m'], index=0, key="t_inter")
    with ci3:
        periodo_inter = st.slider("Janela de Observação (Barras):", 20, 500, 100, key="p_inter")
        if tempo_inter == '1d':
            st.caption(f"🕒 **Referência:** {periodo_inter} barras ≈ {int(periodo_inter/20)} meses.")
        else:
            st.caption(f"🕒 **Referência:** {periodo_inter} barras ≈ {int(periodo_inter/7)} dias.")

    if st.button("📈 Gerar Análise de Arbitragem", type="primary", use_container_width=True):
        with st.spinner("Sincronizando mercados globais pelo Motor Híbrido..."):
            
            df_bdr_cru = buscar_dados_hibrido(bdr_sel, tempo_inter, periodo_inter)
            df_stock_cru = buscar_dados_hibrido(stock_sel, tempo_inter, periodo_inter)
            df_dolar_cru = buscar_dados_hibrido('USDBRL', tempo_inter, periodo_inter)

            df_bdr = processar_ativo_comparador(df_bdr_cru, bdr_sel, tempo_inter, periodo_inter)
            df_stock = processar_ativo_comparador(df_stock_cru, stock_sel, tempo_inter, periodo_inter)
            df_dolar = processar_ativo_comparador(df_dolar_cru, 'USDBRL', tempo_inter, periodo_inter)

            if all(v is not None for v in [df_bdr, df_stock, df_dolar]):
                
                # Nivelamento %
                df_bdr[bdr_sel] = ((df_bdr['Close'] / df_bdr['Close'].iloc[0]) - 1) * 100
                df_stock[stock_sel] = ((df_stock['Close'] / df_stock['Close'].iloc[0]) - 1) * 100
                df_dolar['DÓLAR'] = ((df_dolar['Close'] / df_dolar['Close'].iloc[0]) - 1) * 100

                # Outer join para lidar com os feriados dos EUA x Brasil
                df_prova = pd.DataFrame()
                df_prova = df_prova.join(df_bdr[[bdr_sel]], how='outer')\
                                   .join(df_stock[[stock_sel]], how='outer')\
                                   .join(df_dolar[['DÓLAR']], how='outer')
                
                df_prova = df_prova.ffill().dropna()

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
                else: st.error("Sincronização das datas falhou. Tente uma janela de observação maior.")
            else:
                st.error("O sistema falhou ao puxar um dos ativos internacionais. A corretora pode estar offline ou o código da Stock alterado.")

    st.markdown("---")
    st.markdown("### 📖 Glossário da Prova Real")
    st.markdown("""
    * **Retorno Teorico:** É a soma da variação da Stock lá fora com o Dólar aqui.
    * **Arbitragem:** Se o desvio for muito grande, robôs institucionais entrarão para fechar esse "gap".
    * **Atrasada:** Oportunidade de compra; a BDR ainda não reagiu à alta da Stock ou do Dólar.
    """)
