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

# --- Cabeçalho com link para o Manual ---
col_tit, col_man = st.columns([4, 1])
with col_tit:
    st.title("🕳️ Smart Money: Gaps Institucionais (FVG)")
with col_man:
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.link_button("📖 Manual FVG", "https://seusite.com/manual_fvg", use_container_width=True)

st.markdown("Identifique desequilíbrios de preço (vácuos de liquidez) e opere nas zonas defendidas pelos grandes bancos.")
st.divider()

# --- CRIAÇÃO DAS SUB-ABAS ---
aba_individual, aba_radar = st.tabs(["🔍 Raio-X Individual", "📡 Radar de Oportunidades"])

# ==========================================
# ABA 1: RAIO-X INDIVIDUAL
# ==========================================
with aba_individual:
    st.subheader("Análise Detalhada por Ativo")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        lupa_ativo = st.text_input("Ativo (Ex: TSLA34):", value="TSLA34", key="fvg_ativo").upper()
    with c2:
        lupa_tempo = st.selectbox("Tempo Gráfico:", 
                                   ['15m', '60m', '1d', '1wk', '1mo'], 
                                   index=2,
                                   format_func=lambda x: {'15m':'15 min','60m':'60 min','1d':'Diário','1wk':'Semanal','1mo':'Mensal'}[x],
                                   key="fvg_tempo")
    with c3:
        lupa_bars = st.number_input("Qtd. de Velas:", value=300, step=50, key="fvg_velas")

    btn_fvg = st.button("🔍 Escanear Desequilíbrios", type="primary", use_container_width=True, key="btn_fvg_ind")

    if btn_fvg:
        ativo = lupa_ativo.strip().replace('.SA', '') # Limpa o .SA se o usuário digitar
        mapa_intervalos = {'15m': Interval.in_15_minute, '60m': Interval.in_1_hour, '1d': Interval.in_daily, '1wk': Interval.in_weekly, '1mo': Interval.in_monthly}
        intervalo_tv = mapa_intervalos.get(lupa_tempo, Interval.in_daily)

        with st.spinner(f"Caçando Gaps em {ativo}..."):
            try:
                df = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=lupa_bars)
                
                if df is not None and len(df) > 3:
                    df.rename(columns={'high': 'High', 'low': 'Low', 'close': 'Close', 'open': 'Open'}, inplace=True)
                    
                    lista_gaps = []
                    preco_atual = df['Close'].iloc[-1]
                    alerta_oportunidade = False
                    
                    for i in range(2, len(df)):
                        # FVG Alta
                        if df['Low'].iloc[i] > df['High'].iloc[i-2]:
                            topo, fundo = df['Low'].iloc[i], df['High'].iloc[i-2]
                            aberto = df['Low'].iloc[i:].min() > fundo
                            if aberto and (fundo <= preco_atual <= topo): alerta_oportunidade = True
                            lista_gaps.append({'Data': df.index[i].strftime('%d/%m %H:%M'), 'Tipo': 'Alta 🟢', 'Zona': 'Suporte (Demanda)', 'Limite Superior': topo, 'Limite Inferior': fundo, 'Status': "Aberto" if aberto else "Preenchido"})

                        # FVG Baixa
                        if df['High'].iloc[i] < df['Low'].iloc[i-2]:
                            topo, fundo = df['Low'].iloc[i-2], df['High'].iloc[i]
                            aberto = df['High'].iloc[i:].max() < topo
                            if aberto and (fundo <= preco_atual <= topo): alerta_oportunidade = True
                            lista_gaps.append({'Data': df.index[i].strftime('%d/%m %H:%M'), 'Tipo': 'Baixa 🔴', 'Zona': 'Resistência (Oferta)', 'Limite Superior': topo, 'Limite Inferior': fundo, 'Status': "Aberto" if aberto else "Preenchido"})

                    st.subheader(f"📊 Zonas de Desequilíbrio: {ativo}")
                    st.markdown(f"**Cotação Atual:** R$ {preco_atual:.2f}")
                    
                    if alerta_oportunidade:
                        st.error(f"🚨 **OPORTUNIDADE:** O preço atual de {ativo} está exatamente DENTRO de uma zona de Gap Institucional ABERTO! Fique atento a reações nesta faixa.")
                    
                    if lista_gaps:
                        gaps_abertos = [g for g in lista_gaps if g['Status'] == 'Aberto']
                        destaques = gaps_abertos[-3:] if gaps_abertos else lista_gaps[-3:]
                            
                        cols = st.columns(len(destaques))
                        for idx, gap in enumerate(destaques):
                            with cols[idx]:
                                st.markdown(f"### {gap['Tipo']}")
                                st.markdown(f"*{gap['Zona']}*")
                                st.metric("Topo da Zona", f"R$ {gap['Limite Superior']:.2f}")
                                st.metric("Fundo da Zona", f"R$ {gap['Limite Inferior']:.2f}")
                                st.caption(f"Status: **{gap['Status']}** | Detectado: {gap['Data']}")
                        st.divider()
                        df_final = pd.DataFrame(lista_gaps).sort_index(ascending=False)
                        df_final['Limite Superior'] = df_final['Limite Superior'].apply(lambda x: f"R$ {x:.2f}")
                        df_final['Limite Inferior'] = df_final['Limite Inferior'].apply(lambda x: f"R$ {x:.2f}")
                        st.dataframe(df_final, use_container_width=True, hide_index=True)
                    else:
                        st.success("Mercado em equilíbrio. Nenhum Gap relevante encontrado.")
                else:
                    st.error("Ativo não encontrado ou dados insuficientes.")
            except Exception as e:
                st.error(f"Erro no processamento: {e}")

