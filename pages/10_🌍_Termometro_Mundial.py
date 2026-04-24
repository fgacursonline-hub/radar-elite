import streamlit as st
import plotly.graph_objects as go
import requests
import streamlit.components.v1 as components
import pandas as pd
import yfinance as yf

# ==========================================
# 1. SEGURANÇA E CONFIGURAÇÃO
# ==========================================
st.set_page_config(page_title="Termômetro Mundial", layout="wide", page_icon="🌍")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

st.title("🌍 Termômetro de Sentimento")
st.markdown("Compare o humor de Wall Street com a força do Ibovespa em tempo real.")

# ==========================================
# 🧠 FUNÇÕES DE CAPTURA (USA & BR)
# ==========================================

@st.cache_data(ttl=1800)
def buscar_fear_and_greed():
    url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        data = r.json()
        score = int(data['fear_and_greed']['score'])
        rating = data['fear_and_greed']['rating'].title()
        tradutor = {
            "Extreme Fear": "Pânico 🩸", "Fear": "Medo 🔴", "Neutral": "Neutro 🟡",
            "Greed": "Ganância 🟢", "Extreme Greed": "Euforia 🚀"
        }
        return score, tradutor.get(rating, rating)
    except:
        return 50, "Indisponível"

@st.cache_data(ttl=3600)
def calcular_sentimento_brasil():
    try:
        ibov = yf.download("^BVSP", period="60d", interval="1d", progress=False)
        if ibov.empty: return 50, "B3 sem dados"
        
        # Limpeza de colunas (correção do erro de processamento)
        if isinstance(ibov.columns, pd.MultiIndex):
            fechamentos = ibov['Close']['^BVSP']
        else:
            fechamentos = ibov['Close']

        # Cálculo do IFR (RSI) Seguro
        delta = fechamentos.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        score_br = int(rsi.dropna().iloc[-1])
        if score_br >= 70: status = "Euforia 🚀"
        elif score_br >= 60: status = "Ganância 🟢"
        elif score_br >= 40: status = "Neutro 🟡"
        elif score_br >= 30: status = "Medo 🔴"
        else: status = "Pânico 🩸"
        return score_br, status
    except:
        return 50, "Erro B3"

# ==========================================
# 📊 EXIBIÇÃO LADO A LADO (GAUGES)
# ==========================================
st.divider()
score_us, status_us = buscar_fear_and_greed()
score_br, status_br = calcular_sentimento_brasil()

col_us, col_br = st.columns(2)

with col_us:
    fig_us = go.Figure(go.Indicator(
        mode = "gauge+number", value = score_us,
        title = {'text': f"🇺🇸 Wall Street (F&G)<br><span style='font-size:0.8em;color:gray'>{status_us}</span>"},
        gauge = {
            'axis': {'range': [0, 100]},
            'steps': [
                {'range': [0, 25], 'color': "#ff4d4d"}, {'range': [25, 45], 'color': "#ff9933"},
                {'range': [45, 55], 'color': "#ffcc00"}, {'range': [55, 75], 'color': "#99cc33"},
                {'range': [75, 100], 'color': "#33cc33"}
            ],
            'bar': {'color': "white", 'thickness': 0.2}
        }
    ))
    fig_us.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={'color': "white"}, height=300, margin=dict(l=30, r=30, t=50, b=20))
    st.plotly_chart(fig_us, use_container_width=True)

with col_br:
    fig_br = go.Figure(go.Indicator(
        mode = "gauge+number", value = score_br,
        title = {'text': f"🇧🇷 Ibovespa (IFR)<br><span style='font-size:0.8em;color:gray'>{status_br}</span>"},
        gauge = {
            'axis': {'range': [0, 100]},
            'steps': [
                {'range': [0, 30], 'color': "#ff4d4d"}, {'range': [30, 45], 'color': "#ff9933"},
                {'range': [45, 55], 'color': "#ffcc00"}, {'range': [55, 70], 'color': "#99cc33"},
                {'range': [70, 100], 'color': "#33cc33"}
            ],
            'bar': {'color': "white", 'thickness': 0.2}
        }
    ))
    fig_br.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={'color': "white"}, height=300, margin=dict(l=30, r=30, t=50, b=20))
    st.plotly_chart(fig_br, use_container_width=True)

