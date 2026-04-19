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
# ABA 1: RAIO-X INDIVIDUAL (O que já fizemos)
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
        ativo = lupa_ativo.strip()
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
# ABA 2: RADAR DE OPORTUNIDADES (A Varredura)
# ==========================================
with aba_radar:
    st.subheader("Varredura em Massa")
    st.markdown("Busque em uma lista de ativos quais estão testando as zonas de Gaps Abertos **exatamente agora**.")
    
    r1, r2 = st.columns([3, 1])
    with r1:
        ativos_input = st.text_area("Lista de Ativos (separados por vírgula):", 
                                    value="TSLA34, AAPL34, MSFT34, NVDC34, MELI34, PETR4, VALE3, ITUB4, WEGE3, BBDC4",
                                    help="Cole aqui os códigos que deseja monitorar.", key="radar_ativos")
    with r2:
        radar_tempo = st.selectbox("Tempo Gráfico:", 
                                   options=['60m', '1d', '1wk'], 
                                   index=1,
                                   format_func=lambda x: {'60m':'60 min (Intraday)','1d':'Diário (Swing)','1wk':'Semanal (Posição)'}[x],
                                   key="radar_tempo")
        
    btn_radar = st.button("🚀 Iniciar Varredura do Radar", type="primary", use_container_width=True, key="btn_radar_massa")

    if btn_radar:
        lista_ativos = [ativo.strip().upper() for ativo in ativos_input.split(',') if ativo.strip()]
        total_ativos = len(lista_ativos)
        
        if total_ativos == 0:
            st.warning("Por favor, insira pelo menos um ativo.")
        else:
            mapa_intervalos = {'60m': Interval.in_1_hour, '1d': Interval.in_daily, '1wk': Interval.in_weekly}
            intervalo_tv = mapa_intervalos.get(radar_tempo, Interval.in_daily)

            st.markdown("---")
            texto_status = st.empty()
            barra_progresso = st.progress(0)
            oportunidades_encontradas = []

            for idx, ativo in enumerate(lista_ativos):
                texto_status.text(f"Analisando liquidez de {ativo} ({idx+1}/{total_ativos})...")
                try:
                    df = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=150)
                    if df is not None and len(df) > 3:
                        df.rename(columns={'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                        preco_atual = df['Close'].iloc[-1]
                        
                        for i in range(2, len(df)):
                            # Testa FVG ALTA
                            if df['Low'].iloc[i] > df['High'].iloc[i-2]:
                                topo, fundo = df['Low'].iloc[i], df['High'].iloc[i-2]
                                se_aberto = df['Low'].iloc[i:].min() > fundo
                                if se_aberto and (fundo <= preco_atual <= topo):
                                    oportunidades_encontradas.append({'Ativo': ativo, 'Sinal': '🟢 COMPRA (Suporte)', 'Cotação': f"R$ {preco_atual:.2f}", 'Topo FVG': f"R$ {topo:.2f}", 'Fundo FVG': f"R$ {fundo:.2f}"})
                            
                            # Testa FVG BAIXA
                            if df['High'].iloc[i] < df['Low'].iloc[i-2]:
                                topo, fundo = df['Low'].iloc[i-2], df['High'].iloc[i]
                                se_aberto = df['High'].iloc[i:].max() < topo
                                if se_aberto and (fundo <= preco_atual <= topo):
                                    oportunidades_encontradas.append({'Ativo': ativo, 'Sinal': '🔴 VENDA (Resistência)', 'Cotação': f"R$ {preco_atual:.2f}", 'Topo FVG': f"R$ {topo:.2f}", 'Fundo FVG': f"R$ {fundo:.2f}"})
                except Exception:
                    pass 
                
                barra_progresso.progress((idx + 1) / total_ativos)
                time.sleep(0.1) 

            texto_status.empty()
            barra_progresso.empty()

            if oportunidades_encontradas:
                st.success(f"🎯 **Varredura Concluída!** Encontramos {len(oportunidades_encontradas)} toque(s) em Gaps Institucionais hoje.")
                df_oportunidades = pd.DataFrame(oportunidades_encontradas)
                st.dataframe(df_oportunidades, use_container_width=True, hide_index=True)
                st.info("💡 **Gatilho:** Abra o gráfico destes ativos. Se o seu setup de entrada (ex: 9.1) acionar a favor da zona, o trade tem altíssima probabilidade.")
            else:
                st.warning("Varredura Concluída. Nenhum ativo da lista está dentro de um Gap Institucional neste momento.")
