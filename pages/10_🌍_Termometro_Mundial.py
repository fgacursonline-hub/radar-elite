import streamlit as st
import plotly.graph_objects as go
import requests
import streamlit.components.v1 as components
import pandas as pd

# ==========================================
# 1. SEGURANÇA E CONFIGURAÇÃO
# ==========================================
st.set_page_config(page_title="Termômetro Mundial", layout="wide", page_icon="🌍")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

st.title("🌍 Termômetro Mundial")
st.markdown("Sua central de inteligência macroeconômica e sentimento de mercado.")

# ==========================================
# 🧠 TERMÔMETRO INSTITUCIONAL (FEAR & GREED)
# ==========================================
st.divider()
st.subheader("🧠 Medo & Ganância (Fear & Greed Index)")
st.markdown("Identifique extremos emocionais do mercado americano para alinhar sua tática de entrada e saída.")

@st.cache_data(ttl=1800) # Atualiza a cada 30 minutos
def buscar_fear_and_greed():
    url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        data = r.json()
        score = int(data['fear_and_greed']['score'])
        rating = data['fear_and_greed']['rating'].title()
        
        tradutor = {
            "Extreme Fear": "Pânico Extremo 🩸",
            "Fear": "Medo 🔴",
            "Neutral": "Neutro 🟡",
            "Greed": "Ganância 🟢",
            "Extreme Greed": "Euforia Extrema 🚀"
        }
        rating_pt = tradutor.get(rating, rating)
        
        return score, rating_pt
    except:
        return 50, "Dados Indisponíveis"

score_fg, rating_fg = buscar_fear_and_greed()

# Velocímetro de Elite
fig = go.Figure(go.Indicator(
    mode = "gauge+number",
    value = score_fg,
    domain = {'x': [0, 1], 'y': [0, 1]},
    title = {'text': f"<b>Status Atual do Mercado:</b><br><span style='font-size:0.8em;color:gray'>{rating_fg}</span>"},
    gauge = {
        'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "white"},
        'bar': {'color': "rgba(255, 255, 255, 0.4)", 'thickness': 0.25}, 
        'bgcolor': "rgba(0,0,0,0)",
        'steps': [
            {'range': [0, 25], 'color': "#ff4d4d"},   
            {'range': [25, 45], 'color': "#ff9933"},  
            {'range': [45, 55], 'color': "#ffcc00"},  
            {'range': [55, 75], 'color': "#99cc33"},  
            {'range': [75, 100], 'color': "#33cc33"}  
        ],
        'threshold': {
            'line': {'color': "white", 'width': 4},
            'thickness': 0.75,
            'value': score_fg
        }
    }
))

fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={'color': "white"}, height=350, margin=dict(l=20, r=20, t=50, b=20))

col_vazio1, col_gauge, col_vazio2 = st.columns([1, 2, 1])
with col_gauge:
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

with st.expander("📖 Como interpretar o Termômetro?", expanded=False):
    st.markdown("""
    O índice mede a emoção predominante em Wall Street. O dinheiro inteligente usa esses extremos para operar contra a manada:
    
    * 🩸 **0 a 25 (Pânico Extremo):** O mercado está em liquidação e o varejo está vendendo por desespero. Historicamente, é a zona de suporte máxima. **Foco em gatilhos de COMPRA.**
    * 🔴 **25 a 45 (Medo):** A incerteza domina e os preços sofrem pressão vendedora. Tubarões começam a montar posições silenciosamente.
    * 🟡 **45 a 55 (Neutro):** Mercado sem convicção clara, lateralizado. Momento de cautela.
    * 🟢 **55 a 75 (Ganância):** Otimismo e fluxo constante de capital entrando. Excelente momento para surfar tendências.
    * 🚀 **75 a 100 (Euforia Extrema):** O varejo está comprando topo agressivamente com medo de ficar de fora (FOMO). **Foco em proteção de lucros ou gatilhos de VENDA.**
    """)

# ==========================================
# 🗺️ MAPAS DE CALOR GLOBAIS (TRADINGVIEW)
# ==========================================
st.divider()
st.subheader("🗺️ Mapas de Calor Setoriais")
st.markdown("Identifique instantaneamente onde o dinheiro está entrando e de onde está fugindo hoje.")

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
      "symbolUrl": "",
      "colorTheme": "dark",
      "hasTopBar": false,
      "isDataSetEnabled": false,
      "isZoomEnabled": true,
      "hasSymbolTooltip": true,
      "width": "100%",
      "height": "100%"
    }
      </script>
    </div>
    """
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
      "symbolUrl": "",
      "colorTheme": "dark",
      "hasTopBar": false,
      "isDataSetEnabled": false,
      "isZoomEnabled": true,
      "hasSymbolTooltip": true,
      "width": "100%",
      "height": "100%"
    }
      </script>
    </div>
    """
    components.html(html_heatmap_eua, height=250)

st.caption("💡 **Dica de Caçador:** O tamanho do bloco representa o valor de mercado (Market Cap). Blocos verdes intensos indicam forte entrada de fluxo no setor.")

