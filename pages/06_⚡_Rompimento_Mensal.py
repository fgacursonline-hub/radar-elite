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

st.title("⚡ Radar de Rompimento de Máximas/Fechamentos")
st.markdown("Estratégia: Identificação de fluxo institucional por superação de níveis de períodos anteriores.")
st.divider()

aba_rad_p, aba_raio_x = st.tabs(["📡 Radar (Padrão)", "🔬 Raio-X Individual"])

with aba_rad_p:
    # FILTROS DE ENTRADA
    c1, c2, c3 = st.columns(3)
    with c1: 
        escolha_lista = st.selectbox("Escolha a Lista:", ["BDRs Elite", "IBrX Seleção", "Todos (BDR + IBrX)"], key="r_lst")
        tipo_romp = st.radio("Romper por:", ["Máxima", "Fechamento"], horizontal=True, help="Máxima considera o pavio. Fechamento considera o corpo do candle anterior.")
    with c2:
        tempo_grafico = st.selectbox("Tempo Gráfico:", ["60m", "Diário", "Mensal", "Anual"], index=3, key="r_tmp")
        cap_trade = st.number_input("Capital por Trade (R$):", value=5000, step=500, key="r_cap")
    with c3:
        st.info(f"Critério: Preço Atual > {tipo_romp} do período anterior.")

    if st.button("🚀 Iniciar Radar de Rompimento", type="primary", use_container_width=True):
        lista_ativos = bdrs_elite if escolha_lista == "BDRs Elite" else ibrx_selecao if escolha_lista == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        
        barra = st.progress(0)
        encontrados = []

        for idx, ativo in enumerate(lista_ativos):
            barra.progress((idx + 1) / len(lista_ativos), text=f"🔍 Analisando {ativo}...")
            try:
                # Puxamos dados suficientes para identificar o período anterior fechado
                df_d = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=Interval.in_daily, n_bars=300)
                
                if df_d is not None and len(df_d) > 260:
                    df_d.columns = [c.capitalize() for c in df_d.columns]
                    pa = df_d['Close'].iloc[-1]
                    col_ref = "High" if tipo_romp == "Máxima" else "Close"

                    # DEFINIÇÃO DA REFERÊNCIA (PERÍODO ANTERIOR FECHADO)
                    if tempo_grafico == "Anual":
                        # Máxima ou Fechamento do ano de 2025 (Excluindo 2026)
                        ref_val = df_d[col_ref].iloc[-300:-76].max() 
                    elif tempo_grafico == "Mensal":
                        # Máxima ou Fechamento do mês passado
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
                        qtd_lote = cap_trade // pa
                        
                        encontrados.append({
                            'Ativo': ativo,
                            'Preço Atual': f"R$ {pa:.2f}",
                            f'Ref. {tipo_romp}': f"R$ {ref_val:.2f}",
                            'Resultado': "🟢 LUCRO",
                            'Lucro Real (%)': f"{lucro_real:.2f}%",
                            'Duração': f"{cont_dias} dias úteis",
                            'Lote (Ações)': int(qtd_lote)
                        })
            except: pass
        
        barra.empty()
        if encontrados:
            st.success(f"Encontrados {len(encontrados)} ativos rompidos ({tipo_romp}) no {tempo_grafico}!")
            st.dataframe(pd.DataFrame(encontrados), use_container_width=True, hide_index=True)
        else:
            st.warning(f"Nenhum rompimento de {tipo_romp} detectado.")

with aba_raio_x:
    st.subheader("🔬 Raio-X Individual")
    # ... Lógica do Raio-X aqui ...
