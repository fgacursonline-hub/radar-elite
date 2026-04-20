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

# Criação das Abas
aba_rad_p, aba_backtest, aba_raio_x = st.tabs(["📡 Radar (Padrão)", "📊 Backtest", "🔬 Raio-X Individual"])

# ==========================================
# 1. RADAR (PADRÃO)
# ==========================================
with aba_rad_p:
    # Filtros
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

    # Botão de Ação
    if st.button("🚀 Iniciar Radar de Rompimento", type="primary", use_container_width=True, key="btn_radar_p"):
        lista_ativos = bdrs_elite if escolha_lista == "BDRs Elite" else ibrx_selecao if escolha_lista == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        barra = st.progress(0)
        encontrados = []

        for idx, ativo in enumerate(lista_ativos):
            barra.progress((idx + 1) / len(lista_ativos), text=f"🔍 Analisando {ativo}...")
            try:
                df_d = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=Interval.in_daily, n_bars=300)
                
                if df_d is not None and len(df_d) > 260:
                    df_d.columns = [c.capitalize() for c in df_d.columns]
                    pa = df_d['Close'].iloc[-1]
                    col_ref = "High" if tipo_romp == "Máxima" else "Close"

                    # DEFINIÇÃO DA REFERÊNCIA
                    if tempo_grafico == "Anual":
                        ref_val = df_d[col_ref].iloc[-300:-76].max() 
                    elif tempo_grafico == "Mensal":
                        ref_val = df_d[col_ref].iloc[-45:-22].max()
                    elif tempo_grafico == "60m":
                        df_h = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=Interval.in_1_hour, n_bars=3)
                        if df_h is not None:
                            df_h.columns = [c.capitalize() for c in df_h.columns]
                            ref_val = df_h[col_ref].iloc[-2]
                        else:
                            continue
                    else:
                        ref_val = df_d[col_ref].iloc[-2]
                        
                    # VERIFICA O ROMPIMENTO
                    if pa > ref_val:
                        cont_dias = 0
                        for v in range(len(df_d)-1, -1, -1):
                            if df_d['High'].iloc[v] > ref_val: cont_dias += 1
                            else: break
                        
                        lucro_real = ((pa / ref_val) - 1) * 100
                        
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
            
            def destacar_alvo(val):
                color = '#d4edda' if '🎯' in str(val) else 'transparent'
                return f'background-color: {color}; color: black'

            try:
                st.dataframe(df_final.style.map(destacar_alvo, subset=['Status p/ Alvo']), use_container_width=True, hide_index=True)
            except:
                st.dataframe(df_final.style.applymap(destacar_alvo, subset=['Status p/ Alvo']), use_container_width=True, hide_index=True)
        else:
            st.warning(f"Nenhum rompimento de {tipo_romp} detectado no momento.")

