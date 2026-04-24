import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import warnings
import sys
import os
from datetime import datetime

warnings.filterwarnings('ignore')

# ==========================================
# 1. IMPORTAÇÃO CENTRALIZADA DOS ATIVOS
# ==========================================
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from config_ativos import bdrs_elite, ibrx_selecao
except ImportError:
    st.error("❌ Arquivo 'config_ativos.py' não encontrado na raiz do projeto.")
    st.stop()

# ==========================================
# 2. CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Radar TPV Elite", layout="wide", page_icon="🎯")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

st.title("🎯 Máquina Quantitativa: TPV (Tendência Preço/Volume)")
st.markdown("Opere o fluxo com base matemática: Oportunidades, Gestão de Posições e Backtest Estatístico.")

# ==========================================
# 3. PAINEL DE CONTROLE (FILTROS)
# ==========================================
with st.container(border=True):
    col_f1, col_f2, col_f3 = st.columns(3)

    with col_f1:
        lista_opcoes = ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"]
        lista_selecionada = st.selectbox("Lista de Ativos:", lista_opcoes)

    with col_f2:
        capital_trade = st.number_input("Capital por Trade (R$):", value=10000.00, step=1000.00)

    with col_f3:
        tempo_grafico = st.selectbox("Tempo Gráfico:", ["1d (Diário)", "1wk (Semanal)"])
        intervalo_yf = "1d" if "1d" in tempo_grafico else "1wk"

# Definição dos ativos baseado na seleção
if lista_selecionada == "BDRs Elite":
    ativos_alvo = bdrs_elite
elif lista_selecionada == "IBrX Seleção":
    ativos_alvo = ibrx_selecao
else:
    ativos_alvo = bdrs_elite + ibrx_selecao

ativos_alvo = sorted(list(set([a.replace('.SA', '') for a in ativos_alvo])))

btn_iniciar = st.button("🚀 Iniciar Varredura e Backtest TPV", type="primary", use_container_width=True)
# ==========================================
# 4. MOTOR DE BACKTEST E RASTREAMENTO
# ==========================================
def processar_tpv(lista_ativos, capital, intervalo):
    oportunidades_hoje = []
    operacoes_andamento = []
    historico_trades = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    hoje = datetime.now().date()
    
    for i, ativo in enumerate(lista_ativos):
        ticker = f"{ativo}.SA"
        status_text.text(f"Analisando histórico e posições: {ativo} ({i+1}/{len(lista_ativos)})")
        progress_bar.progress((i + 1) / len(lista_ativos))
        
        try:
            # Puxamos 2 anos para ter histórico suficiente para o Backtest e as Médias
            df = yf.download(ticker, period="2y", interval=intervalo, progress=False)
            
            if df.empty or len(df) < 60: continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            df.index = df.index.tz_localize(None) # Remove fuso horário para cálculos de data limpos

            # --- CÁLCULO TPV ---
            df['Retorno'] = df['Close'].pct_change()
            df['TPV'] = (df['Volume'] * df['Retorno']).cumsum()
            df['TPV_MA55'] = df['TPV'].rolling(window=55).mean()
            
            # --- CRUZAMENTOS (SINAIS) ---
            df['Cruzou_Compra'] = (df['TPV'].shift(1) <= df['TPV_MA55'].shift(1)) & (df['TPV'] > df['TPV_MA55'])
            df['Cruzou_Venda'] = (df['TPV'].shift(1) >= df['TPV_MA55'].shift(1)) & (df['TPV'] < df['TPV_MA55'])
            
            df.dropna(inplace=True)
            
            trade_aberto = None
            trades_fechados_ativo = []
            
            # --- MÁQUINA DO TEMPO (SIMULADOR DE TRADES) ---
            for j in range(len(df)):
                linha = df.iloc[j]
                data_atual = df.index[j]
                
                # Se não estamos posicionados, buscamos entrada
                if trade_aberto is None:
                    if linha['Cruzou_Compra']:
                        # Se for a ÚLTIMA barra do gráfico, é Oportunidade de Hoje
                        if j == len(df) - 1:
                            # Calcula divergência dos últimos 5 períodos
                            tendencia_preco = df['Close'].iloc[-1] - df['Close'].iloc[-5]
                            tendencia_tpv = df['TPV'].iloc[-1] - df['TPV'].iloc[-5]
                            div = "🚀 ALTA (Forte)" if (tendencia_preco < 0 and tendencia_tpv > 0) else "-"
                            
                            oportunidades_hoje.append({
                                "Ativo": ativo,
                                "Preço Atual": linha['Close'],
                                "Divergência (5p)": div
                            })
                        else:
                            # Registra a entrada no passado
                            trade_aberto = {
                                'entrada_data': data_atual,
                                'entrada_preco': linha['Close'],
                                'pico': linha['Close'],
                                'pior_queda': 0.0
                            }
                # Se já estamos posicionados
                else:
                    # Atualiza o pico máximo para medir Drawdown
                    if linha['High'] > trade_aberto['pico']:
                        trade_aberto['pico'] = linha['High']
                    
                    # Calcula o rebaixamento máximo (Drawdown) em relação ao pico
                    dd_atual = (linha['Low'] / trade_aberto['pico']) - 1
                    if dd_atual < trade_aberto['pior_queda']:
                        trade_aberto['pior_queda'] = dd_atual
                        
                    # Verifica condição de saída (Cruzou para Baixo)
                    if linha['Cruzou_Venda']:
                        lucro_pct = (linha['Close'] / trade_aberto['entrada_preco']) - 1
                        lucro_rs = capital * lucro_pct
                        
                        trades_fechados_ativo.append({
                            'lucro_pct': lucro_pct,
                            'lucro_rs': lucro_rs,
                            'pior_queda': trade_aberto['pior_queda']
                        })
                        trade_aberto = None # Zera posição
            
            # --- FINAL DO LOOP ---
            # Se o loop acabou e o trade ainda está aberto, vai para "Em Andamento"
            if trade_aberto is not None:
                dias_posicionado = (hoje - trade_aberto['entrada_data'].date()).days
                resultado_pct = (df['Close'].iloc[-1] / trade_aberto['entrada_preco']) - 1
                
                operacoes_andamento.append({
                    "Ativo": ativo,
                    "Entrada": trade_aberto['entrada_data'].strftime("%d/%m/%Y"),
                    "Dias": dias_posicionado,
                    "PM": trade_aberto['entrada_preco'],
                    "Cotação Atual": df['Close'].iloc[-1],
                    "Proj. Máx": trade_aberto['pior_queda'],
                    "Resultado Atual": resultado_pct
                })
                
            # Agrega estatísticas para o Backtest Histórico
            if len(trades_fechados_ativo) > 0:
                total_trades = len(trades_fechados_ativo)
                pior_queda_geral = min([t['pior_queda'] for t in trades_fechados_ativo])
                total_investido = capital * total_trades # Capital girado
                lucro_total_rs = sum([t['lucro_rs'] for t in trades_fechados_ativo])
                resultado_final_pct = lucro_total_rs / total_investido if total_investido > 0 else 0
                
                historico_trades.append({
                    "Ativo": ativo,
                    "Trades": total_trades,
                    "Pior Queda": pior_queda_geral,
                    "Investimentos": total_investido,
                    "Lucro R$": lucro_total_rs,
                    "Resultado": resultado_final_pct
                })

        except Exception as e:
            continue
            
    progress_bar.empty()
    status_text.empty()
    
    return pd.DataFrame(oportunidades_hoje), pd.DataFrame(operacoes_andamento), pd.DataFrame(historico_trades)

