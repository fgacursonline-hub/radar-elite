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
    '15m': Interval.in_15_minute, '60m': Interval.in_1_hour,
    '1d': Interval.in_daily, '1wk': Interval.in_weekly
}

tradutor_periodo_nome = {
    '6mo': '6 Meses', '1y': '1 Ano', '2y': '2 Anos', 
    '5y': '5 Anos', 'max': 'Máximo'
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
        val_str = str(row.get('Resultado Atual', row.get('Lucro Total (R$)', '0')))
        val = float(val_str.replace('R$', '').replace('%', '').replace('+', '').replace(',', '').strip())
        cor = 'lightgreen' if val > 0 else 'lightcoral' if val < 0 else 'white'
        return [f'color: {cor}'] * len(row)
    except: return [''] * len(row)

# ==========================================
# 2. MOTOR MATEMÁTICO: FIBONACCI ESTRUTURAL
# ==========================================
def identificar_fibonacci(df, lookback=120):
    df['MM200'] = ta.sma(df['Close'], length=200)
    df['Tendencia_Alta'] = df['Close'] > df['MM200']
    
    # --- FUNDO ESTRUTURAL (Âncora Base) ---
    # Mantemos o fundo absoluto da janela, pois inicia o movimento
    df['Fundo_Ref'] = df['Low'].rolling(window=lookback).min().shift(1)
    
    # --- TOPO ESTRUTURAL (Lógica de Price Action com Confirmação) ---
    # 1. Encontra a máxima no momento exato
    df['Rolling_Max'] = df['High'].rolling(window=lookback).max()
    df['Is_Novo_Topo'] = df['High'] == df['Rolling_Max']
    
    # 2. Guarda a mínima exata do candle que fez essa máxima
    df['Min_do_Topo'] = np.where(df['Is_Novo_Topo'], df['Low'], np.nan)
    df['Min_do_Topo'] = df['Min_do_Topo'].ffill()
    
    # 3. Guarda o valor da Máxima em si
    df['Valor_do_Topo'] = np.where(df['Is_Novo_Topo'], df['High'], np.nan)
    df['Valor_do_Topo'] = df['Valor_do_Topo'].ffill()
    
    # 4. A CONFIRMAÇÃO: Um topo só é válido se a sua mínima foi rompida posteriormente
    df['Rompeu_Minima'] = (df['Low'] < df['Min_do_Topo']) & (~df['Is_Novo_Topo'])
    
    # 5. Valida e crava o Topo Confirmado (shift 1 para operar no dia seguinte)
    df['Topo_Confirmado'] = np.where(df['Rompeu_Minima'], df['Valor_do_Topo'], np.nan)
    df['Topo_Ref'] = df['Topo_Confirmado'].ffill().shift(1)
    
    # --- CÁLCULO DAS RETRAÇÕES ---
    df['Range_Fibo'] = df['Topo_Ref'] - df['Fundo_Ref']
    df['Perna_Valida'] = (df['Topo_Ref'] / df['Fundo_Ref']) > 1.10
    
    df['Fibo_382'] = df['Topo_Ref'] - (df['Range_Fibo'] * 0.382)
    df['Fibo_500'] = df['Topo_Ref'] - (df['Range_Fibo'] * 0.500)
    df['Fibo_618'] = df['Topo_Ref'] - (df['Range_Fibo'] * 0.618)
    df['Fibo_786'] = df['Topo_Ref'] - (df['Range_Fibo'] * 0.786)
    
    # --- REJEIÇÃO NA ZONA DE OURO ---
    df['Corpo'] = abs(df['Open'] - df['Close'])
    df['Pavio_Inf'] = df[['Open', 'Close']].min(axis=1) - df['Low']
    df['Rejeicao'] = df['Pavio_Inf'] >= (df['Corpo'] * 1.5)
    
    df['Tocou_Zona'] = (df['Low'] <= df['Fibo_382']) & (df['Low'] >= df['Fibo_786'])
    df['Defesa_Institucional'] = df['Close'] >= df['Fibo_618']
    
    df['Is_Sinal_Fibo'] = df['Tendencia_Alta'] & df['Perna_Valida'] & df['Tocou_Zona'] & df['Rejeicao'] & df['Defesa_Institucional']
    
    return df

# ==========================================
# 3. INTERFACE E ABAS
# ==========================================
col_titulo, col_botao = st.columns([4, 1])
with col_titulo:
    st.title("📐 Rastreador de Fibonacci (Retração Confirmada)")
with col_botao:
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.link_button("📖 Ler Manual", "https://seusite.com/manual_fibo", use_container_width=True)

aba_radar, aba_individual = st.tabs(["📡 Radar Completo (Histórico + Hoje)", "🔬 Raio-X Individual"])

# ==========================================
# ABA 1: RADAR COMPLETO
# ==========================================
with aba_radar:
    with st.expander("⚙️ Configurações do Fibo e Backtest", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            lista_sel = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"], key="rad_f_lst")
            rad_capital = st.number_input("Capital por Trade (R$):", value=10000.0, step=1000.0, key="rad_f_cap")
        with c2:
            tempo_grafico = st.selectbox("Tempo Gráfico:", ['1d', '60m'], format_func=lambda x: {'60m': '60 min', '1d': 'Diário'}[x], key="rad_f_tmp")
            rad_periodo = st.selectbox("Período de Backtest:", ['6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=1, key="rad_f_per")
        with c3:
            tipo_alvo = st.selectbox("Tipo de Alvo:", ["Retorno ao Topo (100%)", "Risco Projetado (Ex: 2x)"], key="rad_f_tipo_alvo")
            alvo_val = st.number_input("Múltiplo de Risco (Se aplicável):", value=2.0, step=0.5, key="rad_f_alvo")
        with c4:
            rad_lookback = st.slider("Tamanho da Perna (Dias):", min_value=20, max_value=250, value=120, step=10, help="Quantidade de pregões para procurar o fundo e as máximas estruturais.")
            usar_stop_rad = st.checkbox("Usar Stop Loss", value=True, key="rad_f_chk")
            tipo_stop = st.selectbox("Tipo de Stop:", ["Técnico (Abaixo do Pavio)", "Abaixo dos 78.6% (Fibo)"], disabled=not usar_stop_rad, key="rad_f_tipo_stop")
            
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        btn_iniciar_radar = st.button("🚀 Escanear Retrações Institucionais", type="primary", use_container_width=True)

    if btn_iniciar_radar:
        ativos_analise = bdrs_elite if lista_sel == "BDRs Elite" else ibrx_selecao if lista_sel == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        intervalo_tv = tradutor_intervalo.get(tempo_grafico, Interval.in_daily)
        
        ls_armados, ls_abertos, ls_historico = [], [], []
        p_bar = st.progress(0); s_text = st.empty()

        for idx, ativo_raw in enumerate(ativos_analise):
            ativo = ativo_raw.replace('.SA', '')
            s_text.text(f"🔍 Medindo Fibo Estrutural em {ativo} ({idx+1}/{len(ativos_analise)})")
            p_bar.progress((idx + 1) / len(ativos_analise))

            try:
                df_full = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=5000)
                if df_full is None or len(df_full) < 250: continue
                df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                
                df_full = identificar_fibonacci(df_full, lookback=rad_lookback).dropna()

                if rad_periodo == '6mo': data_corte = df_full.index[-1] - pd.DateOffset(months=6)
                elif rad_periodo == 'max': data_corte = df_full.index[0]
                else: data_corte = df_full.index[-1] - pd.DateOffset(years=int(rad_periodo[0]))
                
                df_back = df_full[df_full.index >= data_corte].copy().reset_index()
                col_data = df_back.columns[0]

                em_pos = False
                preco_entrada, stop_loss, alvo, d_ent = 0.0, 0.0, 0.0, None
                topo_trade, fundo_trade = 0.0, 0.0
                lucro_total_ativo = 0.0
                vitorias, total_trades = 0, 0

                for i in range(1, len(df_back)):
                    atual, ontem = df_back.iloc[i], df_back.iloc[i-1]
                    
                    if em_pos:
                        if usar_stop_rad and atual['Low'] <= stop_loss:
                            lucro_total_ativo += rad_capital * ((stop_loss/preco_entrada)-1)
                            total_trades += 1; em_pos = False
                        elif atual['High'] >= alvo:
                            lucro_total_ativo += rad_capital * ((alvo/preco_entrada)-1)
                            total_trades += 1; vitorias += 1; em_pos = False
                        continue

                    if ontem['Is_Sinal_Fibo'] and atual['High'] > ontem['High'] and not em_pos:
                        em_pos = True
                        preco_entrada = max(ontem['High'] + 0.01, atual['Open'])
                        d_ent = atual[col_data]
                        topo_trade = ontem['Topo_Ref']
                        fundo_trade = ontem['Fundo_Ref']
                        
                        stop_loss = ontem['Low'] - 0.01 if "Pavio" in tipo_stop else ontem['Fibo_786'] - 0.01
                        
                        if "Topo" in tipo_alvo: alvo = ontem['Topo_Ref']
                        else: alvo = preco_entrada + ((preco_entrada - stop_loss) * alvo_val)

                if total_trades > 0:
                    ls_historico.append({
                        'Ativo': ativo, 'Operações Fechadas': total_trades,
                        'Taxa de Acerto': f"{(vitorias/total_trades)*100:.1f}%",
                        'Lucro Total (R$)': lucro_total_ativo
                    })

                if em_pos:
                    cot_atual = df_back['Close'].iloc[-1]
                    res_pct = (cot_atual / preco_entrada) - 1
                    ls_abertos.append({
                        'Ativo': ativo, 'Entrada': d_ent.strftime('%d/%m/%Y'), 'Dias': (df_back[col_data].iloc[-1] - d_ent).days,
                        'Fundo (Fibo)': f"R$ {fundo_trade:.2f}", 'Topo Confirmado': f"R$ {topo_trade:.2f}",
                        'PM': f"R$ {preco_entrada:.2f}", 'Cotação Atual': f"R$ {cot_atual:.2f}", 
                        'Alvo Programado': f"R$ {alvo:.2f}", 'Resultado Atual': f"+{res_pct*100:.2f}%" if res_pct > 0 else f"{res_pct*100:.2f}%"
                    })
                else:
                    atual = df_back.iloc[-1]
                    if atual['Is_Sinal_Fibo']:
                        gatilho = atual['High'] + 0.01
                        alvo_proj = atual['Topo_Ref'] if "Topo" in tipo_alvo else gatilho + ((gatilho - (atual['Low'] - 0.01)) * alvo_val)
                        ls_armados.append({
                            'Ativo': ativo, 'Sinal': 'Rejeição em 61.8% 🎯', 'Gatilho (Start)': f"R$ {gatilho:.2f}", 
                            'Alvo': f"R$ {alvo_proj:.2f}", 'Status': "Aguardando Rompimento"
                        })

            except Exception as e: pass
            time.sleep(0.01)

        s_text.empty(); p_bar.empty()
        st.divider()

        st.subheader(f"🏆 TOP 20 Histórico: Retrações ({tradutor_periodo_nome[rad_periodo]})")
        if ls_historico:
            df_hist = pd.DataFrame(ls_historico).sort_values(by='Lucro Total (R$)', ascending=False).head(20)
            df_hist['Lucro Total (R$)'] = df_hist['Lucro Total (R$)'].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(df_hist.style.apply(colorir_lucro, axis=1), use_container_width=True, hide_index=True)
        else: st.info("Sem dados históricos validados neste período.")

        st.subheader("🚀 Oportunidades Hoje na Golden Zone")
        if ls_armados: st.dataframe(pd.DataFrame(ls_armados), use_container_width=True, hide_index=True)
        else: st.info("Nenhum ativo defendeu a zona de Fibonacci hoje.")

        st.subheader("⏳ Operações Fibo em Andamento")
        if ls_abertos: 
            df_abertos = pd.DataFrame(ls_abertos).sort_values(by='Dias', ascending=False)
            st.dataframe(df_abertos.style.apply(colorir_lucro, axis=1), use_container_width=True, hide_index=True)
        else: st.info("Sem operações abertas para este setup no momento.")

# ==========================================
# ABA 2: RAIO-X INDIVIDUAL (BACKTEST DETALHADO)
# ==========================================
with aba_individual:
    st.subheader("🔬 Raio-X Individual: Laboratório de Fibonacci Estrutural")
    
    cr1, cr2, cr3, cr4 = st.columns(4)
    with cr1:
        rx_ativo = st.text_input("Ativo Base:", value="PRIO3", key="rx_f_ativo").upper().replace('.SA', '')
        rx_capital = st.number_input("Capital Operado (R$):", value=10000.0, step=1000.0, key="rx_f_cap")
    with cr2:
        rx_periodo = st.selectbox("Período:", options=['6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=1, key="rx_f_per")
        rx_tempo = st.selectbox("Tempo Gráfico:", ['60m', '1d', '1wk'], index=1, format_func=lambda x: {'60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="rx_f_tmp")
    with cr3:
        rx_tipo_alvo = st.selectbox("Tipo de Alvo:", ["Retorno ao Topo (100%)", "Risco Projetado (Ex: 2x)"], key="rx_f_tipo_alvo")
        rx_alvo_val = st.number_input("Múltiplo de Risco:", value=2.0, step=0.5, key="rx_f_alvo")
    with cr4:
        rx_lookback = st.slider("Tamanho da Perna (Dias):", min_value=20, max_value=250, value=120, step=10, key="rx_lookback")
        rx_usar_stop = st.checkbox("Usar Stop Loss", value=True, key="rx_f_chk")
        rx_tipo_stop = st.selectbox("Tipo de Stop:", ["Técnico (Abaixo do Pavio)", "Abaixo dos 78.6% (Fibo)"], disabled=not rx_usar_stop, key="rx_f_tipo_stop")

    btn_raiox = st.button("🔍 Rodar Backtest Fibo", type="primary", use_container_width=True, key="rx_f_btn")

    if btn_raiox:
        if not rx_ativo: st.error("Digite o código de um ativo.")
        else:
            with st.spinner(f'A mapear estrutura gráfica e retrações em {rx_ativo}...'):
                try:
                    df_full = tv.get_hist(symbol=rx_ativo, exchange='BMFBOVESPA', interval=tradutor_intervalo.get(rx_tempo, Interval.in_daily), n_bars=5000)
                    df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                    
                    df_full = identificar_fibonacci(df_full, lookback=rx_lookback).dropna()

                    if rx_periodo == '6mo': data_corte = df_full.index[-1] - pd.DateOffset(months=6)
                    elif rx_periodo == 'max': data_corte = df_full.index[0]
                    else: data_corte = df_full.index[-1] - pd.DateOffset(years=int(rx_periodo[0]))
                    
                    df_back = df_full[df_full.index >= data_corte].copy().reset_index()
                    col_data = df_back.columns[0]

                    trades, em_pos = [], False
                    preco_entrada, stop_loss, alvo, d_ent = 0.0, 0.0, 0.0, None
                    topo_trade, fundo_trade = 0.0, 0.0
                    vitorias, derrotas, extremo_trade = 0, 0, 0.0 

                    for i in range(1, len(df_back)):
                        atual, ontem = df_back.iloc[i], df_back.iloc[i-1]

                        if em_pos:
                            extremo_trade = min(extremo_trade, atual['Low'])
                            queda_max = (extremo_trade / preco_entrada) - 1
                            if rx_usar_stop and atual['Low'] <= stop_loss:
                                trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': atual[col_data].strftime('%d/%m/%Y'), 'Fundo (Fibo)': f"R$ {fundo_trade:.2f}", 'Topo Confirmado': f"R$ {topo_trade:.2f}", 'Duração': (atual[col_data] - d_ent).days, 'Lucro (R$)': rx_capital * ((stop_loss/preco_entrada)-1), 'Queda Máx': queda_max, 'Situação': 'Stop ❌'})
                                derrotas += 1; em_pos = False
                            elif atual['High'] >= alvo:
                                trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': atual[col_data].strftime('%d/%m/%Y'), 'Fundo (Fibo)': f"R$ {fundo_trade:.2f}", 'Topo Confirmado': f"R$ {topo_trade:.2f}", 'Duração': (atual[col_data] - d_ent).days, 'Lucro (R$)': rx_capital * ((alvo/preco_entrada)-1), 'Queda Máx': queda_max, 'Situação': 'Gain ✅'})
                                vitorias += 1; em_pos = False
                            continue

                        if ontem['Is_Sinal_Fibo'] and atual['High'] > ontem['High'] and not em_pos:
                            em_pos, preco_entrada, d_ent = True, max(ontem['High'] + 0.01, atual['Open']), atual[col_data]
                            extremo_trade = atual['Low']
                            topo_trade = ontem['Topo_Ref']
                            fundo_trade = ontem['Fundo_Ref']
                            
                            stop_loss = ontem['Low'] - 0.01 if "Pavio" in rx_tipo_stop else ontem['Fibo_786'] - 0.01
                            if "Topo" in rx_tipo_alvo: alvo = ontem['Topo_Ref']
                            else: alvo = preco_entrada + ((preco_entrada - stop_loss) * rx_alvo_val)
                                    
                    st.divider()
                    
                    if em_pos:
                        cot_atual = df_back['Close'].iloc[-1]
                        res_pct = (cot_atual / preco_entrada) - 1
                        queda_max_aberta = (extremo_trade / preco_entrada) - 1
                        st.warning(f"""
                        **⏳ {rx_ativo}: Em Operação**
                        * **Entrada:** {d_ent.strftime('%d/%m/%Y')} | **Dias na Operação:** {(df_back[col_data].iloc[-1] - d_ent).days}
                        * **Fundo (Fibo):** R$ {fundo_trade:.2f} | **Topo Confirmado:** R$ {topo_trade:.2f}
                        * **PM:** R$ {preco_entrada:.2f} | **Cotação Atual:** R$ {cot_atual:.2f} | **Alvo Programado:** R$ {alvo:.2f}
                        * **Queda Máx:** {queda_max_aberta*100:.2f}% | **Resultado Atual:** {res_pct*100:.2f}%
                        """)
                    else:
                        st.success(f"✅ **{rx_ativo}: Aguardando Novo Sinal de Retração Estrutural**")
                    
                    st.markdown(f"### 📊 Resultado Consolidado: {rx_ativo}")
                    if len(trades) > 0:
                        df_t = pd.DataFrame(trades)
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("Lucro Total", f"R$ {df_t['Lucro (R$)'].sum():,.2f}")
                        m2.metric("Taxa de Acerto", f"{(vitorias / len(df_t)) * 100:.1f}%")
                        m3.metric("Operações Fechadas", len(df_t))
                        m4.metric("Pior Queda", f"{df_t['Queda Máx'].min()*100:.2f}%")

                        df_t['Queda Máx'] = df_t['Queda Máx'].apply(lambda x: f"{x*100:.2f}%")
                        st.dataframe(df_t, use_container_width=True, hide_index=True)
                    else:
                        st.info(f"Nenhum pullback estrutural defendido no período.")
                except Exception as e: st.error(f"Erro: {e}")