# ==========================================
# 2. BACKTEST GLOBAL (PORTFÓLIO)
# ==========================================
with aba_backtest:
    st.subheader("📊 Backtest Global da Estratégia")
    st.markdown("Varre uma lista completa para descobrir a Taxa de Acerto, Payoff e Retorno Acumulado histórico.")
    
    col_b1, col_b2, col_b3, col_b4 = st.columns(4)
    with col_b1:
        lista_bk = st.selectbox("Lista:", ["BDRs Elite", "IBrX Seleção", "Todos (BDR + IBrX)"], key="bk_lst")
        tipo_romp_bk = st.radio("Romper por:", ["Máxima", "Fechamento"], horizontal=True, key="bk_tipo")
    with col_b2:
        tempo_bk = st.selectbox("Tempo Gráfico:", ["Semanal", "Mensal", "Anual"], index=2, key="bk_tmp")
        hist_bk = st.number_input("Histórico (Velas Diárias):", value=1500, step=500, key="bk_velas", help="1500 = ~6 anos")
    with col_b3:
        alvo_bk = st.number_input("Alvo de Ganho (Gain %):", value=40.0, step=5.0, key="bk_alvo")
        # --- CHECKBOX ADICIONADO AQUI ---
        usar_stop_bk = st.checkbox("Habilitar Stop Loss", value=True, key="bk_usar_stop")
        stop_bk = st.number_input("Stop Loss (Loss %):", value=15.0, step=5.0, key="bk_stop")
    with col_b4:
        st.info("Payoff = Média de Ganho / Média de Perda.")
        st.caption("O simulador comprará quando o preço de fechamento superar a referência escolhida.")

    if st.button("⚙️ Rodar Backtest em Lote", type="primary", use_container_width=True, key="btn_run_bk"):
        ativos = bdrs_elite if lista_bk == "BDRs Elite" else ibrx_selecao if lista_bk == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        
        janela = 252 if tempo_bk == "Anual" else (21 if tempo_bk == "Mensal" else 5) 
        
        resultados_bk = []
        barra_bk = st.progress(0)

        for idx, ativo in enumerate(ativos):
            barra_bk.progress((idx + 1) / len(ativos), text=f"Calculando métricas para {ativo}...")
            try:
                df = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=Interval.in_daily, n_bars=hist_bk)
                if df is None or len(df) <= janela:
                    continue
                    
                df.columns = [c.capitalize() for c in df.columns]
                
                col_ref_bk = "High" if tipo_romp_bk == "Máxima" else "Close"
                df['Max_Ref'] = df[col_ref_bk].rolling(window=janela).max().shift(1)
                
                em_trade = False
                lucros = []
                prejuizos = []
                
                for i in range(janela, len(df)):
                    if not em_trade:
                        # Gatilho de Entrada: Fechamento atual cruza a referência móvel
                        if df['Close'].iloc[i] > df['Max_Ref'].iloc[i]:
                            em_trade = True
                            p_in = df['Close'].iloc[i]
                            p_gain = p_in * (1 + (alvo_bk / 100))
                            p_loss = p_in * (1 - (stop_bk / 100))
                    else:
                        # Monitoramento de Saída
                        if df['High'].iloc[i] >= p_gain:
                            lucros.append(alvo_bk)
                            em_trade = False
                        # --- TRAVA DO STOP LOSS APLICADA AQUI ---
                        elif usar_stop_bk and df['Low'].iloc[i] <= p_loss:
                            prejuizos.append(stop_bk)
                            em_trade = False
                            
                # Cálculos Finais
                total_ops = len(lucros) + len(prejuizos)
                if total_ops > 0:
                    acertos = len(lucros)
                    erros = len(prejuizos)
                    tx_acerto = (acertos / total_ops) * 100
                    
                    media_gain = alvo_bk
                    media_loss = stop_bk
                    payoff = media_gain / media_loss if media_loss > 0 else media_gain
                    
                    acumulado = sum(lucros) - sum(prejuizos)
                    
                    resultados_bk.append({
                        'Ativo': ativo,
                        'Ops': total_ops,
                        'Acertos': acertos,
                        'Erros': erros,
                        'Tx. Acerto': f"{tx_acerto:.1f}%",
                        'Payoff': f"{payoff:.2f}",
                        'Acumulado': acumulado
                    })
            except: pass
                
        barra_bk.empty()
        
        if resultados_bk:
            st.success(f"Backtest processado em {len(resultados_bk)} ativos da lista '{lista_bk}'!")
            df_res = pd.DataFrame(resultados_bk)
            
            df_res = df_res.sort_values(by='Acumulado', ascending=False)
            df_res['Acumulado'] = df_res['Acumulado'].apply(lambda x: f"{x:.1f}%")
            
            def colorir_acumulado(val):
                try:
                    num = float(val.replace('%',''))
                    if num > 0: return 'color: #28a745; font-weight: bold'
                    elif num < 0: return 'color: #dc3545'
                except: pass
                return ''
                
            try:
                st.dataframe(df_res.style.map(colorir_acumulado, subset=['Acumulado']), use_container_width=True, hide_index=True)
            except:
                st.dataframe(df_res.style.applymap(colorir_acumulado, subset=['Acumulado']), use_container_width=True, hide_index=True)
        else:
            st.warning("Nenhum trade foi finalizado no histórico selecionado.")
