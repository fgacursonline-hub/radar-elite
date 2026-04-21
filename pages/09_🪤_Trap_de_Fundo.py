import streamlit as st
from tvDatafeed import TvDatafeed, Interval
import pandas as pd
import numpy as np
import pandas_ta as ta
import time
import warnings
from datetime import datetime

warnings.filterwarnings('ignore')

# ==========================================
# 1. SEGURANÇA E CONEXÃO
# ==========================================
if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, inicie sessão na página inicial (Home) com o seu Email.")
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

tradutor_periodo_nome = {
    '1mo': '1 Mês', '3mo': '3 Meses', '6mo': '6 Meses',
    '1y': '1 Ano', '2y': '2 Anos', '5y': '5 Anos',
    'max': 'Máximo'
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
    try:
        val = float(row['Resultado Atual'].replace('%', '').replace('+', ''))
        cor = 'lightgreen' if val > 0 else 'lightcoral' if val < 0 else 'white'
        return [f'color: {cor}'] * len(row)
    except:
        return [''] * len(row)

# ==========================================
# 3. INTERFACE E ABAS
# ==========================================
col_titulo, col_botao = st.columns([4, 1])
with col_titulo:
    st.title("🪤 Trap de Fundo (Estocástico)")
with col_botao:
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.link_button("📖 Ler Manual Quant", "https://seusite.com/manual_trap", use_container_width=True)

aba_radar, aba_individual = st.tabs(["📡 Radar de Armadilhas", "🔬 Raio-X Individual"])

# ==========================================
# ABA 1: RADAR DE ARMADILHAS
# ==========================================
with aba_radar:
    st.subheader("Radar de Falsos Rompimentos")
    st.markdown("Procura ativos com o Estocástico sobrevendido onde os institucionais estoparam a massa rompendo um suporte recente, mas o *candle* rejeitou a queda, armando uma armadilha para os vendidos.")
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        lista_sel = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"], key="rad_lst_trap")
        tempo_grafico = st.selectbox("Tempo Gráfico:", ['1d', '60m'], index=0, format_func=lambda x: {'60m': '60 min', '1d': 'Diário'}[x], key="rad_tmp_trap")
    with c2:
        st.markdown("**Configuração do Alvo**")
        alvo_risco = st.number_input("Risco/Retorno (Ex: 2.0 = Alvo 2x o Stop):", value=2.0, step=0.5, key="rad_alvo_trap")
    with c3:
        st.markdown("**Filtro Estocástico**")
        estoc_limite = st.number_input("Limite de Sobrevenda:", value=25, max_value=40, step=5, key="rad_estoc_trap", help="Geralmente 20 ou 25.")
    with c4:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        btn_iniciar_radar = st.button("🚀 Iniciar Varredura de Traps", type="primary", use_container_width=True)

    if btn_iniciar_radar:
        ativos_analise = bdrs_elite if lista_sel == "BDRs Elite" else ibrx_selecao if lista_sel == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        intervalo_tv = tradutor_intervalo.get(tempo_grafico, Interval.in_daily)
        
        ls_armados, ls_abertos = [], []
        p_bar = st.progress(0)
        s_text = st.empty()

        for idx, ativo_raw in enumerate(ativos_analise):
            ativo = ativo_raw.replace('.SA', '')
            s_text.text(f"🔍 Procurando armadilhas em {ativo} ({idx+1}/{len(ativos_analise)})")
            p_bar.progress((idx + 1) / len(ativos_analise))

            try:
                df_full = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=300)
                if df_full is None or len(df_full) < 50: continue
                df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                
                # Indicadores do Trap
                stoch = ta.stoch(df_full['High'], df_full['Low'], df_full['Close'], k=8, d=3, smooth_k=3)
                if stoch is not None:
                    df_full['STOCH_K'] = stoch['STOCHk_8_3_3']
                else: continue
                
                # Suporte Recente (Mínima dos últimos 8 dias, shift(1) para evitar look-ahead)
                df_full['Min_8'] = df_full['Low'].rolling(window=8).min().shift(1)
                
                # Identifica os Candles de Trap (Perdeu o fundo, mas fechou acima da metade do candle)
                df_full['Meio_Candle'] = df_full['Low'] + ((df_full['High'] - df_full['Low']) * 0.5)
                df_full['Is_Trap'] = (df_full['Low'] < df_full['Min_8']) & (df_full['Close'] > df_full['Meio_Candle']) & (df_full['STOCH_K'] < estoc_limite)
                
                df_full = df_full.dropna()
                df_back = df_full.reset_index()
                col_data = df_back.columns[0]

                em_pos, preco_entrada, stop_loss, alvo, min_price_in_trade, d_ent = False, 0.0, 0.0, 0.0, 0.0, None

                # SIMULADOR (Para encontrar operações em andamento)
                for i in range(1, len(df_back)):
                    atual, ontem = df_back.iloc[i], df_back.iloc[i-1]
                    
                    if em_pos:
                        min_price_in_trade = min(min_price_in_trade, atual['Low'])
                        if atual['Low'] <= stop_loss: em_pos = False
                        elif atual['High'] >= alvo: em_pos = False
                        continue

                    # Gatilho de Entrada: Ontem armou o Trap e Hoje rompeu a máxima de ontem
                    if ontem['Is_Trap'] and atual['High'] > ontem['High'] and not em_pos:
                        em_pos = True
                        preco_entrada = max(ontem['High'] + 0.01, atual['Open']) # Compra no rompimento ou na abertura se houver gap
                        min_price_in_trade = atual['Low']
                        d_ent = atual[col_data]
                        
                        # Stop e Alvo da Estratégia de Elite
                        stop_loss = ontem['Low'] - 0.01
                        risco = preco_entrada - stop_loss
                        alvo = preco_entrada + (risco * alvo_risco)

                # FORA DO LOOP: Avalia Hoje
                if em_pos:
                    cotacao_atual = df_back['Close'].iloc[-1]
                    res_pct = (cotacao_atual / preco_entrada) - 1
                    ls_abertos.append({
                        'Ativo': ativo, 'Entrada': d_ent.strftime('%d/%m/%Y'), 'Dias': (df_back[col_data].iloc[-1] - d_ent).days,
                        'PM (Entrada)': f"R$ {preco_entrada:.2f}", 'Cotação Atual': f"R$ {cotacao_atual:.2f}",
                        'Queda Máx': f"{((min_price_in_trade / preco_entrada) - 1)*100:.2f}%",
                        'Alvo Programado': f"R$ {alvo:.2f}", 'Resultado Atual': f"+{res_pct*100:.2f}%" if res_pct > 0 else f"{res_pct*100:.2f}%"
                    })
                else:
                    # Não estamos posicionados. O ativo armou a armadilha HOJE? (Candle fechado/fechando agora)
                    atual = df_back.iloc[-1]
                    if atual['Is_Trap']:
                        gatilho = atual['High'] + 0.01
                        stop = atual['Low'] - 0.01
                        risco = gatilho - stop
                        
                        ls_armados.append({
                            'Ativo': ativo, 'Sinal': 'Trap de Fundo 🪤', 'Gatilho Compra': f"R$ {gatilho:.2f}",
                            'Stop': f"R$ {stop:.2f}", 'Alvo Projetado': f"R$ {gatilho + (risco * alvo_risco):.2f}"
                        })

            except Exception as e: pass
            time.sleep(0.01)

        s_text.empty(); p_bar.empty()

        st.subheader(f"🚀 Oportunidades Hoje (Aguardando Rompimento)")
        if ls_armados: 
            st.dataframe(pd.DataFrame(ls_armados), use_container_width=True, hide_index=True)
            st.info("💡 Coloque a ordem de Start (Compra) no Gatilho apontado acima. A entrada só acontece se a máxima for rompida amanhã.")
        else: 
            st.info("Nenhuma armadilha armada no pregão de hoje.")

        st.subheader("⏳ Operações em Andamento (Aguardando Alvo)")
        if ls_abertos:
            df_abertos = pd.DataFrame(ls_abertos).sort_values(by='Dias', ascending=False)
            st.dataframe(df_abertos.style.apply(colorir_lucro, axis=1), use_container_width=True, hide_index=True)
        else: st.info("A carteira de Falsos Rompimentos está vazia no momento.")