# ==========================================
# ABA 2: RADAR DE OPORTUNIDADES (Com Listas Fixas)
# ==========================================
with aba_radar:
    st.subheader("Varredura em Massa")
    st.markdown("Busque nas listas VIPs quais ativos estão testando as zonas de Gaps Abertos **exatamente agora**.")
    
    # Definição das listas 
    bdrs_elite = ['NVDC34', 'P2LT34', 'ROXO34', 'INBR32', 'M1TA34', 'TSLA34', 'LILY34', 'AMZO34', 'AURA33', 'GOGL34', 'MSFT34', 'MUTC34', 'MELI34', 'C2OI34', 'ORCL34', 'M2ST34', 'A1MD34', 'NFLX34', 'ITLC34', 'AVGO34', 'COCA34', 'JBSS32', 'AAPL34', 'XPBR31', 'STOC34']
    ibrx_selecao = ['PETR4', 'VALE3', 'ITUB4', 'BBDC4', 'BBAS3', 'B3SA3', 'ABEV3', 'WEGE3', 'AXIA3', 'SUZB3', 'RENT3', 'RADL3', 'EQTL3', 'LREN3', 'PRIO3', 'HAPV3', 'GGBR4', 'VBBR3', 'SBSP3', 'CMIG4', 'CPLE3', 'ENEV3', 'TIMS3', 'TOTS3', 'EGIE3', 'CSAN3', 'ALOS3', 'DIRR3', 'VIVT3', 'KLBN11', 'UGPA3', 'PSSA3', 'CYRE3', 'ASAI3', 'RAIL3', 'ISAE3', 'CSNA3', 'MGLU3', 'EMBJ3', 'TAEE11', 'BBSE3', 'FLRY3', 'MULT3', 'TFCO4', 'LEVE3', 'CPFE3', 'GOAU4', 'MRVE3', 'YDUQ3', 'SMTO3', 'SLCE3', 'CVCB3', 'USIM5', 'BRAP4', 'BRAV3', 'EZTC3', 'PCAR3', 'AUAU3', 'DXCO3', 'CASH3', 'VAMO3', 'AZZA3', 'AURE3', 'BEEF3', 'ECOR3', 'FESA4', 'POMO4', 'CURY3', 'INTB3', 'JHSF3', 'LIGT3', 'LOGG3', 'MDIA3', 'MBRF3', 'NEOE3', 'QUAL3', 'RAPT4', 'ROMI3', 'SANB11', 'SIMH3', 'TEND3', 'VULC3', 'PLPL3', 'CEAB3', 'UNIP6', 'LWSA3', 'BPAC11', 'GMAT3', 'CXSE3', 'ABCB4', 'CSMG3', 'SAPR11', 'GRND3', 'BRAP3', 'LAVV3', 'RANI3', 'ITSA3', 'ALUP11', 'FIQE3', 'COGN3', 'IRBR3', 'SEER3', 'ANIM3', 'JSLG3', 'POSI3', 'MYPK3', 'SOJA3', 'BLAU3', 'PGMN3', 'TUPY3', 'VVEO3', 'MELK3', 'SHUL4', 'BRSR6']

    r1, r2 = st.columns([3, 1])
    with r1:
        escolha_lista = st.selectbox("Escolha a Lista de Ativos:", 
                                     options=["BDRs Elite (25 ativos)", "IBrX Seleção (93 ativos)", "Varrer o Mercado Todo (Ambas as listas)"],
                                     key="radar_lista")
    with r2:
        radar_tempo = st.selectbox("Tempo Gráfico:", 
                                   options=['60m', '1d', '1wk'], 
                                   index=1,
                                   format_func=lambda x: {'60m':'60 min (Intraday)','1d':'Diário (Swing)','1wk':'Semanal (Posição)'}[x],
                                   key="radar_tempo")
        
    btn_radar = st.button("🚀 Iniciar Radar Automático", type="primary", use_container_width=True, key="btn_radar_massa")

    if btn_radar:
        if "BDRs Elite" in escolha_lista:
            lista_ativos = bdrs_elite
        elif "IBrX" in escolha_lista:
            lista_ativos = ibrx_selecao
        else:
            lista_ativos = bdrs_elite + ibrx_selecao
            
        total_ativos = len(lista_ativos)
        
        mapa_intervalos = {'60m': Interval.in_1_hour, '1d': Interval.in_daily, '1wk': Interval.in_weekly}
        intervalo_tv = mapa_intervalos.get(radar_tempo, Interval.in_daily)

        st.markdown("---")
        # Barra de progresso correndo com o texto
        barra_progresso = st.progress(0, text="Iniciando motores do Radar...")
        oportunidades_encontradas = []

        for idx, ativo in enumerate(lista_ativos):
            percentual = (idx + 1) / total_ativos
            barra_progresso.progress(percentual, text=f"🔍 Analisando liquidez de {ativo} ({idx+1}/{total_ativos})...")
            
            try:
                df = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=150)
                if df is not None and len(df) > 3:
                    df.rename(columns={'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                    preco_atual = df['Close'].iloc[-1]
                    
                    for i in range(2, len(df)):
                        # FVG ALTA
                        if df['Low'].iloc[i] > df['High'].iloc[i-2]:
                            topo, fundo = df['Low'].iloc[i], df['High'].iloc[i-2]
                            se_aberto = df['Low'].iloc[i:].min() > fundo
                            if se_aberto and (fundo <= preco_atual <= topo):
                                oportunidades_encontradas.append({'Ativo': ativo, 'Sinal': '🟢 COMPRA (Suporte)', 'Cotação': f"R$ {preco_atual:.2f}", 'Topo FVG': f"R$ {topo:.2f}", 'Fundo FVG': f"R$ {fundo:.2f}"})
                        
                        # FVG BAIXA
                        if df['High'].iloc[i] < df['Low'].iloc[i-2]:
                            topo, fundo = df['Low'].iloc[i-2], df['High'].iloc[i]
                            se_aberto = df['High'].iloc[i:].max() < topo
                            if se_aberto and (fundo <= preco_atual <= topo):
                                oportunidades_encontradas.append({'Ativo': ativo, 'Sinal': '🔴 VENDA (Resistência)', 'Cotação': f"R$ {preco_atual:.2f}", 'Topo FVG': f"R$ {topo:.2f}", 'Fundo FVG': f"R$ {fundo:.2f}"})
            except Exception:
                pass 
            
            time.sleep(0.05) 

        barra_progresso.empty()

        if oportunidades_encontradas:
            st.success(f"🎯 **Varredura Concluída!** Encontramos {len(oportunidades_encontradas)} toque(s) em Gaps Institucionais hoje.")
            df_oportunidades = pd.DataFrame(oportunidades_encontradas)
            st.dataframe(df_oportunidades, use_container_width=True, hide_index=True)
            st.info("💡 **Gatilho:** Abra o gráfico destes ativos. Se o seu setup de entrada (ex: 9.1) acionar a favor da zona, o trade tem altíssima probabilidade.")
        else:
            st.warning("Varredura Concluída. Nenhum ativo da lista está dentro de um Gap Institucional neste momento.")
