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
# 2. DETECTOR DE PADRÕES
# ==========================================
def identificar_padroes(df):
    df['Corpo'] = abs(df['Open'] - df['Close'])
    df['Range'] = df['High'] - df['Low']
    df['Pavio_Sup'] = df['High'] - df[['Open', 'Close']].max(axis=1)
    df['Pavio_Inf'] = df[['Open', 'Close']].min(axis=1) - df['Low']
    df['MME9'] = ta.ema(df['Close'], length=9)
    df['Tendencia'] = np.where(df['Close'] > df['MME9'], 'Alta', 'Baixa')
    df['Range'] = df['Range'].replace(0, 0.0001)

    df['Is_Martelo'] = (df['Tendencia'] == 'Baixa') & (df['Pavio_Inf'] >= 2 * df['Corpo']) & (df['Pavio_Sup'] <= 0.15 * df['Range']) & (df['Corpo'] <= 0.3 * df['Range'])
    df['Is_Enforcado'] = (df['Tendencia'] == 'Alta') & (df['Pavio_Inf'] >= 2 * df['Corpo']) & (df['Pavio_Sup'] <= 0.15 * df['Range']) & (df['Corpo'] <= 0.3 * df['Range'])
    df['Is_Estrela'] = (df['Tendencia'] == 'Alta') & (df['Pavio_Sup'] >= 2 * df['Corpo']) & (df['Pavio_Inf'] <= 0.15 * df['Range']) & (df['Corpo'] <= 0.3 * df['Range'])
    df['Is_InsideBar'] = (df['High'] < df['High'].shift(1)) & (df['Low'] > df['Low'].shift(1))
    return df

# ==========================================
# 3. INTERFACE E ABAS
# ==========================================
col_titulo, col_botao = st.columns([4, 1])
with col_titulo:
    st.title("🕯️ Price Action (Padrões de Candle)")
with col_botao:
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.link_button("📖 Ler Manual", "https://seusite.com/manual_padroes", use_container_width=True)

aba_radar, aba_individual = st.tabs(["📡 Radar Completo (Histórico + Hoje)", "🔬 Raio-X Individual"])

