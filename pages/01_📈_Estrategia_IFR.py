import streamlit as st
from tvDatafeed import TvDatafeed, Interval
import pandas as pd
import pandas_ta as ta
import time

# --- 1. CONFIGURAÇÃO E SEGURANÇA ---
st.set_page_config(page_title="Estratégia IFR", layout="wide")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Acesso negado. Faça login na página inicial.")
    st.stop()

# --- 2. CONEXÃO E DADOS ---
@st.cache_resource
def get_tv_connection():
    return TvDatafeed()

tv = get_tv_connection()

bdrs_elite = ['NVDC34.SA', 'P2LT34.SA', 'ROXO34.SA', 'TSLA34.SA', 'AAPL34.SA', 'AMZO34.SA', 'MSFT34.SA'] # Simplificado para teste
ibrx_selecao = ['PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'BBDC4.SA', 'BBAS3.SA'] # Simplificado para teste

tradutor_periodo_nome = {'1mo': '1 Mês', '3mo': '3 Meses', '6mo': '6 Meses', '1y': '1 Ano', '60d': '60 Dias'}
tradutor_intervalo = {'15m': Interval.in_15_minute, '60m': Interval.in_1_hour, '1d': Interval.in_daily}

# --- 3. INTERFACE DE ABAS ---
st.title("📈 Estratégia: IFR (Índice de Força Relativa)")
aba_padrao, aba_pm, aba_stop, aba_individual, aba_futuros = st.tabs([
    "📡 Radar (Padrão)", "📡 Radar (PM)", "🛡️ Alvo & Stop", "🔬 Raio-X Individual", "📉 Raio-X Futuros"
])

# --- 4. ABA 1: RADAR PADRÃO (O QUE VOCÊ QUER AGORA) ---
with aba_padrao:
    st.subheader("📡 Radar Padrão (Entrada Única & Alvo Fixo)")
    
    cp1, cp2, cp3 = st.columns(3)
    with cp1:
        lista_padrao = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção"], key="p_lista")
        ativos_padrao = bdrs_elite if lista_padrao == "BDRs Elite" else ibrx_selecao
    with cp2:
        alvo_padrao = st.number_input("Alvo de Lucro (%):", value=5.0, step=0.5, key="p_alvo")
        ifr_periodo = st.number_input("Período IFR:", value=8, key="p_ifr")
    with cp3:
        capital_padrao = st.number_input("Capital por Trade (R$):", value=10000.0, key="p_cap")
        tempo_padrao = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d'], index=2, key="p_tmp")

    if st.button("🚀 Iniciar Varredura Padrão", type="primary", use_container_width=True):
        ls_sinais, ls_abertos = [], []
        progress = st.progress(0)
        
        for idx, ativo_raw in enumerate(ativos_padrao):
            ativo = ativo_raw.replace('.SA', '')
            progress.progress((idx + 1) / len(ativos_padrao))
            
            try:
                df = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=tradutor_intervalo[tempo_padrao], n_bars=200)
                if df is None: continue
                
                df['IFR'] = ta.rsi(df['close'], length=ifr_periodo)
                df['IFR_Prev'] = df['IFR'].shift(1)
                
                # Lógica de Sinal (Crossover 25)
                hoje = df.iloc[-1]
                ontem = df.iloc[-2]
                
                if ontem['IFR'] < 25 and hoje['IFR'] >= 25:
                    ls_sinais.append({'Ativo': ativo, 'Preço': f"R$ {hoje['close']:.2f}", 'IFR': f"{hoje['IFR']:.2f}"})
            except:
                continue

        st.subheader("🚀 Oportunidades Identificadas")
        if ls_sinais:
            st.dataframe(pd.DataFrame(ls_sinais), use_container_width=True)
        else:
            st.info("Nenhum sinal de entrada no momento.")

# --- AS OUTRAS ABAS FICARÃO VAZIAS POR ENQUANTO PARA NÃO ATRAPALHAR SEU RACIOCÍNIO ---
with aba_pm: st.write("Em breve...")
with aba_stop: st.write("Em breve...")
with aba_individual: st.write("Em breve...")
with aba_futuros: st.write("Em breve...")