# ==========================================
# 5. RENDERIZAÇÃO DOS RESULTADOS
# ==========================================
if btn_iniciar:
    with st.spinner("Processando Inteligência de Fluxo..."):
        df_oportunidades, df_andamento, df_historico = processar_tpv(ativos_alvo, capital_trade, intervalo_yf)
        
        # --- SESSÃO 1: OPORTUNIDADES HOJE ---
        st.subheader("🚀 Oportunidades Hoje (Sinal Ativo)")
        if not df_oportunidades.empty:
            df_oportunidades['Preço Atual'] = df_oportunidades['Preço Atual'].apply(lambda x: f"R$ {x:.2f}")
            st.dataframe(df_oportunidades, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum ativo disparou sinal de entrada no pregão atual.")

        # --- SESSÃO 2: OPERAÇÕES EM ANDAMENTO ---
        st.subheader("⏳ Operações em Andamento (Aguardando Alvo/Venda)")
        if not df_andamento.empty:
            # Formatação
            df_andamento['PM'] = df_andamento['PM'].apply(lambda x: f"R$ {x:.2f}")
            df_andamento['Cotação Atual'] = df_andamento['Cotação Atual'].apply(lambda x: f"R$ {x:.2f}")
            df_andamento['Proj. Máx'] = df_andamento['Proj. Máx'].apply(lambda x: f"{x*100:.2f}%")
            
            def color_resultado_andamento(val):
                if isinstance(val, str): return ''
                color = '#00FFCC' if val > 0 else '#FF4D4D'
                return f'color: {color}; font-weight: bold'

            st.dataframe(
                df_andamento.style.format({'Resultado Atual': "{:.2%}"}).map(color_resultado_andamento, subset=['Resultado Atual']),
                use_container_width=True, hide_index=True
            )
        else:
            st.info("Nenhuma operação em aberto no momento para a lista selecionada.")

        # --- SESSÃO 3: BACKTEST (TOP 20 HISTÓRICO) ---
        st.subheader("📊 Top 20 Histórico (Estatística do TPV)")
        if not df_historico.empty:
            # Ordena pelos mais lucrativos e pega os 20 primeiros
            df_historico = df_historico.sort_values(by="Lucro R$", ascending=False).head(20)
            
            df_historico['Pior Queda'] = df_historico['Pior Queda'].apply(lambda x: f"{x*100:.2f}%")
            df_historico['Investimentos'] = df_historico['Investimentos'].apply(lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
            
            def color_lucro(val):
                if isinstance(val, str): return ''
                color = '#00FFCC' if val > 0 else '#FF4D4D'
                return f'color: {color}'

            st.dataframe(
                df_historico.style
                .format({
                    'Lucro R$': "R$ {:,.2f}",
                    'Resultado': "{:.2%}"
                })
                .map(color_lucro, subset=['Lucro R$', 'Resultado']),
                use_container_width=True, hide_index=True
            )
            
            st.markdown("---")
            st.markdown("""
            **🔍 Como interpretar o Laboratório:**
            * **Pior Queda (Drawdown):** O máximo que a operação ficou negativa antes de fechar. Isso ajuda a calibrar o seu *Stop Loss*. Se a pior queda média é -8%, não adianta colocar um stop de -3%, você será "violinado".
            * **Resultado (%):** Representa a eficiência do capital girado (Lucro / Total Investido em todos os trades do ativo).
            """)
