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
# 2. MOTOR MATEMÁTICO: FURA-TETO / CHÃO
# ==========================================
def identificar_fura_teto_chao(df, periodo_teto=1):
    df['MME8'] = ta.ema(df['Close'], length=8)
    
    # Agora a linha de Teto/Chão respeita os N períodos (linha "escadinha" branca do Profit)
    df['Teto'] = df['High'].rolling(window=periodo_teto).max().shift(1)
    df['Chao'] = df['Low'].rolling(window=periodo_teto).min().shift(1)
    
    return df

# ==========================================
# 3. INTERFACE E ABAS
# ==========================================
col_titulo, col_botao = st.columns([4, 1])
with col_titulo:
    st.title("🚀 Fura-Teto & Fura-Chão (Momentum)")
with col_botao:
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.link_button("📖 Ler Manual", "https://seusite.com/manual_fura_teto", use_container_width=True)

aba_radar, aba_individual = st.tabs(["📡 Radar Completo (Histórico + Hoje)", "🔬 Raio-X Individual"])

# ==========================================
# ABA 1: RADAR COMPLETO
# ==========================================
with aba_radar:
    with st.expander("⚙️ Configurações do Setup e Backtest", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            lista_sel = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"], key="rad_ft_lst")
            direcao_sel = st.selectbox("Direção:", ["Apenas Fura-Teto (Compra)", "Apenas Fura-Chão (Venda)", "Ambos (Compra e Venda)"], key="rad_ft_dir")
            rad_capital = st.number_input("Capital por Trade (R$):", value=10000.0, step=1000.0, key="rad_ft_cap")
        with c2:
            tempo_grafico = st.selectbox("Tempo Gráfico:", ['1d', '1wk', '60m'], format_func=lambda x: {'60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="rad_ft_tmp")
            rad_periodo = st.selectbox("Período de Backtest:", ['6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=1, key="rad_ft_per")
        with c3:
            rad_ft_periodo = st.number_input("Período do Teto/Chão (Profit):", value=14, step=1, min_value=1, help="Coloque o mesmo número do indicador Fura-Teto do Profit.", key="rad_ft_periodo_in")
            tipo_alvo = st.selectbox("Tipo de Alvo:", ["Risco Projetado (Ex: 2x)", "Alvo Fixo (%)"], key="rad_ft_tipo_alvo")
            alvo_val = st.number_input("Múltiplo ou %:", value=2.0, step=0.5, key="rad_ft_alvo")
        with c4:
            usar_filtro = st.checkbox("Filtro MME8", value=True, help="Só compra se estiver acima da Média de 8.", key="rad_ft_filtro")
            rad_stop_loss = st.selectbox("Stop Loss:", ["Mínima do Candle Sinal", "Fixo (%)"], key="rad_ft_stop")
            
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        btn_iniciar_radar = st.button("🚀 Iniciar Varredura de Momentum", type="primary", use_container_width=True)

    if btn_iniciar_radar:
        ativos_analise = bdrs_elite if lista_sel == "BDRs Elite" else ibrx_selecao if lista_sel == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        intervalo_tv = tradutor_intervalo.get(tempo_grafico, Interval.in_daily)
        
        ls_armados, ls_abertos, ls_historico = [], [], []
        p_bar = st.progress(0); s_text = st.empty()

        for idx, ativo_raw in enumerate(ativos_analise):
            ativo = ativo_raw.replace('.SA', '')
            s_text.text(f"🔍 Procurando Rompimentos em {ativo} ({idx+1}/{len(ativos_analise)})")
            p_bar.progress((idx + 1) / len(ativos_analise))

            try:
                df_full = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=5000)
                if df_full is None or len(df_full) < 50: continue
                df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                
                df_full = identificar_fura_teto_chao(df_full, periodo_teto=rad_ft_periodo).dropna()

                if rad_periodo == '6mo': data_corte = df_full.index[-1] - pd.DateOffset(months=6)
                elif rad_periodo == 'max': data_corte = df_full.index[0]
                else: data_corte = df_full.index[-1] - pd.DateOffset(years=int(rad_periodo[0]))
                
                df_back = df_full[df_full.index >= data_corte].copy().reset_index()
                col_data = df_back.columns[0]

                em_pos = False
                preco_entrada, stop_loss, alvo, d_ent, direcao_trade = 0.0, 0.0, 0.0, None, 0
                lucro_total_ativo = 0.0
                vitorias, total_trades = 0, 0

                for i in range(1, len(df_back)):
                    atual, ontem = df_back.iloc[i], df_back.iloc[i-1]
                    
                    if em_pos:
                        if direcao_trade == 1: 
                            if atual['Low'] <= stop_loss:
                                lucro_total_ativo += rad_capital * ((stop_loss/preco_entrada)-1)
                                total_trades += 1; em_pos = False
                            elif atual['High'] >= alvo:
                                lucro_total_ativo += rad_capital * ((alvo/preco_entrada)-1)
                                total_trades += 1; vitorias += 1; em_pos = False
                        else: 
                            if atual['High'] >= stop_loss:
                                lucro_total_ativo += rad_capital * ((preco_entrada-stop_loss)/preco_entrada)
                                total_trades += 1; em_pos = False
                            elif atual['Low'] <= alvo:
                                lucro_total_ativo += rad_capital * ((preco_entrada-alvo)/preco_entrada)
                                total_trades += 1; vitorias += 1; em_pos = False
                        continue

                    # Gatilho com o período configurado pelo usuário
                    gatilho_compra = atual['Teto'] + 0.01
                    gatilho_venda = atual['Chao'] - 0.01
                    pode_comprar = ontem['Close'] > ontem['MME8'] if usar_filtro else True
                    pode_vender = ontem['Close'] < ontem['MME8'] if usar_filtro else True

                    if not em_pos:
                        if ("Compra" in direcao_sel or "Ambos" in direcao_sel) and pode_comprar:
                            if atual['High'] >= gatilho_compra:
                                em_pos, direcao_trade = True, 1
                                preco_entrada = max(gatilho_compra, atual['Open'])
                                d_ent = atual[col_data]
                                stop_loss = ontem['Low'] - 0.01 if "Mínima" in rad_stop_loss else preco_entrada * 0.95
                                alvo = preco_entrada + ((preco_entrada - stop_loss) * alvo_val) if "Risco" in tipo_alvo else preco_entrada * (1 + (alvo_val/100))
                                
                                if atual['Low'] <= stop_loss:
                                    lucro_total_ativo += rad_capital * ((stop_loss/preco_entrada)-1)
                                    total_trades += 1; em_pos = False
                                    continue
                                elif atual['High'] >= alvo:
                                    lucro_total_ativo += rad_capital * ((alvo/preco_entrada)-1)
                                    total_trades += 1; vitorias += 1; em_pos = False
                                    continue

                        if ("Venda" in direcao_sel or "Ambos" in direcao_sel) and not em_pos and pode_vender:
                            if atual['Low'] <= gatilho_venda:
                                em_pos, direcao_trade = True, -1
                                preco_entrada = min(gatilho_venda, atual['Open'])
                                d_ent = atual[col_data]
                                stop_loss = ontem['High'] + 0.01 if "Mínima" in rad_stop_loss else preco_entrada * 1.05
                                alvo = preco_entrada - ((stop_loss - preco_entrada) * alvo_val) if "Risco" in tipo_alvo else preco_entrada * (1 - (alvo_val/100))
                                
                                if atual['High'] >= stop_loss:
                                    lucro_total_ativo += rad_capital * ((preco_entrada-stop_loss)/preco_entrada)
                                    total_trades += 1; em_pos = False
                                    continue
                                elif atual['Low'] <= alvo:
                                    lucro_total_ativo += rad_capital * ((preco_entrada-alvo)/preco_entrada)
                                    total_trades += 1; vitorias += 1; em_pos = False
                                    continue

                if total_trades > 0:
                    ls_historico.append({
                        'Ativo': ativo, 'Operações Fechadas': total_trades,
                        'Taxa de Acerto': f"{(vitorias/total_trades)*100:.1f}%",
                        'Lucro Total (R$)': lucro_total_ativo
                    })

                if em_pos:
                    cot_atual = df_back['Close'].iloc[-1]
                    res_pct = (cot_atual / preco_entrada) - 1 if direcao_trade == 1 else (preco_entrada - cot_atual) / preco_entrada
                    ls_abertos.append({
                        'Ativo': ativo, 'Direção': '📈 Compra' if direcao_trade == 1 else '📉 Venda',
                        'Entrada': d_ent.strftime('%d/%m/%Y'), 'Dias': (df_back[col_data].iloc[-1] - d_ent).days,
                        'PM': f"R$ {preco_entrada:.2f}", 'Cotação Atual': f"R$ {cot_atual:.2f}", 
                        'Alvo': f"R$ {alvo:.2f}", 'Resultado Atual': f"+{res_pct*100:.2f}%" if res_pct > 0 else f"{res_pct*100:.2f}%"
                    })
                else:
                    atual = df_back.iloc[-1]
                    ontem = df_back.iloc[-2]
                    pode_comprar = ontem['Close'] > ontem['MME8'] if usar_filtro else True
                    pode_vender = ontem['Close'] < ontem['MME8'] if usar_filtro else True

                    if ("Compra" in direcao_sel or "Ambos" in direcao_sel) and pode_comprar:
                        gatilho = atual['Teto'] + 0.01
                        alvo_proj = gatilho + ((gatilho - (atual['Low'] - 0.01)) * alvo_val) if "Risco" in tipo_alvo else gatilho * (1 + (alvo_val/100))
                        ls_armados.append({
                            'Ativo': ativo, 'Sinal': f'🚀 Teto de {rad_ft_periodo}d Armado', 'Gatilho (Start)': f"R$ {gatilho:.2f}", 
                            'Alvo Projetado': f"R$ {alvo_proj:.2f}", 'Status': "Aguardando Pregão de Amanhã"
                        })
                    if ("Venda" in direcao_sel or "Ambos" in direcao_sel) and pode_vender:
                        gatilho = atual['Chao'] - 0.01
                        alvo_proj = gatilho - (((atual['High'] + 0.01) - gatilho) * alvo_val) if "Risco" in tipo_alvo else gatilho * (1 - (alvo_val/100))
                        ls_armados.append({
                            'Ativo': ativo, 'Sinal': f'🔻 Chão de {rad_ft_periodo}d Armado', 'Gatilho (Start)': f"R$ {gatilho:.2f}", 
                            'Alvo Projetado': f"R$ {alvo_proj:.2f}", 'Status': "Aguardando Pregão de Amanhã"
                        })

            except Exception as e: pass
            time.sleep(0.01)

        s_text.empty(); p_bar.empty()
        st.divider()

        st.subheader(f"🏆 TOP 20 Histórico: Inércia ({tradutor_periodo_nome[rad_periodo]})")
        if ls_historico:
            df_hist = pd.DataFrame(ls_historico).sort_values(by='Lucro Total (R$)', ascending=False).head(20)
            df_hist['Lucro Total (R$)'] = df_hist['Lucro Total (R$)'].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(df_hist.style.apply(colorir_lucro, axis=1), use_container_width=True, hide_index=True)
        else: st.info("Sem dados históricos validados neste período.")

        st.subheader("🚀 Oportunidades de Rompimento Hoje")
        if ls_armados: st.dataframe(pd.DataFrame(ls_armados), use_container_width=True, hide_index=True)
        else: st.info("Nenhum ativo alinhado para rompimento no pregão de hoje.")

        st.subheader("⏳ Operações em Andamento")
        if ls_abertos: 
            df_abertos = pd.DataFrame(ls_abertos).sort_values(by='Dias', ascending=False)
            st.dataframe(df_abertos.style.apply(colorir_lucro, axis=1), use_container_width=True, hide_index=True)
        else: st.info("Sem operações abertas para este setup no momento.")

# ==========================================
# ABA 2: RAIO-X INDIVIDUAL (BACKTEST DETALHADO)
# ==========================================
with aba_individual:
    st.subheader("🔬 Raio-X Individual: Laboratório de Inércia")
    
    cr1, cr2, cr3, cr4 = st.columns(4)
    with cr1:
        rx_ativo = st.text_input("Ativo Base:", value="PRIO3", key="rx_ft_ativo").upper().replace('.SA', '')
        rx_direcao = st.selectbox("Direção:", ["Apenas Fura-Teto (Compra)", "Apenas Fura-Chão (Venda)", "Ambos"], key="rx_ft_dir")
        rx_capital = st.number_input("Capital Operado (R$):", value=10000.0, step=1000.0, key="rx_ft_cap")
    with cr2:
        rx_periodo = st.selectbox("Período:", options=['6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=1, key="rx_ft_per")
        rx_tempo = st.selectbox("Tempo Gráfico:", ['60m', '1d', '1wk'], index=1, format_func=lambda x: {'60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="rx_ft_tmp")
    with cr3:
        rx_ft_periodo_individual = st.number_input("Período Teto/Chão:", value=14, step=1, min_value=1, key="rx_ft_periodo_in")
        rx_tipo_alvo = st.selectbox("Tipo de Alvo:", ["Risco Projetado (Ex: 2x)", "Alvo Fixo (%)"], key="rx_ft_tipo_alvo")
        rx_alvo_val = st.number_input("Múltiplo ou %:", value=2.0, step=0.5, key="rx_ft_alvo")
    with cr4:
        rx_usar_filtro = st.checkbox("Filtro MME8", value=True, key="rx_ft_filtro")
        rx_stop_loss = st.selectbox("Stop Loss:", ["Mínima do Candle Sinal", "Fixo (%)"], key="rx_ft_stop")

    btn_raiox = st.button("🔍 Rodar Backtest Fura-Teto/Chão", type="primary", use_container_width=True, key="rx_ft_btn")

    if btn_raiox:
        if not rx_ativo: st.error("Digite o código de um ativo.")
        else:
            with st.spinner(f'A calcular a matemática da inércia em {rx_ativo}...'):
                try:
                    df_full = tv.get_hist(symbol=rx_ativo, exchange='BMFBOVESPA', interval=tradutor_intervalo.get(rx_tempo, Interval.in_daily), n_bars=5000)
                    df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                    
                    df_full = identificar_fura_teto_chao(df_full, periodo_teto=rx_ft_periodo_individual).dropna()

                    if rx_periodo == '6mo': data_corte = df_full.index[-1] - pd.DateOffset(months=6)
                    elif rx_periodo == 'max': data_corte = df_full.index[0]
                    else: data_corte = df_full.index[-1] - pd.DateOffset(years=int(rx_periodo[0]))
                    
                    df_back = df_full[df_full.index >= data_corte].copy().reset_index()
                    col_data = df_back.columns[0]

                    trades, em_pos = [], False
                    preco_entrada, stop_loss, alvo, d_ent, direcao_trade = 0.0, 0.0, 0.0, None, 0
                    vitorias, derrotas, extremo_trade = 0, 0, 0.0 

                    for i in range(1, len(df_back)):
                        atual, ontem = df_back.iloc[i], df_back.iloc[i-1]

                        if em_pos:
                            if direcao_trade == 1:
                                extremo_trade = min(extremo_trade, atual['Low'])
                                queda_max = (extremo_trade / preco_entrada) - 1
                                if atual['Low'] <= stop_loss:
                                    trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': atual[col_data].strftime('%d/%m/%Y'), 'Direção': 'Compra', 'Duração': (atual[col_data] - d_ent).days, 'Lucro (R$)': rx_capital * ((stop_loss/preco_entrada)-1), 'Queda Máx': queda_max, 'Situação': 'Stop ❌'})
                                    derrotas += 1; em_pos = False
                                elif atual['High'] >= alvo:
                                    trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': atual[col_data].strftime('%d/%m/%Y'), 'Direção': 'Compra', 'Duração': (atual[col_data] - d_ent).days, 'Lucro (R$)': rx_capital * ((alvo/preco_entrada)-1), 'Queda Máx': queda_max, 'Situação': 'Gain ✅'})
                                    vitorias += 1; em_pos = False
                            else:
                                extremo_trade = max(extremo_trade, atual['High'])
                                queda_max = (preco_entrada - extremo_trade) / preco_entrada
                                if atual['High'] >= stop_loss:
                                    trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': atual[col_data].strftime('%d/%m/%Y'), 'Direção': 'Venda', 'Duração': (atual[col_data] - d_ent).days, 'Lucro (R$)': rx_capital * ((preco_entrada-stop_loss)/preco_entrada), 'Queda Máx': queda_max, 'Situação': 'Stop ❌'})
                                    derrotas += 1; em_pos = False
                                elif atual['Low'] <= alvo:
                                    trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': atual[col_data].strftime('%d/%m/%Y'), 'Direção': 'Venda', 'Duração': (atual[col_data] - d_ent).days, 'Lucro (R$)': rx_capital * ((preco_entrada-alvo)/preco_entrada), 'Queda Máx': queda_max, 'Situação': 'Gain ✅'})
                                    vitorias += 1; em_pos = False
                            continue

                        gatilho_compra = atual['Teto'] + 0.01
                        gatilho_venda = atual['Chao'] - 0.01
                        pode_comprar = ontem['Close'] > ontem['MME8'] if rx_usar_filtro else True
                        pode_vender = ontem['Close'] < ontem['MME8'] if rx_usar_filtro else True

                        if not em_pos:
                            if ("Compra" in rx_direcao or "Ambos" in rx_direcao) and pode_comprar:
                                if atual['High'] >= gatilho_compra:
                                    em_pos, direcao_trade = True, 1
                                    preco_entrada = max(gatilho_compra, atual['Open'])
                                    d_ent = atual[col_data]
                                    extremo_trade = atual['Low']
                                    stop_loss = ontem['Low'] - 0.01 if "Mínima" in rx_stop_loss else preco_entrada * 0.95
                                    alvo = preco_entrada + ((preco_entrada - stop_loss) * rx_alvo_val) if "Risco" in rx_tipo_alvo else preco_entrada * (1 + (rx_alvo_val/100))
                                    
                                    if atual['Low'] <= stop_loss:
                                        trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': atual[col_data].strftime('%d/%m/%Y'), 'Direção': 'Compra', 'Duração': 0, 'Lucro (R$)': rx_capital * ((stop_loss/preco_entrada)-1), 'Queda Máx': (atual['Low']/preco_entrada)-1, 'Situação': 'Stop ❌'})
                                        derrotas += 1; em_pos = False
                                        continue
                                    elif atual['High'] >= alvo:
                                        trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': atual[col_data].strftime('%d/%m/%Y'), 'Direção': 'Compra', 'Duração': 0, 'Lucro (R$)': rx_capital * ((alvo/preco_entrada)-1), 'Queda Máx': (atual['Low']/preco_entrada)-1, 'Situação': 'Gain ✅'})
                                        vitorias += 1; em_pos = False
                                        continue
                            
                            if ("Venda" in rx_direcao or "Ambos" in rx_direcao) and not em_pos and pode_vender:
                                if atual['Low'] <= gatilho_venda:
                                    em_pos, direcao_trade = True, -1
                                    preco_entrada = min(gatilho_venda, atual['Open'])
                                    d_ent = atual[col_data]
                                    extremo_trade = atual['High']
                                    stop_loss = ontem['High'] + 0.01 if "Mínima" in rx_stop_loss else preco_entrada * 1.05
                                    alvo = preco_entrada - ((stop_loss - preco_entrada) * rx_alvo_val) if "Risco" in rx_tipo_alvo else preco_entrada * (1 - (rx_alvo_val/100))
                                    
                                    if atual['High'] >= stop_loss:
                                        trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': atual[col_data].strftime('%d/%m/%Y'), 'Direção': 'Venda', 'Duração': 0, 'Lucro (R$)': rx_capital * ((preco_entrada-stop_loss)/preco_entrada), 'Queda Máx': (preco_entrada-atual['High'])/preco_entrada, 'Situação': 'Stop ❌'})
                                        derrotas += 1; em_pos = False
                                        continue
                                    elif atual['Low'] <= alvo:
                                        trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': atual[col_data].strftime('%d/%m/%Y'), 'Direção': 'Venda', 'Duração': 0, 'Lucro (R$)': rx_capital * ((preco_entrada-alvo)/preco_entrada), 'Queda Máx': (preco_entrada-atual['High'])/preco_entrada, 'Situação': 'Gain ✅'})
                                        vitorias += 1; em_pos = False
                                        continue
                                    
                    st.divider()
                    
                    if em_pos:
                        cot_atual = df_back['Close'].iloc[-1]
                        res_pct = (cot_atual / preco_entrada) - 1 if direcao_trade == 1 else (preco_entrada - cot_atual) / preco_entrada
                        queda_max_aberta = (extremo_trade / preco_entrada) - 1 if direcao_trade == 1 else (preco_entrada - extremo_trade) / preco_entrada
                        dir_texto = '📈 Compra' if direcao_trade == 1 else '📉 Venda'
                        st.warning(f"""
                        **⏳ {rx_ativo}: Em Operação ({dir_texto})**
                        * **Entrada:** {d_ent.strftime('%d/%m/%Y')} | **Dias na Operação:** {(df_back[col_data].iloc[-1] - d_ent).days}
                        * **PM:** R$ {preco_entrada:.2f} | **Cotação Atual:** R$ {cot_atual:.2f} | **Alvo:** R$ {alvo:.2f}
                        * **Queda Máx:** {queda_max_aberta*100:.2f}% | **Resultado Atual:** {res_pct*100:.2f}%
                        """)
                    else:
                        st.success(f"✅ **{rx_ativo}: Fora de posição. Aguardando novo rompimento de {rx_ft_periodo_individual}d.**")
                    
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
                        st.info(f"Nenhum rompimento validado no período.")
                except Exception as e: st.error(f"Erro: {e}")
