import streamlit as st
import pandas as pd
from tvDatafeed import TvDatafeed, Interval
import time

# 1. Configuração da Página
st.set_page_config(page_title="Radar de Rompimento", layout="wide", page_icon="⚡")

# Inicializa o TradingView
if 'tv' not in st.session_state:
    st.session_state.tv = TvDatafeed()
tv = st.session_state.tv

# Listas Oficiais (As mesmas que você usa no FVG e IFR)
bdrs_elite = ['NVDC34', 'P2LT34', 'ROXO34', 'INBR32', 'M1TA34', 'TSLA34', 'LILY34', 'AMZO34', 'AURA33', 'GOGL34', 'MSFT34', 'MUTC34', 'MELI34', 'C2OI34', 'ORCL34', 'M2ST34', 'A1MD34', 'NFLX34', 'ITLC34', 'AVGO34', 'COCA34', 'JBSS32', 'AAPL34', 'XPBR31', 'STOC34']
ibrx_selecao = ['PETR4', 'VALE3', 'ITUB4', 'BBDC4', 'BBAS3', 'B3SA3', 'ABEV3', 'WEGE3', 'AXIA3', 'SUZB3', 'RENT3', 'RADL3', 'EQTL3', 'LREN3', 'PRIO3', 'HAPV3', 'GGBR4', 'VBBR3', 'SBSP3', 'CMIG4', 'CPLE3', 'ENEV3', 'TIMS3', 'TOTS3', 'EGIE3', 'CSAN3', 'ALOS3', 'DIRR3', 'VIVT3', 'KLBN11', 'UGPA3', 'PSSA3', 'CYRE3', 'ASAI3', 'RAIL3', 'ISAE3', 'CSNA3', 'MGLU3', 'EMBJ3', 'TAEE11', 'BBSE3', 'FLRY3', 'MULT3', 'TFCO4', 'LEVE3', 'CPFE3', 'GOAU4', 'MRVE3', 'YDUQ3', 'SMTO3', 'SLCE3', 'CVCB3', 'USIM5', 'BRAP4', 'BRAV3', 'EZTC3', 'PCAR3', 'AUAU3', 'DXCO3', 'CASH3', 'VAMO3', 'AZZA3', 'AURE3', 'BEEF3', 'ECOR3', 'FESA4', 'POMO4', 'CURY3', 'INTB3', 'JHSF3', 'LIGT3', 'LOGG3', 'MDIA3', 'MBRF3', 'NEOE3', 'QUAL3', 'RAPT4', 'ROMI3', 'SANB11', 'SIMH3', 'TEND3', 'VULC3', 'PLPL3', 'CEAB3', 'UNIP6', 'LWSA3', 'BPAC11', 'GMAT3', 'CXSE3', 'ABCB4', 'CSMG3', 'SAPR11', 'GRND3', 'BRAP3', 'LAVV3', 'RANI3', 'ITSA3', 'ALUP11', 'FIQE3', 'COGN3', 'IRBR3', 'SEER3', 'ANIM3', 'JSLG3', 'POSI3', 'MYPK3', 'SOJA3', 'BLAU3', 'PGMN3', 'TUPY3', 'VVEO3', 'MELK3', 'SHUL4', 'BRSR6']

st.title("⚡ Radar de Rompimento de Máximas")
st.markdown("Estratégia: Compra na superação da máxima anterior. **Duração** calculada em dias úteis reais.")
st.divider()

# --- Estrutura de Abas do Menu ---
aba_rad_p, aba_rad_pm, aba_alvo_st, aba_raio_x = st.tabs([
    "📡 Radar (Padrão)", "📡 Radar (PM)", "🛡️ Alvo & Stop", "🔬 Raio-X Individual"
])

