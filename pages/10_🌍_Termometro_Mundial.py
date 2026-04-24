import streamlit as st
import plotly.graph_objects as go
import requests
import streamlit.components.v1 as components
import pandas as pd # <-- Adicionado para ler o CSV da B3

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
# 🗺️ MAPA DE CALOR GLOBAL (HEATMAP)
# ==========================================
st.divider()
st.subheader("🗺️ Mapa de Calor: Wall Street (S&P 500)")
st.markdown("Identifique instantaneamente onde o dinheiro está entrando e de onde está fugindo hoje.")

heatmap_url = "https://finviz.com/map.ashx?t=sec"
components.iframe(heatmap_url, height=500, scrolling=True)

st.caption("💡 **Dica de Caçador:** Blocos verdes grandes indicam fluxo institucional em Big Techs. Blocos vermelhos em setores específicos podem indicar rotação de carteira.")

# ==========================================
# 🐋 INTELIGÊNCIA DE FLUXO (SALDO ESTRANGEIRO)
# ==========================================
st.divider()
st.subheader("🐋 Fluxo Institucional (O rastro do Gringo B3)")
st.markdown("Monitore se os grandes tubarões estrangeiros estão aportando ou retirando dinheiro da nossa bolsa.")

# Função que vai baixar e ler a tabela da B3 silenciosamente
@st.cache_data(ttl=3600) # Atualiza a cada 1 hora
def puxar_fluxo_gringo_b3():
    url_b3 = "https://sistemaswebb3-listados.b3.com.br/marketDataProxy/MarketDataCall/GetDownloadMarketData/RELATORIO_DADOS_DE_MERCADO.csv"
    try:
        # Lê o CSV da URL. Usa separador ';' e codificação para ler acentuação do português
        df = pd.read_csv(url_b3, sep=';', encoding='latin-1', on_bad_lines='skip')
        df = df.dropna(how='all') # Remove linhas completamente em branco
        return df
    except Exception as e:
        return f"Erro de conexão com o servidor da B3: {e}"

# Roda a extração
with st.spinner("Interceptando dados de fluxo no servidor da B3..."):
    dados_b3 = puxar_fluxo_gringo_b3()

# Verifica se o robô conseguiu baixar e transformar em DataFrame
if isinstance(dados_b3, pd.DataFrame):
    st.success("✅ **Dados oficiais da B3 interceptados com sucesso!**")
    # Mostra a tabela lindamente na tela do Streamlit
    st.dataframe(dados_b3, use_container_width=True, hide_index=True)
else:
    # Se a B3 estiver fora do ar ou bloquear o robô, mostra erro e o botão de segurança
    st.warning("Aviso: Não foi possível pré-carregar a tabela neste momento. O servidor da B3 pode estar instável.")
    st.link_button("📥 Tentar baixar CSV Manualmente", "https://sistemaswebb3-listados.b3.com.br/marketDataProxy/MarketDataCall/GetDownloadMarketData/RELATORIO_DADOS_DE_MERCADO.csv", use_container_width=True)

with st.expander("📖 Por que rastrear o Gringo?", expanded=False):
    st.markdown("""
    O investidor estrangeiro é responsável por mais de **50% do volume da B3**. 
    
    * **Gringo Comprando + IBOV Subindo:** Tendência saudável e forte. O "dinheiro inteligente" está apostando no país.
    * **Gringo Vendendo + IBOV Subindo:** Alerta de armadilha. A alta pode estar sendo sustentada apenas pelo varejo (pessoa física), o que costuma durar pouco.
    * **D+2:** Lembre-se que o dado oficial da B3 sempre carrega um atraso operacional de 2 dias úteis. Analise o saldo acumulado para confirmar tendências primárias.
    """)
