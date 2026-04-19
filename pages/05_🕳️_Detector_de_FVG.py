import streamlit as st
import pandas as pd
import pandas_ta as ta
from tvDatafeed import TvDatafeed, Interval
import time

# 1. Configuração da Página
st.set_page_config(page_title="Detector de FVG", layout="wide")

# Inicializa o TradingView
if 'tv' not in st.session_state:
    st.session_state.tv = TvDatafeed()
tv = st.session_state.tv

# --- Cabeçalho ---
col_tit, col_man = st.columns([4, 1])
with col_tit:
    st.title("🕳️ Smart Money: Gaps Institucionais (FVG)")
with col_man:
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.link_button("📖 Manual FVG", "https://seusite.com/manual_fvg", use_container_width=True)

st.markdown("Identifique desequilíbrios de preço e opere nas zonas defendidas pelos grandes bancos.")
st.divider()

# --- CRIAÇÃO DAS 4 SUB-ABAS ---
aba_individual, aba_radar, aba_backtest, aba_supremo = st.tabs([
    "🔍 Raio-X Individual", 
    "📡 Radar de Oportunidades", 
    "📊 Backtest FVG (Estatísticas)",
    "🔥 Radar Supremo (9.1 + FVG)"
])

# ==========================================
# ABA 1: RAIO-X INDIVIDUAL
# ==========================================
with aba_individual:
    st.subheader("Análise Detalhada por Ativo")
    c1, c2, c3 = st.columns(3)
    with c1: lupa_ativo = st.text_input("Ativo (Ex: TSLA34):", value="TSLA34", key="fvg_ativo").upper()
    with c2: lupa_tempo = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk', '1mo'], index=2, format_func=lambda x: {'15m':'15 min','60m':'60 min','1d':'Diário','1wk':'Semanal','1mo':'Mensal'}[x], key="fvg_tempo")
    with c3: lupa_bars = st.number_input("Qtd. de Velas:", value=300, step=50, key="fvg_velas")

    if st.button("🔍 Escanear Desequilíbrios", type="primary", use_container_width=True, key="btn_fvg_ind"):
        ativo = lupa_ativo.strip().replace('.SA', '')
        intervalo_tv = {'15m': Interval.in_15_minute, '60m': Interval.in_1_hour, '1d': Interval.in_daily, '1wk': Interval.in_weekly, '1mo': Interval.in_monthly}.get(lupa_tempo, Interval.in_daily)

        with st.spinner(f"Caçando Gaps em {ativo}..."):
            try:
                df = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=lupa_bars)
                if df is not None and len(df) > 3:
                    df.rename(columns={'high': 'High', 'low': 'Low', 'close': 'Close', 'open': 'Open'}, inplace=True)
                    lista_gaps = []
                    preco_atual = df['Close'].iloc[-1]
                    alerta_oportunidade = False
                    
                    for i in range(2, len(df)):
                        if df['Low'].iloc[i] > df['High'].iloc[i-2]:
                            topo, fundo = df['Low'].iloc[i], df['High'].iloc[i-2]
                            aberto = df['Low'].iloc[i:].min() > fundo
                            if aberto and (fundo <= preco_atual <= topo): alerta_oportunidade = True
                            lista_gaps.append({'Data': df.index[i].strftime('%d/%m %H:%M'), 'Tipo': 'Alta 🟢', 'Zona': 'Suporte', 'Limite Superior': topo, 'Limite Inferior': fundo, 'Status': "Aberto" if aberto else "Preenchido"})

                        if df['High'].iloc[i] < df['Low'].iloc[i-2]:
                            topo, fundo = df['Low'].iloc[i-2], df['High'].iloc[i]
                            aberto = df['High'].iloc[i:].max() < topo
                            if aberto and (fundo <= preco_atual <= topo): alerta_oportunidade = True
                            lista_gaps.append({'Data': df.index[i].strftime('%d/%m %H:%M'), 'Tipo': 'Baixa 🔴', 'Zona': 'Resistência', 'Limite Superior': topo, 'Limite Inferior': fundo, 'Status': "Aberto" if aberto else "Preenchido"})

                    st.subheader(f"📊 Zonas de Desequilíbrio: {ativo} | Atual: R$ {preco_atual:.2f}")
                    if alerta_oportunidade: st.error(f"🚨 **OPORTUNIDADE:** Preço de {ativo} está DENTRO de uma zona de Gap Institucional ABERTO!")
                    
                    if lista_gaps:
                        gaps_abertos = [g for g in lista_gaps if g['Status'] == 'Aberto']
                        destaques = gaps_abertos[-3:] if gaps_abertos else lista_gaps[-3:]
                        cols = st.columns(len(destaques))
                        for idx, gap in enumerate(destaques):
                            with cols[idx]:
                                st.markdown(f"### {gap['Tipo']}\n*{gap['Zona']}*")
                                st.metric("Topo", f"R$ {gap['Limite Superior']:.2f}")
                                st.metric("Fundo", f"R$ {gap['Limite Inferior']:.2f}")
                                st.caption(f"Status: **{gap['Status']}** | {gap['Data']}")
                        st.divider()
                        df_final = pd.DataFrame(lista_gaps).sort_index(ascending=False)
                        df_final['Limite Superior'] = df_final['Limite Superior'].apply(lambda x: f"R$ {x:.2f}")
                        df_final['Limite Inferior'] = df_final['Limite Inferior'].apply(lambda x: f"R$ {x:.2f}")
                        st.dataframe(df_final, use_container_width=True, hide_index=True)
                    else:
                        st.success("Mercado em equilíbrio. Nenhum Gap relevante.")
                else: st.error("Ativo não encontrado.")
            except Exception as e: st.error(f"Erro: {e}")