# ==========================================
# 1. RADAR (PADRÃO)
# ==========================================
with aba_rad_p:
    st.subheader("📡 Varredura de Mercado")
    
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1: 
        escolha_lista = st.selectbox("Escolha a Lista:", ["BDRs Elite", "IBrX Seleção", "Todos (BDR + IBrX)"], key="rad_lst_p")
    with col_f2:
        tempo_grafico = st.selectbox("Tempo Gráfico:", ["60m", "Diário", "Mensal", "Anual"], index=3, key="rad_tmp_p")
    with col_f3:
        cap_trade = st.number_input("Capital por Trade (R$):", value=5000, step=500, key="rad_cap_p")

    if st.button("🚀 Iniciar Radar de Rompimento", type="primary", use_container_width=True):
        lista_ativos = bdrs_elite if escolha_lista == "BDRs Elite" else ibrx_selecao if escolha_lista == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        
        barra = st.progress(0, text="Sincronizando...")
        encontrados = []

        for idx, ativo in enumerate(lista_ativos):
            barra.progress((idx + 1) / len(lista_ativos), text=f"🔍 Analisando {ativo}...")
            try:
                # Puxamos 260 barras diárias para calcular a duração com precisão de dias úteis
                df_d = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=Interval.in_daily, n_bars=260)
                
                if df_d is not None and len(df_d) > 30:
                    df_d.columns = [c.capitalize() for c in df_d.columns]
                    pa = df_d['Close'].iloc[-1]

                    # Define a Máxima de Referência
                    if tempo_grafico == "Anual":
                        max_ref = df_d['High'].iloc[-255:-1].max() # Aprox. 1 ano
                    elif tempo_grafico == "Mensal":
                        max_ref = df_d['High'].iloc[-22:-1].max()  # Aprox. 1 mês
                    elif tempo_grafico == "60m":
                        # Para o 60m, puxamos o próprio intraday para ser fiel ao tempo
                        df_60 = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=Interval.in_1_hour, n_bars=3)
                        df_60.columns = [c.capitalize() for c in df_60.columns]
                        max_ref = df_60['High'].iloc[-2]
                    else:
                        max_ref = df_d['High'].iloc[-2] # Ontem
                        
                    if pa > max_ref:
                        # Contador de Duração em Dias Úteis
                        cont = 0
                        for v in range(len(df_d)-1, -1, -1):
                            if df_d['Close'].iloc[v] > max_ref:
                                cont += 1
                            else:
                                break
                        
                        resultado_perc = ((pa / max_ref) - 1) * 100
                        status_fin = "🟢 LUCRO" if resultado_perc > 0 else "🔴 PREJUÍZO"
                        qtd_lote = cap_trade // pa
                        
                        encontrados.append({
                            'Ativo': ativo,
                            'Preço': f"R$ {pa:.2f}",
                            'Máxima Rompida': f"R$ {max_ref:.2f}",
                            'Resultado': status_fin,
                            'Lucro (%)': f"{resultado_perc:.2f}%",
                            'Duração': f"{cont} dias úteis",
                            'Lote (Ações)': int(qtd_lote)
                        })
            except: pass
        
        barra.empty()
        if encontrados:
            st.success(f"Encontrados {len(encontrados)} ativos rompidos no {tempo_grafico}!")
            df_final = pd.DataFrame(encontrados)
            
            def colorir_res(val):
                color = '#d4edda' if 'LUCRO' in val else '#f8d7da'
                return f'background-color: {color}; color: black'

            st.dataframe(df_final.style.map(colorir_res, subset=['Resultado']), use_container_width=True, hide_index=True)
        else:
            st.warning(f"Nenhum rompimento detectado no {tempo_grafico} no momento.")

# --- As demais abas (Radar PM, Alvo, Raio-X) seguem o mesmo padrão ---
# ==========================================
# 2. RADAR (PM)
# ==========================================
with aba_rad_pm:
    st.subheader("📡 Radar de Preço Médio (Pullback)")
    st.write("Ativos que romperam mas voltaram para 'testar' a zona rompida (0% a 2% de distância).")
    # ... Lógica similar ao Radar Padrão mas filtrando por distância < 2% ...
    st.info("Utilize para entradas mais conservadoras próximas ao suporte.")

# ==========================================
# 3. 🛡️ ALVO & STOP (CALCULADORA)
# ==========================================
with aba_alvo_st:
    st.subheader("🛡️ Calculadora de Gestão")
    c1, c2, c3 = st.columns(3)
    with c1: ent_p = st.number_input("Preço Entrada (R$):", value=20.0)
    with c2: alvo_p = st.number_input("Alvo Desejado (%):", value=15.0)
    with c3: cap_p = st.number_input("Capital total (R$):", value=10000)
    
    v_alvo = ent_p * (1 + (alvo_p/100))
    lucro_estimado = cap_p * (alvo_p/100)
    
    st.divider()
    res1, res2, res3 = st.columns(3)
    res1.metric("🎯 Preço de Saída", f"R$ {v_alvo:.2f}")
    res2.metric("💰 Lucro Previsto", f"R$ {lucro_estimado:.2f}")
    res3.metric("📈 ROI", f"{alvo_p}%")

# ==========================================
# 4. 🔬 RAIO-X INDIVIDUAL
# ==========================================
with aba_raio_x:
    st.subheader("🔬 Análise Técnica Individual")
    at_foco = st.text_input("Ativo para Raio-X:", value="PETR4").upper()
    per_estudo = st.slider("Período de Estudo (Velas):", 10, 100, 30)
    
    if st.button("Analizar Agora"):
        # Puxa o histórico conforme o período de estudo escolhido
        df_x = tv.get_hist(symbol=at_foco, exchange='BMFBOVESPA', interval=intervalo, n_bars=per_estudo)
        if df_x is not None:
            df_x.columns = [c.capitalize() for c in df_x.columns]
            st.line_chart(df_x['Close'])
            st.write(f"Última Máxima: R$ {df_x['High'].iloc[-2]:.2f}")
