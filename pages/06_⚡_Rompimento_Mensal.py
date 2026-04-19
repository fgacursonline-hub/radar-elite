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

# Listas Oficiais
bdrs_elite = ['NVDC34', 'P2LT34', 'ROXO34', 'INBR32', 'M1TA34', 'TSLA34', 'LILY34', 'AMZO34', 'AURA33', 'GOGL34', 'MSFT34', 'MUTC34', 'MELI34', 'C2OI34', 'ORCL34', 'M2ST34', 'A1MD34', 'NFLX34', 'ITLC34', 'AVGO34', 'COCA34', 'JBSS32', 'AAPL34', 'XPBR31', 'STOC34']
ibrx_selecao = ['PETR4', 'VALE3', 'ITUB4', 'BBDC4', 'BBAS3', 'B3SA3', 'ABEV3', 'WEGE3', 'AXIA3', 'SUZB3', 'RENT3', 'RADL3', 'EQTL3', 'LREN3', 'PRIO3', 'HAPV3', 'GGBR4', 'VBBR3', 'SBSP3', 'CMIG4', 'CPLE3', 'ENEV3', 'TIMS3', 'TOTS3', 'EGIE3', 'CSAN3', 'ALOS3', 'DIRR3', 'VIVT3', 'KLBN11', 'UGPA3', 'PSSA3', 'CYRE3', 'ASAI3', 'RAIL3', 'ISAE3', 'CSNA3', 'MGLU3', 'EMBJ3', 'TAEE11', 'BBSE3', 'FLRY3', 'MULT3', 'TFCO4', 'LEVE3', 'CPFE3', 'GOAU4', 'MRVE3', 'YDUQ3', 'SMTO3', 'SLCE3', 'CVCB3', 'USIM5', 'BRAP4', 'BRAV3', 'EZTC3', 'PCAR3', 'AUAU3', 'DXCO3', 'CASH3', 'VAMO3', 'AZZA3', 'AURE3', 'BEEF3', 'ECOR3', 'FESA4', 'POMO4', 'CURY3', 'INTB3', 'JHSF3', 'LIGT3', 'LOGG3', 'MDIA3', 'MBRF3', 'NEOE3', 'QUAL3', 'RAPT4', 'ROMI3', 'SANB11', 'SIMH3', 'TEND3', 'VULC3', 'PLPL3', 'CEAB3', 'UNIP6', 'LWSA3', 'BPAC11', 'GMAT3', 'CXSE3', 'ABCB4', 'CSMG3', 'SAPR11', 'GRND3', 'BRAP3', 'LAVV3', 'RANI3', 'ITSA3', 'ALUP11', 'FIQE3', 'COGN3', 'IRBR3', 'SEER3', 'ANIM3', 'JSLG3', 'POSI3', 'MYPK3', 'SOJA3', 'BLAU3', 'PGMN3', 'TUPY3', 'VVEO3', 'MELK3', 'SHUL4', 'BRSR6']

st.title("⚡ Radar de Rompimento de Máximas")
st.markdown("Estratégia baseada na superação da máxima do período anterior (Price Action Institucional).")
st.divider()

# --- Estrutura de Abas do Menu (Padrão IFR/Keltner) ---
aba_rad_p, aba_rad_pm, aba_alvo_st, aba_raio_x = st.tabs([
    "📡 Radar (Padrão)", "📡 Radar (PM)", "🛡️ Alvo & Stop", "🔬 Raio-X Individual"
])

# ==========================================
# 1. RADAR (PADRÃO) - VERSÃO EVOLUÍDA
# ==========================================
with aba_rad_p:
    # ... (Mantenha os campos de seleção: lista, tempo e capital) ...

    if st.button("🚀 Iniciar Radar de Rompimento", type="primary", use_container_width=True):
        lista_ativos = bdrs_elite if escolha_lista == "BDRs Elite" else ibrx_selecao if escolha_lista == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        
        mapa_tempo = {"60m": Interval.in_1_hour, "Diário": Interval.in_daily, "Mensal": Interval.in_monthly, "Anual": Interval.in_monthly}
        intervalo = mapa_tempo[tempo_grafico]
        
        # Aumentamos n_bars para 100 para contar os dias de rompimento
        n_velas = 100 

        barra = st.progress(0, text="Sincronizando...")
        encontrados = []

        for idx, ativo in enumerate(lista_ativos):
            barra.progress((idx + 1) / len(lista_ativos), text=f"🔍 Analisando {ativo}...")
            try:
                df = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo, n_bars=n_velas)
                if df is not None and len(df) >= 20:
                    df.columns = [c.capitalize() for c in df.columns]
                    
                    # 1. Define a Máxima do Período Anterior
                    if tempo_grafico == "Anual":
                        # Aproximação: Máxima dos últimos 12 meses (excluindo o atual)
                        max_referencia = df['High'].iloc[-13:-1].max()
                    else:
                        max_referencia = df['High'].iloc[-2]
                        
                    preco_atual = df['Close'].iloc[-1]
                    
                    # 2. Verifica se está rompido
                    if preco_atual > max_referencia:
                        # --- CÁLCULO DE DIAS/CANDLES ROMPIDOS ---
                        # Conta quantos candles seguidos o Close ficou acima da máxima de referência
                        contador = 0
                        for v in range(len(df)-1, 0, -1):
                            if df['Close'].iloc[v] > max_referencia:
                                contador += 1
                            else:
                                break
                        
                        # --- CÁLCULO DE LUCRO/PREJUÍZO DO SINAL ---
                        # Consideramos que a entrada foi no rompimento exato da máxima
                        preco_entrada = max_referencia
                        resultado_perc = ((preco_atual / preco_entrada) - 1) * 100
                        status_financeiro = "🟢 LUCRO" if resultado_perc > 0 else "🔴 PREJUÍZO"
                        
                        qtd_acoes = cap_trade // preco_atual
                        
                        encontrados.append({
                            'Ativo': ativo,
                            'Preço': f"R$ {preco_atual:.2f}",
                            'Ref. Rompida': f"R$ {max_referencia:.2f}",
                            'Resultado': status_financeiro,
                            'Lucro/Prej (%)': f"{resultado_perc:.2f}%",
                            'Duração': f"{contador} barras",
                            'Lote (Ações)': int(qtd_acoes)
                        })
            except: pass
        
        barra.empty()
        if encontrados:
            st.success(f"Encontrados {len(encontrados)} ativos rompidos no {tempo_grafico}!")
            
            # Formatação da tabela para destacar lucro/prejuízo
            df_final = pd.DataFrame(encontrados)
            
            def colorir_financeiro(val):
                color = '#d4edda' if 'LUCRO' in val else '#f8d7da'
                return f'background-color: {color}'

            st.dataframe(df_final.style.map(colorir_financeiro, subset=['Resultado']), use_container_width=True, hide_index=True)
        else:
            st.warning("Nenhum ativo rompido detectado.")
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