# ==========================================
# ABA 2: RADAR DE OPORTUNIDADES
# ==========================================
with aba_radar:
    st.subheader("Varredura em Massa")
    bdrs_elite = ['NVDC34', 'P2LT34', 'ROXO34', 'INBR32', 'M1TA34', 'TSLA34', 'LILY34', 'AMZO34', 'AURA33', 'GOGL34', 'MSFT34', 'MUTC34', 'MELI34', 'C2OI34', 'ORCL34', 'M2ST34', 'A1MD34', 'NFLX34', 'ITLC34', 'AVGO34', 'COCA34', 'JBSS32', 'AAPL34', 'XPBR31', 'STOC34']
    ibrx_selecao = ['PETR4', 'VALE3', 'ITUB4', 'BBDC4', 'BBAS3', 'B3SA3', 'ABEV3', 'WEGE3', 'AXIA3', 'SUZB3', 'RENT3', 'RADL3', 'EQTL3', 'LREN3', 'PRIO3', 'HAPV3', 'GGBR4', 'VBBR3', 'SBSP3', 'CMIG4', 'CPLE3', 'ENEV3', 'TIMS3', 'TOTS3', 'EGIE3', 'CSAN3', 'ALOS3', 'DIRR3', 'VIVT3', 'KLBN11', 'UGPA3', 'PSSA3', 'CYRE3', 'ASAI3', 'RAIL3', 'ISAE3', 'CSNA3', 'MGLU3', 'EMBJ3', 'TAEE11', 'BBSE3', 'FLRY3', 'MULT3', 'TFCO4', 'LEVE3', 'CPFE3', 'GOAU4', 'MRVE3', 'YDUQ3', 'SMTO3', 'SLCE3', 'CVCB3', 'USIM5', 'BRAP4', 'BRAV3', 'EZTC3', 'PCAR3', 'AUAU3', 'DXCO3', 'CASH3', 'VAMO3', 'AZZA3', 'AURE3', 'BEEF3', 'ECOR3', 'FESA4', 'POMO4', 'CURY3', 'INTB3', 'JHSF3', 'LIGT3', 'LOGG3', 'MDIA3', 'MBRF3', 'NEOE3', 'QUAL3', 'RAPT4', 'ROMI3', 'SANB11', 'SIMH3', 'TEND3', 'VULC3', 'PLPL3', 'CEAB3', 'UNIP6', 'LWSA3', 'BPAC11', 'GMAT3', 'CXSE3', 'ABCB4', 'CSMG3', 'SAPR11', 'GRND3', 'BRAP3', 'LAVV3', 'RANI3', 'ITSA3', 'ALUP11', 'FIQE3', 'COGN3', 'IRBR3', 'SEER3', 'ANIM3', 'JSLG3', 'POSI3', 'MYPK3', 'SOJA3', 'BLAU3', 'PGMN3', 'TUPY3', 'VVEO3', 'MELK3', 'SHUL4', 'BRSR6']

    r1, r2 = st.columns([3, 1])
    with r1: escolha_lista = st.selectbox("Escolha a Lista:", ["BDRs Elite (25 ativos)", "IBrX Seleção (93 ativos)", "Ambas as listas"], key="radar_lista_2")
    with r2: radar_tempo = st.selectbox("Tempo Gráfico:", ['60m', '1d', '1wk'], index=1, format_func=lambda x: {'60m':'60 min','1d':'Diário','1wk':'Semanal'}[x], key="radar_tempo_2")
        
    if st.button("🚀 Iniciar Radar Automático", type="primary", use_container_width=True, key="btn_radar_massa_2"):
        lista_ativos = bdrs_elite if "BDRs" in escolha_lista else ibrx_selecao if "IBrX" in escolha_lista else bdrs_elite + ibrx_selecao
        intervalo_tv = {'60m': Interval.in_1_hour, '1d': Interval.in_daily, '1wk': Interval.in_weekly}.get(radar_tempo, Interval.in_daily)
        
        barra_progresso = st.progress(0, text="Iniciando motores...")
        oportunidades = []

        for idx, ativo in enumerate(lista_ativos):
            barra_progresso.progress((idx + 1) / len(lista_ativos), text=f"🔍 Analisando {ativo}...")
            try:
                df = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=150)
                if df is not None and len(df) > 3:
                    df.rename(columns={'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                    pa = df['Close'].iloc[-1]
                    for i in range(2, len(df)):
                        if df['Low'].iloc[i] > df['High'].iloc[i-2]:
                            if df['Low'].iloc[i:].min() > df['High'].iloc[i-2] and (df['High'].iloc[i-2] <= pa <= df['Low'].iloc[i]):
                                oportunidades.append({'Ativo': ativo, 'Sinal': '🟢 COMPRA', 'Cotação': f"R$ {pa:.2f}", 'Zona': f"R$ {df['High'].iloc[i-2]:.2f} - {df['Low'].iloc[i]:.2f}"})
                        if df['High'].iloc[i] < df['Low'].iloc[i-2]:
                            if df['High'].iloc[i:].max() < df['Low'].iloc[i-2] and (df['High'].iloc[i] <= pa <= df['Low'].iloc[i-2]):
                                oportunidades.append({'Ativo': ativo, 'Sinal': '🔴 VENDA', 'Cotação': f"R$ {pa:.2f}", 'Zona': f"R$ {df['High'].iloc[i]:.2f} - {df['Low'].iloc[i-2]:.2f}"})
            except: pass 
            time.sleep(0.05) 
        barra_progresso.empty()
        
        if oportunidades:
            st.success(f"🎯 Encontramos {len(oportunidades)} toque(s) hoje.")
            st.dataframe(pd.DataFrame(oportunidades), use_container_width=True, hide_index=True)
        else: st.warning("Nenhum ativo tocando em Gap no momento.")

# ==========================================
# ABA 3: BACKTEST FINANCEIRO DE FVG
# ==========================================
with aba_backtest:
    st.subheader("Simulador de Estratégia FVG")
    st.markdown("Veja o resultado financeiro operando a favor dos Gaps de Alta. Regra: Compra no toque, Alvo de 2x o Risco.")
    
    b1, b2, b3, b4 = st.columns(4)
    with b1: bk_ativo = st.text_input("Ativo para Backtest:", value="TSLA34").upper()
    with b2: bk_tempo = st.selectbox("Tempo Gráfico:", ['60m', '1d', '1wk'], index=1, format_func=lambda x: {'60m':'60 min','1d':'Diário','1wk':'Semanal'}[x], key="bk_tempo")
    with b3: bk_velas = st.number_input("Histórico (Velas):", value=500, step=100)
    with b4: bk_qtd = st.number_input("Qtd. Ações:", value=100, step=100)

    if st.button("⚙️ Rodar Backtest Financeiro", type="primary", use_container_width=True):
        ativo = bk_ativo.strip().replace('.SA', '')
        intervalo_tv = {'60m': Interval.in_1_hour, '1d': Interval.in_daily, '1wk': Interval.in_weekly}.get(bk_tempo, Interval.in_daily)

        with st.spinner(f"Simulando operações em {ativo}..."):
            try:
                df = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=bk_velas)
                if df is not None and len(df) > 50:
                    df.rename(columns={'high': 'High', 'low': 'Low', 'close': 'Close', 'open': 'Open'}, inplace=True)
                    
                    trades_realizados = []
                    
                    for i in range(2, len(df)-1):
                        if df['Low'].iloc[i] > df['High'].iloc[i-2]:
                            topo = df['Low'].iloc[i]
                            fundo = df['High'].iloc[i-2]
                            
                            preco_entrada = topo 
                            stop_loss = fundo * 0.995 
                            take_profit = preco_entrada + (2 * (preco_entrada - stop_loss)) 
                            
                            entrou = False
                            
                            for j in range(i+1, len(df)):
                                if not entrou:
                                    if df['Low'].iloc[j] <= preco_entrada:
                                        entrou = True
                                        data_entrada = df.index[j]
                                else:
                                    if df['Low'].iloc[j] <= stop_loss:
                                        resultado_fin = (stop_loss - preco_entrada) * bk_qtd
                                        trades_realizados.append({'Data': data_entrada.strftime('%d/%m/%Y'), 'Resultado': '🔴 LOSS', 'Entrada': f"R$ {preco_entrada:.2f}", 'Saída': f"R$ {stop_loss:.2f}", 'Financeiro (R$)': resultado_fin})
                                        break
                                    elif df['High'].iloc[j] >= take_profit:
                                        resultado_fin = (take_profit - preco_entrada) * bk_qtd
                                        trades_realizados.append({'Data': data_entrada.strftime('%d/%m/%Y'), 'Resultado': '🟢 GAIN', 'Entrada': f"R$ {preco_entrada:.2f}", 'Saída': f"R$ {take_profit:.2f}", 'Financeiro (R$)': resultado_fin})
                                        break

                    if trades_realizados:
                        df_trades = pd.DataFrame(trades_realizados)
                        gains = len(df_trades[df_trades['Resultado'] == '🟢 GAIN'])
                        losses = len(df_trades[df_trades['Resultado'] == '🔴 LOSS'])
                        total_trades = gains + losses
                        lucro_total = df_trades['Financeiro (R$)'].sum()
                        
                        if total_trades > 0:
                            taxa_acerto = (gains / total_trades) * 100
                            
                            st.markdown("---")
                            res1, res2, res3, res4, res5, res6 = st.columns(6)
                            res1.metric("Total de Trades", total_trades)
                            res2.metric("Acertos ✅", gains)
                            res3.metric("Erros ❌", losses)
                            res4.metric("Taxa de Acerto", f"{taxa_acerto:.1f}%")
                            res5.metric("Risco/Retorno", "2 para 1")
                            res6.metric("💰 Resultado Final", f"R$ {lucro_total:.2f}")
                            
                            if lucro_total > 0: st.success(f"📈 **Estratégia Lucrativa!** Operando lotes de {bk_qtd} ações, o robô finalizou o período com lucro.")
                            else: st.warning(f"⚠️ **Estratégia no Prejuízo.**")
                            
                            st.write("Histórico Financeiro das Operações:")
                            df_trades_show = df_trades.copy()
                            df_trades_show['Financeiro (R$)'] = df_trades_show['Financeiro (R$)'].apply(lambda x: f"R$ {x:.2f}")
                            
                            def colorir_resultado(val):
                                color = '#d4edda' if 'GAIN' in val else '#f8d7da'
                                text_color = '#155724' if 'GAIN' in val else '#721c24'
                                return f'background-color: {color}; color: {text_color}'
                                
                            st.dataframe(df_trades_show.style.map(colorir_resultado, subset=['Resultado']), use_container_width=True)
                    else: st.info("O robô não encontrou operações que foram fechadas no período.")
                else: st.error("Dados insuficientes.")
            except Exception as e: st.error(f"Erro no backtest: {e}")

# ==========================================
# ABA 4: RADAR SUPREMO (CONFLUÊNCIA 9.1 + FVG)
# ==========================================
with aba_supremo:
    st.subheader("🔥 Radar de Confluência Institucional")
    st.markdown("O Santo Graal: Encontra ativos onde o **Setup 9.1 (MME9 virou para cima)** acabou de acionar **exatamente dentro** de uma zona de suporte institucional (FVG de Alta).")
    
    bdrs_elite_sup = ['NVDC34', 'P2LT34', 'ROXO34', 'INBR32', 'M1TA34', 'TSLA34', 'LILY34', 'AMZO34', 'AURA33', 'GOGL34', 'MSFT34', 'MUTC34', 'MELI34', 'C2OI34', 'ORCL34', 'M2ST34', 'A1MD34', 'NFLX34', 'ITLC34', 'AVGO34', 'COCA34', 'JBSS32', 'AAPL34', 'XPBR31', 'STOC34']
    ibrx_selecao_sup = ['PETR4', 'VALE3', 'ITUB4', 'BBDC4', 'BBAS3', 'B3SA3', 'ABEV3', 'WEGE3', 'AXIA3', 'SUZB3', 'RENT3', 'RADL3', 'EQTL3', 'LREN3', 'PRIO3', 'HAPV3', 'GGBR4', 'VBBR3', 'SBSP3', 'CMIG4', 'CPLE3', 'ENEV3', 'TIMS3', 'TOTS3', 'EGIE3', 'CSAN3', 'ALOS3', 'DIRR3', 'VIVT3', 'KLBN11', 'UGPA3', 'PSSA3', 'CYRE3', 'ASAI3', 'RAIL3', 'ISAE3', 'CSNA3', 'MGLU3', 'EMBJ3', 'TAEE11', 'BBSE3', 'FLRY3', 'MULT3', 'TFCO4', 'LEVE3', 'CPFE3', 'GOAU4', 'MRVE3', 'YDUQ3', 'SMTO3', 'SLCE3', 'CVCB3', 'USIM5', 'BRAP4', 'BRAV3', 'EZTC3', 'PCAR3', 'AUAU3', 'DXCO3', 'CASH3', 'VAMO3', 'AZZA3', 'AURE3', 'BEEF3', 'ECOR3', 'FESA4', 'POMO4', 'CURY3', 'INTB3', 'JHSF3', 'LIGT3', 'LOGG3', 'MDIA3', 'MBRF3', 'NEOE3', 'QUAL3', 'RAPT4', 'ROMI3', 'SANB11', 'SIMH3', 'TEND3', 'VULC3', 'PLPL3', 'CEAB3', 'UNIP6', 'LWSA3', 'BPAC11', 'GMAT3', 'CXSE3', 'ABCB4', 'CSMG3', 'SAPR11', 'GRND3', 'BRAP3', 'LAVV3', 'RANI3', 'ITSA3', 'ALUP11', 'FIQE3', 'COGN3', 'IRBR3', 'SEER3', 'ANIM3', 'JSLG3', 'POSI3', 'MYPK3', 'SOJA3', 'BLAU3', 'PGMN3', 'TUPY3', 'VVEO3', 'MELK3', 'SHUL4', 'BRSR6']

    s1, s2 = st.columns([3, 1])
    with s1: lista_sup = st.selectbox("Escolha a Lista para o Filtro Supremo:", ["BDRs Elite", "IBrX Seleção", "Ambas as listas"], key="supremo_lista")
    with s2: tempo_sup = st.selectbox("Tempo Gráfico:", ['1d', '1wk'], index=0, format_func=lambda x: {'1d':'Diário (Recomendado)','1wk':'Semanal'}[x], key="supremo_tempo")
        
    if st.button("🚨 Caçar Setup Supremo (9.1 + FVG)", type="primary", use_container_width=True, key="btn_supremo"):
        ativos_scan = bdrs_elite_sup if "BDRs" in lista_sup else ibrx_selecao_sup if "IBrX" in lista_sup else bdrs_elite_sup + ibrx_selecao_sup
        interv_sup = {'1d': Interval.in_daily, '1wk': Interval.in_weekly}.get(tempo_sup, Interval.in_daily)
        
        barra = st.progress(0, text="Calculando confluências complexas...")
        achados_supremos = []

        for idx, ativo in enumerate(ativos_scan):
            barra.progress((idx + 1) / len(ativos_scan), text=f"🔥 Cruzando MME9 e Gaps de {ativo}...")
            try:
                df = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=interv_sup, n_bars=150)
                if df is not None and len(df) > 15:
                    df.rename(columns={'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                    
                    df.ta.ema(length=9, append=True)
                    mme9 = df['EMA_9']
                    
                    setup_91_armado = False
                    if (mme9.iloc[-3] >= mme9.iloc[-2]) and (mme9.iloc[-1] > mme9.iloc[-2]):
                        setup_91_armado = True
                    
                    if setup_91_armado:
                        for i in range(2, len(df)-2):
                            if df['Low'].iloc[i] > df['High'].iloc[i-2]:
                                topo = df['Low'].iloc[i]
                                fundo = df['High'].iloc[i-2]
                                
                                if df['Low'].iloc[i:].min() > fundo:
                                    minima_recente = min(df['Low'].iloc[-1], df['Low'].iloc[-2])
                                    
                                    if minima_recente <= topo and minima_recente >= fundo:
                                        
                                        # --- CÁLCULO DE RISCO E ALVO ADICIONADO AQUI ---
                                        entrada = df['High'].iloc[-1]
                                        risco = entrada - fundo
                                        alvo_2x = entrada + (2 * risco)
                                        
                                        achados_supremos.append({
                                            'Ativo': ativo, 
                                            'Gatilho': '🔥 9.1 de COMPRA', 
                                            'Defesa': '🛡️ Dentro do FVG',
                                            'Cotação Atual': f"R$ {df['Close'].iloc[-1]:.2f}",
                                            'Entrada (Máxima)': f"R$ {entrada:.2f}",
                                            'Stop (Fundo FVG)': f"R$ {fundo:.2f}",
                                            '🎯 Alvo (2x Risco)': f"R$ {alvo_2x:.2f}"
                                        })
                                        break
            except: pass 
            time.sleep(0.05) 
            
        barra.empty()
        
        if achados_supremos:
            st.success(f"🎯 **BINGO!** Encontramos {len(achados_supremos)} ativo(s) com a confluência perfeita hoje.")
            st.dataframe(pd.DataFrame(achados_supremos), use_container_width=True, hide_index=True)
            st.info("💡 **Como Operar:** Cadastre no Profit sua ordem de **Compra Start** em 'Entrada', posicione seu **Stop** em 'Stop', e pendure sua saída com lucro em **Alvo**.")
        else: 
            st.warning("Nenhum ativo apresentou a confluência do 9.1 dentro de um FVG hoje. Esse é um setup raro de alta precisão, continue monitorando!")
