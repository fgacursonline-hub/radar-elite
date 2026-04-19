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

st.title("⚡ Radar de Rompimento de Máximas")
st.markdown("Foco: Rompimento de Topos Históricos e Períodos Fechados.")
st.divider()

# Removidas as abas Alvo e PM conforme solicitado
aba_rad_p, aba_raio_x = st.tabs(["📡 Radar (Padrão)", "🔬 Raio-X Individual"])

with aba_rad_p:
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1: 
        escolha_lista = st.selectbox("Escolha a Lista:", ["BDRs Elite", "IBrX Seleção", "Todos (BDR + IBrX)"], key="r_list_final")
    with col_f2:
        tempo_grafico = st.selectbox("Tempo Gráfico:", ["60m", "Diário", "Mensal", "Anual"], index=3, key="r_time_final")
    with col_f3:
        cap_trade = st.number_input("Capital por Trade (R$):", value=5000, step=500, key="r_cap_final")

    if st.button("🚀 Iniciar Radar de Rompimento", type="primary", use_container_width=True):
        lista_ativos = bdrs_elite if escolha_lista == "BDRs Elite" else ibrx_selecao if escolha_lista == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        
        barra = st.progress(0, text="Calculando rompimentos...")
        encontrados = []

        for idx, ativo in enumerate(lista_ativos):
            barra.progress((idx + 1) / len(lista_ativos), text=f"🔍 Analisando {ativo}...")
            try:
                # Puxamos dados diários para o cálculo de duração e lucro preciso
                df_d = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=Interval.in_daily, n_bars=300)
                
                if df_d is not None and len(df_d) > 260:
                    df_d.columns = [c.capitalize() for c in df_d.columns]
                    pa = df_d['Close'].iloc[-1]

                    # CORREÇÃO DA LÓGICA DE MÁXIMA (Pega o período fechado anterior)
                    if tempo_grafico == "Anual":
                        # Máxima de 2025 (Exclui os dias de 2026)
                        # Buscamos a máxima do ano anterior real
                        max_ref = df_d['High'].iloc[-300:-75].max() # Ajuste para pegar o topo do ano passado
                    elif tempo_grafico == "Mensal":
                        max_ref = df_d['High'].iloc[-45:-21].max()  # Máxima do mês anterior fechado
                    else:
                        max_ref = df_d['High'].iloc[-2] # Máxima de ontem
                        
                    if pa > max_ref:
                        # Contagem de dias desde que cruzou a linha pela primeira vez
                        cont_dias = 0
                        for v in range(len(df_d)-1, -1, -1):
                            if df_d['High'].iloc[v] > max_ref:
                                cont_dias += 1
                            else:
                                break
                        
                        lucro_real = ((pa / max_ref) - 1) * 100
                        qtd_lote = cap_trade // pa
                        
                        encontrados.append({
                            'Ativo': ativo,
                            'Preço Atual': f"R$ {pa:.2f}",
                            'Topo Rompido': f"R$ {max_ref:.2f}",
                            'Resultado': "🟢 LUCRO",
                            'Lucro Real (%)': f"{lucro_real:.2f}%",
                            'Duração': f"{cont_dias} dias úteis",
                            'Lote (Ações)': int(qtd_lote)
                        })
            except: pass
        
        barra.empty()
        if encontrados:
            st.success(f"Encontrados {len(encontrados)} ativos rompidos no {tempo_grafico}!")
            st.dataframe(pd.DataFrame(encontrados), use_container_width=True, hide_index=True)
        else:
            st.warning("Nenhum ativo rompendo o topo anterior.")

with aba_raio_x:
    st.subheader("🔬 Análise de Gráfico")
    # Código simplificado para visualização rápida
