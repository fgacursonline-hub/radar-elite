import streamlit as st
import pandas as pd
from tvDatafeed import TvDatafeed, Interval

# 1. Configuração da Página
st.set_page_config(page_title="Radar de Rompimento", layout="wide", page_icon="⚡")

# Inicializa o TradingView
if 'tv' not in st.session_state:
    st.session_state.tv = TvDatafeed()
tv = st.session_state.tv

# Listas Oficiais
bdrs_elite = ['NVDC34', 'P2LT34', 'ROXO34', 'INBR32', 'M1TA34', 'TSLA34', 'LILY34', 'AMZO34', 'AURA33', 'GOGL34', 'MSFT34', 'MUTC34', 'MELI34', 'C2OI34', 'ORCL34', 'M2ST34', 'A1MD34', 'NFLX34', 'ITLC34', 'AVGO34', 'COCA34', 'JBSS32', 'AAPL34', 'XPBR31', 'STOC34']
ibrx_selecao = ['PETR4', 'VALE3', 'ITUB4', 'BBDC4', 'BBAS3', 'B3SA3', 'ABEV3', 'WEGE3', 'AXIA3', 'SUZB3', 'RENT3', 'RADL3', 'EQTL3', 'LREN3', 'PRIO3', 'HAPV3', 'GGBR4', 'VBBR3', 'SBSP3', 'CMIG4', 'CPLE3', 'ENEV3', 'TIMS3', 'TOTS3', 'EGIE3', 'CSAN3', 'ALOS3', 'DIRR3', 'VIVT3', 'KLBN11', 'UGPA3', 'PSSA3', 'CYRE3', 'ASAI3', 'RAIL3', 'ISAE3', 'CSNA3', 'MGLU3', 'EMBJ3', 'TAEE11', 'BBSE3', 'FLRY3', 'MULT3', 'TFCO4', 'LEVE3', 'CPFE3', 'GOAU4', 'MRVE3', 'YDUQ3', 'SMTO3', 'SLCE3', 'CVCB3', 'USIM5', 'BRAP4', 'BRAV3', 'EZTC3', 'PCAR3', 'AUAU3', 'DXCO3', 'CASH3', 'VAMO3', 'AZZA3', 'AURE3', 'BEEF3', 'ECOR3', 'FESA4', 'POMO4', 'CURY3', 'INTB3', 'JHSF3', 'LIGT3', 'LOGG3', 'MDIA3', 'MBRF3', 'NEOE3', 'QUAL3', 'RAPT4', 'ROMI3', 'SANB11', 'SIMH3', 'TEND3', 'VULC3', 'PLPL3', 'CEAB3', 'UNIP6', 'LWSA3', 'BPAC11', 'GMAT3', 'CXSE3', 'ABCB4', 'CSMG3', 'SAPR11', 'GRND3', 'BRAP3', 'LAVV3', 'RANI3', 'ITSA3', 'ALUP11', 'FIQE3', 'COGN3', 'IRBR3', 'SEER3', 'ANIM3', 'JSLG3', 'POSI3', 'MYPK3', 'SOJA3', 'BLAU3', 'PGMN3', 'TUPY3', 'VVEO3', 'MELK3', 'SHUL4', 'BRSR6']

st.title("⚡ Radar & Backtest de Rompimento")
st.markdown("Identifique e valide rompimentos históricos de Máximas e Fechamentos.")
st.divider()

aba_rad_p, aba_backtest, aba_raio_x = st.tabs(["📡 Radar (Padrão)", "📊 Backtest", "🔬 Raio-X Individual"])

