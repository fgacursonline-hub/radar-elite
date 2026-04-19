import streamlit as st
from tvDatafeed import TvDatafeed, Interval
import pandas as pd
import pandas_ta as ta
import time
import warnings

warnings.filterwarnings('ignore')

# 1. SEGURANÇA (Verifica se logou no app.py)
if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

# 2. CONEXÃO E LISTAS (Seu código íntegro)
@st.cache_resource
def get_tv_connection():
    return TvDatafeed()

tv = get_tv_connection()

tradutor_periodo_nome = {
    '1mo': '1 Mês', '3mo': '3 Meses', '6mo': '6 Meses',
    '1y': '1 Ano', '2y': '2 Anos', '5y': '5 Anos',
    'max': 'Máximo', '60d': '60 Dias'
}

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

def colorir_lucro(row):
    if 'Resultado Atual' in row and isinstance(row['Resultado Atual'], str) and row['Resultado Atual'].startswith('+'):
        return ['color: #00FF00; font-weight: bold'] * len(row)
    return [''] * len(row)

# 3. INTERFACE DE ABAS
st.title("📈 Estratégia: IFR")
aba_padrao, aba_pm, aba_stop, aba_individual, aba_futuros = st.tabs([
    "📡 Radar (Padrão)", "📡 Radar (PM)", "🛡️ Alvo & Stop", "🔬 Raio-X Individual", "📉 Raio-X Futuros"
])

