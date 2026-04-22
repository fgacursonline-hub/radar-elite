import streamlit as st
from tvDatafeed import TvDatafeed, Interval
import pandas as pd
import time
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. SEGURANÇA E CONEXÃO
# ==========================================
if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

@st.cache_resource
def get_tv_connection():
    return TvDatafeed()

tv = get_tv_connection()

# ==========================================
# 2. DICIONÁRIO DE PARIDADES (MATEMÁTICA CORRIGIDA)
# ==========================================
bdr_setup = {
    'NVDC34': {'us': 'NVDA', 'exchange': 'NASDAQ', 'paridade': 48},
    'P2LT34': {'us': 'PLTR', 'exchange': 'NYSE', 'paridade': 1},
    'ROXO34': {'us': 'NU', 'exchange': 'NYSE', 'paridade': 6},
    'INBR32': {'us': 'INTR', 'exchange': 'NASDAQ', 'paridade': 1},
    'M1TA34': {'us': 'META', 'exchange': 'NASDAQ', 'paridade': 28},
    'TSLA34': {'us': 'TSLA', 'exchange': 'NASDAQ', 'paridade': 30},
    'LILY34': {'us': 'LLY', 'exchange': 'NYSE', 'paridade': 30},
    'AMZO34': {'us': 'AMZN', 'exchange': 'NASDAQ', 'paridade': 20},  
    'AURA33': {'us': 'ORA', 'exchange': 'TSX', 'paridade': 1},       
    'GOGL34': {'us': 'GOOGL', 'exchange': 'NASDAQ', 'paridade': 12}, 
    'MSFT34': {'us': 'MSFT', 'exchange': 'NASDAQ', 'paridade': 24},  
    'MUTC34': {'us': 'MU', 'exchange': 'NASDAQ', 'paridade': 6},     # Corrigido o dedo gordo (era 16)
    'MELI34': {'us': 'MELI', 'exchange': 'NASDAQ', 'paridade': 120},
    'C2OI34': {'us': 'COIN', 'exchange': 'NASDAQ', 'paridade': 25},
    'ORCL34': {'us': 'ORCL', 'exchange': 'NYSE', 'paridade': 6},
    'M2ST34': {'us': 'MSTR', 'exchange': 'NASDAQ', 'paridade': 70},  
    'A1MD34': {'us': 'AMD', 'exchange': 'NASDAQ', 'paridade': 8},    
    'NFLX34': {'us': 'NFLX', 'exchange': 'NASDAQ', 'paridade': 50},  
    'ITLC34': {'us': 'INTC', 'exchange': 'NASDAQ', 'paridade': 6},    
    'AVGO34': {'us': 'AVGO', 'exchange': 'NASDAQ', 'paridade': 70},  
    'COCA34': {'us': 'KO', 'exchange': 'NYSE', 'paridade': 6},       
    'JBSS32': {'us': 'JBSAY', 'exchange': 'OTC', 'paridade': 1}, 
    'AAPL34': {'us': 'AAPL', 'exchange': 'NASDAQ', 'paridade': 20},
    'XPBR31': {'us': 'XP', 'exchange': 'NASDAQ', 'paridade': 1},
    'STOC34': {'us': 'STNE', 'exchange': 'NASDAQ', 'paridade': 1}
}

SIMBOLO_DOLAR = 'USDBRL'
EXCHANGE_DOLAR = 'FX_IDC'

def colorir_spread(row):
    col = 'Distorção Alvo (%)' if 'Distorção Alvo (%)' in row else None
    if col:
        try:
            val = float(row[col].replace('%', '').replace('+', ''))
            if val > 1.0: 
                return ['color: #00FF00; font-weight: bold'] * len(row)
            elif val < -1.0: 
                return ['color: #ff4d4d; font-weight: bold'] * len(row)
        except: pass
    return [''] * len(row)

# ==========================================
# 3. INTERFACE
# ==========================================
col_titulo, col_botao = st.columns([4, 1])
with col_titulo:
    st.title("⚖️ Arbitragem de BDRs (Long & Short)")
