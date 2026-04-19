import streamlit as st
import pandas as pd
import pandas_ta as ta
initial_sidebar_state="expanded"
from tvDatafeed import TvDatafeed, Interval

# --- CONFIGURAÇÃO INICIAL DA PÁGINA ---
st.set_page_config(page_title="Raio-X Futuros", layout="wide")

# Inicializa o TradingView (Necessário em cada página nova)
@st.cache_resource
def login_tv():
    return TvDatafeed()

tv = login_tv()

# Tradutores necessários para a lógica
tradutor_periodo_nome = {'3mo': '3 Meses', '6mo': '6 Meses', '1y': '1 Ano', 'max': 'Todo o Histórico'}
tradutor_intervalo = {
    '15m': Interval.in_15_minute,
    '60m': Interval.in_1_hour,
    '1d': Interval.in_daily
}

# --- O CÓDIGO DA SUA ABA 5 ---
st.title("📈 Raio-X Mercado Futuro (WIN, WDO)")
st.markdown("Análise técnica detalhada para Day Trade.")

cf1, cf2, cf3 = st.columns(3)
with cf1:
    mapa_futuros = {"WINFUT (Mini Índice)": "WIN1!", "WDOFUT (Mini Dólar)": "WDO1!"}
    fut_selecionado = st.selectbox("Selecione o Ativo:", options=list(mapa_futuros.keys()), key="p_ativo")
    fut_ativo = mapa_futuros[fut_selecionado] 
    fut_estrategia = st.selectbox("Estratégia:", ["Padrão (Sem PM)", "PM Dinâmico", "Alvo & Stop Loss"], key="p_est")
    fut_periodo = st.selectbox("Período:", options=['3mo', '6mo', '1y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=1, key="p_per")

with cf2:
    fut_alvo = st.number_input("Alvo (Pontos):", value=300, step=50, key="p_alvo")
    fut_stop = st.number_input("Stop Loss (Pontos):", value=200, step=50, key="p_stop") if fut_estrategia == "Alvo & Stop Loss" else 0
    fut_contratos = st.number_input("Contratos:", value=1, step=1, key="p_cont")

with cf3:
    valor_mult_padrao = 0.20 if "WIN" in fut_selecionado else 10.00
    fut_multiplicador = st.number_input("Multiplicador (R$):", value=valor_mult_padrao, step=0.10, format="%.2f", key="p_mult")
    fut_tempo = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d'], index=0, key="p_tmp")
    fut_ifr = st.number_input("Período IFR:", min_value=2, max_value=50, value=8, step=1, key="p_ifr")

fut_zerar_daytrade = st.checkbox("⏰ Zeragem Automática no Fim do Dia", value=True, key="p_zerar")

if st.button("🚀 Rodar Backtest", type="primary", use_container_width=True):
    intervalo_tv = tradutor_intervalo.get(fut_tempo, Interval.in_15_minute)
    with st.spinner('Processando dados do TradingView...'):
        try:
            df_full = tv.get_hist(symbol=fut_ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=10000)
            if df_full is not None and len(df_full) > 50:
                df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                df_full['IFR'] = ta.rsi(df_full['Close'], length=fut_ifr)
                df_full['IFR_Prev'] = df_full['IFR'].shift(1)
                df_full = df_full.dropna()

                # Lógica de corte de data
                delta = {'3mo': 3, '6mo': 6, '1y': 12}.get(fut_periodo, 0)
                data_corte = df_full.index[-1] - pd.DateOffset(months=delta) if delta > 0 else df_full.index[0]
                df = df_full[df_full.index >= data_corte].copy()
                
                trades, em_pos, vitorias, derrotas = [], False, 0, 0
                df_back = df.reset_index()
                col_data = df_back.columns[0]

                # LOOP DE TRADES (A Lógica que validamos)
                for i in range(1, len(df_back)):
                    d_at = df_back[col_data].iloc[i]
                    d_ant = df_back[col_data].iloc[i-1]
                    
                    if em_pos and fut_zerar_daytrade and d_at.date() != d_ant.date():
                        p_sai = df_back['Close'].iloc[i-1]
                        p_en_c = preco_medio if fut_estrategia == "PM Dinâmico" else preco_entrada
                        luc = (p_sai - p_en_c) * (contratos_atuais if fut_estrategia == "PM Dinâmico" else fut_contratos) * fut_multiplicador
                        trades.append({'Entrada': d_ent.strftime('%d/%m/%Y %H:%M'), 'Saída': d_ant.strftime('%d/%m/%Y %H:%M'), 'Lucro (R$)': luc, 'Situação': 'Zerad. Fim Dia'})
                        if luc > 0: vitorias += 1
                        else: derrotas += 1
                        em_pos = False

                    cond_ent = (df_back['IFR_Prev'].iloc[i] < 25) and (df_back['IFR'].iloc[i] >= 25)
                    
                    if em_pos:
                        if fut_estrategia == "PM Dinâmico":
                            if df_back['High'].iloc[i] >= take_profit:
                                luc = fut_alvo * contratos_atuais * fut_multiplicador
                                trades.append({'Entrada': d_ent.strftime('%d/%m/%Y %H:%M'), 'Saída': d_at.strftime('%d/%m/%Y %H:%M'), 'Lucro (R$)': luc, 'Situação': 'Ganho ✅'})
                                em_pos, vitorias = False, vitorias + 1
                                continue
                        else:
                            if fut_estrategia == "Alvo & Stop Loss" and df_back['Low'].iloc[i] <= stop_p:
                                trades.append({'Entrada': d_ent.strftime('%d/%m/%Y %H:%M'), 'Saída': d_at.strftime('%d/%m/%Y %H:%M'), 'Lucro (R$)': -(fut_stop * fut_contratos * fut_multiplicador), 'Situação': 'Perda ❌'})
                                em_pos, derrotas = False, derrotas + 1
                                continue
                            elif df_back['High'].iloc[i] >= take_p:
                                trades.append({'Entrada': d_ent.strftime('%d/%m/%Y %H:%M'), 'Saída': d_at.strftime('%d/%m/%Y %H:%M'), 'Lucro (R$)': fut_alvo * fut_contratos * fut_multiplicador, 'Situação': 'Ganho ✅'})
                                em_pos, vitorias = False, vitorias + 1
                                continue
                    
                    if cond_ent and not em_pos:
                        em_pos, d_ent = True, d_at
                        if fut_estrategia == "PM Dinâmico":
                            preco_medio, contratos_atuais = df_back['Close'].iloc[i], fut_contratos
                            take_profit = preco_medio + fut_alvo
                        else:
                            preco_entrada = df_back['Close'].iloc[i]
                            take_p, stop_p = preco_entrada + fut_alvo, preco_entrada - fut_stop
                    elif cond_ent and em_pos and fut_estrategia == "PM Dinâmico":
                        preco_medio = ((preco_medio * contratos_atuais) + (df_back['Close'].iloc[i] * fut_contratos)) / (contratos_atuais + fut_contratos)
                        contratos_atuais += fut_contratos
                        take_profit = preco_medio + fut_alvo

                # EXIBIÇÃO
                if trades:
                    df_t = pd.DataFrame(trades)
                    lucro_total = df_t['Lucro (R$)'].sum()
                    vits = df_t[df_t['Lucro (R$)'] > 0]
                    t_acerto = (len(vits)/len(df_t))*100
                    
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Lucro Total", f"R$ {lucro_total:,.2f}")
                    m2.metric("Taxa Acerto", f"{t_acerto:.1f}%")
                    m3.metric("Operações", len(df_t))
                    
                    if lucro_total > 0: st.success("🚀 Estratégia Lucrativa no período!")
                    else: st.error("🚨 Estratégia prejuízo no período.")
                    
                    st.dataframe(df_t, use_container_width=True)
        except Exception as e: st.error(f"Erro: {e}")
