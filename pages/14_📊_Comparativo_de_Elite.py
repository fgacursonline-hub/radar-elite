import streamlit as st
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
    st.error("❌ Arquivo 'motor_dados.py' não encontrado. O Comparador precisa dele para buscar os dados.")
    st.stop()

warnings.filterwarnings('ignore')

# ==========================================
# 1. SEGURANÇA E CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Comparador de Elite", layout="wide")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, inicie sessão na página inicial (Home).")
    st.stop()

# --- MAPEAMENTO DA LISTA GERAL ---
b3_symbols = [a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao + benchmarks_elite)]
lista_geral = sorted(list(set(b3_symbols + list(macro_elite.keys()))))

# ==========================================
# 2. FUNÇÃO DE LIMPEZA E PADRONIZAÇÃO
# ==========================================
def processar_ativo_comparador(df, simbolo, tempo, periodo):
    """Limpa o fuso horário, normaliza os nomes das colunas e alinha as datas."""
    if df is None or df.empty:
        return None
    
    # Padroniza as colunas (o motor pode retornar 'close' ou 'Close')
    df.columns = [c.capitalize() for c in df.columns]
    if 'Close' not in df.columns:
        return None
        
    # Corta para a janela desejada
    df = df.tail(periodo)
    
    # Remove Fuso Horário (Resolve os conflitos B3 vs Mundo)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
        
    # Se for gráfico diário, zera as horas (ex: 29/04/2026 00:00:00)
    if tempo == '1d': 
        df.index = df.index.normalize()
        
    # Garante que não tem índices duplicados
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
        ativos_comp = st.multiselect("Selecione até 6 ativos:", options=lista_geral, default=["PETR4", "BRN1!"], max_selections=6)
    with c2:
        tempo_comp = st.selectbox("Tempo Gráfico:", ['1d', '60m', '15m'], index=0, key="t_geral")
    with c3:
        periodo_comp = st.slider("Janela de Observação (Barras):", 20, 500, 100, key="p_geral")
        if tempo_comp == '1d':
            st.caption(f"🕒 **Referência:** {periodo_comp} barras ≈ {int(periodo_comp/20)} meses.")
        else:
            st.caption(f"🕒 **Referência:** {periodo_comp} barras ≈ {int(periodo_comp/7)} dias.")

    if st.button("🚀 Gerar Comparativo de Performance", type="primary", use_container_width=True):
        with st.spinner("Analisando e nivelando as cotações via Motor de Dados..."):
            df_final = pd.DataFrame()
            
            for t in ativos_comp:
                try:
                    # Usa o seu motor de dados cego
                    df_at_cru = puxar_dados_blindados(t, tempo_comp)
                    df_at = processar_ativo_comparador(df_at_cru, t, tempo_comp, periodo_comp)
                    
                    if df_at is not None and not df_at.empty:
                        # Ponto zero (Nivelamento em Porcentagem)
                        inicio = df_at['Close'].dropna().iloc[0]
                        df_at[t] = ((df_at['Close'] / inicio) - 1) * 100
                        
                        if df_final.empty: 
                            df_final = df_at[[t]]
                        else: 
                            # OUTER JOIN: Junta os calendários. Se a B3 for feriado, cria um "buraco" pra ela.
                            df_final = df_final.join(df_at[[t]], how='outer')
                except Exception as e: 
                    pass
            
            if not df_final.empty:
                # FFILL: Preenche os "buracos" de feriados/horários com o último preço conhecido
                df_final = df_final.ffill().fillna(0)
                
                st.line_chart(df_final)
                ult = df_final.iloc[-1].sort_values(ascending=False)
                st.info(f"🏆 Liderança do Período: **{ult.index[0]}** com **{ult.iloc[0]:.2f}%**. Diferença para o último colocado: **{ult.max()-ult.min():.2f}%**.")
            else: 
                st.error("Falha ao buscar dados no motor_dados ou não houve sobreposição compatível.")

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
        with st.spinner("Sincronizando mercados globais via Motor de Dados..."):
            
            # Puxa tudo pelo seu motor
            df_bdr_cru = puxar_dados_blindados(bdr_sel, tempo_inter)
            df_stock_cru = puxar_dados_blindados(stock_sel, tempo_inter)
            df_dolar_cru = puxar_dados_blindados('USDBRL', tempo_inter)

            df_bdr = processar_ativo_comparador(df_bdr_cru, bdr_sel, tempo_inter, periodo_inter)
            df_stock = processar_ativo_comparador(df_stock_cru, stock_sel, tempo_inter, periodo_inter)
            df_dolar = processar_ativo_comparador(df_dolar_cru, 'USDBRL', tempo_inter, periodo_inter)

            if all(v is not None for v in [df_bdr, df_stock, df_dolar]):
                
                # Nivelamento em Porcentagem
                df_bdr[bdr_sel] = ((df_bdr['Close'] / df_bdr['Close'].iloc[0]) - 1) * 100
                df_stock[stock_sel] = ((df_stock['Close'] / df_stock['Close'].iloc[0]) - 1) * 100
                df_dolar['DÓLAR'] = ((df_dolar['Close'] / df_dolar['Close'].iloc[0]) - 1) * 100

                # Junta os DataFrames preservando os feriados (outer join) e preenche vazios (ffill)
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
                else: st.error("Sincronização das datas falhou.")
            else:
                st.error("O motor_dados falhou em puxar os ativos gringos ou o dólar. Verifique a conexão.")

    st.markdown("---")
    st.markdown("### 📖 Glossário da Prova Real")
    st.markdown("""
    * **Retorno Teorico:** É a soma da variação da Stock lá fora com o Dólar aqui.
    * **Arbitragem:** Se o desvio for muito grande, robôs institucionais entrarão para fechar esse "gap".
    * **Atrasada:** Oportunidade de compra; a BDR ainda não reagiu à alta da Stock ou do Dólar.
    """)