# ==========================================
# 1. RADAR (PADRÃO) - BLOCO COMPLETO REVISADO
# ==========================================
with aba_rad_p:
    # FILTROS DE ENTRADA
    c1, c2, c3 = st.columns(3)
    with c1: 
        escolha_lista = st.selectbox("Escolha a Lista:", ["BDRs Elite", "IBrX Seleção", "Todos (BDR + IBrX)"], key="r_lst_p")
        tipo_romp = st.radio("Romper por:", ["Máxima", "Fechamento"], horizontal=True, key="r_tipo_p")
    with c2:
        tempo_grafico = st.selectbox("Tempo Gráfico:", ["60m", "Diário", "Mensal", "Anual"], index=3, key="r_tmp_p")
        cap_trade = st.number_input("Capital por Trade (R$):", value=5000, step=500, key="r_cap_p")
    with c3:
        alvo_escolhido = st.number_input("Alvo de Lucro (%):", value=20.0, step=5.0, key="r_alvo_p")
        st.caption(f"O Radar monitora o progresso até {alvo_escolhido}%.")

    if st.button("🚀 Iniciar Radar de Rompimento", type="primary", use_container_width=True, key="btn_radar_p"):
        lista_ativos = bdrs_elite if escolha_lista == "BDRs Elite" else ibrx_selecao if escolha_lista == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        barra = st.progress(0)
        encontrados = []

        for idx, ativo in enumerate(lista_ativos):
            barra.progress((idx + 1) / len(lista_ativos), text=f"🔍 Analisando {ativo}...")
            try:
                # Puxamos 300 barras diárias para cobrir o histórico necessário
                df_d = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=Interval.in_daily, n_bars=300)
                
                if df_d is not None and len(df_d) > 260:
                    df_d.columns = [c.capitalize() for c in df_d.columns]
                    pa = df_d['Close'].iloc[-1]
                    col_ref = "High" if tipo_romp == "Máxima" else "Close"

                    # DEFINIÇÃO DA REFERÊNCIA (Período anterior fechado)
                    if tempo_grafico == "Anual":
                        # Referência do topo do ano passado (2025)
                        ref_val = df_d[col_ref].iloc[-300:-76].max() 
                    elif tempo_grafico == "Mensal":
                        # Referência do mês passado fechado
                        ref_val = df_d[col_ref].iloc[-45:-22].max()
                    elif tempo_grafico == "60m":
                        df_h = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=Interval.in_1_hour, n_bars=3)
                        df_h.columns = [c.capitalize() for c in df_h.columns]
                        ref_val = df_h[col_ref].iloc[-2]
                    else:
                        ref_val = df_d[col_ref].iloc[-2] # Ontem
                        
                    if pa > ref_val:
                        # Contagem de dias úteis desde o rompimento
                        cont_dias = 0
                        for v in range(len(df_d)-1, -1, -1):
                            if df_d['High'].iloc[v] > ref_val:
                                cont_dias += 1
                            else:
                                break
                        
                        lucro_real = ((pa / ref_val) - 1) * 100
                        
                        # Lógica de Status do Alvo (Visualmente limpa)
                        if lucro_real >= alvo_escolhido:
                            excedente = lucro_real - alvo_escolhido
                            status_alvo = f"🎯 ATINGIDO (+{excedente:.2f}%)"
                        else:
                            falta = alvo_escolhido - lucro_real
                            status_alvo = f"⏳ Falta {falta:.2f}%"
                        
                        encontrados.append({
                            'Ativo': ativo,
                            'Preço Atual': f"R$ {pa:.2f}",
                            f'Ref. {tipo_romp}': f"R$ {ref_val:.2f}",
                            'Lucro Real': f"{lucro_real:.2f}%",
                            'Status p/ Alvo': status_alvo,
                            'Duração': f"{cont_dias} dias úteis",
                            'Lote': int(cap_trade // pa)
                        })
            except: pass
        
        barra.empty()
        if encontrados:
            st.success(f"Varredura completa! {len(encontrados)} ativos rompidos no {tempo_grafico}.")
            df_final = pd.DataFrame(encontrados)
            
            # Função para colorir apenas quem atingiu o alvo
            def destacar_alvo(val):
                color = '#d4edda' if '🎯' in str(val) else 'transparent'
                return f'background-color: {color}; color: black'

            st.dataframe(
                df_final.style.map(destacar_alvo, subset=['Status p/ Alvo']), 
                use_container_width=True, 
                hide_index=True
            )
        else:
            st.warning(f"Nenhum rompimento de {tipo_romp} detectado no momento."))