# ==========================================
# 🗺️ MAPAS DE CALOR SETORIAIS
# ==========================================
st.divider()
st.subheader("🗺️ Mapas de Calor Setoriais")
tab_br, tab_eua = st.tabs(["🇧🇷 Ibovespa (B3)", "🇺🇸 S&P 500 (Wall Street)"])

with tab_br:
    html_heatmap_br = """
    <div class="tradingview-widget-container"><script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-stock-heatmap.js" async>
    {"exchanges":["BMFBOVESPA"],"dataSource":"IBOV","grouping":"sector","blockSize":"market_cap_basic","blockColor":"change","locale":"br","colorTheme":"dark","width":"100%","height":"100%"}
    </script></div>"""
    components.html(html_heatmap_br, height=550)

with tab_eua:
    html_heatmap_eua = """
    <div class="tradingview-widget-container"><script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-stock-heatmap.js" async>
    {"exchanges":[],"dataSource":"SPX500","grouping":"sector","blockSize":"market_cap_basic","blockColor":"change","locale":"br","colorTheme":"dark","width":"100%","height":"100%"}
    </script></div>"""
    components.html(html_heatmap_eua, height=550)

# ==========================================
# 🩸 RADAR DE ALUGUEL E SHORT SQUEEZE
# ==========================================
st.divider()
st.subheader("🩸 Radar de Aluguel e Short Squeeze")

ativos_cadastrados = sorted(["MGLU3", "PETR4", "VALE3", "ITUB4", "BBAS3", "COGN3", "BHIA3", "AZUL4", "EMBR3", "PRIO3"])

c1, c2 = st.columns([2, 1], vertical_alignment="bottom")
with c1:
    ativo_alvo = st.selectbox("Selecione o Ativo:", options=ativos_cadastrados, key="aluguel_ticker")
with c2:
    btn_investigar = st.button("🔍 Investigar", use_container_width=True, type="primary")

if btn_investigar:
    st.markdown(f"### 📊 Dossiê: {ativo_alvo}")
    url_si = f"https://statusinvest.com.br/acoes/{ativo_alvo.lower()}#:~:text=ALUGUEL%20DE%20AÇÕES"
    
    col_i1, col_i2 = st.columns(2)
    with col_i1:
        st.info("📉 **Dados de Empréstimo B3**\nRole até o final para ver o quadro de Aluguel.")
        st.link_button(f"🚀 Abrir Painel de {ativo_alvo}", url=url_si, use_container_width=True)
    with col_i2:
        st.error("💣 **Risco de Short Squeeze**\nFoco na Taxa do Tomador. Se estiver subindo, o prejuízo dos vendidos aumenta.")
        st.link_button(f"📈 Ver Gráfico {ativo_alvo}", url=f"https://br.tradingview.com/chart/?symbol=BMFBOVESPA%3A{ativo_alvo}", use_container_width=True)

    st.markdown("""
    | Taxa Tomador | Status | Ação do Caçador |
    | :--- | :--- | :--- |
    | **0% a 7%** | Atenção | Institucionais vendendo. Cuidado com compras. |
    | **7% a 15%** | Alerta Urso | Pessimismo elevado. Monitorar reversão. |
    | **> 15%** | **BARRIL DE PÓLVORA** | **Foco em COMPRA (Short Squeeze).** |
    """)
    st.warning("🚀 **Barril de Pólvora:** Indica energia acumulada para subida violenta. Vendidos serão forçados a comprar para fechar posição.")