# ==========================================
# ABA 1: RADAR COMPLETO
# ==========================================
with aba_radar:
    with st.expander("⚙️ Configurações do Radar e Backtest", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            lista_sel = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"], key="rad_lst")
            padrao_sel = st.selectbox("Buscar Padrão:", ["Martelo (Compra)", "Estrela Cadente (Venda)", "Enforcado (Venda)", "Inside Bar (Rompimento)"], key="rad_padrao")
        with c2:
            tempo_grafico = st.selectbox("Tempo Gráfico:", ['1d', '60m'], format_func=lambda x: {'60m': '60 min', '1d': 'Diário'}[x], key="rad_tmp")
            rad_periodo = st.selectbox("Período de Backtest:", ['6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=1, key="rad_per")
        with c3:
            rad_capital = st.number_input("Capital por Trade (R$):", value=10000.0, step=1000.0, key="rad_cap")
            tipo_alvo = st.selectbox("Tipo de Alvo:", ["Técnico (Risco Projetado)", "Porcentagem (%)"], key="rad_tipo_alvo")
            alvo_val = st.number_input("Valor do Alvo (2 p/ 2x Risco ou 5 p/ 5%):", value=2.0, step=0.5, key="rad_alvo")
        with c4:
            tipo_stop = st.selectbox("Tipo de Stop:", ["Técnico (1 cent. do Sinal)", "Porcentagem (%)"], key="rad_tipo_stop")
            stop_val = st.number_input("Valor do Stop (%) [Se %]:", value=2.0, step=0.5, key="rad_stop_pct") / 100
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            btn_iniciar_radar = st.button("🚀 Iniciar Scanner Completo", type="primary", use_container_width=True)

    if btn_iniciar_radar:
        ativos_analise = bdrs_elite if lista_sel == "BDRs Elite" else ibrx_selecao if lista_sel == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        intervalo_tv = tradutor_intervalo.get(tempo_grafico, Interval.in_daily)
        
        ls_armados, ls_abertos, ls_historico = [], [], []
        p_bar = st.progress(0); s_text = st.empty()

        for idx, ativo_raw in enumerate(ativos_analise):
            ativo = ativo_raw.replace('.SA', '')
            s_text.text(f"🔍 Escaneando o Histórico e Hoje: {ativo} ({idx+1}/{len(ativos_analise)})")
            p_bar.progress((idx + 1) / len(ativos_analise))

            try:
                df_full = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=5000)
                if df_full is None or len(df_full) < 50: continue
                df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                df_full = identificar_padroes(df_full).dropna()

                # Recorte do tempo para o Backtest Histórico
                if rad_periodo == '6mo': data_corte = df_full.index[-1] - pd.DateOffset(months=6)
                elif rad_periodo == 'max': data_corte = df_full.index[0]
                else: data_corte = df_full.index[-1] - pd.DateOffset(years=int(rad_periodo[0]))
                
                df_back = df_full[df_full.index >= data_corte].copy().reset_index()
                col_data = df_back.columns[0]

                em_pos = False
                preco_entrada, stop_loss, alvo, d_ent, direcao = 0.0, 0.0, 0.0, None, 0
                col_sinal = 'Is_Martelo' if 'Martelo' in padrao_sel else 'Is_Estrela' if 'Estrela' in padrao_sel else 'Is_Enforcado' if 'Enforcado' in padrao_sel else 'Is_InsideBar'
                
                lucro_total_ativo = 0.0
                vitorias, total_trades = 0, 0

                for i in range(1, len(df_back)):
                    atual, ontem = df_back.iloc[i], df_back.iloc[i-1]
                    
                    if em_pos:
                        fechou = False
                        lucro_op = 0.0
                        if direcao == 1: # COMPRADO
                            if atual['Low'] <= stop_loss:
                                lucro_op = rad_capital * ((stop_loss/preco_entrada)-1)
                                fechou = True
                            elif atual['High'] >= alvo:
                                lucro_op = rad_capital * ((alvo/preco_entrada)-1)
                                fechou = True; vitorias += 1
                        elif direcao == -1: # VENDIDO
                            if atual['High'] >= stop_loss:
                                lucro_op = rad_capital * ((preco_entrada-stop_loss)/preco_entrada)
                                fechou = True
                            elif atual['Low'] <= alvo:
                                lucro_op = rad_capital * ((preco_entrada-alvo)/preco_entrada)
                                fechou = True; vitorias += 1
                        
                        if fechou:
                            lucro_total_ativo += lucro_op
                            total_trades += 1
                            em_pos = False
                        continue

                    # Gatilho
                    if ontem[col_sinal] and not em_pos:
                        if padrao_sel == "Martelo (Compra)" or padrao_sel == "Inside Bar (Rompimento)":
                            if atual['High'] > ontem['High']:
                                em_pos, direcao = True, 1
                                preco_entrada = max(ontem['High'] + 0.01, atual['Open'])
                                d_ent = atual[col_data]
                                stop_loss = ontem['Low'] - 0.01 if "Técnico" in tipo_stop else preco_entrada * (1 - stop_val)
                                alvo = preco_entrada + ((preco_entrada - (ontem['Low'] - 0.01)) * alvo_val) if "Técnico" in tipo_alvo else preco_entrada * (1 + (alvo_val/100))
                        
                        elif padrao_sel in ["Estrela Cadente (Venda)", "Enforcado (Venda)"]:
                            if atual['Low'] < ontem['Low']:
                                em_pos, direcao = True, -1
                                preco_entrada = min(ontem['Low'] - 0.01, atual['Open'])
                                d_ent = atual[col_data]
                                stop_loss = ontem['High'] + 0.01 if "Técnico" in tipo_stop else preco_entrada * (1 + stop_val)
                                alvo = preco_entrada - (((ontem['High'] + 0.01) - preco_entrada) * alvo_val) if "Técnico" in tipo_alvo else preco_entrada * (1 - (alvo_val/100))

                # Registo no Histórico (Apenas se teve operações)
                if total_trades > 0:
                    ls_historico.append({
                        'Ativo': ativo, 'Operações Fechadas': total_trades,
                        'Taxa de Acerto': f"{(vitorias/total_trades)*100:.1f}%",
                        'Lucro Total (R$)': lucro_total_ativo
                    })

                # Estado de Hoje
                if em_pos:
                    cot_atual = df_back['Close'].iloc[-1]
                    res_pct = (cot_atual / preco_entrada) - 1 if direcao == 1 else (preco_entrada - cot_atual) / preco_entrada
                    ls_abertos.append({
                        'Ativo': ativo, 'Sinal': 'COMPRA 🟢' if direcao == 1 else 'VENDA 🔴', 'Entrada': d_ent.strftime('%d/%m/%Y'),
                        'Dias': (df_back[col_data].iloc[-1] - d_ent).days, 'PM': f"R$ {preco_entrada:.2f}",
                        'Cotação Atual': f"R$ {cot_atual:.2f}", 'Resultado Atual': f"+{res_pct*100:.2f}%" if res_pct > 0 else f"{res_pct*100:.2f}%"
                    })
                else:
                    atual = df_back.iloc[-1]
                    if atual[col_sinal]:
                        dir_texto = "COMPRA" if "Martelo" in padrao_sel else "VENDA" if ("Estrela" in padrao_sel or "Enforcado" in padrao_sel) else "COMPRA/VENDA"
                        gatilho = atual['High'] + 0.01 if dir_texto == "COMPRA" else atual['Low'] - 0.01 if dir_texto == "VENDA" else f"C: {atual['High']+0.01:.2f} / V: {atual['Low']-0.01:.2f}"
                        ls_armados.append({
                            'Ativo': ativo, 'Padrão': padrao_sel.split('(')[0], 'Gatilho (Start)': gatilho, 'Status': "Aguardando Rompimento Amanhã"
                        })

            except Exception as e: pass
            time.sleep(0.01)

        s_text.empty(); p_bar.empty()

        st.divider()

        # 1. TOP 20 HISTÓRICO
        st.subheader(f"🏆 TOP 20 Histórico ({tradutor_periodo_nome[rad_periodo]})")
        st.markdown(f"Ativos mais lucrativos operando o **{padrao_sel.split('(')[0]}** com a gestão de risco selecionada.")
        if ls_historico:
            df_hist = pd.DataFrame(ls_historico).sort_values(by='Lucro Total (R$)', ascending=False).head(20)
            df_hist['Lucro Total (R$)'] = df_hist['Lucro Total (R$)'].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(df_hist.style.apply(colorir_lucro, axis=1), use_container_width=True, hide_index=True)
        else: st.info("Sem dados históricos validados neste período.")

        # 2. OPORTUNIDADES HOJE
        st.subheader("🚀 Oportunidades Hoje")
        if ls_armados: st.dataframe(pd.DataFrame(ls_armados), use_container_width=True, hide_index=True)
        else: st.info("Nenhum padrão armado na última barra.")

        # 3. OPERAÇÕES EM ANDAMENTO
        st.subheader("⏳ Operações em Andamento")
        if ls_abertos: 
            df_abertos = pd.DataFrame(ls_abertos).sort_values(by='Dias', ascending=False)
            st.dataframe(df_abertos.style.apply(colorir_lucro, axis=1), use_container_width=True, hide_index=True)
        else: st.info("Sem operações abertas para este setup no momento.")

# ==========================================
# ABA 2: RAIO-X INDIVIDUAL (MANTIDO INTACTO)
# ==========================================
with aba_individual:
    st.subheader("🔬 Raio-X Individual: Laboratório de Price Action")
    st.info("Aba mantida para análise minuciosa de um ativo específico (operações detalhadas uma a uma).")
    # ... Resto da Aba 2 (se quiser o código do Raio-X Individual aqui, eu adiciono na próxima, ou pode manter a mesma lógica anterior!)