# ==========================================
# 🐋 INTELIGÊNCIA DE FLUXO (SALDO ESTRANGEIRO)
# ==========================================
st.divider()
st.subheader("🐋 Fluxo Institucional (O rastro do Gringo B3)")
st.markdown("Monitore se os grandes tubarões estrangeiros estão aportando ou retirando dinheiro da nossa bolsa.")

col_gringo1, col_gringo2 = st.columns([2, 1])

with col_gringo1:
    st.info("### 🇧🇷 Relatório Oficial (B3)\nO arquivo original da B3 é um relatório formatado com múltiplas tabelas. Baixe o CSV oficial para extrair o saldo mensal do investidor estrangeiro.")
    st.link_button("📥 Fazer Download Rápido do Relatório B3 (.csv)", "https://sistemaswebb3-listados.b3.com.br/marketDataProxy/MarketDataCall/GetDownloadMarketData/RELATORIO_DADOS_DE_MERCADO.csv", use_container_width=True)

with col_gringo2:
    with st.expander("📖 Rastreio Tático", expanded=True):
        st.markdown("""
        * **Gringo Comprando + IBOV Subindo:** Alta verdadeira e sustentável.
        * **Gringo Vendendo + IBOV Subindo:** Armadilha (Varejo puxando sozinho).
        * *Atenção:* Os dados da B3 possuem um atraso estrutural de **D+2**.
        """)

# ==========================================
# 🩸 RADAR DE ALUGUEL E SHORT SQUEEZE
# ==========================================
st.divider()
st.subheader("🩸 Radar de Aluguel e Short Squeeze")
st.markdown("Rastreie onde os institucionais estão apostando na queda e cace explosões de preço.")

c1, c2 = st.columns([2, 1], vertical_alignment="bottom")

with c1:
    ativo_alvo = st.text_input("Digite o Ticker da B3 (Ex: PETR4, MGLU3):", value="MGLU3", max_chars=6, key="aluguel_ticker").strip().upper()

with c2:
    btn_investigar = st.button("🔍 Investigar Posição Vendida", use_container_width=True, type="primary")

if btn_investigar and ativo_alvo:
    st.markdown(f"### 📊 Dossiê Institucional: {ativo_alvo}")
    
    # Link com fragmento de texto para tentar rolar até a seção de aluguel
    url_statusinvest = f"https://statusinvest.com.br/acoes/{ativo_alvo.lower()}#:~:text=ALUGUEL%20DE%20AÇÕES"
    
    col_info1, col_info2 = st.columns(2)
    
    with col_info1:
        st.info("#### 📉 Dados de Empréstimo B3")
        st.markdown(f"Clique no botão abaixo e **role a página até o final** para encontrar o quadro verde de 'Aluguel de Ações'.")
        st.link_button(f"🚀 Abrir Painel de {ativo_alvo}", url=url_statusinvest, use_container_width=True)
        
    with col_info2:
        st.error("#### 💣 Risco de Short Squeeze")
        st.markdown("Analise a **Taxa do Tomador**. Se estiver subindo enquanto o preço rompe resistências, o 'aperto' nos vendidos começou.")
        url_tv = f"https://br.tradingview.com/chart/?symbol=BMFBOVESPA%3A{ativo_alvo}"
        st.link_button(f"📈 Ver Gráfico Real-Time", url=url_tv, use_container_width=True)

    st.markdown("---")
    st.markdown("### 🧠 Tabela Tática de Sentimento (Short Interest)")
    
    # Tabela Interpretativa integrada
    st.markdown("""
    | Taxa do Tomador (A.A.) | Status do Aluguel | Sentimento Institucional | Ação do Caçador |
    | :--- | :--- | :--- | :--- |
    | **0% a 2%** | **Normal** | Mercado em equilíbrio ou desinteresse. | Operar apenas pelo gráfico. |
    | **2% a 7%** | **Atenção** | Institucionais montando posições de venda. | Cuidado com compras de topo. |
    | **7% a 15%** | **Alerta Urso** | Pessimismo elevado. Muitos vendidos no ativo. | Monitorar suportes relevantes. |
    | **Acima de 15%** | **BARRIL DE PÓLVORA** | Vendidos "espremidos" e pagando muito caro. | **Foco total em Short Squeeze.** |
    """)

    st.success(f"💡 **Análise de Elite para {ativo_alvo}:** Se a taxa estiver acima de 10% e o preço romper a média de 20 ou um topo anterior no gráfico, o rali será violento devido ao stop forçado dos vendidos.")

    st.divider()
    
    with st.expander("📖 GUIA RÁPIDO: Como localizar o Aluguel?", expanded=True):
        st.markdown(f"""
        Para visualizar os dados de **{ativo_alvo}**, siga estes passos na página que abrirá:
        
        1. **Role a página** até quase o fim (após a seção de Dividendos e Comunicados).
        2. Localize o quadro verde intitulado **'ALUGUEL DE AÇÕES DO {ativo_alvo}'**.
        3. **Taxa do Tomador (Média):** Acima de 10% indica alto custo para os vendidos.
        4. **Nº de Ações Alugadas:** Se este número estiver subindo, o 'exército' de ursos está crescendo.
        """)
