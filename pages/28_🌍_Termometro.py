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
st.markdown("Análise comparativa de humor e rastro institucional.")

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
        if isinstance(ibov.columns, pd.MultiIndex):
            fechamentos = ibov['Close']['^BVSP']
        else:
            fechamentos = ibov['Close']
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
    st.markdown(f"<h3 style='text-align: center; margin-bottom: -20px;'>🇺🇸 EUA (Fear & Greed)</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: gray;'>{status_us}</p>", unsafe_allow_html=True)
    fig_us = go.Figure(go.Indicator(
        mode = "gauge+number", value = score_us,
        gauge = {
            'axis': {'range': [0, 100]},
            'steps': [
                {'range': [0, 25], 'color': "#ff4d4d"}, {'range': [25, 45], 'color': "#ff9933"},
                {'range': [45, 55], 'color': "#ffcc00"}, {'range': [55, 75], 'color': "#99cc33"},
                {'range': [75, 100], 'color': "#33cc33"}
            ],
            'bar': {'color': "white", 'thickness': 0.25}
        }
    ))
    fig_us.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={'color': "white"}, height=220, margin=dict(l=50, r=50, t=0, b=0))
    st.plotly_chart(fig_us, use_container_width=True, config={'displayModeBar': False})

with col_br:
    st.markdown(f"<h3 style='text-align: center; margin-bottom: -20px;'>🇧🇷 Brasil (IFR B3)</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: gray;'>{status_br}</p>", unsafe_allow_html=True)
    fig_br = go.Figure(go.Indicator(
        mode = "gauge+number", value = score_br,
        gauge = {
            'axis': {'range': [0, 100]},
            'steps': [
                {'range': [0, 30], 'color': "#ff4d4d"}, {'range': [30, 45], 'color': "#ff9933"},
                {'range': [45, 55], 'color': "#ffcc00"}, {'range': [55, 70], 'color': "#99cc33"},
                {'range': [70, 100], 'color': "#33cc33"}
            ],
            'bar': {'color': "white", 'thickness': 0.25}
        }
    ))
    fig_br.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={'color': "white"}, height=220, margin=dict(l=50, r=50, t=0, b=0))
    st.plotly_chart(fig_br, use_container_width=True, config={'displayModeBar': False})

# ==========================================
# 🗺️ MAPAS DE CALOR SETORIAIS
# ==========================================
st.divider()
st.subheader("🗺️ Mapas de Calor Setoriais")
tab_br, tab_eua = st.tabs(["🇧🇷 Ibovespa (B3)", "🇺🇸 S&P 500 (Wall Street)"])

with tab_br:
    html_heatmap_br = """
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-stock-heatmap.js" async>
      {
        "exchanges": ["BMFBOVESPA"],
        "dataSource": "IBOV",
        "grouping": "sector",
        "blockSize": "market_cap_basic",
        "blockColor": "change",
        "locale": "br",
        "colorTheme": "dark",
        "hasTopBar": false,
        "isDataSetEnabled": false,
        "isZoomEnabled": true,
        "hasSymbolTooltip": true,
        "width": "100%",
        "height": 550
      }
      </script>
    </div>"""
    components.html(html_heatmap_br, height=550)

with tab_eua:
    html_heatmap_eua = """
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-stock-heatmap.js" async>
      {
        "exchanges": [],
        "dataSource": "SPX500",
        "grouping": "sector",
        "blockSize": "market_cap_basic",
        "blockColor": "change",
        "locale": "br",
        "colorTheme": "dark",
        "hasTopBar": false,
        "isDataSetEnabled": false,
        "isZoomEnabled": true,
        "hasSymbolTooltip": true,
        "width": "100%",
        "height": 550
      }
      </script>
    </div>"""
    components.html(html_heatmap_eua, height=550)

# ==========================================
# 🐋 FLUXO INSTITUCIONAL (DOWNLOAD B3)
# ==========================================
st.divider()
st.subheader("🐋 Fluxo Institucional (Rastro do Gringo)")
col_g1, col_g2 = st.columns([2,1])
with col_g1:
    st.info("📊 **Relatório Oficial de Dados de Mercado**\nBaixe o CSV consolidado da B3 para analisar o saldo de estrangeiros, institucionais e pessoa física.")
    st.link_button("📥 Baixar Planilha de Fluxo B3 (.csv)", "https://sistemaswebb3-listados.b3.com.br/marketDataProxy/MarketDataCall/GetDownloadMarketData/RELATORIO_DADOS_DE_MERCADO.csv", use_container_width=True)
with col_g2:
    st.warning("⚠️ **Atenção:** Os dados oficiais possuem atraso de **D+2** (dois dias úteis).")

# ==========================================
# 🩸 RADAR DE ALUGUEL E SHORT SQUEEZE
# ==========================================
st.divider()
st.subheader("🩸 Radar de Aluguel e Short Squeeze")
ativos = sorted(["MGLU3", "PETR4", "VALE3", "ITUB4", "BBAS3", "COGN3", "BHIA3", "AZUL4", "EMBR3", "PRIO3", "CVCB3", "LREN3"])

c1, c2 = st.columns([2, 1], vertical_alignment="bottom")
with c1:
    ativo_alvo = st.selectbox("Selecione o Ativo:", options=ativos, key="aluguel_ticker")
with c2:
    btn_investigar = st.button("🔍 Investigar", use_container_width=True, type="primary")

if btn_investigar:
    st.markdown(f"### 📊 Dossiê: {ativo_alvo}")
    url_si = f"https://statusinvest.com.br/acoes/{ativo_alvo.lower()}#:~:text=ALUGUEL%20DE%20AÇÕES"
    col_i1, col_i2 = st.columns(2)
    with col_i1:
        st.info("📉 **Acesso aos Dados**\nRole a página até o quadro verde de Aluguel.")
        st.link_button(f"🚀 Abrir Painel de {ativo_alvo}", url=url_si, use_container_width=True)
    with col_i2:
        st.error("💣 **Risco de Squeeze**\nConfira a Taxa do Tomador (Média).")
        st.link_button(f"📈 Gráfico {ativo_alvo}", url=f"https://br.tradingview.com/chart/?symbol=BMFBOVESPA%3A{ativo_alvo}", use_container_width=True)

    st.markdown("""
    | Taxa Tomador | Status | Significado |
    | :--- | :--- | :--- |
    | **0% a 7%** | Atenção | Institucionais montando venda. |
    | **7% a 15%** | Alerta Urso | Pessimismo elevado. |
    | **> 15%** | **BARRIL DE PÓLVORA** | **Foco em COMPRA (Squeeze).** |
    """)
    st.success(f"🎯 **Tática:** Em 'Barril de Pólvora', a subida é explosiva. O stop dos vendidos vira combustível para sua compra.")