# ==========================================
# ABA 2: RAIO-X INDIVIDUAL (BACKTEST)
# ==========================================
with aba_individual:
    st.subheader("🔬 Raio-X Individual: Laboratório de Traps")
    
    cr1, cr2, cr3, cr4 = st.columns(4)
    with cr1:
        rx_ativo = st.text_input("Ativo Base:", value="MGLU3", key="rx_trap_ativo").upper().replace('.SA', '')
        rx_periodo = st.selectbox("Período de Estudo:", options=['6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=1, key="rx_trap_per")
    with cr2:
        rx_tempo = st.selectbox("Tempo Gráfico:", ['60m', '1d', '1wk'], index=1, format_func=lambda x: {'60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="rx_trap_tmp")
        rx_capital = st.number_input("Capital Operado (R$):", value=10000.0, step=1000.0, key="rx_trap_cap")
    with cr3:
        alvo_risco_rx = st.number_input("Risco/Retorno (Ex: 2.0):", value=2.0, step=0.5, key="rx_trap_alvo")
    with cr4:
        estoc_limite_rx = st.number_input("Limite de Sobrevenda:", value=25, max_value=40, step=5, key="rx_trap_estoc")

    btn_raiox = st.button("🔍 Rodar Backtest da Armadilha", type="primary", use_container_width=True, key="rx_trap_btn")

    if btn_raiox:
        if not rx_ativo: st.error("Digite o código de um ativo.")
        else:
            with st.spinner(f'A mapear o fundo do poço de {rx_ativo}...'):
                try:
                    df_full = tv.get_hist(symbol=rx_ativo, exchange='BMFBOVESPA', interval=tradutor_intervalo.get(rx_tempo, Interval.in_daily), n_bars=5000)
                    if df_full is None or len(df_full) < 100: st.error("Dados insuficientes.")
                    else:
                        df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                        
                        stoch = ta.stoch(df_full['High'], df_full['Low'], df_full['Close'], k=8, d=3, smooth_k=3)
                        df_full['STOCH_K'] = stoch['STOCHk_8_3_3']
                        df_full['Min_8'] = df_full['Low'].rolling(window=8).min().shift(1)
                        df_full['Meio_Candle'] = df_full['Low'] + ((df_full['High'] - df_full['Low']) * 0.5)
                        df_full['Is_Trap'] = (df_full['Low'] < df_full['Min_8']) & (df_full['Close'] > df_full['Meio_Candle']) & (df_full['STOCH_K'] < estoc_limite_rx)
                        df_full = df_full.dropna()

                        data_corte = df_full.index[-1] - pd.DateOffset(months=6) if rx_periodo == '6mo' else df_full.index[-1] - pd.DateOffset(years=int(rx_periodo[0])) if rx_periodo != 'max' else df_full.index[0]
                        df_back = df_full[df_full.index >= data_corte].copy().reset_index()
                        col_data = df_back.columns[0]

                        trades, em_pos = [], False
                        preco_entrada, stop_loss, alvo, min_price_in_trade, d_ent, vitorias, derrotas = 0.0, 0.0, 0.0, 0.0, None, 0, 0

                        for i in range(1, len(df_back)):
                            atual, ontem = df_back.iloc[i], df_back.iloc[i-1]

                            if em_pos:
                                min_price_in_trade = min(min_price_in_trade, atual['Low'])
                                if atual['Low'] <= stop_loss:
                                    d_sai = atual[col_data]
                                    lucro = rx_capital * ((stop_loss / preco_entrada) - 1)
                                    trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': d_sai.strftime('%d/%m/%Y'), 'Duração': (d_sai - d_ent).days, 'Lucro (R$)': lucro, 'Queda Máx': (min_price_in_trade / preco_entrada) - 1, 'Situação': 'Stop Acionado ❌'})
                                    derrotas += 1; em_pos = False
                                elif atual['High'] >= alvo:
                                    d_sai = atual[col_data]
                                    lucro = rx_capital * ((alvo / preco_entrada) - 1)
                                    trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': d_sai.strftime('%d/%m/%Y'), 'Duração': (d_sai - d_ent).days, 'Lucro (R$)': lucro, 'Queda Máx': (min_price_in_trade / preco_entrada) - 1, 'Situação': 'Gain Atingido 🎯'})
                                    vitorias += 1; em_pos = False
                                continue

                            if ontem['Is_Trap'] and atual['High'] > ontem['High'] and not em_pos:
                                em_pos, preco_entrada, min_price_in_trade, d_ent = True, max(ontem['High'] + 0.01, atual['Open']), atual['Low'], atual[col_data]
                                stop_loss = ontem['Low'] - 0.01
                                alvo = preco_entrada + ((preco_entrada - stop_loss) * alvo_risco_rx)

                        st.divider()
                        
                        if em_pos:
                            cotacao_atual = df_back['Close'].iloc[-1]
                            res_pct = (cotacao_atual / preco_entrada) - 1
                            st.warning(f"⏳ **{rx_ativo}: Em Operação** | Entrada: {d_ent.strftime('%d/%m/%Y')} | PM: R$ {preco_entrada:.2f} | Atual: {res_pct*100:.2f}%")
                        else:
                            st.success(f"✅ **{rx_ativo}: Aguardando Novo Sinal**")
                            
                        st.markdown(f"### 📊 Resultado Consolidado: {rx_ativo}")
                        if len(trades) > 0:
                            df_t = pd.DataFrame(trades)
                            m1, m2, m3, m4 = st.columns(4)
                            m1.metric("Lucro Total", f"R$ {df_t['Lucro (R$)'].sum():,.2f}")
                            m2.metric("Taxa de Acerto", f"{(vitorias / len(df_t)) * 100:.1f}%")
                            m3.metric("Operações Fechadas", len(df_t))
                            m4.metric("Payoff (Risco/Retorno)", f"{alvo_risco_rx:.1f}")

                            df_t['Queda Máx'] = df_t['Queda Máx'].apply(lambda x: f"{x*100:.2f}%")
                            st.dataframe(df_t, use_container_width=True, hide_index=True)
                        else:
                            st.info("Nenhum falso rompimento ativado no período.")
                except Exception as e: st.error(f"Erro: {e}")