# ==========================================
# ABA 1: RADAR PADRÃO (SEU CÓDIGO ÍNTEGRO)
# ==========================================
with aba_padrao:
    st.subheader("📡 Radar Padrão (Entrada Única & Alvo Fixo)")
    
    cp1, cp2, cp3 = st.columns(3)
    with cp1:
        lista_padrao = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"], key="p_lista")
        ativos_padrao = bdrs_elite if lista_padrao == "BDRs Elite" else ibrx_selecao if lista_padrao == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        periodo_padrao = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=3, key="p_per")
    with cp2:
        alvo_padrao = st.number_input("Alvo de Lucro (%):", value=5.0, step=0.5, key="p_alvo")
        ifr_padrao = st.number_input("Período do IFR:", min_value=2, max_value=50, value=8, step=1, key="p_ifr")
    with cp3:
        capital_padrao = st.number_input("Capital por Trade (R$):", value=10000.0, step=1000.0, key="p_cap")
        tempo_padrao = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="p_tmp")

    btn_iniciar_padrao = st.button("🚀 Iniciar Varredura Padrão", type="primary", use_container_width=True, key="p_btn")

    if btn_iniciar_padrao:
        # Lógica de ajuste de período automática do seu código original
        if tempo_padrao == '15m' and periodo_padrao not in ['1mo', '3mo']: periodo_padrao = '60d'
        elif tempo_padrao == '60m' and periodo_padrao in ['5y', 'max']: periodo_padrao = '2y'

        intervalo_tv = tradutor_intervalo.get(tempo_padrao, Interval.in_daily)
        alvo_dec = alvo_padrao / 100

        ls_sinais_p, ls_abertos_p, ls_resumo_p = [], [], []
        p_bar_p = st.progress(0)
        s_text_p = st.empty()

        for idx, ativo_raw in enumerate(ativos_padrao):
            ativo = ativo_raw.replace('.SA', '')
            s_text_p.text(f"🔍 Analisando (Padrão): {ativo} ({idx+1}/{len(ativos_padrao)})")
            p_bar_p.progress((idx + 1) / len(ativos_padrao))

            try:
                df_full = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=5000)
                if df_full is None or len(df_full) < 50: continue

                df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                df_full = df_full.dropna()
                
                df_full['IFR'] = ta.rsi(df_full['Close'], length=ifr_padrao)
                df_full['IFR_Prev'] = df_full['IFR'].shift(1)
                df_full = df_full.dropna()

                # Cálculo da data de corte
                data_atual = df_full.index[-1]
                if periodo_padrao == '1mo': data_corte = data_atual - pd.DateOffset(months=1)
                elif periodo_padrao == '3mo': data_corte = data_atual - pd.DateOffset(months=3)
                elif periodo_padrao == '6mo': data_corte = data_atual - pd.DateOffset(months=6)
                elif periodo_padrao == '1y': data_corte = data_atual - pd.DateOffset(years=1)
                elif periodo_padrao == '2y': data_corte = data_atual - pd.DateOffset(years=2)
                elif periodo_padrao == '5y': data_corte = data_atual - pd.DateOffset(years=5)
                elif periodo_padrao == '60d': data_corte = data_atual - pd.DateOffset(days=60)
                else: data_corte = df_full.index[0]

                df = df_full[df_full.index >= data_corte].copy()
                if len(df) == 0: continue

                # Backtest do Radar Padrão
                trades, em_pos = [], False
                df_back = df.reset_index()
                col_data = df_back.columns[0]

                for i in range(1, len(df_back)):
                    if em_pos:
                        if df_back['Low'].iloc[i] < min_price_in_trade:
                            min_price_in_trade = df_back['Low'].iloc[i]
                        if df_back['High'].iloc[i] >= take_profit:
                            trades.append({'Lucro (R$)': float(capital_padrao) * alvo_dec, 'Drawdown_Raw': ((min_price_in_trade / preco_entrada) - 1) * 100})
                            em_pos = False
                            continue

                    condicao_entrada = (df_back['IFR_Prev'].iloc[i] < 25) and (df_back['IFR'].iloc[i] >= 25)
                    if condicao_entrada and not em_pos:
                        em_pos = True
                        d_ent = df_back[col_data].iloc[i]
                        preco_entrada = df_back['Close'].iloc[i]
                        min_price_in_trade = df_back['Low'].iloc[i]
                        take_profit = preco_entrada * (1 + alvo_dec)

                # Coleta de resultados
                if em_pos:
                    res_atual = ((df_back['Close'].iloc[-1] / preco_entrada) - 1) * 100
                    q_max = ((min_price_in_trade / preco_entrada) - 1) * 100
                    ls_abertos_p.append({
                        'Ativo': ativo, 'Entrada': d_ent.strftime('%d/%m %H:%M') if tempo_padrao in ['15m', '60m'] else d_ent.strftime('%d/%m/%Y'),
                        'Dias': (df_back[col_data].iloc[-1] - d_ent).days, 'PM': f"R$ {preco_entrada:.2f}",
                        'Cotação Atual': f"R$ {df_back['Close'].iloc[-1]:.2f}",
                        'Prej. Máx': f"{q_max:.2f}%",
                        'Resultado Atual': f"+{res_atual:.2f}%" if res_atual > 0 else f"{res_atual:.2f}%"
                    })
                else:
                    tem_sinal = (df_full['IFR_Prev'].iloc[-1] < 25) and (df_full['IFR'].iloc[-1] >= 25)
                    if tem_sinal: ls_sinais_p.append({'Ativo': ativo, 'Preço Atual': f"R$ {df_full['Close'].iloc[-1]:.2f}"})

                if len(trades) > 0:
                    df_t = pd.DataFrame(trades)
                    ls_resumo_p.append({
                        'Ativo': ativo, 'Trades': len(df_t), 'Pior Queda': f"{df_t['Drawdown_Raw'].min():.2f}%", 'Lucro R$': df_t['Lucro (R$)'].sum()
                    })
            except: pass
            time.sleep(0.05)

        # --- EXIBIÇÃO DOS RESULTADOS (TEXTOS RESTAURADOS) ---
        s_text_p.empty()
        p_bar_p.empty()

        # 1. Oportunidades Hoje
        st.subheader(f"🚀 Oportunidades Hoje (Padrão | IFR {ifr_padrao})")
        if len(ls_sinais_p) > 0: 
            st.dataframe(pd.DataFrame(ls_sinais_p), use_container_width=True, hide_index=True)
        else: 
            st.info("Nenhum ativo deu sinal de entrada na última barra.")

        # 2. Operações em Andamento
        st.subheader("⏳ Operações em Andamento (Aguardando Alvo)")
        if len(ls_abertos_p) > 0:
            df_abertos = pd.DataFrame(ls_abertos_p).sort_values(by='Dias', ascending=False)
            st.dataframe(df_abertos.style.apply(colorir_lucro, axis=1), use_container_width=True, hide_index=True)
        else: 
            st.success("Sua carteira está limpa.")

        # 3. Top 10 Histórico
        st.subheader(f"📊 Top 10 Histórico ({tradutor_periodo_nome.get(periodo_padrao, periodo_padrao)})")
        if len(ls_resumo_p) > 0:
            df_resumo = pd.DataFrame(ls_resumo_p).sort_values(by='Lucro R$', ascending=False).head(10)
            df_resumo['Lucro R$'] = df_resumo['Lucro R$'].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(df_resumo, use_container_width=True, hide_index=True)
        else: 
            st.warning("Nenhuma operação finalizada.")

# ESPAÇO PARA AS PRÓXIMAS ABAS
with aba_pm: st.info("Pronto para receber o código da Aba 2.")
with aba_stop: st.info("Pronto para receber o código da Aba 3.")
with aba_individual: st.info("Pronto para receber o código da Aba 4.")
with aba_futuros: st.info("Pronto para receber o código da Aba 5.")