# ==========================================
# 3. RAIO-X INDIVIDUAL (Simulador Histórico)
# ==========================================
with aba_raio_x:
    st.subheader("🔬 Simulador de Resultados Históricos (Individual)")
    st.markdown("Audite cada entrada, saída (Gain ou Loss), duração e o 'calor' máximo suportado na operação.")
    
    rx1, rx2, rx3, rx4 = st.columns(4)
    with rx1: 
        at_rx = st.text_input("Ativo para Teste:", value="AURA33", key="rx_ativo").upper()
        tipo_romp_rx = st.radio("Romper por:", ["Máxima", "Fechamento"], horizontal=True, key="rx_tipo")
    with rx2: 
        tempo_rx = st.selectbox("Tempo Gráfico:", ["Mensal", "Anual"], index=1, key="rx_tmp")
        hist_rx = st.number_input("Histórico (Velas Diárias):", value=1500, step=500, key="rx_hist")
    with rx3: 
        alvo_rx = st.number_input("Alvo de Ganho (%):", value=40.0, step=5.0, key="rx_alvo")
    with rx4:
        usar_stop_rx = st.checkbox("Habilitar Stop Loss", value=True, key="rx_chk_stop")
        stop_rx = st.number_input("Stop Loss (%):", value=15.0, step=5.0, key="rx_stop", disabled=not usar_stop_rx)

    if st.button("⚙️ Rodar Simulação do Ativo", type="primary", use_container_width=True, key="btn_rx"):
        try:
            df = tv.get_hist(symbol=at_rx, exchange='BMFBOVESPA', interval=Interval.in_daily, n_bars=hist_rx)
            janela_rx = 252 if tempo_rx == "Anual" else 21
            
            if df is not None and len(df) > janela_rx:
                df.columns = [c.capitalize() for c in df.columns]
                
                # Define a referência móvel (Máxima ou Fechamento)
                col_ref_rx = "High" if tipo_romp_rx == "Máxima" else "Close"
                df['Max_Ref'] = df[col_ref_rx].rolling(window=janela_rx).max().shift(1)
                
                trades = []
                em_trade = False
                
                for i in range(janela_rx, len(df)):
                    if not em_trade:
                        # Gatilho de entrada no rompimento da referência
                        if df['Close'].iloc[i] > df['Max_Ref'].iloc[i]:
                            em_trade = True
                            p_entrada = df['Close'].iloc[i]
                            p_alvo = p_entrada * (1 + (alvo_rx / 100))
                            p_stop = p_entrada * (1 - (stop_rx / 100)) if usar_stop_rx else 0
                            data_entrada = df.index[i]
                            
                            # Inicializa o rastreador de queda máxima
                            preco_minimo_op = p_entrada
                    else:
                        # Rastreia o menor preço alcançado durante o trade (O "Calor")
                        if df['Low'].iloc[i] < preco_minimo_op:
                            preco_minimo_op = df['Low'].iloc[i]
                            
                        # Monitora Saída (Gain)
                        if df['High'].iloc[i] >= p_alvo:
                            dias_op = (df.index[i] - data_entrada).days
                            queda_max = ((preco_minimo_op / p_entrada) - 1) * 100
                            
                            trades.append({
                                'Data Entrada': data_entrada.strftime('%d/%m/%Y'),
                                'Preço Entrada': f"R$ {p_entrada:.2f}",
                                'Data Saída': df.index[i].strftime('%d/%m/%Y'),
                                'Preço Saída': f"R$ {p_alvo:.2f}",
                                'Queda Máxima': f"{queda_max:.2f}%",
                                'Duração': f"{dias_op} dias",
                                'Resultado': f"🟢 GAIN"
                            })
                            em_trade = False
                            
                        # Monitora Saída (Loss / Stop)
                        elif usar_stop_rx and df['Low'].iloc[i] <= p_stop:
                            dias_op = (df.index[i] - data_entrada).days
                            queda_max = ((preco_minimo_op / p_entrada) - 1) * 100
                            
                            trades.append({
                                'Data Entrada': data_entrada.strftime('%d/%m/%Y'),
                                'Preço Entrada': f"R$ {p_entrada:.2f}",
                                'Data Saída': df.index[i].strftime('%d/%m/%Y'),
                                'Preço Saída': f"R$ {p_stop:.2f}",
                                'Queda Máxima': f"{queda_max:.2f}%",
                                'Duração': f"{dias_op} dias",
                                'Resultado': f"🔴 LOSS"
                            })
                            em_trade = False
                
                if trades:
                    # --- CÁLCULO DAS MÉTRICAS QUANTITATIVAS ---
                    total_ops = len(trades)
                    acertos = sum(1 for t in trades if 'GAIN' in t['Resultado'])
                    erros = sum(1 for t in trades if 'LOSS' in t['Resultado'])
                    
                    tx_acerto = (acertos / total_ops) * 100
                    
                    if usar_stop_rx and stop_rx > 0:
                        payoff_str = f"{(alvo_rx / stop_rx):.2f}"
                    else:
                        payoff_str = "N/A"
                        
                    acumulado = (acertos * alvo_rx) - (erros * stop_rx if usar_stop_rx else 0)
                    
                    st.success(f"Simulação concluída para {at_rx}!")
                    
                    # --- PAINEL DE MÉTRICAS (DASHBOARD) ---
                    st.divider()
                    m1, m2, m3, m4, m5, m6 = st.columns(6)
                    m1.metric("Total de Operações", total_ops)
                    m2.metric("🟢 Acertos", acertos)
                    m3.metric("🔴 Erros", erros)
                    m4.metric("🎯 Taxa de Acerto", f"{tx_acerto:.1f}%")
                    m5.metric("⚖️ Payoff", payoff_str)
                    m6.metric("💰 Acumulado", f"{acumulado:.1f}%", delta=f"{acumulado:.1f}%", delta_color="normal" if acumulado >= 0 else "inverse")
                    st.divider()
                    
                    # --- TABELA DE TRADES ---
                    df_trades = pd.DataFrame(trades)
                    
                    def colorir_resultado(val):
                        if 'GAIN' in str(val): return 'color: #28a745; font-weight: bold'
                        elif 'LOSS' in str(val): return 'color: #dc3545; font-weight: bold'
                        return ''
                        
                    try:
                        st.dataframe(df_trades.style.map(colorir_resultado, subset=['Resultado']), use_container_width=True, hide_index=True)
                    except:
                        st.dataframe(df_trades.style.applymap(colorir_resultado, subset=['Resultado']), use_container_width=True, hide_index=True)
                else:
                    st.warning("Nenhum trade finalizado encontrado. O ativo pode estar em operação no momento sem atingir o alvo.")
            else:
                st.error("Histórico insuficiente para essa janela de tempo.")
        except Exception as e: 
            st.error(f"Erro na Simulação: {e}")