with col_botao:
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.link_button("⚙️ Checar Paridades", "https://statusinvest.com.br/acoes/eua", use_container_width=True)

aba_oraculo, aba_radar, aba_historico = st.tabs([
    "🔮 Oráculo de Abertura (Gap)", "📡 Radar de Distorção (Tempo Real)", "📉 Arbitragem Histórica (Z-Score)"
])

# ==========================================
# ABA 1: O ORÁCULO DE ABERTURA
# ==========================================
with aba_oraculo:
    st.subheader("🔮 O Oráculo de Abertura (Caçador de Gaps)")
    st.markdown("O robô calcula o preço teórico exato de abertura do BDR com base no Pre-Market americano.")

    btn_oraculo = st.button("🔍 Prever Gaps de Abertura Hoje", type="primary", use_container_width=True, key="btn_oraculo")

    if btn_oraculo:
        resultados_oraculo = []
        p_bar = st.progress(0)
        
        try:
            df_dolar = tv.get_hist(symbol=SIMBOLO_DOLAR, exchange=EXCHANGE_DOLAR, interval=Interval.in_daily, n_bars=2)
            dolar_atual = df_dolar['close'].iloc[-1]
        except:
            dolar_atual = 5.00 
            st.error("Erro ao puxar o Dólar. Usando R$ 5,00 como segurança.")

        for idx, (bdr, info) in enumerate(bdr_setup.items()):
            p_bar.progress((idx + 1) / len(bdr_setup))
            try:
                df_bdr = tv.get_hist(symbol=bdr, exchange='BMFBOVESPA', interval=Interval.in_daily, n_bars=3)
                if df_bdr is None or len(df_bdr) < 2: continue
                fechamento_bdr_ontem = df_bdr['close'].iloc[-1] 

                df_us = tv.get_hist(symbol=info['us'], exchange=info['exchange'], interval=Interval.in_daily, n_bars=2)
                if df_us is None: continue
                cotacao_us_atual = df_us['close'].iloc[-1]

                preco_teorico = (cotacao_us_atual * dolar_atual) / info['paridade']
                gap_esperado = ((preco_teorico / fechamento_bdr_ontem) - 1) * 100

                acao = "Aguardar ⏳"
                if gap_esperado > 1.0: acao = "Comprar Abertura 🟢"
                elif gap_esperado < -1.0: acao = "Vender Abertura 🔴"

                resultados_oraculo.append({
                    'Ativo BDR': bdr,
                    'US Stock Atual': f"$ {cotacao_us_atual:.2f}",
                    'Fechou B3 Ontem': f"R$ {fechamento_bdr_ontem:.2f}",
                    'Preço Justo Abertura': f"R$ {preco_teorico:.2f}",
                    'Distorção Alvo (%)': f"+{gap_esperado:.2f}%" if gap_esperado > 0 else f"{gap_esperado:.2f}%",
                    'Recomendação': acao
                })
            except: pass
            time.sleep(0.05)

        p_bar.empty()
        
        if resultados_oraculo:
            st.divider()
            c1, c2 = st.columns([1, 4])
            c1.metric("Dólar Usado", f"R$ {dolar_atual:.4f}")
            c2.success("Mapeamento concluído com sucesso!")
            
            df_oraculo = pd.DataFrame(resultados_oraculo)
            df_oraculo['Modulo'] = df_oraculo['Distorção Alvo (%)'].apply(lambda x: abs(float(x.replace('%', '').replace('+', ''))))
            df_oraculo = df_oraculo.sort_values(by='Modulo', ascending=False).drop(columns=['Modulo'])
            
            st.dataframe(df_oraculo.style.apply(colorir_spread, axis=1), use_container_width=True, hide_index=True)
        else:
            st.warning("Não foi possível carregar as cotações.")

