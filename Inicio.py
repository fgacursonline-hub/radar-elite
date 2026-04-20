import streamlit as st
from tvDatafeed import TvDatafeed, Interval
import streamlit.components.v1 as components # <-- Importação adicionada para as Notícias

# Mantendo sua configuração original de página e proteção
st.set_page_config(page_title="Caçadores de Elite", layout="wide", page_icon="🎯", initial_sidebar_state="collapsed")

if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

# Seus alunos cadastrados originais
alunos_cadastrados = {
    "aluno": "elite123",
    "joao": "senha123",
    "maria": "bolsadevalores",
    "admin": "suasenhaforte"
}

if not st.session_state['autenticado']:
    # CSS para esconder o menu antes do login
    st.markdown("<style>[data-testid='stSidebar'] {display: none;} [data-testid='stSidebarNav'] {display: none;}</style>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br><h1 style='text-align: center;'>🎯 Caçadores de Elite</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Área Restrita do Radar Quantitativo</p>", unsafe_allow_html=True)
        with st.form("form_login"):
            usuario = st.text_input("Usuário").lower().strip()
            senha = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar no Sistema", use_container_width=True):
                if usuario in alunos_cadastrados and alunos_cadastrados[usuario] == senha:
                    st.session_state['autenticado'] = True
                    st.rerun()
                else:
                    st.error("❌ Usuário ou senha incorretos.")
    st.stop()

# ==========================================
# TELA APÓS LOGIN (DASHBOARD DE ELITE)
# ==========================================

# Inicializa o TradingView na sessão global APENAS se estiver logado
if 'tv' not in st.session_state:
    try:
        st.session_state.tv = TvDatafeed()
    except Exception:
        pass

# Cabeçalho com o seu botão de saída
c_tit, c_sair = st.columns([8, 1])
with c_tit:
    st.title("🎯 Terminal Caçadores de Elite")
    st.markdown("Bem-vindo ao seu Quartel-General de Operações Institucionais.")
with c_sair:
    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
    if st.button("🚪 Sair", use_container_width=True):
        st.session_state['autenticado'] = False
        st.rerun()

st.divider()

# --- TERMÔMETRO DO MERCADO ---
st.subheader("🌐 Termômetro do Mercado (IBOVESPA)")
st.markdown("Visão geral de como está a força do mercado brasileiro hoje.")

try:
    tv = st.session_state.tv
    df_ibov = tv.get_hist(symbol='IBOV', exchange='BMFBOVESPA', interval=Interval.in_daily, n_bars=2)
    
    if df_ibov is not None and len(df_ibov) >= 2:
        fecho_hoje = df_ibov['close'].iloc[-1]
        fecho_ontem = df_ibov['close'].iloc[-2]
        variacao = ((fecho_hoje - fecho_ontem) / fecho_ontem) * 100
        
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.metric(label="Pontuação Atual", value=f"{fecho_hoje:,.0f} pts", delta=f"{variacao:.2f}%")
        with col_m2:
            estado_mercado = "🐂 Bull Market (Comprador)" if variacao > 0 else "🐻 Bear Market (Vendedor)"
            st.info(f"**Sentimento:** {estado_mercado}")
        with col_m3:
            st.warning("💡 **Dica de Ouro:** Não lute contra a tendência principal do IBOV.")
    else:
        st.caption("Aguardando conexão com os dados da B3...")
except Exception as e:
    st.caption("Sem conexão com os dados do mercado no momento.")

st.divider()

# --- O SEU ARSENAL ---
st.subheader("🛠️ O Seu Arsenal de Ferramentas")
st.markdown("Selecione sua estratégia no menu lateral à esquerda para iniciar as varreduras.")

c1, c2, c3 = st.columns(3)

with c1:
    st.info("### 📉 IFR & Keltner\nDescubra ativos sobrevendidos, esticados e com anomalias de volatilidade usando a regressão à média.")

with c2:
    st.warning("### 🔥 Setup 9.1\nO rastreador de inércia e tendência do lendário Larry Williams. Compre a força e venda a fraqueza.")

with c3:
    st.success("### 🕳️ Smart Money (FVG)\nOpere exatamente como os bancos institucionais, encontrando vácuos de liquidez e armadilhas.")

st.divider()

# ==========================================
# 4. RADAR DE NOTÍCIAS (FONTE: INFOMONEY)
# ==========================================
st.subheader("📰 Radar de Notícias - Brasil")
st.markdown("As últimas manchetes do mercado financeiro em tempo real.")

import xml.etree.ElementTree as ET
import requests
from datetime import datetime

def buscar_noticias_br():
    try:
        # Usando o Feed RSS do InfoMoney (100% em português e focado em mercado)
        url = "https://www.infomoney.com.br/feed/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        
        # Parseando o XML das notícias
        root = ET.fromstring(response.content)
        noticias = []
        
        for item in root.findall('./channel/item')[:10]: # Pega as 10 últimas
            titulo = item.find('title').text
            link = item.find('link').text
            data_pub = item.find('pubDate').text
            
            # Formata a data (opcional)
            noticias.append({"titulo": titulo, "link": link, "data": data_pub})
        return noticias
    except:
        return None

noticias = buscar_noticias_br()

if noticias:
    for n in noticias:
        # Cria um box bonitinho para cada notícia
        with st.container():
            st.markdown(f"**{n['titulo']}**")
            st.caption(f"📅 {n['data']}")
            st.markdown(f"[Ler notícia completa]({n['link']})")
            st.divider()
else:
    st.info("Não foi possível carregar as notícias brasileiras no momento. Tente novamente em instantes.")