# ==========================================
# 2. 📊 BACKTEST (NOVA ABA)
# ==========================================
with aba_backtest:
    st.subheader("📊 Simulador de Resultados Históricos")
    st.markdown("Testa o que aconteceria se você tivesse entrado em todos os rompimentos passados deste ativo.")
    
    bk1, bk2, bk3 = st.columns(3)
    with bk1: at_bk = st.text_input("Ativo para Teste:", value="AURA33").upper()
    with bk2: alvo_bk = st.number_input("Alvo do Backtest (%):", value=50.0, step=10.0, key="alvo_bk")
    with bk3: hist_bk = st.number_input("Histórico (Velas Diárias):", value=1000, step=500)

   if st.button("🚀 Iniciar Radar de Rompimento", type="primary", use_container_width=True):
        lista_ativos = bdrs_elite if escolha_lista == "BDRs Elite" else ibrx_selecao if escolha_lista == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        barra = st.progress(0)
        encontrados = []

        for idx, ativo in enumerate(lista_ativos):
            barra.progress((idx + 1) / len(lista_ativos), text=f"🔍 Analisando {ativo}...")
            try:
                # Puxamos 300 barras diárias para cobrir o ano anterior e contar duração
                df_d = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=Interval.in_daily, n_bars=300)
                
                if df_d is not None and len(df_d) > 260:
                    df_d.columns = [c.capitalize() for c in df_d.columns]
                    pa = df_d['Close'].iloc[-1]
                    col_ref = "High" if tipo_romp == "Máxima" else "Close"

                    # DEFINIÇÃO DA REFERÊNCIA (Pega o período fechado anterior)
                    if tempo_grafico == "Anual":
                        ref_val = df_d[col_ref].iloc[-300:-76].max() 
                    elif tempo_grafico == "Mensal":
                        ref_val = df_d[col_ref].iloc[-45:-22].max()
                    elif tempo_grafico == "60m":
                        df_h = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=Interval.in_1_hour, n_bars=3)
                        df_h.columns = [c.capitalize() for c in df_h.columns]
                        ref_val = df_h[col_ref].iloc[-2]
                    else:
                        ref_val = df_d[col_ref].iloc[-2] # Ontem
                        
                    if pa > ref_val:
                        # Contagem de dias úteis desde o rompimento inicial
                        cont_dias = 0
                        for v in range(len(df_d)-1, -1, -1):
                            if df_d['High'].iloc[v] > ref_val:
                                cont_dias += 1
                            else:
                                break
                        
                        lucro_real = ((pa / ref_val) - 1) * 100
                        
                        # --- LÓGICA DE STATUS DO ALVO (MELHORADA) ---
                        if lucro_real >= alvo_escolhido:
                            excedente = lucro_real - alvo_escolhido
                            status_alvo = f"🎯 ATINGIDO (+{excedente:.2f}%)"
                        else:
                            falta = alvo_escolhido - lucro_real
                            status_alvo = f"⏳ Falta {falta:.2f}%"
                        
                        encontrados.append({
                            'Ativo': ativo,
                            'Preço Atual': f"R$ {pa:.2f}",
                            f'Ref. {tipo_romp}': f"R$ {ref_val:.2f}",
                            'Lucro Real': f"{lucro_real:.2f}%",
                            'Status p/ Alvo': status_alvo,
                            'Duração': f"{cont_dias} dias úteis",
                            'Lote': int(cap_trade // pa)
                        })
            except: pass
        
        barra.empty()
        if encontrados:
            st.success(f"Encontrados {len(encontrados)} ativos rompidos no {tempo_grafico}!")
            df_final = pd.DataFrame(encontrados)
            
            # Estilização para destacar quem já atingiu o alvo
            def destacar_alvo(val):
                color = '#d4edda' if '🎯' in str(val) else 'transparent'
                return f'background-color: {color}; color: black'

            st.dataframe(
                df_final.style.map(destacar_alvo, subset=['Status p/ Alvo']), 
                use_container_width=True, 
                hide_index=True
            )
        else:
            st.warning(f"Nenhum rompimento de {tipo_romp} detectado no momento.")