# ==========================================
# ABA 2: RADAR DE DISTORÇÃO (TEMPO REAL)
# ==========================================
with aba_radar:
    st.subheader("📡 Radar de Distorção (Spread Intraday)")
    st.markdown("Monitorização em tempo real. Identifica falhas no Market Maker da B3 durante o pregão.")

    btn_radar = st.button("📡 Escanear Distorções Agora", type="primary", use_container_width=True, key="btn_radar")

    if btn_radar:
        resultados_radar = []
        p_bar_rad = st.progress(0)
        
        try:
            df_dolar = tv.get_hist(symbol=SIMBOLO_DOLAR, exchange=EXCHANGE_DOLAR, interval=Interval.in_15_minute, n_bars=2)
            dolar_atual = df_dolar['close'].iloc[-1]
        except:
            dolar_atual = 5.00

        for idx, (bdr, info) in enumerate(bdr_setup.items()):
            p_bar_rad.progress((idx + 1) / len(bdr_setup))
            try:
                df_bdr = tv.get_hist(symbol=bdr, exchange='BMFBOVESPA', interval=Interval.in_15_minute, n_bars=2)
                if df_bdr is None: continue
                cotacao_bdr = df_bdr['close'].iloc[-1]

                df_us = tv.get_hist(symbol=info['us'], exchange=info['exchange'], interval=Interval.in_15_minute, n_bars=2)
                if df_us is None: continue
                cotacao_us = df_us['close'].iloc[-1]

                preco_teorico = (cotacao_us * dolar_atual) / info['paridade']
                spread = ((preco_teorico / cotacao_bdr) - 1) * 100

                acao = "Aguardar ⏳"
                if spread > 1.0: acao = "Comprar BDR (Barato) 🟢"
                elif spread < -1.0: acao = "Vender BDR (Caro) 🔴"

                resultados_radar.append({
                    'Ativo BDR': bdr,
                    'BDR na B3': f"R$ {cotacao_bdr:.2f}",
                    'US Stock': f"$ {cotacao_us:.2f}",
                    'Preço Teórico': f"R$ {preco_teorico:.2f}",
                    'Distorção Alvo (%)': f"+{spread:.2f}%" if spread > 0 else f"{spread:.2f}%",
                    'Recomendação': acao
                })
            except: pass
            time.sleep(0.05)

        p_bar_rad.empty()
        
        if resultados_radar:
            st.divider()
            c1, c2 = st.columns([1, 4])
            c1.metric("Dólar Atual", f"R$ {dolar_atual:.4f}")
            c2.info("Valores Positivos (+): O preço da B3 está abaixo do justo (Comprar). Valores Negativos (-): A B3 está cara demais (Vender).")
            
            df_rad = pd.DataFrame(resultados_radar)
            df_rad['Modulo'] = df_rad['Distorção Alvo (%)'].apply(lambda x: abs(float(x.replace('%', '').replace('+', ''))))
            df_rad = df_rad.sort_values(by='Modulo', ascending=False).drop(columns=['Modulo'])
            
            st.dataframe(df_rad.style.apply(colorir_spread, axis=1), use_container_width=True, hide_index=True)

# ==========================================
# ABA 3: ARBITRAGEM HISTÓRICA (Z-SCORE)
# ==========================================
with aba_historico:
    st.subheader("📉 Arbitragem Histórica (Z-Score & Mean Reversion)")
    st.markdown("O robô calcula o *Ratio* diário dos últimos 250 dias e extrai o **Z-Score**. Se o Z-Score passar de +2.0 ou cair de -2.0, o elástico estatístico estourou.")

    c_h1, c_h2, c_h3 = st.columns(3)
    with c_h1:
        ativo_hist = st.selectbox("Selecione o BDR:", list(bdr_setup.keys()), key="hist_ativo")
    with c_h2:
        zscore_alvo = st.number_input("Gatilho Z-Score (+/-):", value=2.0, step=0.1, key="hist_z")
    with c_h3:
        periodo_z = st.number_input("Janela Móvel (Dias):", value=20, step=1, key="hist_jan")

    btn_historico = st.button("🔬 Extrair Raio-X Estatístico", type="primary", use_container_width=True, key="btn_hist")

    if btn_historico:
        info_ativo = bdr_setup[ativo_hist]
        
        with st.spinner(f"Sincronizando fuso horário das bolsas para {ativo_hist}..."):
            try:
                df_b3 = tv.get_hist(symbol=ativo_hist, exchange='BMFBOVESPA', interval=Interval.in_daily, n_bars=300)
                df_ny = tv.get_hist(symbol=info_ativo['us'], exchange=info_ativo['exchange'], interval=Interval.in_daily, n_bars=300)
                df_usd = tv.get_hist(symbol=SIMBOLO_DOLAR, exchange=EXCHANGE_DOLAR, interval=Interval.in_daily, n_bars=300)

                if df_b3 is None or df_ny is None or df_usd is None:
                    st.error("Dados insuficientes retornados pela API.")
                    st.stop()

                df_b3 = df_b3[['close']].rename(columns={'close': 'BDR_Close'})
                df_ny = df_ny[['close']].rename(columns={'close': 'US_Close'})
                df_usd = df_usd[['close']].rename(columns={'close': 'BRL_Close'})

                # A MÁGICA DA SINCRONIZAÇÃO: Cortamos as horas e deixamos só o Dia, removendo fusos conflitantes.
                df_b3.index = pd.to_datetime(df_b3.index).tz_localize(None).normalize()
                df_ny.index = pd.to_datetime(df_ny.index).tz_localize(None).normalize()
                df_usd.index = pd.to_datetime(df_usd.index).tz_localize(None).normalize()

                # Limpamos dias repetidos caso existam
                df_b3 = df_b3[~df_b3.index.duplicated(keep='last')]
                df_ny = df_ny[~df_ny.index.duplicated(keep='last')]
                df_usd = df_usd[~df_usd.index.duplicated(keep='last')]

                # Juntamos as tabelas cruzando exatamente os dias em que houve pregão simultâneo no BR e EUA
                df_master = df_b3.join(df_ny, how='inner').join(df_usd, how='inner')
                
                if df_master.empty:
                    st.error("As datas não bateram entre as bolsas. Impossível gerar o cruzamento de histórico.")
                    st.stop()

                df_master['Preco_Teorico'] = (df_master['US_Close'] * df_master['BRL_Close']) / info_ativo['paridade']
                df_master['Ratio'] = df_master['BDR_Close'] / df_master['Preco_Teorico']

                df_master['Ratio_Mean'] = df_master['Ratio'].rolling(window=periodo_z).mean()
                df_master['Ratio_Std'] = df_master['Ratio'].rolling(window=periodo_z).std()
                df_master['Z-Score'] = (df_master['Ratio'] - df_master['Ratio_Mean']) / df_master['Ratio_Std']
                
                df_master = df_master.dropna()

                z_atual = df_master['Z-Score'].iloc[-1]
                ratio_atual = df_master['Ratio'].iloc[-1]

                st.divider()
                st.markdown(f"### 📊 Estatística Quanti de {ativo_hist} vs {info_ativo['us']}")
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("BDR Atual", f"R$ {df_master['BDR_Close'].iloc[-1]:.2f}")
                m2.metric("Preço Justo (Teórico)", f"R$ {df_master['Preco_Teorico'].iloc[-1]:.2f}")
                
                if z_atual > zscore_alvo: 
                    m3.metric("Z-Score Atual", f"{z_atual:.2f}", delta="Estourado para Cima (Venda BDR)", delta_color="inverse")
                elif z_atual < -zscore_alvo: 
                    m3.metric("Z-Score Atual", f"{z_atual:.2f}", delta="Estourado para Baixo (Compre BDR)")
                else: 
                    m3.metric("Z-Score Atual", f"{z_atual:.2f}", delta="Dentro da Normalidade", delta_color="off")
                
                m4.metric("Ratio Base", f"{ratio_atual:.4f}")

                st.markdown("#### 🌊 Oscilador Z-Score (Desvios da Média)")
                
                df_chart = df_master[['Z-Score']].copy()
                df_chart['Limite Superior'] = zscore_alvo
                df_chart['Limite Inferior'] = -zscore_alvo
                df_chart['Média (Zero)'] = 0.0
                
                st.line_chart(df_chart, color=["#4da6ff", "#ff4d4d", "#00FF00", "#ffffff"])

            except Exception as e:
                st.error(f"Erro inesperado no processamento: {e}")
